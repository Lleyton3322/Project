import os
import logging
logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)
logger = logging.getLogger(__name__)


def setup_game_folders():
    """Create necessary folders for the game"""
    logger.debug("Setting up game folders...")

    # Create main directories
    directories = [
        'assets',
        'sprites',
        'sprites/player',
        'sprites/npc',
        'sprites/obstacles'
    ]

    for directory in directories:
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.debug(f"Created directory: {directory}")
            else:
                logger.debug(f"Directory already exists: {directory}")
        except OSError as e:
            logger.error(f"Error creating directory {directory}: {e}")

    # Create a simple test sprite if needed
    sprite_paths = [
        os.path.join('player', 'adventurer.png'),
        os.path.join('obstacles', 'fountain.png')
    ]
    for sprite_path in sprite_paths:
        full_path = os.path.join('sprites', sprite_path)
        if not os.path.exists(full_path):
            logger.warning(f"NOTE: You need to add a sprite at {full_path}")
            logger.warning("The game will use fallback sprites if not present.")

    logger.debug("Folder setup complete. You can now run the game.")


if __name__ == "__main__":
    setup_game_folders()