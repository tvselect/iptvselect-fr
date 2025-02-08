import subprocess
import time
import shlex
import os

from configparser import ConfigParser

user = os.environ.get("USER")

config_iptv_select = ConfigParser()
config_iptv_select.read("/home/" + user + "/.config/iptvselect-fr/iptv_select_conf.ini")


cmd = "ls ~ | grep ^videos_select$"
output = subprocess.Popen(
    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
)
stdout, stderr = output.communicate()
ls_directory = stdout.decode("utf-8")[:-1]

if ls_directory == "":
    cmd = "mkdir ~/videos_select"
    directory = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    directory.wait()
    print("Le dossier videos_select a été créé dans votre dossier home.\n")

recorders = ["ffmpeg", "vlc", "mplayer", "streamlink"]
answers = [1, 2, 3, 4]
recorder = 5

while recorder not in answers:
    try:
        recorder = int(
            input(
                "Quelle application souhaitez-vous tester?\n\n"
                "1) FFmpeg\n2) VLC\n3) Mplayer\n4) Streamlink\n"
                "Sélectionnez entre 1 et 4\n"
            )
        )
    except ValueError:
        print("Vous devez sélectionner entre 1 et 4")

iptv_provider = input(
    "\nQuel est le fournisseur d'IPTV pour lequel vous souhaitez "
    "tester l'application? (Le nom renseigné doit correspondre au fichier de "
    "configuration du fournisseur se terminant par l'extension.ini et situé dans "
    "le dossier iptv_providers). Par exemple, si votre fichier de configuration "
    "est nommé moniptvquilestbon.ini, le nom de votre fournisseur à renseigner est moniptvquilestbon,  \n"
)


config_iptv_provider = ConfigParser()
config_iptv_provider.read(
    "/home/" + user + "/.config/iptvselect-fr/iptv_providers/" + iptv_provider + ".ini"
)

m3u8_link = ""

while m3u8_link == "":
    channel = input(
        "\nQuel est le nom de la chaine de votre fournisseur iptv pour "
        "laquelle vous souhaitez tester l'application? (la chaîne renseignée doit "
        "correspondre exactement à la chaîne renseignée dans le fichier de configuration.)\n"
    )
    try:
        m3u8_link = config_iptv_provider["CHANNELS"][channel]
    except KeyError:
        print(
            "\nLe fichier de configuration n'est pas conforme ([CHANNELS] n'est pas présent "
            "au début du fichier) ou vous avez mal renseigné le nom de votre fournisseur "
            "iptv (si votre fichier de configuration est nommé moniptvquilestbon.ini, vous devez "
            "renseigner moniptvquilestbon dans le programme recorder_test.py). Cette erreur peut "
            "également se produire si vous n'avez pas saisi correctement la chaine (elle "
            " doit correspondre exactement à la chaine renseignée dans le fichier de "
            "configuration.) Vérifiez ces informations puis relancez le programme "
            "recorder_test.py.\n"
        )
        exit()
    if m3u8_link == "":
        print(
            "La chaine que vous avez renseignée ne comporte pas de lien m3u pour tester un "
            "enregistrement. Veuillez choisir une autre chaîne."
        )

try:
    duration = int(
        input("\nQuelle durée en secondes souhaitez-vous que dure l'enregistrement?\n")
    )
except ValueError:
    print(
        "La valeur fournie pour la durée doit être un nombre en secondes "
        "(exemple 3600 pour 1 heure). Merci de relancer le progamme"
    )
    exit()

title = input("\nQuel titre souhaitez-vous donner à votre vidéo de test?\n")

if recorder == 1:
    cmd = (
        "ffmpeg -y -i {m3u8_link} -map 0:v -map 0:a -map 0:s? -c:v copy "
        "-c:a copy -c:s copy -t {duration} "
        "-f mpegts -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 1"
        " -reconnect_at_eof -y /home/$USER/videos_select/"
        "{title}_ffmpeg.ts >> ~/.local/share/iptvselect-fr/logs/infos_ffmpeg.ts "
        "2>&1".format(m3u8_link=shlex.quote(m3u8_link), duration=duration, title=title)
    )
elif recorder == 2:
    cmd = (
        "vlc -vvv {m3u8_link} --run-time {duration} --sout=file/ts"
        ":/home/$USER/videos_select/{title}_vlc.ts "
        ">> ~/.local/share/iptvselect-fr/logs/infos_vlc.log 2>&1".format(
            m3u8_link=shlex.quote(m3u8_link), duration=duration, title=title
        )
    )
elif recorder == 3:
    cmd = (
        "mplayer {m3u8_link} -dumpstream -dumpfile "
        "/home/$USER/videos_select/{title}_mplayer.ts >> "
        "~/.local/share/iptvselect-fr/logs/infos_mplayer.log 2>&1".format(
            m3u8_link=shlex.quote(m3u8_link), title=title
        )
    )
else:
    cmd = (
        "streamlink --http-no-ssl-verify --hls-live-restart --stream-timeout 600 "
        "--hls-segment-threads 10 --hls-segment-timeout 10 --stream-segment-attempts 100 "
        "--retry-streams 1 --retry-max 100 --hls-duration 00:{duration} "
        "-o /home/$USER/videos_select/{title}_streamlink.ts {m3u8_link} best "
        ">> ~/.local/share/iptvselect-fr/logs/infos_streamlink.log 2>&1".format(
            m3u8_link=shlex.quote(m3u8_link), title=title, duration=duration
        )
    )

print("\nLa commande lancée est:\n")
print(cmd)
print(
    "\nVous pourrez retrouver le fichier vidéo dans le dossier videos_select "
    "qui est lui même situé dans votre dossier home\n"
)
print(
    "Si la vidéo n'est pas présente dans le dossier videos_select, c'est que "
    "celui-ci est en échec avec {application} pour ce fournisseur d'IPTV. Les "
    "logs pour débugger l'échec de l'enregistrement se trouvent dans le fichier "
    "~/.local/share/iptvselect-fr/logs/infos_{application}.log".format(
        application=recorders[recorder - 1]
    )
)

test_record = subprocess.Popen(
    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
)

if 2 <= recorder <= 3:
    time.sleep(duration)
    cmd = "ps -ef | grep {title} | tr -s ' ' " "| cut -d ' ' -f2 | head -n 2".format(
        title=title
    )
    pid_range = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    stdout, stderr = pid_range.communicate()
    pid = stdout.decode("utf-8").split("\n")[:-1][1]
    cmd = "kill {pid}".format(pid=pid)
    kill = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    quit()
