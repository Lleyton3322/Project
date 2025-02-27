import os
import pygame
import logging
from sprite_manager import SpriteManager
from game_classes import AnimatedFountain, EnhancedPlayer, Camera, GameMap

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
BLACK = (0, 0, 0)


def create_fountain_image():
    """Create a fountain.png file if it doesn't exist (for testing)"""
    fountain_dir = os.path.join('sprites', 'obstacles')
    fountain_path = os.path.join(fountain_dir, 'fountain.png')

    if not os.path.exists(fountain_dir):
        os.makedirs(fountain_dir)

    if not os.path.exists(fountain_path):
        logger.warning(f"Creating a test fountain sprite at {fountain_path}")
        # Create a simple 2x3 fountain sprite sheet
        sheet_width, sheet_height = 256, 192
        sheet = pygame.Surface((sheet_width, sheet_height), pygame.SRCALPHA)

        # Define frame size
        frame_width, frame_height = 120, 60
        padding_x, padding_y = 8, 6

        colors = [
            (100, 150, 255),  # Light blue
            (80, 130, 230),  # Medium blue
            (120, 170, 255),  # Bright blue
            (90, 140, 240),  # Another blue
            (110, 160, 250),  # Yet another blue
            (70, 120, 220)  # Dark blue
        ]

        # Create 6 distinct fountain frames (2x3 grid)
        for i in range(6):
            row = i // 2
            col = i % 2

            # Calculate position with padding
            x = col * (frame_width + padding_x)
            y = row * (frame_height + padding_y)

            # Base of fountain (same in all frames)
            pygame.draw.ellipse(sheet, (150, 150, 150),
                                (x + 20, y + 40, 80, 20))  # Stone base

            # Water base (slightly different in each frame)
            pygame.draw.ellipse(sheet, colors[i],
                                (x + 30, y + 30, 60, 15))  # Water pool

            # Center pillar
            pygame.draw.rect(sheet, (130, 130, 130),
                             (x + 55, y + 15, 10, 25))  # Stone pillar

            # Water spray (different in each frame for animation)
            offset = (i % 3) * 2 - 2  # Different positions
            height = 10 + (i % 3) * 2  # Different heights

            # Draw water drops
            for j in range(5):
                drop_x = x + 50 + offset + (j - 2) * 5
                drop_y = y + 10 - (j % 3) * 3
                pygame.draw.circle(sheet, colors[(i + j) % 6],
                                   (drop_x, drop_y), 2 + (j % 3))

            # Draw main spray
            pygame.draw.ellipse(sheet, colors[i],
                                (x + 45, y + 5, 30, height))

        # Save the sheet
        pygame.image.save(sheet, fountain_path)
        logger.info(f"Created test fountain sprite at {fountain_path}")

    return fountain_path


def test_fountain_animation():
    """Test the fountain animation functionality"""
    # Create a test window
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Fountain Animation Test")

    # Create a test fountain image if needed
    create_fountain_image()

    # Create a simple game map
    game_map = GameMap(2000, 2000)

    # Create a camera
    camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)

    # Create player for testing camera movement
    player = EnhancedPlayer("Test Player", 500, 400)

    # Create the fountain
    fountain_size = 180
    fountain_x = 1000 - fountain_size // 2
    fountain_y = 1000 - fountain_size // 2
    fountain = AnimatedFountain("fountain", "Central Fountain",
                                fountain_x, fountain_y,
                                fountain_size, fountain_size)

    game_map.add_obstacle(fountain)

    # Main loop
    clock = pygame.time.Clock()
    running = True

    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        # Handle player movement for camera testing
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        speed = 5

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -speed
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = speed

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -speed
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = speed

        # Move player
        player.x += dx
        player.y += dy

        # Update camera to follow player
        camera.update(player.x, player.y, game_map.width, game_map.height)

        # Update fountain animation
        current_time = pygame.time.get_ticks()
        fountain.update(current_time)

        # Clear screen
        screen.fill(BLACK)

        # Render fountain
        fountain.render(screen, camera.x, camera.y)

        # Draw player position (simple rectangle)
        pygame.draw.rect(screen, (255, 255, 255),
                         (player.x - camera.x, player.y - camera.y,
                          player.width, player.height))

        # Add helpful text
        font = pygame.font.SysFont('Arial', 24)
        text = font.render("Use arrow keys to move. ESC to exit.", True, (255, 255, 255))
        screen.blit(text, (20, 20))

        # Update display
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    test_fountain_animation()