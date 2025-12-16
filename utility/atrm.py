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
    proc = subprocess.run(
        ["atq"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,   # returns str instead of bytes
    )

    pids = [line.split(None, 1)[0] for line in proc.stdout.splitlines() if line.strip()]

    for pid in pids:
        if args.pid_start is None or int(pid) > args.pid_start:
            pid_int = int(pid)

            result = subprocess.run(
                ["atrm", str(pid_int)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )

    print("Toutes les tâches at ont été supprimées!")
