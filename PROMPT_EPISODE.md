Tu vas écrire un épisode pour ma série TikTok « L'AUTO EN 8 BITS » : des vidéos verticales d'environ 60 secondes, en pixel art, qui racontent l'histoire d'un modèle de voiture. Mon programme transforme un fichier JSON en vidéo (voix off, sous-titres, sprites, décors). Ton travail : produire ce JSON.

VOITURE DE L'ÉPISODE : [NOM DU MODÈLE ET GÉNÉRATION, ex. « Volkswagen Golf GTI Mk1 »]
NUMÉRO DE L'ÉPISODE : [ex. 08]

## Méthode
1. Recherche sur le web avant d'écrire. Chaque date, chiffre et anecdote doit venir d'une source fiable (Wikipédia, site du constructeur, presse auto reconnue). Recoupe les chiffres importants avec deux sources.
2. Si les sources se contredisent ou si un fait est douteux, ne l'utilise pas, ou formule-le prudemment (« fin des années 70 », « environ », « aurait »). Pas de légende non vérifiée présentée comme un fait.
3. Choisis 6 à 8 moments forts : une accroche qui intrigue dès la première phrase, l'origine du projet, une anecdote surprenante, la fiche technique, un chiffre marquant, la fin de carrière ou l'héritage.
4. Écris le JSON, puis relis-le avec la liste de vérification en bas.
5. Réponds avec : le JSON complet dans un seul bloc de code, puis 3 à 5 lignes listant les faits que tu as écartés ou adoucis et pourquoi.

## Règles d'écriture
- Français, ton de vulgarisation vivant, phrases courtes, tutoiement pour l'appel final.
- Durée : 145 à 160 mots au total dans les champs `voice` (≈ 60 s). Compte-les.
- `voice` est lu par une synthèse vocale : nombres et dates EN LETTRES (« mille neuf cent quatre-vingt-neuf », « cent quinze chevaux »), sigles avec des points (« B.M.C. », « G.T.I. »), pas de symboles (pas de %, km/h, €, cm3 → écris-les en mots). Écris phonétiquement un mot étranger mal lu au besoin (« Jinba Ittaï »).
- `caption` est le sous-titre affiché : même phrase, mais chiffres en chiffres (« 1989 », « 115 ch », « 80 % »), peut être un peu plus courte. Mets un espace avant « : ? ! » et dans « » comme en typographie française.
- Pas de personne réelle dessinée : les personnages sont des silhouettes génériques, seule la voix cite les noms.

## Format du JSON
```json
{
  "id": "NN_marque_modele",          // minuscules, chiffres, _ uniquement
  "title": "MARQUE MODÈLE",          // majuscules ; chaque mot ≤ 10 caractères
  "subtitle": "1983 - 1998",         // ≤ 20 caractères
  "series": "L'AUTO EN 8 BITS",
  "target_seconds": 60,
  "car": { ... },                    // voir « La voiture »
  "scenes": [ ... ],                 // 7 à 9 scènes, la dernière est "outro"
  "sources": ["https://...", "..."]  // les URL réellement utilisées
}
```

### Les scènes (uniquement ces types)
Champs communs : `type`, `voice`, `caption` (obligatoires) ; `bg` (décor) ; `year` (badge jaune, ≤ 9 caractères, ex. "1989" ou "1983-98", omets-le si inutile).

- `drive` : la voiture roule. `car` : "cruise" (au centre, le décor défile) | "pass" (traverse l'écran) | "enter" (arrive et s'arrête) | "parked". `ground` : "road" (défaut) | "grass" | "field" | "sidewalk" | "floor". `title` (≤ 2 lignes de 10 caractères), `subtitle` (≤ 2 lignes de 20 caractères), `title_at` (0 à 1, moment d'apparition), `lights_up` (true pour lever des phares escamotables).
- `anecdote` : une silhouette parle. `quote` (bulle, ≤ 3 lignes de 13 caractères, idéalement ≤ 35 caractères), `person` (0, 1 ou 2), `ground`, `car`: "enter" (optionnel, la voiture arrive à la fin).
- `reveal` : présentation au salon (rideaux, projecteurs, public). `title` (≤ 18 caractères, ex. "Salon de Genève"), `bubbles` (3 réactions du public, ≤ 10 caractères chacune, ex. ["WOW","!!","JE LA VEUX"]). Mets `bg`: "salon".
- `specs` : fiche technique sur un carnet, 3 ou 4 cases. `title` (≤ 17 caractères), `items` : [{ "icon": ..., "label": ≤ 10 caractères, "match": [mots exacts présents dans voice ou caption qui font apparaître l'icône] }]. Pas de `bg`.
  Icônes : weight (poids), engine (moteur), speed (vitesse/puissance), rwd (propulsion), fwd (traction), popup (phares escamotables), fuel (carburant), water (refroidissement), money (prix), calendar (date), trophy (victoire), people (passagers), heart, sack, car (la voiture elle-même).
- `counter` : un nombre qui défile pendant que la voiture roule. `counter_to` (entier exact), `counter_label` (≤ 2 lignes de 20 caractères), `counter_suffix` (optionnel, ex. "Record !"), `colors` (optionnel : liste de couleurs de carrosserie qui alternent, ex. [{}, {"body":12,"shade":1,"light":7}] — {} = couleur d'origine).
- `date` : une date en grand, la voiture arrive. `date` (≤ 10 caractères, ex. "27.07.1990"), `label` (≤ 2 lignes de 20 caractères), `date_at` (0 à 1).
- `outro` : toujours en dernier, toujours exactement :
  {"type": "outro", "voice": "Et toi, quelle voiture pour le prochain épisode ?", "caption": "Et toi, quelle voiture pour le prochain épisode ?"}

Décors disponibles pour `bg` (aucun autre) : campagne, village, route, ville, usine, salon, circuit, nuit, garage, montagne.
Varie les décors et les types de scènes ; ne mets pas deux `specs` ou deux `reveal`.

### La voiture (sprite vu de profil)
La voiture est dessinée en pixels sur une petite grille, **avant vers la droite**, origine (0,0) en haut à gauche, y vers le bas. Respecte les proportions réelles (longueur / hauteur, empattement, porte-à-faux, forme du toit).
```json
"car": {
  "body": 8, "shade": 2, "light": 14, "glass": 12,   // couleurs (palette ci-dessous)
  "size": [72, 20],                    // largeur 50-74, hauteur 17-24
  "wheels": [15, 56],                  // x du centre des roues arrière et avant
  "wheel_y": 18,                       // y du centre des roues = bas de caisse
  "wheel_d": 11,                       // diamètre : 9 (petite), 11, 13 (grosse)
  "profile": [[2,18],[1,15],[1,11],[3,9],[18,9],[21,10],[41,10],[52,10],[61,11],[67,12],[70,14],[70,17],[68,18]],
  "windows": [[[x,y],...], ...],       // optionnel : vitres latérales (polygones)
  "shapes": [                          // détails : "poly", "rect" (2 coins), "line", "point"
    {"type": "poly", "pts": [[37,3],[39,3],[43,9],[41,9]], "col": "glass"},
    {"type": "line", "pts": [[24,11],[24,16]], "col": "shade"},
    {"type": "rect", "pts": [[68,14],[69,15]], "col": 9}
  ],
  "popup": {"closed": [62,11,65,12], "open": [62,7,65,11]}   // optionnel : phares escamotables
}
```
- `profile` : contour extérieur, sens horaire, en partant du bas arrière. Le point le plus bas doit être à `wheel_y`.
- Les passages de roue sont découpés automatiquement : garde au moins 2 px de carrosserie au-dessus de chaque roue (haut de caisse ≤ wheel_y − wheel_d/2 − 3 à l'aplomb des roues).
- Ajoute ce qui rend le modèle reconnaissable : forme des vitres, montants, lignes de portes, phares (rect jaune 10 ou blanc 7), feux arrière (rouge 8 ou orange 9), pare-chocs (gris 5 ou 6), bandes déco, aileron, prises d'air (0).
- `col` accepte un numéro de palette ou "body", "shade", "light", "glass".
- Couleur : la teinte la plus emblématique du modèle. `shade` = version plus sombre de `body`.

Palette (PICO-8) : 0 noir, 1 bleu nuit, 2 bordeaux, 3 vert foncé, 4 brun, 5 gris foncé, 6 gris clair, 7 blanc, 8 rouge, 9 orange, 10 jaune, 11 vert vif, 12 bleu ciel, 13 lavande, 14 rose, 15 pêche.

## Exemple de scènes (épisode Mazda MX-5 NA, extrait)
```json
{"type": "drive", "bg": "route", "car": "cruise", "title": "MAZDA MX-5", "subtitle": "LA RENAISSANCE DU ROADSTER", "title_at": 0.08,
 "voice": "En mille neuf cent quatre-vingt-neuf, une petite japonaise ressuscite un genre que tout le monde croyait mort : le roadster.",
 "caption": "En 1989, une petite japonaise ressuscite un genre que tout le monde croyait mort : le roadster."},
{"type": "anecdote", "bg": "ville", "person": 0, "car": "enter", "ground": "sidewalk", "quote": "Un petit roadster deux places !",
 "voice": "Tout part d'un journaliste américain, Bob Hall. À la fin des années soixante-dix, il souffle à Mazda l'idée d'un petit roadster deux places, simple et abordable.",
 "caption": "Tout part d'un journaliste américain, Bob Hall. Fin des années 70, il souffle à Mazda l'idée d'un petit roadster deux places, simple et abordable."},
{"type": "specs", "title": "La recette",
 "items": [{"icon": "weight", "label": "-1 tonne", "match": ["tonne"]},
           {"icon": "engine", "label": "115 ch", "match": ["chevaux", "115"]},
           {"icon": "rwd", "label": "propulsion", "match": ["propulsion"]},
           {"icon": "popup", "label": "phares", "match": ["phares"]}],
 "voice": "La recette : moins d'une tonne, un quatre cylindres de cent quinze chevaux, la propulsion… et des phares escamotables.",
 "caption": "La recette : moins d'une tonne, 115 ch, la propulsion… et des phares escamotables."},
{"type": "counter", "bg": "route", "year": "1989-97", "counter_to": 431506, "counter_label": "MX-5 NA produites",
 "voice": "En huit ans, plus de quatre cent trente mille exemplaires sortent de l'usine d'Hiroshima.",
 "caption": "En 8 ans, plus de 430 000 exemplaires sortent de l'usine d'Hiroshima."}
```

## Liste de vérification avant de répondre
- [ ] JSON valide (sans commentaires), un seul bloc.
- [ ] 145-160 mots dans les `voice` ; aucun chiffre ni symbole dans `voice`.
- [ ] Chaque `caption` dit la même chose que sa `voice`.
- [ ] Longueurs respectées (titres, labels, bulles, quote, badges).
- [ ] Seulement les types de scènes, décors et icônes listés ; dernière scène = outro exacte.
- [ ] Chaque `match` de `specs` apparaît réellement dans la `voice` ou la `caption`.
- [ ] Voiture tournée vers la droite, proportions crédibles, roues sous la caisse.
- [ ] Chaque fait est sourcé ; les sources sont dans `sources`.
