# particle_system.py
import pygame
import math
from pygame import gfxdraw

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def add_particle(self, x, y, color, size, lifetime):
        self.particles.append({'x': x, 'y': y, 'color': color, 'size': size, 'life': lifetime, 'created': pygame.time.get_ticks()})

    def update(self):
        current_time = pygame.time.get_ticks()
        self.particles = [p for p in self.particles if current_time - p['created'] < p['life']]

    def render(self, surface, camera_x, camera_y):
        current_time = pygame.time.get_ticks()
        for p in self.particles:
            life_pct = 1.0 - ((current_time - p['created']) / p['life'])
            color = list(p['color'])
            if len(color) > 3:
                color[3] = int(color[3] * life_pct)
            pos_x, pos_y = p['x'] - camera_x, p['y'] - camera_y
            size = p['size'] * life_pct
            if size > 0.5:
                gfxdraw.filled_circle(surface, int(pos_x), int(pos_y), int(size), tuple(color))