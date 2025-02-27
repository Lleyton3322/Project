from game_classes import *
from npc_interaction_system import NPCInteractionManager
from constants import *
import logging
logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)
logger = logging.getLogger(__name__)


def install_npc_interactions():
    """Install the NPC interaction system into the game"""
    logger.debug("Installing NPC Interaction System...")

    # Save original Game.__init__ method
    original_Game_init = Game.__init__

    # Define new __init__ method with interaction manager
    def new_init(self, *args, **kwargs):
        # Call original init
        original_Game_init(self, *args, **kwargs)

        # Add NPC interaction manager
        self.npc_interaction_manager = NPCInteractionManager()

        # Add font for speech bubbles
        self.speech_font = pygame.font.SysFont('Arial', 12)

        logger.debug("NPC Interaction System initialized")

    # Replace Game.__init__ with our new version
    Game.__init__ = new_init

    # Save original Game._update method
    original_Game_update = Game._update

    # Define new _update method that includes NPC interactions
    def new_update(self):
        # Call original update
        original_Game_update(self)

        # Update NPC interactions
        current_time = pygame.time.get_ticks()
        self.npc_interaction_manager.update(self.game_map, self.game_state, current_time)
        self.npc_interaction_manager.update_conversations(self.game_state, current_time)

    # Replace Game._update with our new version
    Game._update = new_update

    # Save original Game._render method
    original_Game_render = Game._render

    # Define new _render method that includes rendering NPC interactions
    def new_render(self):
        # Call original render
        original_Game_render(self)

        # Render NPC interactions
        self.npc_interaction_manager.render(self.screen, self.camera.x, self.camera.y)

    # Replace Game._render with our new version
    Game._render = new_render

    # Save original NPC.update method
    original_NPC_update = NPC.update

    # Define new NPC.update method that includes interaction behavior
    def new_npc_update(self, game_map, game_state, player):
        # Call original update
        original_NPC_update(self, game_map, game_state, player)

        # If this NPC is currently in an interaction
        if hasattr(self, 'is_interacting') and self.is_interacting:
            # Face towards interaction partner
            if self.interaction_partner:
                # Calculate direction to face
                dx = self.interaction_partner.x - self.x
                dy = self.interaction_partner.y - self.y

                # Set direction based on relative position
                if abs(dx) > abs(dy):
                    self.direction = Direction.RIGHT if dx > 0 else Direction.LEFT
                else:
                    self.direction = Direction.DOWN if dy > 0 else Direction.UP

                # Move slightly towards partner if too far
                distance = self.distance_to(self.interaction_partner)
                if distance > NPC_INTERACTION_DISTANCE:  # Use constant
                    # Calculate normalized direction vector
                    total = abs(dx) + abs(dy)
                    move_x = dx / total if total > 0 else 0
                    move_y = dy / total if total > 0 else 0

                    # Move slightly towards partner
                    self.move(int(move_x * self.speed), int(move_y * self.speed), game_map)

    # Replace NPC.update with our new version
    NPC.update = new_npc_update

    logger.debug("NPC Interaction System installed successfully")