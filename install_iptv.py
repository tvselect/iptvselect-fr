import re
import subprocess
import readline
import shlex
import os

from configparser import ConfigParser

from fill_ini import channels, search_url

user = os.environ.get("USER")

print("Configuration des fournisseurs d'IPTV:\n")

print(
    "L'enregistrement de flux IPTV nécessite au minimum un lien m3u8 vers la source du flux. Afin "
    "de faciliter l'organisation des liens m3u8, ceux-ci sont regroupés par fournisseurs dans des "
    "fichiers .ini afin d'éviter de déclencher des enregistrements de flux IPTV pour lesquels vous "
    "n'avez pas souscrits plusieurs lignes simultanés.\n"
    "Un lien m3u8 est composé d'une URL avec un numéro qui permet d'identifier la "
    "chaîne du flux ainsi qu'un identifiant et d'un mot de passe pour les fournisseurs d'IPTV payants."
)

print(
    "Ce programme d'installation permet d'ajouter les liens m3u8 dans un fichier de configuration .ini "
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
    )

lines = []

try:
    with open("/home/" + user + "/.local/share/iptvselect-fr/urls.txt") as file:
        lines = file.read().splitlines()
except FileNotFoundError:
    pass

url_provider = ""

if len(lines) > 0:
    for line in lines[::-1]:
        if iptv_provider in line:
            url_provider = line.replace(re.findall(".*: ", line)[0], "")
            break

manual, manual_crypt, manual_url, automate = "nono", "nono", "nono", "nono"
answers = ["oui", "non", ""]

if url_provider != "":
    print(
        "Le programme a détecter l'url suivante qui provient d'une "
        "précédente analyse du fichier m3u de votre fournisseur "
        "d'IPTV {iptv_provider}:\n\n".format(iptv_provider=iptv_provider) + url_provider
    )
    while manual.lower() not in answers:
        manual = input(
            "\nVoulez-vous utiliser ce lien URL pour construire le fichier de "
            "configuration .ini? (répondre par oui ou non): \n"
        )

if manual == "non" or url_provider == "":
    url_provider = ""
    while "channel_id" not in url_provider:
        while automate not in answers:
            automate = input(
                "\nVoulez-vous lancer une recherche automatique du "
                "lien url à partir du fichier m3u de votre founisseur "
                "d'IPTV? (répondre par oui ou non). Remarque: La "
                "recherche peut durer de nombreuses minutes si "
                "votre fichier m3u est volumineux: \n"
            )
        if automate.lower() == "oui" or automate.lower() == "":
            m3u_file = "123456"
            ls_result = "abcdef"
            while ls_result != (
                "/home/" + user + "/.config/iptvselect-fr/"
                "iptv_providers/" + m3u_file + ".m3u"
            ):
                m3u_file = input(
                    "Quel est le nom du fichier m3u de votre "
                    "fournisseur d'IPTV? (renseignez le nom "
                    "sans l'extension .m3u): "
                )
                cmd = ("ls ~/.config/iptvselect-fr/iptv_providers/{m3u_file}.m3u").format(
                    m3u_file=shlex.quote(m3u_file)
                )
                output = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
                )
                stdout, stderr = output.communicate()
                ls_result = stdout.decode("utf-8")[:-1]
                if ls_result != (
                    "/home/" + user + "/.config/iptvselect-fr/iptv"
                    "_providers/" + m3u_file + ".m3u"
                ):
                    print(
                        "Le fichier {m3u_file}.m3u n'est pas présent dans votre"
                        " dossier iptv_providers. Insérer le fichier m3u de "
                        " votre fournisseur d'IPTV ou modifier le nom du fichier "
                        "m3u pour qu'il corresponde à celui du fichier présent "
                        "dans le dossier.\n".format(m3u_file=m3u_file)
                    )

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
                    )
                if manual_crypt.lower() == "non":
                    exit()
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
                    )
                if manual_url == "non":
                    break

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
        )
        if "channel_id" not in url_provider:
            print(
                "\n************\n\n!!!!Attention!!!! Vous n'avez pas remplacé le numéro identifiant "
                "la chaine par le mot clé channel_id. Faites attention à bien remplacer seulement "
                "le numéro de la chaine dans le lien m3u car si vous remplacez une autre partie du "
                "lien, les enregistrements ne seront pas déclenchés.\n\n**************\n"
            )

cmd = (
    "ls /home/" + user + "/.config/iptvselect-fr/iptv_providers/{iptv_provider}.ini"
).format(iptv_provider=shlex.quote(iptv_provider))
output = subprocess.Popen(
    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
)
stdout, stderr = output.communicate()
ls_result = stdout.decode("ascii")[:-1]
print(ls_result)

if ls_result == (
    "/home/" + user + "/.config/iptvselect-fr/iptv_providers/" + iptv_provider + ".ini"
):
    cmd = (
        "cp /home/" + user + "/.config/iptvselect-fr/iptv_providers/"
        "{iptv_provider}.ini /home/" + user + "/.config/iptvselect-fr/iptv_"
        "providers/{iptv_provider}.ini.bak"
    ).format(iptv_provider=shlex.quote(iptv_provider))
    cp = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )

cmd = (
    "cp /home/" + user + "/.config/iptvselect-fr/iptv_providers"
    "/{iptv_provider}_original.ini /home/" + user + "/.config"
    "/iptvselect-fr/iptv_providers/{iptv_provider}.ini"
).format(iptv_provider=shlex.quote(iptv_provider))
cp = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
cp.wait()

config_file = (
    "/home/" + user + "/.config/iptvselect-fr/iptv_providers/" + iptv_provider + ".ini"
)
config_object = ConfigParser()
config_object.read(config_file)

try:
    for channel, channel_id in config_object["CHANNELS"].items():
        if channel_id != "":
            config_object["CHANNELS"][channel] = url_provider.replace(
                "channel_id", channel_id
            )
        else:
            config_object["CHANNELS"][channel] = ""
        with open(config_file, "w") as conf:
            config_object.write(conf)
except KeyError:
    print(
        "\nLe fichier de configuration n'est pas conforme ([CHANNELS] n'est pas présent "
        "au début du fichier) ou vous avez mal renseigné le nom de votre fournisseur "
        "iptv (si par exemple votre fichier de configuration est nommé moniptvquilestbon_original.ini, vous devez "
        "renseigner moniptvquilestbon dans le programme d'installation install_iptv.py)"
    )
    exit()

cmd = (
    "cp /home/" + user + "/.config/iptvselect-fr/iptv_providers"
    "/{iptv_provider}.ini /home/" + user + "/.config/iptvselect-fr"
    "/iptv_providers/{iptv_provider}_original_m3ulinks.ini"
).format(iptv_provider=shlex.quote(iptv_provider))
cp_ini = subprocess.Popen(
    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
)
cp_ini.wait()

print(
    "\nVotre fichier {iptv_provider}.ini est maintenant configuré avec les liens m3u de votre "
    "fournisseur d'IPTV.\n".format(iptv_provider=iptv_provider)
)
