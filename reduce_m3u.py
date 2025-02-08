import subprocess
import readline
import os

m3u_file = "123456"
ls_result = "abcdef"

user = os.environ.get("USER")

while (
    ls_result
    != "/home/" + user + "/.config/iptvselect-fr/iptv_providers/" + m3u_file + ".m3u"
):
    m3u_file = input(
        "Quel est le nom du fichier m3u de votre "
        "fournisseur d'IPTV? (renseignez le nom "
        "sans l'extension .m3u): "
    )
    cmd = (
        "ls /home/"
        + user
        + "/.config/iptvselect-fr/iptv_providers/{m3u_file}.m3u".format(m3u_file=m3u_file)
    )
    output = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    stdout, stderr = output.communicate()
    ls_result = stdout.decode("utf-8")[:-1]
    if (
        ls_result
        != "/home/" + user + "/.config/iptvselect-fr/iptv_providers/" + m3u_file + ".m3u"
    ):
        print(
            "Le fichier {m3u_file}.m3u n'est pas présent dans votre"
            " dossier ~/.config/iptvselect-fr/iptv_providers. Insérer "
            "le fichier m3u de votre fournisseur d'IPTV ou modifier "
            "le nom du fichier m3u pour qu'il corresponde à celui "
            "du fichier présent dans le dossier.\n".format(m3u_file=m3u_file)
        )

cmd = (
    "du -h /home/" + user + "/.config/iptvselect-fr/iptv_"
    "providers/{m3u_file}.m3u | cut -f1"
).format(m3u_file=m3u_file)
duh = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
stdout, stderr = duh.communicate()
file_size = stdout.decode("utf-8")[:-1]

print(
    "\nLa taille du fichier {m3u_file}.m3u est de {file_size}".format(
        m3u_file=m3u_file, file_size=file_size
    )
)

answers = ["oui", "non"]
answer = "maybe"

while answer.lower() not in answers:
    answer = input(
        "\nVoulez-vous réduire la taille du fichier {m3u_file}.m3u "
        "afin d'exécuter plus rapidement le script fill_ini.py? "
        "(répondre par oui ou non). \n"
        "Le programme va enlever tous les liens m3u du fichier "
        "{m3u_file}.m3u qui contiennent des extensions vidéos "
        "tels que .avi, .mkv et .mp4. Veuillez sauvegarder "
        "votre fichier .m3u si vous voulez conserver l'original "
        "car le script ne créé pas de sauvegarde du "
        "fichier.\nRemarque: Le programme peut durer plusieurs "
        "minutes avant de réduire le fichier en fonction de sa "
        "taille et de la quantité de mémoire vive présente. (merci d'attendre "
        "le retour à l'invite de commande après l'annonce de la nouvelle taille "
        "du fichier car à cause de l'utilisation du SWAP, cela peut durer plusieurs "
        "minutes pour les boxs de moins de 1Gb de mémoire vive.)\n".format(
            m3u_file=m3u_file
        )
    )

extensions = [".avi", ".mkv", ".mp4"]

if answer.lower() == "oui":
    with open(
        "/home/" + user + "/.config/iptvselect-fr/iptv_providers/" + m3u_file + ".m3u", "r"
    ) as m3u:
        m3u_lines = [line for line in m3u]
        lines = []

        for n in range(len(m3u_lines)):
            if m3u_lines[n][0] == "#":
                if m3u_lines[n + 1][-5:-1] not in extensions:
                    lines.append(m3u_lines[n])
            else:
                if m3u_lines[n][-5:-1] not in extensions:
                    lines.append(m3u_lines[n])
else:
    exit()

with open(
    "/home/" + user + "/.config/iptvselect-fr/iptv_providers/" + m3u_file + ".m3u", "w"
) as m3u:
    for line in lines:
        m3u.write(line)

cmd = (
    "du -h /home/" + user + "/.config/iptvselect-fr/iptv_"
    "providers/{m3u_file}.m3u | cut -f1"
).format(m3u_file=m3u_file)
duh = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
stdout, stderr = duh.communicate()
file_size = stdout.decode("utf-8")[:-1]

print(
    "\nLa taille du fichier {m3u_file}.m3u est maintenant de {file_size}".format(
        m3u_file=m3u_file, file_size=file_size
    )
)
