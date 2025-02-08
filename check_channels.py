import subprocess
import argparse
import time
import shlex
import logging
import os

from datetime import datetime

user = os.environ.get("USER")

logging.basicConfig(
    filename=os.path.expanduser("~/.local/share/iptvselect-fr/logs/check_channels.log"),
    format="%(asctime)s %(levelname)s: %(message)s",
    level=logging.INFO,
    filemode="a",
)

parser = argparse.ArgumentParser()
parser.add_argument("iptv_provider")

args = parser.parse_args()

cmd = "ls ~/videos_select | grep ^videos_tests$"
output = subprocess.Popen(
    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
)
stdout, stderr = output.communicate()
ls_directory = stdout.decode("utf-8")[:-1]

if ls_directory == "":
    cmd = "mkdir -p ~/videos_select/videos_tests"
    directory = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    directory.wait()
    print(
        "\nLe dossier videos_select/videos_tests a été créé dans votre dossier home.\n"
    )

if args.iptv_provider[-5:] == "_junk":
    iptv_provider = args.iptv_provider[:-5]
else:
    iptv_provider = args.iptv_provider

cmd = (
    "ls /home/"
    + user
    + "/.config/iptvselect-fr/iptv_providers/{iptv_provider}_original_m3ulinks.ini".format(
        iptv_provider=shlex.quote(iptv_provider)
    )
)
output = subprocess.Popen(
    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
)
stdout, stderr = output.communicate()

try:
    provider = stdout.decode("utf-8").split(".config/iptvselect-fr/")[1][15:-1]
except IndexError:
    provider = ""

if stderr.decode("utf-8")[:-1] != "":
    logging.error(f"Command '{cmd}' failed with error: {stderr.decode('utf-8')}")

if provider != iptv_provider + "_original_m3ulinks.ini":
    print(
        "Le fournisseur {iptv_provider} que vous avez renseigné ne possède "
        "pas de fichier nommé {iptv_provider}_original_m3ulinks.ini ."
        "Veuillez créer ce fichier soit en exécutant les scripts fill_ini.py ou "
        "install_iptv.py ou alors en copiant le fichier {iptv_provider}.ini "
        "en le renommant {iptv_provider}_original_"
        "m3ulinks.ini ".format(iptv_provider=iptv_provider)
    )
    exit()

answers_apps = [1, 2, 3, 4]
provider_recorder = 5

while provider_recorder not in answers_apps:
    try:
        provider_recorder = int(
            input(
                "\nQuelle application souhaitez-vous utiliser pour "
                "enregistrer les vidéos de ce fournisseur d'IPTV? (vous pouvez utiliser "
                "le programme recorder_test.py pour tester la meilleur application). \n\n"
                "1) FFmpeg\n2) VLC\n3) Mplayer\n4) Streamlink\n"
                "Sélectionnez entre 1 et 4\n"
            )
        )
    except ValueError:
        print("Vous devez sélectionner entre 1 et 4")


with open(
    "/home/" + user + "/.config/iptvselect-fr/iptv_providers"
    "/{iptv_provider}_original_m3ulinks.ini".format(iptv_provider=iptv_provider),
    "r",
) as ini:
    first_line = ini.readline()
    lines = ini.read().splitlines()

cmd = (
    "ls /home/" + user + "/.config/iptvselect-fr/iptv_providers/{iptv_provider}_junk.ini"
).format(iptv_provider=shlex.quote(iptv_provider))
output = subprocess.Popen(
    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
)
stdout, stderr = output.communicate()

try:
    junk = stdout.decode("utf-8").split(".config/iptvselect-fr/")[1][15:-1]
except IndexError:
    junk = ""

if stderr.decode("utf-8")[:-1] != "":
    logging.error(f"Command '{cmd}' failed with error: {stderr.decode('utf-8')}")

if junk == iptv_provider + "_junk.ini":
    cmd = (
        "cp /home/{user}/.config/iptvselect-fr/iptv_providers/"
        "{iptv_provider}_junk.ini /home/{user}/.config/"
        "iptvselect-fr/iptv_providers/{iptv_provider}_junk_last.ini".format(
            user=user, iptv_provider=shlex.quote(iptv_provider)
        )
    )
    cp_junk = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    cp_junk.wait()
else:
    cmd = (
        "touch /home/" + user + "/.config/iptvselect-fr/iptv_providers/"
        "{iptv_provider}_junk.ini"
    ).format(iptv_provider=shlex.quote(iptv_provider))
    output = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    output.wait()

check_junk = False

if args.iptv_provider[-5:] == "_junk":
    with open(
        "/home/" + user + "/.config/iptvselect-fr/iptv_providers/"
        "{iptv_provider}_junk.ini".format(iptv_provider=iptv_provider),
        "r",
    ) as ini:
        first_line = ini.readline()
        junks_to_check = ini.read().splitlines()
    check_junk = True

if check_junk:
    lines_to_check = junks_to_check
    file_to_check = "junk"
else:
    lines_to_check = lines
    file_to_check = "original_m3ulinks"

junkies = []
junkies_line = []

record_time = 60
number_m3u_links = 0

for line in lines_to_check:
    if line != "" and line[-3:] != " = ":
        number_m3u_links += 1

print(
    "Le programme de contrôle des chaines a démarré. Il "
    "y a {number_m3u_links} chaînes à vérifier dans le fichier "
    "{iptv_provider}_{file_to_check}.ini . Il faudra donc patienter "
    "environ {minutes} minutes.\n".format(
        number_m3u_links=number_m3u_links,
        iptv_provider=iptv_provider,
        file_to_check=file_to_check,
        minutes=round((number_m3u_links * record_time) / 60),
    )
)

for line in lines_to_check:
    if " = " in line:
        now = datetime.now().strftime("%Y-%m-%d-%H-%M")
        split = line.split(" = ")
        if split[1] != "":
            channel_formated = split[0].replace(" ", "_")
            channel_formated = channel_formated.replace("'", "_")
            if provider_recorder == 1:
                cmd = (
                    "ffmpeg -y -i {m3u8_link} -map 0:v -map 0:a -map 0:s? "
                    "-c:v copy -c:a copy -c:s copy -t 60 "
                    "-f mpegts -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 1"
                    " -reconnect_at_eof -y /home/$USER/videos_select/videos_tests"
                    "/{iptv_provider}_{now}_{channel}.ts >> /home/$USER/videos_select"
                    "/videos_tests/{iptv_provider}_{now}_{channel}"
                    "_test.log 2>&1".format(
                        m3u8_link=shlex.quote(split[1]),
                        channel=shlex.quote(channel_formated),
                        iptv_provider=shlex.quote(iptv_provider),
                        now=now,
                    )
                )
            elif provider_recorder == 2:
                cmd = (
                    "cvlc -v {m3u8_link} --run-time 60 --sout=file/ts:/home/"
                    "$USER/videos_select/videos_tests/{iptv_provider}_{now}"
                    "_{channel}.ts >> /home/$USER/videos_select/videos_tests"
                    "/{iptv_provider}_{now}_{channel}_test.log 2>&1".format(
                        m3u8_link=shlex.quote(split[1]),
                        channel=shlex.quote(channel_formated),
                        iptv_provider=shlex.quote(iptv_provider),
                        now=now,
                    )
                )
            elif provider_recorder == 3:
                cmd = (
                    "mplayer {m3u8_link} -dumpstream -dumpfile "
                    "/home/$USER/videos_select/videos_tests/{iptv_provider}_{now}_{channel}.ts >> "
                    "/home/$USER/videos_select/videos_tests/{iptv_provider}_{now}_{channel}_"
                    "test.log 2>&1".format(
                        m3u8_link=shlex.quote(split[1]),
                        channel=shlex.quote(channel_formated),
                        iptv_provider=shlex.quote(iptv_provider),
                        now=now,
                    )
                )
            else:
                cmd = (
                    "streamlink --http-no-ssl-verify --hls-live-restart "
                    "--hls-segment-threads 10 --hls-segment-timeout 10 "
                    "--stream-segment-attempts 100 --retry-streams 1 "
                    "--retry-max 100 --hls-duration 00:60 -o "
                    "/home/$USER/videos_select/videos_tests/{iptv_provider}_{now}_{channel}.ts "
                    "-f {m3u8_link} best >> "
                    "/home/$USER/videos_select/videos_tests/{iptv_provider}_{now}_{channel}_test.log"
                    " 2>&1".format(
                        m3u8_link=shlex.quote(split[1]),
                        channel=shlex.quote(channel_formated),
                        iptv_provider=shlex.quote(iptv_provider),
                        now=now,
                    )
                )

            record = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )

            time.sleep(record_time)

            if 2 <= provider_recorder <= 3:
                cmd = (
                    "ps -ef | grep {iptv_provider}_{now}_{channel}.ts | tr -s ' ' | "
                    "cut -d ' ' -f2 | "
                    "head -n 2".format(
                        channel=shlex.quote(channel_formated),
                        iptv_provider=shlex.quote(iptv_provider),
                        now=now,
                    )
                )
                stdout = subprocess.check_output(cmd, shell=True)
                pid = int(stdout.decode("utf-8").split("\n")[:-1][1])
                cmd = "kill {pid}".format(pid=pid)
                kill = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
                )

            cmd = (
                "du /home/$USER/videos_select/videos_tests/{iptv_provider}_{now}_{channel}.ts | cut -f1"
            ).format(
                channel=shlex.quote(channel_formated),
                iptv_provider=shlex.quote(iptv_provider),
                now=now,
            )
            du_cmd = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )
            stdout, stderr = du_cmd.communicate()

            try:
                stdout_utf = stdout.decode("utf-8")[:-1]
                file_size = int(stdout_utf)
                if stderr.decode("utf-8")[:-1] != "":
                    logging.error(
                        f"Command '{cmd}' failed with error: {stderr.decode('utf-8')}"
                    )
            except ValueError:
                print(
                    "La chaine {channel} n'a pas pu être contrôlée".format(
                        channel=split[0]
                    )
                )
                file_size = 10

            if file_size < 1000:
                print(
                    "La chaine {channel} n'a pas été enregistrée!!!!!!".format(
                        channel=split[0]
                    )
                )
                junkies.append((split[0], split[1]))
                junkies_line.append(split[0] + " = " + split[1])
            else:
                print(
                    "La chaine {channel} a pu être enregistrée.".format(
                        channel=split[0]
                    )
                )

with open(
    "/home/" + user + "/.config/iptvselect-fr/iptv_providers/" + iptv_provider + "_junk.ini",
    "w",
) as ini:
    ini.write("[CHANNELS]" + "\n")
    for line in junkies_line:
        ini.write(line + "\n")

if len(junkies) > 0:
    print(
        "\nLes chaînes qui ne fonctionnent pas par rapport au fichier original de liens m3u sont:\n"
    )
    for junk in junkies:
        print(junk[0])

cmd = (
    "ls /home/" + user + "/.config/iptvselect-fr/iptv_providers/"
    "{iptv_provider}_junk_last.ini"
).format(
    iptv_provider=shlex.quote(iptv_provider),
)
output = subprocess.Popen(
    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
)
stdout, stderr = output.communicate()

try:
    file_junk = stdout.decode("utf-8").split(".config/iptvselect-fr/")[1][15:-1]
except IndexError:
    file_junk = ""

repaired = []

if file_junk == "{iptv_provider}_junk_last.ini".format(iptv_provider=iptv_provider):
    with open(
        "/home/" + user + "/.config/iptvselect-fr/iptv_providers/"
        "{iptv_provider}_junk_last.ini".format(iptv_provider=iptv_provider),
        "r",
    ) as ini:
        first_line = ini.readline()
        last_junks = ini.read().splitlines()

    for junk in last_junks:
        if junk not in junkies_line:
            split = junk.split(" = ")
            repaired.append(split[0])

    if len(repaired) > 0:
        print(
            "\nLes chaînes qui sont de nouveau fonctionnelles depuis le dernier "
            "contrôle des chaines du fournisseur d'IPTV "
            "{iptv_provider} sont:\n\n".format(iptv_provider=iptv_provider)
        )
        for repair in repaired:
            print(repair)
    else:
        print(
            "\nAucune chaine n'a été réparée depuis le dernier "
            "contrôle des chaines du fournisseur d'IPTV "
            "{iptv_provider}.".format(iptv_provider=iptv_provider)
        )

    new_junk = []

    for junk in junkies_line:
        if junk not in last_junks:
            new_junk.append(junk)

    if check_junk is False:
        if len(new_junk) > 0:
            print(
                "\nLes chaînes qui ne sont plus fonctionnelles depuis le dernier "
                "contrôle des chaines du fournisseur d'IPTV "
                "{iptv_provider} sont:\n\n".format(iptv_provider=iptv_provider)
            )
            for junk in new_junk:
                junk_split = junk.split(" = ")
                print(junk_split[0])
        else:
            print(
                "\nAucune nouvelle chaine apparait comme endommagée "
                "depuis le dernier contrôle des chaines du fournisseur d'IPTV "
                "{iptv_provider}.".format(iptv_provider=iptv_provider)
            )

with open(
    "/home/" + user + "/.config/iptvselect-fr/iptv_providers/" + iptv_provider + ".ini", "w"
) as ini:
    ini.write("[CHANNELS]" + "\n")
    for line in lines:
        if line not in junkies_line:
            ini.write(line + "\n")
        else:
            split = line.split(" = ")
            ini.write(split[0] + " = \n")

if check_junk is False and len(junkies_line) > 0 or check_junk and len(repaired) > 0:
    print(
        "\nLe fichier {iptv_provider}.ini vient "
        "d'être reconfiguré.".format(iptv_provider=iptv_provider)
    )
