import subprocess

"""Script to remove specific at tasks"""

cmd = "crontab -l | sed -n '/iptv-select/p' | cut -d '*' -f1"
time_cron = subprocess.Popen(
    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
)
stdout, stderr = time_cron.communicate()
time_curl = stdout.decode("utf-8")[:-2].split(" ")

print(
    "Votre box iptv est programmée pour rechercher les informations des vidéos que "
    "vous souhaitez enregistrer à {hour}H{minute}.".format(
        hour=time_curl[1], minute=time_curl[0]
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

cmd = "atq | cut -f1"
atq = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
stdout, stderr = atq.communicate()
pids = stdout.decode("utf-8").split("\n")[:-1]

not_deleted = True
to_skip = True
answers = ["oui", "non"]
answer = "maybe"

while not_deleted:

    for pid in pids:
        cmd = "at -c {pid} | sed -n '/fusion_script/p' | " "cut -d ' ' -f3".format(
            pid=int(pid)
        )
        atprint = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        stdout, stderr = atprint.communicate()
        title = stdout.decode("utf-8")[:-1]
        if title != "":
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

    for pid in pids:
        cmd = "at -c {pid} | sed -n '/{delete}/p' | " "cut -d ' ' -f3".format(
            pid=int(pid), delete=delete
        )
        atprint = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        stdout, stderr = atprint.communicate()
        if stdout.decode("utf-8")[:-1] != "":
            cmd = "atrm {pid}".format(pid=pid)
            atrm = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )
            atrm.wait()
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
