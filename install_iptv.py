import os
import pwd
import re
import subprocess
import shutil
from configparser import ConfigParser
from pathlib import Path

from fill_ini import channels, search_url

try:
    user = pwd.getpwuid(os.getuid()).pw_name
except KeyError:
    raise ValueError("Unable to determine current system user")

home = Path(pwd.getpwnam(user).pw_dir)

print("Configuration des fournisseurs d'IPTV:\n")

print(
    "L'enregistrement de flux IPTV nécessite au minimum un lien m3u8 vers la source du flux. Afin "
    "de faciliter l'organisation des liens m3u8, ceux-ci sont regroupés par fournisseurs dans des "
    "fichiers .ini .\n"
    "Un lien m3u8 est composé d'une URL avec un numéro qui permet d'identifier la "
    "chaîne du flux ainsi qu'un identifiant et d'un mot de passe pour les fournisseurs d'IPTV payants."
)

print(
    "Ce programme permet d'ajouter les liens m3u8 dans un fichier de configuration .ini "
    "à partir d'un fichier se terminant par _original.ini que vous avez récupéré ou que vous avez "
    "construit manuellement en attribuant un numéro d'identification pour chaque chaines "
    "disponibles dans iptv-select.fr et votre fournisseurs d'IPTV.\n"
    "Le fichier de configuration se terminant par _original.ini ne sera pas modifié par ce programme. "
    "Un fichier de configuration avec le nom de votre fournisseur iptv et l'extension .ini "
    "sera créé ainsi qu'une sauvegarde de celui-ci se terminant par .ini.bak si vous lancez ce "
    "programme de nouveau (pour changer votre mot de passe par exemple). Un fichier "
    "terminant par _original_m3ulinks.ini sera également créé pour sauvegarder les chaines originales "
    "de votre fournisseur d'IPTV si des chaines non fonctionnelles sont enlevés du fichier .ini."
)

iptv_provider = ""

while iptv_provider == "":
    iptv_provider = input(
        "Quel est le nom de votre fournisseur d'IPTV? (Le nom renseigné doit correspondre au "
        "fichier de configuration du fournisseur se terminant par l'extension.ini).  Par exemple, si "
        "votre fichier de configuration est nommé moniptvquilestbon_original.ini, le nom de votre fournisseur à "
        "renseigner est moniptvquilestbon : \n"
    ).strip()

iptv_provider = os.path.basename(iptv_provider)

if (
    not re.fullmatch(r"[A-Za-z0-9._-]{1,255}", iptv_provider)
    or iptv_provider in {".", ".."}
    or iptv_provider.startswith(".")
):
    print(f"Invalid iptv_provider name: {iptv_provider}")
    exit(1)

lines = []
urls_txt = home / ".local" / "share" / "iptvselect-fr" / "urls.txt"

try:
    if urls_txt.exists() and urls_txt.is_file():
        with urls_txt.open(encoding="utf-8") as file:
            lines = file.read().splitlines()
except Exception:
    lines = []

url_provider = ""

if len(lines) > 0:
    for line in reversed(lines):
        try:
            # Expecting lines of the form "<provider>: <url...>"
            if line.startswith(f"{iptv_provider}:"):
                parts = line.split(": ", 1)
                if len(parts) == 2:
                    url_candidate = parts[1].strip()
                    # quick sanity check for 'channel_id' presence or at least a scheme
                    if url_candidate:
                        url_provider = url_candidate
                        break
        except Exception:
            continue

manual, manual_crypt, manual_url, automate = "nono", "nono", "nono", "nono"
answers = ["oui", "non", ""]

if url_provider != "":
    print(
        "Le programme a détecter l'url suivante qui provient d'une "
        "précédente analyse du fichier m3u de votre fournisseur "
        "d'IPTV {iptv_provider}:\n\n".format(iptv_provider=iptv_provider)
        + url_provider
    )
    while manual.lower() not in answers:
        manual = input(
            "\nVoulez-vous utiliser ce lien URL pour construire le fichier de "
            "configuration .ini? (répondre par oui ou non): \n"
        ).strip().lower()

if manual == "non" or url_provider == "":
    url_provider = ""
    # We'll preserve the original interactive/looping behavior, but replace 'ls' calls
    while "channel_id" not in url_provider:
        while automate not in answers:
            automate = input(
                "\nVoulez-vous lancer une recherche automatique du "
                "lien url à partir du fichier m3u de votre founisseur "
                "d'IPTV? (répondre par oui ou non). Remarque: La "
                "recherche peut durer de nombreuses minutes si "
                "votre fichier m3u est volumineux: \n"
            ).strip().lower()

        if automate == "oui" or automate == "":
            m3u_file = "123456"
            ls_result = "abcdef"
            # Prepare allowed directory for provider m3u files
            config_dir = (home / ".config" / "iptvselect-fr" / "iptv_providers").resolve()
            # Ensure config_dir exists (if not, we'll still allow user to input, but checks below will fail)
            while ls_result != str(config_dir / f"{m3u_file}.m3u"):
                m3u_file = input(
                    "Quel est le nom du fichier m3u de votre "
                    "fournisseur d'IPTV? (renseignez le nom "
                    "sans l'extension .m3u): "
                ).strip()

                # sanitize m3u_file: do not allow path separators or traversal in the filename itself
                m3u_file_basename = os.path.basename(m3u_file)
                if m3u_file_basename != m3u_file:
                    print(
                        "Nom de fichier invalide (ne doit pas contenir de séparateurs de chemin). "
                        "Veuillez indiquer uniquement le nom du fichier sans chemin ni extension."
                    )
                    continue

                # Build expected path
                m3u_path = config_dir / f"{m3u_file}.m3u"

                try:
                    if not m3u_path.exists() or not m3u_path.is_file():
                        print(
                            f"Le fichier {m3u_file}.m3u n'est pas présent dans votre"
                            " dossier iptv_providers. Insérer le fichier m3u de "
                            " votre fournisseur d'IPTV ou modifier le nom du fichier "
                            "m3u pour qu'il corresponde à celui du fichier présent "
                            "dans le dossier.\n"
                        )
                        ls_result = "abcdef"
                        continue

                    # Resolve and ensure it's inside the allowed directory (prevent symlink escape)
                    try:
                        real_file = m3u_path.resolve(strict=True)
                    except FileNotFoundError:
                        print(
                            f"Le fichier {m3u_file}.m3u non trouvé après résolution. "
                            "Vérifiez le chemin et les permissions."
                        )
                        ls_result = "abcdef"
                        continue

                    # Prevent path traversal or symlink pointing outside the config dir
                    if config_dir not in real_file.parents and real_file != config_dir:
                        print(
                            "Le fichier m3u est situé en dehors du dossier autorisé iptv_providers. "
                            "Action refusée."
                        )
                        ls_result = "abcdef"
                        continue

                    # If all checks pass, set ls_result to the canonical path string to exit loop
                    ls_result = str(real_file)
                except PermissionError:
                    print(
                        f"Permission refusée pour accéder au fichier {m3u_path}. "
                        "Vérifiez les permissions du fichier."
                    )
                    ls_result = "abcdef"
                except Exception as e:
                    print(f"Erreur inattendue lors de la vérification du fichier m3u: {e}")
                    ls_result = "abcdef"

            print("\nLancement de la recherche des liens urls:\n")

            search_urls = search_url(channels, m3u_file)

            if len(search_urls[0]) == 0 and search_urls[1] > 0:
                print("\nLe script a déterminé que les liens urls sont chiffrés.\n")
                while manual_crypt.lower() not in answers:
                    manual_crypt = input(
                        "\nSi vous pensez que c'est une erreur, vous pouvez "
                        "passer en mode manuel pour inscrire l'url "
                        "correspondante. Voulez-vous passer en mode manuel? "
                        "(Répondre par oui ou non): \n"
                    ).strip().lower()
                if manual_crypt == "non":
                    exit(0)
                else:
                    automate = "non"
            elif len(search_urls[0]) == 0 and search_urls[1] == 0:
                print(
                    "\nLe script fill_ini.py n'a pas pu déterminer de lien url dans "
                    "votre fichier {m3u_file}.m3u".format(m3u_file=m3u_file)
                )
            else:
                print("\nLe script fill_ini.py a déterminé l'url suivante: \n")
                url_provider = (
                    search_urls[0][0][0] + "channel_id" + search_urls[0][0][1]
                )
                print(url_provider)
                print(
                    "\n\nchannel_id représente la partie numérique correspondant "
                    "aux différentes chaines."
                )
                while manual_url.lower() not in answers:
                    manual_url = input(
                        "\nSi vous pensez que c'est une erreur, vous pouvez "
                        "passer en mode manuel pour inscrire l'url "
                        "correspondante. Voulez-vous passer en mode manuel? "
                        "(Répondre par oui ou non): \n"
                    ).strip().lower()
                if manual_url == "non":
                    break

        # Manual entry for url_provider if automation not used or failed
        url_provider = input(
            "\nQuel est le lien URL de votre fournisseur d'IPTV? Le lien doit mentionner "
            "votre identifiant, votre mot de passe et le mot channel_id pour la partie correpondant aux "
            "numéros qui sont déjà présents dans le fichier de configuration pour chaques chaînes. Voici "
            "un exemple de lien à mentionner: \n"
            "http://moniptvquilestbon:8080/live/monsuperpseudo/khkjcbniufh/26491.m3u8 qui peut être transcrit en \n"
            "http://moniptvquilestbon:8080/live/votre_identifiant/votre_mot_de_passe/channel_id.m3u8 . Dans ce cas, "
            "il vous faudra mentionner l'url suivante: \n"
            "http://moniptvquilestbon:8080/live/monsuperpseudo/khkjcbniufh/channel_id.m3u8\n"
            "\nIl faut veiller à ne pas prendre un lien m3u qui correspond au streaming d'une vidéo car "
            "ces liens m3u se terminent généralement par .mkv ou .avi et sont différents des liens m3u"
            "correspondant aux chaines. Recherchez une chaine dans votre fichier m3u (par exemple "
            "France 2) puis copiez/collez le lien m3u correspondant."
            "\nIl suffit ensuite de remplacer le numéro correspondant à l'identification de la chaine. Voici un "
            "autre exemple où channel_id remplace le numéro d'identification de la chaine: \n\n"
            "http://moniptvquilestbon:8080/live/monsuperpseudo/khkjcbniufh/26491 qui peut être transcrit en \n"
            "http://moniptvquilestbon:8080/live/votre_identifiant/votre_mot_de_passe/channel_id . Dans ce cas, "
            "il vous faudra mentionner l'url suivante: \n"
            "http://moniptvquilestbon:8080/live/monsuperpseudo/khkjcbniufh/channel_id\n"
        ).strip()

        if "channel_id" not in url_provider:
            print(
                "\n************\n\n!!!!Attention!!!! Vous n'avez pas remplacé le numéro identifiant "
                "la chaine par le mot clé channel_id. Faites attention à bien remplacer seulement "
                "le numéro de la chaine dans le lien m3u car si vous remplacez une autre partie du "
                "lien, les enregistrements ne seront pas déclenchés.\n\n**************\n"
            )

# ---------------------------
# Prepare paths for ini handling
# ---------------------------
base = home / ".config" / "iptvselect-fr" / "iptv_providers"
ini_path = base / f"{iptv_provider}.ini"
bak_path = base / f"{iptv_provider}.ini.bak"
original_path = base / f"{iptv_provider}_original.ini"

try:
    if ini_path.exists() and ini_path.is_file():
        try:
            shutil.copy2(ini_path, bak_path)
            # Enforce restrictive permissions on the backup as well
            try:
                os.chmod(bak_path, 0o600)
            except Exception:
                pass
        except Exception as e:
            print(f"Warning: unable to create backup {bak_path}: {e}")
except Exception as e:
    print(f"Warning: could not inspect existing ini file: {e}")

# Copy original -> ini if original exists; fail if permission denied
try:
    if not original_path.exists():
        print(f"Original file not found: {original_path}")
    else:
        shutil.copy2(original_path, ini_path)
        try:
            os.chmod(ini_path, 0o600)
        except Exception:
            # If chmod is not available or fails, fall back silently but keep file
            pass
except PermissionError as e:
    print(f"Permission denied while copying file: {e}")
    exit(1)
except Exception as e:
    print(f"Unexpected error while copying file: {e}")
    exit(1)

config_file = str(ini_path)
config_object = ConfigParser()
config_object.read(config_file)

# ---------------------------
# Update CHANNELS in the config
# - keep writing inside the loop as original, but use atomic write to avoid partial writes
# ---------------------------
try:
    # ensure section exists before attempting to iterate
    if "CHANNELS" not in config_object:
        raise KeyError("CHANNELS")
    for channel, channel_id in list(config_object["CHANNELS"].items()):
        if channel_id != "":
            config_object["CHANNELS"][channel] = url_provider.replace("channel_id", channel_id)
        else:
            config_object["CHANNELS"][channel] = ""

        # Perform atomic write to avoid corrupted files if interrupted
        temp_path = ini_path.with_suffix(ini_path.suffix + ".tmp")
        try:
            with temp_path.open("w", encoding="utf-8") as conf:
                config_object.write(conf)
            # atomic replace
            os.replace(str(temp_path), str(ini_path))
            # enforce restrictive permissions on the final ini file
            try:
                os.chmod(ini_path, 0o600)
            except Exception:
                pass
        finally:
            # ensure temp file removed if present
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except Exception:
                pass
except KeyError:
    print(
        "\nLe fichier de configuration n'est pas conforme ([CHANNELS] n'est pas présent "
        "au début du fichier) ou vous avez mal renseigné le nom de votre fournisseur "
        "iptv (si par exemple votre fichier de configuration est nommé moniptvquilestbon_original.ini, vous devez "
        "renseigner moniptvquilestbon dans le programme d'installation install_iptv.py)"
    )
    exit(1)

try:
    src = base / f"{iptv_provider}.ini"
    dest = base / f"{iptv_provider}_original_m3ulinks.ini"
    if src.exists() and src.is_file():
        shutil.copy2(src, dest)
        try:
            os.chmod(dest, 0o600)
        except Exception:
            pass
    else:
        print(f"Warning: source ini not found for creating m3ulinks copy: {src}")
except Exception as e:
    print(f"Warning: could not create original m3ulinks copy: {e}")

print(
    f"\nVotre fichier {iptv_provider}.ini est maintenant configuré avec les liens m3u de votre "
    "fournisseur d'IPTV.\n"
)
