import os
import math
import random
from pygame import gfxdraw

import pygame
import sys
import time

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any

from game_classes import GameMap, Entity, MovingEntity, Direction, EntityType, Weather, TimeOfDay, Game

# Initialize pygame
pygame.init()

# Add these new constants under your existing constants
PLAYER_ACCELERATION = 0.5
PLAYER_FRICTION = 0.85
MOVEMENT_SMOOTHING = True
ENABLE_PIXEL_PERFECT_COLLISION = True

# Game constants
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
TILE_SIZE = 64
PLAYER_SPEED = 5
NPC_SPEED = 2
FONT_SIZE = 20
DIALOG_WIDTH = 700
DIALOG_PADDING = 20
INVENTORY_WIDTH = 300
INVENTORY_HEIGHT = 400
INTERACTION_DISTANCE = 100  # Pixels within which interaction is possible
DAY_LENGTH = 30000  # 30 seconds per in-game day

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (150, 150, 150)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (70, 70, 70)
BEIGE = (245, 245, 220)
BROWN = (139, 69, 19)
DARK_GREEN = (0, 100, 0)
LIGHT_GREEN = (144, 238, 144)
BLUE = (0, 0, 255)
LIGHT_BLUE = (173, 216, 230)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
DARK_YELLOW = (204, 204, 0)
GOLD = (255, 215, 0)
TRANSPARENT = (0, 0, 0, 128)  # Semi-transparent black





class Player(MovingEntity):
    """Player character"""

    def __init__(self, name: str, x: int, y: int):
        super().__init__("player", name, x, y, TILE_SIZE, TILE_SIZE,
                         color=(0, 100, 255), entity_type=EntityType.PLAYER,
                         speed=PLAYER_SPEED)
        self.health = 100
        self.gold = 50
        self.inventory = []
        self.current_location = "village_square"
        self.quests = []
        self.relationships = {}  # NPC relationships
        self.sprite_sheet = None
        self.sprites = {}
        self.animation_frame = 0
        self.last_frame_change = 0
        self.frame_delay = 150  # milliseconds

    def load_sprites(self):
        """Load player sprites"""
        # For this demo, we'll use colored rectangles
        # In a full game, you'd load actual character sprites here
        self.sprites = {
            Direction.DOWN: [pygame.Surface((self.width, self.height)) for _ in range(4)],
            Direction.LEFT: [pygame.Surface((self.width, self.height)) for _ in range(4)],
            Direction.RIGHT: [pygame.Surface((self.width, self.height)) for _ in range(4)],
            Direction.UP: [pygame.Surface((self.width, self.height)) for _ in range(4)]
        }

        # Color the sprites differently based on direction
        for direction, frames in self.sprites.items():
            for i, frame in enumerate(frames):
                # Base color
                frame.fill(self.color)
                # Add some variation based on frame
                variation = pygame.Surface((self.width, self.height))
                alpha = 50 + i * 20
                variation.set_alpha(alpha)
                if direction == Direction.DOWN:
                    variation.fill((0, 0, 100))
                elif direction == Direction.LEFT:
                    variation.fill((0, 100, 0))
                elif direction == Direction.RIGHT:
                    variation.fill((100, 0, 0))
                elif direction == Direction.UP:
                    variation.fill((100, 100, 0))
                frame.blit(variation, (0, 0))

    def get_current_sprite(self):
        """Get the current sprite based on direction and animation frame"""
        if not self.sprites:
            self.load_sprites()

        # Update animation frame if moving
        current_time = pygame.time.get_ticks()
        if self.is_moving:
            if current_time - self.last_frame_change > self.frame_delay:
                self.animation_frame = (self.animation_frame + 1) % 4
                self.last_frame_change = current_time
        else:
            self.animation_frame = 0

        return self.sprites[self.direction][self.animation_frame]

    def add_to_inventory(self, item):
        """Add an item to inventory"""
        self.inventory.append(item)

    def remove_from_inventory(self, item_id):
        """Remove an item from inventory"""
        for i, item in enumerate(self.inventory):
            if item.entity_id == item_id:
                return self.inventory.pop(i)
        return None

    def handle_input(self, keys, game_map):
        """Handle keyboard input for player movement"""
        dx, dy = 0, 0
        self.is_moving = False

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -self.speed
            self.is_moving = True
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = self.speed
            self.is_moving = True

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -self.speed
            self.is_moving = True
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = self.speed
            self.is_moving = True

        if dx != 0 or dy != 0:
            self.move(dx, dy, game_map)


def simulate_nlp_response(npc, environment_state, player_message):
    """
    Placeholder for NLP response simulation
    In a production game, this would call an LLM API
    """
    # This function is a simplified version that would be replaced
    # with an actual call to an LLM API in a production game

    # Construct prompt
    prompt = f"""
You are {npc.name}, a {npc.personality} character.
Your backstory: {npc.backstory}

The time is {environment_state['time_of_day'].name} and the weather is {environment_state['weather'].name}.
You've been asked: "{player_message}"

Your memories:
{npc.get_memory_summary()}

Respond as your character would, keeping your response under 100 characters.
"""

    # In a real implementation, send this prompt to an LLM API
    # response = llm_api.generate_response(prompt)

    # For the demo, use the rule-based response
    response = npc.simulate_npc_response(environment_state, player_message)

    return response


def main():
    """Entry point for the game"""
    try:
        # Display loading screen
        pygame.init()
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Whispers of the Forgotten Vale")

        # Draw loading screen
        screen.fill(BLACK)
        font = pygame.font.SysFont('Arial', 32, bold=True)
        loading_text = font.render("Loading Game World...", True, WHITE)
        loading_rect = loading_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        screen.blit(loading_text, loading_rect)
        pygame.display.flip()

        # Initialize and run game
        game = Game()
        game.run()

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pygame.quit()
        sys.exit()


# Add to the imports at the top
import os
from pygame import gfxdraw

# Add these constants in the constants section
PLAYER_ACCELERATION = 0.5
PLAYER_FRICTION = 0.85
MOVEMENT_SMOOTHING = True
ENABLE_PIXEL_PERFECT_COLLISION = True








# Update the Game._update method to include particle updates
def _update(self):
    """Update game state"""
    # Get keyboard input
    keys = pygame.key.get_pressed()

    # Update player based on input
    self.player.handle_input(keys, self.game_map)

    # Update player effects
    self.player.add_footstep_particle(self.game_state)
    self.player.update_particles()

    # Update all NPCs
    for npc in self.game_map.npcs:
        npc.update(self.game_map, self.game_state, self.player)

    # Update camera to follow player
    self.camera.update(self.player.x, self.player.y,
                       self.game_map.width, self.game_map.height)

    # Update game state (time, weather, etc.)
    self.game_state.update()

    # Update player's current location
    current_room = self.game_map.get_room_at_position(self.player.x, self.player.y)
    if current_room:
        self.player.current_location = current_room.room_id


# Update the Game._render method to include enhanced visual effects
def _render(self):
    """Render the game with enhanced visual effects"""
    # Fill background
    self.screen.fill(BLACK)

    # Render map
    self.game_map.render(self.screen, self.camera.x, self.camera.y)

    # Draw player footstep particles
    self.player.render_particles(self.screen, self.camera.x, self.camera.y)

    # Render items
    for item in self.game_map.items:
        if not item.is_collected:
            item_rect = pygame.Rect(
                item.x - self.camera.x,
                item.y - self.camera.y,
                item.width,
                item.height
            )
            pygame.draw.rect(self.screen, item.color, item_rect)

            # Add shine effect with glow
            shine_size = min(item.width, item.height) // 3
            shine_pos = (
                item.x - self.camera.x + item.width // 4,
                item.y - self.camera.y + item.height // 4
            )

            # Draw glow
            glow_surf = pygame.Surface((shine_size * 4, shine_size * 4), pygame.SRCALPHA)
            for radius in range(shine_size * 2, 0, -2):
                alpha = max(5, 40 - radius * 2)
                pygame.draw.circle(glow_surf, (*item.color[:3], alpha), (shine_size * 2, shine_size * 2), radius)

            self.screen.blit(glow_surf,
                             (shine_pos[0] - shine_size * 2, shine_pos[1] - shine_size * 2),
                             special_flags=pygame.BLEND_ADD)

            # Draw main shine
            pygame.draw.circle(self.screen, WHITE, shine_pos, shine_size)

    # Render player shadow first (appears beneath player)
    self.player.render_shadow(self.screen, self.camera.x, self.camera.y)

    # Render NPCs with shadows
    for npc in self.game_map.npcs:
        # Draw NPC shadow (simple offset version)
        shadow_x = npc.x - self.camera.x + 4
        shadow_y = npc.y - self.camera.y + npc.height - 4
        shadow_width = npc.width - 8
        shadow_height = npc.height // 3

        shadow_rect = pygame.Rect(
            shadow_x,
            shadow_y,
            shadow_width,
            shadow_height
        )

        # Draw semi-transparent shadow
        pygame.draw.ellipse(self.screen, (0, 0, 0, 60), shadow_rect)

        # Draw NPC
        npc_sprite = npc.get_current_sprite()
        self.screen.blit(npc_sprite,
                         (npc.x - self.camera.x, npc.y - self.camera.y))

        # Render NPC name above if close to player
        if self.player.distance_to(npc) < INTERACTION_DISTANCE * 1.5:
            name_font = pygame.font.SysFont('Arial', 14)
            name_surface = name_font.render(npc.name, True, WHITE)
            name_rect = name_surface.get_rect()
            name_rect.midbottom = (npc.x - self.camera.x + npc.width // 2,
                                   npc.y - self.camera.y - 5)

            # Add background for better readability
            bg_rect = name_rect.copy()
            bg_rect.inflate_ip(10, 6)
            bg_surface = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
            bg_surface.fill((0, 0, 0, 150))
            self.screen.blit(bg_surface, bg_rect)
            self.screen.blit(name_surface, name_rect)

    # Render player
    player_sprite = self.player.get_current_sprite()
    self.screen.blit(player_sprite,
                     (self.player.x - self.camera.x,
                      self.player.y - self.camera.y))

    # Optional: Add player lighting effect during dark times
    if self.game_state.time_of_day in [TimeOfDay.EVENING, TimeOfDay.NIGHT]:
        light_radius = self.player.light_radius
        light_surface = pygame.Surface((light_radius * 2, light_radius * 2), pygame.SRCALPHA)

        # Create radial gradient
        for r in range(light_radius, 0, -1):
            alpha = 0 if r > light_radius - 5 else min(180, int(180 * (1 - r / light_radius)))
            color = (255, 220, 150, alpha)  # Warm light color
            pygame.draw.circle(light_surface, color, (light_radius, light_radius), r)

        # Position light centered on player
        light_x = self.player.x - self.camera.x + self.player.width // 2 - light_radius
        light_y = self.player.y - self.camera.y + self.player.height // 2 - light_radius
        self.screen.blit(light_surface, (light_x, light_y), special_flags=pygame.BLEND_ADD)

    # Apply time of day color overlay
    time_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    time_overlay.fill(self.game_state.get_time_color_overlay())
    self.screen.blit(time_overlay, (0, 0))

    # Apply weather effects with more variation
    if self.game_state.weather != Weather.CLEAR:
        self._render_enhanced_weather_effects()
    else:
        self.game_state.get_weather_effect(self.screen)

    # Render HUD
    self.hud.render(self.screen, self.player, self.game_state, self.game_map)

    # Render dialogue if active
    self.dialogue_manager.render(self.screen)

    # Render inventory if visible
    self.inventory_ui.render(self.screen, self.player, self.game_map)

    # Render pause overlay if paused
    if self.paused:
        pause_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pause_overlay.fill((0, 0, 0, 150))
        self.screen.blit(pause_overlay, (0, 0))

        pause_font = pygame.font.SysFont('Arial', 48, bold=True)
        pause_text = pause_font.render("PAUSED", True, WHITE)
        text_rect = pause_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(pause_text, text_rect)

        instructions_font = pygame.font.SysFont('Arial', 20)
        instructions_text = instructions_font.render(
            "Press ESC to resume, Q to quit", True, WHITE
        )
        inst_rect = instructions_text.get_rect(
            center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50)
        )
        self.screen.blit(instructions_text, inst_rect)

    # Update display
    pygame.display.flip()


def _render_enhanced_weather_effects(self):
    """Render enhanced weather effects"""
    width, height = self.screen.get_size()
    weather_surface = pygame.Surface((width, height), pygame.SRCALPHA)

    if self.game_state.weather == Weather.CLOUDY:
        # Add dynamic clouds
        weather_surface.fill((200, 200, 200, 40))
        current_time = pygame.time.get_ticks() // 50  # Slow time factor
        for i in range(5):
            cloud_x = (current_time // (10 + i * 5) + i * width // 5) % (width + 200) - 100
            cloud_y = height // 10 + i * 20
            cloud_width = 100 + i * 30
            cloud_height = 40 + i * 10

            # Draw cloud shape
            for j in range(5):
                offset_x = j * cloud_width // 8
                offset_y = math.sin(j * 0.8) * 5
                size = cloud_height // 2 + j * 5
                pygame.draw.circle(weather_surface, (220, 220, 220, 20),
                                   (int(cloud_x + offset_x), int(cloud_y + offset_y)), size)

    elif self.game_state.weather == Weather.RAINY:
        # Add blue-gray overlay and animated rain drops
        weather_surface.fill((100, 100, 150, 60))
        current_time = pygame.time.get_ticks()
        rain_count = 100

        for i in range(rain_count):
            # Use time to animate rain vertically
            seed = i * 10
            x = (seed * 97 + current_time // 20) % width
            y_offset = (current_time // 10 + seed * 13) % height
            y = (y_offset + seed * 17) % height

            length = random.randint(5, 15)
            thickness = 1 if random.random() < 0.8 else 2

            # Add slight angle to rain
            angle = math.pi / 6  # 30 degrees
            end_x = x - math.sin(angle) * length
            end_y = y + math.cos(angle) * length

            # Vary drop alpha based on distance from camera
            alpha = random.randint(100, 200)
            pygame.draw.line(weather_surface, (200, 200, 255, alpha),
                             (x, y), (end_x, end_y), thickness)

            # Occasionally add splash effect
            if random.random() < 0.02:
                splash_x = random.randint(0, width)
                splash_y = random.randint(0, height)

                for j in range(3):
                    angle = random.random() * math.pi * 2
                    splash_length = random.randint(2, 4)
                    splash_end_x = splash_x + math.cos(angle) * splash_length
                    splash_end_y = splash_y + math.sin(angle) * splash_length
                    pygame.draw.line(weather_surface, (200, 200, 255, 100),
                                     (splash_x, splash_y), (splash_end_x, splash_end_y), 1)

    elif self.game_state.weather == Weather.FOGGY:
        # Add dynamic fog
        base_alpha = 100
        current_time = pygame.time.get_ticks() // 100

        # Create fog layer
        weather_surface.fill((255, 255, 255, base_alpha))

        # Add swirling fog patterns
        for i in range(8):
            fog_x = (current_time // (20 + i * 10) + i * 100) % (width * 2) - width // 2
            fog_y = height // 4 + math.sin(current_time / 1000 + i) * height // 8
            fog_radius = 100 + i * 30

            # Vary fog density
            fog_alpha = 20 + int(15 * math.sin(current_time / 500 + i * 0.5))

            for r in range(fog_radius, 0, -fog_radius // 5):
                pygame.draw.circle(weather_surface, (255, 255, 255, fog_alpha),
                                   (int(fog_x), int(fog_y)), r)

    elif self.game_state.weather == Weather.STORMY:
        # Dark overlay with lightning
        weather_surface.fill((50, 50, 70, 100))

        # Random lightning flash (more dramatic)
        current_time = pygame.time.get_ticks()
        if random.random() < 0.02:  # 2% chance per frame for lightning
            # Determine lightning duration
            self.lightning_start = current_time
            self.lightning_duration = random.randint(50, 150)

        # If lightning is active, draw it
        if hasattr(self, 'lightning_start') and current_time - self.lightning_start < self.lightning_duration:
            # Calculate flash intensity (peaks in the middle)
            progress = (current_time - self.lightning_start) / self.lightning_duration
            intensity = math.sin(progress * math.pi)
            flash_alpha = int(200 * intensity)

            # Create lightning flash
            flash_surface = pygame.Surface((width, height), pygame.SRCALPHA)
            flash_surface.fill((255, 255, 255, flash_alpha))
            weather_surface.blit(flash_surface, (0, 0))

            # Add lightning bolt occasionally
            if random.random() < 0.3 and flash_alpha > 100:
                # Draw jagged lightning bolt
                bolt_start_x = random.randint(0, width)
                bolt_start_y = 0
                bolt_segments = random.randint(4, 8)
                bolt_width = 3

                last_x, last_y = bolt_start_x, bolt_start_y
                for j in range(bolt_segments):
                    next_x = last_x + random.randint(-80, 80)
                    next_y = last_y + height // bolt_segments

                    # Draw main bolt
                    pygame.draw.line(weather_surface, (200, 200, 255, 240),
                                     (last_x, last_y), (next_x, next_y), bolt_width)

                    # Add glow
                    for k in range(3):
                        glow_width = bolt_width + k * 2
                        glow_alpha = 150 - k * 50
                        pygame.draw.line(weather_surface, (200, 200, 255, glow_alpha),
                                         (last_x, last_y), (next_x, next_y), glow_width)

                    # Add occasional fork
                    if random.random() < 0.3:
                        fork_x = next_x + random.randint(-40, 40)
                        fork_y = next_y + random.randint(10, 30)
                        pygame.draw.line(weather_surface, (200, 200, 255, 200),
                                         (next_x, next_y), (fork_x, fork_y), bolt_width - 1)

                    last_x, last_y = next_x, next_y

            # Add distant thunder sound effect here if you have audio support

        # Blend the weather effects onto the screen
        self.screen.blit(weather_surface, (0, 0))


# Import the enhancements
from enhanced_game import (
    enhanced_render,
    EnhancedPlayer,
    fix_assets_path,
    PLAYER_SPEED,
    PLAYER_ACCELERATION,
    PLAYER_FRICTION,
    DIAGONAL_FACTOR
)

# Replace the existing Player class with the EnhancedPlayer
Player = EnhancedPlayer

# Ensure assets directory exists
fix_assets_path()

# Update game constants if needed
PLAYER_SPEED = 7
PLAYER_ACCELERATION = 0.8
PLAYER_FRICTION = 0.9

# Replace GameMap render method
GameMap.render = enhanced_render


if __name__ == "__main__":
    main()