# -*- coding: utf-8 -*-
"""
Created on Wed Oct  8 08:19:55 2025

@author: ncrosnie
TD1 : Space invaders
"""

import pygame
import sys

# --- Constantes globales ---
Width=900
Height=900
FPS=60
Player_surf_W=60
Player_surf_H=20
Blue=(80, 115, 210)
White = (255, 255, 255)           # Définition de la couleur blanc en RGB
Black = (0, 0, 0)                 # Définition de la couleur noir en RGB
Green = (80, 220, 100)
Red =(255, 0, 0)
Playing=0
Game_over=1


class Player(pygame.sprite.Sprite):
    def __init__(self,x=450,y=100,speed=5):
        super().__init__()
        self.image=pygame.Surface((Player_surf_W,Player_surf_H))
        self.image.fill(Green)
        self.rect=self.image.get_rect(midbottom=(x,y))
        self.speed=speed
        self.shoot_cooldown=250 #ms
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
        self.rect.top=max(self.rect.top,0)
        self.rect.bottom=min(self.rect.bottom,Height)

    def can_shoot(self):
        return pygame.time.get_ticks()-self.last_shot >=self.shoot_cooldown
    
    def shoot(self,bullet_group,all_sprites_group):
        if self.can_shoot():
            bullet=Bullet(self.rect.centerx,self.rect.top)
            bullet_group.add(bullet)
            all_sprites_group.add(bullet)
            self.last_shot=pygame.time.get_ticks()

class Bullet(pygame.sprite.Sprite):
    def __init__(self,x,y,speed=-8): #défaut négatif -> balle monte
        super().__init__()
        self.image=pygame.Surface((4,20))
        self.image.fill(White)
        self.rect=self.image.get_rect(midbottom=(x,y))
        self.speed=speed

    def update(self,*_):
        self.rect.y +=self.speed
        if self.rect.bottom<0:
            self.kill()

class Enemy(pygame.sprite.Sprite):
    def __init__(self,x,y,):
        super().__init__()
        self.image=pygame.Surface((40,30))
        self.image.fill(Red)
        self.rect=self.image.get_rect(topleft=(x,y))
    


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode(((Width,Height)))
        pygame.display.set_caption("Space Invaders")
        self.clock=pygame.time.Clock()
        self.font=pygame.font.SysFont("comicsans",30)
        self.reset()

    def reset(self):
        self.all_sprites=pygame.sprite.Group()
        self.bullets=pygame.sprite.Group()
        self.ennemies=pygame.sprite.Group()
        
        #joueurs
        self.player=Player(Width/2,Height-30)
        self.all_sprites.add(self.player)
        
        #grille ennemis
        for row in range(3):
            for col in range(10):
                e=Enemy(80+col*70,60+row*40)
                self.ennemies.add(e)
                self.all_sprites.add(e)
        
        self.fleet_direction=1 #1:right ; -1:left
        self.fleet_speed=1.0
        self.drop_amount=15

        self.state=Playing
        self.score=0


    def run(self):
        while True:
            self.clock.tick(FPS)
            self.handle_events()
            self.update()
            self.draw()
        pygame.quit()
        sys.exit()

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if self.state==Playing and e.type==pygame.KEYDOWN and e.key==pygame.K_a:
                self.player.shoot(self.bullets,self.all_sprites)
            if self.state==Game_over and e.type==pygame.KEYDOWN and e.key==pygame.K_r:
                self.reset()


    def update(self):
        keys=pygame.key.get_pressed()
        if self.state != Playing:
            return
        
        self.all_sprites.update(keys) #met à jour tous les sprites du groupe

        #déplacement flotte ennemis
        edge_hit=False
        for e in self.ennemies:
            e.rect.x += self.fleet_direction * self.fleet_speed
            if e.rect.right >= Width-5 or e.rect.left <=5:
                edge_hit=True
        if edge_hit:
            self.fleet_direction *= -1
            for e in self.ennemies:
                e.rect.y += self.drop_amount
        
        #collisions balles-ennemis
        hits=pygame.sprite.groupcollide(self.ennemies,self.bullets,True,True)   #supprime les deux sprites en collision
        self.score += len(hits)*10

        #Défaite:
        for e in self.ennemies:
            if e.rect.bottom >= Height-40:
                self.state=Game_over
            if e.rect.colliderect(self.player.rect):
                self.player.lives -=1
                self.state=Game_over
        
        #Victoire:
        if not self.ennemies:
            self.state=Game_over
        
    def draw(self):
        self.screen.fill(Black)
        self.all_sprites.draw(self.screen)
        
        #HUD
        score_surf=self.font.render(f"Score: {self.score}",True,White)
        lives_surf=self.font.render(f"Lives: {self.player.lives}",True,White)
        self.screen.blit(score_surf,(10,10))
        self.screen.blit(lives_surf,(Width-100,10))
        
        if self.state==Game_over:
            msg=self.font.render("Game Over! Press R to Restart",True,Red)
            rect=msg.get_rect(center=(Width/2,Height/2))
            self.screen.blit(msg,rect)
        
        pygame.display.flip()
        


if __name__=="__main__":
    Game().run()