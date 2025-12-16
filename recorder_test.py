import os
import signal
import subprocess
import time
import re
import getpass

from configparser import ConfigParser
from pathlib import Path

user = getpass.getuser()

config_iptv_select = ConfigParser(interpolation=None)
config_iptv_select.read(f"/home/{user}/.config/iptvselect-fr/iptv_select_conf.ini")

home_dir = os.path.expanduser("~")
target_dir = os.path.join(home_dir, "videos_select")

if not os.path.isdir(target_dir):
    try:
        os.makedirs(target_dir, exist_ok=True)
        print("Le dossier videos_select a été créé dans votre dossier home.\n")
    except Exception:
        print("Impossible de créer le dossier videos_select.")
        exit()
else:
    print("Le dossier videos_select existe déjà.\n")

recorders = ["ffmpeg", "vlc", "mplayer", "streamlink"]
answers = [1, 2, 3, 4]
recorder = 666

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

if not re.fullmatch(r"[A-Za-z0-9_\-]+", iptv_provider):
    print("Nom de fournisseur IPTV invalide.")
    exit()

config_iptv_provider = ConfigParser(interpolation=None)
config_iptv_provider.read(
    f"/home/{user}/.config/iptvselect-fr/iptv_providers/{iptv_provider}.ini"
)

m3u8_link = ""

while m3u8_link == "":
    channel = input(
        "\nQuel est le nom de la chaine de votre fournisseur iptv pour "
        "laquelle vous souhaitez tester l'application? (la chaîne renseignée doit "
        "correspondre exactement à la chaîne renseignée dans le fichier de configuration.)\n"
    )

    if "\x00" in channel:  # NULL byte attack prevention
        print("Nom de chaîne invalide (caractère interdit détecté).")
        exit()

    channel = channel.strip()

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

    if not m3u8_link.startswith(("http://", "https://", "rtsp://")):
        print("Le lien m3u8/rtsp du fichier .ini semble invalide.")
        exit()

    if len(m3u8_link) > 2000:
        print("URL IPTV trop longue, potentiellement dangereuse.")
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

safe_title = re.sub(r"[^A-Za-z0-9._-]", "_", title)

home = Path.home()
videos_dir = home / "videos_select"
logs_dir = home / ".local/share/iptvselect-fr/logs"

videos_dir.mkdir(exist_ok=True, parents=True)
logs_dir.mkdir(exist_ok=True, parents=True)

output_path = videos_dir / f"{safe_title}_{recorders[recorder-1]}.ts"
log_path = logs_dir / f"infos_{recorders[recorder-1]}.log"

if recorder == 1:
    cmd = [
        "ffmpeg", "-y", "-i", m3u8_link,
        "-map", "0:v", "-map", "0:a", "-map", "0:s?",
        "-c:v", "copy", "-c:a", "copy", "-c:s", "copy",
        "-t", str(duration),
        "-f", "mpegts",
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "1",
        "-reconnect_at_eof", "-y",
        str(output_path)
    ]

elif recorder == 2:
    cmd = [
        "vlc", "-vvv", m3u8_link,
        "--run-time", str(duration),
        f"--sout=file/ts:{output_path}"
    ]

elif recorder == 3:
    cmd = [
        "mplayer", m3u8_link,
        "-dumpstream",
        "-dumpfile", str(output_path)
    ]

else:
    cmd = [
        str(home / ".local/share/iptvselect-fr/.venv/bin/streamlink"),
        "--ffmpeg-validation-timeout", "15.0",
        "--http-no-ssl-verify",
        # "--hls-live-restart",
        "--stream-segment-attempts", "100",
        "--retry-streams", "1",
        "--retry-max", "100",
        "--stream-segmented-duration", str(duration),
        "-o", str(output_path),
        m3u8_link,
        "best"
    ]

print("\nLa commande lancée est:\n")
print(" ".join(cmd))

print(
    "\nVous pourrez retrouver le fichier vidéo dans le dossier videos_select "
    "qui est lui-même situé dans votre dossier home\n"
)
print(
    f"Les logs se trouvent dans {log_path}\n"
)

with open(log_path, "w") as log_file:
    test_record = subprocess.Popen(
        cmd, stdout=log_file, stderr=subprocess.STDOUT
    )

try:
    test_record.wait(timeout=duration + 30)
except subprocess.TimeoutExpired:
    print("Processus trop long, arrêt forcé.")
    try:
        test_record.kill()
    except Exception:
        pass

if 2 <= recorder <= 3:
    try:
        os.kill(test_record.pid, signal.SIGTERM)
    except Exception:
        pass

quit()
