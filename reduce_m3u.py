import os
import re
import stat
from pathlib import Path

def human_readable(size_bytes):
    """Convert bytes to a human-readable format similar to `du -h`."""
    for unit in ["B", "K", "M", "G", "T"]:
        if size_bytes < 1024.0:
            # Remove decimal for bytes, keep one decimal for larger units
            return f"{int(size_bytes)}{unit}" if unit == "B" else f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}P"

home_dir = Path.home()

# SECURITY: whitelist filenames to avoid path traversal
valid_filename_re = re.compile(r"^[A-Za-z0-9._-]+$")

while True:
    m3u_file = input(
        "Quel est le nom du fichier m3u de votre "
        "fournisseur d'IPTV? (renseignez le nom sans "
        "l'extension .m3u): "
    ).strip()

    if not valid_filename_re.match(m3u_file):
        print("Nom de fichier invalide. Caractères autorisés: lettres, chiffres, ., _, -\n")
        continue

    m3u_path = home_dir / ".config/iptvselect-fr/iptv_providers" / f"{m3u_file}.m3u"

    # SECURITY: prevent symlink attacks
    if m3u_path.exists() and m3u_path.is_symlink():
        print("Erreur: le fichier est un lien symbolique. Refus pour raisons de sécurité.\n")
        continue

    if not m3u_path.exists():
        print(
            f"Le fichier {m3u_file}.m3u n'est pas présent dans votre dossier "
            "~/.config/iptvselect-fr/iptv_providers. "
            "Insérez le fichier m3u de votre fournisseur d'IPTV "
            "ou modifiez le nom du fichier pour qu'il corresponde.\n"
        )
        continue
    break

file_size = human_readable(m3u_path.stat().st_size)
print(f"\nLa taille du fichier {m3u_file}.m3u est de {file_size}")

answers = ["oui", "non"]
answer = "maybe"

while answer.lower() not in answers:
    answer = input(
        f"\nVoulez-vous réduire la taille du fichier {m3u_file}.m3u "
        "afin d'exécuter plus rapidement le script fill_ini.py? "
        "(répondre par oui ou non). \n"
        "Le programme va enlever tous les liens m3u du fichier "
        f"{m3u_file}.m3u qui contiennent des extensions vidéos "
        "tels que .avi, .mkv et .mp4. Veuillez sauvegarder "
        "votre fichier .m3u si vous voulez conserver l'original "
        "car le script ne créé pas de sauvegarde du "
        "fichier.\nRemarque: Le programme peut durer plusieurs "
        "minutes avant de réduire le fichier en fonction de sa "
        "taille et de la quantité de mémoire vive présente. (merci d'attendre "
        "le retour à l'invite de commande après l'annonce de la nouvelle taille "
        "du fichier car à cause de l'utilisation du SWAP, cela peut durer plusieurs "
        "minutes pour les boxs de moins de 1Gb de mémoire vive.)\n"
    )

extensions = [".avi", ".mkv", ".mp4"]

if answer.lower() == "oui":
    with open(m3u_path, "r", encoding="utf-8") as m3u:
        m3u_lines = m3u.readlines()
        lines = []

        for i, line in enumerate(m3u_lines):
            next_line = m3u_lines[i + 1] if i + 1 < len(m3u_lines) else None

            if line.startswith("#"):
                if next_line and next_line[-5:-1] not in extensions:
                    lines.append(line)
            else:
                if line[-5:-1] not in extensions:
                    lines.append(line)
else:
    exit()

with open(m3u_path, "w", encoding="utf-8") as m3u:
    for line in lines:
        m3u.write(line)

# SECURITY: enforce strict file permissions
os.chmod(m3u_path, stat.S_IRUSR | stat.S_IWUSR)  # 600

file_size = human_readable(m3u_path.stat().st_size)
print(f"\nLa taille du fichier {m3u_file}.m3u est maintenant de {file_size}")
