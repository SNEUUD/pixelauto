Tu vas écrire un épisode pour ma série TikTok « L'INFO EN CLAIR » : des vidéos verticales d'environ 60 secondes qui expliquent une notion d'informatique à un public non technique, dans un style graphique sobre et professionnel (cartes, icônes, schémas animés). Mon programme transforme un fichier JSON en vidéo (voix off, sous-titres, visuels). Ton travail : produire ce JSON.

SUJET DE L'ÉPISODE : [ex. « Comment marche le HTTPS ? »]
NUMÉRO DE L'ÉPISODE : [ex. 03]

## Méthode
1. Recherche sur le web avant d'écrire. Chaque date, chiffre et fait doit venir d'une source fiable (documentation officielle, RFC, Wikipédia, CNIL, ANSSI, Mozilla MDN, presse tech reconnue). Recoupe les chiffres importants avec deux sources.
2. Si les sources se contredisent ou si un fait est douteux, ne l'utilise pas, ou formule-le prudemment (« environ », « souvent », « en général »). Simplifie, mais n'écris rien de faux : une simplification doit rester vraie.
3. Construis l'épisode comme une explication : une accroche (une question que le spectateur se pose), la définition simple, une analogie de la vie courante, le fonctionnement en étapes, un exemple concret ou un chiffre marquant, un conseil ou une anecdote, puis l'outro.
4. Écris le JSON, puis relis-le avec la liste de vérification en bas.
5. Réponds avec : le JSON complet dans un seul bloc de code, puis 3 à 5 lignes listant les faits que tu as écartés ou simplifiés et pourquoi.

## Règles d'écriture
- Français, ton clair et posé, phrases courtes, tutoiement. Un seul concept par scène. Pas de jargon sans l'expliquer.
- Durée : 145 à 160 mots au total dans les champs `voice` (≈ 60 s). Compte-les.
- `voice` est lu par une synthèse vocale : nombres et dates EN LETTRES (« mille neuf cent quatre-vingt-trois », « treize »), sigles avec des points (« D.N.S. », « H.T.T.P.S. », « I.P. »), pas de symboles (pas de %, €, Go, /, → : écris-les en mots, « gigaoctets »). Écris phonétiquement un mot anglais mal lu au besoin (« naïte-loukeupe »).
- `caption` est le sous-titre affiché : même phrase, mais chiffres en chiffres (« 1983 », « 16 Go »), sigles sans points (« DNS »), peut être un peu plus courte. Mets un espace avant « : ? ! » et dans « » comme en typographie française.
- Dans les textes affichés (titres, labels, définitions), `*mot*` met un mot en couleur : 1 ou 2 mots clés par texte au maximum, jamais dans `voice` ni `caption`.
- Les exemples de code et de commandes doivent être corrects et réalistes. N'invente pas de résultat précis (adresse IP, temps de réponse) présenté comme vrai : choisis un exemple vérifiable ou un résultat générique.

## Format du JSON
```json
{
  "id": "NN_sujet",                  // minuscules, chiffres, _ uniquement
  "title": "Le HTTPS",               // ≤ 24 caractères
  "subtitle": "Le cadenas du web",   // ≤ 40 caractères
  "series": "L'info en clair",
  "number": "NN",
  "icon": "lock",                    // icône de l'outro
  "theme": "light",                  // light ou dark (dark convient bien au code et à la sécurité)
  "accent": "bleu",                  // bleu, indigo, violet, vert, cyan, orange, rose, rouge
  "target_seconds": 60,
  "scenes": [ ... ],                 // 6 à 8 scènes, la première "title", la dernière "outro"
  "sources": ["https://...", "..."]  // les URL réellement utilisées
}
```

### Les scènes (uniquement ces types)
Champs communs obligatoires : `type`, `voice`, `caption`.
`match` : liste de mots EXACTS présents dans la `voice` (en minuscules) ; l'élément apparaît quand la voix les prononce. Mets-le sur les éléments qui arrivent en cours de phrase.

- `title` : accroche. `title` (≤ 45 caractères, une question de préférence), `kicker` (thème, ≤ 16 caractères, ex. "Réseau", "Sécurité"), `icon`, `subtitle` (optionnel, ≤ 60).
- `concept` : définition. `term` (≤ 20), `definition` (≤ 110), `icon` (ou "text:SIGLE"), `tag` (optionnel, défaut "Définition"), `match` (mot qui fait apparaître la définition).
- `analogy` : la notion (gauche) comparée à un objet du quotidien (droite). `left` et `right` : {"icon", "label" (≤ 16), "sub" (≤ 28)}, `right.match`, `title` optionnel (≤ 30, ex. "Imagine une cuisine").
- `flow` : fonctionnement en étapes reliées par des flèches. `nodes` : 2 à 4 × {"icon", "label" (≤ 20), "sub" (≤ 28, optionnel), "match", "alt": true pour l'étape finale ou la réponse}. `layout` : "column" (défaut) ou "row" (3 étapes max, label ≤ 12, sub ≤ 18). `back`: true si une réponse revient au point de départ (requête/réponse). `title` optionnel (≤ 30).
- `list` : 2 à 5 points. `items` : [{"text" (≤ 50), "match", "icon" (optionnel), "style" (optionnel)}], `title` (≤ 30), `style` : "number" (défaut), "icon", "check" (bons réflexes), "cross" (erreurs à éviter).
- `code` : extrait de code ou commande. `code` : texte avec \n, ≤ 10 lignes, ≤ 36 caractères par ligne. `style` : "editor" (défaut, coloration syntaxique) ou "terminal" (les lignes qui commencent par "$ " sont tapées, les autres sont la sortie). `file` (nom de fichier affiché, ex. "app.py"), `highlight` : [numéros de lignes à mettre en avant], `title` (≤ 30, ex. "Essaie chez toi :").
- `stat` : un chiffre clé. `value` (nombre exact), `prefix` / `suffix` (≤ 4 caractères, ex. " Go", " %", "×"), `label` (≤ 40), `note` (≤ 70, optionnel), `icon`, `match` (fait apparaître la note).
- `versus` : deux choses comparées. `left` et `right` : {"icon", "label" (≤ 12), "points" : 2 ou 3 textes ≤ 22 caractères}, `right.match`, `title` optionnel.
- `fact` : une phrase forte. `text` (≤ 90), `kicker` (≤ 18 : "Le saviez-vous ?" par défaut, ou une année), `detail` (≤ 70, optionnel), `icon`, `match` (fait apparaître le détail).
- `outro` : toujours en dernier, toujours exactement :
  {"type": "outro", "voice": "Et toi, quel sujet pour le prochain épisode ? Dis-le en commentaire !", "caption": "Et toi, quel sujet pour le prochain épisode ? Dis-le en commentaire !"}

Varie les types de scènes : pas deux fois le même type d'affilée, au moins un `flow` ou un `analogy`.

Icônes disponibles (aucune autre) : at, battery, binary, bolt, book, bug, calendar, chart, check, clock, cloud, code, cookie, cpu, cross, database, disk, download, eye, file, folder, gear, globe, hash, heart, home, image, info, key, keyboard, laptop, layers, lightbulb, link, lock, mail, message, money, monitor, network, package, password, phone, pin, question, ram, refresh, robot, router, search, server, shield, shield-check, sparkles, speed, target, terminal, trophy, truck, unlock, upload, user, users, video, warning, wifi.
Pour un sigle sans icône adaptée : "text:SIGLE" (4 caractères max, ex. "text:DNS", "text:IP", "text:404").

## Exemple de scènes (épisode « Le DNS », extrait)
```json
{"type": "title", "icon": "globe", "kicker": "Réseau", "title": "Comment ton navigateur trouve un *site* ?",
 "voice": "Tu tapes un nom de site, et la page s'affiche presque aussitôt. Mais comment ton ordinateur sait-il où aller ?",
 "caption": "Tu tapes un nom de site, et la page s'affiche presque aussitôt. Mais comment ton ordinateur sait-il où aller ?"},
{"type": "analogy",
 "left": {"icon": "text:DNS", "label": "Le DNS", "sub": "un nom → une adresse IP"},
 "right": {"icon": "book", "label": "Un annuaire", "sub": "un nom → un numéro", "match": ["annuaire"]},
 "voice": "Les machines ne parlent qu'en chiffres. Le D.N.S., c'est leur annuaire : tu donnes un nom, il te rend un numéro.",
 "caption": "Les machines ne parlent qu'en chiffres. Le DNS, c'est leur annuaire : tu donnes un nom, il te rend un numéro."},
{"type": "flow", "back": true,
 "nodes": [{"icon": "laptop", "label": "Ton ordinateur", "sub": "« wikipedia.org ? »"},
           {"icon": "router", "label": "Le résolveur", "sub": "souvent chez ton FAI", "match": ["résolveur"]},
           {"icon": "server", "label": "Serveurs DNS", "sub": "racine, .org, puis le site", "match": ["racine"]},
           {"icon": "check", "label": "L'adresse IP", "sub": "renvoyée à ton ordinateur", "match": ["adresse"], "alt": true}],
 "voice": "Ton ordinateur demande d'abord à un résolveur, souvent chez ton fournisseur d'accès. Lui interroge les serveurs racine, puis ceux du point org, et enfin celui du site, qui renvoie l'adresse.",
 "caption": "Ton ordinateur demande d'abord à un résolveur, souvent chez ton fournisseur d'accès. Lui interroge les serveurs racine, puis ceux du .org, et enfin celui du site, qui renvoie l'adresse."},
{"type": "stat", "icon": "server", "value": 13, "label": "noms de serveurs racine",
 "note": "copiés en plus de 1 000 exemplaires dans le monde", "match": ["copiés"],
 "voice": "Tout en haut, il n'y a que treize noms de serveurs racine, copiés en plus de mille exemplaires dans le monde.",
 "caption": "Tout en haut, il n'y a que 13 noms de serveurs racine, copiés en plus de 1 000 exemplaires dans le monde."}
```

## Liste de vérification avant de répondre
- [ ] JSON valide (sans commentaires), un seul bloc.
- [ ] 145-160 mots dans les `voice` ; aucun chiffre ni symbole dans `voice`.
- [ ] Chaque `caption` dit la même chose que sa `voice`.
- [ ] Longueurs respectées (titres, labels, points, lignes de code).
- [ ] Seulement les types de scènes et les icônes listés ; première scène `title`, dernière = outro exacte.
- [ ] Chaque mot de `match` apparaît réellement dans la `voice`, en minuscules.
- [ ] Le code est correct et tient en 10 lignes de 36 caractères.
- [ ] Chaque fait est sourcé ; les sources sont dans `sources`.
