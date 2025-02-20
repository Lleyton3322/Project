import os
import pygame
import random
import math
from pygame import gfxdraw

from game_classes import GameMap, MovingEntity, Weather, Direction, EntityType, Game

# Import necessary classes from main2.py
from enum import Enum

# Reproduce necessary constants
TILE_SIZE = 64
BLACK = (0, 0, 0)
BROWN = (139, 69, 19)
DARK_GRAY = (70, 70, 70)
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768

# Create an assets directory if it doesn't exist
if not os.path.exists('assets'):
    os.makedirs('assets')


# Enhance the GameMap class to include better rendering
def enhanced_render(self, surface, camera_x, camera_y):
    """Render the entire map with enhanced visuals"""
    # Draw rooms with better visuals
    for room in self.rooms:
        room_rect = pygame.Rect(
            room.x - camera_x,
            room.y - camera_y,
            room.width,
            room.height
        )

        # Draw main floor
        pygame.draw.rect(surface, room.floor_color, room_rect)

        # Add floor pattern/texture
        if room.room_id == "village_square":
            # Draw cobblestone pattern
            stone_size = 16
            for x in range(room.x, room.x + room.width, stone_size):
                for y in range(room.y, room.y + room.height, stone_size):
                    if (x // stone_size + y // stone_size) % 2 == 0:
                        rect = pygame.Rect(
                            x - camera_x,
                            y - camera_y,
                            stone_size,
                            stone_size
                        )
                        pygame.draw.rect(surface, (180, 180, 180), rect)
                        pygame.draw.rect(surface, (100, 100, 100), rect, 1)

            # Draw fountain splash particles
            current_time = pygame.time.get_ticks()
            fountain_x = 550 - camera_x + 50
            fountain_y = 500 - camera_y + 50

            # Draw water base
            water_rect = pygame.Rect(fountain_x - 30, fountain_y - 20, 60, 40)
            pygame.draw.ellipse(surface, (100, 150, 255), water_rect)

            # Draw fountain particles
            for i in range(8):
                particle_life = (current_time // 100 + i * 50) % 1000
                if particle_life < 500:  # Only show particles in first half of animation
                    height_factor = 1 - (particle_life / 500)  # Start high, fall down
                    width_factor = particle_life / 500  # Spread out as they fall

                    px = fountain_x + math.sin(i * math.pi / 4) * 15 * width_factor
                    py = fountain_y - 20 * height_factor

                    # Particle size decreases as it falls
                    size = max(1, int(4 * height_factor))
                    alpha = int(200 * height_factor)

                    # Draw water particle
                    if size > 0:
                        gfxdraw.filled_circle(surface, int(px), int(py), size, (150, 200, 255, alpha))

        elif room.room_id == "tavern":
            # Draw wooden floor pattern
            plank_width = 20
            for y in range(room.y, room.y + room.height, plank_width):
                rect = pygame.Rect(
                    room.x - camera_x,
                    y - camera_y,
                    room.width,
                    plank_width
                )
                # Alternate plank colors
                color = (110, 60, 20) if (y // plank_width) % 2 == 0 else (130, 70, 20)
                pygame.draw.rect(surface, color, rect)
                pygame.draw.rect(surface, (80, 40, 10), rect, 1)

            # Draw some ambient particles (dust motes in tavern light)
            current_time = pygame.time.get_ticks()
            light_x = room.x + room.width // 2 - camera_x
            light_y = room.y + 50 - camera_y

            # Draw light beam
            beam_surface = pygame.Surface((100, 150), pygame.SRCALPHA)
            for i in range(100):
                alpha = max(5, 50 - i // 2)
                pygame.draw.line(beam_surface, (255, 220, 150, alpha),
                                 (50, 0), (50 - i // 2, i), 2)
                pygame.draw.line(beam_surface, (255, 220, 150, alpha),
                                 (50, 0), (50 + i // 2, i), 2)
            surface.blit(beam_surface, (light_x - 50, light_y))

            # Dust particles
            for i in range(10):
                particle_x = light_x - 40 + math.sin((current_time + i * 100) / 500) * 30 + i * 8
                particle_y = light_y + 20 + (current_time % 1000) / 1000 * 100 + i * 10
                alpha = 100 - (particle_y - light_y) // 2
                if 0 <= particle_y - light_y <= 150:
                    pygame.draw.circle(surface, (255, 220, 150, alpha),
                                       (int(particle_x), int(particle_y)), 1)

        elif room.room_id in ["deep_forest", "forest_edge", "hidden_glade"]:
            # Draw organic ground pattern for forest areas
            for i in range(50):  # Random grass/foliage patches
                patch_x = random.randint(room.x, room.x + room.width - 10)
                patch_y = random.randint(room.y, room.y + room.height - 10)
                patch_size = random.randint(5, 15)

                if (patch_x - camera_x >= 0 and patch_x - camera_x <= SCREEN_WIDTH and
                        patch_y - camera_y >= 0 and patch_y - camera_y <= SCREEN_HEIGHT):
                    # Random green shade
                    green_value = random.randint(100, 200)
                    color = (0, green_value, 0, 150)

                    # Draw grass patch
                    gfxdraw.filled_circle(surface,
                                          patch_x - camera_x,
                                          patch_y - camera_y,
                                          patch_size, color)

            # Add floating particles for forest (pollen/fireflies)
            if room.room_id == "hidden_glade":
                current_time = pygame.time.get_ticks()
                for i in range(20):
                    # Circular motion
                    angle = (current_time / 2000 + i / 3) * math.pi * 2
                    radius = 30 + 10 * math.sin(current_time / 1000 + i)

                    particle_x = room.x + room.width // 2 - camera_x + math.cos(angle) * radius
                    particle_y = room.y + room.height // 2 - camera_y + math.sin(angle) * radius

                    # Pulsing size and alpha
                    pulse = (math.sin(current_time / 200 + i) + 1) / 2
                    size = 1 + pulse
                    alpha = int(100 + 100 * pulse)

                    # Draw firefly/pollen
                    gfxdraw.filled_circle(surface,
                                          int(particle_x), int(particle_y),
                                          int(size), (220, 220, 100, alpha))

        # Draw border with depth effect
        for thickness in range(3, 0, -1):
            border_color = (
                max(0, DARK_GRAY[0] - thickness * 20),
                max(0, DARK_GRAY[1] - thickness * 20),
                max(0, DARK_GRAY[2] - thickness * 20)
            )
            pygame.draw.rect(surface, border_color, room_rect, thickness)

    # Draw paths between rooms
    for room in self.rooms:
        for direction, connected_room_id in room.exits.items():
            connected_room = self.get_room_by_id(connected_room_id)
            if connected_room:
                # Calculate start and end points for path
                if direction == "north":
                    start_x = room.x + room.width // 2
                    start_y = room.y
                    end_x = connected_room.x + connected_room.width // 2
                    end_y = connected_room.y + connected_room.height
                elif direction == "south":
                    start_x = room.x + room.width // 2
                    start_y = room.y + room.height
                    end_x = connected_room.x + connected_room.width // 2
                    end_y = connected_room.y
                elif direction == "east":
                    start_x = room.x + room.width
                    start_y = room.y + room.height // 2
                    end_x = connected_room.x
                    end_y = connected_room.y + connected_room.height // 2
                elif direction == "west":
                    start_x = room.x
                    start_y = room.y + room.height // 2
                    end_x = connected_room.x + connected_room.width
                    end_y = connected_room.y + connected_room.height // 2

                # Draw path with shadow effect
                path_width = 20
                path_points = []

                # Create smooth path
                if direction in ["north", "south"]:
                    mid_y = (start_y + end_y) // 2
                    path_points = [
                        (start_x, start_y),
                        (start_x, mid_y),
                        (end_x, mid_y),
                        (end_x, end_y)
                    ]
                else:  # east or west
                    mid_x = (start_x + end_x) // 2
                    path_points = [
                        (start_x, start_y),
                        (mid_x, start_y),
                        (mid_x, end_y),
                        (end_x, end_y)
                    ]

                # Adjust points for camera
                camera_adjusted_points = [(x - camera_x, y - camera_y) for x, y in path_points]

                # Draw path shadow
                pygame.draw.lines(surface, (50, 50, 50), False,
                                  camera_adjusted_points, path_width + 4)

                # Draw main path
                path_color = (180, 160, 140)  # Path/road color
                pygame.draw.lines(surface, path_color, False,
                                  camera_adjusted_points, path_width)

                # Add path details (stones/planks)
                path_length = math.sqrt((end_x - start_x) ** 2 + (end_y - start_y) ** 2)
                num_details = int(path_length / 30)

                for i in range(num_details):
                    # Position along path
                    t = i / max(1, num_details - 1)
                    if len(path_points) == 4:  # Ensure we have all points for bezier
                        # Calculate position using cubic Bezier curve
                        point_x = (1 - t) ** 3 * path_points[0][0] + 3 * (1 - t) ** 2 * t * path_points[1][0] + \
                                  3 * (1 - t) * t ** 2 * path_points[2][0] + t ** 3 * path_points[3][0]
                        point_y = (1 - t) ** 3 * path_points[0][1] + 3 * (1 - t) ** 2 * t * path_points[1][1] + \
                                  3 * (1 - t) * t ** 2 * path_points[2][1] + t ** 3 * path_points[3][1]

                        # Draw path detail (stone/plank)
                        detail_rect = pygame.Rect(
                            point_x - camera_x - 4, point_y - camera_y - 2,
                            8, 4
                        )
                        # Alternate colors
                        detail_color = (150, 140, 130) if i % 2 == 0 else (170, 160, 150)
                        pygame.draw.rect(surface, detail_color, detail_rect)

    # Draw obstacles with enhanced visuals
    for obstacle in self.obstacles:
        obstacle_rect = pygame.Rect(
            obstacle.x - camera_x,
            obstacle.y - camera_y,
            obstacle.width,
            obstacle.height
        )

        # Enhanced visuals based on obstacle type
        if "tree" in obstacle.entity_id:
            # Draw tree trunk
            trunk_width = obstacle.width // 2
            trunk_height = obstacle.height // 3
            trunk_rect = pygame.Rect(
                obstacle.x + (obstacle.width - trunk_width) // 2 - camera_x,
                obstacle.y + obstacle.height - trunk_height - camera_y,
                trunk_width,
                trunk_height
            )
            pygame.draw.rect(surface, BROWN, trunk_rect)

            # Draw tree foliage as a circle
            foliage_radius = obstacle.width // 2 + 4
            foliage_x = obstacle.x + obstacle.width // 2 - camera_x
            foliage_y = obstacle.y + obstacle.height // 2 - trunk_height // 2 - camera_y

            # Draw shadow under tree
            shadow_y = obstacle.y + obstacle.height - camera_y - 4
            shadow_width = obstacle.width + 10
            shadow_height = 10
            shadow_rect = pygame.Rect(
                obstacle.x - 5 - camera_x,
                shadow_y,
                shadow_width,
                shadow_height
            )
            pygame.draw.ellipse(surface, (0, 0, 0, 80), shadow_rect)

            # Draw tree with shading
            if "deep" in obstacle.entity_id:  # Darker trees for deep forest
                pygame.draw.circle(surface, (0, 50, 0), (foliage_x, foliage_y), foliage_radius)
                # Add highlights
                highlight_radius = foliage_radius - 4
                pygame.draw.circle(surface, (0, 70, 0),
                                   (foliage_x - 2, foliage_y - 2), highlight_radius)
            else:
                pygame.draw.circle(surface, (20, 100, 20), (foliage_x, foliage_y), foliage_radius)
                # Add highlights
                highlight_radius = foliage_radius - 4
                pygame.draw.circle(surface, (40, 120, 40),
                                   (foliage_x - 2, foliage_y - 2), highlight_radius)

        elif "fountain" in obstacle.entity_id:
            # Already enhanced in the room rendering
            pass

        elif "forge" in obstacle.entity_id:
            # Draw forge with embers/glow effect
            pygame.draw.rect(surface, obstacle.color, obstacle_rect)

            # Add ember particles and glow
            current_time = pygame.time.get_ticks()
            center_x = obstacle.x + obstacle.width // 2 - camera_x
            center_y = obstacle.y + obstacle.height // 2 - camera_y

            # Draw base glow
            glow_radius = 30 + math.sin(current_time / 200) * 5
            for r in range(int(glow_radius), 0, -1):
                alpha = max(5, 50 - r)
                pygame.draw.circle(surface, (255, 100, 20, alpha),
                                   (center_x, center_y), r)

            # Draw embers
            for i in range(8):
                # Calculate ember position with "rising" effect
                ember_life = (current_time // 50 + i * 100) % 1000
                if ember_life < 800:  # Only show embers for part of animation
                    rise_factor = ember_life / 800  # 0 to 1 over lifetime
                    spread_factor = rise_factor * 0.5  # Spread out a bit as they rise

                    ember_x = center_x + math.sin(i * math.pi / 4 + current_time / 500) * 10 * spread_factor
                    ember_y = center_y - 15 * rise_factor

                    # Ember size and alpha decrease as it rises
                    size = max(1, int(3 * (1 - rise_factor)))
                    alpha = int(200 * (1 - rise_factor))

                    # Draw ember
                    if size > 0:
                        ember_color = (255, 150 + int(100 * rise_factor), 0, alpha)
                        gfxdraw.filled_circle(surface, int(ember_x), int(ember_y), size, ember_color)

        else:
            # Draw standard obstacle with 3D effect
            pygame.draw.rect(surface, obstacle.color, obstacle_rect)

            # Add simple highlight/shadow for 3D effect
            highlight_rect = pygame.Rect(
                obstacle_rect.x, obstacle_rect.y,
                obstacle_rect.width, obstacle_rect.height // 4
            )
            shadow_rect = pygame.Rect(
                obstacle_rect.x, obstacle_rect.y + 3 * obstacle_rect.height // 4,
                obstacle_rect.width, obstacle_rect.height // 4
            )

            # Lighten top
            highlight = pygame.Surface((highlight_rect.width, highlight_rect.height), pygame.SRCALPHA)
            highlight.fill((255, 255, 255, 50))
            surface.blit(highlight, highlight_rect)

            # Darken bottom
            shadow = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
            shadow.fill((0, 0, 0, 70))
            surface.blit(shadow, shadow_rect)


# Replace GameMap.render with the enhanced version
GameMap.render = enhanced_render


# Fix the path for assets
def fix_assets_path():
    """Make sure the assets path exists"""
    if not os.path.exists('assets'):
        os.makedirs('assets')
        print("Created assets directory")


# Call the function to ensure assets directory exists
fix_assets_path()

# Adjust these constants for better player movement
PLAYER_SPEED = 7  # Faster base speed
PLAYER_ACCELERATION = 0.8  # Stronger acceleration
PLAYER_FRICTION = 0.9  # Less friction for smoother movement
DIAGONAL_FACTOR = 0.7071  # sqrt(2)/2, prevents faster diagonal movement


class EnhancedPlayer(MovingEntity):
    """Enhanced player character with better physics and visuals"""

    def __init__(self, name: str, x: int, y: int):
        super().__init__("player", name, x, y, TILE_SIZE - 8, TILE_SIZE - 8,
                         color=(0, 100, 255), entity_type=EntityType.PLAYER,
                         speed=PLAYER_SPEED)
        self.health = 100
        self.gold = 50
        self.inventory = []
        self.current_location = "village_square"
        self.quests = []
        self.relationships = {}  # NPC relationships

        # Physics properties for smooth movement
        self.vel_x = 0
        self.vel_y = 0
        self.acceleration = PLAYER_ACCELERATION
        self.friction = PLAYER_FRICTION
        self.diagonal_factor = DIAGONAL_FACTOR

        # Animation properties
        self.sprite_sheet = None
        self.sprites = {}
        self.animation_frame = 0
        self.last_frame_change = 0
        self.frame_delay = 80  # milliseconds - faster animation
        self.load_sprites()

        # Visual effects
        self.light_radius = 150
        self.shadow_offset = 4
        self.footstep_particles = []
        self.particle_timer = 0
        self.particle_delay = 150  # ms between particle emissions
        self.trail_effect = []  # Movement trail effect

        # Motion blur effect
        self.previous_positions = []  # Store previous positions for trail effect
        self.max_trail_length = 4
        self.trail_opacity = 40  # Alpha value for trail images

        # Character customization
        self.base_color = (30, 100, 200)  # Brighter blue
        self.highlight_color = (100, 180, 255)  # Light blue highlight
        self.has_hat = True
        self.has_cape = False

    def load_sprites(self):
        """Load player sprites with better visuals"""
        self.sprites = {
            Direction.DOWN: [pygame.Surface((self.width, self.height), pygame.SRCALPHA) for _ in range(4)],
            Direction.LEFT: [pygame.Surface((self.width, self.height), pygame.SRCALPHA) for _ in range(4)],
            Direction.RIGHT: [pygame.Surface((self.width, self.height), pygame.SRCALPHA) for _ in range(4)],
            Direction.UP: [pygame.Surface((self.width, self.height), pygame.SRCALPHA) for _ in range(4)]
        }

        # Generate better looking sprites
        for direction, frames in self.sprites.items():
            for i, frame in enumerate(frames):
                # Animation offset for bouncing effect
                bounce = math.sin(i * math.pi / 2) * 2  # -2 to 2 pixels

                # Base character body
                if direction == Direction.LEFT:
                    # Facing left - draw asymmetrical shape
                    pygame.draw.rect(frame, self.base_color,
                                     (8, 4 + bounce, self.width - 16, self.height - 8))
                    # Add head
                    pygame.draw.circle(frame, self.base_color,
                                       (16, 12 + bounce), 10)
                    # Add face details
                    pygame.draw.circle(frame, (0, 0, 0), (12, 10 + bounce), 2)  # Eye
                    pygame.draw.arc(frame, (0, 0, 0), (8, 12 + bounce, 8, 8),
                                    math.pi * 1.5, math.pi * 2.5, 1)  # Mouth

                elif direction == Direction.RIGHT:
                    # Facing right
                    pygame.draw.rect(frame, self.base_color,
                                     (8, 4 + bounce, self.width - 16, self.height - 8))
                    # Add head
                    pygame.draw.circle(frame, self.base_color,
                                       (self.width - 16, 12 + bounce), 10)
                    # Add face details
                    pygame.draw.circle(frame, (0, 0, 0),
                                       (self.width - 12, 10 + bounce), 2)  # Eye
                    pygame.draw.arc(frame, (0, 0, 0),
                                    (self.width - 16, 12 + bounce, 8, 8),
                                    math.pi * 0.5, math.pi * 1.5, 1)  # Mouth

                elif direction == Direction.UP:
                    # Facing up - show back of character
                    pygame.draw.rect(frame, self.base_color,
                                     (8, 4 + bounce, self.width - 16, self.height - 8))
                    # Add head (from behind)
                    pygame.draw.circle(frame, self.base_color,
                                       (self.width // 2, 12 + bounce), 10)

                else:  # Direction.DOWN
                    # Facing down - show front of character
                    pygame.draw.rect(frame, self.base_color,
                                     (8, 4 + bounce, self.width - 16, self.height - 8))
                    # Add head
                    pygame.draw.circle(frame, self.base_color,
                                       (self.width // 2, 12 + bounce), 10)
                    # Add face
                    eye_spacing = 8
                    pygame.draw.circle(frame, (0, 0, 0),
                                       (self.width // 2 - eye_spacing // 2, 10 + bounce), 2)  # Left eye
                    pygame.draw.circle(frame, (0, 0, 0),
                                       (self.width // 2 + eye_spacing // 2, 10 + bounce), 2)  # Right eye
                    # Smile
                    pygame.draw.arc(frame, (0, 0, 0),
                                    (self.width // 2 - 6, 12 + bounce, 12, 8),
                                    0, math.pi, 1)

                # Add hat if enabled
                if self.has_hat:
                    if direction == Direction.LEFT:
                        pygame.draw.rect(frame, (70, 40, 20),
                                         (8, 2 + bounce, 16, 4))  # Hat brim
                        pygame.draw.rect(frame, (100, 60, 30),
                                         (12, -4 + bounce, 8, 6))  # Hat top
                    elif direction == Direction.RIGHT:
                        pygame.draw.rect(frame, (70, 40, 20),
                                         (self.width - 24, 2 + bounce, 16, 4))  # Hat brim
                        pygame.draw.rect(frame, (100, 60, 30),
                                         (self.width - 20, -4 + bounce, 8, 6))  # Hat top
                    elif direction == Direction.UP:
                        pygame.draw.rect(frame, (70, 40, 20),
                                         (self.width // 2 - 8, 2 + bounce, 16, 4))  # Hat brim
                        pygame.draw.rect(frame, (100, 60, 30),
                                         (self.width // 2 - 4, -4 + bounce, 8, 6))  # Hat top
                    else:  # Direction.DOWN
                        pygame.draw.rect(frame, (70, 40, 20),
                                         (self.width // 2 - 8, 2 + bounce, 16, 4))  # Hat brim
                        pygame.draw.rect(frame, (100, 60, 30),
                                         (self.width // 2 - 4, -4 + bounce, 8, 6))  # Hat top

                # Add cape if enabled
                if self.has_cape:
                    # Cape animation based on frame
                    cape_wave = math.sin(i * math.pi / 2 + math.pi / 4) * 3
                    if direction == Direction.LEFT:
                        # Cape points right when facing left
                        pygame.draw.polygon(frame, (180, 0, 0), [
                            (self.width - 8, 15 + bounce),  # Shoulder
                            (self.width + cape_wave, 15 + bounce),  # Cape out
                            (self.width - 4, self.height - 10 + bounce),  # Cape bottom
                            (self.width - 12, self.height - 15 + bounce),  # Body
                        ])
                    elif direction == Direction.RIGHT:
                        # Cape points left when facing right
                        pygame.draw.polygon(frame, (180, 0, 0), [
                            (8, 15 + bounce),  # Shoulder
                            (-cape_wave, 15 + bounce),  # Cape out
                            (4, self.height - 10 + bounce),  # Cape bottom
                            (12, self.height - 15 + bounce),  # Body
                        ])
                    elif direction == Direction.UP:
                        # Cape visible from behind
                        pygame.draw.polygon(frame, (180, 0, 0), [
                            (self.width // 2 - 12, 15 + bounce),  # Left shoulder
                            (self.width // 2 + 12, 15 + bounce),  # Right shoulder
                            (self.width // 2 + 16 + cape_wave, self.height - 10 + bounce),  # Right bottom
                            (self.width // 2 - 16 - cape_wave, self.height - 10 + bounce),  # Left bottom
                        ])
                    else:  # Direction.DOWN
                        # Cape mostly hidden from front
                        pygame.draw.rect(frame, (180, 0, 0),
                                         (4, 15 + bounce, 8, self.height - 25))  # Left cape edge
                        pygame.draw.rect(frame, (180, 0, 0),
                                         (self.width - 12, 15 + bounce, 8, self.height - 25))  # Right cape edge

                # Add limbs based on animation frame
                if direction in [Direction.LEFT, Direction.RIGHT]:
                    # Arms - position depends on frame for walking animation
                    arm_back_y = 20 + bounce + (i * 4 % 8)  # Swings back arm
                    arm_front_y = 20 + bounce - (i * 4 % 8)  # Swings front arm

                    if direction == Direction.LEFT:
                        # Left-facing arms
                        pygame.draw.line(frame, self.base_color,
                                         (16, 20 + bounce), (8, arm_back_y), 3)  # Back arm
                        pygame.draw.line(frame, self.base_color,
                                         (16, 20 + bounce), (24, arm_front_y), 3)  # Front arm
                    else:
                        # Right-facing arms
                        pygame.draw.line(frame, self.base_color,
                                         (self.width - 16, 20 + bounce),
                                         (self.width - 8, arm_front_y), 3)  # Front arm
                        pygame.draw.line(frame, self.base_color,
                                         (self.width - 16, 20 + bounce),
                                         (self.width - 24, arm_back_y), 3)  # Back arm

                # Legs - position depends on frame for walking animation
                leg_left_offset = math.sin(i * math.pi / 2) * 6
                leg_right_offset = -math.sin(i * math.pi / 2) * 6

                if direction == Direction.LEFT or direction == Direction.RIGHT:
                    # Side view legs
                    leg_y_start = self.height - 10 + bounce
                    leg_y_end = self.height - 4 + bounce

                    # Body center x-coordinate depends on direction
                    body_x = 16 if direction == Direction.LEFT else self.width - 16

                    pygame.draw.line(frame, self.base_color,
                                     (body_x, leg_y_start),
                                     (body_x + leg_left_offset, leg_y_end), 4)  # Left leg
                    pygame.draw.line(frame, self.base_color,
                                     (body_x, leg_y_start),
                                     (body_x + leg_right_offset, leg_y_end), 4)  # Right leg

                else:  # UP or DOWN
                    # Front/back view legs
                    leg_spacing = 6
                    leg_y_start = self.height - 15 + bounce
                    leg_y_end = self.height - 4 + bounce

                    pygame.draw.line(frame, self.base_color,
                                     (self.width // 2 - leg_spacing, leg_y_start),
                                     (self.width // 2 - leg_spacing + leg_left_offset, leg_y_end), 4)  # Left leg
                    pygame.draw.line(frame, self.base_color,
                                     (self.width // 2 + leg_spacing, leg_y_start),
                                     (self.width // 2 + leg_spacing + leg_right_offset, leg_y_end), 4)  # Right leg

                # Add highlights/shading for depth
                highlight = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                # Left or top highlight
                if direction == Direction.LEFT:
                    highlight_rect = pygame.Rect(8, 4 + bounce, 8, self.height - 8)
                elif direction == Direction.RIGHT:
                    highlight_rect = pygame.Rect(self.width - 16, 4 + bounce, 8, self.height - 8)
                elif direction == Direction.UP:
                    highlight_rect = pygame.Rect(8, 4 + bounce, self.width - 16, 8)
                else:  # DOWN
                    highlight_rect = pygame.Rect(8, 4 + bounce, self.width - 16, 8)

                # Apply highlight
                pygame.draw.rect(highlight, (255, 255, 255, 60), highlight_rect)
                frame.blit(highlight, (0, 0))

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

                # Store position for trail effect when moving
                if len(self.previous_positions) >= self.max_trail_length:
                    self.previous_positions.pop(0)
                self.previous_positions.append((self.x, self.y, self.direction, self.animation_frame))
        else:
            # Use standing frame when not moving
            self.animation_frame = 0
            # Clear trail when stopped
            self.previous_positions = []

        return self.sprites[self.direction][self.animation_frame]

    def render_trail(self, surface, camera_x, camera_y):
        """Render motion trail/blur effect"""
        if not self.previous_positions:
            return

        # Render previous positions with decreasing opacity
        for i, (x, y, direction, frame) in enumerate(self.previous_positions):
            # Calculate opacity based on position in trail
            opacity = int(self.trail_opacity * (i + 1) / len(self.previous_positions))

            # Get sprite for this trail position
            trail_sprite = self.sprites[direction][frame].copy()

            # Apply opacity
            alpha_surface = pygame.Surface(trail_sprite.get_size(), pygame.SRCALPHA)
            alpha_surface.fill((255, 255, 255, opacity))
            trail_sprite.blit(alpha_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

            # Draw trail sprite
            surface.blit(trail_sprite, (x - camera_x, y - camera_y))

    def add_footstep_particle(self, game_state):
        """Add a footstep particle effect"""
        if not self.is_moving:
            return

        current_time = pygame.time.get_ticks()
        if current_time - self.particle_timer < self.particle_delay:
            return

        self.particle_timer = current_time

        # Add particle based on current foot position
        foot_offset = 5
        if self.direction in [Direction.LEFT, Direction.RIGHT]:
            if self.animation_frame in [1, 3]:  # Left foot
                offset_x, offset_y = -foot_offset, foot_offset
            else:  # Right foot
                offset_x, offset_y = foot_offset, foot_offset
        else:  # Up/down
            if self.animation_frame in [1, 3]:  # Left foot
                offset_x, offset_y = -foot_offset, 0
            else:  # Right foot
                offset_x, offset_y = foot_offset, 0

        # Adjust particle color based on location and weather
        if game_state.weather == Weather.RAINY:
            color = (100, 100, 150, 200)  # Muddy splash
            size = random.randint(3, 6)
            lifetime = random.randint(300, 600)
        else:
            color = (200, 200, 180, 150)  # Dust
            size = random.randint(2, 4)
            lifetime = random.randint(200, 400)

        particle = {
            'x': self.x + self.width // 2 + offset_x,
            'y': self.y + self.height - 2,
            'size': size,
            'color': color,
            'life': lifetime,
            'created': current_time
        }

        self.footstep_particles.append(particle)

    def update_particles(self):
        """Update and expire particles"""
        current_time = pygame.time.get_ticks()
        self.footstep_particles = [p for p in self.footstep_particles
                                   if current_time - p['created'] < p['life']]

    def render_particles(self, surface, camera_x, camera_y):
        """Render footstep particles"""
        for particle in self.footstep_particles:
            # Calculate remaining life percentage
            current_time = pygame.time.get_ticks()
            life_pct = 1.0 - ((current_time - particle['created']) / particle['life'])

            # Adjust alpha based on remaining life
            color = list(particle['color'])
            if len(color) > 3:
                color[3] = int(color[3] * life_pct)

            # Draw particle
            pos_x = particle['x'] - camera_x
            pos_y = particle['y'] - camera_y
            size = particle['size'] * life_pct

            if size > 0.5:  # Only draw if big enough
                if len(color) > 3:
                    # Use gfxdraw for anti-aliased circle with alpha
                    gfxdraw.filled_circle(surface,
                                          int(pos_x), int(pos_y),
                                          int(size), tuple(color))
                else:
                    # Fallback to regular circle
                    pygame.draw.circle(surface, tuple(color),
                                       (int(pos_x), int(pos_y)), int(size))

    def render_shadow(self, surface, camera_x, camera_y):
        """Render a shadow beneath the player"""
        shadow_x = self.x - camera_x + self.shadow_offset
        shadow_y = self.y - camera_y + self.height - 4

        # Create elongated ellipse shadow
        shadow_width = self.width - 8
        shadow_height = self.height // 3

        shadow_rect = pygame.Rect(
            shadow_x - shadow_width // 2 + self.width // 2,
            shadow_y,
            shadow_width,
            shadow_height
        )

        # Draw semi-transparent shadow
        shadow_surface = pygame.Surface((shadow_width, shadow_height), pygame.SRCALPHA)
        shadow_surface.fill((0, 0, 0, 0))
        gfxdraw.filled_ellipse(shadow_surface,
                               shadow_width // 2, shadow_height // 2,
                               shadow_width // 2, shadow_height // 2,
                               (0, 0, 0, 80))

        surface.blit(shadow_surface, shadow_rect)

    def handle_input(self, keys, game_map):
        """Handle keyboard input with improved physics-based movement"""
        # Reset acceleration
        accel_x, accel_y = 0, 0
        self.is_moving = False

        # Determine acceleration based on input
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            accel_x = -self.acceleration
            self.direction = Direction.LEFT
            self.is_moving = True
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            accel_x = self.acceleration
            self.direction = Direction.RIGHT
            self.is_moving = True

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            accel_y = -self.acceleration
            self.direction = Direction.UP
            self.is_moving = True
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            accel_y = self.acceleration
            self.direction = Direction.DOWN
            self.is_moving = True

        # Fix diagonal movement speed
        if accel_x != 0 and accel_y != 0:
            accel_x *= self.diagonal_factor
            accel_y *= self.diagonal_factor

        # Apply acceleration
        self.vel_x += accel_x
        self.vel_y += accel_y

        # Apply friction
        self.vel_x *= self.friction
        self.vel_y *= self.friction

        # Clamp velocity to maximum speed
        vel_magnitude = math.sqrt(self.vel_x ** 2 + self.vel_y ** 2)
        if vel_magnitude > self.speed:
            vel_scale = self.speed / vel_magnitude
            self.vel_x *= vel_scale
            self.vel_y *= vel_scale

        # Move based on velocity (if significant)
        if abs(self.vel_x) > 0.1 or abs(self.vel_y) > 0.1:
            self.move(int(self.vel_x), int(self.vel_y), game_map)

            # Still moving even if keys released
            if self.vel_x != 0 or self.vel_y != 0:
                self.is_moving = True

                # Update direction based on velocity if no keys pressed
                if accel_x == 0 and accel_y == 0:
                    if abs(self.vel_x) > abs(self.vel_y):
                        self.direction = Direction.RIGHT if self.vel_x > 0 else Direction.LEFT
                    else:
                        self.direction = Direction.DOWN if self.vel_y > 0 else Direction.UP
        else:
            # Make sure to reset moving flag if velocity is negligible
            self.is_moving = False

    def add_to_inventory(self, item):
        """Add an item to inventory"""
        self.inventory.append(item)

    def remove_from_inventory(self, item_id):
        """Remove an item from inventory"""
        for i, item in enumerate(self.inventory):
            if item.entity_id == item_id:
                return self.inventory.pop(i)
        return None


# Define necessary constants
BLACK = (0, 0, 0)
DARK_GRAY = (70, 70, 70)
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
TILE_SIZE = 64


# Existing code for enhanced_render, EnhancedPlayer, etc.

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


def _render(self):
    """Render the game with enhanced visual effects"""
    # Fill background
    self.screen.fill(BLACK)

    # Render map
    self.game_map.render(self.screen, self.camera.x, self.camera.y)

    # Render player trail effect
    self.player.render_trail(self.screen, self.camera.x, self.camera.y)

    # Draw player footstep particles
    self.player.render_particles(self.screen, self.camera.x, self.camera.y)

    # Rest of the existing rendering code
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

    # Add rest of the rendering logic from the original _render method

    # Update display
    pygame.display.flip()


def _render_enhanced_weather_effects(self):
    """Render enhanced weather effects"""
    width, height = self.screen.get_size()
    weather_surface = pygame.Surface((width, height), pygame.SRCALPHA)

    # Implement weather effects similar to the original method
    if self.game_state.weather == Weather.CLOUDY:
        # Cloudy weather rendering
        pass
    elif self.game_state.weather == Weather.RAINY:
        # Rainy weather rendering
        pass
    # Add other weather conditions

    # Blend weather effects onto the screen
    self.screen.blit(weather_surface, (0, 0))


# Ensure this is at the end of the file
Game._update = _update
Game._render = _render
Game._render_enhanced_weather_effects = _render_enhanced_weather_effects

