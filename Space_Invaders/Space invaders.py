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
White = (255, 255, 255)           # Définition de la couleur blanc en RGB (non utilisée ici).
Black = (0, 0, 0)                 # Définition de la couleur noir en RGB (pour le fond).
Green = (80, 220, 100)
Red = (220,80,100)
Orange=(255,119,0)
PLAYING=0
GAME_OVER=1
MAIN_MENU = 2
HIGH_SCORE_SCREEN = 3
PAUSED = 4
ENTERING_NAME = 5
MAX_HIGH_SCORES = 5

# --- Répertoire des assets ---
# Cette ligne définit le dossier dans lequel se trouvent toutes les images du jeu.
# On part du dossier où se trouve ce fichier Python (__file__), puis on ajoute "assets".
Assets = Path(__file__).parent / "assets"

class Player(pygame.sprite.Sprite):
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
        self.base_shoot_cooldown = 300
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
        # Applique la friction
        self.velocity += self.velocity * self.friction
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

        # Cap the speed
        if self.velocity.length() > self.max_speed:
            self.velocity.scale_to_length(self.max_speed)

        # Met à jour la position
        self.rect.x += self.velocity.x
        self.rect.y += self.velocity.y
        
        # Mise à jour des power-ups
        now = pygame.time.get_ticks()
        if self.shield_active and now > self.shield_end_time:
            self.shield_active = False
        
        if self.fire_rate_boost_active and now > self.fire_rate_boost_end_time:
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
            self.velocity.y *= -0.5

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
        return pygame.time.get_ticks()-self.last_shot>=self.shoot_cooldown
    
    def shoot(self,bullets_group,all_sprites_group, bullet_image):
        if self.can_shoot():
            bullet=Bullet(self.rect.centerx,self.rect.top, bullet_image)
            bullets_group.add(bullet)
            all_sprites_group.add(bullet)
            self.last_shot=pygame.time.get_ticks()


class Opponent(pygame.sprite.Sprite):
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
    def __init__(self, x, y, image_surface):
        super().__init__(x, y, image_surface, hp=3, score_value=50)

class ShooterOpponent(Opponent):
    def __init__(self, x, y, image_surface):
        super().__init__(x, y, image_surface, hp=1, score_value=20)

    def can_shoot(self, probability):
        """Détermine si l'ennemi peut tirer en fonction d'une probabilité"""
        return random.random() < probability
        

class Boss(pygame.sprite.Sprite):
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
        self.HP -= 1
        if self.HP <= 0:
            self.kill()
    '''
    def update(self, *args):
        # Cette méthode update basique sera utilisée pour déplacer le boss.
        # Nous gérerons la logique de mouvement dans la méthode Game.update pour l'instant.
        # Si vous souhaitez un comportement de boss plus complexe, vous pouvez l'ajouter ici.
        pass
    '''
    def can_shoot(self):
        """Vérifie si le boss peut tirer en fonction du cooldown"""
        now = pygame.time.get_ticks()
        return now - self.last_shot >= self.shoot_cooldown


class PowerUp(pygame.sprite.Sprite):
    def __init__(self, center, image):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(center=center)
        self.speedy = 2

    def update(self, *_):
        self.rect.y += self.speedy
        if self.rect.top > Height:
            self.kill()
    '''
    def apply_effect(self, player):
        """Cette méthode sera surchargée par les sous-classes."""
        pass
        '''
class HealthPowerUp(PowerUp):
    def __init__(self, center, image):
        super().__init__(center, image)

    def apply_effect(self, player):
        player.add_health(10)

class ShieldPowerUp(PowerUp):
    def __init__(self, center, image):
        super().__init__(center, image)

    def apply_effect(self, player):
        player.activate_shield()

class FireRatePowerUp(PowerUp):
    def __init__(self, center, image):
        super().__init__(center, image)

    def apply_effect(self, player):
        player.activate_fire_rate_boost()

class Bullet(pygame.sprite.Sprite):
    def __init__(self,x,y,image_surface,speed=-8):
        super().__init__()
        self.image=image_surface
        self.rect=self.image.get_rect(midbottom=(x,y))
        self.speed=speed
    
    def update(self,*_):
        self.rect.y += self.speed
        if self.rect.bottom<0:
            self.kill()

class EnemyBullet(pygame.sprite.Sprite):
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
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((Width,Height))
        pygame.display.set_caption("Space Invaders")
        self.clock=pygame.time.Clock()
        self.font=pygame.font.SysFont("comicsans", 40)
        self.title_font = pygame.font.SysFont("comicsans", 72)
        self.high_scores = []
        self.background = self.load_image("Fond.jpg", (Width, Height))
        self.state = MAIN_MENU # Start in the main menu
        self.load_high_scores()
        self.reset(start_game=False) # Initialize game variables without starting
        
    def load_image(self, filename, size=None, colorkey=None):
        """Charge une image depuis le dossier assets, gère erreurs et redimensionnement."""
        path = Assets / filename
        if not path.exists():                                    # si le fichier n’existe pas
            print(f"[⚠] Fichier introuvable : {path}")
            surf = pygame.Surface(size or (50, 50))              # carré rouge par défaut
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
        logs_dir.mkdir(exist_ok=True)  # Assure que le dossier logs existe
        self.high_score_file = logs_dir / "meilleurs_scores.json"
        try:
            with open(self.high_score_file, 'r') as f:
                self.high_scores = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.high_scores = []

    def save_high_scores(self):
        """Sauvegarde la liste des meilleurs scores dans le fichier"""
        with open(self.high_score_file, 'w') as f:
            json.dump(self.high_scores, f, indent=4)

    def check_for_high_score(self):
        """Vérifie si le score actuel est un meilleur score et retourne True si c'est le cas"""
        if len(self.high_scores) < MAX_HIGH_SCORES:
            return True
        # La liste est triée par ordre décroissant, donc on vérifie par rapport au dernier score
        return self.score > self.high_scores[-1]['score']
        
    def reset(self, start_game=True):
        """Réinitialise le jeu à son état initial pour une nouvelle partie."""
        self.all_sprites=pygame.sprite.Group()
        self.bullet = pygame.sprite.Group()         # Groupe dédié aux projectiles (facilite la gestion/collisions).
        self.Opponent = pygame.sprite.Group()         # Groupe des ennemis.
        self.Boss=pygame.sprite.Group()
        self.EnemyBullet=pygame.sprite.Group()
        self.powerups = pygame.sprite.Group()

        if start_game:
            # --- Chargement des images depuis /assets ---
            self.player_img = self.load_image("Player.png", (75, 75))
            self.enemy_img = self.load_image("Ennemis.png", (75,75)) # Utilise un des PNG pour le calcul de la largeur
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

            self.wave = 0
            self.start_new_wave()
            self.state = PLAYING

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
        self.EnemyBullet.empty() # Clear any remaining bullets
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

    def run(self):
        while True:
            self.clock.tick(FPS)
            self.handle_events()
            self.update()
            self.draw()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if self.state == MAIN_MENU:
                    if event.key == pygame.K_DOWN:
                        self.selected_option = (self.selected_option + 1) % 3
                    elif event.key == pygame.K_UP:
                        self.selected_option = (self.selected_option - 1) % 3
                    elif event.key == pygame.K_RETURN:
                        if self.selected_option == 0: # Play
                            self.reset()
                        elif self.selected_option == 1: # High Scores
                            self.state = HIGH_SCORE_SCREEN
                        elif self.selected_option == 2: # Exit
                            pygame.quit()
                            sys.exit()
                
                elif self.state == HIGH_SCORE_SCREEN:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
                        self.state = MAIN_MENU

                elif self.state == PLAYING:
                    if event.key == pygame.K_SPACE:
                        self.player.shoot(self.bullet,self.all_sprites, self.player_bullet_img)
                    elif event.key == pygame.K_ESCAPE:
                        self.state = PAUSED
                        self.selected_option = 0 # Réinitialise la sélection du menu pause
                
                elif self.state == PAUSED:
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
                            self.state = MAIN_MENU
                        elif self.selected_option == 2: # Quitter
                            pygame.quit()
                            sys.exit()
                elif self.state == ENTERING_NAME:
                    if event.key == pygame.K_RETURN:
                        new_score = {'name': self.player_name or "AAA", 'score': self.score, 'wave': self.wave}
                        self.high_scores.append(new_score)
                        # Trie par score décroissant
                        self.high_scores.sort(key=lambda x: x['score'], reverse=True)
                        # Garde seulement les meilleurs scores
                        self.high_scores = self.high_scores[:MAX_HIGH_SCORES]
                        self.save_high_scores()
                        self.state = HIGH_SCORE_SCREEN
                    elif event.key == pygame.K_BACKSPACE:
                        self.player_name = self.player_name[:-1]
                    elif len(self.player_name) < 10: # Limite la longueur du nom
                        self.player_name += event.unicode
                
                elif self.state == GAME_OVER:
                    if event.key == pygame.K_r:
                        self.reset()
                        self.load_high_scores() # Recharge les scores lors de la réinitialisation
                    elif event.key == pygame.K_ESCAPE:
                        self.state = MAIN_MENU # Retour au menu

    def update(self):
        # Met à jour la logique du jeu uniquement si l'état est PLAYING
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
        if not self.Opponent and not self.boss_spawned: #Si il n'y à plus d'ennemis et que le boss n'est pas apparus"
            boss = Boss(self.boss_img, self.wave, x=Width/2, y=100)
            self.Boss.add(boss)
            self.all_sprites.add(boss)
            self.boss_spawned = True
        
        if self.boss_spawned and not self.Boss: # Le boss est vaincu, commence la vague suivante
            self.start_new_wave()
        
        for e in self.Opponent:
            if e.rect.bottom >= Height-40:      #Si les ennemis atteignent le bas de l'écran
                self.state = GAME_OVER # You lose
            if e.rect.colliderect(self.player.rect):    #Si le joueur touche un ennemis
                self.player.take_damage(self.player.max_lives) # Mort instantanée au contact
                if self.player.lives <= 0: self.state = GAME_OVER

        # Logique de tir des ennemis
        shoot_probability = 0.001 + (self.wave * 0.0005) # La probabilité augmente avec les vagues
        for enemy in self.Opponent:
            if isinstance(enemy, ShooterOpponent) and enemy.can_shoot(shoot_probability):
                b = EnemyBullet(enemy.rect.centerx, enemy.rect.bottom)
                self.EnemyBullet.add(b)
                self.all_sprites.add(b)
                break # Un seul ennemi tire par frame pour éviter le spam de balles

        # Tir du boss
        for boss in self.Boss:
            if boss.can_shoot():
                # Le boss tire trois balles en même temps
                b1 = EnemyBullet(boss.rect.left, boss.rect.bottom, speed=5, drift=-1)
                b2 = EnemyBullet(boss.rect.centerx, boss.rect.bottom, speed=7) # La balle du milieu est plus rapide
                b3 = EnemyBullet(boss.rect.right, boss.rect.bottom, speed=5, drift=1)
                self.EnemyBullet.add(b1, b2, b3)
                self.all_sprites.add(b1, b2, b3)
                boss.last_shot = pygame.time.get_ticks() # Réinitialise le cooldown
        
        # Collision joueur - powerup
        powerup_hits = pygame.sprite.spritecollide(self.player, self.powerups, True)
        for hit in powerup_hits:
            hit.apply_effect(self.player)
            self.score += 100 # Bonus de score pour la collecte

        # Collision balle ennemie - joueur
        if pygame.sprite.spritecollide(self.player, self.EnemyBullet, True):
            if not self.player.shield_active:
                self.player.take_damage(1)
                if self.player.lives <= 0:
                    self.state = GAME_OVER

        # Vérifie la fin de la partie et met à jour les meilleurs scores
        if self.state == GAME_OVER:
            if self.check_for_high_score():
                self.state = ENTERING_NAME
                self.player_name = "" # Réinitialise le nom pour la saisie
    def draw(self):
        self.screen.blit(self.background,(0,0))

        if self.state == MAIN_MENU:
            self.draw_main_menu()
        elif self.state == HIGH_SCORE_SCREEN:
            self.draw_high_score_screen()
        elif self.state == PAUSED:
            self.draw_pause_menu()
        elif self.state == ENTERING_NAME:
            self.draw_name_entry_screen()
        else:
            self.draw_game_screen()

        pygame.display.flip()

    def draw_game_screen(self):
        self.all_sprites.draw(self.screen)
        #HUD
        score_surf = self.font.render("Score: %d" % self.score, True, White)
        self.screen.blit(score_surf, (10, 10))

        # Barre de vie du joueur
        PLAYER_BAR_LENGTH = 150
        PLAYER_BAR_HEIGHT = 20
        # Positionne-la en bas à gauche
        bar_x = 10
        bar_y = Height - PLAYER_BAR_HEIGHT - 10

        fill_percent = max(0, self.player.lives / self.player.max_lives)
        fill_width = PLAYER_BAR_LENGTH * fill_percent
        
        outline_rect = pygame.Rect(bar_x, bar_y, PLAYER_BAR_LENGTH, PLAYER_BAR_HEIGHT)
        fill_rect = pygame.Rect(bar_x, bar_y, fill_width, PLAYER_BAR_HEIGHT)
        pygame.draw.rect(self.screen, Green, fill_rect)
        pygame.draw.rect(self.screen, White, outline_rect, 2) # Bordure

        # Bouclier du joueur
        if self.player.shield_active:
            pygame.draw.circle(self.screen, Blue, self.player.rect.center, 55, 3)

        # Barre de vie du boss
        if self.boss_spawned:
            for boss in self.Boss: # Il n'y aura qu'un boss à la fois
                BAR_LENGTH = 400
                BAR_HEIGHT = 30
                fill_percent = max(0, boss.HP / boss.max_HP)
                fill_width = BAR_LENGTH * fill_percent
                
                outline_rect = pygame.Rect((Width - BAR_LENGTH) / 2, 50, BAR_LENGTH, BAR_HEIGHT)
                fill_rect = pygame.Rect((Width - BAR_LENGTH) / 2, 50, fill_width, BAR_HEIGHT)
                
                pygame.draw.rect(self.screen, Red, outline_rect)
                pygame.draw.rect(self.screen, Green, fill_rect)
                pygame.draw.rect(self.screen, White, outline_rect, 3) # Bordure
        wave_surf = self.font.render("Vague: %d" % self.wave, True, White)
        self.screen.blit(wave_surf, (Width/2 - wave_surf.get_width()/2, 10))


        if self.state == GAME_OVER:
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

        options = ["Reprendre", "Menu Principal", "Quitter"]
        for i, option in enumerate(options):
            color = Orange if i == self.selected_option else White
            text_surf = self.font.render(option, True, color)
            text_rect = text_surf.get_rect(center=(Width/2, Height/2 + i * 60))
            self.screen.blit(text_surf, text_rect)

    def draw_main_menu(self):
        title_surf = self.title_font.render("Space Invaders", True, White)
        self.screen.blit(title_surf, (Width/2 - title_surf.get_width()/2, Height/4))

        options = ["Jouer", "Meilleurs Scores", "Quitter"]
        for i, option in enumerate(options):
            color = Orange if i == self.selected_option else White
            text_surf = self.font.render(option, True, color)
            text_rect = text_surf.get_rect(center=(Width/2, Height/2 + i * 60))
            self.screen.blit(text_surf, text_rect)

    def draw_high_score_screen(self):
        title_surf = self.title_font.render("Meilleurs Scores", True, White)
        self.screen.blit(title_surf, (Width/2 - title_surf.get_width()/2, Height/4))
        
        if not self.high_scores:
            no_scores_surf = self.font.render("Aucun score enregistré", True, White)
            self.screen.blit(no_scores_surf, (Width/2 - no_scores_surf.get_width()/2, Height/2))
        else:
            for i, score_entry in enumerate(self.high_scores):
                name = score_entry['name']
                score = score_entry['score']
                wave = score_entry['wave']
                text = f"{i+1}. {name:<10} - {score:08d} - Vague: {wave}"
                
                color = Orange if i == 0 else White
                score_surf = self.font.render(text, True, color)
                
                y_pos = Height/2 - 80 + i * 50
                self.screen.blit(score_surf, (Width/2 - score_surf.get_width()/2, y_pos))

        back_surf = self.font.render("Appuyez sur Entrée ou Echap pour retourner", True, Orange)
        self.screen.blit(back_surf, (Width/2 - back_surf.get_width()/2, Height - 100))

    def draw_name_entry_screen(self):
        self.screen.blit(self.background, (0, 0))
        title_surf = self.title_font.render("Nouveau Meilleur Score!", True, Orange)
        self.screen.blit(title_surf, (Width/2 - title_surf.get_width()/2, Height/4))

        prompt_surf = self.font.render("Entrez votre nom:", True, White)
        self.screen.blit(prompt_surf, (Width/2 - prompt_surf.get_width()/2, Height/2 - 50))

        # Crée un effet de curseur clignotant
        cursor_char = "_" if int(pygame.time.get_ticks() / 500) % 2 == 0 else " "
        name_surf = self.font.render(self.player_name + cursor_char, True, White)
        self.screen.blit(name_surf, (Width/2 - name_surf.get_width()/2, Height/2 + 10))

        continue_surf = self.font.render("Appuyez sur Entrée pour continuer", True, White)
        self.screen.blit(continue_surf, (Width/2 - continue_surf.get_width()/2, Height - 100))

if __name__=="__main__":
    Game().run()
