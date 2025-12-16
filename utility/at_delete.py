import re
import subprocess

"""Script to remove specific at tasks"""

proc = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
stdout = proc.stdout

lines = [line for line in stdout.splitlines() if "iptvselect" in line]

time_curl = [line.split("*", 1)[0].strip().split() for line in lines]

print(
    "Votre box iptv est programmée pour rechercher les informations des vidéos que "
    "vous souhaitez enregistrer à {hour}H{minute}.".format(
        hour=time_curl[0][1], minute=time_curl[0][0]
    )
)
print(
    "\nVous pouvez donc annuler les enregistrements programmés pour être enregistrés "
    "après cette heure sur le site iptv-select.fr. Pour les vidéos prévues pour "
    "être enregistrées avant cette heure, vous pourrez les annuler grâce à "
    "ce programme."
)

print(
    "\nLe script at_delete.py permet d'annuler les enregistrements programmés "
    "pour être enregistrés dans votre ordinateur. Voici les titres des vidéos "
    " programmées pour être enregistrées dans votre box iptv (vous pouvez "
    "retrouver les détails et heures programmées des enregistrements sur "
    "l'application web iptv-select.fr dans la page 'mes enregistrements "
    "programmés'): \n"
)

proc = subprocess.run(["atq"], capture_output=True, text=True)
if proc.returncode != 0:
    raise RuntimeError(f"atq failed: {proc.stderr.strip()}")

pids = []
for line in proc.stdout.splitlines():
    line = line.strip()
    if not line:
        continue
    first_field = line.split()[0]
    pids.append(first_field)

not_deleted = True
to_skip = True
answers = ["oui", "non"]
answer = "maybe"

while not_deleted:

    for pid_str in pids:
        pid_str = pid_str.strip()
        if not pid_str:
            continue

        try:
            pid = int(pid_str)
        except ValueError:
            continue

        proc = subprocess.run(
            ["at", "-c", str(pid)],
            capture_output=True,
            text=True,
        )

        if proc.returncode != 0:
            continue

        for line in proc.stdout.splitlines():
            if "fusion_script" not in line:
                continue

            parts = line.split()
            title = parts[2] if len(parts) >= 3 else ""

            if title:
                print(title)
                to_skip = False

    if to_skip:
        print(
            "\nIl n'y a aucune vidéos prévues pour être enregistrées dans la box IPTV.\n"
        )
        exit()

    delete = input(
        "\nQuel enregistrement voulez-vous annuler? "
        "(renseignez le numéro identifiant le film): "
    )

    for pid_str in pids:
        pid_str = pid_str.strip()
        if not pid_str:
            continue

        try:
            pid = int(pid_str)
        except ValueError:
            continue

        proc = subprocess.run(
            ["at", "-c", str(pid)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            continue

        escaped_delete = re.escape(delete)

        found = False
        for line in proc.stdout.splitlines():
            if re.search(escaped_delete, line):
                parts = line.split()
                title = parts[2] if len(parts) >= 3 else ""
                if title:
                    found = True
                    break

        if found:
            rm_proc = subprocess.run(["atrm", str(pid)], capture_output=True, text=True)
            not_deleted = False


    if not_deleted:
        while answer.lower() not in answers:
            answer = input(
                "Aucune vidéo n'apparait prévue d'être enregistrée "
                "avec l'identifiant {delete}. Voulez-vous renseigner de nouveau "
                "l'identifiant ? (répondre par oui ou non): "
            )
        if answer.lower() == "non":
            exit()

print(
    "La programmation de l'enregistrement de la vidéo avec "
    "l'identifiant {delete} a été annulé.".format(delete=delete)
)
