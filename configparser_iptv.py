import subprocess
import readline
import shlex
import logging
import os

from configparser import ConfigParser

logging.basicConfig(
    filename=os.path.expanduser("~/.local/share/iptvselect-fr/logs/configparser.log"),
    format="%(asctime)s %(levelname)s: %(message)s",
    level=logging.INFO,
    filemode="a",
)

user = os.environ.get("USER")

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
    exit()

record_ranking = ["première", "deuxième", "troisième", "quatrième"]
provider_rank = 0
answers_apps = [1, 2, 3, 4]
recorders = ["ffmpeg", "vlc", "mplayer", "streamlink"]
provider_recorder = 5
backup_recorder = 5

while True:
    while True:
        iptv_provider = input(
            "\nQuel est le fournisseur d'IPTV pour lequel vous souhaitez "
            "enregistrer la {record_ranking} vidéo parmis celles qui peuvent être enregistrées "
            "simultanément? (Le nom renseigné doit correspondre au fichier de configuration du "
            "fournisseur se terminant par l'extension.ini et situé dans le dossier "
            "~/.config/iptvselect-fr/iptv_providers). Par exemple, si votre fichier de configuration "
            "est nommé moniptvquilestbon.ini, le nom de votre fournisseur à renseigner est moniptvquilestbon. "
            "\n".format(record_ranking=record_ranking[provider_rank])
        )

        cmd = "cd ~/.config/iptvselect-fr && ls iptv_providers/{iptv_provider}.ini".format(
            iptv_provider=shlex.quote(iptv_provider),
        )
        output = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        stdout, stderr = output.communicate()

        try:
            stderr_text = stderr.decode("utf-8")
        except UnicodeDecodeError:
            stderr_text = stderr.decode("latin1")

        try:
            ls_result = stdout.decode("utf-8").rstrip()
        except UnicodeDecodeError:
            ls_result = stdout.decode("latin1").rstrip()

        if stderr_text.strip() != "":
            logging.error(f"Command '{cmd}' failed with error: {stderr_text}")


        if ls_result != "iptv_providers/" + iptv_provider + ".ini":
            print(
                "Le fournisseur d'IPTV que vous avez renseigné ne correspond pas à un "
                "fichier de configuration se terminant pas .ini dans le dossier "
                "iptv_providers."
            )
            continue_config = "maybe"
            while continue_config.lower() not in answers:
                continue_config = input(
                    "Souhaitez-vous saisir de nouveau un fournisseur d'IPTV? "
                    "(répondre par oui ou non). Si vous répondez non, le programme fermera "
                    "pour vous laissez vérifier le nommage de vos fichiers de configuration).\n"
                )
            if continue_config.lower() == "non":
                exit()
        else:
            break

    while provider_recorder not in answers_apps:
        try:
            provider_recorder = int(
                input(
                    "\nQuelle application souhaitez-vous utiliser pour "
                    "enregistrer les vidéos de ce fournisseur d'IPTV? (vous pouvez utiliser "
                    "le programme recorder_test.py pour tester la meilleur application). \n"
                    "1) FFmpeg \n2) VLC\n3) Mplayer\n4) Streamlink\n"
                    "Sélectionnez 1, 2, 3 ou 4\n"
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

    while True:
        if backup_answer.lower() == "oui":
            iptv_backup = input(
                "\nQuel est le fournisseur d'IPTV pour lequel vous souhaitez "
                "sauvegarder la {record_ranking} vidéo parmis celle qui peuvent être enregistrée "
                "simultanément? (Le nom renseigné doit correspondre "
                " au fichier de configuration du fournisseur se terminant par l'extension.ini "
                "et situé dans le dossier iptv_providers). Par exemple, si votre fichier de configuration "
                "est nommé moniptvquilestbon.ini, le nom de votre fournisseur à renseigner est moniptvquilestbon. "
                "\n".format(record_ranking=record_ranking[provider_rank])
            )
            backup_2_ask = True
        else:
            iptv_backup = ""
            backup_recorder_string = ""
            backup_2_ask = False
            break

        cmd = "cd ~/.config/iptvselect-fr && ls iptv_providers/{iptv_backup}.ini".format(
            iptv_backup=shlex.quote(iptv_backup)
        )
        output = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        stdout, stderr = output.communicate()
        ls_result = stdout.decode("utf-8")[:-1]
        if stderr.decode("utf-8")[:-1] != "":
            logging.error(
                f"Command '{cmd}' failed with error: {stderr.decode('utf-8')}"
            )

        if ls_result != "iptv_providers/" + iptv_backup + ".ini":
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
                    "fermera pour vous laissez vérifier le nommage de vos fichiers de configuration). \n"
                )
            if continue_config.lower() == "non":
                exit()
            else:
                continue

        while backup_recorder not in answers_apps:
            try:
                backup_recorder = int(
                    input(
                        "\nQuelle application souhaitez-vous utiliser pour "
                        "enregistrer les vidéos de ce fournisseur d'IPTV? (vous pouvez utiliser "
                        "le programme recorder_test.py pour tester la meilleur application). \n"
                        "1) FFmpeg \n2) VLC\n3) Mplayer\n4) Streamlink\n"
                        "Sélectionnez 1, 2, 3 ou 4\n"
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
                "réaliser la deuxième sauvegarde de la {record_ranking} vidéo parmis celle qui "
                "peuvent être enregistrée simultanément? (Le nom renseigné doit correspondre "
                " au fichier de configuration du fournisseur se terminant par l'extension.ini "
                "et situé dans le dossier iptv_providers). Par exemple, si votre fichier de configuration "
                "est nommé moniptvquilestbon.ini, le nom de votre fournisseur à renseigner est moniptvquilestbon. "
                "\n".format(record_ranking=record_ranking[provider_rank])
            )
        else:
            iptv_backup_2 = ""
            backup_2_recorder_string = ""
            break

        cmd = "cd ~/.config/iptvselect-fr && ls iptv_providers/{iptv_backup_2}.ini".format(
            iptv_backup_2=shlex.quote(iptv_backup_2)
        )
        output = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        stdout, stderr = output.communicate()
        ls_result = stdout.decode("utf-8")[:-1]
        if stderr.decode("utf-8")[:-1] != "":
            logging.error(
                f"Command '{cmd}' failed with error: {stderr.decode('utf-8')}"
            )

        if ls_result != "iptv_providers/" + iptv_backup_2 + ".ini":
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
                exit()
            else:
                continue

        backup_recorder = 5

        while backup_recorder not in answers_apps:
            try:
                backup_recorder = int(
                    input(
                        "\nQuelle application souhaitez-vous utiliser pour "
                        "enregistrer les vidéos de ce fournisseur d'IPTV? (vous pouvez utiliser "
                        "le programme recorder_test.py pour tester la meilleur application). \n"
                        "1) FFmpeg \n2) VLC\n3) Mplayer\n4) Streamlink\n"
                        "Sélectionnez 1, 2, 3 ou 4\n"
                    )
                )
                try:
                    backup_2_recorder_string = recorders[backup_recorder - 1]
                except IndexError:
                    print("Vous devez sélectionner un chiffre entre 1 et 4")
            except ValueError:
                print("Vous devez sélectionner un chiffre entre 1 et 4")
        break

    backup_recorder = 5

    provider_rank += 1

    config_object["PROVIDER_" + str(provider_rank)] = {
        "iptv_provider": iptv_provider,
        "provider_recorder": recorders[provider_recorder - 1],
        "iptv_backup": iptv_backup,
        "backup_recorder": backup_recorder_string,
        "iptv_backup_2": iptv_backup_2,
        "backup_2_recorder": backup_2_recorder_string,
    }

    provider_recorder = 5

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

with open("/home/" + user + "/.config/iptvselect-fr/iptv_select_conf.ini", "w") as conf:
    config_object.write(conf)
