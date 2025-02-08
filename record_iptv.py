import logging
import subprocess
import argparse
import time
import os
import psutil
import signal

from pathlib import Path
from datetime import datetime
from configparser import ConfigParser

parser = argparse.ArgumentParser()
parser.add_argument("title")
parser.add_argument("provider")
parser.add_argument("recorder")
parser.add_argument("m3u8_link")
parser.add_argument("duration")
parser.add_argument("save")
args = parser.parse_args()

user = os.environ.get("USER")

config_iptv_select = ConfigParser()
config_iptv_select.read("/home/" + user + "/.config/iptvselect-fr/iptv_select_conf.ini")

logging.basicConfig(
    filename=os.path.expanduser(
        "~/.local/share/iptvselect-fr/logs/record_{title}_{save}.log".format(
            title=args.title, save=args.save
        )
    ),
    format="%(asctime)s %(levelname)s: %(message)s",
    level=logging.INFO,
)


date_now_epoch = datetime.now().timestamp()
end_video = date_now_epoch + int(args.duration)

record_position = 0


def start_or_kill():
    """
    Write time recording beginning in start_time files or kill
    recorder command"
    """
    file_path = Path(
        "/home/{}/videos_select/{}-save/{}_{}_{}_{}.ts".format(
            user, args.title, args.title, args.provider, record_position, args.save
        )
    )

    if file_path.exists():
        ls_video = str(file_path)
    else:
        ls_video = None

    if (
        ls_video
        == "/home/"
        + user
        + "/videos_select/{title}-save/{title}_{provider}_{record_position}_{save}.ts".format(
            title=args.title,
            provider=args.provider,
            record_position=record_position,
            save=args.save,
        )
    ):
        time_now_epoch = datetime.now().timestamp()
        time_movie = round(time_now_epoch - 30)

        logging.info("Started!!!!")

        with open(
            "/home/" + user + "/videos_select/{title}-save/start_time_{title}_"
            "{provider}_{save}.txt".format(
                title=args.title, provider=args.provider, save=args.save
            ),
            "a",
        ) as file:
            file.write(str(time_movie) + "\n")
    else:
        search_string = "{}_{}_{}_{}.ts".format(
            args.title,
            args.provider,
            record_position,
            args.save,
        )

        matching_pids = []
        for proc in psutil.process_iter(["pid", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline")
                if cmdline and any(search_string in arg for arg in cmdline):
                    matching_pids.append(proc.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        if len(matching_pids) > 1:
            pid_stream = matching_pids[1]
        else:
            pid_stream = None

        try:
            os.kill(pid_stream, signal.SIGTERM)
            logging.info("Process killed!!!")
        except ProcessLookupError:
            logging.error(f"Process with PID {pid_stream} not found.")
        except PermissionError:
            logging.error(f"Permission denied to kill process with PID {pid_stream}.")
        except Exception as e:
            logging.error(f"An error occurred: {e}")


"""
    Check if the number of process belonging to the
    iptv provider is below the maximum allowed:
"""

max_iptv_provider = 0
config_iptv_select_keys = ["iptv_provider", "iptv_backup", "iptv_backup_2"]

for key in config_iptv_select.keys():
    if str(key) != "DEFAULT":
        for iptv_function in config_iptv_select_keys:
            if config_iptv_select[str(key)][iptv_function] == args.provider:
                max_iptv_provider += 1

search_pattern = "record_iptv.py"
proc_count_provider = sum(
    search_pattern in " ".join(proc.info["cmdline"])
    and args.provider in " ".join(proc.info["cmdline"])
    for proc in psutil.process_iter(["cmdline"])
)

if int(proc_count_provider) > max_iptv_provider:
    logging.info("max_iptv_provider:" + str(max_iptv_provider))
    logging.info("proc_count_provider:" + str(proc_count_provider))
    logging.info(
        "La vidéo {title} ne sera pas enregistrée car vous n'avez pas assez de lignes"
        " de fournisseurs d'IPTV pour cet enregistrement".format(title=args.title)
    )
    exit()

date_now = datetime.now().timestamp()

dir_path = "/home/{}/videos_select/{}-save/{}-to-watch".format(
    user, args.title, args.title
)
os.makedirs(dir_path, exist_ok=True)

file_size = 0
new_file_size = 1

while date_now < end_video:
    if args.recorder == "ffmpeg":
        cmd = "ps aux | grep -c 'ffmpeg -i {m3u8_link} -map 0:v'".format(
            m3u8_link=args.m3u8_link,
        )
        pid_record = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        stdout, stderr = pid_record.communicate()
        proc_count = stdout.decode("utf-8")[:-1]

        cmd = (
            "du /home/$USER/videos_select/{title}-save/{title}_{provider}_{record_position}"
            "_{save}.ts | cut -f1".format(
                title=args.title,
                provider=args.provider,
                record_position=record_position,
                save=args.save,
            )
        )
        du_cmd = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        stdout, stderr = du_cmd.communicate()
        try:
            new_file_size = int(stdout.decode("utf-8")[:-1])
        except ValueError:
            new_file_size = 0

    elif args.recorder == "streamlink":
        cmd = (
            "ps aux | grep -c '{title}_{provider}_{record_position}"
            "_{save}.ts -f {m3u8_link}'".format(
                title=args.title,
                provider=args.provider,
                record_position=record_position,
                save=args.save,
                m3u8_link=args.m3u8_link,
            )
        )
        pid_record = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        stdout, stderr = pid_record.communicate()
        proc_count = stdout.decode("utf-8")[:-1]

    elif args.recorder == "vlc":
        cmd = (
            "ps aux | grep -c '{m3u8_link} --sout="
            "file/ts:/home/.*/videos_select/{title}-save/{title}_"
            "{provider}_{record_position}_{save}.ts'".format(
                m3u8_link=args.m3u8_link,
                title=args.title,
                provider=args.provider,
                record_position=record_position,
                save=args.save,
            )
        )
        pid_record = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        stdout, stderr = pid_record.communicate()
        proc_count = stdout.decode("utf-8")[:-1]
        cmd = (
            "du /home/$USER/videos_select/{title}-save/{title}_{provider}_{record_position}"
            "_{save}.ts | cut -f1".format(
                title=args.title,
                provider=args.provider,
                record_position=record_position,
                save=args.save,
            )
        )
        du_cmd = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        stdout, stderr = du_cmd.communicate()
        try:
            new_file_size = int(stdout.decode("utf-8")[:-1])
        except ValueError:
            new_file_size = 0

    elif args.recorder == "mplayer":
        cmd = "ps aux | grep -c 'mplayer {m3u8_link} -dumpstream'".format(
            m3u8_link=args.m3u8_link
        )
        pid_record = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        stdout, stderr = pid_record.communicate()
        proc_count = stdout.decode("utf-8")[:-1]

    date_now = datetime.now().timestamp()
    left_time = round(end_video - date_now)

    if left_time <= 0:
        if args.recorder == "ffmpeg":
            cmd = (
                "ps -ef | grep 'ffmpeg -i {m3u8_link} -map 0:v'"
                " | tr -s ' ' | cut -d ' ' -f2".format(m3u8_link=args.m3u8_link)
            )
        if args.recorder == "vlc":
            cmd = (
                "ps -ef | grep '{m3u8_link} --sout="
                "file/ts:/home/.*/videos_select/{title}-save/{title}' "
                "| tr -s ' ' | cut -d ' ' -f2".format(
                    m3u8_link=args.m3u8_link, title=args.title
                )
            )
        elif args.recorder == "mplayer":
            cmd = (
                "ps -ef | grep 'mplayer {m3u8_link} -dumpstream "
                "-dumpfile /home/.*/videos_select/{title}-save' "
                "| tr -s ' ' | cut -d ' ' -f2".format(
                    m3u8_link=args.m3u8_link, title=args.title
                )
            )
        pid_range = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        stdout, stderr = pid_range.communicate()
        pid_list = stdout.decode("utf-8").split("\n")[:-1]

        for pid in pid_list:
            cmd = "kill {pid_stream}".format(pid_stream=int(pid))
            kill = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )
            logging.info("kill last process")
        break

    new_file = False

    if int(proc_count) < 3 or (
        args.recorder in ["vlc", "ffmpeg"] and file_size == new_file_size
    ):
        logging.info("!!!! New file !!!!!!!")
        logging.info(
            "file_size = "
            + str(file_size)
            + " , new_file_size = "
            + str(new_file_size)
            + " , proc_count = "
            + str(proc_count)
        )

        record_position += 1

        if args.recorder == "ffmpeg":
            if args.provider == "freeboxtv":
                cmd = (
                    "ffmpeg -i '{m3u8_link}' -map 0:v -map 0:a -map 0:s? "
                    "-c:v copy -c:a copy -c:s copy -t {left_time} -f mpegts "
                    "-fflags nobuffer -err_detect ignore_err -y /home"
                    "/$USER/videos_select/{title}-save/{title}_{provider}"
                    "_{record_position}_{save}.ts >> ~/.local/share/iptvselect-fr"
                    "/logs/infos_{title}_{provider}_{record_position}_"
                    "{save}.log 2>&1".format(
                        m3u8_link=args.m3u8_link,
                        left_time=left_time,
                        title=args.title,
                        provider=args.provider,
                        record_position=record_position,
                        save=args.save,
                    )
                )
            else:
                cmd = (
                    "ffmpeg -i '{m3u8_link}' -map 0:v -map 0:a -map 0:s? "
                    "-c:v copy -c:a copy -c:s copy -t {left_time} "
                    "-f mpegts -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 1"
                    " -reconnect_at_eof -y /home/$USER/videos_select/{title}-save/{title}_"
                    "{provider}_{record_position}_{save}.ts >> ~/.local/share/iptvselect-fr"
                    "/logs/infos_{title}_{provider}_{record_position}_{save}.log "
                    "2>&1".format(
                        m3u8_link=args.m3u8_link,
                        left_time=left_time,
                        title=args.title,
                        provider=args.provider,
                        record_position=record_position,
                        save=args.save,
                    )
                )
            record = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )

            time.sleep(30)

            cmd = (
                "du ~/videos_select/{title}-save/{title}"
                "_{provider}_{record_position}"
                "_{save}.ts | cut -f1".format(
                    title=args.title,
                    provider=args.provider,
                    record_position=record_position,
                    save=args.save,
                )
            )
            logging.info("cmd:" + cmd)
            du_cmd = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )
            stdout, stderr = du_cmd.communicate()

            try:
                logging.info("stdout:" + stdout.decode("utf-8")[:-1])
                file_size = int(stdout.decode("utf-8")[:-1])
                new_file = True
            except ValueError:
                file_size = 0
                new_file = False

            start_or_kill()

        if args.recorder == "streamlink":
            cmd = (
                "streamlink --http-no-ssl-verify --hls-live-restart "
                "--hls-segment-threads 10 --hls-segment-timeout 10 --stream-segment-attempts 100 "
                "--retry-streams 1 --retry-max 100 --hls-duration 00:{left_time} -o "
                "/home/$USER/videos_select/{title}-save/{title}_{provider}_{record_position}"
                "_{save}.ts -f {m3u8_link} best >> ~/.local/share/iptvselect-fr/logs/infos"
                "_{title}_{provider}_{record_position}_{save}.log "
                "2>&1".format(
                    left_time=left_time,
                    title=args.title,
                    provider=args.provider,
                    record_position=record_position,
                    save=args.save,
                    m3u8_link=args.m3u8_link,
                )
            )
            record = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )

            time.sleep(30)

            start_or_kill()

        elif args.recorder == "vlc":
            record_position_last = record_position - 1

            cmd = (
                "ps -ef | grep {title}_{provider}_{record_position}_"
                "{save}.ts | tr -s ' ' | cut -d ' ' -f2 | "
                "head -n 2".format(
                    title=args.title,
                    provider=args.provider,
                    record_position=record_position_last,
                    save=args.save,
                )
            )
            stdout = subprocess.check_output(cmd, shell=True)
            pid_vlc = int(stdout.decode("utf-8").split("\n")[:-1][1])
            cmd = "kill {pid_vlc}".format(pid_vlc=pid_vlc)
            kill = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )

            cmd = (
                "cvlc -v --run-time={left_time} '{m3u8_link}' --sout=file/ts:"
                "/home/$USER/videos_select/{title}-save/{title}_{provider}"
                "_{record_position}_{save}.ts "
                ">> ~/.local/share/iptvselect-fr/logs/infos_{title}_{provider}"
                "_{record_position}_{save}.log 2>&1".format(
                    left_time=left_time,
                    m3u8_link=args.m3u8_link,
                    title=args.title,
                    provider=args.provider,
                    save=args.save,
                    record_position=record_position,
                )
            )
            record = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )

            time.sleep(30)

            cmd = (
                "du ~/videos_select/{title}-save/{title}"
                "_{provider}_{record_position}"
                "_{save}.ts | cut -f1".format(
                    title=args.title,
                    provider=args.provider,
                    record_position=record_position,
                    save=args.save,
                )
            )
            logging.info("cmd:" + cmd)
            du_cmd = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )
            stdout, stderr = du_cmd.communicate()

            try:
                logging.info("stdout:" + stdout.decode("utf-8")[:-1])
                file_size = int(stdout.decode("utf-8")[:-1])
                new_file = True
            except ValueError:
                file_size = 0
                new_file = False

            start_or_kill()

        elif args.recorder == "mplayer":
            cmd = (
                "mplayer {m3u8_link} -dumpstream -dumpfile "
                "/home/$USER/videos_select/{title}-save/{title}_{provider}"
                "_{record_position}_{save}.ts >> ~/.local/share/iptvselect-fr/logs/infos_{title}_{provider}"
                "_{record_position}_{save}.log 2>&1".format(
                    m3u8_link=args.m3u8_link,
                    title=args.title,
                    provider=args.provider,
                    save=args.save,
                    record_position=record_position,
                )
            )
            record = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )

            time.sleep(30)

            start_or_kill()

    if new_file is False and args.recorder in ["vlc", "ffmpeg"]:
        logging.info("new_file:" + str(new_file))
        file_size = new_file_size

    time.sleep(40)
