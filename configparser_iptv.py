#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import getpass
import logging
import os
import re
import stat
import sys
from configparser import ConfigParser
from pathlib import Path

# --- Configuration for paths and permissions ---
HOME = Path.home()
BASE_CONFIG_DIR = HOME / ".config" / "iptvselect-fr"
PROVIDERS_DIR = BASE_CONFIG_DIR / "iptv_providers"
LOG_DIR = HOME / ".local" / "share" / "iptvselect-fr" / "logs"
LOG_FILE = LOG_DIR / "configparser.log"
CONF_FILE = BASE_CONFIG_DIR / "iptv_select_conf.ini"

# Ensure directories exist with conservative permissions (owner rwx only)
def ensure_dir(path: Path, mode: int = 0o700) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True, mode=mode)
        # Some systems ignore mode on exist_ok; force it
        path.chmod(mode)
    except Exception:
        print(f"Impossible de créer ou configurer le répertoire : {path}")
        sys.exit(1)


ensure_dir(LOG_DIR, mode=0o700)
ensure_dir(PROVIDERS_DIR, mode=0o700)
ensure_dir(BASE_CONFIG_DIR, mode=0o700)

logging.basicConfig(
    filename=str(LOG_FILE),
    format="%(asctime)s %(levelname)s: %(message)s",
    level=logging.INFO,
    filemode="a",
)

try:
    user = getpass.getuser()
except Exception:
    user = os.environ.get("USER", "")
    if not user:
        user = "unknown"

config_object = ConfigParser()

print(
    "Ce programme permet de configurer le fichier iptv_select_conf.ini. "
    "Ce fichier comporte les informations nécessaires pour définir les "
    "fournisseurs d'IPTV pour enregistrer les vidéos ainsi que les secours "
    "au cas où un enregistrement s'arrête inopinément (ce qui est le cas "
    "pour les fournisseurs d'IPTV dont les serveurs ne sont pas stables). "
    "L'enregistrement de sauvegardes "
    "permettra de fournir la partie de la vidéo manquante entre l'arrêt et "
    "le redémarrage de la commande d'enregistrement du flux IPTV. \n"
    "Il est donc conseillé d'avoir au moins une ligne supplémentaire pour chaque "
    "enregistrement afin d'éviter d'éventuels coupures des vidéos. "
    "Vous pouvez ajouter jusqu'à 4 fournisseurs d'IPTV (pour enregistrer "
    "des vidéos diffusés en même temps) et 8 sauvegardes (c'est à dire "
    "2 backups par enregistrement). "
    "Les fournisseurs d'IPTV peuvent êtres identiques s'il "
    "vous permettent d'enregistrer des vidéos simultanéments (cela dépend "
    "de la souscription pour les fournisseurs payants mais cela n'est "
    "généralement pas limité pour les fournisseurs d'IPTV gratuits) mais si "
    "le serveur d'un fournisseur ne fonctionne plus, un fournisseur d'IPTV "
    "différent pour les secours permettra de continuer l'enregistrement de la sauvegarde. \n"
    "Lors de la sélection des chaines pour vos recherches dans iptv-select.fr, "
    "il faudra veiller à ce que les fournisseurs d'IPTV pour l'enregistrement "
    "et les secours fournissent les mêmes chaînes pour permettre la sauvegarde.\n"
)

answers = ["oui", "non"]
answer = "maybe"

while answer.lower() not in answers:
    answer = input(
        "Voulez-vous configurer le fichier iptv_select_conf.ini? (répondre par oui ou non) "
    )

if answer.lower() == "non":
    sys.exit(0)

record_ranking = ["première", "deuxième", "troisième", "quatrième"]
provider_rank = 0
answers_apps = [1, 2, 3, 4]
recorders = ["ffmpeg", "vlc", "mplayer", "streamlink"]
provider_recorder = 666
backup_recorder = 666

# Allowed provider name pattern: letters, digits, dot, underscore, hyphen
VALID_PROVIDER_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def sanitize_provider_name(name: str) -> str:
    """Return stripped name if allowed, else empty string."""
    if not name:
        return ""
    name = name.strip()
    # Reject any path components or traversal attempts
    if "/" in name or "\\" in name or ".." in name:
        return ""
    if not VALID_PROVIDER_RE.match(name):
        return ""
    return name


def provider_path_from_name(name: str) -> Path:
    """Return resolved provider path and ensure it's under PROVIDERS_DIR."""
    candidate = (PROVIDERS_DIR / f"{name}.ini").expanduser()
    try:
        # Resolve to the real absolute path
        resolved = candidate.resolve(strict=False)
    except Exception:
        # If resolve fails for some reason, return non-existent candidate
        resolved = candidate.absolute()
    # Ensure resolved path is a child of PROVIDERS_DIR (prevents symlink escape)
    try:
        prov_resolved = PROVIDERS_DIR.resolve(strict=True)
    except Exception:
        prov_resolved = PROVIDERS_DIR.absolute()
    # Compare common paths
    try:
        if os.path.commonpath([str(resolved), str(prov_resolved)]) != str(prov_resolved):
            return Path()  # invalid/escape attempt
    except Exception:
        return Path()
    return resolved


while True:
    while True:
        iptv_provider = input(
            "\nQuel est le fournisseur d'IPTV pour lequel vous souhaitez "
            f"enregistrer la {record_ranking[provider_rank]} vidéo parmi "
            "celles qui peuvent être enregistrées simultanément ? (Le nom "
            "renseigné doit correspondre au fichier de configuration du "
            "fournisseur se terminant par l'extension .ini et situé dans le dossier "
            "~/.config/iptvselect-fr/iptv_providers). Par exemple, si votre "
            "fichier de configuration est nommé moniptvquilestbon.ini, le nom "
            "de votre fournisseur à renseigner est moniptvquilestbon. "
            "\n"
        )

        sanitized = sanitize_provider_name(iptv_provider)
        if not sanitized:
            logging.error("Nom de fournisseur invalide ou contenant des caractères interdits.")
            print(
                "Nom invalide : utilisez uniquement lettres, chiffres, '.', '_' et '-'. "
                "Aucun séparateur de chemin ou '..' n'est autorisé."
            )
            continue

        provider_path = provider_path_from_name(sanitized)

        if provider_path and provider_path.exists() and provider_path.is_file():
            logging.info(f"Fichier trouvé : {provider_path}")
            # Keep the original variable for use later
            iptv_provider = sanitized
            break
        else:
            logging.error(f"Fichier non trouvé ou chemin invalide : {provider_path}")
            print(
                "Le fournisseur d'IPTV que vous avez renseigné ne correspond pas à un "
                "fichier de configuration se terminant par .ini dans le dossier "
                "iptv_providers."
            )

            continue_config = "maybe"
            while continue_config.lower() not in answers:
                continue_config = input(
                    "Souhaitez-vous saisir de nouveau un fournisseur d'IPTV ? "
                    "(répondre par oui ou non). Si vous répondez non, le programme fermera "
                    "pour vous laisser vérifier le nommage de vos fichiers de configuration).\n"
                )
            if continue_config.lower() == "non":
                sys.exit(0)

    while provider_recorder not in answers_apps:
        try:
            provider_recorder = int(
                input(
                    "\nQuelle application souhaitez-vous utiliser pour "
                    "enregistrer les vidéos de ce fournisseur d'IPTV ?\n"
                    "(Vous pouvez utiliser le programme *recorder_test.py* "
                    "pour tester l'application la plus adaptée.)\n\n"
                    "1) FFmpeg\n2) VLC\n3) MPlayer\n4) Streamlink\n\n"
                    "Veuillez sélectionner une option entre 1 et 4 : "
                )
            )
        except ValueError:
            print("Vous devez sélectionner entre 1 et 4")

    backup_answer = "maybe"

    while backup_answer.lower() not in answers:
        backup_answer = input(
            "Voulez-vous ajouter un fournisseur pour la sauvegarde de ces "
            "enregistrements? (répondre par oui ou non) "
        )

    ls_result = ""
    backup_recorder_string = ""
    backup_2_recorder_string = ""

    while True:
        if backup_answer.lower() == "oui":
            iptv_backup = input(
                "\nQuel est le fournisseur d'IPTV pour lequel vous souhaitez "
                f"sauvegarder la {record_ranking[provider_rank]} vidéo parmis "
                "celle qui peuvent être enregistrée simultanément? (Le nom "
                "renseigné doit correspondre au fichier de configuration du "
                "fournisseur se terminant par l'extension.ini et situé dans "
                "le dossier iptv_providers). Par exemple, si votre fichier de "
                "configuration est nommé moniptvquilestbon.ini, le nom de votre "
                "fournisseur à renseigner est moniptvquilestbon.\n"
            )
            backup_2_ask = True
        else:
            iptv_backup = ""
            backup_2_ask = False
            break

        sanitized_bk = sanitize_provider_name(iptv_backup)
        if not sanitized_bk:
            logging.error("Nom de fournisseur de sauvegarde invalide.")
            print(
                "Nom invalide pour le fournisseur de sauvegarde : utilisez uniquement "
                "lettres, chiffres, '.', '_' et '-'."
            )
            # Ask user again or allow to exit
            continue_config = "maybe"
            while continue_config.lower() not in answers:
                continue_config = input(
                    "Souhaitez-vous saisir de nouveau un fournisseur d'IPTV? "
                    "(répondre par oui ou non). Si vous répondez non, le programme "
                    "fermera pour vous laissez vérifier le nommage de vos "
                    "fichiers de configuration).\n"
                )
            if continue_config.lower() == "non":
                sys.exit(0)
            else:
                continue

        provider_path = provider_path_from_name(sanitized_bk)

        if provider_path and provider_path.exists():
            ls_result = str(provider_path)
            logging.info(f"Fichier trouvé : {provider_path}")
        else:
            logging.error(f"File not found: {provider_path}")
            ls_result = ""

        expected = str(PROVIDERS_DIR / f"{sanitized_bk}.ini")
        if ls_result != expected:
            print(
                "Le fournisseur d'IPTV que vous avez renseigné pour la sauvegarde "
                "ne correspond pas à un fichier de configuration se terminant "
                "par .ini dans le dossier iptv_providers."
            )
            continue_config = "maybe"
            while continue_config.lower() not in answers:
                continue_config = input(
                    "Souhaitez-vous saisir de nouveau un fournisseur d'IPTV? "
                    "(répondre par oui ou non). Si vous répondez non, le programme "
                    "fermera pour vous laissez vérifier le nommage de vos fichiers "
                    "de configuration).\n"
                )
            if continue_config.lower() == "non":
                sys.exit(0)
            else:
                continue

        while backup_recorder not in answers_apps:
            try:
                backup_recorder = int(
                    input(
                        "\nQuelle application souhaitez-vous utiliser pour "
                        "enregistrer les vidéos de ce fournisseur d'IPTV ?\n"
                        "(Vous pouvez utiliser le programme *recorder_test.py* "
                        "pour tester l'application la plus adaptée.)\n\n"
                        "1) FFmpeg\n2) VLC\n3) MPlayer\n4) Streamlink\n\n"
                        "Veuillez sélectionner une option entre 1 et 4 : "
                    )
                )
                try:
                    backup_recorder_string = recorders[backup_recorder - 1]
                except IndexError:
                    print("Vous devez sélectionner un chiffre entre 1 et 4")
            except ValueError:
                print("Vous devez sélectionner un chiffre entre 1 et 4")
        break

    backup_2_answer = "maybe"

    if backup_2_ask:
        while backup_2_answer.lower() not in answers:
            backup_2_answer = input(
                "Voulez-vous ajouter un 3ème fournisseur d'IPTV (au cas où "
                "celui pour l'enregistrement et la 1ère sauvegarde serait en échec) pour "
                "la sauvegarde de ces enregistrements? (répondre par oui ou non) "
            )
    else:
        backup_2_answer = "non"

    while True:
        if backup_2_answer.lower() == "oui":
            iptv_backup_2 = input(
                "\nQuel est le fournisseur d'IPTV pour lequel vous souhaitez "
                f"réaliser la deuxième sauvegarde de la {record_ranking[provider_rank]} "
                "vidéo parmis celle qui peuvent être enregistrée simultanément? "
                "(Le nom renseigné doit correspondre au fichier de configuration "
                "du fournisseur se terminant par l'extension.ini et situé dans le "
                "dossier iptv_providers). Par exemple, si votre fichier de configuration "
                "est nommé moniptvquilestbon.ini, le nom de votre fournisseur à renseigner "
                "est moniptvquilestbon.\n"
            )
        else:
            iptv_backup_2 = ""
            backup_2_recorder_string = ""
            break

        sanitized_bk2 = sanitize_provider_name(iptv_backup_2)
        if not sanitized_bk2:
            logging.error("Nom de fournisseur de 2ème sauvegarde invalide.")
            print(
                "Nom invalide pour le fournisseur de 2ème sauvegarde : utilisez uniquement "
                "lettres, chiffres, '.', '_' et '-'."
            )
            continue_config = "maybe"
            while continue_config.lower() not in answers:
                continue_config = input(
                    "Souhaitez-vous saisir de nouveau un fournisseur d'IPTV? "
                    "(répondre par oui ou non). Si vous répondez non, le programme fermera "
                    "pour vous laissez vérifier le nommage de vos fichiers de configuration). \n"
                )
            if continue_config.lower() == "non":
                sys.exit(0)
            else:
                continue

        provider_path = provider_path_from_name(sanitized_bk2)

        if provider_path and provider_path.exists():
            ls_result = str(provider_path)
            logging.info(f"Fichier trouvé : {provider_path}")
        else:
            ls_result = ""
            logging.error(f"Fichier non trouvé : {provider_path}")

        expected = str(PROVIDERS_DIR / f"{sanitized_bk2}.ini")
        if ls_result != expected:
            print(
                "Le fournisseur d'IPTV que vous avez renseigné pour la 2ème sauvegarde "
                "ne correspond pas à un fichier de configuration se terminant "
                "pas .ini dans le dossier iptv_providers."
            )
            continue_config = "maybe"
            while continue_config.lower() not in answers:
                continue_config = input(
                    "Souhaitez-vous saisir de nouveau un fournisseur d'IPTV? "
                    "(répondre par oui ou non). Si vous répondez non, le programme fermera "
                    "pour vous laissez vérifier le nommage de vos fichiers de configuration). \n"
                )
            if continue_config.lower() == "non":
                sys.exit(0)
            else:
                continue

        backup_recorder = 666

        while backup_recorder not in answers_apps:
            try:
                backup_recorder = int(
                    input(
                        "\nQuelle application souhaitez-vous utiliser pour "
                        "enregistrer les vidéos de ce fournisseur d'IPTV ?\n"
                        "(Vous pouvez utiliser le programme *recorder_test.py* "
                        "pour tester l'application la plus adaptée.)\n\n"
                        "1) FFmpeg\n2) VLC\n3) MPlayer\n4) Streamlink\n\n"
                        "Veuillez sélectionner une option entre 1 et 4 : "
                    )
                )
                try:
                    backup_2_recorder_string = recorders[backup_recorder - 1]
                except IndexError:
                    print("Vous devez sélectionner un chiffre entre 1 et 4")
            except ValueError:
                print("Vous devez sélectionner un chiffre entre 1 et 4")
        break

    backup_recorder = 666

    provider_rank += 1

    config_object["PROVIDER_" + str(provider_rank)] = {
        "iptv_provider": iptv_provider,
        "provider_recorder": recorders[provider_recorder - 1],
        "iptv_backup": iptv_backup,
        "backup_recorder": backup_recorder_string,
        "iptv_backup_2": iptv_backup_2,
        "backup_2_recorder": backup_2_recorder_string,
    }

    provider_recorder = 666

    if provider_rank < 4:
        answer = "maybe"
        while answer.lower() not in answers:
            answer = input(
                "\nVoulez-vous configurer un autre fournisseur d'IPTV? "
                "(pour enregistrer simultanément une autre vidéo). "
                "Répondre par oui ou non: "
            )
        if answer.lower() == "non":
            while provider_rank < 4:
                provider_rank += 1
                config_object["PROVIDER_" + str(provider_rank)] = {
                    "iptv_provider": "",
                    "provider_recorder": "",
                    "iptv_backup": "",
                    "backup_recorder": "",
                    "iptv_backup_2": "",
                    "backup_2_recorder": "",
                }
            break
    else:
        print("Vous avez configuré le nombre maximal de fournisseur d'IPTV.")
        break

try:
    with CONF_FILE.open("w", encoding="utf-8") as conf:
        config_object.write(conf)
    CONF_FILE.chmod(0o600)
    logging.info(f"Fichier de configuration écrit : {CONF_FILE}")
except Exception as e:
    logging.error(f"Erreur lors de l'écriture du fichier de configuration : {e}")
    print("Impossible d'écrire le fichier de configuration. Vérifiez les permissions.")
    sys.exit(1)
