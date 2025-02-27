# NPC Interaction System

This system allows NPCs in your game to interact with each other using natural language conversations powered by the existing NLP capabilities.

## Features

- NPCs will automatically interact when they come close to each other
- NPCs use their personality traits to generate contextual conversations
- Speech bubbles appear above NPCs during conversations
- NPCs will face each other and move toward each other during conversations
- Interactions influence relationships between NPCs over time
- Personality traits affect relationship development (compatible vs. clashing traits)

## How to Use

1. Place the following files in your game directory:
   - `npc_interaction_system.py`
   - `install_npc_interactions.py`

2. Run the game using the new main file:
   ```
   python main_with_npc_interactions.py
   ```

   Or integrate it manually in your existing code:
   ```python
   # At the top of your file:
   from install_npc_interactions import install_npc_interactions
   
   # Before creating your Game instance:
   install_npc_interactions()
   ```

## Configuration

You can modify these settings in the `NPCInteractionManager` class:

- `interaction_distance` - How close NPCs need to be to interact (default: 120 pixels)
- `interaction_cooldown` - Time between interactions for the same NPCs (default: 15000 ms)
- `interaction_duration` - How long each interaction lasts (default: 3000 ms)

## How It Works

1. The system periodically checks for NPCs that are close to each other and not already in a conversation.
2. When two NPCs are close enough, one initiates a greeting using NLP.
3. The other NPC responds with its own generated dialogue.
4. NPCs will face each other and move slightly closer if needed.
5. Speech bubbles show the conversation to the player.
6. After the interaction ends, each NPC's relationship values are updated.

## Relationship System

NPCs maintain relationship data for other NPCs they've interacted with:

- `familiarity` - Increases with each interaction (0.0 to 1.0)
- `friendship` - Changes based on personality compatibility (-1.0 to 1.0)
- `interactions` - Count of total interactions

Personality traits can be complementary or clashing:
- Complementary traits (ex: friendly + shy) increase friendship
- Clashing traits (ex: serious + playful) decrease friendship

## Further Development Ideas

- Add more complex conversation patterns (questions and answers)
- Display relationship status with icons or visual cues
- Add different interaction types (trading, arguing, etc.)
- Allow player to influence NPC relationships
- Create emergent quests based on NPC relationships
