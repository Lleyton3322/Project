import pygame
import random
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
import math
import json
import os
from game_enums import EventType

logger = logging.getLogger(__name__)


class RelationshipLevel(Enum):
    STRANGER = 0
    ACQUAINTANCE = 1
    FRIENDLY = 2
    FRIEND = 3
    CLOSE_FRIEND = 4


@dataclass
class MemoryEvent:
    """A single memory/event that an NPC remembers about the player"""
    event_type: EventType
    timestamp: int  # Game time when this happened
    location_id: str  # Where it happened
    details: Dict[str, any] = field(default_factory=dict)  # Additional details about the event
    is_positive: bool = True  # Whether this was viewed positively by the NPC
    importance: float = 1.0  # How important this memory is (affects decay rate)

    def age(self, current_time):
        """Calculate how old this memory is"""
        return current_time - self.timestamp

    def get_decay_factor(self, current_time, memory_half_life=10000):
        """Calculate how much this memory has decayed"""
        age = self.age(current_time)
        # Important memories decay slower
        adjusted_half_life = memory_half_life * self.importance
        return math.exp(-age / adjusted_half_life)

    def get_importance(self, current_time):
        """Get the current importance of this memory based on decay"""
        return self.importance * self.get_decay_factor(current_time)

    def to_dict(self):
        """Convert to a dictionary for serialization"""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "location_id": self.location_id,
            "details": self.details,
            "is_positive": self.is_positive,
            "importance": self.importance
        }

    @classmethod
    def from_dict(cls, data):
        """Create a MemoryEvent from a dictionary"""
        return cls(
            event_type=EventType(data["event_type"]),
            timestamp=data["timestamp"],
            location_id=data["location_id"],
            details=data["details"],
            is_positive=data["is_positive"],
            importance=data["importance"]
        )


class NPCRelationshipManager:
    """Manages NPC relationships with the player"""

    def __init__(self, npc):
        self.npc = npc
        self.relationship_level = RelationshipLevel.STRANGER
        self.friendship = 0.0  # 0.0 to 100.0
        self.trust = 0.0  # 0.0 to 100.0
        self.respect = 0.0  # 0.0 to 100.0
        self.fear = 0.0  # 0.0 to 100.0
        self.memories = []
        self.topics_discussed = set()  # Topics already discussed
        self.last_interaction_time = 0
        self.interactions_count = 0

    def add_memory(self, event_type, details, location_id, current_time,
                   is_positive=True, importance=1.0):
        """Add a new memory about the player"""
        # Create the memory event
        memory = MemoryEvent(
            event_type=event_type,
            timestamp=current_time,
            location_id=location_id,
            details=details,
            is_positive=is_positive,
            importance=importance
        )

        # Add to memories list
        self.memories.append(memory)

        # Update relationship based on event
        self._update_relationship_from_event(memory)

        # If this is the first meeting, record it specially
        if event_type == EventType.FIRST_MEETING:
            self.last_interaction_time = current_time

        logger.debug(f"{self.npc.name} formed a new memory about the player: {event_type.value}")
        return memory

    def _update_relationship_from_event(self, memory):
        """Update relationship metrics based on a memory event"""
        base_impact = 5.0 * memory.importance

        if not memory.is_positive:
            base_impact = -base_impact

        # Different events affect different relationship aspects
        if memory.event_type == EventType.FIRST_MEETING:
            # First impressions matter
            self.friendship += base_impact * 0.5
            self.trust += base_impact * 0.3

        elif memory.event_type == EventType.CONVERSATION:
            # Conversations build friendship
            self.friendship += base_impact * 1.0

            # Check if any personal topics were discussed
            if memory.details.get("personal_topic", False):
                self.trust += base_impact * 1.5

        elif memory.event_type == EventType.QUEST_COMPLETED:
            # Completing quests builds respect and trust
            self.respect += base_impact * 2.0
            self.trust += base_impact * 1.0
            self.friendship += base_impact * 0.5

        elif memory.event_type == EventType.QUEST_FAILED:
            # Failed quests damage trust
            self.respect -= base_impact * 1.5
            self.trust -= base_impact * 2.0

        elif memory.event_type == EventType.ITEM_GIFTED:
            # Gifts build friendship
            self.friendship += base_impact * 2.0
            # Value of gift affects impact
            if memory.details.get("value", 0) > 50:
                self.respect += base_impact * 0.5

        elif memory.event_type == EventType.OBSERVED_COMBAT:
            # Seeing player in combat can affect fear and respect
            self.respect += base_impact * 1.0

            if memory.details.get("player_won", False):
                self.fear += base_impact * 0.5

        elif memory.event_type == EventType.HELPED_IN_DANGER:
            # Being helped builds trust and friendship
            self.trust += base_impact * 2.0
            self.friendship += base_impact * 1.5
            self.respect += base_impact * 1.0

        elif memory.event_type == EventType.BETRAYAL:
            # Betrayal severely damages trust
            self.trust -= base_impact * 3.0
            self.friendship -= base_impact * 2.0
            self.fear += base_impact * 1.0

        # Clamp values
        self.friendship = max(0.0, min(100.0, self.friendship))
        self.trust = max(0.0, min(100.0, self.trust))
        self.respect = max(0.0, min(100.0, self.respect))
        self.fear = max(0.0, min(100.0, self.fear))

        # Update relationship level
        self._update_relationship_level()

    def _update_relationship_level(self):
        """Update the relationship level based on current metrics"""
        combined = self.friendship + self.trust + self.respect

        if combined < 30:
            self.relationship_level = RelationshipLevel.STRANGER
        elif combined < 90:
            self.relationship_level = RelationshipLevel.ACQUAINTANCE
        elif combined < 150:
            self.relationship_level = RelationshipLevel.FRIENDLY
        elif combined < 220:
            self.relationship_level = RelationshipLevel.FRIEND
        else:
            self.relationship_level = RelationshipLevel.CLOSE_FRIEND

    def get_important_memories(self, current_time, max_count=3):
        """Get the most important memories an NPC has about the player"""
        # Calculate current importance of each memory based on decay
        with_importance = [
            (memory, memory.get_importance(current_time))
            for memory in self.memories
        ]

        # Sort by current importance (descending)
        with_importance.sort(key=lambda x: x[1], reverse=True)

        # Return the most important memories (limited by max_count)
        return [memory for memory, importance in with_importance[:max_count]]

    def get_potential_conversation_topics(self, current_time):
        """Get topics the NPC might want to talk about based on memories"""
        important_memories = self.get_important_memories(current_time, 5)
        topics = []

        for memory in important_memories:
            # Skip already discussed topics for this conversation
            if memory.event_type.value in self.topics_discussed:
                continue

            # Create a topic based on memory type
            if memory.event_type == EventType.QUEST_COMPLETED:
                topics.append({
                    "type": "quest_reference",
                    "quest_id": memory.details.get("quest_id", "unknown"),
                    "text": f"I'm still grateful for your help with that {memory.details.get('quest_name', 'task')}.",
                    "importance": memory.get_importance(current_time)
                })

            elif memory.event_type == EventType.OBSERVED_COMBAT:
                topics.append({
                    "type": "combat_reference",
                    "enemy_type": memory.details.get("enemy_type", "creature"),
                    "text": f"I saw you fighting that {memory.details.get('enemy_type', 'creature')} at {memory.location_id}. Impressive!",
                    "importance": memory.get_importance(current_time)
                })

            elif memory.event_type == EventType.VISITED_LOCATION:
                topics.append({
                    "type": "location_reference",
                    "location": memory.location_id,
                    "text": f"I heard you visited {memory.location_id}. What did you think of it?",
                    "importance": memory.get_importance(current_time)
                })

            elif memory.event_type == EventType.ITEM_GIFTED:
                topics.append({
                    "type": "gift_reference",
                    "item_name": memory.details.get("item_name", "gift"),
                    "text": f"That {memory.details.get('item_name', 'gift')} you gave me has been very useful.",
                    "importance": memory.get_importance(current_time)
                })

        # Add relationship-based topics
        if self.relationship_level == RelationshipLevel.ACQUAINTANCE:
            topics.append({
                "type": "relationship",
                "text": "Nice to see you again. I remember you from before.",
                "importance": 0.7
            })
        elif self.relationship_level == RelationshipLevel.FRIENDLY:
            topics.append({
                "type": "relationship",
                "text": "Good to see a familiar face around here!",
                "importance": 0.8
            })
        elif self.relationship_level == RelationshipLevel.FRIEND:
            topics.append({
                "type": "relationship",
                "text": "My friend! It's always good to see you.",
                "importance": 0.9
            })
        elif self.relationship_level == RelationshipLevel.CLOSE_FRIEND:
            topics.append({
                "type": "relationship",
                "text": "There you are! I was hoping to see you today.",
                "importance": 1.0
            })

        # Sort by importance
        topics.sort(key=lambda x: x["importance"], reverse=True)
        return topics

    def get_greeting(self, current_time):
        """Get an appropriate greeting based on relationship level and memories"""
        # Time since last interaction
        time_diff = current_time - self.last_interaction_time
        long_time = time_diff > 50000  # Adjust based on your game time scale

        # First meeting
        if not self.memories:
            return f"Hello there, I don't believe we've met. I'm {self.npc.name}."

        # Get general greeting based on relationship level
        if self.relationship_level == RelationshipLevel.STRANGER:
            greeting = f"Hello. Can I help you with something?"
        elif self.relationship_level == RelationshipLevel.ACQUAINTANCE:
            if long_time:
                greeting = f"Oh, it's you again. Been a while."
            else:
                greeting = f"Hello again. What brings you back?"
        elif self.relationship_level == RelationshipLevel.FRIENDLY:
            if long_time:
                greeting = f"Well look who it is! Been ages since I've seen you around."
            else:
                greeting = f"Good to see you again! How have you been?"
        elif self.relationship_level == RelationshipLevel.FRIEND:
            if long_time:
                greeting = f"My friend! Where have you been all this time? I've missed our chats."
            else:
                greeting = f"Hey there, friend! Always a pleasure to see you."
        elif self.relationship_level == RelationshipLevel.CLOSE_FRIEND:
            if long_time:
                greeting = f"There you are! I was beginning to worry something had happened to you."
            else:
                greeting = f"Hey! Just the person I wanted to see. How's everything?"

        # Get most recent important memory to reference
        important_memories = self.get_important_memories(current_time, 1)
        if important_memories:
            memory = important_memories[0]

            # Add a reference to the memory if appropriate
            if memory.event_type == EventType.QUEST_COMPLETED and memory.is_positive:
                greeting += f" Still grateful for your help with that {memory.details.get('quest_name', 'quest')}."
            elif memory.event_type == EventType.ITEM_GIFTED and memory.is_positive:
                greeting += f" That {memory.details.get('item_name', 'gift')} you gave me has been quite useful."
            elif memory.event_type == EventType.HELPED_IN_DANGER:
                greeting += f" I still owe you for helping me out of that tight spot."

        # Update interaction tracking
        self.last_interaction_time = current_time
        self.interactions_count += 1
        self.topics_discussed = set()  # Reset discussed topics for new conversation

        return greeting

    def mark_topic_discussed(self, topic_type):
        """Mark a topic as having been discussed in the current conversation"""
        self.topics_discussed.add(topic_type)

    def to_dict(self):
        """Convert to a dictionary for serialization"""
        return {
            "npc_id": self.npc.entity_id,
            "relationship_level": self.relationship_level.value,
            "friendship": self.friendship,
            "trust": self.trust,
            "respect": self.respect,
            "fear": self.fear,
            "memories": [memory.to_dict() for memory in self.memories],
            "last_interaction_time": self.last_interaction_time,
            "interactions_count": self.interactions_count
        }

    @classmethod
    def from_dict(cls, data, npc):
        """Create a RelationshipManager from a dictionary"""
        manager = cls(npc)
        manager.relationship_level = RelationshipLevel(data["relationship_level"])
        manager.friendship = data["friendship"]
        manager.trust = data["trust"]
        manager.respect = data["respect"]
        manager.fear = data["fear"]
        manager.memories = [MemoryEvent.from_dict(memory_data) for memory_data in data["memories"]]
        manager.last_interaction_time = data["last_interaction_time"]
        manager.interactions_count = data["interactions_count"]
        return manager


class PlayerMemorySystem:
    """Manages all NPC memories and relationships with the player"""

    def __init__(self, save_path="player_relationships.json"):
        self.npc_relationships = {}  # NPC ID -> RelationshipManager
        self.save_path = save_path
        self.global_events = []  # Events that all NPCs should know about

    def get_relationship_manager(self, npc):
        """Get (or create) a relationship manager for an NPC"""
        if npc.entity_id not in self.npc_relationships:
            self.npc_relationships[npc.entity_id] = NPCRelationshipManager(npc)
        return self.npc_relationships[npc.entity_id]

    def record_event(self, event_type, player, details, location_id,
                     current_time, npc=None, witnesses=None, is_global=False,
                     is_positive=True, importance=1.0):
        """
        Record an event involving the player

        Parameters:
            event_type: Type of event from EventType enum
            player: Player object
            details: Dictionary of event-specific details
            location_id: ID of location where event occurred
            current_time: Current game time
            npc: Specific NPC involved (if any)
            witnesses: List of NPCs who witnessed the event
            is_global: Whether all NPCs should learn about this event
            is_positive: Whether the event is viewed positively
            importance: How important the event is (affects memory decay)
        """
        # Record for specific NPC if provided
        if npc:
            relationship = self.get_relationship_manager(npc)
            relationship.add_memory(
                event_type, details, location_id, current_time,
                is_positive, importance
            )

        # Record for witnesses
        if witnesses:
            for witness in witnesses:
                if witness != npc:  # Skip if already recorded
                    relationship = self.get_relationship_manager(witness)
                    # Witnesses have a slightly different perspective (less important)
                    witness_importance = importance * 0.7
                    relationship.add_memory(
                        event_type, details, location_id, current_time,
                        is_positive, witness_importance
                    )

        # Record global events for word-of-mouth sharing
        if is_global:
            self.global_events.append({
                "event_type": event_type,
                "details": details,
                "location_id": location_id,
                "timestamp": current_time,
                "is_positive": is_positive,
                "importance": importance * 0.5  # Less important as hearsay
            })

    def update_npc_knowledge(self, npc, current_time, chance_to_know=0.3):
        """Update an NPC's knowledge with relevant global events through gossip"""
        relationship = self.get_relationship_manager(npc)

        # Skip if NPC already has many memories
        if len(relationship.memories) > 20:
            return

        # Check each global event
        for event in self.global_events:
            # Skip if too recent (news takes time to spread)
            if current_time - event["timestamp"] < 5000:
                continue

            # Skip if too old (old news gets forgotten)
            if current_time - event["timestamp"] > 100000:
                continue

            # Chance to know depends on:
            # 1. Base chance parameter
            # 2. Event importance (more important = more likely to know)
            # 3. Time since event (more recent = more likely to know)
            time_factor = 1.0 - ((current_time - event["timestamp"]) / 100000)
            importance_factor = event["importance"]
            knowledge_chance = chance_to_know * importance_factor * time_factor

            # Random check if NPC knows this event
            if random.random() < knowledge_chance:
                # NPC heard about this event
                relationship.add_memory(
                    EventType(event["event_type"]),
                    event["details"],
                    event["location_id"],
                    event["timestamp"],  # Use original timestamp
                    event["is_positive"],
                    event["importance"]
                )
                logger.debug(f"{npc.name} heard about event {event['event_type']} through gossip")

    def save_relationships(self):
        """Save all NPC relationships to a file"""
        try:
            data = {
                npc_id: relationship.to_dict()
                for npc_id, relationship in self.npc_relationships.items()
            }

            # Also save global events
            data["global_events"] = self.global_events

            with open(self.save_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved {len(self.npc_relationships)} NPC relationships to {self.save_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving NPC relationships: {e}")
            return False

    def load_relationships(self, npcs_by_id):
        """
        Load NPC relationships from a file

        Parameters:
            npcs_by_id: Dictionary mapping NPC IDs to NPC objects
        """
        if not os.path.exists(self.save_path):
            logger.info(f"No relationship file found at {self.save_path}")
            return False

        try:
            with open(self.save_path, 'r') as f:
                data = json.load(f)

            # Load global events
            if "global_events" in data:
                self.global_events = data["global_events"]
                del data["global_events"]

            # Load relationships
            for npc_id, relationship_data in data.items():
                if npc_id in npcs_by_id:
                    npc = npcs_by_id[npc_id]
                    self.npc_relationships[npc_id] = NPCRelationshipManager.from_dict(
                        relationship_data, npc
                    )

            logger.info(f"Loaded {len(self.npc_relationships)} NPC relationships from {self.save_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading NPC relationships: {e}")
            return False


# Extension of NPC class with memory system
def enhance_npc_with_memory(npc, memory_system, current_time):
    """Extend an NPC with memory and relationship features"""
    # Add relationship manager attribute if not present
    if not hasattr(npc, 'relationship_manager'):
        npc.relationship_manager = memory_system.get_relationship_manager(npc)

    # Add advanced dialogue methods if not present
    if not hasattr(npc, 'get_player_greeting'):
        def get_player_greeting(current_time):
            """Get a greeting for the player based on their relationship"""
            return npc.relationship_manager.get_greeting(current_time)

        npc.get_player_greeting = get_player_greeting

    if not hasattr(npc, 'get_conversation_topics'):
        def get_conversation_topics(current_time):
            """Get topics this NPC might want to discuss with player"""
            return npc.relationship_manager.get_potential_conversation_topics(current_time)

        npc.get_conversation_topics = get_conversation_topics

    if not hasattr(npc, 'record_player_interaction'):
        def record_player_interaction(event_type, details, location_id, is_positive=True, importance=1.0):
            """Record an interaction with the player"""
            npc.relationship_manager.add_memory(
                event_type, details, location_id, current_time, is_positive, importance
            )

        npc.record_player_interaction = record_player_interaction

    # Update NPC with global knowledge
    memory_system.update_npc_knowledge(npc, current_time)

    return npc


# Example usage
def example_conversation(npc, player, memory_system, current_time, location_id):
    """Example of how to use the memory system in a conversation"""
    # Ensure NPC has memory features
    enhance_npc_with_memory(npc, memory_system, current_time)

    # First meeting?
    if not npc.relationship_manager.memories:
        # Record first meeting
        memory_system.record_event(
            EventType.FIRST_MEETING,
            player,
            {"initial_impression": "neutral"},
            location_id,
            current_time,
            npc=npc
        )
        greeting = f"Hello there, I don't believe we've met. I'm {npc.name}."
    else:
        # Get greeting based on relationship
        greeting = npc.get_player_greeting(current_time)

    print(f"{npc.name}: {greeting}")

    # Get potential conversation topics
    topics = npc.get_conversation_topics(current_time)
    if topics:
        topic = topics[0]  # Use most important topic
        print(f"{npc.name}: {topic['text']}")
        npc.relationship_manager.mark_topic_discussed(topic['type'])

    # Record this conversation
    memory_system.record_event(
        EventType.CONVERSATION,
        player,
        {"length": "short", "personal_topic": False},
        location_id,
        current_time,
        npc=npc
    )