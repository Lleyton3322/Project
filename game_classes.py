import pygame
import math
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional
import random
import textwrap
import os
import sys
from pygame import gfxdraw

# Constants needed by GameMap
TILE_SIZE = 64
DARK_GRAY = (70, 70, 70)
WHITE = (255, 255, 255)
BROWN = (139, 69, 19)

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


class TimeOfDay(Enum):
    MORNING = 0
    AFTERNOON = 1
    EVENING = 2
    NIGHT = 3


class Weather(Enum):
    CLEAR = 0
    CLOUDY = 1
    RAINY = 2
    FOGGY = 3
    STORMY = 4


class Direction(Enum):
    UP = 0
    RIGHT = 1
    DOWN = 2
    LEFT = 3

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

    def move(self, dx: int, dy: int, game_map: 'GameMap') -> bool:
        """Move the entity if there's no collision"""
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
        """Render the entire map"""
        # Draw rooms
        for room in self.rooms:
            room_rect = pygame.Rect(
                room.x - camera_x,
                room.y - camera_y,
                room.width,
                room.height
            )
            pygame.draw.rect(surface, room.floor_color, room_rect)
            pygame.draw.rect(surface, DARK_GRAY, room_rect, 3)  # Border

        # Draw obstacles
        for obstacle in self.obstacles:
            obstacle_rect = pygame.Rect(
                obstacle.x - camera_x,
                obstacle.y - camera_y,
                obstacle.width,
                obstacle.height
            )
            pygame.draw.rect(surface, obstacle.color, obstacle_rect)

        # Draw items
        for item in self.items:
            if not item.is_collected:
                item_rect = pygame.Rect(
                    item.x - camera_x,
                    item.y - camera_y,
                    item.width,
                    item.height
                )
                pygame.draw.rect(surface, item.color, item_rect)
                # Add shine effect
                shine_size = min(item.width, item.height) // 3
                shine_pos = (
                    item.x - camera_x + item.width // 4,
                    item.y - camera_y + item.height // 4
                )
                pygame.draw.circle(surface, WHITE, shine_pos, shine_size)







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
        return (self.x + self.width // 2, self.y + self.height // 2)


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


class DialogueManager:
    """Manages NPC dialogue"""

    def __init__(self):
        self.is_active = False
        self.current_npc = None
        self.dialogue_history = []
        self.player_input = ""
        self.font = pygame.font.SysFont('Arial', FONT_SIZE)
        self.input_active = False

    def start_dialogue(self, npc):
        """Start dialogue with an NPC"""
        self.is_active = True
        self.current_npc = npc
        self.dialogue_history = []
        self.player_input = ""
        self.input_active = True

        # Add greeting
        greeting = npc.simulate_npc_response(
            {"time_of_day": TimeOfDay.MORNING, "weather": Weather.CLEAR},
            "hello"
        )
        self.dialogue_history.append({"speaker": "npc", "text": greeting})

        # Mark NPC as talking
        npc.is_talking = True

    def end_dialogue(self):
        """End the current dialogue"""
        if self.current_npc:
            self.current_npc.is_talking = False
        self.is_active = False
        self.current_npc = None
        self.input_active = False

    def handle_input(self, event, game_state):
        """Handle input in dialogue mode"""
        if not self.is_active or not self.input_active:
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if self.player_input.strip():
                    # Add player input to history
                    self.dialogue_history.append({"speaker": "player", "text": self.player_input})

                    # Get NPC response
                    if self.current_npc:
                        response = self.current_npc.simulate_npc_response(
                            game_state.get_environment_state(self.current_npc.location_id),
                            self.player_input
                        )
                        self.dialogue_history.append({"speaker": "npc", "text": response})

                    # Clear input
                    self.player_input = ""

                    # End dialogue on "goodbye"
                    if any(word in self.player_input.lower() for word in ["goodbye", "bye", "farewell", "leave"]):
                        self.end_dialogue()

            elif event.key == pygame.K_BACKSPACE:
                self.player_input = self.player_input[:-1]
            elif event.key == pygame.K_ESCAPE:
                self.end_dialogue()
            else:
                # Add character to input
                if len(self.player_input) < 50:  # Limit input length
                    self.player_input += event.unicode

    def render(self, surface):
        """Render dialogue UI"""
        if not self.is_active:
            return

        width, height = surface.get_size()

        # Create dialogue box
        dialogue_height = height // 3
        dialogue_y = height - dialogue_height
        dialogue_box = pygame.Rect(0, dialogue_y, width, dialogue_height)

        # Draw semi-transparent background
        dialogue_surface = pygame.Surface((width, dialogue_height), pygame.SRCALPHA)
        dialogue_surface.fill((0, 0, 0, 200))  # Semi-transparent black
        surface.blit(dialogue_surface, (0, dialogue_y))

        # Draw border
        pygame.draw.rect(surface, WHITE, dialogue_box, 2)

        # Get NPC name if available
        npc_name = self.current_npc.name if self.current_npc else "NPC"

        # Show dialogue history
        history_y = dialogue_y + 10
        visible_history = self.dialogue_history[-4:] if len(self.dialogue_history) > 4 else self.dialogue_history

        for entry in visible_history:
            speaker = entry["speaker"]
            text = entry["text"]

            # Determine text color and speaker name
            if speaker == "player":
                text_color = LIGHT_BLUE
                display_name = "You"
            else:
                text_color = YELLOW
                display_name = npc_name

            # Render speaker name
            name_surface = self.font.render(f"{display_name}:", True, text_color)
            surface.blit(name_surface, (DIALOG_PADDING, history_y))

            # Wrap and render dialogue text
            wrapped_text = textwrap.wrap(text, width=100)
            text_y = history_y + self.font.get_height()

            for line in wrapped_text:
                text_surface = self.font.render(line, True, WHITE)
                surface.blit(text_surface, (DIALOG_PADDING + 20, text_y))
                text_y += self.font.get_height()

            history_y = text_y + 10

        # Draw input box if active
        if self.input_active:
            input_box = pygame.Rect(
                DIALOG_PADDING,
                dialogue_y + dialogue_height - 40,
                width - (DIALOG_PADDING * 2),
                30
            )
            pygame.draw.rect(surface, DARK_GRAY, input_box)
            pygame.draw.rect(surface, WHITE, input_box, 1)

            # Render current input
            input_surface = self.font.render(self.player_input, True, WHITE)
            surface.blit(input_surface, (input_box.x + 5, input_box.y + 5))

            # Draw blinking cursor
            if pygame.time.get_ticks() % 1000 < 500:
                cursor_x = input_box.x + 5 + self.font.size(self.player_input)[0]
                cursor_y = input_box.y + 5
                pygame.draw.line(
                    surface,
                    WHITE,
                    (cursor_x, cursor_y),
                    (cursor_x, cursor_y + self.font.get_height()),
                    1
                )


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

    def get_weather_effect(self, surface):
        """Apply weather effects to the screen"""
        if self.weather == Weather.CLEAR:
            return  # No effect

        width, height = surface.get_size()
        weather_surface = pygame.Surface((width, height), pygame.SRCALPHA)

        if self.weather == Weather.CLOUDY:
            # Add slight gray overlay
            weather_surface.fill((200, 200, 200, 40))

        elif self.weather == Weather.RAINY:
            # Add blue-gray overlay and rain drops
            weather_surface.fill((100, 100, 150, 60))
            # Draw rain drops
            for _ in range(100):
                x = random.randint(0, width)
                y = random.randint(0, height)
                length = random.randint(5, 15)
                pygame.draw.line(weather_surface, (200, 200, 255, 150),
                                 (x, y), (x - 2, y + length), 1)

        elif self.weather == Weather.FOGGY:
            # Add white fog
            weather_surface.fill((255, 255, 255, 100))

        elif self.weather == Weather.STORMY:
            # Dark overlay with occasional lightning
            weather_surface.fill((50, 50, 70, 100))
            # Random lightning flash
            if random.random() < 0.02:  # 2% chance per frame
                flash = pygame.Surface((width, height), pygame.SRCALPHA)
                flash.fill((255, 255, 255, 100))
                weather_surface.blit(flash, (0, 0))

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


class Obstacle(Entity):
    """Impassable obstacle"""

    def __init__(self, obstacle_id: str, name: str, x: int, y: int,
                 width: int, height: int,
                 color: Tuple[int, int, int] = BROWN):
        super().__init__(obstacle_id, name, x, y, width, height,
                         color, EntityType.OBSTACLE)


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

        # Interaction prompt if near an NPC or item
        nearest_npc = game_map.get_npc_near_position(
            player.x, player.y, INTERACTION_DISTANCE
        )
        nearest_items = game_map.get_items_near_position(
            player.x, player.y, INTERACTION_DISTANCE
        )

        if nearest_npc or nearest_items:
            prompt_y = bottom_bar_y - 40
            prompt_text = "Press E to "

            if nearest_npc:
                prompt_text += f"talk to {nearest_npc.name}"
            elif nearest_items:
                item_names = [item.name for item in nearest_items[:3]]
                if len(nearest_items) > 3:
                    item_names.append("...")
                prompt_text += f"pick up {', '.join(item_names)}"

            prompt_surface = self.font.render(prompt_text, True, WHITE)
            # Add background for better readability
            prompt_bg_rect = prompt_surface.get_rect()
            prompt_bg_rect.center = (width // 2, prompt_y)
            prompt_bg_rect.inflate_ip(20, 10)

            prompt_bg = pygame.Surface(prompt_bg_rect.size, pygame.SRCALPHA)
            prompt_bg.fill((0, 0, 0, 180))
            surface.blit(prompt_bg, prompt_bg_rect)

            # Draw actual prompt centered
            prompt_rect = prompt_surface.get_rect()
            prompt_rect.center = (width // 2, prompt_y)
            surface.blit(prompt_surface, prompt_rect)


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


class NPC(MovingEntity):
    """NPC with personality and AI behavior"""

    def __init__(self, entity_id: str, name: str, x: int, y: int,
                 personality: str, backstory: str, location_id: str,
                 items: List[str] = None, color: Tuple[int, int, int] = YELLOW):
        super().__init__(entity_id, name, x, y, TILE_SIZE, TILE_SIZE,
                         color=color, entity_type=EntityType.NPC)
        self.personality = personality
        self.backstory = backstory
        self.location_id = location_id
        self.items = items or []
        self.memory = []
        self.mood = self._get_default_mood()
        self.behavior_state = "idle"
        self.idle_timer = 0
        self.wandering_timer = 0
        self.dialogue_options = self._generate_dialogue_options()
        self.last_action_time = 0
        self.action_cooldown = 5000  # 5 seconds between autonomous actions
        self.sprites = {}
        self.animation_frame = 0
        self.last_frame_change = 0
        self.frame_delay = 200  # NPCs animate slower than player
        self.is_talking = False

    def _get_default_mood(self):
        """Set default mood based on personality"""
        mood_map = {
            "friendly": "cheerful",
            "cautious": "wary",
            "wise": "contemplative",
            "mysterious": "guarded",
            "aggressive": "irritable",
            "mischievous": "playful"
        }
        return mood_map.get(self.personality, "neutral")

    def _generate_dialogue_options(self):
        """Generate dialogue options based on personality"""
        dialogue = {
            "friendly": {
                "greeting": [
                    "Hello there! Lovely day, isn't it?",
                    "Welcome, traveler! How can I help you today?",
                    "Oh, hello! It's so nice to see a new face around here!"
                ],
                "farewell": [
                    "Safe travels, friend!",
                    "Do come back soon!",
                    "It was wonderful chatting with you!"
                ],
                "about_village": [
                    "Our little village is peaceful and welcoming. Everyone looks out for each other here.",
                    "You'll find all sorts of interesting folk in our village. Have you visited the tavern yet?"
                ]
            },
            "cautious": {
                "greeting": [
                    "Yes? What do you want?",
                    "Hmm... another stranger. What brings you here?",
                    "*nods silently*"
                ],
                "farewell": [
                    "Watch yourself out there.",
                    "Be careful where you step.",
                    "Mind you don't bring any trouble back with you."
                ],
                "about_village": [
                    "It's peaceful enough, as long as you stay away from the forest after dark.",
                    "We keep to ourselves mostly. Safer that way."
                ]
            },
            # More personality types with dialogue options...
            "wise": {
                "greeting": [
                    "Ah, a seeker walks among us. What wisdom do you pursue?",
                    "The path brings another traveler. What journey calls to you?",
                    "I sense purpose in your steps. What brings you to our humble corner of the world?"
                ],
                "farewell": [
                    "May your path be clear and your heart steady.",
                    "Remember, the answer you seek often lies within.",
                    "Until our paths cross again, walk with wisdom."
                ],
                "about_village": [
                    "This village has stood for generations, each stone holding memories of those who came before.",
                    "There is much history here, for those patient enough to listen."
                ]
            },
            "mysterious": {
                "greeting": [
                    "*watches you with piercing eyes* You're not from around here...",
                    "Interesting... the shadows spoke of your arrival.",
                    "*smiles enigmatically* So, it begins."
                ],
                "farewell": [
                    "Our paths will cross again... when the time is right.",
                    "*whispers* Remember what I told you when the moon is full...",
                    "The answers you seek lie beyond the veil of the ordinary."
                ],
                "about_village": [
                    "This village harbors secrets. Listen closely to the whispers in the wind.",
                    "Not all is as it seems here. Watch carefully who you trust."
                ]
            },
            "aggressive": {
                "greeting": [
                    "What are you looking at?",
                    "*scowls* Another outsider. Great.",
                    "Keep your distance if you know what's good for you."
                ],
                "farewell": [
                    "Don't come back unless you have to.",
                    "*grunts dismissively*",
                    "Next time bring something worth my time."
                ],
                "about_village": [
                    "This place? Full of weaklings and fools.",
                    "Nothing ever happens here. Pathetic, really."
                ]
            },
            "mischievous": {
                "greeting": [
                    "*grins* Well, well! Fresh entertainment!",
                    "Ooh! A newcomer! Want to help me with a little... project?",
                    "*winks* Don't believe anything bad they've told you about me!"
                ],
                "farewell": [
                    "Don't be a stranger! I've got plans that need an extra pair of hands!",
                    "Come back when you're ready for some real fun!",
                    "*laughs* Try not to be too boring while you're away!"
                ],
                "about_village": [
                    "This village? Oh, it's delightfully stuffy and FULL of opportunities for... creative activities!",
                    "Everyone's so serious around here! They need more surprises, don't you think?"
                ]
            }
        }

        # Add generic options for any personality not specifically defined
        generic = {
            "greeting": ["Hello.", "Greetings.", "Yes?"],
            "farewell": ["Goodbye.", "Farewell.", "Until next time."],
            "about_village": ["It's a village like any other.", "People come and go."]
        }

        return dialogue.get(self.personality, generic)

    def load_sprites(self):
        """Load NPC sprites based on personality"""
        # For the demo, we'll use colored rectangles with personality-based colors
        color_map = {
            "friendly": (50, 205, 50),  # Green
            "cautious": (255, 165, 0),  # Orange
            "wise": (138, 43, 226),  # Purple
            "mysterious": (75, 0, 130),  # Indigo
            "aggressive": (178, 34, 34),  # Red
            "mischievous": (255, 105, 180)  # Pink
        }

        base_color = color_map.get(self.personality, self.color)

        self.sprites = {
            Direction.DOWN: [pygame.Surface((self.width, self.height)) for _ in range(4)],
            Direction.LEFT: [pygame.Surface((self.width, self.height)) for _ in range(4)],
            Direction.RIGHT: [pygame.Surface((self.width, self.height)) for _ in range(4)],
            Direction.UP: [pygame.Surface((self.width, self.height)) for _ in range(4)]
        }

        # Color the sprites
        for direction, frames in self.sprites.items():
            for i, frame in enumerate(frames):
                frame.fill(base_color)
                # Add variations for animation
                variation = pygame.Surface((self.width, self.height))
                alpha = 30 + i * 15
                variation.set_alpha(alpha)
                variation.fill((20, 20, 20))
                frame.blit(variation, (0, 0))

    def get_current_sprite(self):
        """Get the current sprite based on direction and animation"""
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

    def update_memory(self, event):
        """Add new event to NPC's memory"""
        memory_entry = {
            "timestamp": pygame.time.get_ticks(),
            "event": event
        }
        self.memory.append(memory_entry)

        # Keep memory limited to last 10 events
        if len(self.memory) > 10:
            self.memory = self.memory[-10:]

    def get_memory_summary(self):
        """Summarize NPC's relevant memories"""
        if not self.memory:
            return "No significant memories."

        recent_memories = self.memory[-3:]  # Get 3 most recent memories
        summary = "Recent memories:\n"
        for memory in recent_memories:
            summary += f"- {memory['event']}\n"
        return summary

    def update(self, game_map, game_state, player):
        """Update NPC behavior"""
        current_time = pygame.time.get_ticks()

        # Skip updates if talking
        if self.is_talking:
            return

        # Check if it's time for a new action
        if current_time - self.last_action_time < self.action_cooldown:
            # Continue current behavior
            if self.behavior_state == "idle":
                # Just stand still
                pass
            elif self.behavior_state == "wander":
                # Continue wandering
                if self.target_x is None or self.target_y is None:
                    self._pick_random_target(game_map)
                self.move_towards_target(game_map)
                self.is_moving = True

                # Check if reached target
                if self.target_x is None and self.target_y is None:
                    self.behavior_state = "idle"
                    self.idle_timer = current_time
                    self.is_moving = False
            return

        # Time for a new action
        self.last_action_time = current_time

        # Determine new behavior
        if self.behavior_state == "idle":
            # 70% chance to start wandering after being idle
            if random.random() < 0.7:
                self.behavior_state = "wander"
                self._pick_random_target(game_map)
        else:
            # 50% chance to go idle after wandering
            if random.random() < 0.5:
                self.behavior_state = "idle"
                self.idle_timer = current_time
                self.is_moving = False

    def _pick_random_target(self, game_map):
        """Pick a random movement target within the current area"""
        # Get current room boundaries
        room = game_map.get_room_by_id(self.location_id)
        if not room:
            return

        # Pick a random point within the room, with dynamic padding
        padding = min(TILE_SIZE * 2, room.width // 4, room.height // 4)

        # Ensure valid ranges
        x_min = room.x + padding
        x_max = room.x + room.width - padding
        if x_min >= x_max:
            x_min = x_max = room.x + room.width // 2

        y_min = room.y + padding
        y_max = room.y + room.height - padding
        if y_min >= y_max:
            y_min = y_max = room.y + room.height // 2

        # Generate coordinates
        target_x = random.randint(x_min, x_max)
        target_y = random.randint(y_min, y_max)

        # Set as movement target
        self.set_target(target_x, target_y)

    def simulate_npc_response(self, environment_state, player_action):
        """
        Simulate NLP response to determine NPC reaction
        In a production system, this would call an actual LLM API
        """
        # Extract key information
        time_of_day = environment_state.get("time_of_day", TimeOfDay.MORNING)
        weather = environment_state.get("weather", Weather.CLEAR)

        # Parse player action
        action_lower = player_action.lower()
        is_greeting = any(word in action_lower for word in ["hello", "hi", "greet", "hey"])
        is_farewell = any(word in action_lower for word in ["goodbye", "bye", "farewell", "leave"])
        is_question_village = "village" in action_lower and any(
            word in action_lower for word in ["about", "tell", "what"])
        is_hostile = any(word in action_lower for word in ["attack", "threaten", "steal", "kill"])
        is_friendly = any(word in action_lower for word in ["help", "assist", "gift", "give", "please", "kind"])

        # Select response based on action type and NPC personality
        if is_greeting:
            response = random.choice(self.dialogue_options.get("greeting", ["Hello."]))
        elif is_farewell:
            response = random.choice(self.dialogue_options.get("farewell", ["Goodbye."]))
        elif is_question_village:
            response = random.choice(self.dialogue_options.get("about_village", ["It's a place to live."]))
        elif is_hostile:
            # Reaction depends on personality
            if self.personality == "aggressive":
                response = f"*glares* You want to fight? Bring it on, weakling!"
            elif self.personality == "cautious":
                response = f"*backs away slowly* I don't want any trouble..."
            elif self.personality == "friendly":
                response = f"*looks hurt* What have I done to deserve such hostility?"
            else:
                response = f"I wouldn't do that if I were you."
        elif is_friendly:
            # Reaction depends on personality
            if self.personality == "friendly":
                response = f"Of course I'll help! That's what neighbors are for!"
            elif self.personality == "cautious":
                response = f"Help you? Well... I suppose I could, but what's in it for me?"
            elif self.personality == "aggressive":
                response = f"*snorts* I don't do charity work."
            else:
                response = f"I might be able to assist you with that."
        else:
            # Default responses based on time and weather
            if time_of_day == TimeOfDay.NIGHT:
                if self.personality == "cautious":
                    response = "It's getting late. We shouldn't be talking out here."
                elif self.personality == "mysterious":
                    response = "The night reveals truths that daylight conceals..."
                else:
                    response = "It's rather late to be wandering about, isn't it?"
            elif weather == Weather.STORMY:
                response = "This weather doesn't bode well. Best find shelter soon."
            else:
                # Generic response
                generic_responses = [
                    f"*{self.mood}* What else do you need?",
                    "Is there something specific you wanted?",
                    "*nods*"
                ]
                response = random.choice(generic_responses)

        # Update NPC's memory with this interaction
        self.update_memory(f"Player said: '{player_action}'. I responded: '{response}'")

        return response


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
        """Load player sprites from file or create fallback sprites"""
        sprite_file = os.path.join('assets', 'player_sheet.png')
        try:
            if os.path.exists(sprite_file):
                self.sprite_sheet = SpriteSheet(sprite_file)
                # Load directional animations (assuming 32x32 sprites with 4 frames per direction)
                self.sprites = {
                    Direction.DOWN: self.sprite_sheet.load_strip((0, 0, 32, 32), 4),
                    Direction.LEFT: self.sprite_sheet.load_strip((0, 32, 32, 32), 4),
                    Direction.RIGHT: self.sprite_sheet.load_strip((0, 64, 32, 32), 4),
                    Direction.UP: self.sprite_sheet.load_strip((0, 96, 32, 32), 4)
                }
            else:
                self._create_fallback_sprites()
        except:
            # If loading fails for any reason, use fallback
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
        """Handle keyboard input with physics-based movement"""
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

        if MOVEMENT_SMOOTHING:
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
            # Simple movement without physics
            if accel_x != 0 or accel_y != 0:
                dx = int(accel_x * self.speed / self.acceleration)
                dy = int(accel_y * self.speed / self.acceleration)
                self.move(dx, dy, game_map)


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
        self.player = Player("Adventurer", 500, 500)
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.game_state = GameState()
        self.dialogue_manager = DialogueManager()
        self.inventory_ui = InventoryUI()
        self.hud = HUD()

        # Game flags
        self.paused = False

        # Update the update and render methods
        self._update = _update
        self._render = _render

    def _create_game_world(self):
        """Create the game world with rooms, NPCs, and items"""
        # Create game map (larger than screen)
        game_map = GameMap(3000, 3000)

        # Create rooms
        village_square = Room(
            "village_square",
            "Village Square",
            400, 400,
            400, 300,
            "A bustling village square with a central fountain."
        )
        village_square.floor_color = LIGHT_GRAY

        tavern = Room(
            "tavern",
            "The Prancing Pony Tavern",
            400, 750,
            350, 250,
            "A warm, lively tavern filled with the scent of ale and roasted meat."
        )
        tavern.floor_color = BROWN

        blacksmith = Room(
            "blacksmith",
            "Ironheart Forge",
            850, 400,
            250, 200,
            "The blacksmith's shop rings with the sound of hammer on anvil."
        )
        blacksmith.floor_color = (169, 169, 169)  # Dark gray

        forest_edge = Room(
            "forest_edge",
            "Forest Edge",
            400, 100,
            500, 250,
            "The edge of a dense forest. Tall trees loom overhead."
        )
        forest_edge.floor_color = LIGHT_GREEN

        deep_forest = Room(
            "deep_forest",
            "Deep Forest",
            100, 100,
            250, 250,
            "A dark, dense part of the forest. Sunlight barely penetrates."
        )
        deep_forest.floor_color = DARK_GREEN

        hidden_glade = Room(
            "hidden_glade",
            "Hidden Glade",
            100, 400,
            250, 200,
            "A peaceful glade hidden deep in the forest."
        )
        hidden_glade.floor_color = (144, 238, 144)  # Light green

        farm = Room(
            "farm",
            "Sunflower Farm",
            100, 650,
            250, 350,
            "A small farm with fields of vegetables and a modest farmhouse."
        )
        farm.floor_color = (210, 180, 140)  # Tan

        # Add rooms to map
        for room in [village_square, tavern, blacksmith,
                     forest_edge, deep_forest, hidden_glade, farm]:
            game_map.add_room(room)

        # Connect rooms (define exits)
        village_square.exits = {
            "north": "forest_edge",
            "east": "blacksmith",
            "south": "tavern",
            "west": "farm"
        }

        tavern.exits = {
            "north": "village_square"
        }

        blacksmith.exits = {
            "west": "village_square"
        }

        forest_edge.exits = {
            "south": "village_square",
            "west": "deep_forest"
        }

        deep_forest.exits = {
            "east": "forest_edge",
            "south": "hidden_glade"
        }

        hidden_glade.exits = {
            "north": "deep_forest",
            "south": "farm"
        }

        farm.exits = {
            "north": "hidden_glade",
            "east": "village_square"
        }

        # Create obstacles
        # Village square fountain
        fountain = Obstacle(
            "fountain",
            "Village Fountain",
            550, 500,
            100, 100,
            (100, 100, 200)  # Blue-ish
        )
        game_map.add_obstacle(fountain)

        # Tavern bar counter
        bar_counter = Obstacle(
            "bar_counter",
            "Bar Counter",
            450, 850,
            250, 30,
            BROWN
        )
        game_map.add_obstacle(bar_counter)

        # Blacksmith forge
        forge = Obstacle(
            "forge",
            "Forge",
            950, 450,
            60, 60,
            (200, 50, 10)  # Reddish-orange
        )
        game_map.add_obstacle(forge)

        # Trees in forest
        for i in range(15):
            tree_x = random.randint(forest_edge.x + 50, forest_edge.x + forest_edge.width - 50)
            tree_y = random.randint(forest_edge.y + 50, forest_edge.y + forest_edge.height - 50)
            tree = Obstacle(
                f"tree_{i}",
                "Tree",
                tree_x, tree_y,
                40, 40,
                DARK_GREEN
            )
            game_map.add_obstacle(tree)

        # More trees in deep forest
        for i in range(20):
            tree_x = random.randint(deep_forest.x + 30, deep_forest.x + deep_forest.width - 30)
            tree_y = random.randint(deep_forest.y + 30, deep_forest.y + deep_forest.height - 30)
            tree = Obstacle(
                f"deep_tree_{i}",
                "Ancient Tree",
                tree_x, tree_y,
                50, 50,
                (0, 60, 0)  # Darker green
            )
            game_map.add_obstacle(tree)

        # Add NPCs
        merchant = NPC(
            "merchant",
            "Galen the Merchant",
            500, 450,
            "friendly",
            "Galen travels between villages selling goods. He's known for fair prices.",
            "village_square",
            items=["healing_potion", "map_fragment"],
            color=YELLOW
        )
        game_map.add_npc(merchant)

        village_elder = NPC(
            "village_elder",
            "Elder Miriam",
            600, 550,
            "wise",
            "Miriam has been the village elder for over thirty years.",
            "village_square",
            items=["mysterious_herb"],
            color=(138, 43, 226)  # Purple
        )
        game_map.add_npc(village_elder)

        bartender = NPC(
            "bartender",
            "Duran the Barkeep",
            500, 800,
            "friendly",
            "Duran runs the tavern and knows all the local gossip.",
            "tavern",
            items=["apple"],
            color=(210, 105, 30)  # Chocolate
        )
        game_map.add_npc(bartender)

        mysterious_stranger = NPC(
            "mysterious_stranger",
            "The Stranger",
            650, 850,
            "mysterious",
            "Nobody knows this person's name or where they came from.",
            "tavern",
            items=["rusty_key"],
            color=(75, 0, 130)  # Indigo
        )
        game_map.add_npc(mysterious_stranger)

        blacksmith = NPC(
            "blacksmith",
            "Brenna Ironheart",
            900, 480,
            "cautious",
            "Brenna is a skilled blacksmith who learned her craft from her father.",
            "blacksmith",
            items=["iron_dagger"],
            color=(178, 34, 34)  # Firebrick red
        )
        game_map.add_npc(blacksmith)

        hunter = NPC(
            "hunter",
            "Rowan the Hunter",
            600, 200,
            "cautious",
            "Rowan provides the village with game and furs. He knows the forest better than anyone.",
            "forest_edge",
            items=["silver_coin"],
            color=(139, 69, 19)  # Saddle brown
        )
        game_map.add_npc(hunter)

        forest_spirit = NPC(
            "forest_spirit",
            "Whisperleaf",
            200, 150,
            "mysterious",
            "A nature spirit that few have seen. It's said to protect the forest.",
            "deep_forest",
            items=[],
            color=(152, 251, 152)  # Pale green
        )
        game_map.add_npc(forest_spirit)

        wolf = NPC(
            "wolf",
            "Gray Wolf",
            150, 250,
            "aggressive",
            "A large wolf that roams the forest. Territorial but not usually hostile unless provoked.",
            "deep_forest",
            items=[],
            color=(128, 128, 128)  # Gray
        )
        game_map.add_npc(wolf)

        druid = NPC(
            "druid",
            "Thorn the Druid",
            200, 500,
            "wise",
            "Thorn has lived in the forest for decades, communing with nature and studying its magic.",
            "hidden_glade",
            items=["healing_potion", "mysterious_herb"],
            color=(34, 139, 34)  # Forest green
        )
        game_map.add_npc(druid)

        farmer = NPC(
            "farmer",
            "Eliza the Farmer",
            200, 800,
            "friendly",
            "Eliza runs the farm with her family. They provide most of the village's food.",
            "farm",
            items=["apple"],
            color=(210, 180, 140)  # Tan
        )
        game_map.add_npc(farmer)

        # Add items
        # Village square items
        silver_coin = Item(
            "silver_coin",
            "Silver Coin",
            520, 530,
            "A shiny silver coin with strange markings",
            value=10,
            color=LIGHT_GRAY
        )
        game_map.add_item(silver_coin)

        # Tavern items
        rusty_key = Item(
            "rusty_key",
            "Rusty Key",
            700, 840,
            "An old, rusty key. It might open something nearby",
            value=5,
            color=BROWN
        )
        game_map.add_item(rusty_key)

        # Blacksmith items
        iron_dagger = Item(
            "iron_dagger",
            "Iron Dagger",
            920, 520,
            "A simple but effective iron dagger",
            value=20,
            color=(192, 192, 192)  # Silver
        )
        game_map.add_item(iron_dagger)

        # Forest edge items
        mysterious_herb = Item(
            "mysterious_herb",
            "Mysterious Herb",
            450, 150,
            "An unusual herb with a sweet aroma",
            value=8,
            color=(173, 255, 47)  # Green-yellow
        )
        game_map.add_item(mysterious_herb)

        # Deep forest items
        healing_potion = Item(
            "healing_potion",
            "Healing Potion",
            150, 200,
            "A small vial of red liquid that restores health",
            value=15,
            color=(220, 20, 60)  # Crimson
        )
        game_map.add_item(healing_potion)

        # Hidden glade items
        map_fragment = Item(
            "map_fragment",
            "Map Fragment",
            180, 480,
            "A torn piece of an old map",
            value=25,
            color=BEIGE
        )
        game_map.add_item(map_fragment)

        # Farm items
        apple = Item(
            "apple",
            "Apple",
            250, 800,
            "A fresh, juicy apple",
            value=2,
            color=(255, 0, 0)  # Red
        )
        game_map.add_item(apple)

        return game_map

    def run(self):
        """Main game loop"""
        while self.running:
            # Handle events
            self._handle_events()

            # Update game state if not paused
            if not self.paused and not self.dialogue_manager.is_active:
                self._update()

            # Render everything
            self._render()

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

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.dialogue_manager.is_active:
                        self.dialogue_manager.end_dialogue()
                    elif self.inventory_ui.is_visible:
                        self.inventory_ui.toggle()
                    else:
                        self.paused = not self.paused

                elif event.key == pygame.K_i:
                    if not self.dialogue_manager.is_active:
                        self.inventory_ui.toggle()

                elif event.key == pygame.K_e:
                    if not self.dialogue_manager.is_active and not self.inventory_ui.is_visible:
                        self._handle_interaction()

            # Handle dialogue input if active
            self.dialogue_manager.handle_input(event, self.game_state)

            # Handle inventory input if visible
            self.inventory_ui.handle_input(event, self.player)

    def _handle_interaction(self):
        """Handle player interaction with NPCs or items"""
        # Check for nearby NPC
        nearest_npc = self.game_map.get_npc_near_position(
            self.player.x, self.player.y, INTERACTION_DISTANCE
        )

        if nearest_npc:
            # Start dialogue with NPC
            self.dialogue_manager.start_dialogue(nearest_npc)
            return

        # Check for nearby items
        nearest_items = self.game_map.get_items_near_position(
            self.player.x, self.player.y, INTERACTION_DISTANCE
        )

        if nearest_items:
            # Pick up the first item
            item = nearest_items[0]
            item.is_collected = True
            self.player.add_to_inventory(item)

            # Display pickup message (could be improved with a message system)
            print(f"Picked up: {item.name} - {item.description}")

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
