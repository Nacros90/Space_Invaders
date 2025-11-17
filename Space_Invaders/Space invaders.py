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

# --- Répertoire des assets ---
# Cette ligne définit le dossier dans lequel se trouvent toutes les images du jeu.
# On part du dossier où se trouve ce fichier Python (__file__), puis on ajoute "assets".
Assets = Path(__file__).parent / "assets"

class Player(pygame.sprite.Sprite):
    def __init__(self,x,y,image_surface,speed=5):
        super().__init__()
        self.image=image_surface
        self.rect=self.image.get_rect(midbottom=(x,y))
        self.speed=speed
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
        if keys[pygame.K_LEFT]:
            self.rect.x -=self.speed
        if keys[pygame.K_RIGHT]:
            self.rect.x += self.speed
        if keys[pygame.K_UP]:
            self.rect.y -=self.speed
        if keys[pygame.K_DOWN]:
            self.rect.y +=self.speed
        #bornes
        self.rect.left=max(self.rect.left,0)
        self.rect.right=min(self.rect.right,Width)

        # Update power-up timers
        now = pygame.time.get_ticks()
        if self.shield_active and now > self.shield_end_time:
            self.shield_active = False
        
        if self.fire_rate_boost_active and now > self.fire_rate_boost_end_time:
            self.fire_rate_boost_active = False
            self.shoot_cooldown = self.base_shoot_cooldown

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
        self.font=pygame.font.SysFont("comicsans",30)
        self.reset()
        
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
        self.boss_spawned = False  # Ajout du flag boss_spawned

    def start_new_wave(self):
        """Sets up the start of a new wave."""
        self.wave += 1
        self.boss_spawned = False
        self.EnemyBullet.empty() # Clear any remaining bullets
        self.all_sprites.remove(self.EnemyBullet)

        # Spawn enemies based on the wave number
        # Increase enemies per row, but cap it to avoid going off-screen
        enemies_per_row = min(12, 5 + self.wave) 
        for i in range(enemies_per_row):
            start_x = (Width - (enemies_per_row * 100 - 40)) / 2
            x_pos = start_x + i * 100

            # Create different enemies based on position or randomness
            if i % 4 == 1: # Every 4th enemy in the top row is armored
                enemy1 = ArmoredOpponent(x_pos, 100, self.enemy_img)
            else:
                enemy1 = Opponent(x_pos, 100, self.enemy_img)

            enemy2 = ShooterOpponent(x_pos, 160, self.enemy_img) # Bottom row are all shooters
            self.Opponent.add(enemy1, enemy2)
            self.all_sprites.add(enemy1, enemy2)

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

            if self.state==PLAYING and event.type==pygame.KEYDOWN and event.key==pygame.K_SPACE:
                self.player.shoot(self.bullet,self.all_sprites, self.player_bullet_img)
            
            if self.state==GAME_OVER and event.type==pygame.KEYDOWN and event.key==pygame.K_r:
                self.reset()

    def update(self):
        keys=pygame.key.get_pressed()
        if self.state !=PLAYING:
            return
        
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
            self.player.take_damage(1)
            if self.player.lives <= 0 and not self.player.shield_active:
                self.state = GAME_OVER

    def draw(self):
        self.screen.blit(self.background,(0,0))
        self.all_sprites.draw(self.screen)
        #HUD
        score_surf = self.font.render("Score: %d" % self.score, True, White)
        wave_surf = self.font.render("Wave: %d" % self.wave, True, White)
        self.screen.blit(score_surf, (10, 10))

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

        pygame.display.flip()



if __name__=="__main__":
    Game().run()
