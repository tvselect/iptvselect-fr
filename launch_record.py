import logging
import json
import subprocess
import os
import glob
import shutil
import shlex

from configparser import ConfigParser
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from getpass import getuser


# --- Basic environment setup ---
user = os.environ.get("USER") or getuser()

config_iptv_select = ConfigParser()
config_path = os.path.join("/home", user, ".config", "iptvselect-fr", "iptv_select_conf.ini")
try:
    config_iptv_select.read(config_path)
except Exception as e:
    # minimal fallback logging if logging below isn't configured yet
    logging.basicConfig(level=logging.INFO)
    logging.exception("Failed to read iptv_select_conf.ini (%s): %s", config_path, e)
    raise

log_file = os.path.expanduser("~/.local/share/iptvselect-fr/logs/cron_launch_record.log")
max_bytes = 2 * 1024 * 1024
backup_count = 2
log_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)

log_format = "%(asctime)s %(levelname)s %(message)s"
log_datefmt = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter(log_format, log_datefmt)
log_handler.setFormatter(formatter)

logging.basicConfig(level=logging.INFO, handlers=[log_handler])

log_dir = os.path.expanduser("~/.local/share/iptvselect-fr/logs")
os.makedirs(log_dir, exist_ok=True)
size_limit = 50 * 1024 * 1024


def get_dir_size(directory):
    """Calculate the total size of the directory (robust to permission errors)."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total_size += os.path.getsize(fp)
            except OSError:
                logging.debug("Unable to stat file %s when calculating directory size", fp)
    return total_size


def delete_oldest_files(directory, size_limit):
    """Delete the oldest files starting with 'record_' or 'infos_' when size exceeds limit."""
    try:
        files = glob.glob(os.path.join(directory, "record_*")) + glob.glob(
            os.path.join(directory, "infos_*")
        )
        files = sorted(files, key=lambda p: os.path.getmtime(p))
    except Exception as e:
        logging.exception("Error listing files in logs directory: %s", e)
        return

    total_size = get_dir_size(directory)

    while total_size > size_limit and files:
        oldest_file = files.pop(0)
        try:
            file_size = os.path.getsize(oldest_file)
        except OSError:
            file_size = 0
        try:
            os.remove(oldest_file)
            total_size -= file_size
            logging.info("Deleted %s, freed %d bytes.", oldest_file, file_size)
        except Exception as e:
            logging.exception("Failed to delete %s: %s", oldest_file, e)


try:
    if get_dir_size(log_dir) > size_limit:
        delete_oldest_files(log_dir, size_limit)
    else:
        logging.info("Logs directory size is within the limit of 50Mb.")
except Exception as e:
    logging.exception("Error while checking/cleaning log directory: %s", e)


def start_fusion_calcul(start_f):
    minutes = ["58", "59"]
    if start_f[-2:] not in minutes:
        if int(start_f[-2:]) > 7:
            return start_f[:-2] + str(int(start_f[-2:]) + 2)
        else:
            return start_f[:-2] + "0" + str(int(start_f[-2:]) + 2)
    else:
        return start_f[:-2] + str(int(start_f[-2:]) - 2)


config_iptv_select_keys = ["iptv_provider", "iptv_backup", "iptv_backup_2"]


class Provider:
    """Define a provider"""

    def __init__(self, iptv_provider, time_last):
        self.iptv_provider = iptv_provider
        self.time_last = time_last

    def max_iptv(self, config_iptv_select):
        """
        Calcul the maximum number of process allowed for an
        iptv provider.
        """
        self.config_iptv_select = config_iptv_select

        max_iptv_provider = 0

        for key in self.config_iptv_select.keys():
            if str(key) != "DEFAULT":
                for iptv_function in config_iptv_select_keys:
                    if (
                        self.config_iptv_select[str(key)][iptv_function]
                        == self.iptv_provider
                    ):
                        max_iptv_provider += 1

        return max_iptv_provider


providers = {}

for key in config_iptv_select.keys():
    if str(key) != "DEFAULT":
        for iptv_function in config_iptv_select_keys:
            iptv_prov = config_iptv_select[str(key)][iptv_function]
            if iptv_prov not in providers.keys():
                providers[iptv_prov] = Provider(iptv_prov, {})

info_progs_path = os.path.join("/home", user, ".local", "share", "iptvselect-fr", "info_progs.json")
info_progs_last_path = os.path.join("/home", user, ".local", "share", "iptvselect-fr", "info_progs_last.json")

try:
    with open(info_progs_path, "r", encoding="utf-8") as jsonfile:
        data = json.load(jsonfile)
except Exception as e:
    logging.exception("Failed to load %s: %s", info_progs_path, e)
    data = []

try:
    with open(info_progs_last_path, "r", encoding="utf-8") as jsonfile:
        data_last = json.load(jsonfile)
except FileNotFoundError:
    data_last = []
except Exception as e:
    logging.exception("Failed to load %s: %s", info_progs_last_path, e)
    data_last = []

dates_late = []

for video in data_last:
    try:
        date_video = datetime(
            year=int(video["start"][:4]),
            month=int(video["start"][4:6]),
            day=int(video["start"][6:8]),
            hour=int(video["start"][8:10]),
            minute=int(video["start"][10:]),
        ) + timedelta(seconds=int(video["duration"]))
        if date_video > datetime.now():
            dates_late.append(date_video)
    except Exception:
        logging.debug("Skipping invalid entry in info_progs_last.json: %s", video)

provider_rank = 1

while provider_rank < 5:
    try:
        provider = config_iptv_select["PROVIDER_" + str(provider_rank)]
    except KeyError:
        logging.warning(
            "Le fichier iptv_select_conf.ini n'est pas configuré. "
            "Assurez-vous de le configurer au moyen du script configparser_iptv.py."
        )
        exit()
    if provider.get("iptv_provider", "") != "":
        provider_iptv_recorded = provider["iptv_provider"]
        rank_provider_iptv_recorded = str(provider_rank) + provider_iptv_recorded
        if len(dates_late) > 0:
            providers[provider_iptv_recorded].time_last[rank_provider_iptv_recorded] = (
                dates_late[0]
            )
            dates_late.pop(0)
        else:
            providers[provider_iptv_recorded].time_last[
                rank_provider_iptv_recorded
            ] = datetime.now()
    provider_rank += 1


start_records = []
start_records_fusion = []

for video in data:
    start_records.append(video["start"])
    start_records_fusion.append(video["start_fusion"])

title_last = "kjgfsdkjfghl"
start_last = 202212080820

for video in data:
    provider_rank = 1
    iptv_provider_set = False
    iptv_backup_set = False
    iptv_backup_2_set = False
    video_start = video["start"]

    try:
        video_start_datetime = datetime(
            year=int(video_start[:4]),
            month=int(video_start[4:6]),
            day=int(video_start[6:8]),
            hour=int(video_start[8:10]),
            minute=int(video_start[10:]),
        )
    except Exception:
        logging.warning("Invalid start date format for video: %s", video.get("start"))
        continue

    provider_iptv_recorded = "no_provider"
    provider_iptv_backup = "no_backup"
    provider_iptv_backup_2 = "no_backup_2"

    if title_last == video["title"][:10] and video_start == start_last:
        continue

    title_last = video["title"][:10]
    start_last = video_start

    while provider_rank < 5:
        try:
            provider = config_iptv_select["PROVIDER_" + str(provider_rank)]
        except KeyError:
            logging.warning(
                "Le fichier iptv_select_conf.ini n'est pas configuré. "
                "Assurez-vous de le configurer au moyen du script configparser_iptv.py."
            )
            exit()

        if provider.get("iptv_provider", "") != "" and iptv_provider_set is False:
            config_iptv_provider = ConfigParser(interpolation=None)
            provider_cfg_path = os.path.join(
                "/home", user, ".config", "iptvselect-fr", "iptv_providers", provider["iptv_provider"] + ".ini"
            )
            try:
                config_iptv_provider.read(provider_cfg_path)
            except Exception as e:
                logging.exception("Error reading provider config %s: %s", provider_cfg_path, e)
                provider_rank += 1
                continue

            if len(config_iptv_provider) < 2:
                logging.error(
                    "Le fichier iptv_select_conf.ini n'est pas configuré correctement "
                    " car le fournisseur d'IPTV renseigné %s ne correspond pas "
                    "à un fichier de configuration du fournisseur se terminant par "
                    "l'extension .ini", provider["iptv_provider"]
                )
                exit()
            try:
                time_last = providers[provider["iptv_provider"]].time_last.get(str(provider_rank) + provider["iptv_provider"], datetime.now())
            except KeyError:
                time_last = datetime.now()
            if time_last < video_start_datetime:
                try:
                    m3u8_link = config_iptv_provider["CHANNELS"][video["channel"].lower()]
                    if isinstance(m3u8_link, str) and m3u8_link.strip() != "":
                        cmd = ["at", "-t", video_start]
                        script = (
                            ". $HOME/.local/share/iptvselect-fr/.venv/bin/activate "
                            "&& python3 record_iptv.py {title} {provider} "
                            "{recorder} '{m3u8_link}' {duration} {save} >> "
                            "~/.local/share/iptvselect-fr/logs/record_{title}_"
                            "original.log 2>&1\n".format(
                                title=video["title"],
                                provider=provider["iptv_provider"],
                                recorder=provider.get("provider_recorder", ""),
                                m3u8_link=m3u8_link,
                                save="original",
                                duration=video.get("duration", ""),
                            )
                        )
                        try:
                            with open(log_file, "a", encoding="utf-8") as log:
                                launch = subprocess.Popen(
                                    cmd, stdin=subprocess.PIPE, stdout=log, stderr=log
                                )
                                try:
                                    launch.communicate(input=script.encode(), timeout=30)
                                except subprocess.TimeoutExpired:
                                    launch.kill()
                                    logging.warning("Scheduling (at) process timed out for video %s", video.get("title"))
                                launch.wait()
                        except Exception as e:
                            logging.exception("Failed to schedule recording with at for video %s: %s", video.get("title"), e)

                        iptv_provider_set = True
                        provider_iptv_recorded = provider["iptv_provider"]
                        rank_provider_iptv_recorded = (
                            str(provider_rank) + provider_iptv_recorded
                        )
                        providers[provider_iptv_recorded].time_last[
                            rank_provider_iptv_recorded
                        ] = video_start_datetime + timedelta(
                            seconds=int(video["duration"])
                        )
                    else:
                        logging.info(
                            "La chaîne %s ne comporte pas de lien m3u dans le fichier %s pour réaliser l'enregistrement de ce programme. Le fournisseur d'IPTV %s ne sera donc pas utilisé pour enregistrer la vidéo %s.",
                            video.get("channel"), provider["iptv_provider"] + ".ini", provider["iptv_provider"], video.get("title")
                        )
                except KeyError:
                    logging.warning(
                        "La chaîne %s n'est pas présente dans le fichier %s. Le fournisseur d'IPTV %s ne sera donc pas utilisé pour enregistrer la vidéo %s .",
                        video.get("channel"), provider["iptv_provider"] + ".ini", provider["iptv_provider"], video.get("title")
                    )
            else:
                logging.info(
                    "La position %s du fichier iptv_select_conf.ini pour le founisseur d'IPTV %s n'est pas libre pour enregistrer le film %s.",
                    str(provider_rank), provider["iptv_provider"], video.get("title")
                )
                provider_rank += 1
                continue
        else:
            provider_rank += 1
            continue

        if provider.get("iptv_backup", "") != "" and iptv_backup_set is False:
            config_iptv_backup = ConfigParser(interpolation=None)
            backup_cfg_path = os.path.join(
                "/home", user, ".config", "iptvselect-fr", "iptv_providers", provider["iptv_backup"] + ".ini"
            )
            try:
                config_iptv_backup.read(backup_cfg_path)
            except Exception as e:
                logging.exception("Error reading backup config %s: %s", backup_cfg_path, e)
                provider_rank += 1
                continue
            if len(config_iptv_backup) < 2:
                logging.error(
                    "Le fichier iptv_select_conf.ini n'est pas configuré correctement "
                    " car le fournisseur d'IPTV renseigné %s ne correspond pas à un fichier .ini",
                    provider["iptv_backup"]
                )
                exit()

            try:
                if video_start[-2:] != "59":
                    if int(video_start[-2:]) > 8:
                        video_start_backup = video_start[:-2] + str(
                            int(video_start[-2:]) + 1
                        )
                    else:
                        video_start_backup = (
                            video_start[:-2] + "0" + str(int(video_start[-2:]) + 1)
                        )
                else:
                    video_start_backup = video_start[:-2] + str(
                        int(video_start[-2:]) - 1
                    )
                m3u8_link = config_iptv_backup["CHANNELS"][video["channel"].lower()]
                if isinstance(m3u8_link, str) and m3u8_link.strip() != "":
                    cmd = [
                        "at",
                        "-t",
                        video_start_backup,
                    ]
                    script = (
                        ". $HOME/.local/share/iptvselect-fr/.venv/bin/activate "
                        "&& python3 record_iptv.py {title} {provider} "
                        "{recorder} '{m3u8_link}' {duration} {save} >> "
                        "~/.local/share/iptvselect-fr/logs/record_{title}_"
                        "backup.log 2>&1\n".format(
                            title=video["title"],
                            provider=provider["iptv_backup"],
                            recorder=provider.get("backup_recorder", ""),
                            m3u8_link=m3u8_link,
                            save="backup",
                            duration=video["duration"],
                        )
                    )
                    try:
                        with open(log_file, "a", encoding="utf-8") as log:
                            launch = subprocess.Popen(
                                cmd, stdin=subprocess.PIPE, stdout=log, stderr=log
                            )
                            try:
                                launch.communicate(input=script.encode(), timeout=30)
                            except subprocess.TimeoutExpired:
                                launch.kill()
                                logging.warning("Scheduling backup (at) timed out for video %s", video.get("title"))
                            launch.wait()
                    except Exception as e:
                        logging.exception("Failed to schedule backup recording: %s", e)

                    iptv_backup_set = True
                    provider_iptv_backup = provider["iptv_backup"]
                    if iptv_provider_set is True and provider.get("iptv_backup_2", "") == "":
                        break
                else:
                    logging.info(
                        "La chaîne %s ne comporte pas de lien m3u dans le fichier %s pour réaliser l'enregistrement de ce programme. Le fournisseur d'IPTV %s ne sera donc pas utilisé pour enregistrer la 1ère sauvegarde de la vidéo %s .",
                        video.get("channel"), provider["iptv_backup"] + ".ini", provider["iptv_backup"], video.get("title")
                    )
            except KeyError:
                logging.warning(
                    "La chaîne %s n'est pas présente dans le fichier %s. Le fournisseur d'IPTV %s ne sera donc pas utilisé pour enregistrer la 1ère sauvegarde de la vidéo %s",
                    video.get("channel"), provider["iptv_backup"] + ".ini", provider["iptv_backup"], video.get("title")
                )
        else:
            provider_rank += 1
            continue

        if provider.get("iptv_backup_2", "") != "" and iptv_backup_2_set is False:
            config_iptv_backup_2 = ConfigParser(interpolation=None)
            backup2_cfg_path = os.path.join(
                "/home", user, ".config", "iptvselect-fr", "iptv_providers", provider["iptv_backup_2"] + ".ini"
            )
            try:
                config_iptv_backup_2.read(backup2_cfg_path)
            except Exception as e:
                logging.exception("Error reading backup2 config %s: %s", backup2_cfg_path, e)
                provider_rank += 1
                continue
            if len(config_iptv_backup_2) < 2:
                logging.error(
                    "Le fichier iptv_select_conf.ini n'est pas configuré correctement "
                    " car le fournisseur d'IPTV renseigné %s ne correspond pas à un fichier .ini",
                    provider["iptv_backup_2"]
                )
                exit()

            try:
                if int(video_start[-2:]) < 58:
                    if int(video_start[-2:]) > 7:
                        video_start_backup_2 = video_start[:-2] + str(
                            int(video_start[-2:]) + 2
                        )
                    else:
                        video_start_backup_2 = (
                            video_start[:-2] + "0" + str(int(video_start[-2:]) + 2)
                        )
                else:
                    video_start_backup_2 = video_start[:-2] + str(
                        int(video_start[-2:]) - 2
                    )
                m3u8_link = config_iptv_backup_2["CHANNELS"][video["channel"].lower()]
                if isinstance(m3u8_link, str) and m3u8_link.strip() != "":
                    cmd = [
                        "at",
                        "-t",
                        video_start_backup_2,
                    ]
                    script = (
                        ". $HOME/.local/share/iptvselect-fr/.venv/bin/activate "
                        "&& python3 record_iptv.py {title} {provider} "
                        "{recorder} '{m3u8_link}' {duration} {save} >> "
                        "~/.local/share/iptvselect-fr/logs/record_{title}_"
                        "backup_2.log 2>&1\n".format(
                            title=video["title"],
                            provider=provider["iptv_backup_2"],
                            recorder=provider.get("backup_2_recorder", ""),
                            m3u8_link=m3u8_link,
                            save="backup_2",
                            duration=video["duration"],
                        )
                    )
                    try:
                        with open(log_file, "a", encoding="utf-8") as log:
                            launch = subprocess.Popen(
                                cmd, stdin=subprocess.PIPE, stdout=log, stderr=log
                            )
                            try:
                                launch.communicate(input=script.encode(), timeout=30)
                            except subprocess.TimeoutExpired:
                                launch.kill()
                                logging.warning("Scheduling backup_2 (at) timed out for video %s", video.get("title"))
                            launch.wait()
                    except Exception as e:
                        logging.exception("Failed to schedule backup_2 recording: %s", e)

                    iptv_backup_2_set = True
                    provider_iptv_backup_2 = provider["iptv_backup_2"]
                    if iptv_provider_set is True:
                        break
                    else:
                        provider_rank += 1
                else:
                    logging.info(
                        "La chaîne %s ne comporte pas de lien m3u dans le fichier %s pour réaliser l'enregistrement de ce programme. Le fournisseur d'IPTV %s ne sera donc pas utilisé pour enregistrer la 2ème sauvegarde de la vidéo %s .",
                        video.get("channel"), provider["iptv_backup_2"] + ".ini", provider["iptv_backup_2"], video.get("title")
                    )
                    provider_rank += 1
                    continue

            except KeyError:
                logging.warning(
                    "La chaîne %s n'est pas présente dans le fichier %s. Le fournisseur d'IPTV %s ne sera donc pas utilisé pour enregistrer la 2ème sauvegarde de la vidéo %s.",
                    video.get("channel"), provider["iptv_backup_2"] + ".ini", provider["iptv_backup_2"], video.get("title")
                )
                provider_rank += 1
                continue
        else:
            provider_rank += 1
            continue

    if iptv_provider_set:
        start_fusion_origin = video["start_fusion"]
        if video["start_fusion"] in start_records:
            video["start_fusion"] = start_fusion_calcul(video["start_fusion"])
        if start_records_fusion.count(video["start_fusion"]) > 1:
            if video["start_fusion"] == start_fusion_origin:
                start_records_fusion.remove(video["start_fusion"])
            video["start_fusion"] = start_fusion_calcul(video["start_fusion"])

        cmd = [
            "at",
            "-t",
            video["start_fusion"],
        ]
        script = " ".join([
            "python3",
            "fusion_script.py",
            video["title"],
            provider_iptv_recorded,
            provider_iptv_backup,
            provider_iptv_backup_2,
        ]) + "\n"

        try:
            with open(log_file, "a", encoding="utf-8") as log:
                at_process = subprocess.Popen(
                    cmd, stdin=subprocess.PIPE, stdout=log, stderr=log
                )
                try:
                    at_process.communicate(input=script.encode(), timeout=30)
                except subprocess.TimeoutExpired:
                    at_process.kill()
                    logging.warning("Scheduling fusion (at) timed out for %s", video.get("title"))
                at_process.wait()
        except Exception as e:
            logging.exception("Failed to schedule fusion script for %s: %s", video.get("title"), e)

src = info_progs_path
dest = info_progs_last_path
try:
    shutil.copy(src, dest)
except Exception as e:
    logging.exception("Failed to copy %s to %s: %s", src, dest, e)
