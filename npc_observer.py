import math
import logging
from game_enums import EventType, Direction

logger = logging.getLogger(__name__)


class NPCObserverSystem:
    """System for NPCs to observe and react to player actions in the world"""

    def __init__(self, memory_system):
        self.memory_system = memory_system
        self.observation_radius = 300  # Pixels - how far NPCs can see
        self.last_check_time = 0
        self.check_interval = 1000  # ms between observation checks

        # Track events to avoid duplicates
        self.recent_observations = {}

        # Track player's notable actions
        self.player_kills = {}
        self.player_items = set()
        self.player_locations = set()
        self.player_quests = {}

    def update(self, game_map, player, current_time):
        """Update NPC observations of the player"""
        # Only check periodically to save performance
        if current_time - self.last_check_time < self.check_interval:
            return

        self.last_check_time = current_time

        # Find NPCs in observation range of player
        witnesses = self._get_witnesses(game_map, player)

        # Check what these NPCs might observe
        self._check_player_observations(witnesses, player, game_map, current_time)

        # Clean up old recent observations
        self._clean_old_observations(current_time)

    def _get_witnesses(self, game_map, player):
        """Find NPCs who can see the player right now"""
        witnesses = []

        for npc in game_map.npcs:
            # Calculate distance to player
            dx = npc.x - player.x
            dy = npc.y - player.y
            distance = math.sqrt(dx * dx + dy * dy)

            # Check if in observation range
            if distance <= self.observation_radius:
                # Check if NPC is facing approximately the right direction
                is_facing_player = self._is_facing_towards(npc, player)

                # Either very close or facing the right way
                if distance <= self.observation_radius * 0.5 or is_facing_player:
                    witnesses.append(npc)

        return witnesses

    def _is_facing_towards(self, npc, target):
        """Check if an NPC is facing roughly towards a target"""
        # Calculate direction vector to target
        dx = target.x - npc.x
        dy = target.y - npc.y

        # Determine primary direction (N, E, S, W)
        if abs(dx) > abs(dy):
            # Primarily East/West
            target_dir = Direction.RIGHT if dx > 0 else Direction.LEFT
        else:
            # Primarily North/South
            target_dir = Direction.DOWN if dy > 0 else Direction.UP

        # Check if NPC is facing that direction
        return npc.direction == target_dir

    def _check_player_observations(self, witnesses, player, game_map, current_time):
        """Check what witnesses might observe about the player"""
        # Skip if no witnesses
        if not witnesses:
            return

        current_room = game_map.get_room_at_position(player.x, player.y)
        location_id = current_room.room_id if current_room else "unknown"

        # Check if player has new equipment or items
        for item in player.inventory:
            if item.entity_id not in self.player_items:
                # New item acquisition
                self.player_items.add(item.entity_id)

                # Only record for valuable or unique items
                if item.value > 50 or 'unique' in item.entity_id:
                    self._record_item_observation(
                        witnesses, player, item, location_id, current_time
                    )

        # Check if player is in combat (simplified)
        if hasattr(player, 'in_combat') and player.in_combat:
            self._record_combat_observation(
                witnesses, player, location_id, current_time
            )

        # Check if player is in a new location
        if location_id not in self.player_locations:
            self.player_locations.add(location_id)
            self._record_location_observation(
                witnesses, player, location_id, current_time
            )

        # Check for special zone actions based on location
        self._check_special_zone_actions(
            witnesses, player, location_id, current_time
        )

    def _record_item_observation(self, witnesses, player, item, location_id, current_time):
        """Record observation of player with a notable item"""
        event_key = f"item_{item.entity_id}_{current_time // 10000}"

        # Skip if recently observed
        if event_key in self.recent_observations:
            return

        # Record this observation
        self.recent_observations[event_key] = current_time

        # Create event details
        details = {
            "item_id": item.entity_id,
            "item_name": item.name,
            "item_value": item.value,
            "is_equipped": hasattr(player, 'equipped_items') and item in player.equipped_items
        }

        # Record event for witnesses
        self.memory_system.record_event(
            EventType.VISITED_LOCATION,
            player,
            details,
            location_id,
            current_time,
            witnesses=witnesses,
            is_global=item.value > 100  # Very valuable items become gossip
        )

        logger.debug(f"{len(witnesses)} NPCs observed player with {item.name}")

    def _record_combat_observation(self, witnesses, player, location_id, current_time):
        """Record observation of player in combat"""
        # Get enemy info if available
        enemy_type = "unknown"
        player_won = False

        if hasattr(player, 'combat_target'):
            enemy_type = getattr(player.combat_target, 'name', 'creature')
            player_won = getattr(player, 'won_last_combat', False)

        event_key = f"combat_{enemy_type}_{current_time // 10000}"

        # Skip if recently observed
        if event_key in self.recent_observations:
            return

        # Record this observation
        self.recent_observations[event_key] = current_time

        # Create event details
        details = {
            "enemy_type": enemy_type,
            "player_won": player_won,
            "was_difficult": getattr(player, 'last_combat_difficult', False)
        }

        # Record event for witnesses
        self.memory_system.record_event(
            EventType.OBSERVED_COMBAT,
            player,
            details,
            location_id,
            current_time,
            witnesses=witnesses,
            is_global=True  # Combat is notable and becomes gossip
        )

        logger.debug(f"{len(witnesses)} NPCs observed player fighting {enemy_type}")

        # Keep track of player kills
        if player_won:
            if enemy_type not in self.player_kills:
                self.player_kills[enemy_type] = 0
            self.player_kills[enemy_type] += 1

    def _record_location_observation(self, witnesses, player, location_id, current_time):
        """Record observation of player visiting a location"""
        event_key = f"location_{location_id}_{current_time // 30000}"

        # Skip if recently observed
        if event_key in self.recent_observations:
            return

        # Record this observation
        self.recent_observations[event_key] = current_time

        # Create event details
        details = {
            "first_visit": location_id not in self.player_locations,
            "location_name": location_id
        }

        # Record event for witnesses
        self.memory_system.record_event(
            EventType.VISITED_LOCATION,
            player,
            details,
            location_id,
            current_time,
            witnesses=witnesses,
            is_global=False  # Ordinary location visits aren't gossip
        )

        logger.debug(f"{len(witnesses)} NPCs observed player at {location_id}")

    def _check_special_zone_actions(self, witnesses, player, location_id, current_time):
        """Check for player actions specific to special zones"""
        # Fountain interaction
        if location_id == "town_square" and self._is_near_fountain(player):
            event_key = f"fountain_interact_{current_time // 20000}"

            # Skip if recently observed
            if event_key in self.recent_observations:
                return

            # Record this observation
            self.recent_observations[event_key] = current_time

            # Create event details
            details = {
                "interacted_with": "fountain",
                "action": "observed"
            }

            # Record event for witnesses
            self.memory_system.record_event(
                EventType.VISITED_LOCATION,
                player,
                details,
                location_id,
                current_time,
                witnesses=witnesses,
                is_global=False
            )

            logger.debug(f"{len(witnesses)} NPCs observed player at the fountain")

    def _is_near_fountain(self, player):
        """Check if player is near the fountain"""
        # This could be more sophisticated with actual fountain coordinates
        # For now, just check if player is in a certain area of town_square
        fountain_x, fountain_y = 500, 500  # Approximate center of the town square
        dx = player.x - fountain_x
        dy = player.y - fountain_y
        distance = math.sqrt(dx * dx + dy * dy)
        return distance < 100  # Within 100 pixels of fountain

    def _clean_old_observations(self, current_time):
        """Remove old observations from tracking to prevent memory buildup"""
        to_remove = []

        for event_key, timestamp in self.recent_observations.items():
            # Remove observations older than 5 minutes
            if current_time - timestamp > 300000:
                to_remove.append(event_key)

        for key in to_remove:
            del self.recent_observations[key]

        if to_remove:
            logger.debug(f"Cleaned {len(to_remove)} old NPC observations")

    def record_player_quest_progress(self, player, quest_id, stage, quest_name, location_id, current_time):
        """Record player progress on a quest"""
        # Update quest tracking
        self.player_quests[quest_id] = stage

        # Handle quest acceptance
        if stage == "accepted":
            self.memory_system.record_event(
                EventType.QUEST_ACCEPTED,
                player,
                {"quest_id": quest_id, "quest_name": quest_name},
                location_id,
                current_time,
                is_global=True  # New quests are noteworthy
            )

        # Handle quest completion
        elif stage == "completed":
            self.memory_system.record_event(
                EventType.QUEST_COMPLETED,
                player,
                {"quest_id": quest_id, "quest_name": quest_name},
                location_id,
                current_time,
                is_global=True  # Completed quests are noteworthy
            )

        # Handle quest failure
        elif stage == "failed":
            self.memory_system.record_event(
                EventType.QUEST_FAILED,
                player,
                {"quest_id": quest_id, "quest_name": quest_name},
                location_id,
                current_time,
                is_global=True  # Failed quests are noteworthy
            )

    def record_player_helped_npc(self, player, npc, location_id, current_time, help_type="general"):
        """Record when player helps an NPC"""
        # Find nearby NPCs who witnessed this
        witnesses = self._get_witnesses_near_npc(npc)

        # Create event details
        details = {
            "npc_id": npc.entity_id,
            "npc_name": npc.name,
            "help_type": help_type
        }

        # Record event both for the helped NPC and witnesses
        self.memory_system.record_event(
            EventType.HELPED_IN_DANGER,
            player,
            details,
            location_id,
            current_time,
            npc=npc,  # The NPC who was helped
            witnesses=witnesses,  # Other NPCs who saw it
            is_global=True,  # This is notable
            is_positive=True,
            importance=2.0  # Being helped is very memorable
        )

        logger.debug(f"Player helped {npc.name}, witnessed by {len(witnesses)} NPCs")

    def _get_witnesses_near_npc(self, npc):
        """Find NPCs near another NPC (potential witnesses)"""
        witnesses = []

        # This would use your game's NPC list
        # For example, game_map.npcs
        return witnesses  # Placeholder