import os
import re
import shutil
import logging
import getpass

from pathlib import Path
from unidecode import unidecode

_user = os.environ.get("USER")
if not _user:
    try:
        _user = getpass.getuser()
    except Exception:
        _user = None
if not _user:
    logging.error("Unable to determine user. Exiting.")
    raise SystemExit("Unable to determine user")

user = _user

channels = [
    "13eme rue",
    "al jazeera english",
    "altice studio",
    "bfm paris",
    "cartoon network",
    "chasse et peche",
    "cherie 25",
    "club rtl",
    "crime district",
    "nrj 12",
    "nrj hits",
    "ocs choc",
    "ocs geants",
    "ocs max",
]


def _is_valid_basename(name: str) -> bool:
    """Return True if name is a simple, safe basename we accept (no path separators, no ..).

    Allowed characters: letters, digits, spaces, underscores, hyphens and plus sign.
    Reject empty and anything containing os.sep or ".." or beginning with a dot.
    """
    if not name:
        return False
    if name.startswith('.'):
        return False
    if os.path.sep in name or ('/' in name) or ('\\' in name):
        return False
    if '..' in name:
        return False
    # keep a permissive but safe char set; validate at least one alnum
    if not re.search(r"[A-Za-z0-9]", name):
        return False
    # Reject names with weird control characters
    if re.search(r"[\x00-\x1f\x7f]", name):
        return False
    return True


def _ensure_dir_secure(path: Path, mode: int = 0o700):
    """Ensure a directory exists and has at most the given mode bits for owner.

    We create parents if necessary. We do not make directory world-writable.
    """
    path.mkdir(parents=True, exist_ok=True)
    try:
        # restrict permissions to owner only (mask out group/other)
        path.chmod(mode)
    except Exception:
        # On some platforms chmod may not be permitted; still continue
        logging.debug(f"Could not chmod {path}")


def _safe_copy(src: Path, dst: Path, mode: int = 0o600):
    """Copy a file preserving metadata and set secure permissions on destination.

    Raises OSError on failure.
    """
    shutil.copy2(str(src), str(dst))
    try:
        dst.chmod(mode)
    except Exception:
        logging.debug(f"Could not set permissions on {dst}")


def search_url(channels, m3u_file):
    """Search url for channels in m3u file

    Recreated logic but with safer file handling and validation of m3u_file.
    """
    if not _is_valid_basename(m3u_file):
        raise ValueError("Invalid m3u file name")

    links = []
    crypted = 0

    m3u_path = Path("/home") / user / ".config" / "iptvselect-fr" / "iptv_providers" / f"{m3u_file}.m3u"

    expected_dir = Path("/home") / user / ".config" / "iptvselect-fr" / "iptv_providers"
    try:
        if expected_dir not in m3u_path.parents:
            raise ValueError("m3u path outside allowed directory")
    except Exception:
        raise ValueError("Invalid m3u_file path")

    match = False

    try:
        with m3u_path.open("r", encoding="utf-8", errors="ignore") as m3u:
            for link in m3u:
                if match is True:
                    m3u_link = link
                    part_link = re.findall(r".*/", m3u_link)
                    if len(part_link) > 0:
                        part1 = part_link[0]
                        left = m3u_link.replace(part1, "")
                        if left.isdigit():
                            part2 = ""
                        else:
                            try:
                                part2 = re.findall(r"\..*", left)[0]
                            except IndexError:
                                part2 = ""
                        channel_id = m3u_link.replace(part1, "")
                        channel_id = channel_id.replace(part2, "")
                        if channel_id.endswith("\n"):
                            channel_id = channel_id[:-1]
                        if channel_id.isdigit():
                            if len(links) == 0:
                                links.append((part1, part2, 1))
                            else:
                                added = False
                                change = []
                                for indexo, url in enumerate(links):
                                    if url[0] == part1 and url[1] == part2:
                                        change.append((indexo, url[0], url[1], url[2] + 1))
                                        added = True
                                        break
                                if added is False:
                                    links.append((part1, part2, 1))
                                for ch in change:
                                    # use the saved 'url' variable only in a controlled way
                                    links[ch[0]] = (url[0], url[1], url[2] + 1)
                        else:
                            crypted += 1

                match = False
                if not link:
                    continue
                if link[0] == "#":
                    link_low = unidecode(link.lower())
                    if "tvg-name" in link_low:
                        link_tvg = re.findall('tvg-name="(.*?)"', link_low)
                    else:
                        link_tvg = [link_low]
                    if len(link_tvg) > 0:
                        for chan in channels:
                            if (
                                chan in link_tvg[0]
                                or chan.replace(" ", "") in link_tvg[0]
                                or chan.replace(" ", "-") in link_tvg[0]
                                or chan.replace(" ", "_") in link_tvg[0]
                                or chan.replace("'", "") in link_tvg[0]
                                or chan.replace("+", "") in link_tvg[0]
                            ):
                                info = link
                                match = True
                                break
    except FileNotFoundError:
        logging.error(f"m3u file not found: {m3u_path}")
        raise
    except OSError as e:
        logging.error(f"Error reading m3u file {m3u_path}: {e}")
        raise

    return (links, crypted)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    iptv_provider = "@"

    while not (iptv_provider.isalnum() and len(iptv_provider) <= 64):
        iptv_provider = input(
            "Quel est le nom de votre fournisseur d'IPTV? "
            "(renseignez un nom ne contenant que des "
            "caractères alphanumériques sans espace): "
        ).strip()

    home_user = Path("/home") / user
    dst_dir = home_user / ".config" / "iptvselect-fr" / "iptv_providers"
    _ensure_dir_secure(dst_dir, mode=0o700)

    src = Path("iptv_providers") / "iptv_select_channels.ini"
    dst = dst_dir / f"{iptv_provider}.ini"

    try:
        if not src.exists():
            logging.error(f"Source file not found: {src}")
        else:
            _safe_copy(src, dst)
    except OSError as e:
        logging.error(f"Failed to copy {src} -> {dst}: {e}")

    ini_path = dst
    try:
        with ini_path.open("r", encoding="utf-8", errors="ignore") as ini:
            first_line = ini.readline()
            lines = ini.read().splitlines()
    except Exception as e:
        logging.error(f"Unable to read ini file {ini_path}: {e}")
        raise

    m3u_file = "123456"

    while True:
        m3u_file_candidate = input(
            "Quel est le nom du fichier m3u de votre "
            "fournisseur d'IPTV? (renseignez le nom "
            "sans l'extension .m3u): "
        ).strip()

        if not _is_valid_basename(m3u_file_candidate):
            print("Nom de fichier invalide. N'utilisez pas de caractères spéciaux ou de chemins.")
            continue

        file_path = Path("/home") / user / ".config" / "iptvselect-fr" / "iptv_providers" / f"{m3u_file_candidate}.m3u"

        if not file_path.exists():
            print(
                f"Le fichier {m3u_file_candidate}.m3u n'est pas présent dans votre "
                "dossier ~/.config/iptvselect-fr/iptv_providers. "
                "Insérer le fichier m3u de votre fournisseur d'IPTV "
                "ou modifier le nom du fichier m3u pour qu'il corresponde "
                "à celui du fichier présent dans le dossier.\n"
            )
            continue

        m3u_file = m3u_file_candidate
        break

    match = False

    print(
        "\nCertain fichier de liens m3u contiennent des urls chiffrées. Avec ce "
        "type de fichier, vous ne pourrez pas construire de fichiers .ini originaux "
        "car les identifiants des chaines ne peuvent pas être récupérés. Le script "
        "fill_ini.py se chargera dans ce cas de construire directement le "
        "fichier final .ini contenant les urls.\n"
    )

    answers = ["oui", "non", ""]

    print(
        "Le script fill_ini.py peut rechercher pour vous le lien urls correspondant "
        "aux chaines du fichier m3u de votre fournisseur d'IPTV.\n"
    )

    search = "nono"

    while search.lower() not in answers:
        search = input(
            "Voulez-vous lancer une recherche automatique? (répondre par oui ou non). "
            "Remarque: La recherche peut durer de nombreuses minutes si votre fichier "
            "m3u est volumineux: "
        ).strip()

    manual = "nono"
    crypted = "nono"

    if search.lower() == "oui" or search.lower() == "":
        print("\nLancement de la recherche des liens urls:\n")
        search_urls = search_url(channels, m3u_file)

        if len(search_urls[0]) == 0 and search_urls[1] > 0:
            print("\nLe script a déterminé que les liens urls sont chiffrés.\n")
            while manual.lower() not in answers:
                manual = input(
                    "\nSi vous pensez que c'est une erreur, vous pouvez "
                    "passer en mode manuel pour inscrire l'url "
                    "correspondante. Voulez-vous passer en mode manuel? "
                    "(Répondre par oui ou non): "
                ).strip()
            if manual.lower() == "non":
                crypted = "oui"
        elif len(search_urls[0]) == 0 and search_urls[1] == 0:
            print(
                "\nLe script fill_ini.py n'a pas pu déterminer de lien url dans "
                f"votre fichier {m3u_file}.m3u"
            )
            manual = "oui"
        else:
            print("\nLe script fill_ini.py a déterminé l'url suivante: \n")
            url_provider = search_urls[0][0][0] + "channel_id" + search_urls[0][0][1]
            print(url_provider)
            print(
                "\n\nchannel_id représente la partie numérique correspondant "
                "aux différentes chaines."
            )
            while manual.lower() not in answers:
                manual = input(
                    "\nSi vous pensez que c'est une erreur, vous pouvez "
                    "passer en mode manuel pour inscrire l'url "
                    "correspondante. Voulez-vous passer en mode manuel? "
                    "(Répondre par oui ou non): \n"
                ).strip()

    if (
        search.lower() in ["oui", ""]
        and manual.lower() not in ["oui", ""]
        and crypted != "oui"
    ):
        # Save url_provider into a user-local urls file with secure permissions
        urls_dir = Path.home() / ".local" / "share" / "iptvselect-fr"
        _ensure_dir_secure(urls_dir, mode=0o700)
        urls_file = urls_dir / "urls.txt"
        try:
            # create file if not exists with restrictive permissions
            if not urls_file.exists():
                urls_file.touch(mode=0o600)
            with urls_file.open("a", encoding="utf-8", errors="ignore") as file:
                file.write(iptv_provider + ": " + url_provider + "\n")
            try:
                urls_file.chmod(0o600)
            except Exception:
                logging.debug(f"Could not chmod {urls_file}")
        except Exception as e:
            logging.error(f"Unable to write urls file {urls_file}: {e}")

    extension = [".avi", ".mkv", ".mp4"]
    selected = []

    if search.lower() == "non" or manual == "oui" or manual == "":
        while crypted.lower() not in answers:
            crypted = input(
                "\nEst-ce-que les urls des liens m3u sont chiffrées? \n\nSi vous ne pouvez pas "
                "identifier un couple identifiant/mot de passe et un identifiant de chaine "
                "alors les liens m3u sont chiffrées. Exemple de liens m3u non chiffré: \n\n"
                "#chaine n°1\n"
                "http://fournisseuriptv-non-chiffré:8081/monsuperpseudo/khkjcbniufh/26491.ts\n"
                "#chaine n°2\n"
                "http://fournisseuriptv-non-chiffré:8081/monsuperpseudo/khkjcbniufh/36502.ts\n"
                "#chaine n°3\n"
                "http://fournisseuriptv-non-chiffré:8081/monsuperpseudo/khkjcbniufh/68582.ts\n"
                "\nOn remarque clairement un couple identifiant/mot de passe qui se répête et "
                "une partie numérique qui est différente pour chaque chaines.\n"
                "\nExemple de liens m3u chiffré: \n\n"
                "#chaine n°1\n"
                "http://fournisseuriptv-chiffré:8081/qwertyqfdkjh9skfhjkds8lsdqfksdfjddd/m3u8\n"
                "#chaine n°2\n"
                "http://fournisseuriptv-chiffré:8081/qwertysdfhqsklf7dsqkjfhds6qksdfdslk/m3u8\n"
                "#chaine n°3\n"
                "http://fournisseuriptv-chiffré:8081/qwertysqdfk6lkfhqskqsfjkd7sqdsfdsdq/m3u8\n"
                "\nDans ce cas on ne peut pas identifier un couple identifiant/mot de passe "
                "qui se répête ni une partie numérique qui est différente pour chaque chaines.\n"
                "Répondre par oui ou non: "
            ).strip()

        print("\n*************************************************************")

        url_provider = ""

        if crypted.lower() == "non":
            while "channel_id" not in url_provider:
                url_provider = input(
                    "\nQuel est le lien URL de votre fournisseur d'IPTV? Le lien doit mentionner "
                    "votre identifiant, votre mot de passe et le mot channel_id pour la partie correpondant aux "
                    "numéros qui sont déjà présents dans le fichier de configuration pour chaques cha\u00eenes. Voici "
                    "un exemple de lien à mentionner: \n\n"
                    "http://fournisseuriptv:8081/monsuperpseudo/khkjcbniufh/26491.ts qui peut être transcrit en \n"
                    "http://fournisseuriptv:8081/votre_identifiant/votre_mot_de_passe/channel_id.ts . Dans ce cas, "
                    "il vous faudra mentionner l'url suivante: \n"
                    "http://fournisseuriptv:8081/monsuperpseudo/khkjcbniufh/channel_id.ts\n"
                    "\nIl faut veiller à ne pas prendre un lien m3u qui correspond au streaming d'une vidéo car "
                    "ces liens m3u se terminent généralement par .mkv ou .avi et sont différents des liens m3u "
                    "correspondant aux chaines. Recherchez une chaine dans votre fichier m3u (par exemple "
                    "France 2) puis copiez/collez le lien m3u correspondant."
                    "\nIl suffit ensuite de remplacer le numéro correspondant à l'identification de la chaine. Voici un "
                    "autre exemple où channel_id remplace le numéro d'identification de la chaine: \n\n"
                    "http://fournisseuriptv:8081/monsuperpseudo/khkjcbniufh/26491 qui peut être transcrit en \n"
                    "http://fournisseuriptv:8081/votre_identifiant/votre_mot_de_passe/channel_id . Dans ce cas, "
                    "il vous faudra mentionner l'url suivante: \n"
                    "http://fournisseuriptv:8081/monsuperpseudo/khkjcbniufh/channel_id\n"
                ).strip()
                if "channel_id" not in url_provider:
                    print("\nVous n'avez pas renseigné le channel_id dans votre URL!\n")

    if crypted.lower() != "oui":
        splitted = url_provider.split("channel_id")
    else:
        splitted = []

    chans_spec = ["lci", "lcp"]

    print(
        "\nLe script va maintenant vous proposer une sélection de liens m3u pour "
        "toutes les chaînes présentes dans iptv-select.fr . La durée pour "
        "afficher une sélection de chaines peut être de plusieurs secondes. "
        "Par exemple, la chaine France 3 est souvent longue car il faut "
        "attendre le filtrage des chaines régionales qui ne sont pas souvent "
        "présentes dans les fichiers m3u.\nIl faudra donc faire attention "
        "de ne pas appuyer plusieurs fois sur la touche entrée pour valider "
        "un choix de lien m3u et bien attendre le retour du curseur pour la "
        "prochaine question avant d'appuyer de nouveau sur la touche "
        "entrée (si vous appuyez plusieurs fois sur entrée pour une même "
        "chaine, les prochaines chaines seront sélectionnées sur le 1er "
        "lien m3u proposé).\n"
    )

    for line in lines:
        chan_low = line[:-3].lower()
        if chan_low[:3] in chans_spec:
            chan_low = chan_low[:3]
        m3u_path = Path("/home") / user / ".config" / "iptvselect-fr" / "iptv_providers" / f"{m3u_file}.m3u"
        links = []
        match = False
        info = ""
        try:
            with m3u_path.open("r", encoding="utf-8", errors="ignore") as m3u:
                for link in m3u:
                    if match is True and (not link.endswith(tuple(extension))):
                        m3u_link = link
                        links.append((info, m3u_link))
                    match = False
                    if not link:
                        continue
                    if link[0] == "#":
                        link_low = unidecode(link.lower())
                        if "tvg-name" in link_low:
                            link_tvg = re.findall('tvg-name="(.*?)"', link_low)
                        else:
                            link_tvg = [link_low]
                        if len(link_tvg) > 0:
                            if (
                                chan_low in link_tvg[0]
                                or chan_low.replace(" ", "") in link_tvg[0]
                                or chan_low.replace(" ", "-") in link_tvg[0]
                                or chan_low.replace(" ", "_") in link_tvg[0]
                                or chan_low.replace("'", "") in link_tvg[0]
                                or chan_low.replace("+", "") in link_tvg[0]
                            ):
                                info = link
                                match = True
                            elif (
                                chan_low[:8] == "france 3"
                                and len(chan_low) > 8
                                and chan_low.replace("france 3", "f3") in link_tvg[0]
                            ):
                                info = link
                                match = True
        except FileNotFoundError:
            logging.error(f"m3u file not found during channel scan: {m3u_path}")
            links = []
        except OSError as e:
            logging.error(f"Error reading m3u file {m3u_path}: {e}")
            links = []

        rank = 1
        rank_2 = 1
        ranking = []
        select = -1

        if len(links) > 0:
            print(
                "*********************************************************************"
                "\nVoici les résultats de la recherche de la chaine " + line[:-3] + "\n"
                "*********************************************************************"
            )
            for m3u in links:
                print(str(rank) + ")" + m3u[0])
                print(m3u[1])
                rank += 1
            answer = "answer"
            if len(links) > 10:
                print(
                    "\nLe nombre de liens m3u correspondant à la recherche de "
                    "la chaine " + line[:-3] + " est de " + str(len(links)) + ". \n"
                )
                while answer.lower() not in answers:
                    answer = input(
                        "Il est possible de réduire le nombre de "
                        "chaines sélectionnées en filtrant uniquement "
                        "les informations des chaines qui comportent "
                        "'fr' pour France. Voulez-vous réduire la "
                        "sélection des liens m3u correspondant à la "
                        "chaine " + line[:-3] + "? Tapez directement "
                        "la touche entrée pour filtrer ou répondre par oui ou non: \n\n"
                    ).strip()
                if answer.lower() == "oui" or answer == "":
                    rank, rank_2 = 1, 1
                    for m3u in links:
                        if "fr" in m3u[0].lower():
                            print(str(rank_2) + ")" + m3u[0])
                            print(m3u[1])
                            ranking.append(rank)
                            rank_2 += 1
                        rank += 1
            if len(ranking) > 0:
                max_rank = len(ranking) + 1
            else:
                max_rank = rank
                if answer.lower() == "oui" or answer == "":
                    print(
                        "\nLe filtre n'a pas permis de sélectionner des chaines qui comportent "
                        "'fr' pour France. Veuillez choisir un lien dans la liste précédemment "
                        "affichée.\n"
                    )
            while select < 0 or select > max_rank - 1:
                select = input(
                    "Quel lien m3u voulez-vous choisir pour la "
                    "chaîne "
                    + line[:-3]
                    + '? (Tapez directement "Entré" pour le choix 1 '
                    "ou bien 0 si aucun lien m3u ne correspond à la chaîne): "
                ).strip()
                if select == "":
                    select = 1
                try:
                    select = int(select)
                except ValueError:
                    select = -1
                    pass
            if len(ranking) > 0:
                # protect against index error
                if 0 < select <= len(ranking):
                    select = ranking[select - 1]
                else:
                    select = 0
            if select == 0:
                selected.append(line + "\n")
            elif crypted.lower() == "oui":
                try:
                    selected.append(line + links[select - 1][1])
                except Exception:
                    selected.append(line + "\n")
            else:
                try:
                    link = links[select - 1][1]
                    for part in splitted:
                        link = link.replace(part, "")
                    selected.append(line + link)
                except Exception:
                    selected.append(line + "\n")
        else:
            selected.append(line + "\n")

    providers_dir = Path.home() / ".config" / "iptvselect-fr" / "iptv_providers"
    _ensure_dir_secure(providers_dir, mode=0o700)

    if crypted.lower() == "oui":
        out_path = providers_dir / f"{iptv_provider}.ini"
        try:
            with out_path.open("w", encoding="utf-8", errors="ignore") as ini:
                ini.write("[CHANNELS]" + "\n")
                for line in selected:
                    ini.write(line)
            try:
                out_path.chmod(0o600)
            except Exception:
                logging.debug(f"Could not chmod {out_path}")

            # backup original m3u links copy
            src = out_path
            dest = providers_dir / f"{iptv_provider}_original_m3ulinks.ini"
            try:
                _safe_copy(src, dest)
            except Exception:
                logging.debug(f"Could not copy {src} to {dest}")
        except Exception as e:
            logging.error(f"Unable to write provider ini {out_path}: {e}")
    else:
        out_path = providers_dir / f"{iptv_provider}_original.ini"
        try:
            with out_path.open("w", encoding="utf-8", errors="ignore") as ini:
                ini.write("[CHANNELS]" + "\n")
                for line in selected:
                    ini.write(line)
            try:
                out_path.chmod(0o600)
            except Exception:
                logging.debug(f"Could not chmod {out_path}")
        except Exception as e:
            logging.error(f"Unable to write provider ini {out_path}: {e}")

    print(
        "\nBravo !!! Vous avez configuré un fichier de liens m3u de plus de 200 chaines! :-)\n"
    )
