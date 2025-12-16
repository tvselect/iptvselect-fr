import json
import requests
import shutil
import sys
import os
import stat

from pathlib import Path
from config_manager import ConfigManager, is_valid_url


HEADERS = {
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip, deflate",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
}

MAX_JSON_SIZE = 500 * 1024 * 1024
MAX_PROVIDER_NAME_LENGTH = 100
MAX_USERNAME_LENGTH = 200
MAX_PASSWORD_LENGTH = 200
MAX_URL_LENGTH = 500


def secure_file_permissions(file_path):
    """
    Set secure file permissions on sensitive files.
    Only the owner can read/write the file.

    Args:
        file_path: Path object or string path to the file
    """
    try:
        # Set permissions to 600 (rw-------)
        os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception as e:
        print(f"  Avertissement: Impossible de sécuriser les permissions du fichier {file_path}: {e}")


def validate_provider_name_security(name: str) -> bool:
    """
    Validate provider name for security issues beyond basic character check.
    Prevents path traversal attacks.

    Args:
        name: Provider name to validate

    Returns:
        True if secure, False otherwise
    """
    dangerous_patterns = ["..", "/", "\\", "\x00"]
    for pattern in dangerous_patterns:
        if pattern in name:
            return False

    if len(name) > MAX_PROVIDER_NAME_LENGTH:
        return False

    if not name.strip():
        return False

    return True


def sanitize_stream_name(name: str) -> str:
    """
    Sanitize stream name from API to prevent injection attacks.
    Removes or escapes potentially dangerous characters.

    Args:
        name: Stream name from API

    Returns:
        Sanitized stream name
    """
    if not isinstance(name, str):
        return ""

    sanitized = "".join(char for char in name if ord(char) >= 32 or char in ['\n', '\r', '\t'])

    return sanitized[:500]


def validate_url_security(url: str) -> bool:
    """
    Enhanced URL validation with security checks.

    Args:
        url: URL to validate

    Returns:
        True if URL is valid and secure, False otherwise
    """
    if len(url) > MAX_URL_LENGTH:
        print(f"  L'URL est trop longue (maximum {MAX_URL_LENGTH} caractères).")
        return False

    if not is_valid_url(url):
        return False

    url_lower = url.lower()

    dangerous_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
    for host in dangerous_hosts:
        if host in url_lower:
            print("  Les URLs localhost ne sont pas autorisées pour des raisons de sécurité.")
            return False

    if url_lower.startswith("file://"):
        print("  Le protocole file:// n'est pas autorisé.")
        return False

    return True


def validate_input_length(input_value: str, max_length: int, field_name: str) -> bool:
    """
    Validate input length for security.

    Args:
        input_value: The input to validate
        max_length: Maximum allowed length
        field_name: Name of the field for error messages

    Returns:
        True if valid, False otherwise
    """
    if len(input_value) > max_length:
        print(f"  {field_name} est trop long (maximum {max_length} caractères).")
        return False
    return True


def get_valid_provider_name():
    """
    Prompt user for a valid IPTV provider name.
    Only alphanumeric characters and underscores are allowed.

    Returns:
        Valid provider name string
    """
    while True:
        iptv_provider = input(
            "Nom de votre fournisseur IPTV (lettres, chiffres et '_' uniquement): "
        ).strip()

        if not iptv_provider:
            print(" Le nom ne peut pas être vide.\n")
            continue

        # Security: Validate against path traversal and other attacks
        if not validate_provider_name_security(iptv_provider):
            print(" Le nom contient des caractères dangereux ou est invalide.")
            print("   Évitez les caractères: . . / \\ et autres caractères spéciaux.")
            print("   Exemple : MonFournisseur_IPTV ou Fournisseur2024\n")
            continue

        if all(c.isalnum() or c == '_' for c in iptv_provider):
            return iptv_provider
        else:
            print(" Le nom doit contenir uniquement des lettres, chiffres et '_'.")
            print("   Exemple : MonFournisseur_IPTV ou Fournisseur2024\n")

def normalize_channel_name(name: str) -> str:
    name = name.removesuffix(" = ").lower()
    if name[:3] in CHANS_SPEC:
        name = name[:3]
    return name

def candidates(name: str):
    # Yield possible normalized variants for matching
    yield name
    yield name.replace(" ", "")
    yield name.replace(" ", "-")
    yield name.replace(" ", "_")
    yield name.replace("'", "")
    yield name.replace("+", "")

cfg = ConfigManager()

iptv_providers_listed = cfg.list_providers()

answers = {"oui", "non"}

if len(iptv_providers_listed) > 0:
    print("Voici la liste de vos codes Xtream déjà enregistrés:\n")
    for n, code in enumerate(iptv_providers_listed, start=1):
        print(f" {n}) Fournisseur IPTV: {code['iptv_provider']}\n"
              f"  URL: {code['server_url']}\n"
              f"  Nom d'utilisateur: {code['username']}\n"
              f"  Mot de passe: {code['password']}\n"
              f"  Format URL: {code['url_format']}\n"
              "-----------------------------------")
    delete = "no_se"
    while True:
        delete = input("\nVoulez-vous effacer des codes Xtreams "
                       "de la liste? (vous n'avez pas besoin de supprimer "
                       "des codes pour les mettre à jour). Répondre par oui "
                       "ou non): ").strip().lower()
        if delete.strip().lower() in answers:
            break
    if delete.strip().lower() == "oui":
        while True:
            to_delete = input("Saisissez les numéros des liens à supprimer "
                              "(séparé par des espaces ou des virgules): ")
            indices = []
            for part in to_delete.replace(",", " ").split():
                try:
                    indices.append(int(part))
                except ValueError:
                    pass

            indices = sorted(set(indices), reverse=True)

            for i in indices:
                if 1 <= i <= len(iptv_providers_listed):
                    cfg.delete_provider(iptv_providers_listed[i - 1]["iptv_provider"])

            iptv_providers_listed = cfg.list_providers()

            if len(iptv_providers_listed) > 0:
                print("\nVoici votre nouvelle liste de codes Xtream:\n")
                for n, code in enumerate(iptv_providers_listed, start=1):
                    print(f" {n}) Fournisseur IPTV: {code['iptv_provider']}\n"
                        f"  URL: {code['server_url']}\n"
                        f"  Nom d'utilisateur: {code['username']}\n"
                        f"  Mot de passe: {code['password']}\n"
                        f"  Format de URL: {code['url_format']}"
                        "-----------------------------------")
                break
            else:
                print("Votre liste de codes Xtream est vide.")
                break

url_format = "{server_url}/live/{username}/{password}/{stream_id}.ts"

if len(iptv_providers_listed) > 0:
    print("\nLe programme va maintenant vous demander de saisir le nom de "
        "de votre fournisseur d'IPTV. S'il correspond au nom d'un des codes de "
        "votre liste de codes Xtream, il sera mise à jour à partir des "
        "nouvelles données.\n")

iptv_provider = get_valid_provider_name()

match = None

if len(iptv_providers_listed) > 0:
    match = next(
    (item for item in iptv_providers_listed if item["iptv_provider"] == iptv_provider),
        None
    )

if match is None:
    print("\nLe format de l'URL des servers pour le direct des chaines "
        "télévísées est habituellement de la forme suivante:\n"
        "{server_url}/live/{username}/{password}/{stream_id}.ts\n"
        "Ce format d'URL convient pour la pluplart des cas. Toutefois, si vous savez que le format "
        "d'URL de votre serveur IPTV est différent, vous pouvez le modifier dès maintenant "
        "s'il ne vous convient pas.")
else:
    print("\nLe format de l'URL enregistré pour votre fournisseur IPTV est:\n"
        f"{match['url_format']}\n"
        "Vous pouvez le modifier dès maintenant s'il ne vous convient pas.")

while True:
    modify_url = input("Voulez vous modifier le format d'URL? "
                        "(oui/non): ").strip().lower()
    if modify_url in {"oui", "non"}:
        break
    print("Réponse invalide. Veuillez répondre par 'oui', 'non'.")

url_format_list = [
    "{server_url}/live/{username}/{password}/{stream_id}",
    "{server_url}/live/{username}/{password}/{stream_id}.ts",
    "{server_url}/live/{username}/{password}/{stream_id}.m3u8",
    "{server_url}/{username}/{password}/live/{stream_id}",
    "{server_url}/{username}/{password}/live/{stream_id}.ts",
    "{server_url}/{username}/{password}/live/{stream_id}.m3u8",
    "{server_url}/{username}/{password}/{stream_id}",
    "{server_url}/{username}/{password}/{stream_id}.ts",
    "{server_url}/{username}/{password}/{stream_id}.m3u8"
]

if modify_url == "oui":
    while True:
        print("Choisissez un numéro correspondant au format d'URL de votre serveur IPTV :")
        for i, fmt in enumerate(url_format_list, start=1):
            print(f"  {i}) {fmt}")

        format_choice = input("Votre choix: ").strip()

        if format_choice.isdigit() and 1 <= int(format_choice) <= len(url_format_list):
            url_format = url_format_list[int(format_choice) - 1]
            break
        else:
            print("Réponse invalide. Veuillez entrer un chiffre entre 1 et 9.")
else:
    url_format = url_format_list[1]

source = Path("iptv_providers/iptv_select_channels.ini")
destination = Path.home() / ".config/iptvselect-fr/iptv_providers" / f"{iptv_provider}.ini"

destination.parent.mkdir(parents=True, exist_ok=True)

try:
    os.chmod(destination.parent, stat.S_IRWXU)  # 700 permissions (rwx------)
except Exception as e:
    print(f"  Avertissement: Impossible de sécuriser le répertoire de configuration: {e}")

shutil.copy2(source, destination)

secure_file_permissions(destination)

while True:
    server_url = input("\nSaisissez l'URL de votre founisseur IPTV qu'il vous a fourni pour "
                     "utiliser avec les Xtream Codes (pour faciliter la saisie vous pouvez "
                     "coller le lien avec le raccourci): \n"
                    "- 'Ctrl + Maj + V' dans la plupart des terminaux Linux, \n"
                    "- 'Cmd (⌘) + V' sur macOS, \n"
                    "- ou avec un clic droit > 'Coller' dans PowerShell sous Windows) : \n")

    if not validate_url_security(server_url):
        print("\n URL invalide. Veuillez saisir une URL complète commençant par http:// ou https:// "
            "(exemple : https://monsuperiptvquivabien.com)")
    else:
        break

while True:
    username = input("\nSaisissez votre nom d'utilisateur: ")
    if validate_input_length(username, MAX_USERNAME_LENGTH, "Le nom d'utilisateur"):
        break

while True:
    password = input("\nSaisissez votre mot de passe: ")
    if validate_input_length(password, MAX_PASSWORD_LENGTH, "Le mot de passe"):
        break

cfg.add_or_update_provider(iptv_provider, server_url, username, password, url_format)

print(f"✓ Fournisseur IPTV enregistré : {iptv_provider}")

host_url = f"{server_url}/player_api.php"

params = {
    'username': username,
    'password': password,
    'action': 'get_live_streams',
}

try:
    resp = requests.get(
        host_url,
        params=params,
        headers=HEADERS,
        timeout=(10, 30),
        stream=True
    )
    resp.raise_for_status()

    content_length = resp.headers.get('Content-Length')
    if content_length and int(content_length) > MAX_JSON_SIZE:
        print(f" Erreur: La réponse du serveur est trop grande ({int(content_length)} bytes). "
              f"Maximum autorisé: {MAX_JSON_SIZE} bytes")
        sys.exit()

    content = b""
    for chunk in resp.iter_content(chunk_size=8192):
        content += chunk
        if len(content) > MAX_JSON_SIZE:
            print(f" Erreur: La réponse du serveur dépasse la taille maximale autorisée ({MAX_JSON_SIZE} bytes)")
            sys.exit()

    live_info_data = json.loads(content.decode('utf-8'))

except requests.exceptions.Timeout:
    print(" Erreur: Le délai de connexion au serveur a expiré. "
          "Veuillez vérifier votre connexion Internet et réessayer.")
    sys.exit()
except requests.exceptions.ConnectionError:
    print(" Erreur: Impossible de se connecter au serveur. "
          "Veuillez vérifier l'URL et votre connexion Internet.")
    sys.exit()
except requests.exceptions.RequestException as e:
    print(f" Erreur de requête: {e}")
    live_info_data = {}
except json.JSONDecodeError:
    print(" Erreur: La réponse du serveur n'est pas au format JSON valide.")
    live_info_data = {}
except ValueError:
    print(" Erreur: Impossible de décoder la réponse du serveur.")
    live_info_data = {}

if len(live_info_data) == 0:
    print(f" Le téléchargement des données du fournisseur d'IPTV {iptv_provider} a échoué. "
        "Merci de vérifier vos codes Xtream. Si le problème persiste, "
        "contactez votre fournisseur d'IPTV pour obtenir de l'aide.")
    sys.exit()

print(f"\n Votre fournisseur IPTV possède {len(live_info_data)} flux de direct de chaines télévísées.")

live_info_path = Path.home() / ".config/iptvselect-fr/iptv_providers" / f"{iptv_provider}.json"

with open(live_info_path, "w", encoding="UTF-8") as file:
    json.dump(live_info_data, file, ensure_ascii=False, indent=4)

secure_file_permissions(live_info_path)

providers_dir = Path.home() / ".config/iptvselect-fr/iptv_providers"
ini_path = providers_dir / f"{iptv_provider}.ini"

with open(ini_path, "r", encoding="utf-8") as ini:
    lines = ini.readlines()
    first_line = lines[0] if lines else ""
    lines = [line.rstrip('\n') for line in lines[1:]]

CHANS_SPEC = {"lci", "lcp"}

print(
    "\n Le script va maintenant vous proposer une sélection de flux issus de votre "
    "fournisseur IPTV pour toutes les chaînes répertoriées sur iptv-select.fr. "
    "L'affichage de chaque sélection peut prendre plusieurs secondes. "
    "Par exemple, la chaîne France 3 peut être plus longue à charger, car le script "
    "doit filtrer les déclinaisons régionales, souvent absentes des fichiers M3U.\n\n"
    "Veuillez patienter et éviter d'appuyer plusieurs fois sur la touche Entrée pour "
    "valider un choix. Attendez toujours le retour du curseur avant de répondre à la question "
    "suivante. Un appui répété sur Entrée risque de valider automatiquement les sélections "
    "suivantes avec le premier choix proposé."
)

print(
    "\n La sélection manuelle des chaînes, c'est-à-dire le choix parmi la liste proposée "
    "pour chaque chaîne, est la méthode la plus fiable pour associer correctement les flux "
    "de votre fournisseur IPTV. Elle prend environ 20 minutes pour traiter les plus de 200 "
    "chaînes référencées sur iptv-select.fr. Un mode automatique est disponible, mais il peut "
    "entraîner des erreurs en raison des différences de nommage entre les fournisseurs.\n\n"
    "En cas d'erreurs, que ce soit en mode manuel ou automatique, vous pourrez les corriger "
    "par la suite à l'aide du script manage_urls.py.\n"
)

while True:
    auto_mode = input(
        "Souhaitez-vous utiliser le mode automatique pour associer les URL de votre "
        "fournisseur IPTV aux chaînes proposées par iptv-select.fr ? (oui / non) : "
    ).strip().lower()

    if auto_mode in answers:
        break
    print("Réponse invalide. Veuillez répondre par 'oui', 'non'")


valid_answers = {"oui", "non", ""}
selected = []

for line in lines:
    chan_low = normalize_channel_name(line)
    links = []

    for stream in live_info_data:
        stream_name_raw = stream.get("name", "")

        if not stream_name_raw or not isinstance(stream_name_raw, str):
            continue

        stream_name_raw = sanitize_stream_name(stream_name_raw)
        stream_name = stream_name_raw.lower().strip()

        if any(variant in stream_name for variant in candidates(chan_low)):
            links.append((stream_name_raw, stream["stream_id"]))
            continue

        # Special case for "france 3"
        if chan_low.startswith("france 3") and len(chan_low) > 8:
            f3_variant = chan_low.replace("france 3", "f3")
            if f3_variant in stream_name:
                links.append((stream_name_raw, stream["stream_id"]))

    if len(links) > 0:
        print(
            "*********************************************************************"
            f"\nVoici les résultats de la recherche de la chaine {chan_low}\n"
            "*********************************************************************"
        )
        for n, link in enumerate(links, start=1):
            print(f"  {n}) {link[0]}")
        fr_links = []
        if len(links) > 10:
            print(
                "\nLe nombre de liens url correspondant à la recherche de "
                f"la chaine {line[:-3]} est de {str(len(links))}. \n")
            while True:
                if auto_mode == "non":
                    answer = input(
                        "Il est parfois possible de réduire le nombre de "
                        "chaines sélectionnées en filtrant uniquement "
                        "les informations des chaines qui comportent "
                        "FR pour France. Voulez-vous réduire la "
                        "sélection des liens url correspondant à la "
                        f"chaine {line[:-3]}? Tapez directement "
                        "la touche 'entrée' pour filtrer ou répondre par oui ou non: "
                    ).lower()
                else:
                    answer = ""

                if answer in valid_answers:
                    break
                print("Réponse invalide. Veuillez répondre par 'oui', 'non' ou appuyer sur entrée.")
            if answer in ("oui", ""):
                fr_links = [link for link in links if "fr" in link[0].lower()]
                if fr_links:
                    print("\nChaînes filtrées (FR uniquement):")
                    for i, link in enumerate(fr_links, start=1):
                        print(f"  {i}) {link[0]}")
                else:
                    print(
                        "\nAucune chaîne contenant 'FR' n'a été trouvée. "
                        "Veuillez choisir un lien parmi la liste complète.\n"
                    )

        if len(fr_links) > 0:
            max_rank = len(fr_links)
        else:
            max_rank = len(links)
        while True:
            if auto_mode == "non":
                select = input(
                    "Quel lien url voulez-vous choisir pour la "
                    f"chaîne {line[:-3]}? (Tapez directement 'Entré' pour le choix 1 "
                    "ou bien 0 si aucun ne correspond): "
                )
            else:
                select = ""
            if select == "":
                select = 1
            try:
                select = int(select)
                if 0 <= select <= max_rank:
                    break
            except ValueError:
                pass
            print("Entrée invalide. Merci de saisir un nombre entre 0 et", max_rank)
        if len(fr_links) > 0:
            stream_id = fr_links[select - 1][1]
        else:
            stream_id = links[select - 1][1]
        if select == 0:
            selected.append(line + "\n")
        else:
            selected.append(f"{line}{stream_id}\n")
    else:
        selected.append(line + "\n")

original_ini_path = providers_dir / f"{iptv_provider}_original.ini"

with open(original_ini_path, "w", encoding="UTF-8") as ini:
    ini.write("[CHANNELS]" + "\n")
    for line in selected:
        ini.write(line)

secure_file_permissions(original_ini_path)

with open(original_ini_path, "r", encoding="utf-8") as ini:
    first_line = ini.readline()
    lines = ini.read().splitlines()

with open(ini_path, "w", encoding="UTF-8") as ini:
    ini.write("[CHANNELS]\n")
    for line in lines:
        line_info = line.split(" = ")
        stream_id = line_info[1].strip()
        if stream_id == "":
            formatted_url = ""
        else:
            formatted_url = url_format.format(
                server_url=server_url,
                username=username,
                password=password,
                stream_id=stream_id
            )
        ini.write(f"{line_info[0]} = {formatted_url}\n")

secure_file_permissions(ini_path)

m3ulinks_ini_path = providers_dir / f"{iptv_provider}_original_m3ulinks.ini"
shutil.copy(ini_path, m3ulinks_ini_path)

secure_file_permissions(m3ulinks_ini_path)

if auto_mode == "non":
    print(
        "\n Bravo !!! Vous avez configuré manuellement le fichier "
        f"{iptv_provider}.ini qui contient les liens "
        "de flux télévísés de plus de 200 chaines! :-)\n"
    )
else:
    print(
        f"\n Le fichier {iptv_provider}.ini de liens de flux télévísés a été configuré.\n"
    )
