import random
import logging
from constants import *
logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)
logger = logging.getLogger(__name__)


class NPCInteractionManager:
    """Manages interactions between NPCs in the game world"""

    def __init__(self):
        """Initialize the NPC interaction manager"""
        self.interaction_distance = NPC_INTERACTION_DISTANCE  # From constants.py
        self.interaction_cooldown = NPC_INTERACTION_COOLDOWN  # From constants.py
        self.interaction_duration = NPC_INTERACTION_DURATION  # From constants.py
        self.active_interactions = {}  # Tracks ongoing NPC interactions
        self.last_interaction_time = {}  # Tracks cooldown per NPC pair
        self.speech_font = pygame.font.SysFont('Arial', 14)

        # Debugging flag
        self.debug = __debug__

        self.interactions_enabled = True  # New attribute to control interactions

    def toggle_interactions(self, enable=None):
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
        if enable is None:
            # If no specific state is provided, toggle the current state
            self.interactions_enabled = not self.interactions_enabled
        else:
            # Set to the specified state
            self.interactions_enabled = enable

        # Log the change
        logger.info(f"NPC interactions {'enabled' if self.interactions_enabled else 'disabled'}")

        return self.interactions_enabled

    def initialize_npcs(self, npcs):
        """Set up interaction attributes for NPCs"""
        for npc in npcs:
            if not hasattr(npc, 'is_interacting'):
                npc.is_interacting = False
                npc.interaction_partner = None
                npc.interaction_message = None
                npc.message_time = 0

                # Make sure all NPCs have the required method
                if not hasattr(npc, 'simulate_npc_response'):
                    # Create a simple fallback response function
                    npc.simulate_npc_response = lambda env, msg: f"Hello there! I'm {npc.name}."

    def update(self, game_map, game_state, current_time):
        """
        Override update method to respect the interactions toggle

        Args:
            game_map: Game map containing NPCs
            game_state: Current game state
            current_time: Current game time
        """
        # If interactions are disabled, do nothing
        if not self.interactions_enabled:
            return

        # Initialize NPCs if needed
        self.initialize_npcs(game_map.npcs)

        # End expired interactions
        self._end_expired_interactions(current_time)

        # Check for new interactions
        if len(self.active_interactions) < 2:  # Limit concurrent interactions
            self._check_for_new_interactions(game_map, game_state, current_time)

        self.initialize_npcs(game_map.npcs)
        self._end_expired_interactions(current_time)
        self._check_for_new_interactions(game_map, game_state, current_time)

    def _end_expired_interactions(self, current_time):
        """End interactions that have expired"""
        to_remove = []

        for interaction_id, data in self.active_interactions.items():
            if current_time - data['start_time'] > self.interaction_duration:
                # End the interaction
                npc1 = data['npc1']
                npc2 = data['npc2']

                npc1.is_interacting = False
                npc1.interaction_partner = None
                npc1.interaction_message = None

                npc2.is_interacting = False
                npc2.interaction_partner = None
                npc2.interaction_message = None

                to_remove.append(interaction_id)

                if self.debug:
                    logger.debug(f"Ended interaction between {npc1.name} and {npc2.name}")

        # Remove ended interactions
        for interaction_id in to_remove:
            del self.active_interactions[interaction_id]

    def _check_for_new_interactions(self, game_map, game_state, current_time):
        """Check for new possible interactions between NPCs"""
        npcs = game_map.npcs

        # Only proceed if we have at least 2 NPCs
        if len(npcs) < 2:
            return

        # Check all pairs of NPCs
        for i, npc1 in enumerate(npcs):
            # Skip if already interacting
            if npc1.is_interacting:
                continue

            for j, npc2 in enumerate(npcs[i + 1:], i + 1):
                # Skip if already interacting
                if npc2.is_interacting:
                    continue

                # Calculate distance between NPCs
                distance = npc1.distance_to(npc2)

                # Check if they're close enough
                if distance <= self.interaction_distance:
                    # Check cooldown
                    pair_id = f"{min(npc1.entity_id, npc2.entity_id)}-{max(npc1.entity_id, npc2.entity_id)}"
                    last_time = self.last_interaction_time.get(pair_id, 0)

                    # If cooldown has passed, start interaction
                    if current_time - last_time > self.interaction_cooldown:
                        self._start_interaction(npc1, npc2, game_state, current_time, pair_id)
                        return  # Only start one new interaction per update

    def _start_interaction(self, npc1, npc2, game_state, current_time, pair_id):
        """Start an interaction between two NPCs"""
        # Set interaction state
        npc1.is_interacting = True
        npc1.interaction_partner = npc2
        npc2.is_interacting = True
        npc2.interaction_partner = npc1

        # Generate greeting
        environment_state = game_state.get_environment_state(npc1.location_id)
        try:
            # Get response from NPC
            response = npc1.simulate_npc_response(environment_state, f"Greeting to {npc2.name}")

            # Check if response is a tuple (response text, adjustment, is_farewell)
            if isinstance(response, tuple):
                greeting = response[0]  # Get just the text part
            else:
                greeting = response

            # Clean up the greeting text (remove quotes if present)
            greeting = greeting.strip('"')

            logger.debug(f"Initial greeting: {response}")
        except Exception as e:
            # Fallback to random greeting
            greeting_options = [
                f"Hello, {npc2.name}. How are you today?",
                f"Greetings, {npc2.name}!",
                f"Good to see you, {npc2.name}.",
                f"Hi there, {npc2.name}."
            ]
            greeting = random.choice(greeting_options)
            logger.error(f"Error generating greeting: {e}")

        # Set greeting as interaction message
        npc1.interaction_message = greeting
        npc1.message_time = current_time

        # Record interaction
        interaction_id = f"{current_time}-{npc1.entity_id}-{npc2.entity_id}"
        self.active_interactions[interaction_id] = {
            'npc1': npc1,
            'npc2': npc2,
            'start_time': current_time,
            'last_message_time': current_time,
            'last_speaker': npc1
        }

        # Update cooldown
        self.last_interaction_time[pair_id] = current_time

    def update_conversations(self, game_state, current_time):
        """
        Override conversation update to respect the interactions toggle

        Args:
            game_state: Current game state
            current_time: Current game time
        """
        # If interactions are disabled, do nothing
        if not self.interactions_enabled:
            return

        for interaction_id, data in self.active_interactions.items():
            npc1 = data['npc1']
            npc2 = data['npc2']
            last_speaker = data['last_speaker']
            last_message_time = data['last_message_time']

            # Only generate a response after some time has passed
            if current_time - last_message_time < 2000:  # 2 second delay between messages
                continue

            # Determine who speaks next
            next_speaker = npc2 if last_speaker == npc1 else npc1
            listener = npc1 if next_speaker == npc2 else npc2

            # If next speaker already has a message, skip
            if next_speaker.interaction_message and current_time - next_speaker.message_time < 4000:
                continue

            # Get the previous message
            previous_message = last_speaker.interaction_message

            # Generate response
            try:
                environment_state = game_state.get_environment_state(next_speaker.location_id)
                response = next_speaker.simulate_npc_response(environment_state, previous_message)

                # Handle tuple response
                if isinstance(response, tuple):
                    message = response[0]  # Get just the text part
                else:
                    message = response

                # Clean up message text
                message = message.strip('"')

            except Exception as e:
                logger.error(f"Error generating response: {e}")
                # Fallback responses
                responses = [
                    "I see.",
                    "Interesting.",
                    "That's good to know.",
                    f"Thanks for telling me, {last_speaker.name}.",
                    "Indeed."
                ]
                message = random.choice(responses)

            # Update interaction data
            next_speaker.interaction_message = message
            next_speaker.message_time = current_time
            data['last_speaker'] = next_speaker
            data['last_message_time'] = current_time

    def _render_speech_bubble(self, surface, text, x, y, cache=None):
        """Render a speech bubble with caching"""
        if cache is None:
            cache = {}
        cache_key = (text, x, y)

        # Ensure text is a string
        if isinstance(text, tuple):
            text = text[0]  # Get just the text part if it's a tuple
        text = str(text).strip('"')  # Convert to string and remove quotes

        if cache_key not in cache:
            # Wrap text to fit in bubble
            max_width = 150
            words = text.split()
            lines = []
            line = ""
            for word in words:
                test_line = line + word + " "
                width = self.speech_font.size(test_line)[0]
                if width <= max_width:
                    line = test_line
                else:
                    lines.append(line)
                    line = word + " "
            lines.append(line)

            # Calculate bubble dimensions
            line_height = self.speech_font.get_height()
            bubble_height = len(lines) * line_height + 10
            bubble_width = max(self.speech_font.size(line)[0] for line in lines) + 20

            # Position bubble centered above point
            bubble_rect = pygame.Rect(x - bubble_width // 2, y - bubble_height - 5, bubble_width, bubble_height)

            # Create bubble surface
            bubble_surface = pygame.Surface((bubble_width, bubble_height), pygame.SRCALPHA)
            bubble_surface.fill((255, 255, 255, 200))
            pygame.draw.rect(bubble_surface, (0, 0, 0), (0, 0, bubble_width, bubble_height), 1)

            # Draw text
            for i, line in enumerate(lines):
                text_surface = self.speech_font.render(line, True, (0, 0, 0))
                bubble_surface.blit(text_surface, (10, 5 + i * line_height))

            # Draw pointer
            points = [(bubble_width // 2, bubble_height),
                      (bubble_width // 2 - 5, bubble_height + 5),
                      (bubble_width // 2 + 5, bubble_height + 5)]
            pygame.draw.polygon(bubble_surface, (255, 255, 255), points)
            pygame.draw.polygon(bubble_surface, (0, 0, 0), points, 1)

            cache[cache_key] = bubble_surface

        surface.blit(cache[cache_key], (x - cache[cache_key].get_width() // 2, y - cache[cache_key].get_height() - 5))

    def render(self, surface, camera_x, camera_y):
        """Render speech bubbles for NPC interactions"""
        # Only render if interactions are enabled
        if not self.interactions_enabled:
            return

        # Create a cache to prevent recreating speech bubbles every frame
        speech_bubble_cache = {}

        # Render speech bubbles for all NPCs that have messages
        current_time = pygame.time.get_ticks()
        for npc in [npc for interaction in self.active_interactions.values()
                    for npc in [interaction['npc1'], interaction['npc2']]
                    if npc.interaction_message and current_time - npc.message_time <= self.interaction_duration]:
            bubble_x = npc.x - camera_x + npc.width // 2
            bubble_y = npc.y - camera_y - 10
            self._render_speech_bubble(surface, npc.interaction_message, bubble_x, bubble_y, speech_bubble_cache)