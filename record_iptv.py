import logging
import subprocess
import argparse
import time
import os
import psutil
import signal
import shutil

from pathlib import Path
from datetime import datetime
from configparser import ConfigParser
from typing import Optional
from getpass import getuser

parser = argparse.ArgumentParser()
parser.add_argument("title")
parser.add_argument("provider")
parser.add_argument("recorder")
parser.add_argument("m3u8_link")
parser.add_argument("duration")
parser.add_argument("save")
args = parser.parse_args()


def count_procs_by_pattern(pattern: str, *, exact: bool = False) -> int:
    """
    Count processes whose command-line matches `pattern`.

    Arguments
    ---------
    pattern:
        The substring (or exact string if exact=True) to search for in the process
        command line (args column from `ps`).
    exact:
        If True, count lines where the args column equals `pattern` exactly.
        If False (default), count lines where `pattern` is a substring in the args.

    Returns
    -------
    int
        Number of matching processes. If `ps` fails, returns 0.
    """
    if not pattern:
        return 0

    try:
        proc = subprocess.run(
            ["ps", "-eo", "args"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except Exception:
        return 0

    if proc.returncode != 0 or proc.stdout is None:
        return 0

    if exact:
        return sum(1 for line in proc.stdout.splitlines() if line.strip() == pattern)
    else:
        return sum(1 for line in proc.stdout.splitlines() if pattern in line)


def find_pids_by_pattern(pattern: str) -> list[int]:
    """Return a list of PIDs whose command line matches a given pattern (substring)."""
    try:
        proc = subprocess.run(
            ["ps", "-eo", "pid,args"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except Exception:
        return []

    if proc.returncode != 0 or proc.stdout is None:
        return []

    pids = []
    for line in proc.stdout.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) != 2:
            continue
        pid_str, args_line = parts
        if pattern in args_line:
            try:
                pids.append(int(pid_str))
            except ValueError:
                continue
    return pids


def kill_pids(pids: list[int]):
    """Safely kill the given list of PIDs."""
    for pid in pids:
        try:
            subprocess.run(["kill", str(pid)], check=False)
            logging.info("Killed process %d", pid)
        except Exception as e:
            logging.exception("Failed to kill PID %s: %s", pid, e)


def get_second_matching_pid(title: str, provider: str, record_position: int, save: str) -> Optional[int]:
    """
    Return the second PID among processes whose command line contains the pattern:
      "{title}_{provider}_{record_position}_{save}.ts"
    Equivalent to: ps -ef | grep PATTERN | ... | head -n 2 then take the second line's PID.
    Returns None if no such second PID exists.
    """
    pattern = f"{title}_{provider}_{record_position}_{save}.ts"

    try:
        proc = subprocess.run(
            ["ps", "-eo", "pid,args"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except Exception:
        return None

    if proc.returncode != 0 or proc.stdout is None:
        return None

    matches = []
    for line in proc.stdout.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) != 2:
            continue
        pid_str, args_line = parts
        if pattern in args_line:
            try:
                matches.append(int(pid_str))
            except ValueError:
                continue
        if len(matches) >= 2:
            break  # we found two, like head -n 2

    if len(matches) >= 2:
        return matches[1]  # second PID (index 1)
    return None


# ---------- Security helpers ----------
def sanitize_filename(name: str, max_len: int = 200) -> str:
    """
    Sanitize filename while preserving accents and all Unicode characters.
    Removes only characters that are unsafe for filesystem paths.
    Prevents path traversal and trims excessive length.
    """
    if name is None:
        return ""
    if not isinstance(name, str):
        name = str(name)

    # Replace forbidden characters with underscores.
    # Keep all other Unicode characters (accents ok).
    forbidden_chars = ['/', '\\', '\0', '\n', '\r', '\t', '\v', '\f']
    sanitized = ''.join('_' if ch in forbidden_chars else ch for ch in name)

    # Remove path traversal attempts
    sanitized = sanitized.replace('..', '_')

    sanitized = sanitized.strip()

    # Enforce max length to avoid filesystem issues
    if len(sanitized) > max_len:
        sanitized = sanitized[:max_len]

    return sanitized or "_"

def safe_for_pattern(s: str) -> str:
    """
    Prepare a string for use as a ps/grep pattern: remove newlines and control chars.
    Does NOT quote or modify characters used by ffmpeg URLs; intended only to avoid
    control characters interfering with pattern matching.
    """
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    # Keep printable ASCII and common UTF-8 characters; remove control chars and newlines.
    return "".join(ch for ch in s if ch >= " " and ch != "\x7f").replace("\n", " ").replace("\r", " ")


# ---------- Environment and config ----------
user = os.environ.get("USER") or getuser()

config_iptv_select = ConfigParser()
config_path = f"/home/{user}/.config/iptvselect-fr/iptv_select_conf.ini"
try:
    config_iptv_select.read(config_path)
except Exception as e:
    # Minimal early logging fallback
    logging.basicConfig(level=logging.INFO)
    logging.exception("Failed to read config %s: %s", config_path, e)

# Ensure logs directory exists and build safe log filename
logs_dir = Path.home() / ".local" / "share" / "iptvselect-fr" / "logs"
try:
    logs_dir.mkdir(parents=True, exist_ok=True)
except Exception:
    # ignore; will surface when trying to open logs
    pass

safe_title = sanitize_filename(args.title)
log_filename = logs_dir / f"record_{safe_title}_{args.save}.log"

logging.basicConfig(
    filename=str(log_filename),
    format="%(asctime)s %(levelname)s: %(message)s",
    level=logging.INFO,
)

# ---------- main variables ----------
date_now_epoch = datetime.now().timestamp()
try:
    duration_int = int(args.duration)
except Exception:
    logging.warning("Invalid duration %r; defaulting to 0", args.duration)
    duration_int = 0
end_video = date_now_epoch + duration_int

record_position = 0


def start_or_kill():
    """
    Write time recording beginning in start_time files or kill
    recorder command
    """
    # Build safe file path components for filesystem use
    safe_title = sanitize_filename(args.title)

    file_path = Path(
        f"/home/{user}/videos_select/{safe_title}-save/{safe_title}_{args.provider}_{record_position}_{args.save}.ts"
    )

    if file_path.exists():
        ls_video = str(file_path)
    else:
        ls_video = None

    expected_path = (
        "/home/"
        + user
        + "/videos_select/{title}-save/{title}_{provider}_{record_position}_{save}.ts".format(
            title=safe_title,
            provider=args.provider,
            record_position=record_position,
            save=args.save,
        )
    )

    if ls_video == expected_path:
        time_now_epoch = datetime.now().timestamp()
        time_movie = round(time_now_epoch - 30)

        logging.info("Started!!!!")

        start_time_file = Path(
            f"/home/{user}/videos_select/{safe_title}-save/start_time_{safe_title}_{args.provider}_{args.save}.txt"
        )
        try:
            start_time_file.parent.mkdir(parents=True, exist_ok=True)
            with open(start_time_file, "a", encoding="utf-8") as file:
                file.write(str(time_movie) + "\n")
        except Exception as e:
            logging.exception("Failed to write start_time file %s: %s", start_time_file, e)
    else:
        search_string = f"{safe_title}_{args.provider}_{record_position}_{args.save}.ts"

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

        if pid_stream is not None:
            try:
                os.kill(pid_stream, signal.SIGTERM)
                logging.info("Process killed: %s", pid_stream)
            except ProcessLookupError:
                logging.error("Process with PID %s not found.", pid_stream)
            except PermissionError:
                logging.error("Permission denied to kill process with PID %s.", pid_stream)
            except Exception as e:
                logging.exception("An unexpected error occurred while killing PID %s: %s", pid_stream, e)
        else:
            logging.info("No matching process to kill.")


"""
    Check if the number of process belonging to the
    iptv provider is below the maximum allowed:
"""

max_iptv_provider = 0
config_iptv_select_keys = ["iptv_provider", "iptv_backup", "iptv_backup_2"]

for key in config_iptv_select.keys():
    if str(key) != "DEFAULT":
        for iptv_function in config_iptv_select_keys:
            try:
                if config_iptv_select[str(key)][iptv_function] == args.provider:
                    max_iptv_provider += 1
            except Exception:
                # Missing key/section -- ignore and continue
                continue

# Build a robust proc_count_provider by checking cmdline via psutil safely
proc_count_provider = 0
for proc in psutil.process_iter(["cmdline"]):
    try:
        cmdline = proc.info.get("cmdline")
        if cmdline:
            joined = " ".join(cmdline)
            if "record_iptv.py" in joined and args.provider in joined:
                proc_count_provider += 1
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        continue
    except Exception:
        continue

if int(proc_count_provider) > max_iptv_provider:
    logging.info("max_iptv_provider:" + str(max_iptv_provider))
    logging.info("proc_count_provider:" + str(proc_count_provider))
    logging.info(
        "La vidéo {title} ne sera pas enregistrée car vous n'avez pas assez de lignes"
        " de fournisseurs d'IPTV pour cet enregistrement".format(title=args.title)
    )
    exit()

date_now = datetime.now().timestamp()

dir_path = f"/home/{user}/videos_select/{safe_title}-save/{safe_title}-to-watch"
try:
    os.makedirs(dir_path, exist_ok=True)
except Exception:
    pass

file_size = 0
new_file_size = 1

while date_now < end_video:
    if args.recorder == "ffmpeg":

        # pattern used only for counting processes (not passing to ffmpeg)
        proc_count = count_procs_by_pattern(safe_for_pattern(f"ffmpeg -i {args.m3u8_link} -map 0:v"))

        p = (Path.home()
             / "videos_select"
             / f"{safe_title}-save"
             / f"{safe_title}_{args.provider}_{record_position}_{args.save}.ts"
        )

        try:
            new_file_size = p.stat().st_size
        except FileNotFoundError:
            new_file_size = 0
        except PermissionError:
            new_file_size = 0


    elif args.recorder == "streamlink":

        proc_count = count_procs_by_pattern(safe_for_pattern(f"{safe_title}_{args.provider}_"
                                            f"{record_position}_{args.save}.ts "
                                            f"-f {args.m3u8_link}"))

    elif args.recorder == "vlc":

        pattern = (
            f"{args.m3u8_link} --sout file/ts:/home/{user}/videos_select/"
            f"{safe_title}-save/{safe_title}_{args.provider}_{record_position}_{args.save}.ts"
        )

        proc_count = count_procs_by_pattern(safe_for_pattern(pattern))

        p = (Path.home()
             / "videos_select"
             / f"{safe_title}-save"
             / f"{safe_title}_{args.provider}_{record_position}_{args.save}.ts"
        )

        try:
            new_file_size = p.stat().st_size  # size in bytes
        except (FileNotFoundError, PermissionError):
            new_file_size = 0

    elif args.recorder == "mplayer":

        proc_count = count_procs_by_pattern(safe_for_pattern(f"mplayer {args.m3u8_link} -dumpstream"))

    date_now = datetime.now().timestamp()
    left_time = round(end_video - date_now)

    if left_time <= 0:
        if args.recorder == "ffmpeg":
            pattern = safe_for_pattern(f"ffmpeg -i {args.m3u8_link} -map 0:v")
        elif args.recorder == "vlc":
            pattern = safe_for_pattern(
                f"{args.m3u8_link} --sout file/ts:/home/{user}"
                f"/videos_select/{safe_title}-save/{safe_title}"
            )
        elif args.recorder == "mplayer":
            pattern = safe_for_pattern(
                f"mplayer {args.m3u8_link} -dumpstream "
                f"-dumpfile /home/{user}/videos_select/{safe_title}-save"
            )
        else:
            pattern = None

        if pattern:
            pid_list = find_pids_by_pattern(pattern)
            if pid_list:
                kill_pids(pid_list)
        break

    new_file = False

    if int(proc_count) < 1 or (
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

            left_time_str = str(left_time)

            home = Path.home()
            out_path = (home
                        / "videos_select"
                        / f"{safe_title}-save"
                        / f"{safe_title}_{args.provider}_{record_position}_{args.save}.ts"
                        )

            log_dir = home / ".local" / "share" / "iptvselect-fr" / "logs"
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            log_path = (log_dir
                        / f"infos_{safe_title}_{args.provider}_{record_position}_{args.save}.log"
                        )

            base_args = [
                "ffmpeg",
                "-i", str(args.m3u8_link),
                "-map", "0:v",
                "-map", "0:a",
                "-map", "0:s?",
                "-c:v", "copy",
                "-c:a", "copy",
                "-c:s", "copy",
                "-t", left_time_str,
                "-f", "mpegts",
            ]

            if args.provider == "freeboxtv":
                extra = ["-fflags", "nobuffer", "-err_detect", "ignore_err"]
            else:
                extra = [
                    "-reconnect", "1",
                    "-reconnect_streamed", "1",
                    "-reconnect_delay_max", "1",
                    "-reconnect_at_eof",
                ]

            ffmpeg_cmd = base_args + extra + ["-y", str(out_path)]

            try:
                with open(log_path, "ab") as log_fh:
                    try:
                        record = subprocess.Popen(
                            ffmpeg_cmd,
                            stdout=log_fh,
                            stderr=subprocess.STDOUT,
                            close_fds=True,
                        )
                    except Exception as e:
                        logging.exception("Failed to launch ffmpeg subprocess: %s", e)
                        record = None

                    # Sleep to allow the process to create the file
                    time.sleep(30)

                    p = (
                        Path.home()
                        / "videos_select"
                        / f"{safe_title}-save"
                        / f"{safe_title}_{args.provider}_{record_position}_{args.save}.ts"
                    )

                    logging.info("Checking file size for: %s", p)

                    try:
                        file_size = p.stat().st_size
                        logging.info("File size (bytes): %d", file_size)
                        new_file = True
                    except FileNotFoundError:
                        logging.warning("File not found: %s", p)
                        file_size = 0
                        new_file = False
                    except PermissionError:
                        logging.warning("Permission denied when accessing: %s", p)
                        file_size = 0
                        new_file = False
            except Exception as e:
                logging.exception("Failed handling ffmpeg logging or subprocess: %s", e)
                # continue behaviour preserved

            start_or_kill()

        if args.recorder == "streamlink":

            left_time_str = str(left_time)

            home = Path.home()
            venv_streamlink = (home
                               / ".local" / "share"
                               / "iptvselect-fr" / ".venv"
                               / "bin" / "streamlink"
                            )

            output_file = (
                home / "videos_select" / f"{safe_title}-save" /
                f"{safe_title}_{args.provider}_{record_position}_{args.save}.ts"
            )

            log_dir = home / ".local" / "share" / "iptvselect-fr" / "logs"
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

            log_file = (log_dir
                        / f"infos_{safe_title}_{args.provider}_{record_position}_{args.save}.log"
                    )

            cmd = [
                str(venv_streamlink),
                "--ffmpeg-validation-timeout", "15.0",
                "--http-no-ssl-verify",
                # "--hls-live-restart",
                "--stream-segment-attempts", "100",
                "--retry-streams", "1",
                "--retry-max", "100",
                "--stream-segmented-duration", left_time_str,
                "-o", str(output_file),
                "-f",
                str(args.m3u8_link),
                "best",
            ]

            logging.info("Launching Streamlink: %s", " ".join(cmd))

            try:
                with open(log_file, "ab") as log_fh:
                    try:
                        record = subprocess.Popen(
                            cmd,
                            stdout=log_fh,
                            stderr=subprocess.STDOUT,
                            close_fds=True,
                        )
                    except Exception as e:
                        logging.exception("Failed to launch streamlink subprocess: %s", e)
                        record = None
            except Exception as e:
                logging.exception("Failed to open streamlink log file %s: %s", log_file, e)

            time.sleep(30)

            start_or_kill()

        elif args.recorder == "vlc":
            record_position_last = record_position - 1

            pid_vlc = get_second_matching_pid(safe_title, args.provider, record_position_last, args.save)

            if pid_vlc is not None:
                try:
                    subprocess.run(
                        ["kill", str(pid_vlc)],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    logging.info("Successfully killed PID %s", pid_vlc)
                except subprocess.CalledProcessError as e:
                    stderr = e.stderr.decode().strip() if e.stderr else str(e)
                    logging.error("Failed to kill PID %s: %s", pid_vlc, stderr)
                except Exception as e:
                    logging.exception("Unexpected error killing PID %s: %s", pid_vlc, e)
            else:
                logging.warning("pid_vlc is None — no process to kill.")

            left_time_str = str(left_time)

            home = Path.home()
            out_path = (
                home
                / "videos_select"
                / f"{safe_title}-save"
                / f"{safe_title}_{args.provider}_{record_position}_{args.save}.ts"
            )

            log_dir = home / ".local" / "share" / "iptvselect-fr" / "logs"
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            log_path = log_dir / f"infos_{safe_title}_{args.provider}_{record_position}_{args.save}.log"

            cvlc_bin = shutil.which("cvlc") or "cvlc"

            cmd = [
                cvlc_bin,
                "-v",
                f"--run-time={left_time_str}",
                str(args.m3u8_link),
                "--sout",
                f"file/ts:{str(out_path)}",
            ]

            try:
                with open(log_path, "ab") as log_fh:
                    try:
                        record = subprocess.Popen(
                            cmd,
                            stdout=log_fh,
                            stderr=subprocess.STDOUT,
                            close_fds=True,
                        )
                    except Exception as e:
                        logging.exception("Failed to launch vlc subprocess: %s", e)
                        record = None
            except Exception as e:
                logging.exception("Failed to open vlc log file %s: %s", log_path, e)

            time.sleep(30)

            p = (
                Path.home()
                / "videos_select"
                / f"{safe_title}-save"
                / f"{safe_title}_{args.provider}_{record_position}_{args.save}.ts"
            )

            logging.info("Checking file size for: %s", p)

            try:
                file_size = p.stat().st_size
                new_file = True
                logging.info("File size (bytes): %d", file_size)
            except FileNotFoundError:
                file_size = 0
                new_file = False
                logging.info("File not found: %s", p)
            except PermissionError:
                file_size = 0
                new_file = False
                logging.warning("Permission denied accessing file: %s", p)

            start_or_kill()

        elif args.recorder == "mplayer":
            home = Path.home()
            mplayer_bin = shutil.which("mplayer") or "mplayer"

            out_path = (
                home
                / "videos_select"
                / f"{safe_title}-save"
                / f"{safe_title}_{args.provider}_{record_position}_{args.save}.ts"
            )

            log_dir = home / ".local" / "share" / "iptvselect-fr" / "logs"
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            log_path = log_dir / f"infos_{safe_title}_{args.provider}_{record_position}_{args.save}.log"

            cmd = [
                str(mplayer_bin),
                str(args.m3u8_link),
                "-dumpstream",
                "-dumpfile",
                str(out_path),
            ]

            try:
                log_fh = open(log_path, "ab")
            except Exception as e:
                logging.exception("Failed to open mplayer log %s: %s", log_path, e)
                log_fh = None

            try:
                if log_fh:
                    record = subprocess.Popen(
                        cmd,
                        stdout=log_fh,
                        stderr=subprocess.STDOUT,
                        close_fds=True,
                    )
                else:
                    record = subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.STDOUT,
                        close_fds=True,
                    )
                logging.info("Started mplayer PID %s writing to %s", record.pid, out_path)
            except Exception as e:
                logging.exception("Failed to launch mplayer subprocess: %s", e)
                record = None
            finally:
                # keep file open while process runs; close only if opened here and process not using it
                if log_fh and record is None:
                    try:
                        log_fh.close()
                    except Exception:
                        pass

            time.sleep(30)

            start_or_kill()

    if new_file is False and args.recorder in ["vlc", "ffmpeg"]:
        logging.info("new_file:" + str(new_file))
        file_size = new_file_size

    # throttle loop
    time.sleep(40)
