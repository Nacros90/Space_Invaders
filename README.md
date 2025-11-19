# Space_Invaders
-------
Jeu inspiré de Space Invaders écrit en Python avec Pygame. Le fichier principal est
`Space_Invaders/Space invaders.py` : il gère l'initialisation, la boucle de jeu,
les ennemis, le boss, les projectiles, les power-ups et l'affichage des meilleurs scores.

Structure du projet
-------------------
- `Space_Invaders/Space invaders.py` : code du jeu (classes : Player, Opponent, Boss, PowerUp, Bullet, Game, ...).
- `Space_Invaders/assets/` : images et ressources graphiques (sprites, fond, power-ups, etc.).
- `Space_Invaders/logs/meilleurs_scores.json` : stockage JSON des meilleurs scores (créé automatiquement).
- `README.md` : ce fichier.

Dépendances
-----------
- Python 3.8+ (testé avec Python 3.10)
- Pygame

Installation rapide (PowerShell)
-------------------------------
Installez Pygame si nécessaire :

```powershell
python -m pip install pygame
```

Lancer le jeu
------------
Depuis la racine du projet (où se trouve ce `README.md`) lancez :

```powershell
python ".\Space_Invaders\Space invaders.py"
```

Contrôles
--------
- Flèches gauche/droite/haut/bas : déplacer le vaisseau
- `Espace` : tirer
- `Esc` : pause / revenir au menu
- `R` : recommencer après une partie terminée

Fonctionnement rapide du code
----------------------------
- `Game` : initialise Pygame, charge les images, gère la boucle principale, les états (menu, pause, jeu, saisie de nom), les vagues et les collisions.
- `Player` : gère la physique simple (vitesse, friction), les vies, le tir et les power-ups (bouclier, cadence).
- `Opponent`, `ArmoredOpponent`, `ShooterOpponent` : ennemis avec PV et logique de tir simple.
- `Boss` : ennemi spécial avec plus de PV et un tir multiple.
- `Bullet` / `EnemyBullet` : projectiles joueurs / ennemis (les balles ennemies peuvent suivre une trajectoire oscillante si voulue par le joueur).
- Power-ups : `HealthPowerUp`, `ShieldPowerUp`, `FireRatePowerUp` (appliquent des effets au joueur).

Sauvegarde des scores
---------------------
Les meilleurs scores sont sauvegardés dans `Space_Invaders/logs/meilleurs_scores.json`. Le dossier `logs` est créé automatiquement si nécessaire.

Améliorations possibles
----------------------
- Ajouter plus de types d'ennemis et animations.
- Son et musiques (ajout de fichiers audio dans `assets`).
- Meilleure UI pour les menus et écrans de transition.

Licence & Contribution
----------------------
Ce projet est un exercice de TP, mais je compte l'amélirorer de mon coté.

Pour la réalisation de ce projet j'ai pue utiliser plusieurs recources, certaines étant de l'ia (Gemini 2.5 Pro) qui ma aider à coder les partie plutot complexe comme la simulation de déplacements plus "organiques" du joueur avec l'ajout d'inertie, les rebonds sur les bords lorq d'une collision.
Tout les sprite utilisé ont été trouver sur internet.