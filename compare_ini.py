import subprocess
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("original")
parser.add_argument("backup")
parser.add_argument("backup_2", nargs="?", default="no_backup_2")

args = parser.parse_args()

user = os.environ.get("USER")

try:
    with open(
        "/home/" + user + "/.config/iptvselect-fr/iptv_providers/"
        "{original}.ini".format(original=args.original),
        "r",
    ) as ini:
        first_line = ini.readline()
        lines_original = ini.read().splitlines()
except FileNotFoundError:
    print(
        "Le fichier {original}.ini n'est pas présent dans le dossier "
        "~/.config/iptvselect-fr/iptv_providers. Veuillez créer ce "
        "fichier en exécutant les scripts fill_ini.py ou "
        "install_iptv.py ou alors en le "
        "créant manuellement.".format(original=args.original)
    )
    exit()

try:
    with open(
        "/home/" + user + "/.config/iptvselect-fr/iptv_providers/"
        "{backup}.ini".format(backup=args.backup),
        "r",
    ) as ini:
        first_line = ini.readline()
        lines_backup = ini.read().splitlines()
except FileNotFoundError:
    print(
        "Le fichier {backup}.ini n'est pas présent dans le dossier "
        "~/.config/iptvselect-fr/iptv_providers. Veuillez créer ce "
        "fichier en exécutant les scripts fill_ini.py ou "
        "install_iptv.py ou alors en le créant "
        "manuellement.".format(backup=args.backup)
    )
    exit()

if args.backup_2 != "no_backup_2":
    try:
        with open(
            "/home/" + user + "/.config/iptvselect-fr/iptv_providers/"
            "{backup_2}.ini".format(backup_2=args.backup_2),
            "r",
        ) as ini:
            first_line = ini.readline()
            lines_backup_2 = ini.read().splitlines()
    except FileNotFoundError:
        print(
            "Le fichier {backup_2}.ini n'est pas présent dans le dossier "
            "~/.config/iptvselect-fr/iptv_providers. Veuillez créer ce "
            "fichier en exécutant les scripts fill_ini.py ou "
            "install_iptv.py ou alors en le créant "
            "manuellement.".format(backup_2=args.backup_2)
        )
        exit()

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
