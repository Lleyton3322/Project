# new_main.py
from game_classes import *
from enhanced_game import fix_assets_path
from npc_interaction_system import NPCInteractionManager
from game_enums import Direction, TimeOfDay, Weather, EventType
from constants import *
from sprite_manager import SpriteManager
from particle_system import ParticleSystem
import logging
import pygame  # Ensure pygame is imported for font initialization

logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Entry point for the game"""
    try:
        # Initialize pygame
        pygame.init()
        pygame.font.init()  # Explicitly initialize the font module

        # Display loading screen
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Whispers of the Forgotten Vale - With NPC Interactions")

        # Draw loading screen
        screen.fill(BLACK)
        font = pygame.font.SysFont('Arial', 32, bold=True)  # Now this should work
        loading_text = font.render("Loading Game World...", True, WHITE)
        loading_rect = loading_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        screen.blit(loading_text, loading_rect)
        pygame.display.flip()

        # Ensure assets directory exists
        fix_assets_path()

        # Replace Player class with EnhancedPlayer
        Player = EnhancedPlayer

        # Define enhanced update method
        def enhanced_update(self):
            keys = pygame.key.get_pressed()
            self.player.handle_input(keys, self.game_map)
            self.player.add_footstep_particle(self.game_state)
            self.particle_system.update()  # Update all particles

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

            # Update NPC interactions
            current_time = pygame.time.get_ticks()
            self.npc_interaction_manager.update(self.game_map, self.game_state, current_time)
            self.npc_interaction_manager.update_conversations(self.game_state, current_time)

        # Initialize and run game
        game = Game()
        game.particle_system = ParticleSystem()  # Add particle system to game instance
        game.sprite_manager = SpriteManager()  # Add sprite manager to game instance

        # Run the game
        print(sys._getframe().f_locals)
        game.run()


    except Exception as e:
        logger.error(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    main()
