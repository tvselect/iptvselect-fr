import subprocess
import readline

"""Script to remove files in ~/.local/share/iptvselect-fr/logs directory"""

print(
    "Le script clean_var_tmp.py permet de supprimer les fichiers de "
    "logs les plus anciens présents dans le dossier "
    "~/.local/share/iptvselect-fr/logs de votre ordinateur."
)

cmd = "du -h ~/.local/share/iptvselect-fr/logs/ 2> /dev/null | tail -n 1"
size = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
stdout, stderr = size.communicate()
size_tmp = stdout.decode("utf-8")[:-1].split("\t")[0]

cmd = "ls -p1t ~/.local/share/iptvselect-fr/logs | grep -v / | wc -l"
file_ls = subprocess.Popen(
    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
)
stdout, stderr = file_ls.communicate()
file_count = stdout.decode("utf-8")[:-1]

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
    cmd = "ls -p1t ~/.local/share/iptvselect-fr/logs | grep -v / | tail -n {files_number}".format(
        files_number=files_number
    )
    # cmd = "ls -1t ~/.local/share/iptvselect-fr/logs | tail -n {files_number}".format(
    # files_number=files_number)
    ls = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    stdout, stderr = ls.communicate()
    files = stdout.decode("utf-8")[:-1]
    print(files)
    delete = input(
        "\nVoulez vous supprimer ces fichiers pour libérer de "
        "l'espace? (Utilisez la molette de la souris pour "
        "remonter dans le terminal et visualiser tous les "
        "fichiers si besoin puis répondre par oui ou non: \n"
    )
    """
        WIP because xargs with subprocess to delete files is not working like that
    """
    if delete.lower() == "oui":
        cms = (
            "ls -p1t ~/.local/share/iptvselect-fr/logs | grep -v / | tail -n "
            + files_number
            + " | xargs -I {} rm ~/.local/share/iptvselect-fr/logs/{}"
        )
        deleted = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        # deleted.wait()
        stdout, stderr = deleted.communicate()
        print(stdout)

        cmd = "du -h ~/.local/share/iptvselect-fr/logs/ 2> /dev/null | tail -n 1"
        size = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        stdout, stderr = size.communicate()
        size_tmp = stdout.decode("utf-8")[:-1].split("\t")[0]

        cmd = "ls -p1t ~/.local/share/iptvselect-fr/logs | grep -v / | wc -l"
        file_ls = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        stdout, stderr = file_ls.communicate()
        file_count = stdout.decode("utf-8")[:-1]

        print(
            "La taille du dossier ~/.local/share/iptvselect-fr/logs est "
            "désormais de " + size_tmp + " et il "
            "contient maintenant" + file_count + " fichiers."
        )
    else:
        exit()
else:
    exit()
