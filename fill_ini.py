import subprocess
import readline
import re
import shlex
import os

from unidecode import unidecode

user = os.environ.get("USER")

channels = [
    "13eme rue",
    "al jazeera english",
    "altice studio",
    "bfm paris",
    "cartoon network",
    "chasse et peche",
    "cherie 25",
    "club rtl",
    "crime district",
    "nrj 12",
    "nrj hits",
    "ocs choc",
    "ocs geants",
    "ocs max",
]


def search_url(channels, m3u_file):
    """Search url for channels in m3u file"""

    match = False
    links = []
    crypted = 0

    for chan in channels:
        with open(
            "/home/" + user + "/.config/iptvselect-fr/iptv_providers/" + m3u_file + ".m3u",
            "r",
        ) as m3u:
            for link in m3u:
                if match is True:
                    m3u_link = link
                    part_link = re.findall(r".*\/", m3u_link)
                    if len(part_link) > 0:
                        part1 = part_link[0]
                        left = m3u_link.replace(part1, "")
                        if left.isdigit():
                            part2 = ""
                        else:
                            try:
                                part2 = re.findall(r"\..*", left)[0]
                            except IndexError:
                                part2 = ""
                        channel_id = m3u_link.replace(part1, "")
                        channel_id = channel_id.replace(part2, "")
                        if channel_id[-1] == "\n":
                            channel_id = channel_id[:-1]
                        if channel_id.isdigit():
                            if len(links) == 0:
                                links.append((part1, part2, 1))
                            else:
                                added = False
                                change = []
                                for indexo, url in enumerate(links):
                                    if url[0] == part1 and url[1] == part2:
                                        change.append(
                                            (indexo, url[0], url[1], url[2] + 1)
                                        )
                                        added = True
                                        break
                                if added is False:
                                    links.append((part1, part2, 1))
                                for ch in change:
                                    links[ch[0]] = (url[0], url[1], url[2] + 1)
                        else:
                            crypted += 1

                match = False
                if link[0] == "#":
                    link_low = unidecode(link.lower())
                    if "tvg-name" in link_low:
                        link_tvg = re.findall('tvg-name="(.*?)"', link_low)
                    else:
                        link_tvg = [link_low]
                    if len(link_tvg) > 0:
                        if (
                            chan in link_tvg[0]
                            or chan.replace(" ", "") in link_tvg[0]
                            or chan.replace(" ", "-") in link_tvg[0]
                            or chan.replace(" ", "_") in link_tvg[0]
                            or chan.replace("'", "") in link_tvg[0]
                            or chan.replace("+", "") in link_tvg[0]
                        ):
                            info = link
                            match = True

    return (links, crypted)


if __name__ == "__main__":
    iptv_provider = "@"

    while iptv_provider.isalnum() is False:
        iptv_provider = input(
            "Quel est le nom de votre fournisseur d'IPTV? "
            "(renseignez un nom ne contenant que des "
            "caractères alphanumériques sans espace): "
        )

    cmd = (
        "cp iptv_providers/iptv_select_channels.ini /home/"
        + user
        + "/.config/iptvselect-fr/iptv_providers/"
        "{provider}.ini".format(provider=shlex.quote(iptv_provider))
    )
    cp_ini = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    cp_ini.wait()

    with open(
        "/home/" + user + "/.config/iptvselect-fr/iptv_providers/" + iptv_provider + ".ini",
        "r",
    ) as ini:
        first_line = ini.readline()
        lines = ini.read().splitlines()

    m3u_file = "123456"
    ls_result = "abcdef"

    while ls_result != (
        "/home/" + user + "/.config/iptvselect-fr/iptv_providers/" + m3u_file + ".m3u"
    ):
        m3u_file = input(
            "Quel est le nom du fichier m3u de votre "
            "fournisseur d'IPTV? (renseignez le nom "
            "sans l'extension .m3u): "
        )
        cmd = (
            "ls /home/" + user + "/.config/iptvselect-fr/iptv_providers/{m3u_file}.m3u"
        ).format(m3u_file=shlex.quote(m3u_file))
        output = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        stdout, stderr = output.communicate()
        ls_result = stdout.decode("utf-8")[:-1]
        if ls_result != (
            "/home/" + user + "/.config/iptvselect-fr/iptv_providers/" + m3u_file + ".m3u"
        ):
            print(
                "Le fichier {m3u_file}.m3u n'est pas présent dans votre"
                " dossier ~/.config/iptvselect-fr/iptv_providers. "
                "Insérer le fichier m3u de votre fournisseur d'IPTV "
                "ou modifier le nom du fichier m3u pour qu'il corresponde "
                "à celui du fichier présent dans le dossier.\n".format(
                    m3u_file=m3u_file
                )
            )

    match = False

    print(
        "\nCertain fichier de liens m3u contiennent des urls chiffrées. Avec ce "
        "type de fichier, vous ne pourrez pas construire de fichiers .ini originaux "
        "car les identifiants des chaines ne peuvent pas être récupérés. Le script "
        "fill_ini.py se chargera dans ce cas de construire directement le "
        "fichier final .ini contenant les urls.\n"
    )

    answers = ["oui", "non", ""]

    print(
        "Le script fill_ini.py peut rechercher pour vous le lien urls correspondant "
        "aux chaines du fichier m3u de votre fournisseur d'IPTV.\n"
    )

    search = "nono"

    while search.lower() not in answers:
        search = input(
            "Voulez-vous lancer une recherche automatique? (répondre par oui ou non). "
            "Remarque: La recherche peut durer de nombreuses minutes si votre fichier "
            "m3u est volumineux: "
        )

    manual = "nono"
    crypted = "nono"

    if search.lower() == "oui" or search.lower() == "":
        print("\nLancement de la recherche des liens urls:\n")
        search_urls = search_url(channels, m3u_file)

        if len(search_urls[0]) == 0 and search_urls[1] > 0:
            print("\nLe script a déterminé que les liens urls sont chiffrés.\n")
            while manual.lower() not in answers:
                manual = input(
                    "\nSi vous pensez que c'est une erreur, vous pouvez "
                    "passer en mode manuel pour inscrire l'url "
                    "correspondante. Voulez-vous passer en mode manuel? "
                    "(Répondre par oui ou non): "
                )
            if manual.lower() == "non":
                crypted = "oui"
        elif len(search_urls[0]) == 0 and search_urls[1] == 0:
            print(
                "\nLe script fill_ini.py n'a pas pu déterminer de lien url dans "
                "votre fichier {m3u_file}.m3u".format(m3u_file=m3u_file)
            )
            manual = "oui"
        else:
            print("\nLe script fill_ini.py a déterminé l'url suivante: \n")
            url_provider = search_urls[0][0][0] + "channel_id" + search_urls[0][0][1]
            print(url_provider)
            print(
                "\n\nchannel_id représente la partie numérique correspondant "
                "aux différentes chaines."
            )
            while manual.lower() not in answers:
                manual = input(
                    "\nSi vous pensez que c'est une erreur, vous pouvez "
                    "passer en mode manuel pour inscrire l'url "
                    "correspondante. Voulez-vous passer en mode manuel? "
                    "(Répondre par oui ou non): \n"
                )

    if (
        search.lower() in ["oui", ""]
        and manual.lower() not in ["oui", ""]
        and crypted != "oui"
    ):
        with open("/home/" + user + "/.local/share/iptvselect-fr/urls.txt", "a") as file:
            file.write(iptv_provider + ": " + url_provider + "\n")

    extension = [".avi", ".mkv", ".mp4"]
    selected = []

    if search.lower() == "non" or manual == "oui" or manual == "":
        while crypted.lower() not in answers:
            crypted = input(
                "\nEst-ce-que les urls des liens m3u sont chiffrées? \n\nSi vous ne pouvez pas "
                "identifier un couple identifiant/mot de passe et un identifiant de chaine "
                "alors les liens m3u sont chiffrées. Exemple de liens m3u non chiffré: \n\n"
                "#chaine n°1\n"
                "http://fournisseuriptv-non-chiffré:8081/monsuperpseudo/khkjcbniufh/26491.ts\n"
                "#chaine n°2\n"
                "http://fournisseuriptv-non-chiffré:8081/monsuperpseudo/khkjcbniufh/36502.ts\n"
                "#chaine n°3\n"
                "http://fournisseuriptv-non-chiffré:8081/monsuperpseudo/khkjcbniufh/68582.ts\n"
                "\nOn remarque clairement un couple identifiant/mot de passe qui se répête et "
                "une partie numérique qui est différente pour chaque chaines.\n"
                "\nExemple de liens m3u chiffré: \n\n"
                "#chaine n°1\n"
                "http://fournisseuriptv-chiffré:8081/qwertyqfdkjh9skfhjkds8lsdqfksdfjddd/m3u8\n"
                "#chaine n°2\n"
                "http://fournisseuriptv-chiffré:8081/qwertysdfhqsklf7dsqkjfhds6qksdfdslk/m3u8\n"
                "#chaine n°3\n"
                "http://fournisseuriptv-chiffré:8081/qwertysqdfk6lkfhqskqsfjkd7sqdsfdsdq/m3u8\n"
                "\nDans ce cas on ne peut pas identifier un couple identifiant/mot de passe "
                "qui se répête ni une partie numérique qui est différente pour chaque chaines.\n"
                "Répondre par oui ou non: "
            )

        print("\n*************************************************************")

        url_provider = ""

        if crypted.lower() == "non":
            while "channel_id" not in url_provider:
                url_provider = input(
                    "\nQuel est le lien URL de votre fournisseur d'IPTV? Le lien doit mentionner "
                    "votre identifiant, votre mot de passe et le mot channel_id pour la partie correpondant aux "
                    "numéros qui sont déjà présents dans le fichier de configuration pour chaques chaînes. Voici "
                    "un exemple de lien à mentionner: \n\n"
                    "http://fournisseuriptv:8081/monsuperpseudo/khkjcbniufh/26491.ts qui peut être transcrit en \n"
                    "http://fournisseuriptv:8081/votre_identifiant/votre_mot_de_passe/channel_id.ts . Dans ce cas, "
                    "il vous faudra mentionner l'url suivante: \n"
                    "http://fournisseuriptv:8081/monsuperpseudo/khkjcbniufh/channel_id.ts\n"
                    "\nIl faut veiller à ne pas prendre un lien m3u qui correspond au streaming d'une vidéo car "
                    "ces liens m3u se terminent généralement par .mkv ou .avi et sont différents des liens m3u "
                    "correspondant aux chaines. Recherchez une chaine dans votre fichier m3u (par exemple "
                    "France 2) puis copiez/collez le lien m3u correspondant."
                    "\nIl suffit ensuite de remplacer le numéro correspondant à l'identification de la chaine. Voici un "
                    "autre exemple où channel_id remplace le numéro d'identification de la chaine: \n\n"
                    "http://fournisseuriptv:8081/monsuperpseudo/khkjcbniufh/26491 qui peut être transcrit en \n"
                    "http://fournisseuriptv:8081/votre_identifiant/votre_mot_de_passe/channel_id . Dans ce cas, "
                    "il vous faudra mentionner l'url suivante: \n"
                    "http://fournisseuriptv:8081/monsuperpseudo/khkjcbniufh/channel_id\n"
                )
                if "channel_id" not in url_provider:
                    print("\nVous n'avez pas renseigné le channel_id dans votre URL!\n")

    if crypted.lower() != "oui":
        splitted = url_provider.split("channel_id")

    chans_spec = ["lci", "lcp"]

    print(
        "\nLe script va maintenant vous proposer une sélection de liens m3u pour "
        "toutes les chaînes présentes dans iptv-select.fr . La durée pour "
        "afficher une sélection de chaines peut être de plusieurs secondes. "
        "Par exemple, la chaine France 3 est souvent longue car il faut "
        "attendre le filtrage des chaines régionales qui ne sont pas souvent "
        "présentes dans les fichiers m3u.\nIl faudra donc faire attention "
        "de ne pas appuyer plusieurs fois sur la touche entrée pour valider "
        "un choix de lien m3u et bien attendre le retour du curseur pour la "
        "prochaine question avant d'appuyer de nouveau sur la touche "
        "entrée (si vous appuyez plusieurs fois sur entrée pour une même "
        "chaine, les prochaines chaines seront sélectionnées sur le 1er "
        "lien m3u proposé).\n"
    )

    for line in lines:
        chan_low = line[:-3].lower()
        if chan_low[:3] in chans_spec:
            chan_low = chan_low[:3]
        with open(
            "/home/" + user + "/.config/iptvselect-fr/iptv_providers/" + m3u_file + ".m3u",
            "r",
        ) as m3u:
            links = []
            for link in m3u:
                if match is True and link[-5:-1] not in extension:
                    m3u_link = link
                    links.append((info, m3u_link))
                match = False
                if link[0] == "#":
                    link_low = unidecode(link.lower())
                    if "tvg-name" in link_low:
                        link_tvg = re.findall('tvg-name="(.*?)"', link_low)
                    else:
                        link_tvg = [link_low]
                    if len(link_tvg) > 0:
                        if (
                            chan_low in link_tvg[0]
                            or chan_low.replace(" ", "") in link_tvg[0]
                            or chan_low.replace(" ", "-") in link_tvg[0]
                            or chan_low.replace(" ", "_") in link_tvg[0]
                            or chan_low.replace("'", "") in link_tvg[0]
                            or chan_low.replace("+", "") in link_tvg[0]
                        ):
                            info = link
                            match = True
                        elif (
                            chan_low[:8] == "france 3"
                            and len(chan_low) > 8
                            and chan_low.replace("france 3", "f3") in link_tvg[0]
                        ):
                            info = link
                            match = True

        rank = 1
        rank_2 = 1
        ranking = []
        select = -1

        if len(links) > 0:
            print(
                "*********************************************************************"
                "\nVoici les résultats de la recherche de la chaine " + line[:-3] + "\n"
                "*********************************************************************"
            )
            for m3u in links:
                print(str(rank) + ")" + m3u[0])
                print(m3u[1])
                rank += 1
            answer = "answer"
            if len(links) > 10:
                print(
                    "\nLe nombre de liens m3u correspondant à la recherche de "
                    "la chaine " + line[:-3] + " est de " + str(len(links)) + ". \n"
                )
                while answer.lower() not in answers:
                    answer = input(
                        "Il est possible de réduire le nombre de "
                        "chaines sélectionnées en filtrant uniquement "
                        "les informations des chaines qui comportent "
                        "'fr' pour France. Voulez-vous réduire la "
                        "sélection des liens m3u correspondant à la "
                        "chaine " + line[:-3] + "? Tapez directement "
                        "la touche entrée pour filtrer ou répondre par oui ou non: \n\n"
                    )
                if answer.lower() == "oui" or answer == "":
                    rank, rank_2 = 1, 1
                    for m3u in links:
                        if "fr" in m3u[0].lower():
                            print(str(rank_2) + ")" + m3u[0])
                            print(m3u[1])
                            ranking.append(rank)
                            rank_2 += 1
                        rank += 1
            if len(ranking) > 0:
                max_rank = len(ranking) + 1
            else:
                max_rank = rank
                if answer.lower() == "oui" or answer == "":
                    print(
                        "\nLe filtre n'a pas permis de sélectionner des chaines qui comportent "
                        "'fr' pour France. Veuillez choisir un lien dans la liste précédemment "
                        "affichée.\n"
                    )
            while select < 0 or select > max_rank - 1:
                select = input(
                    "Quel lien m3u voulez-vous choisir pour la "
                    "chaîne "
                    + line[:-3]
                    + '? (Tapez directement "Entré" pour le choix 1 '
                    "ou bien 0 si aucun lien m3u ne correspond à la chaîne): "
                )
                if select == "":
                    select = 1
                try:
                    select = int(select)
                except ValueError:
                    select = -1
                    pass
            if len(ranking) > 0:
                select = ranking[select - 1]
            if select == 0:
                selected.append(line + "\n")
            elif crypted.lower() == "oui":
                selected.append(line + links[select - 1][1])
            else:
                link = links[select - 1][1]
                for part in splitted:
                    link = link.replace(part, "")
                selected.append(line + link)
        else:
            selected.append(line + "\n")

    if crypted.lower() == "oui":
        with open(
            "/home/"
            + user
            + "/.config/iptvselect-fr/iptv_providers/"
            + iptv_provider
            + ".ini",
            "w",
        ) as ini:
            ini.write("[CHANNELS]" + "\n")
            for line in selected:
                ini.write(line)
        cmd = (
            "cp /home/" + user + "/.config/iptvselect-fr/iptv_providers/"
            "{iptv_provider}.ini /home/" + user + "/.config/iptvselect-fr"
            "/iptv_providers/{iptv_provider}_original_m3ulinks.ini".format(
                iptv_provider=shlex.quote(iptv_provider)
            )
        )
        cp_ini = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        cp_ini.wait()

    else:
        with open(
            "/home/"
            + user
            + "/.config/iptvselect-fr/iptv_providers/"
            + iptv_provider
            + "_original.ini",
            "w",
        ) as ini:
            ini.write("[CHANNELS]" + "\n")
            for line in selected:
                ini.write(line)

    print(
        "\nBravo !!! Vous avez configuré un fichier de liens m3u de plus de 200 chaines! :-)\n"
    )
