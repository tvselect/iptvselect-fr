import argparse
import re
import subprocess
import os

parser = argparse.ArgumentParser()
parser.add_argument("iptv_provider")
parser.add_argument("encrypted", nargs="?")

args = parser.parse_args()

iptv_provider = args.iptv_provider

user = os.environ.get("USER")

try:
    with open(
        "/home/" + user + "/.config/iptvselect-fr/iptv_providers/" + iptv_provider + ".ini",
        "r",
    ) as ini:
        first_line = ini.readline()
        lines_ini = ini.read().splitlines()
except FileNotFoundError:
    print(
        "Le fichier {iptv_provider}.ini n'est pas présent dans le dossier "
        "~/.config/iptvselect-fr/iptv_providers. Veuillez créer ce fichier en exécutant le "
        "script install_iptv.py .".format(iptv_provider=args.iptv_provider)
    )
    exit()

encrypt = 0
not_encrypt = 0

for line in lines_ini[:-1]:
    try:
        m3u_link = line.split(" = ")[1]
    except IndexError:
        print(
            "Le fichier {iptv_provider}.ini n'est pas configurer "
            "correctement. Veuillez créer de nouveau ce fichier "
            "en exécutant le script install_iptv.py (si les liens "
            "m3u ne sont pas chiffrés) ou fill_ini.py (si les liens "
            "m3u sont chiffrés).".format(iptv_provider=args.iptv_provider)
        )
        exit()
    part_link = re.findall(".*\/", m3u_link)
    if len(part_link) > 0:
        part1 = part_link[0]
        left = m3u_link.replace(part1, "")
        if left.isdigit():
            part2 = ""
        else:
            try:
                part2 = re.findall("\..*", left)[0]
            except IndexError:
                part2 = ""
        channel_id = m3u_link.replace(part1, "")
        channel_id = channel_id.replace(part2, "")
        if channel_id[-1] == "\n":
            channel_id = channel_id[:-1]
        if channel_id.isdigit():
            not_encrypt += 1
        else:
            encrypt += 1

numbers = ["1", "2", "3"]
answer = "nono"

if encrypt == 0 and not_encrypt > 0:
    print("Les liens m3u ne sont pas chiffrés.")
    crypt = False
elif not_encrypt == 0 and encrypt > 0:
    print("Les liens m3u sont chiffrés.")
    crypt = True
elif encrypt != 0 and not_encrypt != 0:
    print(
        "Des liens m3u chiffrés et non chiffrés apparaissent dans le "
        "fichier {iptv_provider}.ini . {encrypt} liens m3u apparaissent "
        "comme étant chiffrés et {not_encrypt} liens m3u apparaissent "
        "comme n'étant pas chiffrés.\n".format(
            iptv_provider=args.iptv_provider, encrypt=encrypt, not_encrypt=not_encrypt
        )
    )
    while answer not in numbers:
        answer = input(
            "Choisissez une des options suivante (répondre 1, 2 ou 3):\n\n"
            "1)Considérer tous les liens comme étant non chiffrés.\n"
            "2)Considérer tous les liens comme étant chiffrés.\n"
            "3)sortir du programme et vérifier par vous même l'intégrité "
            "fichier.\n"
        )

if answer == "1":
    crypt = False
elif answer == "2":
    crypt = True
elif answer == "3":
    exit()

answers = ["oui", "non"]

if not crypt or args.encrypted == "not_encrypted":
    try:
        with open(
            "/home/"
            + user
            + "/.config/iptvselect-fr/iptv_providers/"
            + iptv_provider
            + "_original.ini",
            "r",
        ) as ini:
            first_line = ini.readline()
            lines_original = ini.read().splitlines()
    except FileNotFoundError:
        print(
            "Le fichier {iptv_provider}_original.ini n'est pas présent "
            "dans le dossier ~/.config/iptvselect-fr/iptv_providers. "
            "Veuillez créer ce fichier en exécutant le "
            "script fill_ini.py ou alors en le "
            "créant manuellement.".format(iptv_provider=args.iptv_provider)
        )
        exit()

    while answer.lower() not in answers:
        answer = input(
            "Voulez-vous modifier le fichier {iptv_provider}"
            "_original.ini ?(répondre par oui ou non): ".format(
                iptv_provider=args.iptv_provider
            )
        )

    if answer.lower() == "oui":
        modify = "oui"
        chan_to_modify = []
        while modify == "oui":
            match = False

            while not match:
                channel = input(
                    "\nQuel est le nom de la chaine dont vous voulez modifier "
                    "l'identifiant? (remarque: le nom doit exactement "
                    "correspondre au nom d'une chaine présente dans iptv-select.fr): "
                )
                for line in lines_original:
                    try:
                        chan_id = line.split(" = ")
                        chan = chan_id[0]
                        id = chan_id[1]
                    except IndexError:
                        print(
                            "Le fichier {iptv_provider}_original.ini n'est pas configuré "
                            "correctement. Veuillez créer de nouveau ce fichier "
                            "en exécutant le script fill_ini.py .".format(
                                iptv_provider=args.iptv_provider
                            )
                        )
                        exit()
                    if chan.lower() == channel.lower():
                        match = True
                        break
                if not match:
                    print(
                        "\nAucune chaine ne correspond au nom {channel} dans le fichier "
                        "{iptv_provider}_original.ini".format(
                            channel=channel, iptv_provider=iptv_provider
                        )
                    )

            if id != "":
                print(
                    "\nL'identifiant de la chaine {channel} est {id}.".format(
                        channel=channel, id=id
                    )
                )
            else:
                print(
                    "\nLa chaine {channel} n'a pas d'identifiant enregistré.".format(
                        channel=channel
                    )
                )

            new_id = "number"

            while not new_id.isdigit():
                new_id = input(
                    "\nQuel le nouvel identifiant de la chaine? (saisir uniquement des chiffres): "
                )
            chan_to_modify.append((chan, new_id))

            modify = "nono"

            while modify not in answers:
                modify = input(
                    "\nVoulez-vous modifier l'identifiant d'une autre chaine? (répondre par oui ou non): "
                )

        with open(
            "/home/"
            + user
            + "/.config/iptvselect-fr/iptv_providers/"
            + iptv_provider
            + "_original.ini",
            "w",
        ) as ini:
            ini.write("[CHANNELS]" + "\n")
            for line in lines_original:
                modified = False
                chan_id = line.split(" = ")
                for chan in chan_to_modify[::-1]:
                    if chan[0].lower() == chan_id[0].lower():
                        ini.write(chan_id[0] + " = " + chan[1] + "\n")
                        modified = True
                        break
                if not modified:
                    ini.write(line + "\n")

        print(
            "\nLe fichier {iptv_provider}_original.ini a été modifié. Les liens "
            "m3u n'étant pas chiffrés, il vous faut maintenant lancer le script "
            "install_iptv.py avec la commande python3 install_iptv.py \n"
            "Ceci vous permettra de synchroniser les fichiers {iptv_provider}.ini "
            "et {iptv_provider}_original_m3ulinks.ini avec le fichier "
            "{iptv_provider}_original.ini".format(iptv_provider=iptv_provider)
        )

elif crypt or args.encrypted == "encrypted":
    try:
        with open(
            "/home/"
            + user
            + "/.config/iptvselect-fr/iptv_providers/"
            + iptv_provider
            + "_original_m3ulinks.ini",
            "r",
        ) as ini:
            first_line = ini.readline()
            lines_original = ini.read().splitlines()
    except FileNotFoundError:
        print(
            "Le fichier {iptv_provider}_original_m3ulinks.ini n'est "
            "pas présent dans le dossier ~/.config/iptvselect-fr/iptv_providers. "
            "Veuillez créer ce fichier en exécutant le "
            "script fill_ini.py .".format(iptv_provider=args.iptv_provider)
        )
        exit()

    try:
        with open(
            "/home/"
            + user
            + "/.config/iptvselect-fr/iptv_providers/"
            + iptv_provider
            + ".ini",
            "r",
        ) as ini:
            first_line = ini.readline()
            lines = ini.read().splitlines()
    except FileNotFoundError:
        print(
            "Le fichier {iptv_provider}.ini n'est pas présent dans "
            "le dossier ~/.config/iptvselect-fr/iptv_providers. "
            "Veuillez créer ce fichier en exécutant le "
            "script fill_ini.py.".format(iptv_provider=args.iptv_provider)
        )
        exit()

    while answer.lower() not in answers:
        answer = input(
            "Voulez-vous modifier les fichiers {iptv_provider}"
            "_original_m3ulinks.ini et {iptv_provider}.ini ?"
            "(répondre par oui ou non): ".format(iptv_provider=args.iptv_provider)
        )

    if answer.lower() == "oui":
        modify = "oui"
        chan_to_modify = []
        while modify == "oui":
            match = False

            while not match:
                channel = input(
                    "\nQuel est le nom de la chaine dont vous voulez modifier "
                    "l'identifiant? (remarque: le nom doit exactement "
                    "correspondre au nom d'un chaine présente dans iptv-select.fr).: "
                )
                for line in lines_original:
                    try:
                        chan_url = line.split(" = ")
                        chan = chan_url[0]
                        url = chan_url[1]
                    except IndexError:
                        print(
                            "Le fichier {iptv_provider}_original.ini n'est pas configuré "
                            "correctement. Veuillez créer de nouveau ce fichier "
                            "en exécutant le script fill_ini.py .".format(
                                iptv_provider=args.iptv_provider
                            )
                        )
                        exit()
                    if chan.lower() == channel.lower():
                        match = True
                        break
                if not match:
                    print(
                        "\nAucune chaine ne correspond au nom {channel} dans le fichier "
                        "{iptv_provider}_original_m3ulinks.ini".format(
                            channel=channel, iptv_provider=iptv_provider
                        )
                    )

            if url != "":
                print(
                    "\nL'url de lien m3u de la chaine {channel} est {url}.".format(
                        channel=channel, url=url
                    )
                )
            else:
                print(
                    "\nLa chaine {channel} n'a pas d'url enregistré.".format(
                        channel=channel
                    )
                )

            new_url = input("\nQuelle est la nouvelle url du lien m3u de la chaine?: ")
            chan_to_modify.append((chan, new_url))

            modify = "nono"

            while modify not in answers:
                modify = input(
                    "\nVoulez-vous modifier l'url d'une autre chaine? (répondre par oui ou non): "
                )

        with open(
            "/home/"
            + user
            + "/.config/iptvselect-fr/iptv_providers/"
            + iptv_provider
            + "_original_m3ulinks.ini",
            "w",
        ) as ini:
            ini.write("[CHANNELS]" + "\n")
            for line in lines_original:
                modified = False
                chan_url = line.split(" = ")
                for chan in chan_to_modify[::-1]:
                    if chan[0].lower() == chan_url[0].lower():
                        ini.write(chan_url[0] + " = " + chan[1] + "\n")
                        modified = True
                        break
                if not modified:
                    ini.write(line + "\n")

        with open(
            "/home/"
            + user
            + "/.config/iptvselect-fr/iptv_providers/"
            + iptv_provider
            + ".ini",
            "w",
        ) as ini:
            ini.write("[CHANNELS]" + "\n")
            for line in lines:
                modified = False
                chan_url = line.split(" = ")
                for chan in chan_to_modify[::-1]:
                    if chan[0].lower() == chan_url[0].lower():
                        ini.write(chan_url[0] + " = " + chan[1] + "\n")
                        modified = True
                        break
                if not modified:
                    ini.write(line + "\n")

        print(
            "\nLes fichiers {iptv_provider}_original_m3ulinks.ini et "
            "{iptv_provider}.ini ont été modifiés.".format(iptv_provider=iptv_provider)
        )
