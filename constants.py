# constants.py
import pygame

# Game constants
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
TILE_SIZE = 64
PLAYER_SPEED = 6
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

# Animation and Particle Constants
FOUNTAIN_ANIMATION_SPEED = 200  # milliseconds
PARTICLE_DELAY = 200  # milliseconds for footstep particles

# NPC Interaction Constants
NPC_INTERACTION_DISTANCE = 100
NPC_INTERACTION_COOLDOWN = 10000  # 10 seconds between interactions (ms)
NPC_INTERACTION_DURATION = 4000  # How long a conversation lasts (ms)

# Physics Constants
PLAYER_ACCELERATION = 0.5
PLAYER_FRICTION = 0.85
DIAGONAL_FACTOR = 0.7071  # sqrt(2)/2, prevents faster diagonal movement
MOVEMENT_SMOOTHING = True
ENABLE_PIXEL_PERFECT_COLLISION = True