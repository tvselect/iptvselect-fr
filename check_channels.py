import subprocess
import argparse
import time
import shutil
import signal
import logging
import os
import sys
import re

from datetime import datetime
from pathlib import Path

user = os.environ.get("USER")
if not user or "/" in user or "\\" in user:
    logging.error("Invalid or undefined USER environment variable.")
    sys.exit(1)

# ---------------- Logging ----------------
log_dir = Path.home() / ".local/share/iptvselect-fr/logs"
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=log_dir / "check_channels.log",
    format="%(asctime)s %(levelname)s: %(message)s",
    level=logging.INFO,
    filemode="a",
)

# ---------------- Argument Parsing ----------------
parser = argparse.ArgumentParser()
parser.add_argument("iptv_provider")
args = parser.parse_args()

# ---------------- Validate IPTV provider input ----------------
VALID_FILENAME = re.compile(r"^[A-Za-z0-9._-]+$")
iptv_provider_safe = args.iptv_provider.rstrip("_junk")
if not VALID_FILENAME.match(iptv_provider_safe):
    logging.error(f"Invalid provider name: {iptv_provider_safe}")
    sys.exit(1)

if args.iptv_provider.endswith("_junk"):
    iptv_provider = args.iptv_provider[:-5]
else:
    iptv_provider = args.iptv_provider

# ---------------- Prepare videos directory ----------------
videos_dir = Path.home() / "videos_select"
videos_tests = videos_dir / "videos_tests"
created = False
if not videos_tests.exists():
    try:
        videos_tests.mkdir(parents=True, exist_ok=True)
        created = True
    except OSError as e:
        print(f"Erreur lors de la création du dossier: {e!s}")

if created:
    print("\nLe dossier videos_select/videos_tests a été créé dans votre dossier home.\n")

# ---------------- Helper: Check file ownership ----------------
def ensure_owned_by_user(path: Path):
    if not path.exists():
        logging.error(f"File not found: {path}")
        sys.exit(1)
    try:
        if path.stat().st_uid != os.getuid():
            logging.error(f"File {path} is not owned by the current user.")
            sys.exit(1)
    except OSError as e:
        logging.error(f"Cannot stat {path}: {e}")
        sys.exit(1)

# ---------------- Original provider file ----------------
base_config_dir = Path("/home") / user / ".config" / "iptvselect-fr" / "iptv_providers"
original_file = base_config_dir / f"{iptv_provider}_original_m3ulinks.ini"
ensure_owned_by_user(original_file)

provider = original_file.name
if provider != iptv_provider + "_original_m3ulinks.ini":
    print(
        f"Le fournisseur {iptv_provider} que vous avez renseigné ne possède "
        f"pas de fichier nommé {iptv_provider}_original_m3ulinks.ini ."
        f"Veuillez créer ce fichier soit en exécutant les scripts fill_ini.py ou "
        f"install_iptv.py ou alors en copiant le fichier {iptv_provider}.ini "
        f"en le renommant {iptv_provider}_original_m3ulinks.ini "
    )
    sys.exit(1)

# ---------------- User selects recorder ----------------
answers_apps = [1, 2, 3, 4]
provider_recorder = 666
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

# ---------------- Read original m3u links ----------------
with open(original_file, "r", encoding="utf-8") as ini:
    first_line = ini.readline()
    lines = ini.read().splitlines()

# ---------------- Junk file management ----------------
junk_file = base_config_dir / f"{iptv_provider}_junk.ini"
junk_last_file = base_config_dir / f"{iptv_provider}_junk_last.ini"
if junk_file.exists():
    try:
        rel_after_config = junk_file.resolve().as_posix().split(".config/iptvselect-fr/", 1)[1]
        prefix = "iptv_providers/"
        junk = rel_after_config[len(prefix):] if rel_after_config.startswith(prefix) else rel_after_config
    except IndexError:
        junk = ""
else:
    junk = ""
    logging.error(f"File not found: {junk_file}")

# ---------------- Copy junk to junk_last safely ----------------
home_user = Path("/home") / user
if junk == f"{iptv_provider}_junk.ini":
    try:
        junk_file.resolve().relative_to(home_user)
        junk_last_file.resolve().relative_to(home_user)
    except Exception:
        logging.error("Invalid path: source or destination is outside user's home.")
    else:
        if not junk_file.exists():
            logging.error(f"Source file not found: {junk_file}")
        else:
            try:
                shutil.copy2(junk_file, junk_last_file)
            except OSError as e:
                logging.error(f"Failed to copy {junk_file} -> {junk_last_file}: {e}")
else:
    try:
        junk_file.parent.mkdir(parents=True, exist_ok=True)
        junk_file.touch(exist_ok=True)
    except OSError as e:
        logging.error(f"Failed to touch {junk_file}: {e}")

# ---------------- Read junk lines if needed ----------------
check_junk = False
if args.iptv_provider.endswith("_junk"):
    with open(junk_file, "r", encoding="utf-8") as ini:
        first_line = ini.readline()
        junks_to_check = ini.read().splitlines()
    check_junk = True

lines_to_check = junks_to_check if check_junk else lines
file_to_check = "junk" if check_junk else "original_m3ulinks"

junkies = []
junkies_line = []

record_time = 60
number_m3u_links = sum(1 for line in lines_to_check if line != "" and line[-3:] != " = ")

print(
    f"Le programme de contrôle des chaines a démarré. Il "
    f"y a {number_m3u_links} chaînes à vérifier dans le fichier "
    f"{iptv_provider}_{file_to_check}.ini . Il faudra donc patienter "
    f"environ {round((number_m3u_links * record_time) / 60)} minutes.\n"
)

# ---------------- Record channels ----------------
for line in lines_to_check:
    if " = " in line:
        now = datetime.now().strftime("%Y-%m-%d-%H-%M")
        split = line.split(" = ")
        if split[1] != "":
            channel_formated = split[0].replace(" ", "_").replace("'", "_")
            output_dir = Path.home() / "videos_select" / "videos_tests"

            # ---------------- Recorder commands ----------------
            if provider_recorder == 1:
                cmd = [
                    "ffmpeg", "-y", "-i", split[1],
                    "-map", "0:v", "-map", "0:a", "-map", "0:s?",
                    "-c:v", "copy", "-c:a", "copy", "-c:s", "copy",
                    "-t", "60",
                    "-f", "mpegts",
                    "-reconnect", "1",
                    "-reconnect_streamed", "1",
                    "-reconnect_delay_max", "1",
                    "-reconnect_at_eof",
                    str(output_dir / f"{iptv_provider}_{now}_{channel_formated}.ts")
                ]
                log_path = output_dir / f"{iptv_provider}_{now}_{channel_formated}_test.log"

            elif provider_recorder == 2:
                cmd = [
                    "cvlc", "-v", split[1],
                    "--run-time", "60",
                    f"--sout=file/ts:{output_dir / f'{iptv_provider}_{now}_{channel_formated}.ts'}"
                ]
                log_path = output_dir / f"{iptv_provider}_{now}_{channel_formated}_test.log"

            elif provider_recorder == 3:
                cmd = [
                    "mplayer", split[1],
                    "-dumpstream",
                    "-dumpfile",
                    str(output_dir / f"{iptv_provider}_{now}_{channel_formated}.ts")
                ]
                log_path = output_dir / f"{iptv_provider}_{now}_{channel_formated}_test.log"

            else:
                cmd = [
                    str(Path.home() / ".local/share/iptvselect-fr/.venv/bin/streamlink"),
                    "--ffmpeg-validation-timeout", "15.0",
                    "--http-no-ssl-verify", "--hls-live-restart",
                    "--stream-segment-attempts", "100", "--retry-streams", "1",
                    "--retry-max", "100", "--stream-segmented-duration", "60",
                    "-o", str(output_dir / f"{iptv_provider}_{now}_{channel_formated}.ts"),
                    "-f", split[1], "best"
                ]
                log_path = output_dir / f"{iptv_provider}_{now}_{channel_formated}_test.log"

            with open(log_path, "a", encoding="utf-8") as logfile:
                subprocess.Popen(cmd, stdout=logfile, stderr=subprocess.STDOUT)

            time.sleep(record_time)

            # ---------------- Kill lingering processes ----------------
            if 2 <= provider_recorder <= 3:
                search_pattern = f"{iptv_provider}_{now}_{channel_formated}.ts"
                ps = subprocess.run(["ps", "-ef"], stdout=subprocess.PIPE, text=True)
                matching_pids = []
                for ps_line in ps.stdout.splitlines():
                    if search_pattern in ps_line:
                        parts = ps_line.split()
                        if len(parts) > 1:
                            try:
                                matching_pids.append(int(parts[1]))
                            except ValueError:
                                pass
                if len(matching_pids) >= 2:
                    pid_to_kill = matching_pids[1]
                    try:
                        os.kill(pid_to_kill, signal.SIGTERM)
                    except ProcessLookupError:
                        print(f"Process {pid_to_kill} no longer exists")

            # ---------------- File size check ----------------
            p = output_dir / f"{iptv_provider}_{now}_{channel_formated}.ts"
            try:
                size_bytes = p.stat().st_size
                file_size = (size_bytes + 1023) // 1024
            except (FileNotFoundError, OSError) as e:
                logging.error(f"Failed to stat {p}: {e}")
                file_size = 10

            if file_size < 1000:
                print(f"La chaine {split[0]} n'a pas été enregistrée!!!!!!")
                junkies.append((split[0], split[1]))
                junkies_line.append(f"{split[0]} = {split[1]}")
            else:
                print(f"La chaine {split[0]} a pu être enregistrée.")

# ---------------- Write junk.ini ----------------
with open(base_config_dir / f"{iptv_provider}_junk.ini", "w", encoding="utf-8") as ini:
    ini.write("[CHANNELS]\n")
    for line in junkies_line:
        ini.write(line + "\n")

if junkies:
    print("\nLes chaînes qui ne fonctionnent pas par rapport au fichier original de liens m3u sont:\n")
    for junk in junkies:
        print(junk[0])

# ---------------- Compare junk_last ----------------
junk_last_path = junk_last_file
repaired = []

if junk_last_path.exists() and junk_last_path.name == f"{iptv_provider}_junk_last.ini":
    with open(junk_last_path, "r", encoding="utf-8") as ini:
        first_line = ini.readline()
        last_junks = ini.read().splitlines()
    for junk in last_junks:
        if junk not in junkies_line:
            split = junk.split(" = ")
            repaired.append(split[0])

    if repaired:
        print(f"\nLes chaînes qui sont de nouveau fonctionnelles depuis le dernier contrôle des chaines du fournisseur d'IPTV {iptv_provider} sont:\n")
        for repair in repaired:
            print(repair)
    else:
        print(f"\nAucune chaine n'a été réparée depuis le dernier contrôle des chaines du fournisseur d'IPTV {iptv_provider}.")

    new_junk = [j for j in junkies_line if j not in last_junks]
    if not check_junk and new_junk:
        print(f"\nLes chaînes qui ne sont plus fonctionnelles depuis le dernier contrôle des chaines du fournisseur d'IPTV {iptv_provider} sont:\n")
        for junk in new_junk:
            print(junk.split(" = ")[0])
    elif not check_junk and not new_junk:
        print(f"\nAucune nouvelle chaine apparait comme endommagée depuis le dernier contrôle des chaines du fournisseur d'IPTV {iptv_provider}.")

# ---------------- Rewrite original ini ----------------
with open(base_config_dir / f"{iptv_provider}.ini", "w", encoding="utf-8") as ini:
    ini.write("[CHANNELS]\n")
    for line in lines:
        if line not in junkies_line:
            ini.write(line + "\n")
        else:
            split = line.split(" = ")
            ini.write(f"{split[0]} = \n")

if (not check_junk and junkies_line) or (check_junk and repaired):
    print(f"\nLe fichier {iptv_provider}.ini vient d'être reconfiguré.")
