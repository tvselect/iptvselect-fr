import subprocess
import os

from configparser import ConfigParser

user = os.environ.get("USER")

config_constants = ConfigParser()
config_constants.read("/home/" + user + "/.config/iptvselect-fr/constants.ini")

min_time_actual = config_constants["FUSION"]["MIN_TIME"]
safe_time_actual = config_constants["FUSION"]["SAFE_TIME"]

print(
    "Le script fusion_script.py permet d'assembler les différentes vidéos lorsque 1 ou 2 "
    "sauvegardes sont enregistrées en même temps que la vidéo du 1er fournisseur d'IPTV. "
    "Lors de l'assemblage des vidéos, celles qui sont ajoutées après la 1ère sont découpées "
    "afin de diminuer la différence de temps entre la fin de la vidéo dont "
    "l'enregistrement s'est arrêtée et le début de la prochaine vidéo ce qui facilite ainsi "
    "la lecture.\n"
    "\nLe script change_diff_time permet de modifier la différence de temps minimum entre 2 vidéos "
    "avant de couper le début de la 2ème vidéo. Par exemple, si les 2 vidéos ont les mêmes "
    "temps de diffusion (le programme commence en même temps pour les 2 fournisseurs d'IPTV) "
    "et que la différence de temps minimum est de 120 secondes, alors le début de la 2ème "
    "vidéo sera coupé si elle commence plus de 2 minutes avant la fin de la 1ère.\n\nCependant, "
    "à cause des différences importantes des temps de début de diffusion des programmes (un "
    "film peut commencer par exemple 60 secondes après chez un autre fournisseur d'IPTV), il "
    "est préférable d'ajouter un temps de sécurité afin de ne pas trop couper la vidéo "
    "suivante. Ce temps de sécurité peut également être modifié par le script change_diff_time.\n"
)

print("---------------------------------------------")
print(
    "\nLa différence de temps minimum entre 2 vidéos avant de couper le début de la 2ème vidéo est "
    "actuellement de " + min_time_actual + " secondes.\n"
)

answers = ["oui", "non"]
answer_mini = "maybe"

while answer_mini.lower() not in answers:
    answer_mini = input(
        "\nVoulez-vous modifier cette différence de temps minimum? (répondre par oui ou non): "
    )

if answer_mini.lower() == "oui":
    min_time = "Doit être un nombre"
    while min_time.isdigit() is False:
        min_time = input(
            "\nQuelle nouvelle valeur en seconde voulez-vous attribuer pour la "
            "différence de temps minimum entre 2 vidéos avant de couper le début "
            "de la 2ème vidéo?: "
        )
else:
    min_time = min_time_actual

print("---------------------------------------------")
print(
    "\nLe temps ajouté par sécurité avant de couper la 2ème vidéo est de "
    + safe_time_actual
    + " secondes."
)

if int(safe_time_actual) > int(min_time):
    print(
        "\nCette valeur est supérieure à la valeur de la différence de temps minimum entre 2 "
        "vidéos que vous avez défini. Le temps ajouté par sécurité ne pouvant être supérieur à"
        "la différence de temps minimum entre 2 vidéos, celui-ci sera égale à la valeur "
        "de " + min_time + " secondes si vous ne le modifiez pas."
    )
    safe_time_actual = min_time

answer_safe = "maybe"

while answer_safe.lower() not in answers:
    answer_safe = input(
        "\nVoulez-vous modifier cette différence de temps minimum? (répondre par oui ou non): "
    )

if answer_safe.lower() == "oui":
    safe_time = "Doit être un nombre"
    while safe_time.isdigit() is False:
        safe_time = input(
            "\nQuelle nouvelle valeur en seconde voulez-vous attribuer pour le "
            "temps ajouté par sécurité avant de couper la 2ème vidéo?: "
        )
        try:
            if int(safe_time) > int(min_time):
                print(
                    "\nCette valeur est supérieure à la valeur de la différence de temps "
                    "minimum entre 2 vidéos que vous avez défini. Le temps ajouté par sécurité "
                    "ne peut pas être supérieur à la différence de temps minimum entre 2 vidéos. "
                    "Veuillez définir une valeur inférieure ou égale à "
                    + min_time
                    + " secondes."
                )
                safe_time = "Doit être un nombre"
        except ValueError:
            print("\nLa valeur défini pour le temps doit être un nombre.")
else:
    safe_time = safe_time_actual

if answer_safe.lower() == "oui" or answer_mini.lower() == "oui":
    config_constants["FUSION"]["MIN_TIME"] = min_time
    config_constants["FUSION"]["SAFE_TIME"] = safe_time
    with open("/home/" + user + "/.config/iptvselect-fr/constants.ini", "w") as conf:
        config_constants.write(conf)

    if answer_mini.lower() == "oui" and answer_safe.lower() == "non":
        print(
            "Le temps minimum entre 2 vidéos avant de couper le début de la 2ème vidéo a "
            "bien été modifié dans le fichier fusion_script.py."
        )
    if answer_mini.lower() == "non" and answer_safe.lower() == "oui":
        print(
            "Le temps ajouté par sécurité avant de couper la 2ème vidéo a bien été "
            "modifié dans le fichier fusion_script.py"
        )
    else:
        print("\nLes valeurs ont bien été modifiées dans le fichier fusion_script.py")
else:
    print(
        "\nLes valeurs de différence de temps minimum et de temps ajoutés par sécurité n'ont "
        "pas été modifiées dans le fichier fusion_script.py"
    )
