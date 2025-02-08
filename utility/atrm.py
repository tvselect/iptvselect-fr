import subprocess
import argparse

"""Script to remove at tasks"""

parser = argparse.ArgumentParser()
parser.add_argument("pid_start", nargs="?", type=int)
args = parser.parse_args()

print(
    "Le script atrm.py permet d'annuler toutes les taches at présentes "
    "dans votre ordinateur."
)
answer = input("Voulez-vous annuler toutes les taches at? (répondre par oui ou non): ")

if answer.lower() != "oui":
    exit()
else:
    cmd = "atq | cut -f1"
    atq = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    stdout, stderr = atq.communicate()
    pids = stdout.decode("utf-8").split("\n")[:-1]

    for pid in pids:
        if args.pid_start is None or int(pid) > args.pid_start:
            cmd = "atrm {pid}".format(pid=int(pid))
            atrm = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )
            atrm.wait()

    print("Toutes les tâches at ont été supprimées!")
