# -*- coding: utf-8 -*-
"""
Created on Wed Oct  8 08:19:55 2025

@author: ncrosnie
TD1 : Space invaders
"""

import pygame
import sys

#- Constantes globales
Width=900
Height=900
FPS=60
Player_surf_W=60
Player_surf_H=20
Blue=(80, 115, 210)
White = (255, 255, 255)           # Définition de la couleur blanc en RGB (non utilisée ici).
Black = (0, 0, 0)                 # Définition de la couleur noir en RGB (pour le fond).
Green = (80, 220, 100)


class Player(pygame.sprite.Sprite):
    def __init__(self,x=450,y=100,speed=5):
        super().__init__()
        self.image=pygame.Surface((Player_surf_W,Player_surf_H))
        self.image.fill(Green)
        self.rect=self.image.get_rect(midbottom=(x,y))
        self.speed=speed

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


class Game:
    def __init__(self):
        pygame.init()
        
        self.screen = pygame.display.set_mode(((Width,Height)))
        pygame.display.set_caption("Affichage de l'écran")
        self.clock=pygame.time.Clock()
        
        #groupes
        self.all_sprites=pygame.sprite.Group()
        
        #joueurs
        self.player=Player(Width/2,Height-30)
        self.all_sprites.add(self.player)
        
        self.running =True
    
    def run(self):
        while self.running:
            self.clock.tick(FPS)
            self.handle_events()
            self.update()
            self.draw()
        pygame.quit()
        sys.exit()

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running =False

    def update(self):
        keys=pygame.key.get_pressed()
        self.all_sprites.update(keys)
        
    def draw(self):
        self.screen.fill(Black)
        self.all_sprites.draw(self.screen)
        pygame.display.flip()
        


if __name__=="__main__":
    Game().run()