import logging
import subprocess
import argparse
import shlex
import os

from configparser import ConfigParser

user = os.environ.get("USER")

config_constants = ConfigParser()
config_constants.read("/home/" + user + "/.config/iptvselect-fr/constants.ini")

MIN_TIME = int(config_constants["FUSION"]["MIN_TIME"])
SAFE_TIME = int(config_constants["FUSION"]["SAFE_TIME"])

parser = argparse.ArgumentParser()
parser.add_argument("title")
parser.add_argument("provider_iptv_recorded")
parser.add_argument("provider_iptv_backup")
parser.add_argument("provider_iptv_backup_2")
args = parser.parse_args()

logging.basicConfig(
    filename=os.path.expanduser("~/.local/share/iptvselect-fr/logs/fusion.log"),
    format="%(asctime)s %(levelname)s: %(message)s",
    level=logging.INFO,
)

path_video = "/home/" + user + "/videos_select/{title}-save/".format(title=args.title)

first_movies = []
providers_list = []

"Order movies from iptv provider 1 by starting time:"

cmd = (
    "ls -rt /home/$USER/videos_select/{title}-save/"
    "{title}_{provider_iptv_recorded}_*_original*".format(
        title=shlex.quote(args.title),
        provider_iptv_recorded=shlex.quote(args.provider_iptv_recorded),
    )
)
output_1 = subprocess.Popen(
    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
)
stdout, stderr = output_1.communicate()
lst_movies_1 = stdout.decode("utf-8").split("\n")[:-1]
lst_movies_1[:] = (elem[len(path_video) :] for elem in lst_movies_1)

if len(lst_movies_1) == 0:
    logging.info(
        "Le fournisseur d'IPTV {provider_iptv_recorded} n'a fourni aucune "
        "vidéo pour le film {title}.".format(
            title=args.title, provider_iptv_recorded=args.provider_iptv_recorded
        )
    )
else:
    starts_1 = []

    try:
        with open(
            "/home/" + user + "/videos_select/{title}-save/start_time_"
            "{title}_{provider}_original.txt".format(
                title=args.title, provider=args.provider_iptv_recorded
            )
        ) as f:
            for time_epoch in f:
                starts_1.append(time_epoch)
    except FileNotFoundError:
        logging.info(
            "Le fichier /home/{user}/videos_select/{title}-save/start_time_"
            "{title}_{provider}_original.txt est absent. La fusion des "
            "vidéos ne peut pas être réalisée".format(
                user=user, title=args.title, provider=args.provider_iptv_recorded
            )
        )
        exit()

    list_movies_1 = []

    for a, b in zip(lst_movies_1, starts_1):
        cmd = (
            "ffprobe -i /home/$USER/videos_select/{title}-save/{video} -v quiet "
            "-show_entries format=duration -hide_banner -of default=noprint"
            "_wrappers=1:nokey=1".format(
                title=shlex.quote(args.title), video=shlex.quote(a)
            )
        )
        duration = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        duration.wait()
        stdout, stderr = duration.communicate()
        try:
            video_duration = int(float(stdout.decode("utf-8").strip("\n")))
        except ValueError:
            logging.warning(stderr.decode("utf-8"))
            continue
        list_movies_1.append(
            (int(b.strip("\n")), video_duration, int(b.strip("\n")) + video_duration, a)
        )

    for movie in list_movies_1:
        if movie[1] < 80:
            list_movies_1.remove(movie)
        else:
            break

    if len(list_movies_1) > 0:
        first_movies.append(list_movies_1[0])
        providers_list.append(list_movies_1)

"Order movies from iptv provider 2 by starting time:"

list_movies_2 = []

if args.provider_iptv_backup != "no_backup":
    cmd = (
        "ls -rt /home/$USER/videos_select/{title}-save/{title}_"
        "{provider_iptv_backup}_*_backup*".format(
            title=shlex.quote(args.title),
            provider_iptv_backup=shlex.quote(args.provider_iptv_backup),
        )
    )
    output_2 = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    stdout, stderr = output_2.communicate()
    lst_movies_2 = stdout.decode("utf-8").split("\n")[:-1]
    lst_movies_2[:] = (elem[len(path_video) :] for elem in lst_movies_2)

    if len(lst_movies_2) == 0:
        logging.info(
            "Le fournisseur d'IPTV {provider_iptv_backup} n'a fourni aucune "
            "vidéo pour le film {title}.".format(
                title=args.title, provider_iptv_backup=args.provider_iptv_backup
            )
        )
    else:
        starts_2 = []

        try:
            with open(
                "/home/" + user + "/videos_select/{title}-save/start_time_{title}_"
                "{provider}_backup.txt".format(
                    title=args.title, provider=args.provider_iptv_backup
                )
            ) as f:
                for time_epoch in f:
                    starts_2.append(time_epoch)
        except FileNotFoundError:
            logging.info(
                "Le fichier /home/{user}/videos_select/{title}-save/start_time_"
                "{title}_{provider}_backup.txt est absent. La fusion des "
                "vidéos ne peut pas être réalisée".format(
                    user=user, title=args.title, provider=args.provider_iptv_backup
                )
            )
            exit()

        for a, b in zip(lst_movies_2, starts_2):
            cmd = (
                "ffprobe -i /home/$USER/videos_select/{title}-save/{video} -v quiet "
                "-show_entries format=duration -hide_banner -of default=noprint"
                "_wrappers=1:nokey=1".format(
                    title=shlex.quote(args.title), video=shlex.quote(a)
                )
            )
            duration = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )
            duration.wait()
            stdout, stderr = duration.communicate()
            try:
                video_duration = int(float(stdout.decode("utf-8").strip("\n")))
            except ValueError:
                logging.warning(stderr.decode("utf-8"))
                continue
            list_movies_2.append(
                (
                    int(b.strip("\n")),
                    video_duration,
                    int(b.strip("\n")) + video_duration,
                    a,
                )
            )

        for movie in list_movies_2:
            if movie[1] < 80:
                list_movies_2.remove(movie)
            else:
                break

        if len(list_movies_2) > 0:
            first_movies.append(list_movies_2[0])
            providers_list.append(list_movies_2)

list_movies_3 = []

if args.provider_iptv_backup_2 != "no_backup_2":
    cmd = (
        "ls -rt /home/$USER/videos_select/{title}-save/{title}_"
        "{provider_iptv_backup}_*_backup_2*".format(
            title=shlex.quote(args.title),
            provider_iptv_backup=shlex.quote(args.provider_iptv_backup_2),
        )
    )
    output_3 = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    stdout, stderr = output_3.communicate()
    lst_movies_3 = stdout.decode("utf-8").split("\n")[:-1]
    lst_movies_3[:] = (elem[len(path_video) :] for elem in lst_movies_3)

    if len(lst_movies_3) == 0:
        logging.info(
            "Le fournisseur d'IPTV {provider_iptv_backup} n'a fourni aucune "
            "vidéo pour le film {title}.".format(
                title=args.title, provider_iptv_backup=args.provider_iptv_backup_2
            )
        )
    else:
        starts_3 = []

        try:
            with open(
                "/home/" + user + "/videos_select/{title}-save/start_time_{title}_"
                "{provider}_backup_2.txt".format(
                    title=args.title, provider=args.provider_iptv_backup_2
                )
            ) as f:
                for time_epoch in f:
                    starts_3.append(time_epoch)
        except FileNotFoundError:
            logging.info(
                "Le fichier /home/{user}/videos_select/{title}-save/start_time_"
                "{title}_{provider}_backup_2.txt est absent. La fusion des "
                "vidéos ne peut pas être réalisée".format(
                    user=user, title=args.title, provider=args.provider_iptv_backup_2
                )
            )
            exit()

        for a, b in zip(lst_movies_3, starts_3):
            cmd = (
                "ffprobe -i /home/$USER/videos_select/{title}-save/{video} -v quiet "
                "-show_entries format=duration -hide_banner -of default=noprint"
                "_wrappers=1:nokey=1".format(
                    title=shlex.quote(args.title), video=shlex.quote(a)
                )
            )
            duration = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )
            duration.wait()
            stdout, stderr = duration.communicate()
            try:
                video_duration = int(float(stdout.decode("utf-8").strip("\n")))
            except ValueError:
                logging.warning(stderr.decode("utf-8"))
                continue
            list_movies_3.append(
                (
                    int(b.strip("\n")),
                    video_duration,
                    int(b.strip("\n")) + video_duration,
                    a,
                )
            )

        for movie in list_movies_3:
            if movie[1] < 80:
                list_movies_3.remove(movie)
            else:
                break

        if len(list_movies_3) > 0:
            first_movies.append(list_movies_3[0])
            providers_list.append(list_movies_3)

if len(first_movies) == 1:
    logging.info(
        "Un seul fournisseur d'IPTV a pu permettre d'enregistrer des "
        "vidéos. La fusion des vidéos ne peut pas être réalisée."
    )
    exit()
elif len(first_movies) == 0:
    logging.info(
        "Aucun fournisseur d'IPTV n'a pu permettre d'enregistrer des "
        "vidéos. La fusion des vidéos ne peut pas être réalisée."
    )
    exit()

"Make a list of movies by time duration and start time:"

streams_best = []

list_movies = []

for list_movie in providers_list:
    for movie in list_movie:
        list_movies.append(movie)


max_end = 0

for movie in list_movies:
    end = movie[2]
    if end > max_end:
        max_end = end

continuum = True
last_continuous = []

while continuum:
    if len(streams_best) == 0:
        start = []
        for movie in list_movies:
            start.append(movie[0])
        index_min = [i for i, j in enumerate(start) if j == min(start)][0]
        streams_best.append(list_movies[index_min])
        list_movies.remove(list_movies[index_min])
    else:
        continuous = []
        for movie in list_movies:
            if movie[0] < streams_best[-1][2] < movie[2]:
                continuous.append(movie)
        if continuous == last_continuous:
            break
        if len(continuous) > 0:
            end = []
            for movie in continuous:
                end.append(movie[2])
            index_max = [i for i, j in enumerate(end) if j == max(end)][0]
            streams_best.append(continuous[index_max])
            list_movies.remove(continuous[index_max])
        else:
            continuum = False
        last_continuous = continuous[:]


movies_remaster = [streams_best[0][3]]

for n in range(len(streams_best) - 1):
    diff_time = streams_best[n][2] - streams_best[n + 1][0]
    cmd = (
        "ffprobe -i /home/$USER/videos_select/{title}-save/{file} -v "
        "quiet -print_format json -show_format -show_streams "
        "-hide_banner | grep -o "
        "-P '(?<=start_time\": \").*(?=\.)' | sed -n '1p'".format(
            title=shlex.quote(args.title), file=shlex.quote(streams_best[n + 1][3])
        )
    )
    start = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    stdout, stderr = start.communicate()

    if diff_time > MIN_TIME:
        start = int(stdout.decode("utf-8")) + diff_time - SAFE_TIME
    else:
        start = int(stdout.decode("utf-8"))
    logging.info(stdout.decode("utf-8"))
    logging.info("start_time: " + str(start))
    cmd = (
        "ffmpeg -seek_timestamp 1 -ss {start} -i "
        "/home/$USER/videos_select/{title}-save/{file_1} -y -c copy -copyts "
        "-to 10000000 -muxdelay 0 /home/$USER/videos_select/{title}-save/"
        "{file_2}_s.ts -loglevel quiet >> ~/.local/share/iptvselect-fr/logs/"
        "split_infos.log 2>&1".format(
            title=shlex.quote(args.title),
            start=start,
            file_1=shlex.quote(streams_best[n + 1][3]),
            file_2=shlex.quote(streams_best[n + 1][3][:-3]),
        )
    )
    file_split = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    file_split.wait()
    movies_remaster.append(streams_best[n + 1][3][:-3] + "_s.ts")

rank = 1

for stream in movies_remaster:
    cmd = (
        "cp /home/$USER/videos_select/{title}-save/{movie} /home/$USER/videos_select"
        "/{title}-save/{title}-to-watch/{rank}_{movie}".format(
            title=shlex.quote(args.title), movie=shlex.quote(stream), rank=rank
        )
    )
    cpfiles = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    cpfiles.wait()
    rank += 1

cmd = "touch /home/$USER/videos_select/{title}-save/{title}-to-watch/{title}_report.txt".format(
    title=shlex.quote(args.title)
)
touch = subprocess.Popen(
    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
)
touch.wait()

with open(
    "/home/" + user + "/videos_select/{title}-save/{title}-to-watch/{title}_"
    "report.txt".format(title=args.title),
    "w",
) as ini:
    if streams_best[-1][2] < max_end - 300:
        ini.write(
            "\nAttention! Une discontinuité de l'enregistrement apparait pour cette vidéo.\n"
        )
    else:
        ini.write("\nL'enregistrement semble être correcte.\n")

# To delete files with sizes = 0 bytes or not recorded:

cmd = "du -b /home/$USER/videos_select/{title}-save/*".format(
    title=shlex.quote(args.title)
)

dub = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
stdout, stderr = dub.communicate()
lst_movies = stdout.decode("utf-8").split("\n")[:-1]

movies_sorted = []

for movie in lst_movies:
    size, title = movie.split("\t")
    movies_sorted.append((int(size), title))

todelete = []
sizes = []

for movie in movies_sorted:
    if movie[0] == 0:
        todelete.append(movie[1])
    else:
        sizes.append(movie[0])
        if sizes.count(movie[0]) > 5:
            todelete.append(movie[1])

for movie in todelete:
    cmd = ("rm {movie}").format(movie=shlex.quote(movie))
    rmfiles = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    rmfiles.wait()
