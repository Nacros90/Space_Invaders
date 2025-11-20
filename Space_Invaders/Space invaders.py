# -*- coding: utf-8 -*-
"""
Created on Wed Oct  8 08:19:55 2025

@author: ncrosnie
TD1 : Space invaders
"""

import pygame
import sys
import math
import random
import json
from pathlib import Path

#- Constantes globales
Width=1280
Height=720
FPS=90
player_surf_W=60
player_surf_H=20
Blue=(80, 115, 210)
White = (255, 255, 255)
Green = (80, 220, 100)
Red = (220,80,100)
Orange=(255,119,0)

# États du jeu
PLAYING=0
GAME_OVER=1
MAIN_MENU = 2
HIGH_SCORE_SCREEN = 3
PAUSED = 4
ENTERING_NAME = 5
TRANSITION = 6
MAX_HIGH_SCORES = 5

# --- Répertoire des assets ---
# Cette ligne définit le dossier dans lequel se trouvent toutes les images du jeu.
# On part du dossier où se trouve ce fichier Python (__file__), puis on ajoute "assets".
Assets = Path(__file__).parent / "assets"

class Player(pygame.sprite.Sprite):
    """Représente le vaisseau contrôlé par le joueur.

    Gère la physique basique (vitesse, accélération, friction), les vies,
    la cadence de tir et les power-ups (bouclier, augmentation de cadence).
    """ 
    def __init__(self,x,y,image_surface):
        super().__init__()
        self.image=image_surface
        self.rect=self.image.get_rect(midbottom=(x,y))
        
        # --- Physique pour des mouvement organiques ---
        self.velocity = pygame.math.Vector2(0, 0)
        self.acceleration = 0.7
        self.friction = -0.12
        self.max_speed = 7
        #Constantes du joueur
        self.base_shoot_cooldown = 100
        self.shoot_cooldown = self.base_shoot_cooldown     #en ms
        self.last_shot=0
        self.lives=20
        self.max_lives = self.lives

        # Etat des power-up
        self.shield_active = False
        self.shield_end_time = 0
        self.fire_rate_boost_active = False
        self.fire_rate_boost_end_time = 0

    def add_health(self, amount):
        """Ajoute de la vie au joueur"""
        self.lives += amount
        if self.lives > self.max_lives:
            self.lives = self.max_lives

    def take_damage(self, amount):
        """Réduit la vie du joueur"""
        if not self.shield_active:
            self.lives -= amount

    def update(self,keys):
        '''Met à jour la position et l'état du joueur en fonction des entrées clavier.'''
        self.velocity += self.velocity * self.friction  # Applique la friction
        # Stop le mouvement si la vitesse est trop basse, cela évite de bouger à l'infini
        if self.velocity.length() < 0.1:
            self.velocity.x = 0
            self.velocity.y = 0

        # On applique l'accélération selon les touches pressées
        if keys[pygame.K_LEFT]:
            self.velocity.x -= self.acceleration
        if keys[pygame.K_RIGHT]:
            self.velocity.x += self.acceleration
        if keys[pygame.K_UP]:
            self.velocity.y -= self.acceleration
        if keys[pygame.K_DOWN]:
            self.velocity.y += self.acceleration

        # Limite la vitesse maximale
        if self.velocity.length() > self.max_speed:
            self.velocity.scale_to_length(self.max_speed)

        # Met à jour la position
        self.rect.x += self.velocity.x
        self.rect.y += self.velocity.y
        
        # Mise à jour des power-ups
        now = pygame.time.get_ticks()
        if self.shield_active and now > self.shield_end_time:   # Bouclier expiré
            self.shield_active = False
        
        if self.fire_rate_boost_active and now > self.fire_rate_boost_end_time:   # Augmentation de cadence expirée
            self.fire_rate_boost_active = False
            self.shoot_cooldown = self.base_shoot_cooldown

        # Vérification des limites avec effet de "rebond"
        if self.rect.left < 0:
            self.rect.left = 0
            self.velocity.x *= -0.5  # Inverse et réduit la vitesse
        if self.rect.right > Width:
            self.rect.right = Width
            self.velocity.x *= -0.5 # Inverse et réduit la vitesse
        if self.rect.top < 0:
            self.rect.top = 0
            self.velocity.y *= -0.5 # Inverse et réduit la vitesse

    def activate_shield(self, duration=5000):
        """Active le bouclier pour une durée donnée"""
        self.shield_active = True
        self.shield_end_time = pygame.time.get_ticks() + duration

    def activate_fire_rate_boost(self, duration=7000):
        """Active l'augmentation de la cadence de tir pour une durée donnée"""
        self.fire_rate_boost_active = True
        self.fire_rate_boost_end_time = pygame.time.get_ticks() + duration
        self.shoot_cooldown = self.base_shoot_cooldown / 2 # Double la cadence de tir
    
    def can_shoot(self):    
        """Vérifie si le joueur peut tirer en fonction du cooldown"""
        return pygame.time.get_ticks()-self.last_shot>=self.shoot_cooldown
    
    def shoot(self,bullets_group,all_sprites_group, bullet_image):
        """Permet au joueur de tirer un projectile si le cooldown est écoulé"""
        if self.can_shoot():
            bullet=Bullet(self.rect.centerx,self.rect.top, bullet_image)
            bullets_group.add(bullet)
            all_sprites_group.add(bullet)
            self.last_shot=pygame.time.get_ticks()


class Opponent(pygame.sprite.Sprite):
    """Classe de base pour un ennemi.

    Attributs principaux:
    - hp: points de vie
    - score_value: points accordés au joueur lors de la destruction
    """
    def __init__(self, x, y, image_surface, hp=1, score_value=10):
        super().__init__()
        self.image = image_surface.copy() # Utilise une copie pour permettre les changements de couleur
        self.rect = self.image.get_rect(topleft=(x, y))
        self.hp = hp
        self.max_hp = hp
        self.score_value = score_value

    def hit(self):
        """Réduit les PV de 1 et supprime le sprite si les PV sont à 0."""
        self.hp -= 1
        if self.hp <= 0:
            self.kill()
        return self.hp <= 0

class ArmoredOpponent(Opponent):
    """Ennemi blindé : plus de PV, plus de points"""
    def __init__(self, x, y, image_surface):
        super().__init__(x, y, image_surface, hp=3, score_value=50)

    # Ennemi blindé : plus de PV, plus de points

class ShooterOpponent(Opponent):
    """Ennemi tireur : peut générer des projectiles selon une probabilité"""
    def __init__(self, x, y, image_surface):
        super().__init__(x, y, image_surface, hp=1, score_value=20)

    def can_shoot(self, probability):
        """Détermine si l'ennemi peut tirer en fonction d'une probabilité"""
        return random.random() < probability
        

class Boss(pygame.sprite.Sprite):
    """Boss majeur d'une vague.

    Possède beaucoup de PV, un cooldown de tir qui évolue avec la vague,
    et peut tirer plusieurs projectiles simultanément.
    """
    def __init__(self, image_surface, wave, x=450, y=100, speed=2.5):
        super().__init__()
        self.image = image_surface
        self.rect = self.image.get_rect(centerx=x, top=y)
        self.speed=speed

        # --- Échelle de difficulté avec le numéro de vague ---
        self.HP = 10 + (wave - 1) * 5  # Commence à 10 PV, gagne 5 PV à chaque vague
        self.max_HP = self.HP
        # Commence à 1 sec de cooldown, devient 8% plus rapide à chaque vague, minimum de 250ms
        self.shoot_cooldown = max(250, 1000 * (0.92 ** (wave - 1)))
        self.last_shot = pygame.time.get_ticks()

    def hit(self):
        """Réduit les PV du boss de 1. Si les PV atteignent 0, le boss est supprimé."""
        self.HP -= 1
        if self.HP <= 0:
            self.kill()

    def can_shoot(self):
        """Vérifie si le boss peut tirer en fonction du cooldown"""
        now = pygame.time.get_ticks()
        return now - self.last_shot >= self.shoot_cooldown


class PowerUp(pygame.sprite.Sprite):
    """Classe mère pour les power-ups ramassables par le joueur.
    Se déplace verticalement vers le bas.
    """
    def __init__(self, center, image):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(center=center)
        self.speedy = 2

    def update(self, *_):
        """Met à jour la position du power-up."""
        self.rect.y += self.speedy
        if self.rect.top > Height:
            self.kill()

class HealthPowerUp(PowerUp):
    """Power-up qui rend de la vie au joueur"""
    def __init__(self, center, image):
        super().__init__(center, image)
        # Power-up qui rend de la vie

    def apply_effect(self, player):
        """Applique l'effet de soin au joueur."""
        player.add_health(10)

class ShieldPowerUp(PowerUp):
    def __init__(self, center, image):
        super().__init__(center, image)
        # Power-up qui active un bouclier temporaire

    def apply_effect(self, player):
        """Applique l'effet de bouclier au joueur."""
        player.activate_shield()

class FireRatePowerUp(PowerUp):
    """Power-up qui augmente la cadence de tir du joueur"""
    def __init__(self, center, image):
        super().__init__(center, image)
        # Power-up qui réduit le cooldown de tir (augmentation de cadence)

    def apply_effect(self, player):
        """Applique l'effet d'augmentation de cadence de tir au joueur."""
        player.activate_fire_rate_boost()

class Bullet(pygame.sprite.Sprite):
    """Projectile tiré par le joueur.

    Se déplace verticalement vers le haut (valeur `speed` négative).
    """
    def __init__(self,x,y,image_surface,speed=-8):
        super().__init__()
        self.image=image_surface
        self.rect=self.image.get_rect(midbottom=(x,y))
        self.speed=speed
    
    def update(self,*_):
        """Met à jour la position du projectile."""
        self.rect.y += self.speed
        if self.rect.bottom<0:
            self.kill()

class EnemyBullet(pygame.sprite.Sprite):
    """Projectile tiré par les ennemis.

    Peut suivre une trajectoire sinusoïdale (amplitude, fréquence, phase)
    et une dérive horizontale constante.
    """
    def __init__(self, x, y, speed=4, amp=0, freq=1.2, phase=0.0, drift=0.0):
        """
        speed : vitesse verticale (px/frame)
        amp   : amplitude horizontale (px)
        freq  : fréquence en Hz (oscillations par seconde, approx si FPS constant)
        phase : phase initiale (radians)
        drift : dérive horizontale constante (px/frame), 0 = aucune
        """
        super().__init__()
        # sprite simple 
        self.image = pygame.Surface((8, 24), pygame.SRCALPHA)
        self.image.fill((220, 80, 80))
        self.rect = self.image.get_rect(midtop=(x, y))

        # paramètres de mouvement
        self.speed = speed
        self.amp = amp
        self.freq = freq
        self.phase = phase
        self.drift = drift

        # états continus (pour éviter les erreurs d'arrondi)
        self.spawn_x = float(x)
        self.pos_y = float(y)
        self.t = 0.0                            # temps "simulé" en secondes approx
        self.omega = 2.0 * math.pi * self.freq

    def update(self, *_):
        # incrémente le temps
        self.t += 1.0 / FPS
        # avance verticalement
        self.pos_y += self.speed
        # oscillation horizontale + dérive éventuelle
        x = self.spawn_x + self.amp * math.sin(self.phase + self.omega * self.t) + self.drift * (self.t * FPS)
        # applique la position
        self.rect.y = int(self.pos_y)
        self.rect.centerx = int(x)
        # hors écran -> suppression
        if self.rect.top > Height or self.rect.right < -40 or self.rect.left > Width + 40:
            self.kill()

class Game:
    """Contrôleur principal du jeu.
    Initialise Pygame, gère la boucle principale, l'état du jeu, les sprites,
    les vagues d'ennemis, les collisions et l'affichage.
    """
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((Width,Height))
        pygame.display.set_caption("Space Invaders")
        self.clock=pygame.time.Clock()
        self.font=pygame.font.SysFont("comicsans", 40)
        self.title_font = pygame.font.SysFont("comicsans", 72)
        self.high_scores = []
        self.background = self.load_image("Fond.jpg", (Width, Height))
        self.state = MAIN_MENU # Démarre dans le menu principal
        self.load_high_scores()
        self.init_transition_vars() # Initialise les variables de transition
        self.reset(start_game=False) # Initialise le jeu sans démarrer une partie
        
    def load_image(self, filename, size=None, colorkey=None):
        """Charge une image depuis le dossier assets, gère erreurs et redimensionnement."""
        path = Assets / filename
        if not path.exists():                            # si le fichier n’existe pas on affiche une erreur et crée une surface rouge
            print(f"[⚠] Fichier introuvable : {path}")
            surf = pygame.Surface(size or (50, 50))      # carré rouge par défaut
            surf.fill(Red)
            return surf
        # Charge l'image et la convertit pour gérer correctement la transparence.
        if colorkey is not None:
            img = pygame.image.load(path).convert()
            img.set_colorkey(colorkey)                           # rend une couleur transparente
        else:
            img = pygame.image.load(path).convert_alpha()        # pour les PNG avec transparence
        if size:
            img = pygame.transform.smoothscale(img, size)        # redimensionne si demandé
        return img

    def load_high_scores(self):
        """Charge la liste des meilleurs scores depuis le fichier JSON"""
        logs_dir = Path(__file__).parent / "logs"
        logs_dir.mkdir(exist_ok=True)  # S'assure que le dossier "logs" existe
        self.high_score_file = logs_dir / "meilleurs_scores.json"
        try:    # Essaie de charger les scores existants
            with open(self.high_score_file, 'r') as f:
                self.high_scores = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):  # Fichier absent ou corrompu
            self.high_scores = []  # Crée une liste vide

    def save_high_scores(self):
        """Sauvegarde la liste des meilleurs scores dans le fichier"""
        with open(self.high_score_file, 'w') as f:
            json.dump(self.high_scores, f, indent=4)

    def check_for_high_score(self):
        """Vérifie si le score actuel est un meilleur score et retourne True si c'est le cas"""
        if len(self.high_scores) < MAX_HIGH_SCORES:
            return True
        '''La liste est triée par ordre décroissant, donc on vérifie par rapport au dernier score'''
        return self.score > self.high_scores[-1]['score']
        
    def reset(self, start_game=True):
        """Réinitialise le jeu à son état initial pour une nouvelle partie."""
        self.all_sprites=pygame.sprite.Group()
        self.bullet = pygame.sprite.Group()         # Groupe dédié aux projectiles (facilite la gestion/collisions).
        self.Opponent = pygame.sprite.Group()         # Groupe des ennemis.
        self.Boss=pygame.sprite.Group()
        self.EnemyBullet=pygame.sprite.Group()
        self.powerups = pygame.sprite.Group()

        if start_game:  # Démarre une nouvelle partie
            # --- Chargement des images depuis /assets ---
            self.player_img = self.load_image("Player.png", (75, 75))
            self.enemy_img = self.load_image("Ennemis.png", (75,75))
            self.armored_enemy_img = self.load_image("Ennemis_armored.png", (75,75))
            self.shooter_enemy_img = self.load_image("Ennemis_shooter.png", (75,75))
            self.player_bullet_img = self.load_image("player_bullet.png", (8, 24))
            
            # --- Chargement des images des power-ups ---
            self.health_powerup_img = self.load_image("powerup_health.png", (40, 40))
            self.shield_powerup_img = self.load_image("powerup_shield.png", (40, 40))
            self.firerate_powerup_img = self.load_image("powerup_firerate.png", (40, 40))
            self.boss_img = self.load_image("boss.png", (150, 150))
            
            # Création du joueur
            self.player=Player(Width/2,Height-30,self.player_img)
            self.all_sprites.add(self.player)

            # Initialisation de la première vague
            self.wave = 0
            self.start_new_wave()

        self.fleet_dir=1 #1 droite ; 0 gauche
        self.fleet_speed = 1
        self.drop_amount = 15
        self.score = 0 
        self.selected_option = 0 # Pour la navigation dans le menu
        self.player_name = "" # Pour la saisie du nom dans les meilleurs scores
        self.boss_spawned = False  # Ajout du flag boss_spawned

    def start_new_wave(self):
        """Configure le début d'une nouvelle vague."""
        self.wave += 1
        self.boss_spawned = False
        self.EnemyBullet.empty() # Enlève les projectiles ennemis restants
        self.all_sprites.remove(self.EnemyBullet)

        # Génère les ennemis en fonction du numéro de la vague
        top_row_enemies = min(12, 7 + self.wave) # La rangée du haut est la plus large
        enemy_spacing = 110
        num_rows = 3

        for row_index in range(num_rows):
            # Chaque rangée a 2 ennemis de moins que celle au-dessus
            enemies_in_this_row = top_row_enemies - (row_index * 2)
            if enemies_in_this_row <= 0:
                continue # Ne crée pas de rangées vides ou négatives

            fleet_width = (enemies_in_this_row - 1) * enemy_spacing + self.enemy_img.get_width()
            start_x = (Width - fleet_width) / 2
            y_pos = 100 + row_index * 60 # 60 pixels entre les rangées
            for i in range(enemies_in_this_row):
                x_pos = start_x + i * enemy_spacing
                # La rangée du haut a des ennemis blindés, les autres sont des tireurs
                if row_index == 0 and i % 4 == 1:
                    enemy = ArmoredOpponent(x_pos, y_pos, self.armored_enemy_img)
                else:
                    enemy = ShooterOpponent(x_pos, y_pos, self.shooter_enemy_img)
                self.Opponent.add(enemy)
                self.all_sprites.add(enemy)

    def start_transition(self, next_state):
        """Démarre une transition en fondu vers un autre état."""
        if self.state != TRANSITION:
            self.transition_target_state = next_state
            self.state = TRANSITION
            self.fading_out = True

    def init_transition_vars(self):
        """Initialise ou réinitialise les variables utilisées pour les transitions."""
        self.transition_alpha = 0
        self.transition_speed = 10 # Vitesse du fondu
        self.transition_target_state = None
        self.fading_out = False
        self.transition_surface = pygame.Surface((Width, Height))
        self.transition_surface.fill((0, 0, 0))

    def run(self):
        """Boucle principale du jeu."""
        while True:
            self.clock.tick(FPS)
            self.handle_events()   # Gère les entrées utilisateur
            self.update()          # Met à jour la logique du jeu
            self.draw()            # Dessine tout à l'écran

    def handle_events(self):
        """Gère les événements Pygame (clavier, fermeture de la fenêtre, etc.)."""
        for event in pygame.event.get(): # Parcourt tous les événements
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN: # Gère les entrées clavier
                if self.state == MAIN_MENU:
                    if event.key == pygame.K_DOWN:
                        self.selected_option = (self.selected_option + 1) % 3
                    elif event.key == pygame.K_UP:
                        self.selected_option = (self.selected_option - 1) % 3
                    elif event.key == pygame.K_RETURN:
                        if self.selected_option == 0: # Play
                            self.start_transition(PLAYING)
                        elif self.selected_option == 1: # High Scores
                            self.start_transition(HIGH_SCORE_SCREEN)
                        elif self.selected_option == 2: # Exit
                            pygame.quit()
                            sys.exit()
                
                elif self.state == HIGH_SCORE_SCREEN: # Retour au menu principal
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
                        self.start_transition(MAIN_MENU)

                elif self.state == PLAYING: # Jeu en cours
                    if event.key == pygame.K_SPACE:
                        self.player.shoot(self.bullet,self.all_sprites, self.player_bullet_img)
                    elif event.key == pygame.K_ESCAPE:
                        self.state = PAUSED
                        self.selected_option = 0 # Réinitialise la sélection du menu pause
                
                elif self.state == PAUSED: # Menu pause
                    if event.key == pygame.K_DOWN:
                        self.selected_option = (self.selected_option + 1) % 3
                    elif event.key == pygame.K_UP:
                        self.selected_option = (self.selected_option - 1) % 3
                    elif event.key == pygame.K_ESCAPE:
                        self.state = PLAYING # Reprendre avec ESC
                    elif event.key == pygame.K_RETURN:
                        if self.selected_option == 0: # Reprendre
                            self.state = PLAYING
                        elif self.selected_option == 1: # Menu principal
                            self.start_transition(MAIN_MENU)
                        elif self.selected_option == 2: # Quitter
                            pygame.quit()
                            sys.exit()

                elif self.state == ENTERING_NAME: # Saisie du nom pour le high score
                    if event.key == pygame.K_RETURN:
                        new_score = {'name': self.player_name or "AAA", 'score': self.score, 'wave': self.wave}
                        self.high_scores.append(new_score)
                        # Trie par score décroissant
                        self.high_scores.sort(key=lambda x: x['score'], reverse=True)
                        # Garde seulement les meilleurs scores
                        self.high_scores = self.high_scores[:MAX_HIGH_SCORES]
                        self.save_high_scores()
                        self.start_transition(HIGH_SCORE_SCREEN)
                    elif event.key == pygame.K_BACKSPACE:
                        self.player_name = self.player_name[:-1]
                    elif len(self.player_name) < 10: # Limite la longueur du nom
                        self.player_name += event.unicode
                
                elif self.state == GAME_OVER: # Écran de fin de partie
                    if event.key == pygame.K_r:
                        self.start_transition(PLAYING)
                    elif event.key == pygame.K_ESCAPE:
                        self.start_transition(MAIN_MENU)

    def update(self):
        """Met à jour la logique du jeu en fonction de l'état actuel (State Machine)."""
        if self.state == TRANSITION:
            self.handle_transition()
        elif self.state == PLAYING:
            self.update_playing()
        elif self.state == GAME_OVER:
            # Vérifie si le score est un high score pour passer à l'écran de saisie
            if self.check_for_high_score():
                self.state = ENTERING_NAME
                self.player_name = "" # Réinitialise le nom pour la saisie
        # Les états MAIN_MENU, HIGH_SCORE_SCREEN, PAUSED, et ENTERING_NAME
        # n'ont pas de logique de mise à jour continue, ils ne réagissent qu'aux événements.

    def update_playing(self):
        """Met à jour la logique du jeu quand l'état est PLAYING."""
        if self.state != PLAYING:
            return

        keys=pygame.key.get_pressed()
        self.all_sprites.update(keys)
        
        #Déplacement de la flotte
        edge_hit=False
        # Mouvement des ennemis normaux
        for e in self.Opponent:
            e.rect.x += self.fleet_dir * self.fleet_speed
            if e.rect.right >= Width-5 or e.rect.left <= 5:
                edge_hit = True
        
        # Mouvement du boss (s'il existe)
        for b in self.Boss:
            b.rect.x += self.fleet_dir * self.fleet_speed
            if b.rect.right >= Width-5 or b.rect.left <= 5:
                edge_hit = True
                
        if edge_hit: # Si un ennemi OU le boss a touché le bord
            self.fleet_dir *= -1 # Reverse direction
            # Déplace tout les ennemis vers le bas
            for opponent in self.Opponent:
                opponent.rect.y += self.drop_amount
            # Déplace le boss vers le bas
            for boss in self.Boss:
                boss.rect.y += self.drop_amount
                
        # collisions avec les ennemis
        hits = pygame.sprite.groupcollide(self.Opponent, self.bullet, False, True)
        for opponent, bullets_hit in hits.items():
            for _ in bullets_hit:
                is_killed = opponent.hit()
                if is_killed:
                    self.score += opponent.score_value
        
        # collisions avec le boss
        boss_hits = pygame.sprite.groupcollide(self.Boss, self.bullet, False, True)
        for boss in boss_hits:
            if boss.HP > 0: # Empêche plusieurs drops de power-up si plusieurs balles touchent sur la même frame
                boss.hit()
                self.score += 25
                if boss.HP <= 0:
                    # Choisit aléatoirement un power-up à faire apparaître
                    powerup_choice = random.choice(['health', 'shield', 'firerate'])
                    if powerup_choice == 'health':
                        powerup = HealthPowerUp(boss.rect.center, self.health_powerup_img)
                    elif powerup_choice == 'shield':
                        powerup = ShieldPowerUp(boss.rect.center, self.shield_powerup_img)
                    else: # firerate
                        powerup = FireRatePowerUp(boss.rect.center, self.firerate_powerup_img)

                    self.all_sprites.add(powerup)
                    self.powerups.add(powerup)
                    self.score += 100 # Bonus de score pour avoir vaincu le boss

        #Evenement de fin de partie
        if not self.Opponent and not self.boss_spawned: #Si il n'y à plus d'ennemis et que le boss n'est pas apparus le boss apparait"
            boss = Boss(self.boss_img, self.wave, x=Width/2, y=100)
            self.Boss.add(boss)
            self.all_sprites.add(boss)
            self.boss_spawned = True
        
        if self.boss_spawned and not self.Boss: # Le boss est vaincu on commence la vague suivante
            self.start_new_wave()
        
        for e in self.Opponent:
            if e.rect.bottom >= Height-40:      #Si les ennemis atteignent le bas de l'écran on perd
                self.state = GAME_OVER
                # On sort de la boucle de mise à jour du jeu car la partie est finie.
                return
            if e.rect.colliderect(self.player.rect):    #Si le joueur touche un ennemis il perd toute sa vie
                self.player.take_damage(self.player.max_lives)
                if self.player.lives <= 0: self.state = GAME_OVER

        # Logique de tir des ennemis
        shoot_probability = 0.001 + (self.wave * 0.0005) # La probabilité de tir augmente avec les vagues
        for enemy in self.Opponent:
            if isinstance(enemy, ShooterOpponent) and enemy.can_shoot(shoot_probability):
                b = EnemyBullet(enemy.rect.centerx, enemy.rect.bottom)
                self.EnemyBullet.add(b)
                self.all_sprites.add(b)
                break # Un seul ennemi tire par frame pour éviter le spam de balles

        # Tir du boss
        for boss in self.Boss:
            if boss.can_shoot():
                # Le boss tire trois balles en même temps en créant un effet de spread
                b1 = EnemyBullet(boss.rect.left, boss.rect.bottom, speed=5, drift=-1)
                b2 = EnemyBullet(boss.rect.centerx, boss.rect.bottom, speed=7) # La balle du milieu est plus rapide et droite
                b3 = EnemyBullet(boss.rect.right, boss.rect.bottom, speed=5, drift=1)
                self.EnemyBullet.add(b1, b2, b3)
                self.all_sprites.add(b1, b2, b3)
                boss.last_shot = pygame.time.get_ticks() # Réinitialise le cooldown
        
        # Collision joueur - powerup
        powerup_hits = pygame.sprite.spritecollide(self.player, self.powerups, True) # Supprime le power-up ramassé
        for hit in powerup_hits:    # Applique l'effet du power-up au joueur
            hit.apply_effect(self.player)
            self.score += 100 # Bonus de score pour la collecte

        # Collision balle ennemie - joueur
        if pygame.sprite.spritecollide(self.player, self.EnemyBullet, True): # Supprime la balle qui touche le joueur
            if not self.player.shield_active: # Le joueur ne prend pas de dégâts si le bouclier est actif
                self.player.take_damage(1)
                if self.player.lives <= 0:    # Le joueur n'a plus de vie -> fin de partie
                    self.state = GAME_OVER

    def handle_transition(self):
        """Gère l'animation de fondu entre les états."""
        if self.fading_out:
            self.transition_alpha += self.transition_speed
            if self.transition_alpha >= 255:
                self.transition_alpha = 255
                self.fading_out = False

                # C'est ici qu'on change réellement l'état du jeu (au milieu de la transition)
                if self.transition_target_state == PLAYING:
                    self.reset(start_game=True) # Réinitialise et démarre une partie
                elif self.transition_target_state == MAIN_MENU:
                    self.reset(start_game=False) # Réinitialise sans démarrer de partie
                elif self.transition_target_state == HIGH_SCORE_SCREEN:
                    self.reset(start_game=False) # Réinitialise aussi pour éviter les bugs après une partie
        else: # Fading in
            self.transition_alpha -= self.transition_speed
            if self.transition_alpha <= 0:
                self.transition_alpha = 0
                # La transition est terminée, on change l'état pour de bon.
                self.state = self.transition_target_state
                self.transition_target_state = None # Nettoie la cible
                self.init_transition_vars() # Réinitialise les variables de transition pour la prochaine fois

    def draw(self):
        """Dessine tout à l'écran."""
        # Détermine quel écran dessiner en arrière-plan
        current_state_to_draw = self.state
        if self.state == TRANSITION:
            current_state_to_draw = self.transition_target_state

        self.screen.blit(self.background, (0, 0))

        if current_state_to_draw == MAIN_MENU:
            self.draw_main_menu()
        elif current_state_to_draw == HIGH_SCORE_SCREEN:
            self.draw_high_score_screen()
        elif current_state_to_draw == PAUSED:
            self.draw_pause_menu()
        elif current_state_to_draw == ENTERING_NAME:
            self.draw_name_entry_screen()
        elif current_state_to_draw == PLAYING or current_state_to_draw == GAME_OVER:
            self.draw_game_screen()
        
        # Si l'état actuel est un menu, on le dessine par-dessus le jeu si nécessaire
        if self.state == PAUSED:
            self.draw_pause_menu()

        # Dessine l'effet de transition par-dessus tout le reste
        if self.state == TRANSITION or self.transition_alpha > 0:
            self.transition_surface.set_alpha(self.transition_alpha)
            self.screen.blit(self.transition_surface, (0, 0))

        pygame.display.flip() # Met à jour l'affichage

    def draw_previous_state_for_transition(self):
        """Redessine l'écran approprié en fonction de l'état de destination."""
        # Cette fonction est un peu une rustine pour que le fondu entrant ait un fond.
        pass # Pour l'instant, on ne fait rien, le fond noir suffit.

    def draw_game_screen(self):
        """Dessine l'écran de jeu"""
        # On ne dessine les éléments de jeu que si un joueur existe.
        if hasattr(self, 'player'):
            self.all_sprites.draw(self.screen)
            #HUD
            score_surf = self.font.render("Score: %d" % self.score, True, White)
            self.screen.blit(score_surf, (10, 10))

            # Barre de vie du joueur
            PLAYER_BAR_LENGTH = 150
            PLAYER_BAR_HEIGHT = 20
            #On la place en bas à gauche
            bar_x = 10
            bar_y = Height - PLAYER_BAR_HEIGHT - 10

            fill_percent = max(0, self.player.lives / self.player.max_lives)    # Pourcentage de vie restante
            fill_width = PLAYER_BAR_LENGTH * fill_percent                     # Largeur de la barre remplie
            
            # Dessine la barre de vie
            outline_rect = pygame.Rect(bar_x, bar_y, PLAYER_BAR_LENGTH, PLAYER_BAR_HEIGHT)
            fill_rect = pygame.Rect(bar_x, bar_y, fill_width, PLAYER_BAR_HEIGHT)
            pygame.draw.rect(self.screen, Green, fill_rect)
            pygame.draw.rect(self.screen, White, outline_rect, 2) # Bordure

            # Bouclier du joueur
            if self.player.shield_active:
                pygame.draw.circle(self.screen, Blue, self.player.rect.center, 55, 3) # Cercle bleu autour du joueur représentant le bouclier

            # Barre de vie du boss
            if self.boss_spawned:
                for boss in self.Boss: # Il n'y aura qu'un boss à la fois
                    BAR_LENGTH = 400
                    BAR_HEIGHT = 30
                    fill_percent = max(0, boss.HP / boss.max_HP)
                    fill_width = BAR_LENGTH * fill_percent
                    
                    # Dessine la barre de vie du boss
                    outline_rect = pygame.Rect((Width - BAR_LENGTH) / 2, 50, BAR_LENGTH, BAR_HEIGHT)
                    fill_rect = pygame.Rect((Width - BAR_LENGTH) / 2, 50, fill_width, BAR_HEIGHT)
                    pygame.draw.rect(self.screen, Red, outline_rect)
                    pygame.draw.rect(self.screen, Green, fill_rect)
                    pygame.draw.rect(self.screen, White, outline_rect, 3) # Bordure
            
            # Numéro de la vague
            wave_surf = self.font.render("Vague: %d" % self.wave, True, White)
            self.screen.blit(wave_surf, (Width/2 - wave_surf.get_width()/2,0))

        if self.state == GAME_OVER: # Dessine l'écran de fin de partie
            msg = self.font.render("FIN : Appuie sur R pour recommencer", True, White)
            rect = msg.get_rect(centerx=Width//2, centery=Height//2)
            self.screen.blit(msg, rect)
            back_msg = self.font.render("Appuie sur ESC pour retourner au menu", True, White)
            back_rect = back_msg.get_rect(centerx=Width//2, centery=Height//2 + 50)
            self.screen.blit(back_msg, back_rect)

    def draw_pause_menu(self):
        # D'abord, dessine l'écran de jeu tel qu'il était lors de la pause
        self.draw_game_screen()

        # Ensuite, dessine une superposition semi-transparente
        overlay = pygame.Surface((Width, Height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # Affiche le menu de pause
        title_surf = self.title_font.render("Pause", True, White)
        self.screen.blit(title_surf, (Width/2 - title_surf.get_width()/2, Height/4))

        # Options du menu de pause
        options = ["Reprendre", "Menu Principal", "Quitter"]
        for i, option in enumerate(options):
            color = Orange if i == self.selected_option else White
            text_surf = self.font.render(option, True, color)
            text_rect = text_surf.get_rect(center=(Width/2, Height/2 + i * 60))
            self.screen.blit(text_surf, text_rect)

    def draw_main_menu(self):
        '''Dessine le menu principal'''
        title_surf = self.title_font.render("Space Invaders", True, White)
        self.screen.blit(title_surf, (Width/2 - title_surf.get_width()/2, Height/4))
        # Options du menu principal
        options = ["Jouer", "Meilleurs Scores", "Quitter"]
        for i, option in enumerate(options):
            color = Orange if i == self.selected_option else White
            text_surf = self.font.render(option, True, color)
            text_rect = text_surf.get_rect(center=(Width/2, Height/2 + i * 60))
            self.screen.blit(text_surf, text_rect)

    def draw_high_score_screen(self):
        '''Dessine l'écran des meilleurs scores'''
        title_surf = self.title_font.render("Meilleurs Scores", True, White)
        self.screen.blit(title_surf, (Width/2 - title_surf.get_width()/2, Height/4))
        
        if not self.high_scores: # Si aucun score n'est enregistré
            no_scores_surf = self.font.render("Aucun score enregistré", True, White)
            self.screen.blit(no_scores_surf, (Width/2 - no_scores_surf.get_width()/2, Height/2))
        else: # Affiche les scores
            for i, score_entry in enumerate(self.high_scores):
                name = score_entry['name']
                score = score_entry['score']
                wave = score_entry['wave']
                text = f"{i+1}. {name:<10} - {score:08d} - Vague: {wave}"
                
                color = Orange if i == 0 else White
                score_surf = self.font.render(text, True, color)
                
                y_pos = Height/2 - 80 + i * 50
                self.screen.blit(score_surf, (Width/2 - score_surf.get_width()/2, y_pos))

        # Instruction pour revenir au menu
        back_surf = self.font.render("Appuyez sur Entrée ou Echap pour retourner", True, Orange)
        self.screen.blit(back_surf, (Width/2 - back_surf.get_width()/2, Height - 100))

    def draw_name_entry_screen(self):
        '''Dessine l'écran de saisie du nom pour le meilleur score'''
        self.screen.blit(self.background, (0, 0))
        title_surf = self.title_font.render("Nouveau Meilleur Score!", True, Orange)
        self.screen.blit(title_surf, (Width/2 - title_surf.get_width()/2, Height/4))

        prompt_surf = self.font.render("Entrez votre nom:", True, White) # Invite à entrer le nom du joueur
        self.screen.blit(prompt_surf, (Width/2 - prompt_surf.get_width()/2, Height/2 - 50))

        # Crée un effet de curseur clignotant
        cursor_char = "_" if int(pygame.time.get_ticks() / 500) % 2 == 0 else " "
        name_surf = self.font.render(self.player_name + cursor_char, True, White)
        self.screen.blit(name_surf, (Width/2 - name_surf.get_width()/2, Height/2 + 10))

        continue_surf = self.font.render("Appuyez sur Entrée pour continuer", True, White)
        self.screen.blit(continue_surf, (Width/2 - continue_surf.get_width()/2, Height - 100))

if __name__=="__main__":    # Lance le jeu
    Game().run()
