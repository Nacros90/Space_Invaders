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

# --- Répertoire des assets ---
# Cette ligne définit le dossier dans lequel se trouvent toutes les images du jeu.
# On part du dossier où se trouve ce fichier Python (__file__), puis on ajoute "assets".
Assets = Path(__file__).parent / "assets"

class Player(pygame.sprite.Sprite):
    def __init__(self,x,y,image_surface):
        super().__init__()
        self.image=image_surface
        self.rect=self.image.get_rect(midbottom=(x,y))
        
        # --- Physics for organic movement ---
        self.velocity = pygame.math.Vector2(0, 0)
        self.acceleration = 0.7
        self.friction = -0.12 # Value to slow down the ship
        self.max_speed = 7
        self.base_shoot_cooldown = 300 # The normal cooldown
        self.shoot_cooldown = self.base_shoot_cooldown     #en ms
        self.last_shot=0
        self.lives=20
        self.max_lives = self.lives

        # Power-up states
        self.shield_active = False
        self.shield_end_time = 0
        self.fire_rate_boost_active = False
        self.fire_rate_boost_end_time = 0

    def add_health(self, amount):
        """Adds health to the player, capping at max_lives."""
        self.lives += amount
        if self.lives > self.max_lives:
            self.lives = self.max_lives

    def take_damage(self, amount):
        """Reduces player's lives if shield is not active."""
        if not self.shield_active:
            self.lives -= amount

    def update(self,keys):
        # Apply friction
        self.velocity += self.velocity * self.friction
        # Stop movement if velocity is very low
        if self.velocity.length() < 0.1:
            self.velocity.x = 0
            self.velocity.y = 0

        # Apply acceleration based on key presses
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

        # Update position based on velocity
        self.rect.x += self.velocity.x
        self.rect.y += self.velocity.y
        
        # Update power-up timers
        now = pygame.time.get_ticks()
        if self.shield_active and now > self.shield_end_time:
            self.shield_active = False
        
        if self.fire_rate_boost_active and now > self.fire_rate_boost_end_time:
            self.fire_rate_boost_active = False
            self.shoot_cooldown = self.base_shoot_cooldown

        # Boundary check with "bump" effect
        if self.rect.left < 0:
            self.rect.left = 0
            self.velocity.x *= -0.5 # Reverse and dampen velocity
        if self.rect.right > Width:
            self.rect.right = Width
            self.velocity.x *= -0.5 # Reverse and dampen velocity
        if self.rect.top < 0:
            self.rect.top = 0
            self.velocity.y *= -0.5

    def activate_shield(self, duration=5000):
        """Activates the shield for a given duration in milliseconds."""
        self.shield_active = True
        self.shield_end_time = pygame.time.get_ticks() + duration

    def activate_fire_rate_boost(self, duration=7000):
        """Activates the fire rate boost for a given duration."""
        self.fire_rate_boost_active = True
        self.fire_rate_boost_end_time = pygame.time.get_ticks() + duration
        self.shoot_cooldown = self.base_shoot_cooldown / 2 # Double the fire rate
    
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
        self.image = image_surface.copy() # Use a copy to allow for color changes
        self.rect = self.image.get_rect(topleft=(x, y))
        self.hp = hp
        self.max_hp = hp
        self.score_value = score_value

    def hit(self):
        """Reduces HP by 1 and kills the sprite if HP is 0."""
        self.hp -= 1
        if self.hp <= 0:
            self.kill()
        return self.hp <= 0
'''
    def update(self, *args):
        # The base update is empty; movement is handled by the Game class for the fleet.
        pass
'''
class ArmoredOpponent(Opponent):
    def __init__(self, x, y, image_surface):
        super().__init__(x, y, image_surface, hp=3, score_value=50)
        # Tint the image to distinguish it
        self.image.fill((180, 180, 220), special_flags=pygame.BLEND_RGB_MULT)

class ShooterOpponent(Opponent):
    def __init__(self, x, y, image_surface):
        super().__init__(x, y, image_surface, hp=1, score_value=20)
        # Tint the image red to show it's a shooter
        self.image.fill((220, 180, 180), special_flags=pygame.BLEND_RGB_MULT)

    def can_shoot(self, probability):
        """Determines if the enemy can shoot based on a probability."""
        return random.random() < probability
        

class Boss(pygame.sprite.Sprite):
    def __init__(self, wave, x=450, y=100, speed=2.5):
        super().__init__()
        self.image=pygame.Surface((120,40))
        self.image.fill(Orange)
        self.rect=self.image.get_rect(topleft=(x,y))
        self.speed=speed

        # --- Scale difficulty with wave number ---
        self.HP = 10 + (wave - 1) * 5  # Starts at 10 HP, gains 5 HP each wave
        self.max_HP = self.HP
        # Starts at 1 sec cooldown, gets 8% faster each wave, minimum of 250ms
        self.shoot_cooldown = max(250, 1000 * (0.92 ** (wave - 1)))
        self.last_shot = pygame.time.get_ticks()

    def hit(self):
        self.HP -= 1
        if self.HP <= 0:
            self.kill()

    def update(self, *args):
        # This basic update method will be used to move the boss.
        # We'll handle the movement logic inside the Game.update method for now.
        # If you want more complex boss behavior, you can add it here.
        pass

    def can_shoot(self):
        """Checks if the boss can shoot based on the cooldown."""
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

    def apply_effect(self, player):
        """This method will be overridden by subclasses."""
        pass

class HealthPowerUp(PowerUp):
    def __init__(self, center):
        image = pygame.Surface((30, 30))
        image.fill(Green) # Green for health
        pygame.draw.rect(image, White, (12, 5, 6, 20)) # Plus sign
        pygame.draw.rect(image, White, (5, 12, 20, 6))
        super().__init__(center, image)

    def apply_effect(self, player):
        player.add_health(10)

class ShieldPowerUp(PowerUp):
    def __init__(self, center):
        image = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(image, Blue, (15, 15), 15)
        super().__init__(center, image)

    def apply_effect(self, player):
        player.activate_shield()

class FireRatePowerUp(PowerUp):
    def __init__(self, center):
        image = pygame.Surface((30, 30))
        image.fill((255, 165, 0)) # Orange for fire rate
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
        self.reset()
        self.state = MAIN_MENU # Start in the main menu
        self.load_high_scores()
        
    def load_image(self, filename, size=None, colorkey=None):
        """Charge une image depuis le dossier assets, gère erreurs et redimensionnement."""
        path = Assets / filename
        if not path.exists():                                    # si le fichier n’existe pas
            print(f"[⚠] Fichier introuvable : {path}")
            surf = pygame.Surface(size or (50, 50))              # carré rouge par défaut
            surf.fill(Red)
            return surf
        img = pygame.image.load(path).convert()                  # charge l’image
        if colorkey is not None:
            img.set_colorkey(colorkey)                           # rend une couleur transparente
        if size:
            img = pygame.transform.smoothscale(img, size)        # redimensionne si demandé
        return img

    def load_high_scores(self):
        """Loads high score and high wave from 'meilleurs_scores.txt' in the logs folder."""
        logs_dir = Path(__file__).parent / "logs"
        logs_dir.mkdir(exist_ok=True)  # Ensure the logs directory exists
        self.high_score_file = logs_dir / "meilleurs_scores.txt"
        try:
            with open(self.high_score_file, 'r') as f:
                self.high_score = int(f.readline())
                self.high_wave = int(f.readline())
        except (FileNotFoundError, ValueError):
            # If file doesn't exist or is empty/corrupt, start with 0
            self.high_score = 0
            self.high_wave = 0

    def save_high_scores(self):
        """Saves the current high score and wave to the file."""
        with open(self.high_score_file, 'w') as f:
            f.write(str(self.high_score) + '\n')
            f.write(str(self.high_wave) + '\n')
        
    def reset(self):
        """Resets the game to its initial state for a new game."""
        self.all_sprites=pygame.sprite.Group()
        self.bullet = pygame.sprite.Group()         # Groupe dédié aux projectiles (facilite la gestion/collisions).
        self.Opponent = pygame.sprite.Group()         # Groupe des ennemis.
        self.Boss=pygame.sprite.Group()
        self.EnemyBullet=pygame.sprite.Group()
        self.powerups = pygame.sprite.Group()

        # --- Chargement des images depuis /assets ---
        self.background = self.load_image("Fond.jpg", (Width, Height))
        self.player_img = self.load_image("Player.jpg", (54, 96), Black)
        self.enemy_img = self.load_image("Ennemis.jpg", (96,54))
        self.player_bullet_img = self.load_image("red.jpg", (8, 24))
        
        # Création du joueur
        self.player=Player(Width/2,Height-30,self.player_img)
        self.all_sprites.add(self.player)

        self.wave = 0
        self.start_new_wave()

        self.fleet_dir=1 #1 droite ; 0 gauche
        self.fleet_speed = 1
        self.drop_amount = 15
        self.state = PLAYING
        self.score = 0 
        self.selected_option = 0 # For menu navigation
        self.boss_spawned = False  # Ajout du flag boss_spawned

    def start_new_wave(self):
        """Sets up the start of a new wave."""
        self.wave += 1
        self.boss_spawned = False
        self.EnemyBullet.empty() # Clear any remaining bullets
        self.all_sprites.remove(self.EnemyBullet)

        # Spawn enemies based on the wave number
        top_row_enemies = min(12, 7 + self.wave) # Top row is widest
        enemy_spacing = 110
        num_rows = 3

        for row_index in range(num_rows):
            # Each row has 2 fewer enemies than the one above it
            enemies_in_this_row = top_row_enemies - (row_index * 2)
            if enemies_in_this_row <= 0:
                continue # Don't create empty or negative rows

            fleet_width = (enemies_in_this_row - 1) * enemy_spacing + self.enemy_img.get_width()
            start_x = (Width - fleet_width) / 2
            y_pos = 100 + row_index * 60 # 60 pixels between rows

            for i in range(enemies_in_this_row):
                x_pos = start_x + i * enemy_spacing
                # Top row has armored enemies, other rows are shooters
                if row_index == 0 and i % 4 == 1:
                    enemy = ArmoredOpponent(x_pos, y_pos, self.enemy_img)
                else:
                    enemy = ShooterOpponent(x_pos, y_pos, self.enemy_img)
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
                
                elif self.state == GAME_OVER:
                    if event.key == pygame.K_r:
                        self.reset()
                        self.load_high_scores() # Reload scores on reset
                    elif event.key == pygame.K_ESCAPE:
                        self.state = MAIN_MENU # Go back to menu

    def update(self):
        # Only update game logic if in PLAYING state
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
            if boss.HP > 0: # Prevent multiple powerup drops if multiple bullets hit on the same frame
                boss.hit()
                self.score += 25
                if boss.HP <= 0:
                    # Randomly choose a power-up to spawn
                    powerup_type = random.choice([HealthPowerUp, ShieldPowerUp, FireRatePowerUp])
                    powerup = powerup_type(boss.rect.center)
                    self.all_sprites.add(powerup)
                    self.powerups.add(powerup)
                    self.score += 100 # Bonus score for defeating the boss

        #Evenement de fin de partie
        if not self.Opponent and not self.boss_spawned: #Si il n'y à plus d'ennemis et que le boss n'est pas apparus"
            boss = Boss(self.wave, x=Width/2 - 60, y=100)
            self.Boss.add(boss)
            self.all_sprites.add(boss)
            self.boss_spawned = True
        
        if self.boss_spawned and not self.Boss: # Boss is defeated, start next wave
            self.start_new_wave()
        
        for e in self.Opponent:
            if e.rect.bottom >= Height-40:      #Si les ennemis atteignent le bas de l'écran
                self.state = GAME_OVER # You lose
            if e.rect.colliderect(self.player.rect):    #Si le joueur touche un ennemis
                self.player.take_damage(self.player.max_lives) # Instant death on collision
                if self.player.lives <= 0: self.state = GAME_OVER

        # Enemy shooting logic
        shoot_probability = 0.001 + (self.wave * 0.0005) # Probability increases with waves
        for enemy in self.Opponent:
            if isinstance(enemy, ShooterOpponent) and enemy.can_shoot(shoot_probability):
                b = EnemyBullet(enemy.rect.centerx, enemy.rect.bottom)
                self.EnemyBullet.add(b)
                self.all_sprites.add(b)
                break # Only one enemy shoots per frame to avoid bullet spam

        # Tir du boss
        for boss in self.Boss:
            if boss.can_shoot():
                # The boss shoots three bullets at once
                b1 = EnemyBullet(boss.rect.left, boss.rect.bottom, speed=5, drift=-1)
                b2 = EnemyBullet(boss.rect.centerx, boss.rect.bottom, speed=6) # Middle one is faster
                b3 = EnemyBullet(boss.rect.right, boss.rect.bottom, speed=5, drift=1)
                self.EnemyBullet.add(b1, b2, b3)
                self.all_sprites.add(b1, b2, b3)
                boss.last_shot = pygame.time.get_ticks() # Reset cooldown
        
        # Collision joueur - powerup
        powerup_hits = pygame.sprite.spritecollide(self.player, self.powerups, True)
        for hit in powerup_hits:
            hit.apply_effect(self.player)
            self.score += 100 # Bonus score for collecting

        # Collision balle ennemie - joueur
        if pygame.sprite.spritecollide(self.player, self.EnemyBullet, True):
            if not self.player.shield_active:
                self.player.take_damage(1)
                if self.player.lives <= 0:
                    self.state = GAME_OVER

        # Check for game over and update high scores
        if self.state == GAME_OVER:
            if self.score > self.high_score:
                self.high_score = self.score
                self.high_wave = self.wave
                self.save_high_scores()

    def draw(self):
        self.screen.blit(self.background,(0,0))

        if self.state == MAIN_MENU:
            self.draw_main_menu()
        elif self.state == HIGH_SCORE_SCREEN:
            self.draw_high_score_screen()
        else: # PLAYING or GAME_OVER
            self.draw_game_screen()

        pygame.display.flip()

    def draw_game_screen(self):
        self.all_sprites.draw(self.screen)
        #HUD
        score_surf = self.font.render("Score: %d" % self.score, True, White)
        wave_surf = self.font.render("Wave: %d" % self.wave, True, White)
        high_score_surf = self.font.render(f"Best Score: {self.high_score}", True, White)
        high_wave_surf = self.font.render(f"Best Wave: {self.high_wave}", True, White)
        self.screen.blit(score_surf, (10, 10))
        self.screen.blit(high_score_surf, (Width - high_score_surf.get_width() - 10, 10))
        self.screen.blit(high_wave_surf, (Width - high_wave_surf.get_width() - 10, 40))

        # Draw Player Health Bar
        PLAYER_BAR_LENGTH = 150
        PLAYER_BAR_HEIGHT = 20
        # Position it in the bottom left
        bar_x = 10
        bar_y = Height - PLAYER_BAR_HEIGHT - 10

        fill_percent = max(0, self.player.lives / self.player.max_lives)
        fill_width = PLAYER_BAR_LENGTH * fill_percent
        
        outline_rect = pygame.Rect(bar_x, bar_y, PLAYER_BAR_LENGTH, PLAYER_BAR_HEIGHT)
        fill_rect = pygame.Rect(bar_x, bar_y, fill_width, PLAYER_BAR_HEIGHT)
        pygame.draw.rect(self.screen, Green, fill_rect)
        pygame.draw.rect(self.screen, White, outline_rect, 2) # Border

        # Draw Player Shield
        if self.player.shield_active:
            pygame.draw.circle(self.screen, Blue, self.player.rect.center, 55, 3)

        # Draw Boss Health Bar
        if self.boss_spawned:
            for boss in self.Boss: # Should only be one boss
                BAR_LENGTH = 400
                BAR_HEIGHT = 30
                fill_percent = max(0, boss.HP / boss.max_HP)
                fill_width = BAR_LENGTH * fill_percent
                
                outline_rect = pygame.Rect((Width - BAR_LENGTH) / 2, 50, BAR_LENGTH, BAR_HEIGHT)
                fill_rect = pygame.Rect((Width - BAR_LENGTH) / 2, 50, fill_width, BAR_HEIGHT)
                
                pygame.draw.rect(self.screen, Red, outline_rect)
                pygame.draw.rect(self.screen, Green, fill_rect)
                pygame.draw.rect(self.screen, White, outline_rect, 3) # Border
        self.screen.blit(wave_surf, (Width/2 - wave_surf.get_width()/2, 10))


        if self.state == GAME_OVER:
            msg = self.font.render("FIN : Appuie sur R pour recommencer", True, White)
            rect = msg.get_rect(centerx=Width//2, centery=Height//2)
            self.screen.blit(msg, rect)
            back_msg = self.font.render("Appuie sur ESC pour retourner au menu", True, White)
            back_rect = back_msg.get_rect(centerx=Width//2, centery=Height//2 + 50)
            self.screen.blit(back_msg, back_rect)

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

        score_text = f"Meilleur Score : {self.high_score}"
        wave_text = f"Meilleure Vague : {self.high_wave}"

        score_surf = self.font.render(score_text, True, White)
        wave_surf = self.font.render(wave_text, True, White)

        self.screen.blit(score_surf, (Width/2 - score_surf.get_width()/2, Height/2 - 20))
        self.screen.blit(wave_surf, (Width/2 - wave_surf.get_width()/2, Height/2 + 40))

        back_surf = self.font.render("Appuyez sur Entrée ou Echap pour retourner", True, Orange)
        self.screen.blit(back_surf, (Width/2 - back_surf.get_width()/2, Height - 100))

if __name__=="__main__":
    Game().run()
