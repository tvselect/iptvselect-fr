import subprocess
import readline
import random
import getpass
import os
import shutil
import glob
import requests

from pathlib import Path


def create_dir_with_permissions(path, mode):
    """
    Creates a directory if it doesn't exist and sets the desired permissions.
    Updates the permissions if the directory already exists.

    Parameters:
        path (str): The directory path to create or check.
        mode (int): The permission mode to set (e.g., 0o740).
    """
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        os.chmod(path, mode)
        print(f"Directory created: {path}")
    else:
        print(f"Directory already exists: {path}")


answers = ["oui", "non"]
answer = "maybe"

home_dir = os.path.expanduser("~")
output = subprocess.Popen(
    ["ls", home_dir], stdout=subprocess.PIPE, stderr=subprocess.PIPE
)
stdout, stderr = output.communicate()

ls_directory = ""
for line in stdout.decode("utf-8").splitlines():
    if line == "videos_select":
        ls_directory = line
        break

if ls_directory == "":
    directory_path = os.path.expanduser("~/videos_select")
    cmd = ["mkdir", directory_path]
    directory = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    directory.wait()
    print("Le dossier videos_select a été créé dans votre dossier home.\n")

permission_mode = 0o700

create_dir_with_permissions(os.path.expanduser("~/.local"), permission_mode)
create_dir_with_permissions(os.path.expanduser("~/.local/share"), permission_mode)
create_dir_with_permissions(
    os.path.expanduser("~/.local/share/iptvselect-fr"), permission_mode
)
create_dir_with_permissions(
    os.path.expanduser("~/.local/share/iptvselect-fr/logs"), permission_mode
)
create_dir_with_permissions(os.path.expanduser("~/.config"), permission_mode)
create_dir_with_permissions(os.path.expanduser("~/.config/iptvselect-fr"), permission_mode)
create_dir_with_permissions(
    os.path.expanduser("~/.config/iptvselect-fr/iptv_providers"), permission_mode
)


print(
    "\nLes dossiers ~/.config/iptvselect-fr/iptv_providers et "
    "~/.local/share/iptvselect-fr/logs ont été créés.\n"
)

src = os.path.expanduser("~/iptvselect-fr/constants.ini")
dest_dir = os.path.expanduser("~/.config/iptvselect-fr")
dest = os.path.join(dest_dir, "constants.ini")

if not os.path.isfile(dest):
    shutil.copy(src, dest)
    print(f"Le fichier {src} a été copié vers {dest}.\n")
else:
    print(f"Le fichier constants.ini existe déjà dans {dest}.\n")

src_path = os.path.expanduser("~/iptvselect-fr/iptv_providers/freeboxtv*")
dest_dir = os.path.expanduser("~/.config/iptvselect-fr/iptv_providers")
for file in glob.glob(src_path):
    shutil.copy(file, dest_dir)
print(
    "Les fichiers freeboxtv pour les abonnés Free ont été copiés "
    "dans le dossier ~/.config/iptvselect-fr/iptv_providers .\n"
)

print("Configuration des tâches cron du programme IPTV-select:\n")

response = requests.head("https://iptv-select.fr")
http_response = response.status_code

if http_response != 200:
    print(
        "\nLa box IPTV-select n'est pas connectée à internet. Veuillez "
        "vérifier votre connection internet et relancer le programme "
        "d'installation.\n\n"
    )
    exit()

username = input(
    "Veuillez saisir votre identifiant de connexion (adresse "
    "email) sur IPTV-select.fr: "
)
password_iptvrecord = getpass.getpass(
    "Veuillez saisir votre mot de passe sur IPTV-select.fr: "
)

home_dir = Path.home()
netrc_file = home_dir / ".netrc"
ls_netrc = ".netrc" if netrc_file.exists() else ""

if ls_netrc == "":
    netrc_path = Path(os.path.expanduser("~/.netrc"))
    netrc_path.touch(exist_ok=True)
    cmd = ["chmod", "go=", str(netrc_path)]
    chmod = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

user = os.environ.get("USER")

authprog_response = 403

with open("/home/" + user + "/.netrc", "r") as file:
    lines_origin = file.read().splitlines()

while authprog_response != 200:
    with open("/home/" + user + "/.netrc", "r") as file:
        lines = file.read().splitlines()

    try:
        position = lines.index("machine www.iptv-select.fr")
        lines[position + 1] = "  login {username}".format(username=username)
        lines[position + 2] = "  password {password_iptvrecord}".format(
            password_iptvrecord=password_iptvrecord
        )
    except ValueError:
        lines.append("machine www.iptv-select.fr")
        lines.append("  login {username}".format(username=username))
        lines.append(
            "  password {password_iptvrecord}".format(
                password_iptvrecord=password_iptvrecord
            )
        )

    with open("/home/" + user + "/.netrc", "w") as file:
        for line in lines:
            file.write(line + "\n")

    response = requests.head("https://www.iptv-select.fr/api/v1/prog")
    authprog_response = response.status_code

    if authprog_response != 200:
        try_again = input(
            "Le couple identifiant de connexion et mot de passe "
            "est incorrect.\nVoulez-vous essayer de nouveau?(oui ou non): "
        )
        answer_hide = "maybe"
        if try_again.lower() == "oui":
            username = input(
                "Veuillez saisir de nouveau votre identifiant de connexion (adresse email) sur IPTV-select.fr: "
            )
            while answer_hide.lower() not in answers:
                answer_hide = input(
                    "Voulez-vous afficher le mot de passe que vous saisissez "
                    "pour que cela soit plus facile? (répondre par oui ou non): "
                )
            if answer_hide.lower() == "oui":
                password_iptvrecord = input(
                    "Veuillez saisir de nouveau votre mot de passe sur IPTV-select.fr: "
                )
            else:
                password_iptvrecord = getpass.getpass(
                    "Veuillez saisir de nouveau votre mot de passe sur IPTV-select.fr: "
                )
        else:
            with open("/home/" + user + "/.netrc", "w") as file:
                for line in lines_origin:
                    file.write(line + "\n")
            exit()

auto_update = "no_se"

while auto_update.lower() not in answers:
    auto_update = (
        input(
            "\n\nAutorisez-vous l'application à se mettre à jour automatiquement? "
            "Si vous répondez 'non', vous devrez mettre à jour l'application par "
            "vous-même. (répondre par oui ou non) : "
        )
        .strip()
        .lower()
    )

heure = random.randint(6, 23)
minute = random.randint(0, 58)
minute_2 = minute + 1
heure_auto_update = heure - 1
minute_auto_update = random.randint(0, 59)

crontab_init = subprocess.Popen(
    ["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
)
stdout, stderr = crontab_init.communicate()

if stderr:
    print("Erreur lors de l'initialisation du cron: ", stderr.decode("utf-8"))
    print(
        "Le cron ne sera pas sauvegardé (ce qui est attendu si l'erreur "
        "reportée est no crontab for user)."
    )


with open("cron_tasks.sh", "wb") as file:
    file.write(stdout)

with open("cron_tasks.sh", "r") as crontab_file:
    cron_lines = crontab_file.readlines()

curl = (
    "{minute} {heure} * * * curl -H 'Accept: application/json;"
    "indent=4' -n https://www.iptv-select.fr/api/v1/prog > $HOME/.local/share"
    "/iptvselect-fr/info_progs.json 2>> $HOME/.local/share/iptvselect-fr/"
    "logs/cron_launch_record.log\n".format(
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


cron_lines = [
    curl if "iptvselect-fr/info_progs.json" in cron else cron for cron in cron_lines
]
cron_lines = [cron_launch if "iptvselect-fr &&" in cron else cron for cron in cron_lines]

if auto_update.lower() == "oui":
    cron_lines = [
        cron_auto_update if "iptvselect-fr/auto_update" in cron else cron
        for cron in cron_lines
    ]
else:
    cron_lines = [cron for cron in cron_lines if "iptvselect-fr/auto_update" not in cron]

cron_lines_join = "".join(cron_lines)

if "iptvselect-fr/info_progs.json" not in cron_lines_join:
    cron_lines.append(curl)
if "cd /home/$USER/iptvselect-fr &&" not in cron_lines_join:
    cron_lines.append(cron_launch)

if auto_update.lower() == "oui" and "iptvselect-fr/auto_update" not in cron_lines_join:
    cron_lines.append(cron_auto_update)

with open("cron_tasks.sh", "w") as crontab_file:
    for cron_task in cron_lines:
        crontab_file.write(cron_task)

cmd = ["crontab", "cron_tasks.sh"]
cron = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
cron.wait()
cmd = ["rm", "cron_tasks.sh"]
rm = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

print("\nLes tâches cron de votre box IPTV-select sont maintenant configurés!\n")
