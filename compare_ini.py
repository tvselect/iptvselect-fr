import argparse
import os
import sys
import errno
import re

parser = argparse.ArgumentParser()
parser.add_argument("original")
parser.add_argument("backup")
parser.add_argument("backup_2", nargs="?", default="no_backup_2")

args = parser.parse_args()

VALID_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
for name, value in (("original", args.original), ("backup", args.backup), ("backup_2", args.backup_2)):
    if value != "no_backup_2" and not VALID_NAME.match(value):
        print(
            f"Invalid provider name for {name}. Only letters, numbers, dot, dash and underscore are allowed."
        )
        sys.exit(1)

user = os.environ.get("USER")
if not user or "/" in user:
    print("Invalid or undefined USER environment variable.")
    sys.exit(1)

base_path = os.path.join("/home", user, ".config", "iptvselect-fr", "iptv_providers")

def safe_open(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as e:
        if e.errno == errno.ELOOP:
            print(f"Refusing to follow symlink: {path}")
            sys.exit(1)
        raise
    return os.fdopen(fd, "r", encoding="utf-8")


def ensure_owned_by_user(path):
    try:
        st = os.stat(path)
    except FileNotFoundError:
        return False
    if st.st_uid != os.getuid():
        print(f"Security error: {path} is not owned by the current user.")
        sys.exit(1)
    return True


original_path = os.path.join(base_path, f"{args.original}.ini")
if not ensure_owned_by_user(original_path):
    print(
        "Le fichier {original}.ini n'est pas présent dans le dossier "
        "~/.config/iptvselect-fr/iptv_providers. Veuillez créer ce "
        "fichier en exécutant les scripts fill_ini.py ou "
        "install_iptv.py ou alors en le créant manuellement.".format(
            original=args.original
        )
    )
    sys.exit(1)

try:
    with safe_open(original_path) as ini:
        first_line = ini.readline()
        lines_original = ini.read().splitlines()
except FileNotFoundError:
    print(
        "Le fichier {original}.ini n'est pas présent dans le dossier "
        "~/.config/iptvselect-fr/iptv_providers. Veuillez créer ce "
        "fichier en exécutant les scripts fill_ini.py ou "
        "install_iptv.py ou alors en le créant manuellement.".format(
            original=args.original
        )
    )
    sys.exit(1)

backup_path = os.path.join(base_path, f"{args.backup}.ini")
if not ensure_owned_by_user(backup_path):
    print(
        "Le fichier {backup}.ini n'est pas présent dans le dossier "
        "~/.config/iptvselect-fr/iptv_providers. Veuillez créer ce "
        "fichier en exécutant les scripts fill_ini.py ou "
        "install_iptv.py ou alors en le créant manuellement.".format(
            backup=args.backup
        )
    )
    sys.exit(1)

try:
    with safe_open(backup_path) as ini:
        first_line = ini.readline()
        lines_backup = ini.read().splitlines()
except FileNotFoundError:
    print(
        "Le fichier {backup}.ini n'est pas présent dans le dossier "
        "~/.config/iptvselect-fr/iptv_providers. Veuillez créer ce "
        "fichier en exécutant les scripts fill_ini.py ou "
        "install_iptv.py ou alors en le créant manuellement.".format(
            backup=args.backup
        )
    )
    sys.exit(1)

if args.backup_2 != "no_backup_2":
    backup_2_path = os.path.join(base_path, f"{args.backup_2}.ini")
    if not ensure_owned_by_user(backup_2_path):
        print(
            "Le fichier {backup_2}.ini n'est pas présent dans le dossier "
            "~/.config/iptvselect-fr/iptv_providers. Veuillez créer ce "
            "fichier en exécutant les scripts fill_ini.py ou "
            "install_iptv.py ou alors en le créant manuellement.".format(
                backup_2=args.backup_2
            )
        )
        sys.exit(1)

    try:
        with safe_open(backup_2_path) as ini:
            first_line = ini.readline()
            lines_backup_2 = ini.read().splitlines()
    except FileNotFoundError:
        print(
            "Le fichier {backup_2}.ini n'est pas présent dans le dossier "
            "~/.config/iptvselect-fr/iptv_providers. Veuillez créer ce "
            "fichier en exécutant les scripts fill_ini.py ou "
            "install_iptv.py ou alors en le créant manuellement.".format(
                backup_2=args.backup_2
            )
        )
        sys.exit(1)

    lines_backup_2_broadcast = []

    for line in lines_backup_2:
        if " = " in line:
            split = line.split(" = ")
            if split[1] != "":
                lines_backup_2_broadcast.append(split[0])

    lines_backup_2_broadcast = [chan.upper() for chan in lines_backup_2_broadcast]


lines_original_broadcast = []

for line in lines_original:
    if " = " in line:
        split = line.split(" = ")
        if split[1] != "":
            lines_original_broadcast.append(split[0])

lines_backup_broadcast = []

for line in lines_backup:
    if " = " in line:
        split = line.split(" = ")
        if split[1] != "":
            lines_backup_broadcast.append(split[0])

match = []

lines_original_broadcast = [chan.upper() for chan in lines_original_broadcast]
lines_backup_broadcast = [chan.upper() for chan in lines_backup_broadcast]

for channel in lines_original_broadcast:
    if channel in lines_backup_broadcast:
        match.append(channel)

if args.backup_2 != "no_backup_2":
    match_backup_2 = []
    for channel in match:
        if channel in lines_backup_2_broadcast:
            match_backup_2.append(channel)

    print(
        "Il y a {number} chaines pour lesquels les fournisseurs d'IPTV {original}, "
        "{backup} et {backup_2} diffusent tous les 3 parmis les chaines d'IPTV-select.fr. "
        "Voici la listes des chaines pour effectuer vos recherches dans "
        "le site web iptv-select.fr: \n".format(
            number=len(match_backup_2),
            original=args.original,
            backup=args.backup,
            backup_2=args.backup_2,
        )
    )

    for channel in match_backup_2:
        print(channel)

else:
    print(
        "Il y a {number} chaines pour lesquels les fournisseurs d'IPTV {original} et "
        "{backup} diffusent tous les 2 parmis les chaines d'IPTV-select.fr. "
        "Voici la listes des chaines pour effectuer vos recherches dans "
        "le site web iptv-select.fr: \n".format(
            number=len(match), original=args.original, backup=args.backup
        )
    )

    for channel in match:
        print(channel)
