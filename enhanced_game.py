from constants import *
from sprite_manager import SpriteManager
from particle_system import ParticleSystem
import logging
logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)
logger = logging.getLogger(__name__)
from game_classes import *
import pygame

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
# GameMap.render = enhanced_render


def create_fountain_sprite():
    try:
        sprite_manager = SpriteManager()
        sprite_path = os.path.join('obstacles', 'fountain.png')
        fountain_surface = sprite_manager.load_sprite(sprite_path, (100, 100))
        logger.debug(f"Loaded fountain sprite from {sprite_path}")
        return fountain_surface
    except Exception as e:
        logger.error(f"Error loading fountain sprite: {e}")
        fallback = pygame.Surface((100, 100), pygame.SRCALPHA)
        fallback.fill((0, 149, 237, 255))  # Blue color
        logger.warning("Using blue fallback sprite")
        return fallback


# Fix the path for assets
def fix_assets_path():
    """Make sure the assets path exists"""
    try:
        if not os.path.exists('assets'):
            os.makedirs('assets')
            logger.debug("Created assets directory")
    except OSError as e:
        logger.error(f"Error creating assets directory: {e}")


# Call the function to ensure assets directory exists
fix_assets_path()


def _render(self):
    """Render the game with enhanced visual effects"""
    # Fill background
    self.screen.fill(BLACK)

    # Render map (floors and static elements)
    self.game_map.render(self.screen, self.camera.x, self.camera.y)

    # Render player trail and particles
    self.player.render_trail(self.screen, self.camera.x, self.camera.y)
    self.player.render_particles(self.screen, self.camera.x, self.camera.y)

    # Render animated obstacles (like the fountain)
    for obstacle in self.game_map.obstacles:
        if isinstance(obstacle, AnimatedFountain):
            obstacle.render(self.screen, self.camera.x, self.camera.y)

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
