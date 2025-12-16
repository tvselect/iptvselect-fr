import getpass
import glob
import keyring
import os
import random
import readline
import requests
import tempfile
import subprocess
import shutil
import stat
import pathlib
import errno

from requests.exceptions import ConnectTimeout, ConnectionError, RequestException
from time import sleep

def create_dir_with_permissions(path, mode):
    """
    Creates a directory if it doesn't exist and sets the desired permissions.
    Updates the permissions if the directory already exists.

    Parameters:
        path (str): The directory path to create or check.
        mode (int): The permission mode to set (e.g., 0o740).
    """
    path_obj = pathlib.Path(path).expanduser()
    try:
        if not path_obj.exists():
            # umask may interfere; set permissions explicitly after creation
            path_obj.mkdir(parents=True, exist_ok=True)
            os.chmod(str(path_obj), mode)
            print(f"Directory created: {path}")
        else:
            # ensure permissions are at least as strict as requested
            current = stat.S_IMODE(os.stat(str(path_obj)).st_mode)
            if current != mode:
                os.chmod(str(path_obj), mode)
            print(f"Directory already exists: {path}")
    except OSError as e:
        print(f"Failed to create or set permissions on {path}: {e}")
        raise

def get_gpg_keys():
    """Lists GPG keys with cryptographic method and key strength."""
    cmd = ["gpg", "--list-keys", "--with-colons"]

    try:
        output = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError:
        print("Error retrieving GPG keys.")
        return []

    keys = []
    for line in output.splitlines():
        parts = line.split(":")
        if parts[0] == "pub":  # Public key entry
            # guard against malformed output
            try:
                key_size = int(parts[2])
                key_type = parts[3]
                key_id = parts[4][-8:]
            except (IndexError, ValueError):
                continue

            # Determine key type and strength
            if key_type == "1":
                algo = "RSA"
                secure = key_size >= 4096
            elif key_type == "16":
                algo = "ElGamal"
                secure = False
            elif key_type == "17":
                algo = "DSA"
                secure = False
            elif key_type == "18":
                algo = "ECDSA"
                secure = key_size >= 256
            elif key_type == "19":
                algo = "Ed25519"
                secure = True
            elif key_type == "22":
                algo = "Curve25519"
                secure = True
            else:
                algo = f"Unknown ({key_type})"
                secure = False

            if secure:
                keys.append((key_id, algo, key_size))

    return keys

home_dir = os.path.expanduser("~")

videos_select_path = os.path.join(home_dir, "videos_select")
try:
    if not os.path.isdir(videos_select_path):
        os.makedirs(videos_select_path, exist_ok=True)
        os.chmod(videos_select_path, 0o700)
        print("Le dossier videos_select a été créé dans votre dossier home.\n")
except OSError as e:
    print(f"Erreur lors de la création de {videos_select_path}: {e}")
    raise

permission_mode = 0o700

# create required directories with explicit permissions
create_dir_with_permissions(os.path.expanduser("~/.local"), permission_mode)
create_dir_with_permissions(os.path.expanduser("~/.local/share"), permission_mode)
create_dir_with_permissions(os.path.expanduser("~/.local/share/iptvselect-fr"), permission_mode)
create_dir_with_permissions(os.path.expanduser("~/.local/share/iptvselect-fr/logs"), permission_mode)
create_dir_with_permissions(os.path.expanduser("~/.config"), permission_mode)
create_dir_with_permissions(os.path.expanduser("~/.config/iptvselect-fr"), permission_mode)
create_dir_with_permissions(os.path.expanduser("~/.config/iptvselect-fr/iptv_providers"), permission_mode)


print(
    "\nLes dossiers ~/.config/iptvselect-fr/iptv_providers et "
    "~/.local/share/iptvselect-fr/logs ont été créés.\n"
)

src = os.path.expanduser("~/iptvselect-fr/constants.ini")
dest_dir = os.path.expanduser("~/.config/iptvselect-fr")
dest = os.path.join(dest_dir, "constants.ini")

try:
    if not os.path.isfile(dest):
        if os.path.isfile(src):
            shutil.copy2(src, dest)
            os.chmod(dest, 0o640)
            print(f"Le fichier {src} a été copié vers {dest}.\n")
        else:
            print(f"Fichier source manquant : {src} — impossible de copier constants.ini.")
    else:
        print(f"Le fichier constants.ini existe déjà dans {dest}.\n")
except (OSError, shutil.Error) as e:
    print(f"Erreur lors de la copie de constants.ini : {e}")

# copy provider files but guard against missing pattern
src_path = os.path.expanduser("~/iptvselect-fr/iptv_providers/freeboxtv*")
dest_dir = os.path.expanduser("~/.config/iptvselect-fr/iptv_providers")
files_copied = 0
for file in glob.glob(src_path):
    try:
        shutil.copy2(file, dest_dir)
        files_copied += 1
    except (OSError, shutil.Error) as e:
        print(f"Failed to copy {file} -> {dest_dir}: {e}")
if files_copied:
    print(
        "Les fichiers freeboxtv pour les abonnés Free ont été copiés "
        "dans le dossier ~/.config/iptvselect-fr/iptv_providers .\n"
    )
else:
    print("Aucun fichier freeboxtv trouvé à copier.\n")

print("Configuration des tâches cron du programme IPTV-select:\n")

timeout = 6

try:
    response = requests.head("https://iptv-select.fr", timeout=timeout)
    response.raise_for_status()
except ConnectTimeout:
    print(f"Connection to IPTV-select.fr timed out after {timeout} seconds")
    exit(1)
except ConnectionError:
    print("Failed to connect to IPTV-select.fr")
    exit(1)
except RequestException as e:
    print(f"Request failed: {e}")
    exit(1)

http_response = response.status_code

if http_response != 200:
    print(
        "\nLa box IPTV-select n'est pas connectée à internet. Veuillez "
        "vérifier votre connection internet et relancer le programme "
        "d'installation.\n\n"
    )
    exit(1)

user = os.environ.get("USER") or getpass.getuser()

user = str(user).strip()
if "\n" in user or "\r" in user or user == "":
    raise SystemExit("Invalid USER environment variable detected; aborting for safety.")

answers = ["oui", "non"]

crypted = "no_se"

while crypted.lower() not in answers:
    crypted = input(
        "\nVoulez vous chiffrer les identifiants de connection à "
        "l'application web IPTV-select.fr? Si vous répondez oui, "
        "il faudra penser à débloquer gnome-keyring (ou tout "
        "autre backend disponible sur votre système) à chaque "
        "nouvelle session afin de permettre l'accès aux "
        "identifiants par l'application IPTV-select-fr. "
        "(répondre par oui ou non) : "
    ).strip().lower()

config_path = os.path.join("/home", user, ".config/iptvselect-fr/config.py")
template_path = os.path.join("/home", user, "iptvselect-fr/config_template.py")

# create config by copying template atomically and set secure mode
try:
    if not os.path.exists(config_path):
        if os.path.isfile(template_path):
            # write to temp file then atomically replace
            with tempfile.NamedTemporaryFile("w", delete=False, dir=os.path.dirname(config_path)) as tf:
                tf_name = tf.name
                with open(template_path, "r") as tpl:
                    tf.write(tpl.read())
            os.replace(tf_name, config_path)
            os.chmod(config_path, 0o640)
        else:
            print(f"Template missing: {template_path}; cannot create config.")
except OSError as e:
    print(f"Error creating config at {config_path}: {e}")

# generate random times
heure = random.randint(6, 23)
minute = random.randint(0, 58)
minute_2 = minute + 1
heure_auto_update = heure - 1
minute_auto_update = random.randint(0, 59)

params = ["CRYPTED_CREDENTIALS", "CURL_HOUR", "CURL_MINUTE"]

# Write config values securely using atomic write
conf_lines = []
for param in params:
    if "CRYPTED_CREDENTIALS" in param:
        conf_lines.append(f"CRYPTED_CREDENTIALS = {crypted.lower() == 'oui'}\n")
    elif "CURL_HOUR" in param:
        conf_lines.append(f"{param} = {heure}\n")
    elif "CURL_MINUTE" in param:
        conf_lines.append(f"{param} = {minute}\n")

try:
    conf_dir = os.path.dirname(config_path)
    os.makedirs(conf_dir, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=conf_dir) as tf:
        tf.write("".join(conf_lines))
        tmpname = tf.name
    # set secure permissions and replace atomically
    os.chmod(tmpname, 0o600)
    os.replace(tmpname, config_path)
except OSError as e:
    print(f"Failed to write config values to {config_path}: {e}")

hdmi_screen = "no_se"

if crypted.lower() == "oui":
    ssh_connection = os.environ.get("SSH_CONNECTION")
    display_available = os.environ.get("DISPLAY")
    if ssh_connection is not None or not display_available:
        while hdmi_screen.lower() not in answers:
            hdmi_screen = input(
                "\nVous êtes connecté en SSH à votre machine ou votre système pourrait ne "
                "pas avoir d'interface graphique. Avez-vous accès à une interface graphique? "
                "Répondez 'oui' si vous pouvez connecter un écran et visualiser les applications, "
                "ou 'non' si vous ne pouvez vous connecter que via SSH ou si aucune interface graphique n'est disponible"
                "(exemple: VM, carte Nanopi-NEO, server, OS sans interface graphique): "
            ).strip().lower()
    else:
        hdmi_screen = "oui"

    if hdmi_screen == "non":
        gpg_keys = get_gpg_keys()
        if not gpg_keys:
            print(
                "Aucune clé GPG suffisament sécurisé n'est détectée dans votre système. Vous pouvez ajouter une clé GPG "
                "à votre trousseau de clés pour chiffrer vos identifiants en utilisant "
                "la commande suivante pour générer une nouvelle clé GPG: "
                "\n\ngpg --full-generate-key\nVous pouvez suivre le tutoriel suivant pour ajouter "
                "la clé GPG sécurisé: https://iptv-select.fr/advice-gpg puis relancez le programme d'installation."
            )
            exit(1)
        else:
            print("Voici la liste de vos clés GPG qui sont assez sécurisées pour chiffrer vos identifiants de connexion:")
            for index, (key_id, algo, key_size) in enumerate(gpg_keys, start=1):
                print(f"{index}) Key ID: {key_id}, Algorithm: {algo}, Size: {key_size} bits")
            if len(gpg_keys) > 1:
                selected_key = 0
                while not (1 <= selected_key <= len(gpg_keys)):
                    try:
                        selected_key = int(input(f"Merci de choisir un nombre entre 1 et {len(gpg_keys)} "
                                                "pour sélectionner la clé de chiffrement GPG à utiliser: "))
                    except ValueError:
                        print("Veuillez entrer un nombre valide.")
            else:
                selected_key = 1

            # initialize pass with the chosen key, check returncode
            try:
                proc = subprocess.run(
                    ["pass", "init", gpg_keys[selected_key - 1][0]],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if proc.returncode != 0:
                    print(f"pass init failed: {proc.stderr.strip()}")
            except FileNotFoundError:
                print("Le gestionnaire 'pass' n'est pas installé ou non trouvé dans PATH.")
                exit(1)

http_status = 403

if hdmi_screen == "non":
    sleep(1)
    print(
        "Veuillez saisir l'email de votre compte à IPTV-select.fr. L'email "
        "ne sera pas visible par mesure de sécurité et devra être répété "
        "une 2ème fois pour s'assurer d'avoir saisi l'email correctement. S'"
        "il vous est posé la question 'An entry already exists for "
        "iptv-select/email. Overwrite it? [y/N] y', répondez y"
    )
    try:
        insert_email = subprocess.run(["pass", "insert", "iptv-select/email"], check=False)
    except FileNotFoundError:
        print("Le gestionnaire 'pass' n'est pas installé ou non trouvé dans PATH.")
        exit(1)

    sleep(1)
    print(
        "Veuillez saisir le mot de passe de votre compte à IPTV-select.fr. "
        "Le mot de passe ne sera pas visible par mesure de sécurité et "
        "devra être répété une 2ème fois pour s'assurer d'avoir saisi "
        "l'email correctement. S'il vous est posé la question 'An entry already exists for "
        "iptv-select/password. Overwrite it? [y/N] y', répondez y"
    )
    try:
        insert_password = subprocess.run(["pass", "insert", "iptv-select/password"], check=False)
    except FileNotFoundError:
        print("Le gestionnaire 'pass' n'est pas installé ou non trouvé dans PATH.")
        exit(1)
else:
    username_iptvselect = input(
        "Veuillez saisir votre identifiant de connexion (adresse "
        "email) sur IPTV-select.fr: "
    ).strip()
    password_iptvselect = getpass.getpass(
        "Veuillez saisir votre mot de passe sur IPTV-select.fr: "
    )

# helper to safely read from 'pass' and return decoded text stripped
def run_pass_get(entry):
    try:
        p = subprocess.run(["pass", entry], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except FileNotFoundError:
        print("Le gestionnaire 'pass' n'est pas installé ou non trouvé dans PATH.")
        raise
    if p.returncode != 0:
        # it's possible pass returns non-zero when entry not found
        raise RuntimeError(f"'pass {entry}' failed: {p.stderr.strip()}")
    # pass prints a trailing newline; strip it, also protect against control chars
    value = p.stdout.strip()
    if "\n" in value or "\r" in value:
        # multi-line values are suspicious for credentials in this context
        raise ValueError("Unexpected multiline value returned from pass; aborting.")
    return value

while http_status != 200:

    if hdmi_screen == "non":
        try:
            username_iptvselect = run_pass_get("iptv-select/email")
            password_iptvselect = run_pass_get("iptv-select/password")
        except Exception as e:
            print(f"Failed to retrieve credentials from pass: {e}")
            try_again = input("Voulez-vous réessayer d'entrer les identifiants manuellement? (oui/non): ").strip().lower()
            if try_again != "oui":
                exit(1)
            else:
                username_iptvselect = input("Veuillez saisir de nouveau votre identifiant (email): ").strip()
                password_iptvselect = getpass.getpass("Veuillez saisir de nouveau votre mot de passe: ")

    timeout = 4

    try:
        response = requests.head(
            "https://www.iptv-select.fr/api/v1/prog",
            auth=(username_iptvselect, password_iptvselect),
            timeout=timeout,
        )
        response.raise_for_status()
    except ConnectTimeout:
        print(f"Connection to IPTV-select.fr timed out after {timeout} seconds")
        http_status = 0
        continue
    except ConnectionError:
        print("Failed to connect to IPTV-select.fr")
        http_status = 0
        continue
    except RequestException as e:
        if hasattr(e, "response") and e.response is not None:
            http_status = e.response.status_code
        else:
            print(f"Request failed: {e}")
            http_status = 0
        pass
    else:
        http_status = response.status_code

    if http_status != 200:
        try_again = input(
            "Le couple identifiant de connexion et mot de passe "
            "est incorrect.\nVoulez-vous essayer de nouveau?(oui ou non): "
        ).strip().lower()
        answer_hide = "maybe"
        if try_again.lower() == "oui":
            if hdmi_screen == "oui" or hdmi_screen == "no_se":
                username_iptvselect = input(
                    "Veuillez saisir de nouveau votre identifiant de connexion (adresse email) sur IPTV-select.fr: "
                ).strip()
                while answer_hide.lower() not in answers:
                    answer_hide = input(
                        "Voulez-vous afficher le mot de passe que vous saisissez "
                        "pour que cela soit plus facile? (répondre par oui ou non): "
                    ).strip().lower()
                if answer_hide.lower() == "oui":
                    password_iptvselect = input(
                        "Veuillez saisir de nouveau votre mot de passe sur IPTV-select.fr: "
                    )
                else:
                    password_iptvselect = getpass.getpass(
                        "Veuillez saisir de nouveau votre mot de passe sur IPTV-select.fr: "
                    )
            else:
                sleep(1)
                print(
                    "Veuillez saisir l'email de votre compte à IPTV-select.fr. L'email "
                    "ne sera pas visible par mesure de sécurité et devra être répété "
                    "une 2ème fois pour s'assurer d'avoir saisi l'email correctement."
                )
                try:
                    subprocess.run(["pass", "insert", "iptv-select/email"], check=False)
                except FileNotFoundError:
                    print("Le gestionnaire 'pass' n'est pas installé ou non trouvé dans PATH.")
                    exit(1)
                sleep(1)
                print(
                    "Veuillez saisir le mot de passe de votre compte à IPTV-select.fr. "
                    "Le mot de passe ne sera pas visible par mesure de sécurité et "
                    "devra être répété une 2ème fois pour s'assurer d'avoir saisi l'email correctement."
                )
                try:
                    subprocess.run(["pass", "insert", "iptv-select/password"], check=False)
                except FileNotFoundError:
                    print("Le gestionnaire 'pass' n'est pas installé ou non trouvé dans PATH.")
                    exit(1)
        else:
            exit(1)

# At this point credentials validated
netrc_path = os.path.expanduser("~/.netrc")
try:
    # create netrc if missing and set strict perms
    if not os.path.exists(netrc_path):
        # create file and set mode to 0o600
        open(netrc_path, "a").close()
        os.chmod(netrc_path, 0o600)
    else:
        # ensure perms are strict
        os.chmod(netrc_path, 0o600)
except OSError as e:
    print(f"Failed to create or set permissions on {netrc_path}: {e}")
    raise

try:
    with open(netrc_path, "r") as file:
        lines = file.read().splitlines()
except OSError:
    lines = []

# helper sanitizer to avoid newlines or injection
def sanitize_token(value):
    if value is None:
        return ""
    v = str(value).strip()
    if "\n" in v or "\r" in v:
        raise ValueError("Unsafe characters in token")
    return v

username_iptvselect_safe = sanitize_token(username_iptvselect)
password_iptvselect_safe = sanitize_token(password_iptvselect)

try:
    position = None
    for idx, line in enumerate(lines):
        if line.strip() == "machine www.iptv-select.fr":
            position = idx
            break
    if position is not None:
        # Replace next lines or append as needed
        if position + 1 < len(lines):
            lines[position + 1] = f"  login {username_iptvselect_safe}"
        else:
            lines.insert(position + 1, f"  login {username_iptvselect_safe}")
        if crypted.lower() == "non":
            pwd_line = f"  password {password_iptvselect_safe}"
        else:
            pwd_line = "  password XXXXXXXX"
        if position + 2 < len(lines):
            lines[position + 2] = pwd_line
        else:
            lines.insert(position + 2, pwd_line)
    else:
        lines.append("machine www.iptv-select.fr")
        lines.append(f"  login {username_iptvselect_safe}")
        if crypted.lower() == "non":
            lines.append(f"  password {password_iptvselect_safe}")
        else:
            lines.append("  password XXXXXXXX")
except ValueError as ve:
    print(f"Input sanitization error: {ve}")
    exit(1)

# Atomically write back to .netrc
try:
    dirpath = os.path.dirname(netrc_path)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=dirpath) as tf:
        for line in lines:
            tf.write(line + "\n")
        tmp_netrc = tf.name
    os.chmod(tmp_netrc, 0o600)
    os.replace(tmp_netrc, netrc_path)
except OSError as e:
    print(f"Failed to write to {netrc_path}: {e}")
    raise

# store in keyring only if local display available and crypted option chosen
if hdmi_screen == "oui" and crypted.lower() != "non":
    print(
        "Si votre système d'exploitation ne déverrouille pas automatiquement le trousseau de clés "
        "comme sur Raspberry OS, une fenêtre du gestionnaire du trousseau s'est ouverte et il vous "
        "faudra la débloquer en saisissant votre mot de passe. Si c'est la première ouverture "
        "de votre trousseau de clé, il vous sera demandé de créer un mot de passe qu'il faudra renseigner à chaque "
        "nouvelle session afin de permettre l'accès des identifiants chiffrés au programme iptvselect-fr."
    )
    try:
        keyring.set_password("iptv-select", "username", username_iptvselect_safe)
        keyring.set_password("iptv-select", "password", password_iptvselect_safe)
    except Exception as e:
        print(f"Failed to save credentials to keyring: {e}")

auto_update = "no_se"

while auto_update.lower() not in answers:
    auto_update = (
        input(
            "\n\nAutorisez-vous l'application à se mettre à jour automatiquement? "
            "(répondre par oui ou non) : "
        )
        .strip()
        .lower()
    )

# Export current crontab to a secure temp file
try:
    crontab_init = subprocess.Popen(["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = crontab_init.communicate()
    if crontab_init.returncode not in (0, 1):
        # 1 is often returned when no crontab exists -> acceptable
        print("Erreur lors de l'initialisation du cron: ", stderr.decode("utf-8"))
        print(
            "Le cron ne sera pas sauvegardé (ce qui est attendu si l'erreur "
            "reportée est no crontab for user)."
        )
except Exception as e:
    print(f"Failed to list crontab: {e}")
    stdout = b""

# write to a secure temporary file (binary) and keep name for later use
try:
    with tempfile.NamedTemporaryFile("wb", delete=False) as tf:
        tf_name = tf.name
        tf.write(stdout)
    # set strict perms on temp file
    os.chmod(tf_name, 0o600)
except OSError as e:
    print(f"Failed to create temporary crontab export: {e}")
    raise

# Read lines from the temp file
try:
    with open(tf_name, "r") as crontab_file:
        cron_lines = crontab_file.readlines()
except OSError as e:
    print(f"Failed to read temporary crontab file: {e}")
    cron_lines = []

curl = (
    "{minute} {heure} * * * env DBUS_SESSION_BUS_ADDRESS=unix:path=/run"
    "/user/$(id -u)/bus /bin/bash $HOME/iptvselect-fr/curl_"
    "iptvselect.sh\n".format(
        minute=minute,
        heure=heure,
    )
)

cron_launch = (
    "{minute_2} {heure} * * * export TZ='Europe/Paris' USER='{user}' && "
    "cd /home/$USER/iptvselect-fr && "
    "bash cron_launch_record.sh\n".format(user=user, minute_2=minute_2, heure=heure)
)

cron_auto_update = (
    '{minute_auto_update} {heure_auto_update} * * * /bin/bash -c "$HOME'
    "/iptvselect-fr/auto_update.sh >> $HOME/.local/share"
    '/iptvselect-fr/logs/auto_update.log 2>&1"\n'.format(
        minute_auto_update=minute_auto_update, heure_auto_update=heure_auto_update
    )
)

if hdmi_screen == "oui" or hdmi_screen == "no_se":
    cron_lines = [curl if "iptvselect-fr/curl_iptvselect.sh" in cron else cron for cron in cron_lines]
else:
    cron_lines = [cron for cron in cron_lines if "iptvselect-fr/curl_iptvselect.sh" not in cron]
cron_lines = [cron_launch if "iptvselect-fr &&" in cron else cron for cron in cron_lines]

if auto_update.lower() == "oui":
    cron_lines = [
        cron_auto_update if "iptvselect-fr/auto_update" in cron else cron
        for cron in cron_lines
    ]
else:
    cron_lines = [cron for cron in cron_lines if "iptvselect-fr/auto_update" not in cron]

cron_lines_join = "".join(cron_lines)

if (hdmi_screen == "oui" or hdmi_screen == "no_se") and "iptvselect-fr/curl_iptvselect.sh" not in cron_lines_join:
    cron_lines.append(curl)
if "cd /home/$USER/iptvselect-fr &&" not in cron_lines_join:
    cron_lines.append(cron_launch)

if auto_update.lower() == "oui" and "iptvselect-fr/auto_update" not in cron_lines_join:
    cron_lines.append(cron_auto_update)

try:
    with tempfile.NamedTemporaryFile("w", delete=False) as tf:
        for cron_task in cron_lines:
            tf.write(cron_task)
        tf_cron_name = tf.name
    os.chmod(tf_cron_name, 0o600)

    process = subprocess.run(["crontab", tf_cron_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode != 0:
        print(f"\n Error loading cron tasks: {process.stderr}")
    else:
        print("\n Cron tasks loaded successfully.")
except OSError as e:
    print(f"Failed to write crontab temporary file or load crontab: {e}")
    raise
finally:
    # cleanup temporary files
    for tmp in (tf_cron_name if 'tf_cron_name' in locals() else None, tf_name if 'tf_name' in locals() else None):
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass

print("\nLes tâches cron de votre box IPTV-select sont maintenant configurés!\n")
