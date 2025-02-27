import os

from npc_memory_system import PlayerMemorySystem, enhance_npc_with_memory
from npc_dialogue_enhancement import EnhancedDialogueManager  # If used, but typically from game_classes.py itself
from npc_observer import NPCObserverSystem
from npc_interaction_system import NPCInteractionManager
from constants import *
from game_enums import Direction, TimeOfDay, Weather, EventType
from sprite_manager import SpriteManager
from particle_system import ParticleSystem
import logging

logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)
logger = logging.getLogger(__name__)

import pygame
import math
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional
import random
import textwrap
import sys
from pygame import gfxdraw
from huggingface_hub import InferenceClient


def is_near_fountain(npc, game_map):
    """
    Check if an NPC is near the fountain

    Args:
        npc: NPC object
        game_map: Game map object

    Returns:
        bool: True if NPC is close to the fountain, False otherwise
    """
    # Find the fountain in the game map
    fountain = next((obs for obs in game_map.obstacles if "fountain" in obs.entity_id.lower()), None)

    if not fountain:
        return False

    # Calculate distance between NPC and fountain
    dx = npc.x - fountain.x
    dy = npc.y - fountain.y
    distance = math.sqrt(dx * dx + dy * dy)

    # Define a threshold for "near" (adjust as needed)
    return distance <= 250  # pixels


def fountain_conversation_responses(npc, environment_state, player_message, game_map):
    """
    Generate context-specific responses about the fountain
    Only if NPC is near the fountain
    """
    fountain_topics = [
        "The fountain has been the heart of our town for generations.",
        "I love watching the water dance in the sunlight.",
        "This fountain holds so many memories of our community.",
        "The way light reflects on the water is truly magical.",
        "Every drop tells a story of our town's history."
    ]

    # Check if NPC is near the fountain
    if not is_near_fountain(npc, game_map):
        # If not near fountain, use a generic response
        return f"Hello, I'm {npc.name}. How are you today?"

    # If no specific message, return a random fountain-related comment
    if not player_message or len(player_message.strip()) < 3:
        return random.choice(fountain_topics)

    # Use the NLP model for more nuanced responses
    try:
        base_response = query_local_model(npc, environment_state, player_message)

        # Blend in fountain-specific flavor if response is too short
        if len(base_response) < 20:
            base_response += " " + random.choice(fountain_topics)

        return base_response
    except Exception:
        return random.choice(fountain_topics)


def create_fountain_interaction_npcs(game_map, map_width, map_height):
    """
    Create NPCs specifically positioned around the fountain
    with interactions tailored to the location
    """
    # Fountain-specific NPCs with water/town-related backgrounds
    fountain_npcs = [
        NPC("water_carrier", "Elena the Water Carrier",
            map_width // 2 - 150, map_height // 2 + 100,
            personality="friendly,hardworking",
            backstory="I've been bringing water from this fountain to the town for years.",
            location_id="town_square",
            color=(0, 105, 148)),  # Deep water blue

        NPC("town_gossip", "Old Marcus",
            map_width // 2 + 150, map_height // 2 - 100,
            personality="talkative,wise",
            backstory="This fountain has been the heart of our town's stories for decades.",
            location_id="town_square",
            color=(139, 69, 19)),  # Rich brown

        NPC("young_artist", "Aria the Painter",
            map_width // 2 - 50, map_height // 2 + 200,
            personality="creative,observant",
            backstory="I find inspiration in the way light plays on the fountain's waters.",
            location_id="town_square",
            color=(255, 99, 71))  # Tomato red
    ]

    # Add NPCs to the game map and customize their interaction method
    for npc in fountain_npcs:
        # Override the conversation method with fountain-specific responses
        # Pass game_map to the method to check fountain proximity
        npc.simulate_npc_response = lambda env, msg, n=npc, gm=game_map: fountain_conversation_responses(n, env, msg,
                                                                                                         gm)
        game_map.add_npc(npc)

    return fountain_npcs


class EntityType(Enum):
    PLAYER = 0
    NPC = 1
    ITEM = 2
    OBSTACLE = 3


@dataclass
class Entity:
    """Base class for all game entities"""
    entity_id: str
    name: str
    x: int
    y: int
    width: int = TILE_SIZE
    height: int = TILE_SIZE
    color: Tuple[int, int, int] = WHITE
    entity_type: EntityType = EntityType.OBSTACLE

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def distance_to(self, other: 'Entity') -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)


class Obstacle(Entity):
    """Impassable obstacle"""

    def __init__(self, obstacle_id: str, name: str, x: int, y: int,
                 width: int, height: int,
                 color: Tuple[int, int, int] = BROWN):
        super().__init__(obstacle_id, name, x, y, width, height,
                         color, EntityType.OBSTACLE)


# Modify the Obstacle class to support custom sprites
class SpriteObstacle(Obstacle):
    """An obstacle that can have a custom sprite"""

    def __init__(self, obstacle_id, name, x, y, width, height, color=BROWN, sprite=None):
        super().__init__(obstacle_id, name, x, y, width, height, color)
        self.sprite = sprite

    def render(self, surface, x, y):
        """Render the obstacle with its sprite"""
        if self.sprite:
            # Blit the sprite at the given position
            surface.blit(self.sprite, (x, y))
        else:
            # Fallback to standard rectangle rendering
            obstacle_rect = pygame.Rect(x, y, self.width, self.height)
            pygame.draw.rect(surface, self.color, obstacle_rect)


def load_character_spritesheet(filename, sprite_width=32, sprite_height=32, color_key=None):
    """
    Load a character spritesheet with consistent layout

    Assumes spritesheet has 4 rows (Down, Left, Right, Up)
    Each row has multiple animation frames

    Args:
        filename (str): Path to spritesheet image
        sprite_width (int): Width of each sprite frame
        sprite_height (int): Height of each sprite frame
        color_key (tuple, optional): Color to use as transparency

    Returns:
        dict: Directional sprites with animation frames
    """
    try:
        # Change the path to look in the 'sprites' folder
        spritesheet = pygame.image.load(os.path.join('sprites', 'player', filename)).convert_alpha()

        # If color key is provided, set transparency
        if color_key:
            spritesheet.set_colorkey(color_key)

        # Prepare sprite dictionaryw
        sprites = {
            Direction.DOWN: [],
            Direction.LEFT: [],
            Direction.RIGHT: [],
            Direction.UP: []
        }

        # Directions correspond to rows in the spritesheet
        directions = [Direction.DOWN, Direction.LEFT, Direction.RIGHT, Direction.UP]

        # Extract sprites for each direction
        for row, direction in enumerate(directions):
            # Calculate row position
            y_pos = row * sprite_height

            # Find how many frames are in this row
            frames = spritesheet.get_width() // sprite_width

            # Extract each frame for this direction
            for frame in range(frames):
                x_pos = frame * sprite_width

                # Create surface for this sprite
                sprite = pygame.Surface((sprite_width, sprite_height), pygame.SRCALPHA)
                sprite.blit(spritesheet, (0, 0),
                            (x_pos, y_pos, sprite_width, sprite_height))

                # Resize to match tile size
                sprite = pygame.transform.scale(sprite, (TILE_SIZE, TILE_SIZE))

                sprites[direction].append(sprite)

        return sprites

    except Exception as e:
        print(f"Error loading spritesheet {filename}: {e}")

        # Fallback sprite generation if loading fails
        return {
            Direction.DOWN: [pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA) for _ in range(4)],
            Direction.LEFT: [pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA) for _ in range(4)],
            Direction.RIGHT: [pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA) for _ in range(4)],
            Direction.UP: [pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA) for _ in range(4)]
        }


class MovingEntity(Entity):
    """Base class for entities that can move"""

    def __init__(self, entity_id: str, name: str, x: int, y: int,
                 width: int = TILE_SIZE, height: int = TILE_SIZE,
                 color: Tuple[int, int, int] = WHITE,
                 entity_type: EntityType = EntityType.NPC,
                 speed: int = 2):  # Default NPC_SPEED is 2
        super().__init__(entity_id, name, x, y, width, height, color, entity_type)
        self.speed = speed
        self.direction = Direction.DOWN
        self.is_moving = False
        self.pathfinder = None
        self.path = []
        self.target_x = None
        self.target_y = None

    def update(self, game_map, game_state, player):
        """Update method for moving entities"""
        # You can add common update logic for all moving entities here
        pass

    def move(self, dx: int, dy: int, game_map: 'GameMap') -> bool:
        """Move the entity if there's no collision, with vibration effect"""
        new_x = self.x + dx
        new_y = self.y + dy

        # Update direction
        if abs(dx) > abs(dy):
            self.direction = Direction.RIGHT if dx > 0 else Direction.LEFT
        else:
            self.direction = Direction.DOWN if dy > 0 else Direction.UP

        # Check boundary collisions
        if new_x < 0 or new_x > game_map.width - self.width or new_y < 0 or new_y > game_map.height - self.height:
            return False

        # Check collision with obstacles
        temp_rect = pygame.Rect(new_x, new_y, self.width, self.height)
        for obstacle in game_map.obstacles:
            if temp_rect.colliderect(obstacle.get_rect()):
                # Try to slide along the obstacle
                slide_x, slide_y = new_x, new_y

                # Check horizontal sliding
                if not any(temp_rect.move(-self.speed, 0).colliderect(obs.get_rect()) for obs in game_map.obstacles):
                    slide_x -= self.speed
                elif not any(temp_rect.move(self.speed, 0).colliderect(obs.get_rect()) for obs in game_map.obstacles):
                    slide_x += self.speed

                # Check vertical sliding
                if not any(temp_rect.move(0, -self.speed).colliderect(obs.get_rect()) for obs in game_map.obstacles):
                    slide_y -= self.speed
                elif not any(temp_rect.move(0, self.speed).colliderect(obs.get_rect()) for obs in game_map.obstacles):
                    slide_y += self.speed

                # If we can slide, update the position
                if slide_x != new_x or slide_y != new_y:
                    new_x, new_y = slide_x, slide_y
                else:
                    # If we can't slide, stop movement in this direction
                    return False

        # Move if no collision
        self.x = new_x
        self.y = new_y
        return True

    def set_target(self, x: int, y: int):
        """Set a movement target"""
        self.target_x = x
        self.target_y = y

    def move_towards_target(self, game_map: 'GameMap'):
        """Move towards the target position"""
        if self.target_x is None or self.target_y is None:
            return

        dx = self.target_x - self.x
        dy = self.target_y - self.y

        # Calculate direction vector
        distance = max(1, math.sqrt(dx * dx + dy * dy))
        dx = dx / distance * self.speed
        dy = dy / distance * self.speed

        # Move
        self.move(int(dx), int(dy), game_map)

        # Check if we've reached the target
        if abs(self.x - self.target_x) < self.speed and abs(self.y - self.target_y) < self.speed:
            self.target_x = None
            self.target_y = None


class GameMap:
    """Game world map with rooms and entities"""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.rooms = []
        self.npcs = []
        self.items = []
        self.obstacles = []

    def add_room(self, room: 'Room'):
        """Add a room to the map"""
        self.rooms.append(room)

    def add_npc(self, npc: 'NPC'):
        """Add an NPC to the map"""
        self.npcs.append(npc)

    def add_item(self, item: 'Item'):
        """Add an item to the map"""
        self.items.append(item)

    def add_obstacle(self, obstacle: 'Obstacle'):
        """Add an obstacle to the map"""
        self.obstacles.append(obstacle)

    def get_room_by_id(self, room_id: str) -> Optional['Room']:
        """Get a room by its ID"""
        for room in self.rooms:
            if room.room_id == room_id:
                return room
        return None

    def get_room_at_position(self, x: int, y: int) -> Optional['Room']:
        """Get the room at a specific position"""
        for room in self.rooms:
            if room.contains_point(x, y):
                return room
        return None

    def get_npc_by_id(self, npc_id: str) -> Optional['NPC']:
        """Get an NPC by ID"""
        for npc in self.npcs:
            if npc.entity_id == npc_id:
                return npc
        return None

    def get_npcs_in_room(self, room_id: str) -> List['NPC']:
        """Get all NPCs in a specific room"""
        return [npc for npc in self.npcs if npc.location_id == room_id]

    def get_items_in_room(self, room_id: str) -> List['Item']:
        """Get all items in a specific room"""
        room = self.get_room_by_id(room_id)
        if not room:
            return []

        return [item for item in self.items
                if not item.is_collected and
                room.contains_point(item.x, item.y)]

    def get_items_near_position(self, x: int, y: int, radius: int) -> List['Item']:
        """Get items near a position"""
        return [item for item in self.items
                if not item.is_collected and
                math.sqrt((item.x - x) ** 2 + (item.y - y) ** 2) <= radius]

    def get_npc_near_position(self, x: int, y: int, radius: int) -> Optional['NPC']:
        """Get the closest NPC near a position"""
        nearby_npcs = []
        for npc in self.npcs:
            distance = math.sqrt((npc.x - x) ** 2 + (npc.y - y) ** 2)
            if distance <= radius:
                nearby_npcs.append((npc, distance))

        if not nearby_npcs:
            return None

        # Return the closest NPC
        nearby_npcs.sort(key=lambda x: x[1])
        return nearby_npcs[0][0]

    def render(self, surface, camera_x, camera_y):
        """Render the entire map with enhanced visuals"""
        # Fill background
        surface.fill((50, 50, 50))  # Dark background color

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

            # Add special rendering for fountain in village_square
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
            obstacle_x = obstacle.x - camera_x
            obstacle_y = obstacle.y - camera_y

            if isinstance(obstacle, SpriteObstacle) and obstacle.sprite:
                surface.blit(obstacle.sprite, (obstacle_x, obstacle_y))
            else:
                obstacle_rect = pygame.Rect(obstacle_x, obstacle_y, obstacle.width, obstacle.height)
                pygame.draw.rect(surface, obstacle.color, obstacle_rect)

                # Add simple highlight/shadow for 3D effect
                highlight_rect = pygame.Rect(obstacle_rect.x, obstacle_rect.y, obstacle_rect.width,
                                             obstacle_rect.height // 4)
                shadow_rect = pygame.Rect(obstacle_rect.x, obstacle_rect.y + 3 * obstacle_rect.height // 4,
                                          obstacle_rect.width, obstacle_rect.height // 4)

                # Lighten top
                highlight = pygame.Surface((highlight_rect.width, highlight_rect.height), pygame.SRCALPHA)
                highlight.fill((255, 255, 255, 50))
                surface.blit(highlight, highlight_rect)

                # Darken bottom
                shadow = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
                shadow.fill((0, 0, 0, 70))
                surface.blit(shadow, shadow_rect)


class Room:
    """Represents a room or area in the game"""

    def __init__(self, room_id: str, name: str, x: int, y: int,
                 width: int, height: int, description: str):
        self.room_id = room_id
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.description = description
        self.floor_color = LIGHT_GRAY
        self.npcs = []
        self.items = []
        self.obstacles = []
        self.exits = {}  # Direction -> connected room_id

    def contains_point(self, x: int, y: int) -> bool:
        """Check if a point is within this room"""
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)

    def get_center(self) -> Tuple[int, int]:
        """Get the center point of the room"""
        return self.x + self.width // 2, self.y + self.height // 2


class Camera:
    """Camera that follows the player"""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.x = 0
        self.y = 0

    def update(self, target_x, target_y, map_width, map_height):
        """Update camera position to follow a target"""
        # Center camera on target
        self.x = target_x - self.width // 2
        self.y = target_y - self.height // 2

        # Keep camera within map bounds
        self.x = max(0, min(self.x, map_width - self.width))
        self.y = max(0, min(self.y, map_height - self.height))


class GameState:
    """Manages the overall game state"""

    def __init__(self):
        self.time_of_day = TimeOfDay.MORNING
        self.weather = Weather.CLEAR
        self.days_passed = 1
        self.time_cycle = [TimeOfDay.MORNING, TimeOfDay.AFTERNOON,
                           TimeOfDay.EVENING, TimeOfDay.NIGHT]
        self.weather_options = [Weather.CLEAR, Weather.CLOUDY,
                                Weather.RAINY, Weather.FOGGY, Weather.STORMY]
        self.weather_weights = [0.5, 0.25, 0.15, 0.05, 0.05]  # Probabilities
        self.time_last_advanced = pygame.time.get_ticks()
        self.time_per_cycle = DAY_LENGTH // len(self.time_cycle)  # Time per cycle phase
        self.events = {
            "wolf_howl": False,
            "merchant_sale": False,
            "festival_preparation": False
        }

    def update(self):
        """Update game state based on time passage"""
        current_time = pygame.time.get_ticks()

        # Check if it's time to advance the time of day
        if current_time - self.time_last_advanced >= self.time_per_cycle:
            self._advance_time()
            self.time_last_advanced = current_time

    def _advance_time(self):
        """Advance the time of day and potentially the weather"""
        current_index = self.time_cycle.index(self.time_of_day)
        next_index = (current_index + 1) % len(self.time_cycle)
        self.time_of_day = self.time_cycle[next_index]

        # New day begins at morning
        if self.time_of_day == TimeOfDay.MORNING:
            self.days_passed += 1
            # Change weather with the new day
            self.weather = random.choices(
                self.weather_options,
                weights=self.weather_weights,
                k=1
            )[0]

            # Trigger special events with low probability
            if random.random() < 0.2:  # 20% chance each new day
                random_event = random.choice(list(self.events.keys()))
                self.events[random_event] = True

    def get_environment_state(self, room_id):
        """Get environment state for a specific room"""
        return {
            "time_of_day": self.time_of_day,
            "weather": self.weather,
            "days_passed": self.days_passed,
            "events": {k: v for k, v in self.events.items() if v}
        }

    def get_time_color_overlay(self):
        """Get color overlay based on time of day"""
        if self.time_of_day == TimeOfDay.MORNING:
            return (255, 255, 200, 20)  # Slight yellow tint
        elif self.time_of_day == TimeOfDay.AFTERNOON:
            return (255, 255, 255, 0)  # No tint
        elif self.time_of_day == TimeOfDay.EVENING:
            return (255, 200, 150, 40)  # Orange-red tint
        elif self.time_of_day == TimeOfDay.NIGHT:
            return (50, 50, 100, 120)  # Dark blue overlay

    def render_weather_effect(self, surface):
        """Render weather effects on the screen"""
        if self.weather == Weather.CLEAR:
            return

        width, height = surface.get_size()
        weather_surface = pygame.Surface((width, height), pygame.SRCALPHA)

        if self.weather == Weather.CLOUDY:
            weather_surface.fill((200, 200, 200, 40))
            current_time = pygame.time.get_ticks() // 50  # Slow time factor
            for i in range(5):
                cloud_x = (current_time // (10 + i * 5) + i * width // 5) % (width + 200) - 100
                cloud_y = height // 10 + i * 20
                cloud_width = 100 + i * 30
                cloud_height = 40 + i * 10
                for j in range(5):
                    offset_x = j * cloud_width // 8
                    offset_y = math.sin(j * 0.8) * 5
                    size = cloud_height // 2 + j * 5
                    pygame.draw.circle(weather_surface, (220, 220, 220, 20),
                                       (int(cloud_x + offset_x), int(cloud_y + offset_y)), size)

        elif self.weather == Weather.RAINY:
            weather_surface.fill((100, 100, 150, 60))
            current_time = pygame.time.get_ticks()
            rain_count = 100
            for i in range(rain_count):
                seed = i * 10
                x = (seed * 97 + current_time // 20) % width
                y_offset = (current_time // 10 + seed * 13) % height
                y = (y_offset + seed * 17) % height
                length = random.randint(5, 15)
                thickness = 1 if random.random() < 0.8 else 2
                angle = math.pi / 6  # 30 degrees
                end_x = x - math.sin(angle) * length
                end_y = y + math.cos(angle) * length
                alpha = random.randint(100, 200)
                pygame.draw.line(weather_surface, (200, 200, 255, alpha),
                                 (x, y), (end_x, end_y), thickness)

        elif self.weather == Weather.FOGGY:
            base_alpha = 100
            current_time = pygame.time.get_ticks() // 100
            weather_surface.fill((255, 255, 255, base_alpha))
            for i in range(8):
                fog_x = (current_time // (20 + i * 10) + i * 100) % (width * 2) - width // 2
                fog_y = height // 4 + math.sin(current_time / 1000 + i) * height // 8
                fog_radius = 100 + i * 30
                fog_alpha = 20 + int(15 * math.sin(current_time / 500 + i * 0.5))
                for r in range(fog_radius, 0, -fog_radius // 5):
                    pygame.draw.circle(weather_surface, (255, 255, 255, fog_alpha),
                                       (int(fog_x), int(fog_y)), r)

        elif self.weather == Weather.STORMY:
            weather_surface.fill((50, 50, 70, 100))
            current_time = pygame.time.get_ticks()
            if random.random() < 0.02:  # 2% chance per frame for lightning
                self.lightning_start = current_time
                self.lightning_duration = random.randint(50, 150)
            if hasattr(self, 'lightning_start') and current_time - self.lightning_start < self.lightning_duration:
                progress = (current_time - self.lightning_start) / self.lightning_duration
                intensity = math.sin(progress * math.pi)
                flash_alpha = int(200 * intensity)
                flash_surface = pygame.Surface((width, height), pygame.SRCALPHA)
                flash_surface.fill((255, 255, 255, flash_alpha))
                weather_surface.blit(flash_surface, (0, 0))
                if random.random() < 0.3 and flash_alpha > 100:
                    bolt_start_x = random.randint(0, width)
                    bolt_start_y = 0
                    bolt_segments = random.randint(4, 8)
                    bolt_width = 3
                    last_x, last_y = bolt_start_x, bolt_start_y
                    for j in range(bolt_segments):
                        next_x = last_x + random.randint(-80, 80)
                        next_y = last_y + height // bolt_segments
                        pygame.draw.line(weather_surface, (200, 200, 255, 240),
                                         (last_x, last_y), (next_x, next_y), bolt_width)
                        for k in range(3):
                            glow_width = bolt_width + k * 2
                            glow_alpha = 150 - k * 50
                            pygame.draw.line(weather_surface, (200, 200, 255, glow_alpha),
                                             (last_x, last_y), (next_x, next_y), glow_width)
                        if random.random() < 0.3:
                            fork_x = next_x + random.randint(-40, 40)
                            fork_y = next_y + random.randint(10, 30)
                            pygame.draw.line(weather_surface, (200, 200, 255, 200),
                                             (next_x, next_y), (fork_x, fork_y), bolt_width - 1)
                        last_x, last_y = next_x, next_y

        surface.blit(weather_surface, (0, 0))


class Item(Entity):
    """Collectible item"""

    def __init__(self, item_id: str, name: str, x: int, y: int,
                 description: str, value: int = 0,
                 color: Tuple[int, int, int] = GOLD):
        super().__init__(item_id, name, x, y, TILE_SIZE // 2, TILE_SIZE // 2,
                         color, EntityType.ITEM)
        self.description = description
        self.value = value
        self.is_collected = False

    def render(self, surface, camera_x, camera_y):
        """Render the item"""
        if self.is_collected:
            return

        item_rect = pygame.Rect(
            self.x - camera_x,
            self.y - camera_y,
            self.width,
            self.height
        )
        pygame.draw.rect(surface, self.color, item_rect)
        # Add shine effect
        shine_size = min(self.width, self.height) // 3
        shine_pos = (
            self.x - camera_x + self.width // 4,
            self.y - camera_y + self.height // 4
        )
        pygame.draw.circle(surface, WHITE, shine_pos, shine_size)


class InventoryUI:
    """UI for displaying and managing inventory"""

    def __init__(self):
        self.is_visible = False
        self.font = pygame.font.SysFont('Arial', FONT_SIZE)
        self.selected_index = 0

    def toggle(self):
        """Toggle inventory visibility"""
        self.is_visible = not self.is_visible
        if self.is_visible:
            self.selected_index = 0

    def handle_input(self, event, player):
        """Handle input in inventory mode"""
        if not self.is_visible:
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_i:
                self.is_visible = False
            elif event.key == pygame.K_UP:
                self.selected_index = max(0, self.selected_index - 1)
            elif event.key == pygame.K_DOWN:
                self.selected_index = min(len(player.inventory) - 1, self.selected_index + 1)

    def render(self, surface, player, game_world):
        """Render inventory UI"""
        if not self.is_visible:
            return

        width, height = surface.get_size()

        # Create inventory panel
        inventory_rect = pygame.Rect(
            (width - INVENTORY_WIDTH) // 2,
            (height - INVENTORY_HEIGHT) // 2,
            INVENTORY_WIDTH,
            INVENTORY_HEIGHT
        )

        # Draw semi-transparent background
        inventory_surface = pygame.Surface((INVENTORY_WIDTH, INVENTORY_HEIGHT), pygame.SRCALPHA)
        inventory_surface.fill((0, 0, 0, 200))  # Semi-transparent black
        surface.blit(inventory_surface, inventory_rect)

        # Draw border
        pygame.draw.rect(surface, WHITE, inventory_rect, 2)

        # Draw title
        title_surface = self.font.render("INVENTORY", True, GOLD)
        title_width = title_surface.get_width()
        surface.blit(title_surface,
                     (inventory_rect.x + (INVENTORY_WIDTH - title_width) // 2,
                      inventory_rect.y + 10))

        # Draw gold
        gold_surface = self.font.render(f"Gold: {player.gold}", True, GOLD)
        surface.blit(gold_surface, (inventory_rect.x + 20, inventory_rect.y + 40))

        # Draw items
        item_y = inventory_rect.y + 70
        for i, item in enumerate(player.inventory):
            # Highlight selected item
            if i == self.selected_index:
                selection_rect = pygame.Rect(
                    inventory_rect.x + 10,
                    item_y - 2,
                    INVENTORY_WIDTH - 20,
                    self.font.get_height() + 4
                )
                pygame.draw.rect(surface, DARK_YELLOW, selection_rect, 0)

            # Draw item name
            item_surface = self.font.render(item.name, True, WHITE)
            surface.blit(item_surface, (inventory_rect.x + 20, item_y))

            item_y += self.font.get_height() + 5

        # Draw item description if an item is selected
        if player.inventory and 0 <= self.selected_index < len(player.inventory):
            selected_item = player.inventory[self.selected_index]
            description_rect = pygame.Rect(
                inventory_rect.x + 10,
                inventory_rect.y + INVENTORY_HEIGHT - 80,
                INVENTORY_WIDTH - 20,
                60
            )
            pygame.draw.rect(surface, DARK_GRAY, description_rect)
            pygame.draw.rect(surface, LIGHT_GRAY, description_rect, 1)

            # Wrap description text
            wrapped_text = textwrap.wrap(selected_item.description, width=40)
            desc_y = description_rect.y + 5
            for line in wrapped_text:
                desc_surface = self.font.render(line, True, WHITE)
                surface.blit(desc_surface, (description_rect.x + 5, desc_y))
                desc_y += self.font.get_height()

            # Draw value
            value_text = f"Value: {selected_item.value} gold"
            value_surface = self.font.render(value_text, True, GOLD)
            surface.blit(value_surface,
                         (description_rect.x + 5,
                          description_rect.y + description_rect.height - self.font.get_height() - 5))


class HUD:
    """Heads-up display for game information"""

    def __init__(self):
        self.font = pygame.font.SysFont('Arial', FONT_SIZE)
        self.location_font = pygame.font.SysFont('Arial', FONT_SIZE + 4, bold=True)

    def get_average_friendship(self, game_map, player):
        """Calculate the average friendship level with NPCs in the current town."""
        current_room = game_map.get_room_at_position(player.x, player.y)
        if not current_room:
            return 0

        npcs_in_room = game_map.get_npcs_in_room(current_room.room_id)
        if not npcs_in_room:
            return 0

        total_friendship = sum(npc.friendship for npc in npcs_in_room)
        average_friendship = total_friendship / len(npcs_in_room)
        return average_friendship

    def render(self, surface, player, game_state, game_map):
        """Render HUD elements"""
        width, height = surface.get_size()

        # Top bar with location, time, and date
        top_bar_height = 40
        top_bar_rect = pygame.Rect(0, 0, width, top_bar_height)
        top_bar_surface = pygame.Surface((width, top_bar_height), pygame.SRCALPHA)
        top_bar_surface.fill((0, 0, 0, 150))
        surface.blit(top_bar_surface, (0, 0))

        # Get current room
        current_room = game_map.get_room_at_position(player.x, player.y)
        location_name = current_room.name if current_room else "Unknown Location"

        # Render location name
        location_surface = self.location_font.render(location_name, True, WHITE)
        surface.blit(location_surface, (20, 10))

        # Render time and weather
        time_str = f"Day {game_state.days_passed} - {game_state.time_of_day.name}"
        weather_str = f"Weather: {game_state.weather.name}"

        time_surface = self.font.render(time_str, True, WHITE)
        weather_surface = self.font.render(weather_str, True, WHITE)

        # Position at right side of top bar
        surface.blit(time_surface,
                     (width - time_surface.get_width() - 20, 5))
        surface.blit(weather_surface,
                     (width - weather_surface.get_width() - 20, 5 + self.font.get_height()))

        # Bottom bar with health and controls hint
        bottom_bar_height = 30
        bottom_bar_y = height - bottom_bar_height
        bottom_bar_rect = pygame.Rect(0, bottom_bar_y, width, bottom_bar_height)
        bottom_bar_surface = pygame.Surface((width, bottom_bar_height), pygame.SRCALPHA)
        bottom_bar_surface.fill((0, 0, 0, 150))
        surface.blit(bottom_bar_surface, (0, bottom_bar_y))

        # Render health
        health_str = f"Health: {player.health}/100"
        health_surface = self.font.render(health_str, True, WHITE)
        surface.blit(health_surface, (20, bottom_bar_y + 5))

        # Render controls hint
        controls_str = "WASD: Move | E: Interact | I: Inventory | ESC: Menu"
        controls_surface = self.font.render(controls_str, True, WHITE)
        surface.blit(controls_surface,
                     (width - controls_surface.get_width() - 20, bottom_bar_y + 5))

        # Render average friendship in the current town
        if current_room:
            average_friendship = self.get_average_friendship(game_map, player)
            friendship_str = f"Avg Friendship: {average_friendship:.1f}/100"
            friendship_surface = self.font.render(friendship_str, True, WHITE)
            surface.blit(friendship_surface, (width // 2 - friendship_surface.get_width() // 2, bottom_bar_y + 5))

        # Interaction prompt if near an NPC or item
        nearest_npc = game_map.get_npc_near_position(
            player.x, player.y, INTERACTION_DISTANCE
        )
        nearest_items = game_map.get_items_near_position(
            player.x, player.y, INTERACTION_DISTANCE
        )

        if nearest_npc:
            # Render friendship status if near an NPC
            friendship_status = nearest_npc.get_friendship_status()
            friendship_str = f"Friendship: {friendship_status} ({nearest_npc.friendship})"
            friendship_surface = self.font.render(friendship_str, True, WHITE)
            surface.blit(friendship_surface, (width - friendship_surface.get_width() - 20, bottom_bar_y - 30))

            logger.debug(f"Friendship with {nearest_npc.name}: {nearest_npc.friendship} ({friendship_status})")


class SpriteSheet:
    """Utility class for loading and parsing spritesheets"""

    def __init__(self, filename):
        """Load the spritesheet"""
        try:
            self.sheet = pygame.image.load(filename).convert_alpha()
        except pygame.error as e:
            print(f"Unable to load spritesheet image: {filename}")
            print(e)
            # Create a fallback surface if image loading fails
            self.sheet = pygame.Surface((256, 256), pygame.SRCALPHA)
            self.sheet.fill((0, 0, 0, 0))
            # Draw a simple placeholder
            pygame.draw.rect(self.sheet, (100, 100, 255), (0, 0, 64, 64))
            pygame.draw.rect(self.sheet, (255, 100, 100), (64, 0, 64, 64))
            pygame.draw.rect(self.sheet, (100, 255, 100), (0, 64, 64, 64))
            pygame.draw.rect(self.sheet, (255, 255, 100), (64, 64, 64, 64))

    def image_at(self, rectangle, colorkey=None):
        """Load a specific image from a rectangle"""
        rect = pygame.Rect(rectangle)
        image = pygame.Surface(rect.size, pygame.SRCALPHA)
        image.blit(self.sheet, (0, 0), rect)

        if colorkey is not None:
            if colorkey == -1:
                colorkey = image.get_at((0, 0))
            image.set_colorkey(colorkey, pygame.RLEACCEL)

        return image

    def images_at(self, rects, colorkey=None):
        """Load multiple images from a list of rectangles"""
        return [self.image_at(rect, colorkey) for rect in rects]

    def load_strip(self, rect, image_count, colorkey=None):
        """Load a strip of images and return them as a list"""
        tups = [(rect[0] + rect[2] * x, rect[1], rect[2], rect[3])
                for x in range(image_count)]
        return self.images_at(tups, colorkey)


def _generate_trade_skills():
    """Generate trade-specific skills"""
    trade_skills = [
        "Bargaining", "Price Estimation",
        "Item Appraisal", "Market Knowledge"
    ]

    return {skill: random.randint(1, 10) for skill in trade_skills}


class NPC(MovingEntity):
    def __init__(self, entity_id, name, x, y, personality, backstory, location_id, items=None, color=YELLOW):
        super().__init__(entity_id, name, x, y, TILE_SIZE, TILE_SIZE, color=color, entity_type=EntityType.NPC)

        # Enhanced NPC attributes
        self.personality = personality
        self.backstory = backstory
        self.location_id = location_id
        self.items = items or []

        # Add friendship meter
        self.friendship = 50  # Start with a neutral friendship level (0-100)

        # Define thresholds for friendship levels
        self.friendship_thresholds = {
            "hostile": 20,
            "neutral": 50,
            "friendly": 80,
            "best_friend": 100
        }

        # New detailed attributes
        self.attributes = {
            "strength": random.randint(1, 10),
            "intelligence": random.randint(1, 10),
            "charisma": random.randint(1, 10),
            "perception": random.randint(1, 10),
            "health": random.randint(50, 100),
            "age": random.randint(18, 80),
            "occupation": self._generate_occupation(),
            "skills": self._generate_skills(),
            "mana": random.randint(50, 100)  # New mana attribute (0-100)
        }

        # Relationship system
        self.relationships = {
            "friendliness": random.uniform(0, 1),  # 0 to 1 scale
            "trust": random.uniform(0, 1),
            "known_players": [],  # Track player interactions
            "relationship_history": []  # Log of interactions
        }

        # Quest and mission related
        self.quests = {
            "available_quests": self._generate_quests(),
            "active_quest": None,
            "quest_progress": {}
        }

        # Economic attributes
        self.economics = {
            "gold": random.randint(10, 500),
            "trade_inventory": self._generate_trade_inventory(),
            "trade_skills": _generate_trade_skills()
        }

        # Add floating text attributes
        self.floating_text = None
        self.floating_text_timer = 0
        self.floating_text_duration = 5000  # 5 seconds in milliseconds

        # Add following-related attributes
        self.follow_state = NPCFollowState.NOT_FOLLOWING
        self.follow_start_time = 0
        self.follow_duration = 0
        self.original_position = (x, y)
        self.following_player = None
        self.departure_reason = None
        self.game_map = None  # Will be set when following starts

        # Increase speed when following
        self.base_speed = self.speed
        self.follow_speed = self.speed * 1.5  # 50% faster when following

    def set_floating_text(self, text, duration=5000):
        """Set text to float above NPC's head"""
        self.floating_text = text
        self.floating_text_timer = pygame.time.get_ticks()
        self.floating_text_duration = duration

    def render_floating_text(self, surface, camera_x, camera_y):
        """Render floating text above NPC's head"""
        if not self.floating_text:
            return

        # Calculate position above NPC's head
        text_font = pygame.font.SysFont('Arial', 16)
        text_surface = text_font.render(self.floating_text, True, WHITE)

        # Position text centered above NPC
        text_x = self.x - camera_x + (self.width - text_surface.get_width()) // 2
        text_y = self.y - camera_y - text_surface.get_height() - 10

        # Calculate fade based on time remaining
        current_time = pygame.time.get_ticks()
        time_elapsed = current_time - self.floating_text_timer
        remaining_time = self.floating_text_duration - time_elapsed

        if remaining_time > 0:
            # Create background for better readability
            padding = 5
            background_rect = pygame.Rect(
                text_x - padding,
                text_y - padding,
                text_surface.get_width() + padding * 2,
                text_surface.get_height() + padding * 2
            )

            # Draw semi-transparent background
            background = pygame.Surface((background_rect.width, background_rect.height), pygame.SRCALPHA)
            alpha = min(255, max(0, int(255 * remaining_time / self.floating_text_duration)))
            background.fill((0, 0, 0, int(alpha * 0.7)))  # Semi-transparent black
            surface.blit(background, background_rect)

            # Draw text with fade
            text_surface.set_alpha(alpha)
            surface.blit(text_surface, (text_x, text_y))
        else:
            self.floating_text = None  # Clear text after duration
            self.floating_text_timer = 0

    def _generate_occupation(self):
        """Generate a random occupation based on personality"""
        occupations = {
            "friendly": ["Merchant", "Innkeeper", "Town Crier"],
            "mysterious": ["Fortune Teller", "Spy", "Wandering Sage"],
            "wise": ["Scholar", "Elder", "Advisor"],
            "busy": ["Blacksmith", "Farmer", "Trader"],
            "default": ["Villager", "Traveler"]
        }

        # Find matching occupations or use default
        personality_types = self.personality.split(',')
        for p in personality_types:
            if p in occupations:
                return random.choice(occupations[p])

        return random.choice(occupations["default"])

    def _generate_skills(self):
        """Generate a set of skills for the NPC"""
        possible_skills = [
            "Persuasion", "Crafting", "Hunting", "Cooking",
            "Herbalism", "Smithing", "Navigation", "Diplomacy",
            "Storytelling", "Trading", "Farming"
        ]

        # Generate 2-4 random skills
        num_skills = random.randint(2, 4)
        return {skill: random.randint(1, 10) for skill in random.sample(possible_skills, num_skills)}

    def _generate_trade_inventory(self):
        """Generate a trade inventory with potential items"""
        trade_items = [
            {"name": "Health Potion", "price": random.randint(5, 50)},
            {"name": "Map Fragment", "price": random.randint(10, 100)},
            {"name": "Mysterious Herb", "price": random.randint(15, 75)},
            {"name": "Crafting Material", "price": random.randint(5, 30)},
            {"name": "Local Artifact", "price": random.randint(50, 200)}
        ]

        # Generate 2-5 trade items
        return random.sample(trade_items, random.randint(2, 5))

    def _generate_quests(self):
        """Generate potential quests for the NPC"""
        quest_types = [
            {
                "name": "Deliver Message",
                "description": "Deliver a message to another NPC in the village",
                "reward": random.randint(10, 50)
            },
            {
                "name": "Gather Herbs",
                "description": "Collect specific herbs from the nearby forest",
                "reward": random.randint(15, 75)
            },
            {
                "name": "Protect Traveler",
                "description": "Escort a traveler through dangerous terrain",
                "reward": random.randint(25, 100)
            }
        ]

        return random.sample(quest_types, random.randint(1, 3))

    def update_relationship(self, player, interaction_type):
        """Update relationship based on player interactions"""
        interaction_weights = {
            "friendly": 0.5,
            "helpful": 0.3,
            "neutral": 0,
            "hostile": -0.2
        }

        weight = interaction_weights.get(interaction_type, 0)

        # Update relationship metrics
        self.relationships["friendliness"] = min(1, max(0,
                                                        self.relationships["friendliness"] + weight
                                                        ))

        self.relationships["trust"] = min(1, max(0,
                                                 self.relationships["trust"] + weight * 0.7
                                                 ))

        # Log interaction
        interaction_entry = {
            "player_name": player.name,
            "interaction_type": interaction_type,
            "timestamp": pygame.time.get_ticks()
        }
        self.relationships["relationship_history"].append(interaction_entry)

        # Track known players
        if player not in self.relationships["known_players"]:
            self.relationships["known_players"].append(player)

    def get_current_sprite(self):
        """Get the current sprite based on direction and animation frame"""
        if not hasattr(self, 'sprites'):
            # Create basic sprites if not already created
            self.sprites = {
                Direction.DOWN: [pygame.Surface((self.width, self.height), pygame.SRCALPHA) for _ in range(4)],
                Direction.LEFT: [pygame.Surface((self.width, self.height), pygame.SRCALPHA) for _ in range(4)],
                Direction.RIGHT: [pygame.Surface((self.width, self.height), pygame.SRCALPHA) for _ in range(4)],
                Direction.UP: [pygame.Surface((self.width, self.height), pygame.SRCALPHA) for _ in range(4)]
            }

            # Create basic NPC appearance
            for direction, frames in self.sprites.items():
                for i, frame in enumerate(frames):
                    pygame.draw.rect(frame, self.color, (0, 0, self.width, self.height))
                    # Add some variation based on frame
                    variation = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                    alpha = 50 + i * 20
                    variation.fill((0, 0, 0, alpha))
                    frame.blit(variation, (0, 0))

        # Update animation frame if moving
        if not hasattr(self, 'animation_frame'):
            self.animation_frame = 0

        if not hasattr(self, 'last_frame_change'):
            self.last_frame_change = pygame.time.get_ticks()
            self.frame_delay = 200  # milliseconds

        current_time = pygame.time.get_ticks()
        if self.is_moving:
            if current_time - self.last_frame_change > self.frame_delay:
                self.animation_frame = (self.animation_frame + 1) % 4
                self.last_frame_change = current_time
        else:
            # Use standing frame when not moving
            self.animation_frame = 0

        # Ensure direction is set, default to DOWN if not
        if not hasattr(self, 'direction'):
            self.direction = Direction.DOWN

        return self.sprites[self.direction][self.animation_frame]

    def simulate_npc_response(self, environment_state, player_message):
        """Wrapper method to use the global simulate_npc_response function"""
        return simulate_npc_response(self, environment_state, player_message)

    def update(self, game_map, game_state, player):
        """
        Update NPC state, movement, and interactions

        Args:
            game_map (GameMap): Current game map
            game_state (GameState): Current game state
            player (Player): Player character
        """
        # Basic movement and action logic
        current_time = pygame.time.get_ticks()

        # Update floating text if it exists
        if hasattr(self, 'floating_text') and self.floating_text:
            if current_time - self.floating_text_timer > self.floating_text_duration:
                self.floating_text = None
                self.floating_text_timer = 0

        # Implement basic NPC behavior
        if not hasattr(self, 'last_action_time'):
            self.last_action_time = current_time
            self.current_action = "idle"
            self.action_duration = random.randint(2000, 5000)  # 2-5 seconds

        # Change action periodically
        if current_time - self.last_action_time > self.action_duration:
            # Randomly choose next action
            actions = ["idle", "wander", "patrol"]
            self.current_action = random.choice(actions)
            self.last_action_time = current_time
            self.action_duration = random.randint(2000, 5000)

        # Perform current action
        if self.current_action == "idle":
            # Do nothing
            pass
        elif self.current_action == "wander":
            # Random movement
            dx = random.choice([-1, 0, 1]) * self.speed
            dy = random.choice([-1, 0, 1]) * self.speed
            self.move(dx, dy, game_map)
        elif self.current_action == "patrol":
            # Simple patrolling behavior
            if not hasattr(self, 'patrol_target'):
                # Set initial patrol target within room
                room = game_map.get_room_by_id(self.location_id)
                if room:
                    self.patrol_target = (
                        random.randint(room.x, room.x + room.width),
                        random.randint(room.y, room.y + room.height)
                    )

            # Move towards patrol target
            if hasattr(self, 'patrol_target'):
                dx = self.patrol_target[0] - self.x
                dy = self.patrol_target[1] - self.y

                # Normalize movement
                distance = max(1, math.sqrt(dx * dx + dy * dy))
                dx = int(dx / distance * self.speed)
                dy = int(dy / distance * self.speed)

                self.move(dx, dy, game_map)

                # Check if reached target
                if abs(self.x - self.patrol_target[0]) < self.speed and \
                        abs(self.y - self.patrol_target[1]) < self.speed:
                    delattr(self, 'patrol_target')

    def update_friendship(self, amount):
        """Update the friendship meter by a certain amount."""
        self.friendship = max(0, min(100, self.friendship + amount))
        logger.debug(f"Friendship with {self.name} changed by {amount}. New level: {self.friendship}")

    def get_friendship_status(self):
        """Get the current friendship status based on the friendship level."""
        if self.friendship <= self.friendship_thresholds["hostile"]:
            return "hostile"
        elif self.friendship <= self.friendship_thresholds["neutral"]:
            return "neutral"
        elif self.friendship <= self.friendship_thresholds["friendly"]:
            return "friendly"
        else:
            return "best_friend"

    def load_sprites(self):
        """Load NPC sprites based on personality using SpriteManager"""
        try:
            self.sprite_manager = SpriteManager()
            if "merchant" in self.personality.lower():
                sprite_file = 'npc_merchant.png'
            elif "elder" in self.personality.lower():
                sprite_file = 'npc_elder.png'
            else:
                sprite_file = 'npc_generic.png'

            sprite_path = os.path.join('npc', sprite_file)
            self.sprites = {
                Direction.DOWN: [],
                Direction.LEFT: [],
                Direction.RIGHT: [],
                Direction.UP: []
            }
            sprite = self.sprite_manager.load_sprite(sprite_path, (self.width, self.height))
            for direction in self.sprites.keys():
                frames = []
                for i in range(4):  # Assume 4 frames per direction
                    frame = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
                    frame.blit(sprite, (0, 0))
                    # Add simple animation (e.g., offset or color variation)
                    pygame.draw.rect(frame, (255, 255, 255, 50 * (i + 1)), (0, 0, self.width, self.height), 1)
                    frames.append(frame)
                self.sprites[direction] = frames
        except Exception as e:
            logger.error(f"Failed to load NPC sprites for {self.name}: {e}")
            # Create basic colored sprites
            self.sprites = {
                Direction.DOWN: [pygame.Surface((self.width, self.height), pygame.SRCALPHA) for _ in range(4)],
                Direction.LEFT: [pygame.Surface((self.width, self.height), pygame.SRCALPHA) for _ in range(4)],
                Direction.RIGHT: [pygame.Surface((self.width, self.height), pygame.SRCALPHA) for _ in range(4)],
                Direction.UP: [pygame.Surface((self.width, self.height), pygame.SRCALPHA) for _ in range(4)]
            }
            for direction in self.sprites:
                for frame in self.sprites[direction]:
                    frame.fill(self.color)

    # Add this to the NPC class
    def move(self, dx: int, dy: int, game_map) -> bool:
        """Move the NPC if there's no collision"""
        if not game_map:
            print(f"Warning: No game map available for NPC {self.name}")
            return False

        new_x = self.x + dx
        new_y = self.y + dy

        # Update direction based on movement
        if abs(dx) > abs(dy):
            self.direction = Direction.RIGHT if dx > 0 else Direction.LEFT
        else:
            self.direction = Direction.DOWN if dy > 0 else Direction.UP

        # Check boundary collisions
        if new_x < 0 or new_x > game_map.width - self.width or new_y < 0 or new_y > game_map.height - self.height:
            return False

        # Check collision with obstacles
        temp_rect = pygame.Rect(new_x, new_y, self.width, self.height)
        for obstacle in game_map.obstacles:
            if temp_rect.colliderect(obstacle.get_rect()):
                return False

        # Move if no collision
        self.x = new_x
        self.y = new_y
        self.is_moving = True
        return True


class NPCAttributesDisplay:
    """Handles rendering of NPC attributes popup display"""

    def __init__(self):
        """Initialize the display manager with fonts and styling"""
        self.name_font = pygame.font.SysFont('Arial', 14, bold=True)
        self.label_font = pygame.font.SysFont('Arial', 12)
        self.goodbye_font = pygame.font.SysFont('Arial', 13)
        self.bar_width = 80
        self.bar_height = 6
        self.box_width = 160
        self.box_height = 105
        self.box_padding = 10
        self.vertical_spacing = 16
        self.goodbye_duration = 5000  # 5 seconds in milliseconds
        self.fade_duration = 500  # 0.5 seconds fade transition

    def render(self, surface: pygame.Surface, npc, camera_x: int, camera_y: int,
               interaction_distance: float, current_time: int) -> None:
        # Don't render attributes if NPC is following and has a departure message
        if (hasattr(npc, 'follow_state') and
                npc.follow_state == NPCFollowState.DEPARTING and
                npc.departure_reason):
            self._render_departure_message(surface, npc, camera_x, camera_y, current_time)
            return
        """Render the NPC attributes display if player is within range"""
        # Position box above NPC
        box_x = npc.x - camera_x + (npc.width - self.box_width) // 2
        box_y = npc.y - camera_y - self.box_height - 10

        # Create background surface
        box_surface = pygame.Surface((self.box_width, self.box_height), pygame.SRCALPHA)

        # Check if there's a goodbye message and it's still active
        showing_goodbye = (hasattr(npc, 'floating_text') and npc.floating_text and
                           hasattr(npc, 'floating_text_timer') and
                           current_time - npc.floating_text_timer < self.goodbye_duration)

        # Calculate fade alpha for transitions
        alpha = 255
        if showing_goodbye:
            time_left = self.goodbye_duration - (current_time - npc.floating_text_timer)
            if time_left < self.fade_duration:
                alpha = int((time_left / self.fade_duration) * 255)

        # Draw main background
        pygame.draw.rect(box_surface, (64, 64, 64, 230),
                         (0, 0, self.box_width, self.box_height))

        # Draw nameplate section (darker)
        nameplate_height = 25
        pygame.draw.rect(box_surface, (45, 45, 45, 250),
                         (0, 0, self.box_width, nameplate_height))

        # Add borders
        pygame.draw.rect(box_surface, (128, 128, 128, 255),
                         (0, 0, self.box_width, self.box_height), 1)
        pygame.draw.line(box_surface, (128, 128, 128, 255),
                         (0, nameplate_height), (self.box_width, nameplate_height), 1)

        # Render background
        surface.blit(box_surface, (box_x, box_y))

        # Render NPC name centered in nameplate
        name_surface = self.name_font.render(npc.name, True, (255, 255, 255))
        name_rect = name_surface.get_rect()
        name_rect.centerx = box_x + self.box_width // 2
        name_rect.centery = box_y + nameplate_height // 2
        surface.blit(name_surface, name_rect)

        if showing_goodbye:
            # Render goodbye message
            goodbye_surface = pygame.Surface((self.box_width - 20, self.box_height - nameplate_height - 15),
                                             pygame.SRCALPHA)
            wrapped_text = textwrap.wrap(npc.floating_text, width=25)

            text_y = 0
            for line in wrapped_text:
                text_surface = self.goodbye_font.render(line, True, (255, 255, 255, alpha))
                text_rect = text_surface.get_rect(centerx=goodbye_surface.get_width() // 2)
                text_rect.top = text_y
                goodbye_surface.blit(text_surface, text_rect)
                text_y += self.goodbye_font.get_height() + 2

            # Center the goodbye message in the box below the nameplate
            goodbye_rect = goodbye_surface.get_rect()
            goodbye_rect.centerx = box_x + self.box_width // 2
            goodbye_rect.top = box_y + nameplate_height + 10
            surface.blit(goodbye_surface, goodbye_rect)

        else:
            # Define attribute bars with specific colors
            bars = [
                ("Mana", npc.attributes["mana"], 100, (50, 50, 255)),
                ("Wealth", npc.economics["gold"], 500, (255, 215, 0)),
                ("Health", npc.attributes["health"], 100, (255, 50, 50)),
                ("Friendship", npc.friendship, 100, (50, 255, 50))
            ]

            # Calculate positions
            start_y = box_y + nameplate_height + 10
            text_start_x = box_x + 10
            bar_start_x = box_x + self.box_width - self.bar_width - 10

            # Render each attribute bar
            for label, value, max_value, color in bars:
                # Render label with colon prefix
                label_text = f": {label}"
                text_surface = self.label_font.render(label_text, True, (200, 200, 200))

                # Position text
                text_y = start_y + (self.bar_height - text_surface.get_height()) // 2
                surface.blit(text_surface, (text_start_x, text_y))

                # Draw bar background
                bar_bg_rect = pygame.Rect(bar_start_x, start_y, self.bar_width, self.bar_height)
                pygame.draw.rect(surface, (30, 30, 30), bar_bg_rect)

                # Draw filled portion
                filled_width = int((value / max_value) * self.bar_width)
                if filled_width > 0:
                    filled_rect = pygame.Rect(bar_start_x, start_y, filled_width, self.bar_height)
                    pygame.draw.rect(surface, color, filled_rect)

                # Draw bar border
                pygame.draw.rect(surface, (100, 100, 100), bar_bg_rect, 1)

                # Move to next position
                start_y += self.vertical_spacing

    def _render_departure_message(self, surface, npc, camera_x, camera_y, current_time):
        """
        Render a departure message for an NPC that is leaving

        Args:
            surface (pygame.Surface): Surface to render on
            npc (NPC): NPC object
            camera_x (int): Camera x offset
            camera_y (int): Camera y offset
            current_time (int): Current game time
        """
        # Position box above NPC
        box_x = npc.x - camera_x + (npc.width - self.box_width) // 2
        box_y = npc.y - camera_y - self.box_height - 10

        # Create background surface
        box_surface = pygame.Surface((self.box_width, self.box_height), pygame.SRCALPHA)

        # Check if there's a departure message and it's still active
        if (hasattr(npc, 'departure_reason') and npc.departure_reason and
                current_time - npc.floating_text_timer < self.goodbye_duration):

            # Calculate fade alpha for transitions
            time_left = self.goodbye_duration - (current_time - npc.floating_text_timer)
            alpha = int((time_left / self.fade_duration) * 255) if time_left < self.fade_duration else 255

            # Draw main background
            pygame.draw.rect(box_surface, (64, 64, 64, 230),
                             (0, 0, self.box_width, self.box_height))

            # Draw nameplate section (darker)
            nameplate_height = 25
            pygame.draw.rect(box_surface, (45, 45, 45, 250),
                             (0, 0, self.box_width, nameplate_height))

            # Add borders
            pygame.draw.rect(box_surface, (128, 128, 128, 255),
                             (0, 0, self.box_width, self.box_height), 1)
            pygame.draw.line(box_surface, (128, 128, 128, 255),
                             (0, nameplate_height), (self.box_width, nameplate_height), 1)

            # Render background
            surface.blit(box_surface, (box_x, box_y))

            # Render NPC name centered in nameplate
            name_surface = self.name_font.render(npc.name, True, (255, 255, 255))
            name_rect = name_surface.get_rect()
            name_rect.centerx = box_x + self.box_width // 2
            name_rect.centery = box_y + nameplate_height // 2
            surface.blit(name_surface, name_rect)

            # Render departure message
            goodbye_surface = pygame.Surface((self.box_width - 20, self.box_height - nameplate_height - 15),
                                             pygame.SRCALPHA)
            wrapped_text = textwrap.wrap(npc.departure_reason, width=25)

            text_y = 0
            for line in wrapped_text:
                text_surface = self.goodbye_font.render(line, True, (255, 255, 255, alpha))
                text_rect = text_surface.get_rect(centerx=goodbye_surface.get_width() // 2)
                text_rect.top = text_y
                goodbye_surface.blit(text_surface, text_rect)
                text_y += self.goodbye_font.get_height() + 2

            # Center the goodbye message in the box below the nameplate
            goodbye_rect = goodbye_surface.get_rect()
            goodbye_rect.centerx = box_x + self.box_width // 2
            goodbye_rect.top = box_y + nameplate_height + 10
            surface.blit(goodbye_surface, goodbye_rect)


class NPCFollowState(Enum):
    NOT_FOLLOWING = "not_following"
    FOLLOWING = "following"
    CONSIDERING = "considering"
    DEPARTING = "departing"


class NPCTrustLevel(Enum):
    STRANGER = 0  # Won't follow
    ACQUAINTANCE = 1  # Might follow briefly
    FRIENDLY = 2  # Will follow for medium duration
    TRUSTED = 3  # Will follow for long duration
    DEVOTED = 4  # Will follow until necessary to leave


class NPCFollowState(Enum):
    NOT_FOLLOWING = "not_following"
    FOLLOWING = "following"
    CONSIDERING = "considering"
    DEPARTING = "departing"


class NPCTrustLevel(Enum):
    STRANGER = 0
    ACQUAINTANCE = 1
    FRIENDLY = 2
    TRUSTED = 3
    DEVOTED = 4


class NPCFollowerSystem:
    def __init__(self):
        self.trust_thresholds = {
            NPCTrustLevel.STRANGER: 0,
            NPCTrustLevel.ACQUAINTANCE: 25,
            NPCTrustLevel.FRIENDLY: 50,
            NPCTrustLevel.TRUSTED: 75,
            NPCTrustLevel.DEVOTED: 90
        }

        self.follow_durations = {
            NPCTrustLevel.ACQUAINTANCE: (30000, 60000),  # 30-60 seconds
            NPCTrustLevel.FRIENDLY: (120000, 300000),  # 2-5 minutes
            NPCTrustLevel.TRUSTED: (300000, 600000),  # 5-10 minutes
            NPCTrustLevel.DEVOTED: (600000, 1200000)  # 10-20 minutes
        }

        self.departure_reasons = [
            "I need to get back to my duties.",
            "I just remembered something important I need to do.",
            "It's getting late, I should head back.",
            "I have some errands to run.",
            "I promised to meet someone else.",
            "I should check on my shop.",
            "I need to prepare for tomorrow.",
            "My feet are getting tired.",
            "I think I hear someone calling me.",
            "I have some unfinished business to attend to."
        ]

        self.follow_distance = 50
        self.max_follow_distance = 200

    def initialize_npc_following(self, npc) -> None:
        if not hasattr(npc, 'follow_state'):
            npc.follow_state = NPCFollowState.NOT_FOLLOWING
            npc.follow_start_time = 0
            npc.follow_duration = 0
            npc.original_position = (npc.x, npc.y)
            npc.following_player = None
            npc.departure_reason = None

    def get_trust_level(self, npc) -> NPCTrustLevel:
        base_trust = npc.friendship

        if hasattr(npc, 'relationship_history'):
            base_trust += len([x for x in npc.relationship_history
                               if x.get('interaction_type') == 'positive']) * 2

        if hasattr(npc, 'personality'):
            if 'friendly' in npc.personality.lower():
                base_trust += 5
            if 'cautious' in npc.personality.lower():
                base_trust -= 5

        for level, threshold in sorted(self.trust_thresholds.items(),
                                       key=lambda x: x[1], reverse=True):
            if base_trust >= threshold:
                return level

        return NPCTrustLevel.STRANGER

    def request_following(self, npc, player, current_time: int) -> tuple[bool, str]:
        self.initialize_npc_following(npc)

        trust_level = self.get_trust_level(npc)

        if trust_level == NPCTrustLevel.STRANGER:
            return False, "I don't know you well enough to follow you."

        if npc.follow_state != NPCFollowState.NOT_FOLLOWING:
            return False, "I'm already engaged in something else."

        min_duration, max_duration = self.follow_durations.get(
            trust_level, (30000, 60000)
        )
        npc.follow_duration = random.randint(min_duration, max_duration)
        npc.follow_start_time = current_time
        npc.follow_state = NPCFollowState.FOLLOWING
        npc.following_player = player
        # Use the game_map from the Game instance instead of the player
        npc.game_map = npc.game_map  # NPC already has game_map reference

        print(f"NPC {npc.name} starting to follow. Trust level: {trust_level}")  # Debug print
        return True, "I'll come with you for a while."

    def _update_following_position(self, npc) -> None:
        target = npc.following_player
        if not target or not hasattr(npc, 'game_map'):
            print(f"Missing target or game_map for NPC {npc.name}")  # Debug print
            return

        dx = target.x - npc.x
        dy = target.y - npc.y
        distance = math.sqrt(dx * dx + dy * dy)

        print(f"NPC {npc.name} distance to player: {distance}")  # Debug print

        if distance > self.follow_distance + 10 or distance < self.follow_distance - 10:
            target_distance = self.follow_distance
            speed_multiplier = 2 if distance > self.max_follow_distance else 1

            if distance > 0:
                move_x = dx * (1 - target_distance / distance) * speed_multiplier
                move_y = dy * (1 - target_distance / distance) * speed_multiplier

                print(f"Moving NPC {npc.name} by x:{move_x}, y:{move_y}")  # Debug print
                movement_success = npc.move(int(move_x), int(move_y), npc.game_map)
                print(f"Movement success: {movement_success}")  # Debug print

    def update_following(self, npc, current_time: int) -> None:
        if not hasattr(npc, 'follow_state'):
            return

        if npc.follow_state == NPCFollowState.FOLLOWING:
            if current_time - npc.follow_start_time >= npc.follow_duration:
                self.end_following(npc, random.choice(self.departure_reasons))
                return

            if random.random() < 0.001:  # 0.1% chance per update
                self.end_following(npc, random.choice(self.departure_reasons))
                return

            if npc.following_player:
                self._update_following_position(npc)

    def end_following(self, npc, reason: str) -> None:
        npc.follow_state = NPCFollowState.DEPARTING
        npc.departure_reason = reason
        npc.set_floating_text(reason, 5000)
        npc.following_player = None


# Add these commands to your dialogue or interaction system

def handle_follow_command(npc, player, current_time):
    """Handle the player requesting an NPC to follow"""
    if not hasattr(player, 'npc_follower_system'):
        player.npc_follower_system = NPCFollowerSystem()

    success, message = player.npc_follower_system.request_following(npc, player, current_time)

    if success:
        # Update NPC's state and display confirmation
        npc.set_floating_text(message, 3000)
        return f"{npc.name} has agreed to follow you."
    else:
        # Display rejection message
        npc.set_floating_text(message, 3000)
        return f"{npc.name} declines to follow you: {message}"


def update_npc_following(game_state, current_time):
    """Update all NPCs' following behavior"""
    if not hasattr(game_state.player, 'npc_follower_system'):
        game_state.player.npc_follower_system = NPCFollowerSystem()

    for npc in game_state.game_map.npcs:
        game_state.player.npc_follower_system.update_following(npc, current_time)


# Example dialogue integration:
def handle_player_input(self, input_text, npc, player, current_time):
    # Check for follow-related commands
    if input_text.lower() in ["follow me", "come with me", "follow"]:
        return handle_follow_command(npc, player, current_time)

    # Rest of your dialogue handling...


def load_wizard_spritesheet(filename, sprite_width=32, sprite_height=32):
    try:
        spritesheet = pygame.image.load(os.path.join('sprites', 'player', filename)).convert_alpha()

        sprites = {
            "idle": [],
            "walk": [],
            "cast": [],
            "special": []
        }

        # Define the regions for each animation type
        regions = {
            "idle": (0, 0, 3, 1),
            "walk": (0, 1, 4, 1),
            "cast": (4, 1, 5, 1),
            "special": (0, 2, 7, 1)
        }

        for anim_type, (start_x, start_y, num_frames, num_rows) in regions.items():
            for row in range(num_rows):
                for col in range(num_frames):
                    x = (start_x + col) * sprite_width
                    y = (start_y + row) * sprite_height
                    sprite = spritesheet.subsurface((x, y, sprite_width, sprite_height))
                    sprite = pygame.transform.scale(sprite, (TILE_SIZE, TILE_SIZE))
                    sprites[anim_type].append(sprite)

        return sprites

    except Exception as e:
        print(f"Error loading wizard spritesheet {filename}: {e}")
        return None


class Wizard(MovingEntity):
    def __init__(self, entity_id, name, x, y):
        super().__init__(entity_id, name, x, y, TILE_SIZE, TILE_SIZE, color=(255, 165, 0), entity_type=EntityType.NPC)
        self.sprites = load_wizard_spritesheet("wizard_spritesheet.png")
        self.current_animation = "idle"
        self.animation_frame = 0
        self.animation_speed = 0.2
        self.last_update = pygame.time.get_ticks()

    def update(self, game_map, game_state, player):
        super().update(game_map, game_state, player)

        now = pygame.time.get_ticks()
        if now - self.last_update > self.animation_speed * 1000:
            self.animation_frame = (self.animation_frame + 1) % len(self.sprites[self.current_animation])
            self.last_update = now

    def get_current_sprite(self):
        return self.sprites[self.current_animation][self.animation_frame]

    def cast_spell(self):
        self.current_animation = "cast"
        self.animation_frame = 0

    def special_move(self):
        self.current_animation = "special"
        self.animation_frame = 0


# Replace the Player class with this enhanced version
class Player(MovingEntity):
    """Player character with enhanced visuals and physics"""

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
        self.diagonal_factor = DIAGONAL_FACTOR
        self.acceleration = PLAYER_ACCELERATION
        self.friction = PLAYER_FRICTION

        # Animation properties
        self.sprite_sheet = None
        self.sprites = {}
        self.animation_frame = 0
        self.last_frame_change = 0
        self.frame_delay = 100  # milliseconds
        self.load_sprites()

        # Visual effects
        self.light_radius = 150
        self.shadow_offset = 4
        self.footstep_particles = []
        self.particle_timer = 0
        self.particle_delay = 200  # ms between particle emissions

    def load_sprites(self):
        """Load player sprites using SpriteManager"""
        try:
            self.sprite_manager = SpriteManager()
            sprite_path = os.path.join('player', 'adventurer.png')
            self.sprites = {
                Direction.DOWN: [],
                Direction.LEFT: [],
                Direction.RIGHT: [],
                Direction.UP: []
            }
            sprite = self.sprite_manager.load_sprite(sprite_path, (self.width, self.height))
            # Load frames manually or use a spritesheet parser (simplified for now)
            for direction in self.sprites.keys():
                frames = []
                for i in range(4):  # Assume 4 frames per direction
                    frame = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
                    frame.blit(sprite, (0, 0))
                    # Add simple animation (e.g., offset or color variation)
                    pygame.draw.rect(frame, (255, 255, 255, 50 * (i + 1)), (0, 0, self.width, self.height), 1)
                    frames.append(frame)
                self.sprites[direction] = frames
        except Exception as e:
            logger.error(f"Error loading player sprites: {e}")
            self._create_fallback_sprites()

    def _create_fallback_sprites(self):
        """Create basic colored sprites if image loading fails"""
        self.sprites = {
            Direction.DOWN: [pygame.Surface((self.width, self.height), pygame.SRCALPHA) for _ in range(4)],
            Direction.LEFT: [pygame.Surface((self.width, self.height), pygame.SRCALPHA) for _ in range(4)],
            Direction.RIGHT: [pygame.Surface((self.width, self.height), pygame.SRCALPHA) for _ in range(4)],
            Direction.UP: [pygame.Surface((self.width, self.height), pygame.SRCALPHA) for _ in range(4)]
        }

        # Basic shapes with direction indicators
        for direction, frames in self.sprites.items():
            for i, frame in enumerate(frames):
                # Base player shape
                pygame.draw.rect(frame, (30, 100, 255), (0, 0, self.width, self.height))

                # Add direction indicator
                indicator_color = (255, 255, 255)
                bounce_offset = math.sin(i * math.pi / 2) * 2  # Create bouncing animation

                if direction == Direction.DOWN:
                    # Triangle pointing down
                    pygame.draw.polygon(frame, indicator_color, [
                        (self.width // 2, self.height - 4 + bounce_offset),
                        (self.width // 2 - 5, self.height // 2 + bounce_offset),
                        (self.width // 2 + 5, self.height // 2 + bounce_offset)
                    ])
                elif direction == Direction.UP:
                    # Triangle pointing up
                    pygame.draw.polygon(frame, indicator_color, [
                        (self.width // 2, 4 + bounce_offset),
                        (self.width // 2 - 5, self.height // 2 + bounce_offset),
                        (self.width // 2 + 5, self.height // 2 + bounce_offset)
                    ])
                elif direction == Direction.LEFT:
                    # Triangle pointing left
                    pygame.draw.polygon(frame, indicator_color, [
                        (4 + bounce_offset, self.height // 2),
                        (self.width // 2 + bounce_offset, self.height // 2 - 5),
                        (self.width // 2 + bounce_offset, self.height // 2 + 5)
                    ])
                elif direction == Direction.RIGHT:
                    # Triangle pointing right
                    pygame.draw.polygon(frame, indicator_color, [
                        (self.width - 4 + bounce_offset, self.height // 2),
                        (self.width // 2 + bounce_offset, self.height // 2 - 5),
                        (self.width // 2 + bounce_offset, self.height // 2 + 5)
                    ])

                # Add shading effect based on frame
                shade = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                shade_alpha = 50 + i * 15  # Vary transparency with frame
                shade.fill((0, 0, 0, shade_alpha))
                frame.blit(shade, (1, 1))

                # Add highlight
                highlight = pygame.Surface((self.width // 2, self.height // 2), pygame.SRCALPHA)
                highlight.fill((255, 255, 255, 30))
                frame.blit(highlight, (self.width // 4, self.height // 4))

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
            # Use standing frame (first frame) when not moving
            self.animation_frame = 0

        return self.sprites[self.direction][self.animation_frame]

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
        """Handle keyboard input for player movement with diagonal movement"""
        dx, dy = 0, 0
        self.is_moving = False

        # Check horizontal movement
        moving_horizontal = False
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -self.speed
            self.direction = Direction.LEFT
            moving_horizontal = True
            self.is_moving = True
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = self.speed
            self.direction = Direction.RIGHT
            moving_horizontal = True
            self.is_moving = True

        # Check vertical movement
        moving_vertical = False
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -self.speed
            self.direction = Direction.UP
            moving_vertical = True
            self.is_moving = True
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = self.speed
            self.direction = Direction.DOWN
            moving_vertical = True
            self.is_moving = True

        # Diagonal movement speed normalization
        if moving_horizontal and moving_vertical:
            # Reduce speed for diagonal movement to maintain consistent overall speed
            dx *= 0.7071  # approximately 1/sqrt(2)
            dy *= 0.7071  # approximately 1/sqrt(2)

            # Update direction for diagonal movement
            if dx < 0 and dy < 0:
                self.direction = Direction.UP  # Diagonal up-left
            elif dx > 0 and dy < 0:
                self.direction = Direction.UP  # Diagonal up-right
            elif dx < 0 and dy > 0:
                self.direction = Direction.DOWN  # Diagonal down-left
            elif dx > 0 and dy > 0:
                self.direction = Direction.DOWN  # Diagonal down-right

        # Move if there's movement
        if dx != 0 or dy != 0:
            self.move(int(dx), int(dy), game_map)


#####################


#####################

ADVENTURER_SIZE = (75, 56)  # Scaled size (50*1.5, 37*1.5)


class EnhancedPlayer(MovingEntity):
    """Enhanced player character with better physics and visuals"""

    def __init__(self, name: str, x: int, y: int, game_instance=None):
        super().__init__("player", name, x, y,
                         ADVENTURER_SIZE[0], ADVENTURER_SIZE[1],
                         color=(0, 100, 255), entity_type=EntityType.PLAYER,
                         speed=PLAYER_SPEED)

        # Add game instance reference
        self.game_instance = game_instance
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
        self.sprite_manager = SpriteManager()
        self.sprites = {}
        self.animation_frame = 0
        self.last_frame_change = 0
        self.frame_delay_run = 80  # milliseconds - faster animation for run
        self.frame_delay_idle = 200
        self.load_sprites()

        # Visual effects (optional, for enhancement)
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

        # Inventory visibility flag
        self.show_inventory = False  # Initialize the show_inventory attribute

        self.inventory = EnhancedInventory()

    def load_sprites(self):
        """Load player sprites from the adventurer sprite sheet using SpriteManager"""
        try:
            sprite_path = os.path.join('player', 'adventurer.png')
            # Define sprite sheet layout: 13 columns, 15 rows
            cols = 13
            rows = 15
            scale = (self.width, self.height)  # Match player size (e.g., 75x56)

            # Load the sprite sheet with potential padding
            frames = self.sprite_manager.load_sprite_sheet(
                sprite_path, cols, rows, scale,
                padding_x=0, padding_y=0  # Adjust if there’s padding between frames
            )

            # Organize frames by action, assuming the first 5 rows contain the animations
            actions = {
                'idle': frames[0:4],  # Row 0: Idle (4 frames, columns 0–3)
                'run': frames[13:19],  # Row 1: Run (6 frames, columns 0–5, indices 13–18)
                'jump': frames[26:32],  # Row 2: Jump (6 frames, columns 0–5, indices 26–31)
                'fall': frames[39:45],  # Row 3: Fall (6 frames, columns 0–5, indices 39–44)
                'attack': frames[52:58]  # Row 4: Attack (6 frames, columns 0–5, indices 52–57)
            }

            # Initialize sprites dictionary for directions
            self.sprites = {
                Direction.DOWN: [],
                Direction.UP: [],
                Direction.RIGHT: [],
                Direction.LEFT: []
            }

            # Assign run frames to directions (use run for movement)
            for frame in actions['run']:
                # Ensure frame is exactly the target size to prevent warping
                if frame.get_width() != self.width or frame.get_height() != self.height:
                    frame = pygame.transform.scale(frame, (self.width, self.height))
                self.sprites[Direction.DOWN].append(frame)  # Down uses run frames
                self.sprites[Direction.RIGHT].append(frame)  # Right uses run frames
                flipped_frame = pygame.transform.flip(frame, True, False)  # Flip for left/up
                self.sprites[Direction.LEFT].append(flipped_frame)  # Left
                self.sprites[Direction.UP].append(flipped_frame)  # Up

            # Add all idle frames for each direction (cycling through 4 frames)
            for direction in self.sprites:
                for frame in actions['idle']:  # Use all 4 idle frames
                    if frame.get_width() != self.width or frame.get_height() != self.height:
                        frame = pygame.transform.scale(frame, (self.width, self.height))
                    if direction in [Direction.RIGHT, Direction.DOWN]:
                        self.sprites[direction].insert(0, frame)  # Original frames for right/down
                    else:  # LEFT, UP
                        flipped_frame = pygame.transform.flip(frame, True, False)
                        self.sprites[direction].insert(0, flipped_frame)  # Flipped for left/up

            # Optional: Store other actions for future use
            self.actions = actions

        except Exception as e:
            logger.error(f"Error loading adventurer sprites: {e}")
            self._create_fallback_sprites()

    def get_current_sprite(self):
        """Get the current sprite based on movement state with consistent sizing"""
        if not self.sprites:
            self.load_sprites()

        # Determine animation type and frame count
        if not self.is_moving:
            anim_offset = 0  # Start at the first idle frame (index 0)
            frame_count = 4  # Cycle through 4 idle frames
            delay = self.frame_delay_idle  # Use idle-specific delay
        else:
            anim_offset = 4  # Start at the first run frame (index 4, after 4 idle frames)
            frame_count = 6  # Cycle through 6 run frames
            delay = self.frame_delay_run  # Use run-specific delay

        # Update animation frame
        current_time = pygame.time.get_ticks()
        if current_time - self.last_frame_change > delay:
            self.animation_frame = (self.animation_frame + 1) % frame_count
            self.last_frame_change = current_time

        frame = self.sprites[self.direction][anim_offset + self.animation_frame]
        # Ensure frame size matches target size to prevent warping
        if frame.get_width() != self.width or frame.get_height() != self.height:
            frame = pygame.transform.scale(frame, (self.width, self.height))

        return frame

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
            if self.animation_frame in [1, 3, 5]:  # Left foot (adjust based on run animation frames)
                offset_x, offset_y = -foot_offset, foot_offset
            else:  # Right foot (adjust based on run animation frames)
                offset_x, offset_y = foot_offset, foot_offset
        else:  # Up/down
            if self.animation_frame in [1, 3, 5]:  # Left foot
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

    def handle_input(self, keys, game_map, events):
        """Handle keyboard input with improved physics-based movement"""
        # If in dialogue, set to idle
        if self.game_instance.dialogue_manager.is_active:
            self.is_moving = False
            self.vel_x = 0
            self.vel_y = 0
            return

        # Handle inventory events
        if self.show_inventory:
            self.inventory.handle_events(events)

            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left mouse button
                        mouse_pos = pygame.mouse.get_pos()
                        for item in self.inventory.items:
                            if item.icon.get_rect().collidepoint(mouse_pos):
                                self.inventory.start_drag(mouse_pos, item)
                                break
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:  # Left mouse button
                        self.inventory.end_drag(pygame.mouse.get_pos())

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


class Game:
    """Main game class"""

    def __init__(self):
        # Initialize pygame and screen
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Whispers of the Forgotten Vale")

        # Create game components
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_map = self._create_game_world()
        self.player = EnhancedPlayer("Adventurer", 500, 500, game_instance=self)
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.game_state = GameState()
        self.memory_system = PlayerMemorySystem()  # Initialize memory_system first
        self.dialogue_manager = EnhancedDialogueManager(self.memory_system, self)  # Now use it here
        self.inventory_ui = InventoryUI()
        self.hud = HUD()
        self.particle_system = ParticleSystem()
        self.sprite_manager = SpriteManager()
        self.header_font = pygame.font.SysFont('Arial', 18, bold=True)

        # Game flags
        self.paused = False

        # NPC interaction manager
        self.npc_interaction_manager = NPCInteractionManager()
        self.npc_observer = NPCObserverSystem(self.memory_system)  # Use memory_system here
        self.npc_display = NPCAttributesDisplay()
        self.npc_follower_system = NPCFollowerSystem()

        # Initialize all NPCs with following capability and game_map reference
        for npc in self.game_map.npcs:
            self.npc_follower_system.initialize_npc_following(npc)
            npc.game_map = self.game_map  # Add game_map reference to NPCs

    def toggle_npc_interactions(self, enable=None):
        """
        Toggle NPC interactions on or off.

        Args:
            enable (bool, optional):
                - If True, enable interactions
                - If False, disable interactions
                - If None, toggle current state

        Returns:
            bool: The new state of interactions (enabled or disabled)
        """
        result = self.npc_interaction_manager.toggle_interactions(enable)

        # Optional: Add a visual/audio feedback
        message = "NPC Interactions: " + ("Enabled" if result else "Disabled")
        print(message)  # Console output

        return result

    def _create_game_world(self):
        """Create a simplified game world with a single town square wrapped by walls"""
        map_width, map_height = SCREEN_WIDTH, SCREEN_HEIGHT
        game_map = GameMap(map_width, map_height)

        # Town square room
        town_square = Room("town_square", "Town Square", 0, 0, map_width, map_height, "A bustling town square.")
        town_square.floor_color = (200, 200, 180)
        game_map.add_room(town_square)

        # Animated fountain with larger visual size
        fountain_size = 180
        fountain_x = map_width // 2 - fountain_size // 2
        fountain_y = map_height // 2 - fountain_size // 2

        fountain = AnimatedFountain("fountain", "Central Fountain",
                                    fountain_x, fountain_y,
                                    fountain_size, fountain_size)
        print(f"Created fountain: {type(fountain)}")
        print(f"Fountain has update method: {hasattr(fountain, 'update')}")
        game_map.add_obstacle(fountain)

        # Check if it's in the obstacles list
        fountain_in_list = False
        for obs in game_map.obstacles:
            if isinstance(obs, AnimatedFountain):
                fountain_in_list = True
                print("Fountain is in the obstacles list!")
        print(f"Fountain in obstacles list: {fountain_in_list}")

        # Debug prints to confirm
        print("\nFountain Obstacle Details:")
        print(f"Fountain X: {fountain_x}")
        print(f"Fountain Y: {fountain_y}")
        print(f"Fountain Color: {fountain.color}")

        # Add walls around the entire map
        wall_thickness = 20
        walls = [
            Obstacle("north_wall", "North Wall", 0, 0, map_width, wall_thickness, color=(100, 100, 100)),
            Obstacle("south_wall", "South Wall", 0, map_height - wall_thickness, map_width, wall_thickness,
                     color=(100, 100, 100)),
            Obstacle("east_wall", "East Wall", map_width - wall_thickness, 0, wall_thickness, map_height,
                     color=(100, 100, 100)),
            Obstacle("west_wall", "West Wall", 0, 0, wall_thickness, map_height, color=(100, 100, 100))
        ]
        for wall in walls:
            game_map.add_obstacle(wall)

        # Add NPCs (unchanged)
        npcs = [
            NPC("merchant", "Galen the Merchant", 200, 200,
                personality="friendly",
                backstory="I've been trading goods in this square for 20 years.",
                location_id="town_square",
                color=YELLOW),
            NPC("elder", "Elder Miriam", map_width - 200, 200,
                personality="wise",
                backstory="I've watched over this town for more than three decades.",
                location_id="town_square",
                color=(138, 43, 226)),
            NPC("guard", "Guard Tom", 200, map_height - 200,
                personality="stern",
                backstory="I keep the peace in this square day and night.",
                location_id="town_square",
                color=(178, 34, 34)),
            NPC("artist", "Aria the Artist", map_width - 200, map_height - 200,
                personality="creative",
                backstory="I find inspiration for my art in the daily life of the square.",
                location_id="town_square",
                color=(34, 139, 34))
        ]
        for npc in npcs:
            game_map.add_npc(npc)

        # Fountain-specific NPCs (unchanged)
        # fountain_npcs = create_fountain_interaction_npcs(game_map, map_width, map_height)

        return game_map

    def _create_path(self, game_map, start_room, direction, end_room):
        """Create a path between two rooms"""
        start_x, start_y = start_room.get_center()
        end_x, end_y = end_room.get_center()

        path_width = 40
        if direction in ["north", "south"]:
            for y in range(min(start_y, end_y), max(start_y, end_y), 20):
                game_map.add_obstacle(Obstacle(f"path_{start_room.room_id}_{end_room.room_id}_{y}",
                                               "Path", start_x - path_width // 2, y, path_width, 20, (139, 69, 19)))
        else:
            for x in range(min(start_x, end_x), max(start_x, end_x), 20):
                game_map.add_obstacle(Obstacle(f"path_{start_room.room_id}_{end_room.room_id}_{x}",
                                               "Path", x, start_y - path_width // 2, 20, path_width, (139, 69, 19)))

    def _add_village_square_details(self, game_map, room):
        # Add central fountain
        fountain = Obstacle("fountain", "Grand Fountain", room.x + 200, room.y + 200, 100, 100, (100, 149, 237))
        game_map.add_obstacle(fountain)

        # Add market stalls
        for i in range(5):
            stall = Obstacle(f"stall_{i}", f"Market Stall {i + 1}",
                             room.x + 50 + i * 80, room.y + 50, 60, 40, (165, 42, 42))
            game_map.add_obstacle(stall)

        # Add benches
        for i in range(3):
            bench = Obstacle(f"bench_{i}", f"Bench {i + 1}",
                             room.x + 100 + i * 150, room.y + 400, 80, 30, (139, 69, 19))
            game_map.add_obstacle(bench)

    def _add_tavern_details(self, game_map, room):
        # Add bar counter
        bar = Obstacle("bar_counter", "Bar Counter", room.x + 50, room.y + 50, 300, 40, (101, 67, 33))
        game_map.add_obstacle(bar)

        # Add tables
        for i in range(4):
            table = Obstacle(f"table_{i}", f"Table {i + 1}",
                             room.x + 50 + (i % 2) * 150, room.y + 150 + (i // 2) * 100, 60, 60, (139, 69, 19))
            game_map.add_obstacle(table)

    def _add_blacksmith_details(self, game_map, room):
        # Add forge
        forge = Obstacle("forge", "Forge", room.x + 100, room.y + 100, 80, 80, (169, 169, 169))
        game_map.add_obstacle(forge)

        # Add anvil
        anvil = Obstacle("anvil", "Anvil", room.x + 200, room.y + 150, 40, 30, (105, 105, 105))
        game_map.add_obstacle(anvil)

        # Add weapon racks
        rack1 = Obstacle("weapon_rack_1", "Weapon Rack 1", room.x + 50, room.y + 200, 80, 30, (139, 69, 19))
        rack2 = Obstacle("weapon_rack_2", "Weapon Rack 2", room.x + 200, room.y + 50, 30, 80, (139, 69, 19))
        game_map.add_obstacle(rack1)
        game_map.add_obstacle(rack2)

    def _add_forest_details(self, game_map, forest_edge, deep_forest, hidden_glade):
        # Add trees to forest edge
        for _ in range(20):
            x = random.randint(forest_edge.x, forest_edge.x + forest_edge.width - 40)
            y = random.randint(forest_edge.y, forest_edge.y + forest_edge.height - 40)
            tree = Obstacle(f"tree_edge_{_}", "Tree", x, y, 40, 40, (0, 100, 0))
            game_map.add_obstacle(tree)

        # Add denser trees to deep forest
        for _ in range(30):
            x = random.randint(deep_forest.x, deep_forest.x + deep_forest.width - 50)
            y = random.randint(deep_forest.y, deep_forest.y + deep_forest.height - 50)
            tree = Obstacle(f"tree_deep_{_}", "Ancient Tree", x, y, 50, 50, (0, 60, 0))
            game_map.add_obstacle(tree)

        # Add mystical elements to hidden glade
        crystal = Obstacle("crystal", "Glowing Crystal", hidden_glade.x + 150, hidden_glade.y + 100, 30, 30,
                           (200, 230, 255))
        game_map.add_obstacle(crystal)

        for _ in range(5):
            x = random.randint(hidden_glade.x, hidden_glade.x + hidden_glade.width - 20)
            y = random.randint(hidden_glade.y, hidden_glade.y + hidden_glade.height - 20)
            mushroom = Obstacle(f"mushroom_{_}", "Glowing Mushroom", x, y, 20, 20, (255, 182, 193))
            game_map.add_obstacle(mushroom)

    def _add_farm_details(self, game_map, room):
        # Add farmhouse
        farmhouse = Obstacle("farmhouse", "Farmhouse", room.x + 50, room.y + 50, 150, 100, (210, 180, 140))
        game_map.add_obstacle(farmhouse)

        # Add crop rows
        for i in range(5):
            crop = Obstacle(f"crop_row_{i}", f"Crop Row {i + 1}",
                            room.x + 250, room.y + 50 + i * 60, 200, 40, (154, 205, 50))
            game_map.add_obstacle(crop)

        # Add barn
        barn = Obstacle("barn", "Barn", room.x + 300, room.y + 250, 120, 80, (165, 42, 42))
        game_map.add_obstacle(barn)

        # Add windmill
        windmill = Obstacle("windmill", "Windmill", room.x + 50, room.y + 250, 80, 80, (210, 180, 140))
        game_map.add_obstacle(windmill)

    # The _add_npcs and _add_items methods remain the same for now

    def run(self):
        """Main game loop"""
        while self.running:
            # Handle events
            self._handle_events()

            # Update game state if not paused
            if not self.paused and not self.dialogue_manager.is_active:
                self._update()  # This should call update for all objects including AnimatedFountain

            # Render everything
            self._render()  # This should call render for AnimatedFountain

            # Cap the frame rate
            self.clock.tick(60)

        # Clean up
        pygame.quit()
        sys.exit()

    def _handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            # When dialogue is active
            if self.dialogue_manager.is_active:
                current_time = pygame.time.get_ticks()
                self.dialogue_manager.handle_input(event, self.player, self.game_state, current_time)
                continue

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.inventory_ui.is_visible:
                        self.inventory_ui.toggle()
                    else:
                        self.paused = not self.paused

                elif event.key == pygame.K_i:
                    if not self.dialogue_manager.is_active:
                        self.player.show_inventory = not self.player.show_inventory  # Toggle inventory visibility
                        self.inventory_ui.toggle()

                elif event.key == pygame.K_e:
                    if not self.dialogue_manager.is_active and not self.inventory_ui.is_visible:
                        self._handle_interaction()

                elif event.key == pygame.K_n:
                    # Toggle NPC interactions with the 'N' key
                    self.toggle_npc_interactions()

    def _handle_interaction(self):
        nearest_npc = self.game_map.get_npc_near_position(
            self.player.x, self.player.y, INTERACTION_DISTANCE
        )

        if nearest_npc:
            current_time = pygame.time.get_ticks()
            location_id = self.player.current_location
            self.dialogue_manager.start_dialogue(nearest_npc, self.player, current_time, location_id)
            return

    def _update(self):
        """Update game state"""
        keys = pygame.key.get_pressed()
        events = pygame.event.get()  # Get the events
        self.player.handle_input(keys, self.game_map, events)  # Pass events to handle_input
        self.player.add_footstep_particle(self.game_state)
        self.particle_system.update()  # Update all particles

        # Update all NPCs
        for npc in self.game_map.npcs:
            npc.update(self.game_map, self.game_state, self.player)

        # Update animated obstacles (fountains)
        current_time = pygame.time.get_ticks()
        for obstacle in self.game_map.obstacles:
            if isinstance(obstacle, AnimatedFountain):
                obstacle.update(current_time)

        # Update camera to follow player
        self.camera.update(self.player.x, self.player.y,
                           self.game_map.width, self.game_map.height)
        self.game_state.update()

        # Update player's current location
        current_room = self.game_map.get_room_at_position(self.player.x, self.player.y)
        if current_room:
            self.player.current_location = current_room.room_id

        # Update NPC interactions
        self.npc_interaction_manager.update(self.game_map, self.game_state, current_time)
        self.npc_interaction_manager.update_conversations(self.game_state, current_time)

        current_time = pygame.time.get_ticks()
        self.npc_observer.update(self.game_map, self.player, current_time)
        self.dialogue_manager.update(current_time)

        # Update NPC following behavior
        current_time = pygame.time.get_ticks()
        for npc in self.game_map.npcs:
            self.npc_follower_system.update_following(npc, current_time)

        # Update NPC following behavior
        current_time = pygame.time.get_ticks()
        for npc in self.game_map.npcs:
            if hasattr(npc, 'follow_state') and npc.follow_state == NPCFollowState.FOLLOWING:
                print(f"Updating following for {npc.name}")  # Debug print
                self.npc_follower_system.update_following(npc, current_time)

        # Update other game state
        self.game_state.update()

        # Update player's current location
        current_room = self.game_map.get_room_at_position(self.player.x, self.player.y)
        if current_room:
            self.player.current_location = current_room.room_id

        # Update camera position
        self.camera.update(self.player.x, self.player.y,
                           self.game_map.width, self.game_map.height)

    def _render(self):
        """Render the game with optimized visual effects"""
        # Fill background
        self.screen.fill(BLACK)

        # Render map with enhanced visuals (rooms, paths, obstacles)
        self.game_map.render(self.screen, self.camera.x, self.camera.y)

        # Render player effects using centralized particle system
        self.player.render_trail(self.screen, self.camera.x, self.camera.y)
        self.particle_system.render(self.screen, self.camera.x, self.camera.y)
        self.player.render_shadow(self.screen, self.camera.x, self.camera.y)

        # Render animated obstacles (e.g., fountain)
        for obstacle in self.game_map.obstacles:
            if isinstance(obstacle, AnimatedFountain):
                obstacle.render(self.screen, self.camera.x, self.camera.y)

        # Render NPCs (shadows and sprites only, no attributes box yet)
        for npc in self.game_map.npcs:
            # Draw NPC shadow
            shadow_x = npc.x - self.camera.x + 4
            shadow_y = npc.y - self.camera.y + npc.height - 4
            shadow_width = npc.width - 8
            shadow_height = npc.height // 3
            shadow_rect = pygame.Rect(shadow_x, shadow_y, shadow_width, shadow_height)
            pygame.draw.ellipse(self.screen, (0, 0, 0, 60), shadow_rect)

            # Draw NPC sprite
            npc_sprite = npc.get_current_sprite()
            self.screen.blit(npc_sprite, (npc.x - self.camera.x, npc.y - self.camera.y))

        # Render player
        self.screen.blit(self.player.get_current_sprite(),
                         (self.player.x - self.camera.x, self.player.y - self.camera.y))

        # Render NPC interactions (speech bubbles)
        self.npc_interaction_manager.render(self.screen, self.camera.x, self.camera.y)

        # Optional: Add player lighting effect during dark times
        if self.game_state.time_of_day in [TimeOfDay.EVENING, TimeOfDay.NIGHT]:
            light_radius = self.player.light_radius
            light_surface = pygame.Surface((light_radius * 2, light_radius * 2), pygame.SRCALPHA)
            for r in range(light_radius, 0, -1):
                alpha = 0 if r > light_radius - 5 else min(180, int(180 * (1 - r / light_radius)))
                color = (255, 220, 150, alpha)  # Warm light color
                pygame.draw.circle(light_surface, color, (light_radius, light_radius), r)
            light_x = self.player.x - self.camera.x + self.player.width // 2 - light_radius
            light_y = self.player.y - self.camera.y + self.player.height // 2 - light_radius
            self.screen.blit(light_surface, (light_x, light_y), special_flags=pygame.BLEND_ADD)

        # Apply time of day color overlay
        time_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        time_overlay.fill(self.game_state.get_time_color_overlay())
        self.screen.blit(time_overlay, (0, 0))

        # Apply weather effects
        self.game_state.render_weather_effect(self.screen)

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

        # Render NPC attributes if nearby and not in dialogue
        current_time = pygame.time.get_ticks()
        for npc in self.game_map.npcs:
            if (self.player.distance_to(npc) < INTERACTION_DISTANCE * 1.5 and
                    not self.dialogue_manager.is_active):
                self.npc_display.render(self.screen, npc, self.camera.x, self.camera.y,
                                        INTERACTION_DISTANCE, current_time)

        # Update display
        pygame.display.flip()

    def _add_npcs(self, game_map):
        npcs = [
            NPC("merchant", "Galen the Merchant", 1300, 1300,
                personality="friendly,busy",
                backstory="I've been trading goods across the kingdom for 20 years.",
                location_id="village_square",
                items=["healing_potion", "map_fragment"],
                color=YELLOW),

            NPC("village_elder", "Elder Miriam", 1400, 1400,
                personality="wise,calm",
                backstory="I've watched over this village for more than three decades.",
                location_id="village_square",
                items=["ancient_coin"],
                color=(138, 43, 226)),  # Purple

            NPC("bartender", "Duran the Barkeep", 1050, 1800,
                personality="friendly,gossipy",
                backstory="I've been serving drinks and stories in this tavern for 15 years.",
                location_id="tavern",
                items=["ale_mug"],
                color=(210, 105, 30)),  # Chocolate

            NPC("mysterious_stranger", "The Stranger", 1100, 1900,
                personality="mysterious,reserved",
                backstory="Nobody knows where I came from, and I prefer to keep it that way.",
                location_id="tavern",
                items=["cryptic_note"],
                color=(75, 0, 130)),  # Indigo

            NPC("blacksmith", "Brenna Ironheart", 1800, 1350,
                personality="strong,skilled",
                backstory="I learned the art of metalworking from my father, and now I'm the best smith in the region.",
                location_id="blacksmith",
                items=["iron_dagger"],
                color=(178, 34, 34)),  # Firebrick red

            NPC("hunter", "Rowan the Hunter", 900, 850,
                personality="cautious,nature-lover",
                backstory="I've been tracking game and protecting travelers in these woods for years.",
                location_id="forest_edge",
                items=["animal_pelt"],
                color=(139, 69, 19)),  # Saddle brown

            NPC("forest_spirit", "Whisperleaf", 450, 450,
                personality="enigmatic,protective",
                backstory="I am an ancient spirit of the forest, rarely seen by mortal eyes.",
                location_id="deep_forest",
                color=(152, 251, 152)),  # Pale green

            NPC("druid", "Thorn the Druid", 350, 850,
                personality="wise,nature-attuned",
                backstory="I've devoted my life to studying and protecting the balance of nature in this forest.",
                location_id="hidden_glade",
                items=["healing_herb", "nature_tome"],
                color=(34, 139, 34)),  # Forest green

            NPC("farmer", "Eliza the Farmer", 1850, 1750,
                personality="hardworking,kind",
                backstory="My family has tended these fields for generations, providing food for the village.",
                location_id="farm",
                items=["fresh_produce"],
                color=(210, 180, 140))  # Tan
        ]

        for npc in npcs:
            game_map.add_npc(npc)

    def _add_items(self, game_map):
        items = [
            Item("silver_coin", "Silver Coin", 520, 530,
                 "A shiny silver coin with strange markings", value=10, color=LIGHT_GRAY),

            Item("rusty_key", "Rusty Key", 700, 840,
                 "An old, rusty key. It might open something nearby", value=5, color=BROWN),

            Item("iron_dagger", "Iron Dagger", 920, 520,
                 "A simple but effective iron dagger", value=20, color=(192, 192, 192)),  # Silver

            Item("mysterious_herb", "Mysterious Herb", 450, 150,
                 "An unusual herb with a sweet aroma", value=8, color=(173, 255, 47)),  # Green-yellow

            Item("healing_potion", "Healing Potion", 150, 200,
                 "A small vial of red liquid that restores health", value=15, color=(220, 20, 60)),  # Crimson

            Item("map_fragment", "Map Fragment", 180, 480,
                 "A torn piece of an old map", value=25, color=BEIGE),

            Item("apple", "Apple", 250, 800,
                 "A fresh, juicy apple", value=2, color=(255, 0, 0))  # Red
        ]

        for item in items:
            game_map.add_item(item)

    def _initialize_npcs(self):
        current_time = pygame.time.get_ticks()
        for npc in self.game_map.npcs:
            enhance_npc_with_memory(npc, self.memory_system, current_time)


# class AnimatedFountain(SpriteObstacle):
#     """A fountain with animated water effects using the isometric fountain spritesheet"""
#
#     def __init__(self, obstacle_id, name, x, y, visual_width, visual_height):
#         # Create a smaller collision box compared to the visual size
#         collision_width = visual_width // 2  # Half the visual width
#         collision_height = visual_height // 3  # Third of the visual height
#
#         # Adjust collision box position to be centered at the bottom of the sprite
#         collision_x = x + (visual_width - collision_width) // 2
#         collision_y = y + visual_height - collision_height
#
#         # Animation parameters - match your sprite sheet (4 columns, 3 rows)
#         self.frame_count = 4  # Columns in the sheet
#         self.row_count = 3  # Rows in the sheet
#         self.current_frame = 0
#         self.current_row = 0
#         self.animation_speed = 200  # Animation speed in milliseconds (slower for a serene fountain)
#         self.last_update = pygame.time.get_ticks()
#
#         # Visual size of the fountain (for rendering)
#         self.visual_width = visual_width
#         self.visual_height = visual_height
#         self.visual_x = x
#         self.visual_y = y
#
#         # Load the spritesheet and pre-load all frames
#         try:
#             sprite_path = os.path.join('sprites', 'obstacles', 'fountain.png')
#             if not os.path.exists(sprite_path):
#                 print(f"Warning: Fountain sprite not found at {sprite_path}")
#                 self.spritesheet = None
#                 self.frames = [self._create_fallback_sprite()]
#             else:
#                 self.spritesheet = pygame.image.load(sprite_path).convert_alpha()
#                 self.frames = []
#                 for row in range(self.row_count):
#                     for col in range(self.frame_count):
#                         self.frames.append(self.get_frame(row, col))
#
#             # Initialize the obstacle with the smaller collision box
#             super().__init__(obstacle_id, name, collision_x, collision_y,
#                              collision_width, collision_height,
#                              color=(100, 180, 255), sprite=None)
#
#             # Set initial visual sprite
#             self.visual_sprite = self.frames[0]
#
#         except Exception as e:
#             print(f"Error initializing animated fountain: {e}")
#             self.frames = [self._create_fallback_sprite()]
#             self.visual_sprite = self.frames[0]
#             super().__init__(obstacle_id, name, collision_x, collision_y,
#                              collision_width, collision_height,
#                              color=(100, 180, 255), sprite=None)
#
#     def _create_fallback_sprite(self):
#         """Create a fallback sprite if the spritesheet can't be loaded"""
#         fallback = pygame.Surface((self.visual_width, self.visual_height), pygame.SRCALPHA)
#         pygame.draw.ellipse(fallback, (150, 150, 150),
#                             (0, self.visual_height // 2, self.visual_width, self.visual_height // 2))
#         pygame.draw.ellipse(fallback, (100, 180, 255), (
#         self.visual_width // 4, self.visual_height // 3, self.visual_width // 2, self.visual_height // 3))
#         return fallback
#
#     def get_frame(self, row, frame_index):
#         """Extract a frame from the spritesheet"""
#         if not self.spritesheet:
#             return self._create_fallback_sprite()
#
#         # Calculate frame dimensions
#         frame_width = self.spritesheet.get_width() // self.frame_count
#         frame_height = self.spritesheet.get_height() // self.row_count
#
#         # Create a surface for the frame
#         frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
#         frame.blit(self.spritesheet, (0, 0),
#                    (frame_index * frame_width, row * frame_height,
#                     frame_width, frame_height))
#
#         # Scale to desired size
#         return pygame.transform.scale(frame, (self.visual_width, self.visual_height))
#
#     def update(self, current_time):
#         """Update the animation frame"""
#         if not self.frames:
#             return
#
#         time_since_last_update = current_time - self.last_update
#         if time_since_last_update > self.animation_speed:
#             self.current_frame = (self.current_frame + 1) % self.frame_count
#             if self.current_frame == 0:
#                 self.current_row = (self.current_row + 1) % self.row_count
#             self.visual_sprite = self.frames[self.current_row * self.frame_count + self.current_frame]
#             self.last_update = current_time
#
#     def render(self, surface, camera_x, camera_y):
#         """Render the fountain at its visual position"""
#         visual_x = self.visual_x - camera_x
#         visual_y = self.visual_y - camera_y
#
#         if self.visual_sprite:
#             surface.blit(self.visual_sprite, (visual_x, visual_y))
#
#         # Optional: Draw collision box for debugging
#         if ENABLE_PIXEL_PERFECT_COLLISION:
#             collision_rect = pygame.Rect(self.x - camera_x, self.y - camera_y,
#                                          self.width, self.height)
#             pygame.draw.rect(surface, (255, 0, 0, 50), collision_rect, 1)


class AnimatedFountain(SpriteObstacle):
    def __init__(self, obstacle_id, name, x, y, visual_width, visual_height):
        """
        Initialize an animated fountain with a properly loaded spritesheet.

        Args:
            obstacle_id (str): Unique identifier for the obstacle
            name (str): Name of the fountain
            x (int): X-coordinate position
            y (int): Y-coordinate position
            visual_width (int): Width for rendering
            visual_height (int): Height for rendering
        """
        # Store visual dimensions as instance variables
        self.visual_width = visual_width
        self.visual_height = visual_height

        # Create a smaller collision box for better player movement around the fountain
        collision_width = visual_width * 0.6
        collision_height = visual_height * 0.6
        collision_x = x + (visual_width - collision_width) / 2
        collision_y = y + (visual_height - collision_height) / 2

        # Call parent constructor with collision dimensions
        super().__init__(obstacle_id, name, collision_x, collision_y,
                         collision_width, collision_height,
                         color=(100, 180, 255), sprite=None)

        # Visual position (for rendering)
        self.visual_x = x
        self.visual_y = y

        # Animation parameters
        self.sprite_manager = SpriteManager()
        self.animation_speed = 150  # milliseconds between frame changes
        self.last_update = pygame.time.get_ticks()
        self.current_frame = 0

        # Load the spritesheet
        try:
            logger.debug(f"Loading fountain spritesheet")
            sprite_path = 'obstacles/fountain.png'

            # Define expected grid layout for the fountain (2x3 grid)
            cols, rows = 2, 3

            # Load all frames from the spritesheet
            self.frames = self.sprite_manager.load_sprite_sheet(
                sprite_path, cols, rows, (visual_width, visual_height),
                padding_x=2, padding_y=0  # Adjust padding based on your spritesheet layout
            )

            # Log successful loading
            logger.debug(f"Successfully loaded {len(self.frames)} fountain frames")

            # If no frames were loaded, create fallback
            if not self.frames:
                logger.error("No frames loaded for fountain animation")
                self.frames = [self._create_fallback_frame()]
        except Exception as e:
            logger.error(f"Error loading fountain spritesheet: {e}")
            self.frames = [self._create_fallback_frame()]

    def _create_fallback_frame(self):
        """Create a better-looking fallback frame if loading fails"""
        fallback = pygame.Surface((self.visual_width, self.visual_height), pygame.SRCALPHA)

        # Draw a nicer looking fountain shape instead of a red block
        # Base/stone part
        stone_color = (150, 150, 150)
        pygame.draw.ellipse(fallback, stone_color,
                            (10, self.visual_height * 0.6,
                             self.visual_width - 20, self.visual_height * 0.3))

        # Water basin
        basin_color = (100, 180, 255, 200)
        pygame.draw.ellipse(fallback, basin_color,
                            (self.visual_width * 0.25, self.visual_height * 0.5,
                             self.visual_width * 0.5, self.visual_height * 0.2))

        # Center pillar
        pygame.draw.rect(fallback, stone_color,
                         (self.visual_width * 0.45, self.visual_height * 0.3,
                          self.visual_width * 0.1, self.visual_height * 0.3))

        # Top water spray
        water_color = (150, 200, 255, 180)
        pygame.draw.ellipse(fallback, water_color,
                            (self.visual_width * 0.4, self.visual_height * 0.2,
                             self.visual_width * 0.2, self.visual_height * 0.15))

        return fallback

    def update(self, current_time):
        """Update the animation frame"""
        if not self.frames:
            return

        # Update animation frame
        if current_time - self.last_update > self.animation_speed:
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.last_update = current_time

    def render(self, surface, camera_x, camera_y):
        """Render the fountain at its visual position"""
        if not self.frames:
            logger.error("No frames available for fountain rendering")
            return

        # Ensure current_frame is within bounds
        if self.current_frame >= len(self.frames):
            self.current_frame = 0

        # Get current animation frame
        try:
            frame = self.frames[self.current_frame]

            # Calculate position adjusted for camera
            visual_x = self.visual_x - camera_x
            visual_y = self.visual_y - camera_y

            # Render the fountain
            surface.blit(frame, (visual_x, visual_y))

            # Debug: Draw collision box if debugging is enabled
            if __debug__:
                collision_rect = pygame.Rect(
                    self.x - camera_x, self.y - camera_y,
                    self.width, self.height
                )
                pygame.draw.rect(surface, (255, 0, 0, 50), collision_rect, 1)

        except Exception as e:
            logger.error(f"Error rendering fountain frame {self.current_frame}: {e}")


def get_hf_token():
    """
    Retrieve Hugging Face API token securely.
    Recommend storing this in an environment variable.
    """

    token = os.environ.get('HUGGINGFACE_API_TOKEN')
    if not token:
        raise ValueError("""
        Hugging Face API Token not found. 
        Set it as an environment variable:
        export HF_API_TOKEN='your_actual_token_here'
        """)
    return token


def query_local_model(npc, environment_state, player_message):
    """
    Generate contextually appropriate NPC dialogue using Hugging Face's API.
    Debug version with print statements to track farewell detection.
    """
    try:
        print(f"Analyzing message: {player_message}")  # Debug print

        # Check for basic farewell words first
        basic_farewell_words = {"goodbye", "bye", "farewell", "leave", "see you", "later", "take care"}
        basic_farewell = any(word in player_message.lower() for word in basic_farewell_words)
        print(f"Basic farewell check: {basic_farewell}")  # Debug print

        # Construct a detailed prompt for the language model
        prompt = f"""You are {npc.name}, an NPC in a fantasy game with the following characteristics:
        Personality: {npc.personality}
        Backstory: {npc.backstory}
        Current Environment: {environment_state}

        The player says: "{player_message}"

        First, determine if this is some form of goodbye/farewell message.
        Then provide your response in exactly this format:
        IS_FAREWELL: YES or NO
        FRIENDSHIP_ADJUSTMENT: <number>
        RESPONSE: <your in-character response>
        """

        # Initialize the inference client with Hugging Face API
        client = InferenceClient(
            model="mistralai/Mistral-7B-Instruct-v0.2",
            token=get_hf_token()
        )

        # Generate response
        full_response = client.text_generation(
            prompt,
            max_new_tokens=150,
            temperature=0.7,
            do_sample=True,
            return_full_text=False
        )

        # Clean and parse the response
        clean_response = full_response.strip()
        print(f"Raw model response: {clean_response}")  # Debug print

        # Parse the components
        is_farewell = False
        friendship_adjustment = 0
        dialogue_response = ""

        # Extract parts from the response
        for line in clean_response.split('\n'):
            line = line.strip()
            if line.startswith('IS_FAREWELL:'):
                is_farewell = line.replace('IS_FAREWELL:', '').strip().upper() == 'YES'
                print(f"NLP farewell detection: {is_farewell}")  # Debug print
            elif line.startswith('FRIENDSHIP_ADJUSTMENT:'):
                try:
                    friendship_adjustment = int(line.replace('FRIENDSHIP_ADJUSTMENT:', '').strip())
                except ValueError:
                    friendship_adjustment = 0
            elif line.startswith('RESPONSE:'):
                dialogue_response = line.replace('RESPONSE:', '').strip()

        # If no structured response found, handle the raw text
        if not dialogue_response:
            dialogue_response = clean_response

        # Use basic farewell detection as fallback
        is_farewell = is_farewell or basic_farewell
        print(f"Final farewell status: {is_farewell}")  # Debug print

        # If it's a farewell, ensure the response is a goodbye
        if is_farewell and not any(word in dialogue_response.lower() for word in basic_farewell_words):
            dialogue_response += " Farewell, safe travels!"

        # Clean the response text (remove quotes if present)
        clean_response = dialogue_response.strip('"')

        # Set floating text for farewell
        if is_farewell:
            print(f"Setting floating text: {clean_response}")  # Debug print
            npc.set_floating_text(clean_response, 5000)  # 5 seconds

        # Update the NPC's friendship meter
        npc.update_friendship(friendship_adjustment)

        print(
            f"Returning: response='{dialogue_response}', adjustment={friendship_adjustment}, farewell={is_farewell}")  # Debug print
        return dialogue_response, friendship_adjustment, is_farewell

    except Exception as e:
        logger.error(f"NLP Dialogue Generation Error: {e}")
        # Fallback
        print(f"Error in query_local_model: {e}")  # Debug print
        basic_farewell = any(word in player_message.lower() for word in ["goodbye", "bye", "farewell", "leave"])
        return f"I'm sorry, I'm having trouble understanding.", 0, basic_farewell


# Expose the function for use in the dialogue system
def simulate_npc_response(npc, environment_state, player_message):
    """Wrapper to handle any potential exceptions"""
    try:
        return query_local_model(npc, environment_state, player_message)
    except Exception as e:
        print(f"Dialogue generation failed: {e}")
        return f"Hello, I'm {npc.name}. I'm afraid I can't quite understand you right now."


#############
# INVENTORY #
#############

class InventoryItem:
    def __init__(self, item_id, name, description, value, weight, category, icon=None):
        self.item_id = item_id
        self.name = name
        self.description = description
        self.value = value
        self.weight = weight
        self.category = category
        self.icon = icon or self._create_default_icon()
        self.quantity = 1

    def _create_default_icon(self):
        icon = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.rect(icon, (150, 150, 150), (0, 0, 32, 32))
        return icon

class EnhancedInventory:
    def __init__(self, capacity=100.0):
        self.items = []
        self.max_capacity = capacity
        self.current_weight = 0.0
        self.selected_item = None
        self.drag_offset = None

    def add_item(self, item):
        if self.current_weight + item.weight > self.max_capacity:
            return False

        for inv_item in self.items:
            if inv_item.item_id == item.item_id:
                inv_item.quantity += item.quantity
                self.current_weight += item.weight
                return True

        self.items.append(item)
        self.current_weight += item.weight
        return True

    def remove_item(self, item):
        if item in self.items:
            self.items.remove(item)
            self.current_weight -= (item.weight * item.quantity)
            return True
        return False

    def start_drag(self, mouse_pos, item):
        self.selected_item = item
        self.drag_offset = (mouse_pos[0] - item.icon.get_rect().x,
                            mouse_pos[1] - item.icon.get_rect().y)

    def end_drag(self, mouse_pos):
        self.selected_item = None
        self.drag_offset = None

    def render(self, surface):
        for i, item in enumerate(self.items):
            x = 50 + (i % 5) * 60
            y = 50 + (i // 5) * 60
            surface.blit(item.icon, (x, y))

            if item.quantity > 1:
                font = pygame.font.SysFont('Arial', 12)
                qty_text = font.render(str(item.quantity), True, (255, 255, 255))
                surface.blit(qty_text, (x + 20, y + 20))

        if self.selected_item and self.drag_offset:
            mouse_pos = pygame.mouse.get_pos()
            surface.blit(self.selected_item.icon,
                         (mouse_pos[0] - self.drag_offset[0],
                          mouse_pos[1] - self.drag_offset[1]))

    def __iter__(self):
        """Make the inventory iterable by returning an iterator over the items."""
        return iter(self.items)


###########
# Trading #
###########
class TradeManager:
    def __init__(self, base_markup: float = 1.2):
        self.base_markup = base_markup  # Default markup percentage

    def calculate_item_price(self, item: InventoryItem,
                             buyer_reputation: float = 1.0,
                             seller_reputation: float = 1.0) -> float:
        """
        Calculate dynamic pricing based on item value and reputations

        Args:
            item (InventoryItem): Item being priced
            buyer_reputation (float): Buyer's reputation modifier
            seller_reputation (float): Seller's reputation modifier

        Returns:
            float: Calculated item price
        """
        base_price = item.value
        markup = self.base_markup

        # Adjust price based on reputations
        markup *= (buyer_reputation + seller_reputation) / 2

        return base_price * markup


def create_sample_items():
    """Create a set of sample inventory items"""
    return [
        InventoryItem(
            item_id="sword_01",
            name="Iron Sword",
            description="A basic iron sword",
            value=50.0,
            weight=2.5,
            category="weapon"
        ),
        InventoryItem(
            item_id="health_potion",
            name="Health Potion",
            description="Restores 50 HP",
            value=25.0,
            weight=0.5,
            category="consumable",
            quantity=3
        ),
        InventoryItem(
            item_id="leather_armor",
            name="Leather Armor",
            description="Light protective armor",
            value=75.0,
            weight=3.0,
            category="armor"
        )
    ]


class TradeUI:
    def __init__(self, player, npc):
        self.player = player
        self.npc = npc
        self.trade_manager = TradeManager()
        self.visible = False

    def toggle_visibility(self):
        self.visible = not self.visible

    def update(self, events):
        if not self.visible:
            return

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    mouse_pos = pygame.mouse.get_pos()
                    for item in self.player.inventory.items + self.npc.inventory.items:
                        if item.icon.get_rect().collidepoint(mouse_pos):
                            if item in self.player.inventory.items:
                                self.player.inventory.start_drag(mouse_pos, item)
                            else:
                                self.npc.inventory.start_drag(mouse_pos, item)
                            break
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Left mouse button
                    mouse_pos = pygame.mouse.get_pos()
                    if self.player.inventory.selected_item:
                        if self.npc_inventory_rect.collidepoint(mouse_pos):
                            self.trade_items(self.player.inventory.selected_item, self.player.inventory,
                                             self.npc.inventory)
                        self.player.inventory.end_drag(mouse_pos)
                    elif self.npc.inventory.selected_item:
                        if self.player_inventory_rect.collidepoint(mouse_pos):
                            self.trade_items(self.npc.inventory.selected_item, self.npc.inventory,
                                             self.player.inventory)
                        self.npc.inventory.end_drag(mouse_pos)

    def trade_items(self, item, from_inventory, to_inventory):
        buy_price = self.trade_manager.calculate_buy_price(item)
        sell_price = self.trade_manager.calculate_sell_price(item)

        if from_inventory == self.player.inventory:  # Player selling
            if self.player.gold + sell_price > self.player.max_gold:
                return  # Player doesn't have enough gold capacity

            self.player.inventory.remove_item(item)
            self.npc.inventory.add_item(item)
            self.player.gold += sell_price
            self.npc.gold -= sell_price
        else:  # Player buying
            if self.player.gold < buy_price:
                return  # Player can't afford item

            self.npc.inventory.remove_item(item)
            self.player.inventory.add_item(item)
            self.player.gold -= buy_price
            self.npc.gold += buy_price

    def render(self, surface):
        if not self.visible:
            return

        player_inv_x = 100
        player_inv_y = 100
        npc_inv_x = 400
        npc_inv_y = 100

        self.player_inventory_rect = pygame.Rect(player_inv_x, player_inv_y, 300, 400)
        self.npc_inventory_rect = pygame.Rect(npc_inv_x, npc_inv_y, 300, 400)

        pygame.draw.rect(surface, (50, 50, 50), self.player_inventory_rect)
        pygame.draw.rect(surface, (50, 50, 50), self.npc_inventory_rect)

        for i, item in enumerate(self.player.inventory.items):
            x = player_inv_x + 20 + (i % 5) * 60
            y = player_inv_y + 20 + (i // 5) * 60
            surface.blit(item.icon, (x, y))

            price = self.trade_manager.calculate_sell_price(item)
            price_text = self.font.render(f"{price}g", True, (255, 255, 255))
            surface.blit(price_text, (x, y + 40))

        for i, item in enumerate(self.npc.inventory.items):
            x = npc_inv_x + 20 + (i % 5) * 60
            y = npc_inv_y + 20 + (i // 5) * 60
            surface.blit(item.icon, (x, y))

            price = self.trade_manager.calculate_buy_price(item)
            price_text = self.font.render(f"{price}g", True, (255, 255, 255))
            surface.blit(price_text, (x, y + 40))

        player_gold_text = self.font.render(f"Player Gold: {self.player.gold}", True, (255, 255, 255))
        npc_gold_text = self.font.render(f"{self.npc.name}'s Gold: {self.npc.gold}", True, (255, 255, 255))
        surface.blit(player_gold_text, (player_inv_x, player_inv_y - 30))
        surface.blit(npc_gold_text, (npc_inv_x, npc_inv_y - 30))

        if self.player.inventory.selected_item:
            mouse_pos = pygame.mouse.get_pos()
            surface.blit(self.player.inventory.selected_item.icon,
                         (mouse_pos[0] - self.player.inventory.drag_offset[0],
                          mouse_pos[1] - self.player.inventory.drag_offset[1]))
        elif self.npc.inventory.selected_item:
            mouse_pos = pygame.mouse.get_pos()
            surface.blit(self.npc.inventory.selected_item.icon,
                         (mouse_pos[0] - self.npc.inventory.drag_offset[0],
                          mouse_pos[1] - self.npc.inventory.drag_offset[1]))