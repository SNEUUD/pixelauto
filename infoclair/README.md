# L'info en clair — générateur de vidéos TikTok de vulgarisation informatique

Même principe que pixelauto : un épisode JSON devient une vidéo verticale d'environ
60 s (1080x1920, 30 i/s), avec voix off, sous-titres et musique. Le style est plat et
sobre : police Inter, icônes au trait, cartes à ombre douce, schémas animés, thème
clair ou sombre. Tout tourne en local : voix Piper (CPU), rendu Python/Pillow,
musique d'ambiance générée, encodage ffmpeg (NVENC possible).

## Installation (une fois)
    bash install.sh

## Générer une vidéo
    ./video.sh exemples/01_dns.json               # -> out/01_dns.mp4
    ./video.sh --all                              # tous les épisodes nouveaux ou modifiés de episodes/
    ./video.sh --all --force                      # tout refaire
    ./video.sh exemples/01_dns.json --preview 8 --tts silent   # 8 images PNG en 2 s, sans voix
Les réglages (voix, moteur, NVENC, musique) sont en tête de `video.sh`, ou dans un `config.sh`.
`--music ma_musique.mp3` remplace la musique générée (elle est bouclée et baisse
automatiquement quand la voix parle). `--no-music` garde la voix seule.

## Écrire un épisode
Un épisode = un JSON dans `episodes/` (deux exemples complets dans `exemples/`).
`PROMPT_EPISODE.md` est un prompt prêt à l'emploi pour qu'une IA écrive le JSON.

En-tête : `id`, `title`, `subtitle`, `series` (nom affiché en haut), `number` (« #01 »),
`icon` (icône de l'outro), `theme` (`light` | `dark`), `accent` (bleu, indigo, violet,
vert, cyan, orange, rose, rouge ou `#RRGGBB`), `accent2` (couleur secondaire, optionnelle),
`target_seconds`.

Pour chaque scène : `type`, `voice` (lu par la synthèse, nombres en lettres), `caption`
(sous-titre affiché). Dans les titres et les textes, `*mot*` met le mot en couleur.
Le champ `match` (liste de mots de la voix) fait apparaître un élément au moment où
la voix prononce l'un de ces mots.

- `title` : accroche. `title`, `subtitle`, `kicker` (étiquette), `icon`.
- `concept` : une définition sur une carte. `term`, `definition`, `tag`, `icon`, `match`
  (instant où la définition apparaît).
- `analogy` : « c'est comme… ». `left` et `right` : {`icon`, `label`, `sub`, `match`},
  `title`, `sign` (« ≈ » par défaut). À gauche la notion, à droite la vie courante.
- `flow` : schéma en étapes. `nodes` (2 à 4) : {`icon`, `label`, `sub`, `match`, `alt`
  (couleur secondaire), `step`}, `layout` (`column` par défaut, `row` pour 3 étapes
  maximum), `back` (true : le paquet fait l'aller-retour), `title`.
- `list` : 1 à 5 points. `items` : {`text`, `icon`, `match`, `style`}, `title`, `style`
  (`number` | `icon` | `check` | `cross`).
- `code` : code tapé à l'écran. `code` (texte avec `\n`, 14 lignes maximum), `style`
  (`editor` | `terminal` : les lignes `$ ...` sont tapées, les autres s'affichent comme
  une sortie), `file` (nom de l'onglet), `highlight` (numéros de lignes), `title`, `typing`.
- `stat` : chiffre clé qui défile. `value` (nombre), `prefix`, `suffix`, `label`, `note`,
  `icon`, `match`.
- `versus` : comparaison. `left` et `right` : {`icon`, `label`, `points` (4 max), `match`}, `title`.
- `fact` : phrase forte. `text`, `kicker` (« Le saviez-vous ? » par défaut, ou une année),
  `detail`, `icon`, `match`.
- `outro` : titre de l'épisode + appel à commenter. `cta`, `follow`.

## Icônes
65 icônes au trait : at, battery, binary, bolt, book, bug, calendar, chart, check, clock,
cloud, code, cookie, cpu, cross, database, disk, download, eye, file, folder, gear, globe,
hash, heart, home, image, info, key, keyboard, laptop, layers, lightbulb, link, lock, mail,
message, money, monitor, network, package, password, phone, pin, question, ram, refresh,
robot, router, search, server, shield, shield-check, sparkles, speed, target, terminal,
trophy, truck, unlock, upload, user, users, video, warning, wifi.
`"text:DNS"` affiche un sigle (4 caractères maximum) à la place d'un dessin.
`python3 -m engine.icons` exporte la planche de toutes les icônes (`assets/icons_planche.png`).
Pour remplacer une icône ou en ajouter une, dépose `assets/icons/<nom>.png` (carré, fond
transparent) : seule sa forme compte, elle prend la couleur du thème.

## API de rendu
    bash install_api.sh              # une fois (clé d'API dans .env)
    bash install_api.sh --service    # option : démarrage automatique (systemd)
    ./api.sh                         # http://127.0.0.1:8000 — doc interactive : /docs
Routes (en-tête `X-API-Key` obligatoire, sauf /health) :
- `POST /videos` : l'épisode JSON (ou `{"episode": {...}, "webhook": "https://..."}`)
  -> `{"id": ..., "status": "queued"}`. Le JSON est vérifié avant d'entrer en file.
- `GET /videos/{id}` : `queued` | `running` (+ `step` voix/vidéo, `progress` %) |
  `done` (+ `url`) | `failed` (+ `error`). `GET /videos` : derniers rendus.
- `GET /videos/{id}/file` : le MP4. `GET /videos/{id}/log` : le journal du rendu.
- `DELETE /videos/{id}` : annule ou supprime.
Un rendu à la fois ; les rendus en cours reprennent après un redémarrage ; les vidéos
de plus de 14 jours sont nettoyées. Client prêt à l'emploi :
    python3 client.py exemples/01_dns.json exemples/02_ram.json --out videos/

## Déploiement (Coolify, Railpack)
`railpack.json` installe ffmpeg et espeak-ng, télécharge la voix Piper pendant le
build et lance l'API sur le port 8000 (Python 3.12, voir `.python-version`).
Dans Coolify : Build Pack « Railpack », Base Directory `/infoclair`, port 8000,
variables `INFOCLAIR_API_KEY` (obligatoire), `INFOCLAIR_PUBLIC_URL` (webhooks) et
`INFOCLAIR_MUSIC` (optionnelle), et un stockage persistant monté sur `/app/jobs`
(sinon les vidéos disparaissent à chaque redéploiement).
Encodage au processeur par défaut (`INFOCLAIR_NVENC=0`).

## Mise en page et zones sûres TikTok
Rendu directement en 1080x1920. Rien d'important dans les 170 px du haut, les 410 px
du bas et les 130 px de droite : le visuel occupe y = 300 à 1230, les sous-titres
y = 1290 à 1480. Ces repères sont en tête de `engine/gfx.py`.

## Polices
Inter et JetBrains Mono (licence SIL Open Font, fichiers `OFL-*.txt`) sont fournies
dans `assets/fonts`.
