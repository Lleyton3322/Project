import pygame
import logging
import textwrap
import random
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from constants import *
import os
logger = logging.getLogger(__name__)

# Import EventType from your memory system
from game_enums import EventType
from sprite_manager import SpriteManager

DIALOG_PADDING = 20
LINE_HEIGHT = 20
MAX_VISIBLE_LINES = 4


class DialogueNodeType(Enum):
    GREETING = "greeting"
    RESPONSE = "response"
    QUESTION = "question"
    MEMORY_REFERENCE = "memory_reference"
    QUEST_OFFER = "quest_offer"
    QUEST_RESPONSE = "quest_response"
    FAREWELL = "farewell"
    SHOP = "shop"
    GOSSIP = "gossip"


@dataclass
class DialogueNode:
    """A single node in a dialogue tree"""
    id: str
    type: DialogueNodeType
    text: str
    responses: List[str] = None  # List of child node IDs
    conditions: Dict[str, Any] = None  # Conditions for this node to be available
    actions: Dict[str, Any] = None  # Actions to perform when this node is chosen
    metadata: Dict[str, Any] = None  # Additional data for this node


class EnhancedDialogueManager:
    def __init__(self, memory_system, game_instance):
        self.memory_system = memory_system
        self.game_instance = game_instance  # Store game reference
        self.is_active = False
        self.current_npc = None
        self.dialogue_history = []
        self.player_input = ""
        self.input_active = False
        self.scroll_offset = 0
        self.max_visible_entries = 4
        self.font = pygame.font.SysFont('Arial', 16)
        self.header_font = pygame.font.SysFont('Arial', 18, bold=True)
        self.free_text_mode = True
        self.ending_conversation = False
        self.goodbye_message = None
        self.goodbye_timer = 0
        self.is_processing_response = False

    def _check_follow_command(self, input_text: str) -> bool:
        """Check if input is a follow command"""
        follow_commands = [
            "follow me",
            "come with me",
            "follow",
            "join me",
            "come along",
            "accompany me"
        ]
        return any(cmd in input_text.lower() for cmd in follow_commands)

    def handle_input(self, event, player, game_state, current_time):
        """Handle player input in dialogue mode."""
        if not self.is_active or not self.input_active:
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.end_dialogue()
                return

            elif event.key == pygame.K_RETURN:
                if self.player_input.strip():
                    current_input = self.player_input

                    # Add player input to dialogue history
                    self.dialogue_history.append({
                        "speaker": "player",
                        "text": current_input
                    })

                    if self.current_npc:
                        # Check for follow command
                        if self._check_follow_command(current_input):
                            # Set processing flag and show waiting message
                            self.is_processing_response = True

                            # Request NPC to follow using game instance
                            success, message = self.game_instance.npc_follower_system.request_following(
                                self.current_npc, player, current_time
                            )

                            # Add NPC's response to dialogue history
                            self.dialogue_history.append({
                                "speaker": "npc",
                                "text": f"{self.current_npc.name}: {message}",
                                "node_type": DialogueNodeType.RESPONSE.value
                            })

                            # If NPC agreed to follow, end dialogue
                            if success:
                                self.current_npc.set_floating_text(message, 3000)
                                self.end_dialogue()

                            self.is_processing_response = False
                        else:
                            # Handle regular dialogue
                            try:
                                # Set processing flag and show waiting message
                                self.is_processing_response = True
                                self.dialogue_history.append({
                                    "speaker": "npc",
                                    "text": f"{self.current_npc.name}: Thinking...",
                                    "node_type": DialogueNodeType.RESPONSE.value
                                })

                                # Get NPC response
                                response, adjustment, is_farewell = self.current_npc.simulate_npc_response(
                                    game_state.get_environment_state(self.current_npc.location_id),
                                    current_input
                                )

                                # Replace waiting message with actual response
                                self.dialogue_history[-1]["text"] = f"{self.current_npc.name}: {response}"
                                self.is_processing_response = False

                                if is_farewell:
                                    # Clean the response text
                                    clean_response = response.strip('"')
                                    # Set floating text before ending dialogue
                                    self.current_npc.set_floating_text(clean_response, 5000)
                                    # End dialogue
                                    self.end_dialogue()

                            except Exception as e:
                                print(f"Error processing response: {e}")
                                self.dialogue_history.append({
                                    "speaker": "npc",
                                    "text": f"{self.current_npc.name}: I'm having trouble understanding."
                                })
                                self.is_processing_response = False

                    # Reset scroll and clear input
                    self.scroll_offset = 0
                    self.player_input = ""

            elif event.key == pygame.K_BACKSPACE:
                self.player_input = self.player_input[:-1]
            else:
                if len(self.player_input) < 50:  # Limit input length
                    self.player_input += event.unicode

    def update(self, current_time):
        """
        Update method for the dialogue manager.

        Args:
            current_time (int): Current game time in milliseconds
        """
        # Check for and clear expired goodbye messages
        if self.goodbye_message:
            if current_time - self.goodbye_timer > 5000:  # 5 seconds
                self.goodbye_message = None
                self.goodbye_timer = 0

        # You can add additional update logic here if needed
        # For example, tracking conversation duration, managing dialogue state, etc.

    def start_dialogue(self, npc, player, current_time, location_id):
        """Start dialogue with an NPC with memory integration"""
        self.is_active = True
        self.current_npc = npc
        self.dialogue_history = []
        self.ending_conversation = False
        self.goodbye_message = None
        self.goodbye_timer = 0
        self.is_processing_response = False  # Reset processing flag

        # Reset input state based on mode
        self.player_input = ""
        self.input_active = True
        self.scroll_offset = 0

        # Make sure NPC has memory features
        if not hasattr(npc, 'relationship_manager'):
            logger.warning(f"NPC {npc.name} lacks relationship manager")
            npc.relationship_manager = self.memory_system.get_relationship_manager(npc)

        # Record this conversation
        self.memory_system.record_event(
            EventType.CONVERSATION,
            player,
            {"initiated_by": "player"},
            location_id,
            current_time,
            npc=npc
        )

        # Add a greeting message to the dialogue history
        self.dialogue_history.append({
            "speaker": "npc",
            "text": f"{npc.name}: Hello! How can I help you?",
            "node_type": DialogueNodeType.GREETING.value
        })

        # Mark NPC as talking
        npc.is_talking = True

    def end_dialogue(self):
        """End the current dialogue"""
        if self.current_npc:
            self.current_npc.is_talking = False
            # Record the end of conversation in memory system if available
            if hasattr(self.current_npc, 'relationship_manager'):
                relationship = self.current_npc.relationship_manager
                relationship.last_interaction_time = pygame.time.get_ticks()

            # Set the goodbye message and timer
            self.goodbye_message = self.current_npc.floating_text
            self.goodbye_timer = pygame.time.get_ticks()

        self.is_active = False
        self.current_npc = None
        self.input_active = False
        self.ending_conversation = False

    def render(self, surface):
        """Render dialogue UI with scrolling support, NPC details, and real-time friendship bar"""
        if not self.is_active:
            return

        width, height = surface.get_size()

        # Calculate total dialogue interface height (half screen height)
        total_dialogue_height = height // 2

        # Position the entire dialogue interface at the bottom of the screen
        base_y = height - total_dialogue_height

        # Input box height and position
        input_box_height = 40
        input_box_y = height - input_box_height

        # Dialogue box positioned above input box
        dialogue_height = total_dialogue_height - input_box_height - 10  # Subtract input box and padding
        dialogue_y = base_y  # Start at the base_y position

        # Adjust column sizes: Left 2/3, Right 1/3
        dialogue_box = pygame.Rect(0, dialogue_y, width * 2 / 3, dialogue_height)
        details_box_width = width * 1 / 3
        details_box_x = width * 2 / 3

        # Create semi-transparent background for entire dialogue area
        full_bg = pygame.Surface((width, total_dialogue_height), pygame.SRCALPHA)
        full_bg.fill((0, 0, 0, 200))
        surface.blit(full_bg, (0, base_y))

        # Create semi-transparent background for dialogue
        dialogue_surface = pygame.Surface((dialogue_box.width, dialogue_height), pygame.SRCALPHA)
        dialogue_surface.fill((0, 0, 0, 100))  # Slightly transparent black
        surface.blit(dialogue_surface, (0, dialogue_y))

        # Draw border
        pygame.draw.rect(surface, WHITE, dialogue_box, 2)

        # Get NPC name if available
        npc_name = self.current_npc.name if self.current_npc else "NPC"

        # Calculate max entries based on available height
        line_height = self.font.get_height() + 2
        max_visible_lines = int((dialogue_height - 20) / line_height)  # Subtract padding

        # Prepare dialogue entries with line wrapping
        total_lines = []
        for entry in self.dialogue_history:
            speaker = entry["speaker"]
            text = entry["text"]

            if speaker == "player":
                text_color = LIGHT_BLUE
                display_name = "You"
            else:
                text_color = YELLOW
                display_name = npc_name

            wrapped_lines = [
                {"speaker": display_name, "text": line, "color": text_color}
                for line in textwrap.wrap(f"{display_name}: {text}", width=40)
            ]
            total_lines.extend(wrapped_lines)

        # Apply scrolling
        total_line_count = len(total_lines)
        max_scroll_offset = max(0, total_line_count - max_visible_lines)
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll_offset))

        # Show scroll indicators
        if max_scroll_offset > 0:
            if self.scroll_offset < max_scroll_offset:
                up_triangle_points = [
                    (width // 3 - 10, dialogue_y + 10),
                    (width // 3, dialogue_y + 5),
                    (width // 3 + 10, dialogue_y + 10)
                ]
                pygame.draw.polygon(surface, WHITE, up_triangle_points)
            if self.scroll_offset > 0:
                down_triangle_points = [
                    (width // 3 - 10, dialogue_y + dialogue_height - 10),
                    (width // 3, dialogue_y + dialogue_height - 5),
                    (width // 3 + 10, dialogue_y + dialogue_height - 10)
                ]
                pygame.draw.polygon(surface, WHITE, down_triangle_points)

        # Render visible lines
        start_line = max(0, total_line_count - max_visible_lines - self.scroll_offset)
        end_line = start_line + max_visible_lines
        visible_lines = total_lines[start_line:end_line]
        for i, line in enumerate(visible_lines):
            text_surface = self.font.render(line['text'], True, line['color'])
            surface.blit(text_surface, (DIALOG_PADDING + 10, dialogue_y + 10 + i * line_height))

        # Render NPC details and real-time friendship bar in the right column
        if self.current_npc:
            details_box = pygame.Rect(details_box_x, dialogue_y, details_box_width, dialogue_height)

            # Semi-transparent background for details
            details_surface = pygame.Surface((details_box_width, dialogue_height), pygame.SRCALPHA)
            details_surface.fill((50, 50, 50, 200))  # Darker semi-transparent background
            surface.blit(details_surface, (details_box_x, dialogue_y))

            # Draw border
            pygame.draw.rect(surface, WHITE, details_box, 2)

            # Check if there's a goodbye message and it's still active
            current_time = pygame.time.get_ticks()
            if self.goodbye_message and current_time - self.goodbye_timer < 5000:
                # Render centered goodbye message
                goodbye_surface = self.header_font.render(self.goodbye_message, True, WHITE)
                text_rect = goodbye_surface.get_rect(
                    centerx=int(details_box_x + details_box_width / 2),
                    centery=int(dialogue_y + dialogue_height / 2)
                )
                surface.blit(goodbye_surface, text_rect)
            else:
                # NPC Details when not showing goodbye message
                details_y = dialogue_y + 10
                details = [
                    f"Personality: {self.current_npc.personality}",
                    f"Location: {self.current_npc.location_id}",
                    f"Backstory: {textwrap.shorten(self.current_npc.backstory, width=30)}"
                ]
                for detail in details:
                    detail_surface = self.font.render(detail, True, WHITE)
                    surface.blit(detail_surface, (details_box_x + 10, details_y))
                    details_y += self.font.get_height() + 3  # Reduced spacing

                # Define bar data with more compact layout
                bars = [
                    ("Friendship", self.current_npc.friendship, 100, (0, 255, 0)),  # Green
                    ("Health", self.current_npc.attributes["health"], 100, (255, 0, 0)),  # Red
                    ("Wealth", self.current_npc.economics["gold"], 500, (255, 215, 0)),  # Gold
                    ("Mana", self.current_npc.attributes["mana"], 100, (0, 0, 255))  # Blue
                ]

                # Find the maximum label width to determine alignment
                max_label_width = max(self.font.size(bar_label)[0] for bar_label, _, _, _ in bars)
                fixed_bar_x = details_box_x + 10 + max_label_width  # Align all bars at the same x-position, immediately after the longest label

                # Render each bar with its label - More compact layout, with pixel-perfect horizontal and vertical alignment
                bar_y = details_y + 5  # Tighter spacing for better alignment, adjusted
                bar_width = 180  # Match screenshot width
                bar_height = 11  # Match screenshot height
                for label, value, max_value, color in bars:
                    # Render label (left-aligned, simple, fully covered, matching your request)
                    label_surface = self.font.render(label, True, WHITE)  # White text on gray, matching your request
                    surface.blit(label_surface, (details_box_x + 10, bar_y))

                    # Calculate vertical position to align bar with text baseline (fine-tuned for pixel-perfect alignment)
                    label_height = label_surface.get_height()  # Get the height of the label text (16px for Arial 16)
                    bar_y_offset = 3  # Fine-tuned offset to align bars with text baseline (adjust if needed for perfection)

                    # Draw bar background (gray, matching background, simple, fully covered, vertically aligned with text)
                    bar_x = fixed_bar_x + 10  # Use fixed position for all bars, aligning them horizontally
                    bar_rect = pygame.Rect(bar_x, bar_y + bar_y_offset, bar_width, bar_height)
                    pygame.draw.rect(surface, (128, 128, 128),  # Gray background, matching your request
                                     bar_rect)

                    # Draw filled portion with screenshot colors, simple, fully covered, vertically aligned with text
                    filled_width = int((value / max_value) * bar_width)
                    pygame.draw.rect(surface, color,
                                     (bar_x, bar_y + bar_y_offset, filled_width, bar_height))

                    # Draw border (optional, thin white border for clarity, simple, fully covered, vertically aligned with text)
                    pygame.draw.rect(surface, WHITE,
                                     (bar_x, bar_y + bar_y_offset, bar_width, bar_height), 1)

                    bar_y += 30  # Slightly tighter spacing for exact match, matching your request, fully covered

            # Draw input box
            input_box = pygame.Rect(
                DIALOG_PADDING,
                input_box_y,
                width - (DIALOG_PADDING * 2),
                input_box_height - 10
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



