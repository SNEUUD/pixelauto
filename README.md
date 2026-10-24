# L'auto en 8 bits — générateur de vidéos TikTok

Tout tourne en local : voix Piper ou Kokoro (CPU), rendu Python/Pillow en 180x320 agrandi x6
(vrais gros pixels), musique chiptune générée, encodage ffmpeg (NVENC possible).

## Installation (une fois)
    bash install.sh

## Générer une vidéo
    ./video.sh episodes/02_mazda_mx5_na.json     # -> out/02_mazda_mx5_na.mp4
    ./video.sh --all                              # tous les épisodes nouveaux ou modifiés
    ./video.sh --all --force                      # tout refaire
    ./video.sh episodes/02_mazda_mx5_na.json --preview 9   # aperçu PNG rapide
Réglages (voix, moteur, NVENC) en tête de `video.sh`, ou dans un `config.sh`.
Moteurs de voix (`TTS`) : `piper` (défaut), `kokoro` (plus naturel, toujours sur le
processeur, voix `ff_siwis`), `chatterbox` (le plus naturel, GPU, voir `install_tts.sh`).
Pour comparer à l'oreille : `python3 compare_voices.py` (-> `samples/`).
NVENC est testé automatiquement : sans GPU NVIDIA, l'encodage passe au processeur.

## Écrire un épisode
Un épisode = un JSON dans `episodes/`. Pour chaque scène : `voice` (lu, nombres en
lettres), `caption` (affiché), `type`, `bg` (décor de la banque), `year` (badge).

Scènes génériques :
- `drive` : la voiture roule. `car`: cruise | pass | enter | parked, `ground`: road |
  grass | field | sidewalk | floor, `title`, `subtitle`, `title_at` (0-1), `lights_up`.
- `anecdote` : un personnage parle. `quote`, `person` (0-2), `car`: enter.
- `reveal` : présentation au salon. `title`, `bubbles` (3 max), `hearts`.
- `specs` : fiche technique, 4 cases. `items`: [{`icon`, `label`, `match`: [mots de la
  voix/du sous-titre qui font apparaître l'icône]}]. Icônes : weight, engine, rwd,
  popup, fwd, water, people, speed, fuel, sack, farmers, trophy, calendar,
  money, heart, car.
- `counter` : chiffre qui défile. `counter_to`, `counter_label`, `counter_suffix`,
  `colors` (liste de couleurs de carrosserie qui alternent).
- `date` : date en grand. `date`, `label`, `date_at`.
- `outro` : titre de l'épisode + appel à commenter.

## Voiture
Décrite dans `car` (voir l'épisode 02) : `size` [l, h], `profile` (contour vu de
profil, avant à droite), `wheels` [x arrière, x avant], `wheel_y`, `wheel_d`,
couleurs PICO-8 `body`/`shade`/`light`/`glass`, détails `shapes` (poly, rect, line,
point) et `popup` pour des phares escamotables.

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
    python3 client.py episodes/03_renault_4l.json episodes/04_fiat_500.json --out videos/

## Déploiement (Coolify, Railpack)
`railpack.json` installe ffmpeg et espeak-ng, télécharge les voix Piper et Kokoro pendant le
build et lance l'API sur le port 8000 (Python 3.12, voir `.python-version`).
Dans Coolify : Build Pack « Railpack », port 8000, variables `PIXELAUTO_API_KEY`
(obligatoire) et `PIXELAUTO_PUBLIC_URL` (webhooks), et un stockage persistant monté
sur `/app/jobs` (sinon les vidéos disparaissent à chaque redéploiement).
Encodage au processeur par défaut (`PIXELAUTO_NVENC=0`). Voix plus naturelle : `PIXELAUTO_TTS=kokoro`.

## Sprites
Au premier rendu, chaque sprite est exporté dans `assets/sprites/*.png`.
Redessine-les (Aseprite, LibreSprite, Piskel) en gardant la taille : ta version
remplace celle générée par le code. Supprime un PNG pour le régénérer.
Les voitures, elles, se décrivent dans l'épisode (voir « Voiture »).

## Banque de décors
10 décors dessinés par le code (`engine/decors.py`) : campagne, village, route,
ville, usine, salon, circuit, nuit, garage, montagne. Une scène s'en sert avec
`"bg": "<id>"`. Ils sont enregistrés dans `assets/bank/<id>.png` (225x200) :
retouche-les dans Aseprite en gardant taille et palette, ta version sera utilisée.
`python3 -m engine.decors` les redessine tous (écrase tes retouches) + `planche.png`.

## Zones sûres TikTok
Rien d'important dans les 26 px du haut, les 68 px du bas et les 22 px de droite
(coordonnées internes 180x320).
