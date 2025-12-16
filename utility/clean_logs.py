import os
import subprocess

from pathlib import Path

"""Script to remove files in ~/.local/share/iptvselect-fr/logs directory"""

print(
    "Le script clean_var_tmp.py permet de supprimer les fichiers de "
    "logs les plus anciens présents dans le dossier "
    "~/.local/share/iptvselect-fr/logs de votre ordinateur."
)

log_dir = Path.home() / ".local/share/iptvselect-fr/logs"

p1 = subprocess.Popen(["du", "-h", str(log_dir)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
p2 = subprocess.Popen(["tail", "-n", "1"], stdin=p1.stdout, stdout=subprocess.PIPE)
p1.stdout.close()

stdout, _ = p2.communicate()

size_tmp = stdout.decode("utf-8").strip().split("\t")[0]

p1 = subprocess.Popen(["ls", "-p1t", str(log_dir)], stdout=subprocess.PIPE)
p2 = subprocess.Popen(["grep", "-v", "/"], stdin=p1.stdout, stdout=subprocess.PIPE)
p1.stdout.close()

p3 = subprocess.Popen(["wc", "-l"], stdin=p2.stdout, stdout=subprocess.PIPE)
p2.stdout.close()

stdout, _ = p3.communicate()
file_count = stdout.decode("utf-8").strip()

print(
    "La taille du dossier ~/.local/share/iptvselect-fr/logs est de " + size_tmp + " et il "
    "contient " + file_count + " fichiers."
)

answer = input(
    "\nVoulez-vous supprimer les fichiers les plus anciens de ce dossier "
    "pour libérer de l'espace? (répondre par oui ou non): "
)

if answer.lower() == "oui":
    files_number = input(
        "\nCombien des fichiers les plus anciens de ce dossier "
        "voulez-vous supprimer pour libérer de l'espace?: "
    )

    print(
        "\nVoici les {files_number} fichiers les plus anciens: "
        "\n".format(files_number=files_number)
    )

    files_number = int(files_number)

    p1 = subprocess.Popen(["ls", "-p1t", str(log_dir)], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["grep", "-v", "/"], stdin=p1.stdout, stdout=subprocess.PIPE)
    p1.stdout.close()
    p3 = subprocess.Popen(["tail", "-n", str(files_number)], stdin=p2.stdout, stdout=subprocess.PIPE)
    p2.stdout.close()

    stdout, _ = p3.communicate()
    files = stdout.decode("utf-8").strip()

    print(files)
    delete = input(
        "\nVoulez vous supprimer ces fichiers pour libérer de "
        "l'espace? (Utilisez la molette de la souris pour "
        "remonter dans le terminal et visualiser tous les "
        "fichiers si besoin puis répondre par oui ou non: \n"
    )

    if delete.lower() == "oui":

        try:
            files_number = int(files_number)
        except (TypeError, ValueError):
            raise ValueError("files_number must be an integer")

        if files_number < 1:
            raise ValueError("files_number must be >= 1")

        files = [p for p in log_dir.iterdir() if p.is_file()]

        files_sorted = sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)

        to_delete = files_sorted[-files_number:]

        log_dir_resolved = log_dir.resolve()
        safe_to_delete = []
        for p in to_delete:
            try:
                if str(p.resolve()).startswith(str(log_dir_resolved) + os.sep):
                    safe_to_delete.append(p)
                else:
                    print(f"Skipping {p!s}, resolves outside {log_dir_resolved}")
            except FileNotFoundError:
                pass

        deleted = []
        errors = {}
        for p in safe_to_delete:
            try:
                p.unlink()
                deleted.append(p.name)
            except Exception as e:
                errors[p.name] = str(e)

        print("Deleted:", deleted)
        if errors:
            print("Errors:", errors)

        print(stdout)

        if not log_dir.exists():
            raise FileNotFoundError(f"{log_dir} does not exist")

        proc = subprocess.run(
            ["du", "-sh", str(log_dir)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            text=True,
        )

        stdout = proc.stdout.strip()
        if not stdout:
            size_tmp = "0"
        else:
            size_tmp = stdout.split(None, 1)[0]

        print("Directory size (human):", size_tmp)

        p1 = subprocess.Popen(["ls", "-p1t", str(log_dir)], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["grep", "-v", "/"], stdin=p1.stdout, stdout=subprocess.PIPE)
        p1.stdout.close()
        p3 = subprocess.Popen(["wc", "-l"], stdin=p2.stdout, stdout=subprocess.PIPE)
        p2.stdout.close()

        stdout, _ = p3.communicate()
        file_count = stdout.decode("utf-8").strip()

        print(
            "La taille du dossier ~/.local/share/iptvselect-fr/logs est "
            f"désormais de {size_tmp} et il contient maintenant {file_count} fichiers."
        )
    else:
        exit()
else:
    exit()
