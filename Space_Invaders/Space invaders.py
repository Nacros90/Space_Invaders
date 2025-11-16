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
Width=1600
Height=900
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
        self.shoot_cooldown=100     #en ms
        self.last_shot=0
        self.lives=3

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
    
    def can_shoot(self):
        return pygame.time.get_ticks()-self.last_shot>=self.shoot_cooldown
    
    def shoot(self,bullets_group,all_sprites_group, bullet_image):
        if self.can_shoot():
            bullet=Bullet(self.rect.centerx,self.rect.top, bullet_image)
            bullets_group.add(bullet)
            all_sprites_group.add(bullet)
            self.last_shot=pygame.time.get_ticks()


class Opponent(pygame.sprite.Sprite):
    def __init__(self,x,y,image_surface):
        super().__init__()
        self.image=image_surface
        self.rect=self.image.get_rect(topleft=(x,y))

'''
class Boss(pygame.sprite.Sprite):
    def __init__(self,x=450,y=750,speed=2.5):
        super().__init__()
        self.image=pygame.Surface((120,40))
        self.image.fill(Orange)
        self.rect=self.image.get_rect(topleft=(x,y))
        self.speed=speed
        self.HP=10  # mettre HP plus bas pour test plus rapide

    def hit(self):
        self.HP -= 1
        if self.HP <= 0:
            self.kill()
'''
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
    def __init__(self, x, y, speed=4, amp=60, freq=1.2, phase=0.0, drift=0.0):
        """
        speed : vitesse verticale (px/frame)
        amp   : amplitude horizontale (px)
        freq  : fréquence en Hz (oscillations par seconde, approx si FPS constant)
        phase : phase initiale (radians)
        drift : dérive horizontale constante (px/frame), 0 = aucune
        """
        super().__init__()
        # sprite simple (remplace par ton image si tu veux)
        self.image = pygame.Surface((4, 12), pygame.SRCALPHA)
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
        # incrémente le temps (approx si tu tournes à FPS constant)
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
        self.all_sprites=pygame.sprite.Group()
        self.bullet = pygame.sprite.Group()         # Groupe dédié aux projectiles (facilite la gestion/collisions).
        self.Opponent = pygame.sprite.Group()         # Groupe des ennemis.
        self.Boss=pygame.sprite.Group()
        self.EnemyBullet=pygame.sprite.Group()
        
        # --- Chargement des images depuis /assets ---
        self.background = self.load_image("Fond.jpg", (Width, Height))
        self.player_img = self.load_image("Player.jpg", (54, 96), Black)
        self.enemy_img = self.load_image("Ennemis.jpg", (96,54))
        self.player_bullet_img = self.load_image("red.jpg", (8, 24))
        
        # Création du joueur
        self.player=Player(Width/2,Height-30,self.player_img)
        self.all_sprites.add(self.player)
        
        # Trois rangées d'ennemis
        for i in range(10):
            e=Opponent(60+i*100, 10,self.enemy_img)            
            self.Opponent.add(e)
            self.all_sprites.add(e)
        
        for i in range(8):
            h=Opponent(140+i*100,70,self.enemy_img)
            self.Opponent.add(h)
            self.all_sprites.add(h)
        
        for i in range(6):
            g=Opponent(220+i*100,130,self.enemy_img)
            self.Opponent.add(g)
            self.all_sprites.add(g)
        
        self.fleet_dir=1 #1 droite ; 0 gauche
        self.fleet_speed = 1
        self.drop_amount = 15
        self.state = PLAYING
        self.score = 0
        #self.boss_spawned = False  # Ajout du flag boss_spawned
    
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
        for e in self.Opponent:
            e.rect.x += self.fleet_dir * self.fleet_speed
            if e.rect.right >= Width-5 or e.rect.left <= 5:
                edge_hit = True
        if edge_hit:
            self.fleet_dir *= -1
            for e in self.Opponent:
                e.rect.y += self.drop_amount

        #for b in self.Boss:
        #    b.rect.x += self.fleet_dir * self.fleet_speed
        #    if b.rect.right >= Width-5 or b.rect.left <= 5:
        #        edge_hit = True
        #if edge_hit:
        #    self.fleet_dir *= -1
        #    for b in self.Boss:
        #        b.rect.y += self.drop_amount
                
        # collisions avec les ennemis
        hits=pygame.sprite.groupcollide(self.Opponent,self.bullet,True,True)
        self.score+=len(hits)*10
        
        #Evenement de fin de partie
        if not self.Opponent:           #Si il n'y à plus d'ennemis
            self.state=GAME_OVER
        
        for e in self.Opponent:
            if e.rect.bottom >= Height-40:      #Si les ennemis atteignent le bas de l'écran
                self.state = GAME_OVER
            if e.rect.colliderect(self.player.rect):    #Si le joueur touche un ennemis
                self.player.lives -= 1
                self.state = GAME_OVER
        
        #Tir aléatoire des ennemis
        if self.Opponent and random.random() < max(0.002,0.05*len(self.Opponent)/30.0):
            shooter=random.choice(self.Opponent.sprites())
            b = EnemyBullet(shooter.rect.centerx, shooter.rect.bottom)
            self.EnemyBullet.add(b)
            self.all_sprites.add(b)
        
        # Collision balle ennemie - joueur
        if pygame.sprite.spritecollide(self.player, self.EnemyBullet, True):
            self.player.lives -= 1
            if self.player.lives <= 0:
                self.state = GAME_OVER

    def draw(self):
        self.screen.blit(self.background,(0,0))
        self.all_sprites.draw(self.screen)
        #HUD
        score_surf = self.font.render("Score: %d" % self.score, True, White)
        lives_surf = self.font.render("Lives: %d" % self.player.lives, True, White)
        self.screen.blit(score_surf, (10, 10))
        self.screen.blit(lives_surf, (Width-120, 10))

        if self.state == GAME_OVER:
            msg = self.font.render("FIN : Appuie sur R pour recommencer", True, White)
            rect = msg.get_rect(centerx=Width//2, centery=Height//2)
            self.screen.blit(msg, rect)

        pygame.display.flip()


if __name__=="__main__":
    Game().run()
