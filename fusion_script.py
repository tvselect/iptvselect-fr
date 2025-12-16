#!/usr/bin/env python3
import argparse
import json
import logging
import shutil
import subprocess
import os

from configparser import ConfigParser
from pathlib import Path
from getpass import getuser
from typing import List

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

def safe_read_config(path: str) -> ConfigParser:
    cp = ConfigParser()
    try:
        cp.read(path)
    except Exception:
        logging.exception("Failed to read config: %s", path)
    return cp

def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        logging.warning("Invalid integer value %r, using default %s", value, default)
        return default

def run_subprocess(cmd: List[str], **kwargs):
    """
    Run subprocess.run safely: catch exceptions and return a CompletedProcess-like object.
    """
    try:
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **kwargs)
    except Exception as e:
        logging.exception("Subprocess failed to run %s: %s", cmd, e)
        # create dummy-like object for compatibility
        class Dummy:
            returncode = 1
            stdout = ""
            stderr = str(e)
        return Dummy()

def is_within_base(base: Path, target: Path) -> bool:
    """
    Return True if target is inside base (including equal).
    Works with resolved paths when possible.
    """
    try:
        base_r = base.resolve()
        target_r = target.resolve(strict=False)
        return base_r == target_r or base_r in target_r.parents
    except Exception:
        # Fallback conservative: if resolve fails, do a string prefix check but still cautious
        try:
            base_s = str(base)
            target_s = str(target)
            return target_s.startswith(base_s.rstrip("/") + "/") or target_s == base_s
        except Exception:
            return False

# ---------- Setup ----------
user = os.environ.get("USER") or getuser()

config_constants = safe_read_config(f"/home/{user}/.config/iptvselect-fr/constants.ini")
# Read MIN_TIME and SAFE_TIME conservatively
try:
    MIN_TIME = int(config_constants.get("FUSION", {}).get("MIN_TIME", 0))
except Exception:
    try:
        MIN_TIME = int(config_constants["FUSION"]["MIN_TIME"])
    except Exception:
        MIN_TIME = 0
        logging.warning("Could not read MIN_TIME; defaulting to 0")

try:
    SAFE_TIME = int(config_constants.get("FUSION", {}).get("SAFE_TIME", 0))
except Exception:
    try:
        SAFE_TIME = int(config_constants["FUSION"]["SAFE_TIME"])
    except Exception:
        SAFE_TIME = 0
        logging.warning("Could not read SAFE_TIME; defaulting to 0")

parser = argparse.ArgumentParser()
parser.add_argument("title")
parser.add_argument("provider_iptv_recorded")
parser.add_argument("provider_iptv_backup")
parser.add_argument("provider_iptv_backup_2")
args = parser.parse_args()

# Ensure logs dir exists and use sanitized title in log name
safe_title = sanitize_filename(args.title)
logs_dir = Path.home() / ".local" / "share" / "iptvselect-fr" / "logs"
try:
    logs_dir.mkdir(parents=True, exist_ok=True)
except Exception:
    # continue, file open will surface an error
    pass

logging.basicConfig(
    filename=str(logs_dir / "fusion.log"),
    format="%(asctime)s %(levelname)s: %(message)s",
    level=logging.INFO,
)

# Base paths (use sanitized title for FS operations)
base_videos = Path(f"/home/{user}/videos_select")
base = base_videos / f"{safe_title}-save"

# Informational lists
first_movies = []
providers_list = []

# ---------- Provider 1 ----------
# Pattern used only for fns of filesystem listing; sanitize the parts that go into filenames
pattern1 = f"{safe_title}_{args.provider_iptv_recorded}_*_original*"

if not base.is_dir():
    lst_movies_1 = []
else:
    try:
        files = [p for p in base.glob(pattern1) if p.is_file()]
        files.sort(key=lambda p: p.stat().st_mtime)
        lst_movies_1 = [p.name for p in files]
    except Exception:
        logging.exception("Failed enumerating files for pattern %s in %s", pattern1, base)
        lst_movies_1 = []

if len(lst_movies_1) == 0:
    logging.info(
        "Le fournisseur d'IPTV %s n'a fourni aucune vidéo pour le film %s.",
        args.provider_iptv_recorded, args.title
    )
else:
    starts_1 = []
    start_file_1 = base / f"start_time_{safe_title}_{args.provider_iptv_recorded}_original.txt"
    try:
        with start_file_1.open("r", encoding="utf-8") as f:
            for line in f:
                starts_1.append(line.strip())
    except FileNotFoundError:
        logging.info(
            "Le fichier %s est absent. La fusion des vidéos ne peut pas être réalisée",
            start_file_1
        )
        exit()
    except Exception:
        logging.exception("Failed reading start times from %s", start_file_1)
        exit()

    list_movies_1 = []
    for a, b in zip(lst_movies_1, starts_1):
        video_path = base / a
        cmd = [
            "ffprobe",
            "-i", str(video_path),
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-hide_banner",
            "-of", "default=noprint_wrappers=1:nokey=1",
        ]
        process = run_subprocess(cmd)
        stdout = getattr(process, "stdout", "")
        stderr = getattr(process, "stderr", "")
        try:
            video_duration = int(float(stdout.strip()))
        except Exception:
            logging.warning("ffprobe failed or returned invalid duration for %s: %s", video_path, stderr)
            continue

        try:
            start_time = int(b.strip())
        except Exception:
            logging.warning("Invalid start time %r for file %s, skipping", b, a)
            continue

        list_movies_1.append((start_time, video_duration, start_time + video_duration, a))

    # remove short movies (in-place safe iteration)
    filtered = []
    for movie in list_movies_1:
        if movie[1] >= 80:
            filtered.append(movie)
    list_movies_1 = filtered

    if len(list_movies_1) > 0:
        first_movies.append(list_movies_1[0])
        providers_list.append(list_movies_1)

# ---------- Provider 2 ----------
list_movies_2 = []

if args.provider_iptv_backup != "no_backup":
    pattern2 = f"{safe_title}_{args.provider_iptv_backup}_*_backup*"
    if not base.is_dir():
        lst_movies_2 = []
    else:
        try:
            files = [p for p in base.glob(pattern2) if p.is_file()]
            files.sort(key=lambda p: p.stat().st_mtime)
            lst_movies_2 = [p.name for p in files]
        except Exception:
            logging.exception("Failed enumerating files for pattern %s in %s", pattern2, base)
            lst_movies_2 = []

    if len(lst_movies_2) == 0:
        logging.info(
            "Le fournisseur d'IPTV %s n'a fourni aucune vidéo pour le film %s.",
            args.provider_iptv_backup, args.title
        )
    else:
        starts_2 = []
        start_file_2 = base / f"start_time_{safe_title}_{args.provider_iptv_backup}_backup.txt"
        try:
            with start_file_2.open("r", encoding="utf-8") as f:
                for line in f:
                    starts_2.append(line.strip())
        except FileNotFoundError:
            logging.info("Le fichier %s est absent. La fusion des vidéos ne peut pas être réalisée", start_file_2)
            exit()
        except Exception:
            logging.exception("Failed reading start times from %s", start_file_2)
            exit()

        for a, b in zip(lst_movies_2, starts_2):
            video_path = base / a
            cmd = [
                "ffprobe",
                "-i", str(video_path),
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-hide_banner",
                "-of", "default=noprint_wrappers=1:nokey=1",
            ]
            process = run_subprocess(cmd)
            try:
                video_duration = int(float(getattr(process, "stdout", "").strip()))
            except Exception:
                logging.warning("ffprobe failed or returned invalid duration for %s: %s", video_path, getattr(process, "stderr", ""))
                continue

            try:
                start_time = int(b.strip())
            except Exception:
                logging.warning("Invalid start time %r for file %s, skipping", b, a)
                continue

            list_movies_2.append((start_time, video_duration, start_time + video_duration, a))

        filtered2 = []
        for movie in list_movies_2:
            if movie[1] >= 80:
                filtered2.append(movie)
        list_movies_2 = filtered2

        if len(list_movies_2) > 0:
            first_movies.append(list_movies_2[0])
            providers_list.append(list_movies_2)

# ---------- Provider 3 ----------
list_movies_3 = []

if args.provider_iptv_backup_2 != "no_backup_2":
    pattern3 = f"{safe_title}_{args.provider_iptv_backup_2}_*_backup_2*"
    if not base.is_dir():
        lst_movies_3 = []
    else:
        try:
            files = [p for p in base.glob(pattern3) if p.is_file()]
            files.sort(key=lambda p: p.stat().st_mtime)
            lst_movies_3 = [p.name for p in files]
        except Exception:
            logging.exception("Failed enumerating files for pattern %s in %s", pattern3, base)
            lst_movies_3 = []

    if len(lst_movies_3) == 0:
        logging.info(
            "Le fournisseur d'IPTV %s n'a fourni aucune vidéo pour le film %s.",
            args.provider_iptv_backup_2, args.title
        )
    else:
        starts_3 = []
        start_file_3 = base / f"start_time_{safe_title}_{args.provider_iptv_backup_2}_backup_2.txt"
        try:
            with start_file_3.open("r", encoding="utf-8") as f:
                for line in f:
                    starts_3.append(line.strip())
        except FileNotFoundError:
            logging.info("Le fichier %s est absent. La fusion des vidéos ne peut pas être réalisée", start_file_3)
            exit()
        except Exception:
            logging.exception("Failed reading start times from %s", start_file_3)
            exit()

        for a, b in zip(lst_movies_3, starts_3):
            video_path = base / a
            cmd = [
                "ffprobe",
                "-i", str(video_path),
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-hide_banner",
                "-of", "default=noprint_wrappers=1:nokey=1",
            ]
            process = run_subprocess(cmd)
            try:
                video_duration = int(float(getattr(process, "stdout", "").strip()))
            except Exception:
                logging.warning("ffprobe failed or returned invalid duration for %s: %s", video_path, getattr(process, "stderr", ""))
                continue

            try:
                start_time = int(b.strip())
            except Exception:
                logging.warning("Invalid start time %r for file %s, skipping", b, a)
                continue

            list_movies_3.append((start_time, video_duration, start_time + video_duration, a))

        filtered3 = []
        for movie in list_movies_3:
            if movie[1] >= 80:
                filtered3.append(movie)
        list_movies_3 = filtered3

        if len(list_movies_3) > 0:
            first_movies.append(list_movies_3[0])
            providers_list.append(list_movies_3)

# ---------- Validate available providers ----------
if len(first_movies) == 1:
    logging.info(
        "Un seul fournisseur d'IPTV a pu permettre d'enregistrer des vidéos. La fusion des vidéos ne peut pas être réalisée."
    )
    exit()
elif len(first_movies) == 0:
    logging.info(
        "Aucun fournisseur d'IPTV n'a pu permettre d'enregistrer des vidéos. La fusion des vidéos ne peut pas être réalisée."
    )
    exit()

# ---------- Make a list of movies ----------
streams_best = []
list_movies = []
for list_movie in providers_list:
    for movie in list_movie:
        list_movies.append(movie)

max_end = 0
for movie in list_movies:
    end = movie[2]
    if end > max_end:
        max_end = end

continuum = True
last_continuous = []

while continuum:
    if len(streams_best) == 0:
        start_vals = [movie[0] for movie in list_movies]
        if not start_vals:
            break
        index_min = [i for i, j in enumerate(start_vals) if j == min(start_vals)][0]
        streams_best.append(list_movies[index_min])
        list_movies.remove(list_movies[index_min])
    else:
        continuous = []
        for movie in list_movies:
            if movie[0] < streams_best[-1][2] < movie[2]:
                continuous.append(movie)
        if continuous == last_continuous:
            break
        if len(continuous) > 0:
            end_vals = [m[2] for m in continuous]
            index_max = [i for i, j in enumerate(end_vals) if j == max(end_vals)][0]
            streams_best.append(continuous[index_max])
            list_movies.remove(continuous[index_max])
        else:
            continuum = False
        last_continuous = continuous[:]

movies_remaster = [streams_best[0][3]]

for n in range(len(streams_best) - 1):
    diff_time = streams_best[n][2] - streams_best[n + 1][0]
    file_path = base / streams_best[n + 1][3]

    cmd = [
        "ffprobe",
        "-i", str(file_path),
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        "-hide_banner",
    ]
    process = run_subprocess(cmd)

    if getattr(process, "returncode", 1) != 0:
        logging.warning("ffprobe failed: %s", getattr(process, "stderr", ""))
        start_time_value = 0.0
    else:
        try:
            data = json.loads(getattr(process, "stdout", "") or "{}")
            start_time_value = float(data.get("streams", [{}])[0].get("start_time", 0.0))
        except Exception:
            logging.warning("Could not parse start_time from ffprobe output for %s", file_path)
            start_time_value = 0.0

    if diff_time > MIN_TIME:
        start = int(start_time_value) + diff_time - SAFE_TIME
    else:
        start = int(start_time_value)

    logging.info("start_time: %s", start)

    orig_filename = streams_best[n + 1][3]
    file1 = base / orig_filename

    file2_base = Path(orig_filename).stem
    out_file = base / f"{file2_base}_s.ts"

    split_logs = logs_dir / "split_infos.log"
    try:
        with split_logs.open("ab") as f:
            cmd = [
                "ffmpeg",
                "-seek_timestamp", "1",
                "-ss", str(start),
                "-i", str(file1),
                "-y",
                "-c", "copy",
                "-copyts",
                "-to", "10000000",
                "-muxdelay", "0",
                str(out_file),
                "-loglevel", "quiet",
            ]
            result = run_subprocess(cmd)
            # write ffmpeg stdout/stderr to log for troubleshooting
            try:
                if getattr(result, "stdout", None):
                    f.write((result.stdout or "").encode("utf-8", errors="ignore"))
                if getattr(result, "stderr", None):
                    f.write((result.stderr or "").encode("utf-8", errors="ignore"))
            except Exception:
                # if writing binary fails, continue
                pass
    except Exception:
        logging.exception("Failed to run ffmpeg split for %s -> %s", file1, out_file)
        # still add something so logic stays consistent
        movies_remaster.append(str(out_file))
        continue

    if getattr(result, "returncode", 1) != 0:
        try:
            with split_logs.open("a", encoding="utf-8") as f_text:
                f_text.write(f"\nffmpeg failed for {file1} with return code {getattr(result, 'returncode', 'n/a')}\n")
        except Exception:
            pass

    movies_remaster.append(out_file.name)

# ---------- Copy remastered movies to to-watch dir ----------
rank = 1
to_watch_dir = base / f"{safe_title}-to-watch"
try:
    to_watch_dir.mkdir(parents=True, exist_ok=True)
except Exception:
    logging.exception("Failed to create to-watch dir %s", to_watch_dir)

for stream in movies_remaster:
    src = base / stream
    dest_name = f"{rank}_{Path(stream).name}"
    dest = to_watch_dir / dest_name
    try:
        shutil.copy2(src, dest)
    except FileNotFoundError:
        logging.warning("Source file not found: %s", src)
    except PermissionError:
        logging.warning("Permission denied copying %s -> %s", src, dest)
    except Exception as exc:
        logging.exception("Failed to copy %s -> %s: %s", src, dest, exc)
    rank += 1

# ---------- Write report ----------
report_dir = base / f"{safe_title}-to-watch"
try:
    report_dir.mkdir(parents=True, exist_ok=True)
except Exception:
    logging.exception("Failed to ensure report dir exists: %s", report_dir)

report_file = report_dir / f"{safe_title}_report.txt"
try:
    report_file.touch(exist_ok=True)
except Exception as exc:
    logging.exception("Failed to create report file %s: %s", report_file, exc)

try:
    with report_file.open("w", encoding="utf-8") as ini:
        if streams_best and streams_best[-1][2] < max_end - 300:
            ini.write("\nAttention! Une discontinuité de l'enregistrement apparait pour cette vidéo.\n")
        else:
            ini.write("\nL'enregistrement semble être correcte.\n")
except Exception:
    logging.exception("Failed to write report file %s", report_file)

# ---------- Delete zero-size / duplicate-size files ----------
lst_movies = []
if base.is_dir():
    try:
        for f in base.iterdir():
            if f.is_file():
                try:
                    lst_movies.append((f.stat().st_size, str(f)))
                except Exception:
                    continue
    except Exception:
        logging.exception("Failed iterating base dir %s", base)

movies_sorted = sorted(lst_movies, key=lambda x: x[0])

todelete = []
sizes = []
for size, title in movies_sorted:
    if size == 0:
        todelete.append(title)
    else:
        sizes.append(size)
        if sizes.count(size) > 5:
            todelete.append(title)

# Resolve base_dir safely and ensure deletes happen inside it
base_dir = base_videos.resolve()

for movie in todelete:
    p = Path(movie)
    try:
        target = p.resolve(strict=False)
    except Exception:
        logging.warning("Cannot resolve path %r, skipping", movie)
        continue

    if not is_within_base(base_dir, target):
        logging.warning("Skipping path outside base dir: %s", target)
        continue

    try:
        if target.is_symlink() or target.is_file():
            target.unlink()
            logging.info("Removed file: %s", target)
        elif target.is_dir():
            shutil.rmtree(target)
            logging.info("Removed directory tree: %s", target)
        else:
            logging.warning("Not a file or directory, skipping: %s", target)
    except FileNotFoundError:
        logging.warning("File not found (already removed?): %s", target)
    except PermissionError:
        logging.warning("Permission denied removing: %s", target)
    except Exception:
        logging.exception("Failed to remove %s", target)
