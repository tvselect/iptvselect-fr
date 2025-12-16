import json
import requests
import shutil
import sys

from pathlib import Path
from config_manager import ConfigManager, is_valid_url

HEADERS = {
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip, deflate",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
}

def print_columns(channels, lines_per_column=30, column_width=35):
    import sys
    # Split channels into columns
    for i in range(lines_per_column):
        row_items = channels[i::lines_per_column]
        row = "".join(item.ljust(column_width) for item in row_items)
        print(row.rstrip(), flush=True)  # flush ensures immediate output

    # Optional: flush once more at the end
    sys.stdout.flush()

def candidates(name: str):
    # Yield possible normalized variants for matching
    yield name
    yield name.replace(" ", "")
    yield name.replace(" ", "-")
    yield name.replace(" ", "_")
    yield name.replace("'", "")
    yield name.replace("+", "")

def get_url_format():
    """Ask user for URL format with validation."""
    required_placeholders = ['{server_url}', '{username}', '{password}', '{stream_id}']

    while True:
        print("\nEntrez le format d'URL pour ce fournisseur IPTV.")
        print("Le format doit contenir exactement une fois chacun des éléments suivants:")
        print("  {server_url}, {username}, {password}, {stream_id}")
        print("\nExemple: {server_url}/live/{username}/{password}/{stream_id}.ts")

        url_format = input("\nFormat d'URL: ").strip()

        if not url_format:
            print("  Le format ne peut pas être vide.")
            continue

        errors = []
        for placeholder in required_placeholders:
            count = url_format.count(placeholder)
            if count == 0:
                errors.append(f"  {placeholder} est manquant")
            elif count > 1:
                errors.append(f"  {placeholder} apparaît {count} fois "
                              "(doit apparaître 1 seule fois)")

        if errors:
            for error in errors:
                print(error)
            continue

        print("  Format d'URL valide!")
        return url_format

def get_channels_to_exclude(channels, valid_answers):
    """
    Ask user which channels to exclude from modifications.

    Args:
        channels: List of available channel names
        valid_answers: List of valid yes/no answers (e.g., ['oui', 'non'])
    
    Returns:
        List of channel names to exclude
    """
    channels_to_exclude = []
    channels_lower = [ch.lower() for ch in channels]

    while True:
        while True:
            channel_to_exclude = input(
                "\nQuelle est la chaîne que vous voulez exclure des modifications ? : "
            ).strip()

            # Check if channel exists (case-insensitive)
            if channel_to_exclude.lower() in channels_lower:
                channels_to_exclude.append(channel_to_exclude)
                print(f"  '{channel_to_exclude}' ajoutée à la liste d'exclusion.")
                break

            # Channel not found - offer to display list
            print(f"  La chaîne '{channel_to_exclude}' n'est pas présente dans la liste.")

            if ask_yes_no("Voulez-vous afficher la liste des chaînes pour vous aider", valid_answers):
                print_columns(channels)

        # Ask if user wants to exclude another channel
        if not ask_yes_no("Voulez-vous exclure une autre chaîne", valid_answers):
            break

    return channels_to_exclude


def ask_yes_no(question, valid_answers):
    """
    Ask a yes/no question and return True for 'oui', False for 'non'.

    Args:
        question: Question to ask (without question mark or parentheses)
        valid_answers: List of valid answers (e.g., ['oui', 'non'])

    Returns:
        True if answer is 'oui', False if 'non'
    """
    while True:
        answer = input(f"\n{question} ? (oui/non) : ").strip().lower()

        if answer in valid_answers:
            return answer == "oui"

        print("  Réponse invalide. Veuillez répondre par 'oui' ou 'non'.")


def get_live_info_data(server_url, username, password, iptv_provider, HEADERS, is_valid_url):
    """
    Retrieves live stream information from the IPTV provider using Xtream codes.
    If the request fails, offers the user the option to modify their Xtream codes
    or exit the program.

    Returns:
        dict: live_info_data
    """
    live_info_data = {}


    while not live_info_data:
        print("Le programme va tenter de télécharger les informations des flux "
              "des directs des chaines de votre fournisseur d'IPTV "
              f"{iptv_provider} avec ces codes Xtream: \n")
        print(f" URL du serveur: {server_url}\n"
              f" Nom d'utilisateur: {username}\n"
              f" Mot de passe: {password})\n")
        host_url = f"{server_url}/player_api.php"
        params = {
            'username': username,
            'password': password,
            'action': 'get_live_streams',
        }

        try:
            resp = requests.get(host_url, params=params, headers=HEADERS, timeout=(3, 20))
            resp.raise_for_status()
            live_info_data = resp.json()
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            live_info_data = {}
        except ValueError:
            print("Failed to decode JSON")
            live_info_data = {}

        # Handle failed response
        if not live_info_data:
            print(
                f"\nLe téléchargement des données du fournisseur IPTV {iptv_provider} a échoué.\n"
                "Merci de vérifier vos codes Xtream. Si le problème persiste, "
                "contactez votre fournisseur IPTV pour obtenir de l'aide."
            )

            answers_xtream_modify = {"1": "modify_xtream", "2": "exit"}
            while True:
                print("\nChoisissez l'une des options suivantes:")
                for key, value in answers_xtream_modify.items():
                    if value == "modify_xtream":
                        print(
                            f"{key}) Modifier mes codes Xtream et réessayer le téléchargement."
                        )
                    elif value == "exit":
                        print(
                            f"{key}) Quitter le programme pour vérifier mes codes Xtream."
                        )
                xtream_modify_answer = input("\nVotre choix: ").strip()
                if xtream_modify_answer in answers_xtream_modify:
                    break
                print("\nVeuillez choisir une option valide (1 ou 2).\n")

            # Modify Xtream codes
            if xtream_modify_answer == "1":
                print(
                    f"\nVoici vos codes Xtream enregistrés pour le fournisseur IPTV {iptv_provider}:\n"
                    f"  URL: {server_url}\n"
                    f"  Nom d'utilisateur: {username}\n"
                    f"  Mot de passe: {password}\n"
                )

                answers_xtream_option = {"1": "server_url", "2": "username", "3": "password"}
                while True:
                    print("\nQuel élément souhaitez-vous modifier ?")
                    for key, value in answers_xtream_option.items():
                        label = {
                            "server_url": "URL du serveur",
                            "username": "Nom d'utilisateur",
                            "password": "Mot de passe"
                        }[value]
                        print(f"{key}) {label}")
                    xtream_option_answer = input("\nVotre choix: ").strip()
                    if xtream_option_answer in answers_xtream_option:
                        break
                    print("\nVeuillez choisir une option valide (1, 2 ou 3).\n")

                # Update selected field
                if xtream_option_answer == "1":
                    while True:
                        server_url = input(
                            "\nSaisissez l'URL fournie par votre fournisseur IPTV pour Xtream Codes :\n"
                            "(Exemple : https://monsuperiptv.com)\n"
                            "(Raccourcis : Ctrl+Maj+V sur Linux, Cmd+V sur macOS, clic droit > Coller sur Windows)\n\n"
                        )
                        if not is_valid_url(server_url):
                            print("\nURL invalide. Veuillez saisir une URL complète commençant par http:// ou https://")
                        else:
                            break
                elif xtream_option_answer == "2":
                    username = input("\nSaisissez votre nom d'utilisateur : ")
                elif xtream_option_answer == "3":
                    password = input("\nSaisissez votre mot de passe : ")

            else:
                print("Sortie du programme.")
                sys.exit()

    return live_info_data, server_url, username, password


print("Configuration des URLs de votre fournisseur IPTV :\n")

print(
    "Le programme manage_urls.py permet de modifier les URLs enregistrées dans les fichiers "
    "ayant l’extension .ini (exemple : moniptv.ini), ainsi que les identifiants des chaînes "
    "présents dans les fichiers se terminant par _original.ini (exemple : moniptv_original.ini)."
)

iptv_provider = input(
    "\nQuel est le nom du fournisseur IPTV dont vous souhaitez modifier les informations ? "
    "(Ce nom doit correspondre à celui que vous avez saisi lors de l’exécution du script "
    "xtream_codes_data.py, ou au nom de l’un des fichiers se terminant par _original.ini "
    "dans le dossier ~/.config/iptvselect-fr/iptv_providers) :\n"
)

providers_dir = Path.home() / ".config/iptvselect-fr/iptv_providers"

original_ini = providers_dir / f"{iptv_provider}_original.ini"

if original_ini.exists():
    print(f"\nLe fichier {iptv_provider}_original.ini est présent dans le dossier "
          "~/.config/iptvselect-fr/iptv_providers\n")
else:
    print(f"\nLe fichier {iptv_provider}_original.ini n'est pas présent dans le dossier "
          "~/.config/iptvselect-fr/iptv_providers . Vous devez le construire au "
          "moyen du programme xtream_codes_data.py ou si vous l'avez obtenu par "
          "un autre moyen le placer dans le dossier ~/.config/iptvselect-fr/iptv"
          "_providers.\n")
    print("Sortie du programme")
    sys.exit()

cfg = ConfigManager()

iptv_providers_listed = cfg.list_providers()

need_xtream_codes = False

if len(iptv_providers_listed) == 0:
    print("Votre liste de codes Xtream est vide.")
    need_xtream_codes = True

match = next(
    (item for item in iptv_providers_listed if item["iptv_provider"] == iptv_provider),
    None)

if len(iptv_providers_listed) > 0:
    print("Voici la liste de vos codes Xtream déjà enregistrés:\n")
    for n, code in enumerate(iptv_providers_listed, start=1):
        print(f" {n}) Fournisseur IPTV: {code['iptv_provider']}\n"
              f"  URL: {code['server_url']}\n"
              f"  Nom d'utilisateur: {code['username']}\n"
              f"  Mot de passe: {code['password']}\n"
              f"  Format d'URL:  {code['url_format']}"
              "\n-----------------------------------")
    if match:
        print(f"\nLe fournisseur d'IPTV {iptv_provider} est présent dans votre "
                "liste de codes Xtream déjà enregistrés.\n")
    else:
        print(f"\nLe fournisseur d'IPTV {iptv_provider} n'est pas présent dans votre "
              "liste de codes Xtream déjà enregistrés.\n")
        need_xtream_codes = True

codes_modified = False

if need_xtream_codes:
    url_format = "{server_url}/live/{username}/{password}/{stream_id}.ts"

    while True:
        server_url = input("\nSaisissez l'URL de votre founisseur IPTV qu'il vous a fourni pour "
                        "utiliser avec les Xtream Codes (pour faciliter la saisie vous pouvez "
                        "coller le lien avec le raccourci): \n"
                        "- 'Ctrl + Maj + V' dans la plupart des terminaux Linux, \n"
                        "- 'Cmd (⌘) + V' sur macOS, \n"
                        "- ou avec un clic droit > 'Coller' dans PowerShell sous Windows) : \n")

        if not is_valid_url(server_url):
            print("\nURL invalide. Veuillez saisir une URL complète commençant par "
                  "http:// ou https:// (exemple : https://monsuperiptvquivabien.com)")
        else:
            break

    username = input("\nSaisissez votre nom d'utilisateur: ")

    password = input("\nSaisissez votre mot de passe: ")

    codes_modified = True

if match:
    server_url = match["server_url"]
    username = match["username"]
    password = match["password"]
    url_format = match["url_format"]

live_info_data, server_url, username, password = get_live_info_data(
    server_url, username, password, iptv_provider, HEADERS, is_valid_url
)

live_info_path = Path.home() / ".config/iptvselect-fr/iptv_providers" / f"{iptv_provider}.json"

with open(live_info_path, "w", encoding="UTF-8") as file:
    json.dump(live_info_data, file, ensure_ascii=False, indent=4)

print(f"Le téléchargement des données du fournisseur d'IPTV {iptv_provider} a été "
      "réalisé avec succès. ")

cfg.add_or_update_provider(iptv_provider, server_url, username, password, url_format)

print(
    f"\nLes identifiants Xtream du fournisseur {iptv_provider} ont été enregistrés dans "
    "le fichier de configuration ~/.config/iptvselect-fr/xtream_codes.json. "
    "Si vous venez de modifier ces identifiants, le fichier "
    f"{iptv_provider}.ini n’a pas encore été mis à jour. "
    "Vous devrez sélectionner l’option 2 à l’étape suivante (modifier toutes "
    "les URLs) puis l'option 5 ('Je viens de modifier mes codes Xtream...') pour mettre à jour toutes "
    "les URLs du fichier. Relancez le programme à chaque modification des codes."
)


source = Path("iptv_providers/iptv_select_channels.ini")
ini_path = providers_dir / f"{iptv_provider}.ini"

if ini_path.exists():
    print(f"\nLe fichier {iptv_provider}.ini est présent dans le dossier "
          "~/.config/iptvselect-fr/iptv_providers\n")
else:
    shutil.copy2(source, ini_path)

    with open(original_ini, "r", encoding="utf-8") as ini:
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

    m3ulinks_ini_path = providers_dir / f"{iptv_provider}_original_m3ulinks.ini"
    shutil.copy(ini_path, m3ulinks_ini_path)

    print(f"\nLes fichiers {iptv_provider}.ini et {iptv_provider}_original_m3ulinks.ini"
          " ont été créé à partir des numéros d'identification des chaine présents "
          f"dans le fichier {iptv_provider}_orginal.ini et des codes xtream.")
    codes_modified = False

channels_file = Path.home() / "iptvselect-fr/iptv_providers/iptv_select_channels.ini"

with open(channels_file, "r", encoding="UTF-8") as chan:
    channels_iptvselect = chan.readlines()
    channels_iptvselect = [line.rstrip('\n').split(' = ')[0] for line in channels_iptvselect[1:]]

valid_answers = {"oui", "non"}
url_user_answer = "5"

if codes_modified:
    print(f"Les codes Xtream ont été modifiés. Le fichier {iptv_provider}.ini va "
          "maintenant être modifié pour prendre en compte ces nouvelles "
          "modifications.")

    while True:
        answer_exclude = input("\nVoulez vous exclure de la modification "
                                "certaines chaines? (répondre par "
                                "oui ou non): ").strip().lower()
        if answer_exclude in valid_answers:
            break
        print("\nRéponse invalide. Veuillez répondre par 'oui', 'non'.")

    if answer_exclude == "oui":
        excluded = get_channels_to_exclude(channels_iptvselect, valid_answers)
        print(f"\n  Chaînes exclues : {', '.join(excluded)}")
    else:
        excluded = []

    ini_bak = providers_dir / f"{iptv_provider}.ini.bak"
    shutil.copy2(ini_path, ini_bak)

    print(f"Une sauvegarde de votre fichier {iptv_provider}.ini "
            f"a été réalisé dans le fichier {iptv_provider}.ini.bak")

    with open(original_ini, "r", encoding="utf-8") as ini:
        first_line = ini.readline()
        lines = ini.read().splitlines()

    with open(ini_path, "r", encoding="utf-8") as ini:
        first_line = ini.readline()
        lines_ini = ini.read().splitlines()

    with open(ini_path, "w", encoding="UTF-8") as ini:
        ini.write("[CHANNELS]\n")
        for line in lines:
            line_info = line.split(" = ")
            if line_info[0] in excluded:
                matched_line = next(
                    (item for item in lines_ini if item.split(" = ", 1)[0].strip() == line_info[0]),
                    None
                    )
                ini.write(matched_line + "\n")
            else:
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

    m3ulinks_ini_path = providers_dir / f"{iptv_provider}_original_m3ulinks.ini"
    shutil.copy(ini_path, m3ulinks_ini_path)

    print(f"\nLes fichiers {iptv_provider}.ini et {iptv_provider}_original"
          "_m3ulinks.ini ont été modifiés à partir des numéros "
          "d'identification des chaines présents "
          f"dans le fichier {iptv_provider}_original.ini et des nouveaux "
          "codes xtream.")
    url_user_answer = "4"

if url_user_answer != "4":
    with open(ini_path, "r", encoding="utf-8") as chan:
        channels = chan.readlines()
        channels_url = [line.rstrip('\n') for line in channels[1:]]

    answers_url_link = {"1": "single_channel", "2": "all_channels", "3": "exit"}

    while True:
        print("\nChoisissez l'une des options suivantes:")
        for key, value in answers_url_link.items():
            if value == "single_channel":
                print(f"{key}) Je veux modifier une chaine spécifique tel que son numéro "
                    "d'identification ou même l'entière URL.")
            elif value == "all_channels":
                print(f"{key}) Je veux modifier toutes les URLs ou un grand nombre d'URLs. "
                    "Je souhaite par exemple modifier mon mot de passe, mon nom "
                    "d'utilisateur ou l'URL du server pour toutes les chaines.")
            elif value == "exit":
                print(f"{key}) Je veux sortir du programme.")

        url_user_answer = input("\nVotre choix: ").strip()

        if url_user_answer in answers_url_link:
            break
        print("\nVeuillez choisir une option valide (1, 2 ou 3).\n")

answers_single_chan = {"1": "stream_id", "2": "url"}

if url_user_answer == "1":
    while True:
        channel_to_update = input("\nQuelle est la chaine que vous voulez modifier?: ")
        if channel_to_update.lower() in [ch.lower() for ch in channels_iptvselect]:
            break
        print(f"\nLa chaîne {channel_to_update} n'est pas présente dans la liste "
                "des chaines d'IPTV-select.fr .")
        while True:
            answer_display = input("\nVoulez vous afficher la liste des chaines "
                                    "pour vous aider? (répondre par "
                                    "oui ou non): ").strip().lower()
            if answer_display in valid_answers:
                break
            print("\nRéponse invalide. Veuillez répondre par 'oui', 'non'.")
        if answer_display == "oui":
            print_columns(channels_iptvselect)

    while True:
        specify_search = input("\nVoulez vous associer une recherche différente pour "
                               f"la chaine {channel_to_update}? Si vous avez par "
                               "exemple choisi la chaine BFMTV vous "
                               "pourrez ainsi spécifier une recherche différente tel que 'BFM TV'"
                                "(répondre par oui ou non): ").strip().lower()
        if specify_search in valid_answers:
            break
        print("\nRéponse invalide. Veuillez répondre par 'oui', 'non'.")

    if specify_search == "oui":
        search_channel = input("\nSaisissez la recherche défini pour "
                                f"la chaine {channel_to_update}: ")
    else:
        search_channel = channel_to_update

    while True:
        print("\nChoisissez l'une des options suivantes:")
        for key, value in answers_single_chan.items():
            if value == "stream_id":
                print(f"{key}) Je souhaite modifier le numéro d'identification de la chaine.")
            elif value == "url":
                print(f"{key}) Je souhaite modifier l'URL complète de la chaine")

        user_answer = input("\nVotre choix: ").strip()

        if user_answer in answers_single_chan:
            break
        print("\nVeuillez choisir une option valide (1 ou 2).\n")

    if user_answer == "1":
        answers_stream_id = {"1": "known_id", "2": "unknown_id", "3": "exit"}
        while True:
            print("\nChoisissez l'une des options suivantes:")
            for key, value in answers_stream_id.items():
                if value == "known_id":
                    print(f"{key}) Je connais le numéro d'identification de la chaine.")
                elif value == "unknown_id":
                    print(f"{key}) Je ne connais pas le numéro d'identification de la chaine "
                          "et je veux que l'on me propose une liste de chaînes pour "
                          "choisir un numéro d'identication")

            id_stream_user_answer = input("\nVotre choix: ").strip()

            if id_stream_user_answer in answers_stream_id:
                break
            print("\nVeuillez choisir une option valide (1 ou 2).\n")

        if id_stream_user_answer == "1":
            while True:
                new_stream_id = input("Numéro d'identification de la chaîne: ").strip()
                if not new_stream_id:
                    print("  Le numéro ne peut pas être vide.")
                elif not new_stream_id.isdigit():
                    print("  Veuillez entrer uniquement des chiffres.")
                else:
                    break
        else:
            chan_low = search_channel.lower()
            links = []

            for stream in live_info_data:
                # Safely get name with default empty string
                stream_name_raw = stream.get("name", "")

                if not stream_name_raw or not isinstance(stream_name_raw, str):
                    continue

                stream_name = stream_name_raw.lower().strip()

                # Match on all normalized variants
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
                    print(f"  {n}) {link[0]} ------- stream id = {link[1]} ")
                fr_links = []
                if len(links) > 10:
                    print(
                        "\nLe nombre de liens url correspondant à la recherche de "
                        f"la chaine {chan_low} est de {str(len(links))}. \n")
                    while True:
                        answer = input(
                            "Il est parfois possible de réduire le nombre de "
                            "chaines sélectionnées en filtrant uniquement "
                            "les informations des chaines qui comportent "
                            "FR pour France. Voulez-vous réduire la "
                            "sélection des liens url correspondant à la "
                            f"chaine {chan_low}? (répondre par oui ou non): "
                        ).lower()

                        if answer in valid_answers:
                            break
                        print("Réponse invalide. Veuillez répondre par 'oui' ou 'non'")
                    if answer in ("oui", ""):
                        fr_links = [link for link in links if "fr" in link[0].lower()]
                        if fr_links:
                            print("\nChaînes filtrées (FR uniquement):")
                            for i, link in enumerate(fr_links, start=1):
                                print(f"  {i}) {link[0]} ------- stream id = {link[1]}")
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
                    select = input(
                        "Quel numéro d'identification voulez-vous choisir pour la "
                        f"chaîne {chan_low}? (Tapez directement 'Entré' pour le choix 1 "
                        "ou bien 0 si aucun ne correspond): "
                    )
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
                    new_stream_id = fr_links[select - 1][1]
                else:
                    new_stream_id = links[select - 1][1]
            else:
                print(f"Aucune chaine contenant le terme de recherche {search_channel} "
                      f"n'est présente chez votre fournisseur d'IPTV {iptv_provider}")
                print("Sortie du programme")
                sys.exit()

            if select == 0:
                print("\nVous n'avez sélectionnez aucun numéro d'identification pour "
                    f"la chaîne {chan_low}.")
                answers_no_id = {"1": "keep_id", "2": "cancel_channel"}
                while True:
                    print("\nChoisissez l'une des options suivantes:")
                    for key, value in answers_no_id.items():
                        if value == "keep_id":
                            print(
                                f"{key}) Je ne souhaite pas modifier la chaine "
                                f"{chan_low}."
                            )
                        elif value == "cancel_channel":
                            print(
                                f"{key}) Je souhaite retirer la chaîne {chan_low} "
                                "de la liste des chaînes disponibles pour l'enregistrement "
                                f"de mon fournisseur IPTV {iptv_provider}. Le fichier "
                                f"{iptv_provider}_original.ini ne contiendra plus "
                                "d'identifiant pour cette chaîne et le fichier "
                                f"{iptv_provider}.ini ne comportera plus d'URL associée."
                            )
                    no_id_choice = input("\nVotre choix: ").strip()
                    if no_id_choice in answers_no_id:
                        break
                    print("\nVeuillez choisir une option valide (1 ou 2).\n")

                if no_id_choice == "1":
                    print("Aucune chaine de remplacement n'a été sélectionnée. Les fichiers "
                        f"{iptv_provider}_original.ini et {iptv_provider}.ini n'ont pas "
                        "été modifiés.\nSortie du programme")
                    sys.exit()
                else:
                    new_stream_id = ""

        formatted_url = url_format.format(
            server_url=server_url,
            username=username,
            password=password,
            stream_id=new_stream_id
        )

        with open(original_ini, "r", encoding="utf-8") as ini:
            first_line = ini.readline()
            lines = ini.read().splitlines()

        old_stream_id = ""

        with open(original_ini, "w", encoding="utf-8") as ini:
            ini.write("[CHANNELS]\n")
            for line in lines:
                if line.split(" = ")[0].lower() == channel_to_update.lower():
                    old_stream_id = line.split(" = ")[1]
                    ini.write(f"{line.split(' = ')[0]} = {new_stream_id}\n")
                else:
                    ini.write(line + "\n")

        if old_stream_id == "":
            if new_stream_id == "":
                print(f"Aucun numéro d'identification de la chaîne {channel_to_update} n'a "
                      f"été ajouté dans le fichier {iptv_provider}_original.ini .")
            else:
                print(f"Le numéro d'identification {new_stream_id} a été ajouté "
                    f"à la chaîne {channel_to_update} dans le fichier "
                    f"{iptv_provider}_original.ini .")
        else:
            if new_stream_id == "":
                print(f"Le numéro d'identification {old_stream_id} de la "
                      f"la chaîne {channel_to_update} a été supprimé "
                      f" dans le fichier {iptv_provider}_original.ini .")
            else:
                print(f"Le numéro d'identification {old_stream_id} a été remplacé "
                    f"par le numéro d'identification {new_stream_id} pour "
                    f"la chaîne {channel_to_update} dans le fichier "
                    f"{iptv_provider}_original.ini .")

    if user_answer == "2":
        while True:
            formatted_url = input("Saisir l'URL à ajouter ou remplacer pour la chaine "
                        f"{channel_to_update}: ")
            if not is_valid_url(server_url):
                print("\nURL invalide. Veuillez saisir une URL complète commençant par "
                    "http:// ou https:// ")
            else:
                break

    for idx, chan in enumerate(channels_url):
        chan_name, chan_url = chan.split(" = ")
        if channel_to_update.lower() == chan_name.lower():
            if new_stream_id == "":
                channels_url[idx] = f"{chan_name} = "
            else:
                channels_url[idx] = f"{chan_name} = {formatted_url}"
            break

    ini_bak = providers_dir / f"{iptv_provider}.ini.bak"
    shutil.copy2(ini_path, ini_bak)

    print(f"Une sauvegarde de votre fichier {iptv_provider}.ini "
            f"a été réalisé dans le fichier {iptv_provider}.ini.bak")

    with open(ini_path, "w", encoding="UTF-8") as ini:
        ini.write("[CHANNELS]\n")
        for line in channels_url:
            ini.write(f"{line}\n")

    if chan_url == "":
        if new_stream_id == "":
            print(f"Aucune URL n'a été ajouté à la chaîne {chan_name}.")
        else:
            print(f"La chaîne {chan_name} ne possèdait pas d'URL. L'URL "
                    f"{formatted_url} a été ajouté.")
    else:
        if new_stream_id == "":
            print(f"L'URL {chan_url} a été supprimé pour la chaîne {chan_name}.")
        else:
            print(f"L'URL {chan_url} de la chaine {chan_name} a été remplacé "
                    f"par l'URL {formatted_url}.")

elif url_user_answer == "2":
    answers_replace = {"1": "server_url",
                       "2": "username",
                       "3": "password",
                       "4": "url_format",
                       "5": "new_codes"}
    while True:
        print("\nChoisissez l'une des options suivantes:")
        for key, value in answers_replace.items():
            if value == "server_url":
                print(f"{key}) Je souhaite modifier l'URL du server de mon fournisseur "
                      f"d'IPTV {iptv_provider}.")
            elif value == "username":
                print(f"{key}) Je souhaite modifier mon nom d'utilisateur pour mon fournisseur "
                      f"d'IPTV {iptv_provider}.")
            elif value == "password":
                print(f"{key}) Je souhaite modifier mon mot de passe pour mon fournisseur "
                      f"d'IPTV {iptv_provider}.")
            elif value == "url_format":
                print(f"{key}) Je souhaite modifier le format d'URL de mon fournisseur "
                      f"d'IPTV {iptv_provider}.")
            elif value == "new_codes":
                print(f"{key}) Je viens de modifier mes codes Xtream à l'étape "
                      "précédente et je veux mettre à jour mon fichier "
                      f"{iptv_provider}.ini .")

        replace_user_answer = input("\nVotre choix: ").strip()

        if replace_user_answer in answers_replace:
            break
        print("\nVeuillez choisir une option valide (chiffre entre 1 et 5).\n")

    if replace_user_answer == "1":
        print("\nL'URL du server que vous allez remplacer pour votre fournisseur "
              f"d'IPTV {iptv_provider} est {server_url}")
        replace = "URL du server"
        while True:
            server_url = input("\nSaisissez votre nouvelle URL que votre founisseur "
                            "IPTV vous a fourni pour utiliser avec les Xtream "
                            "Codes (pour faciliter la saisie vous pouvez "
                            "coller le lien avec le raccourci): \n"
                            "- 'Ctrl + Maj + V' dans la plupart des terminaux Linux, \n"
                            "- 'Cmd (⌘) + V' sur macOS, \n"
                            "- ou avec un clic droit > 'Coller' dans PowerShell sous Windows) : \n")

            if not is_valid_url(server_url):
                print("\nURL invalide. Veuillez saisir une URL complète "
                      "commençant par http:// ou https:// "
                    "(exemple : https://monsuperiptvquivabien.com)")
            else:
                break
    elif replace_user_answer == "2":
        print("\nLe nom d'utilisateur que vous allez remplacer pour votre fournisseur "
              f"d'IPTV {iptv_provider} est {username}")
        username = input("\nSaisissez votre nouveau nom d'utilisateur: ")
    elif replace_user_answer == "3":
        print("\nLe mot de passe que vous allez remplacer pour votre fournisseur "
              f"d'IPTV {iptv_provider} est {password}")
        password = input("\nSaisissez votre nouveau mot de passe: ")
    elif replace_user_answer == "4":
        print("\nLe format d'URL que vous allez remplacer pour votre fournisseur "
                f"d'IPTV {iptv_provider} est {url_format}")

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

        while True:
            print("Choisissez un numéro correspondant au format d'URL de votre serveur "
                    "(si le format d'URL de votre fournisseur d'IPTV n'est pas "
                    "présent dans la liste, saisissez 0:")
            for i, fmt in enumerate(url_format_list, start=1):
                print(f"  {i}) {fmt}")

            format_choice = input("Votre choix: ").strip()

            if format_choice.isdigit() and 0 <= int(format_choice) <= len(url_format_list):
                if format_choice != "0":
                    url_format = url_format_list[int(format_choice) - 1]
                break
            print("Réponse invalide. Veuillez entrer un chiffre entre 0 et 9.")

        if format_choice == "0":
            url_format = get_url_format()
            print(f"Format enregistré: {url_format}")

    if int(replace_user_answer) < 4:
        live_info_data, server_url, username, password = get_live_info_data(
            server_url, username, password, iptv_provider, HEADERS, is_valid_url
        )


    while True:
        answer_exclude = input("\nVoulez vous exclure de la modification "
                                "certaines chaines? (répondre par "
                                "oui ou non): ").strip().lower()
        if answer_exclude in valid_answers:
            break
        print("\nRéponse invalide. Veuillez répondre par 'oui', 'non'.")

    if answer_exclude == "oui":
        excluded = get_channels_to_exclude(channels_iptvselect, valid_answers)
        print(f"\n  Chaînes exclues : {', '.join(excluded)}")
    else:
        excluded = []

    ini_bak = providers_dir / f"{iptv_provider}.ini.bak"
    shutil.copy2(ini_path, ini_bak)

    print(f"Une sauvegarde de votre fichier {iptv_provider}.ini "
            f"a été réalisé dans le fichier {iptv_provider}.ini.bak")

    with open(original_ini, "r", encoding="utf-8") as ini:
        first_line = ini.readline()
        lines = ini.read().splitlines()

    with open(ini_path, "r", encoding="utf-8") as ini:
        first_line = ini.readline()
        lines_ini = ini.read().splitlines()

    with open(ini_path, "w", encoding="UTF-8") as ini:
        ini.write("[CHANNELS]\n")
        for line in lines:
            line_info = line.split(" = ")
            if line_info[0] in excluded:
                matched_line = next(
                    (item for item in lines_ini if item.split(" = ", 1)[0].strip() == line_info[0]),
                    None
                    )
                ini.write(matched_line + "\n")
            else:
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

    m3ulinks_ini_path = providers_dir / f"{iptv_provider}_original_m3ulinks.ini"
    shutil.copy(ini_path, m3ulinks_ini_path)

    print(f"\nLes fichiers {iptv_provider}.ini et {iptv_provider}_original"
          "_m3ulinks.ini ont été modifiés à partir des numéros "
          "d'identification des chaines présents "
          f"dans le fichier {iptv_provider}_orginal.ini et des codes Xtream.")

    cfg.add_or_update_provider(iptv_provider, server_url, username, password, url_format)

    print(f"\nLes codes Xtream du fournisseur {iptv_provider} ont également été modifiés.")

print("Sortie du programme")

