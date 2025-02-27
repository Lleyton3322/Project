import os
import pygame
import logging

logger = logging.getLogger(__name__)


class SpriteManager:
    def __init__(self):
        self.cache = {}
        # Create a directory structure if it doesn't exist
        for dir_path in ['sprites', 'sprites/obstacles', 'sprites/player', 'sprites/npc']:
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path)
                    logger.info(f"Created directory: {dir_path}")
                except Exception as e:
                    logger.error(f"Error creating directory {dir_path}: {e}")

    def load_sprite(self, path, scale=(100, 100)):
        """Load a single sprite with better error handling"""
        # Use the full path as the cache key
        cache_key = (path, scale)

        if cache_key not in self.cache:
            try:
                # First try with sprites/ prefix
                full_path = os.path.join('sprites', path)

                # If that doesn't exist, try direct path (might be a full path already)
                if not os.path.exists(full_path) and os.path.exists(path):
                    full_path = path

                # Check if file exists
                if os.path.exists(full_path):
                    logger.debug(f"Loading sprite from {full_path}")
                    sprite = pygame.image.load(full_path).convert_alpha()

                    # Scale if needed
                    if sprite.get_width() != scale[0] or sprite.get_height() != scale[1]:
                        sprite = pygame.transform.scale(sprite, scale)

                    self.cache[cache_key] = sprite
                else:
                    #logger.warning(f"Sprite not found at {full_path}, using fallback")
                    self.cache[cache_key] = self._create_fallback_sprite(scale, "missing_file")
            except Exception as e:
                logger.error(f"Error loading sprite {path}: {e}")
                self.cache[cache_key] = self._create_fallback_sprite(scale, "load_error")

        return self.cache[cache_key]

    def load_sprite_sheet(self, path, cols, rows, scale=(100, 100), padding_x=0, padding_y=0):
        """Load a sprite sheet with improved error handling and precise frame extraction"""
        # Create a unique cache key
        cache_key = (path, cols, rows, scale, padding_x, padding_y)

        if cache_key not in self.cache:
            try:
                # Try with sprites/ prefix first
                full_path = os.path.join('sprites', path)

                # If that fails, try direct path
                if not os.path.exists(full_path) and os.path.exists(path):
                    full_path = path

                if not os.path.exists(full_path):
                    logger.warning(f"Sprite sheet not found at {full_path}")
                    # Return a list of fallback sprites (one per expected frame)
                    self.cache[cache_key] = [self._create_fallback_sprite(scale, "missing_file")
                                             for _ in range(cols * rows)]
                    return self.cache[cache_key]

                # Load the sprite sheet
                sprite_sheet = pygame.image.load(full_path).convert_alpha()
                sheet_width, sheet_height = sprite_sheet.get_size()

                # Calculate frame dimensions based on sheet size and grid
                frame_width = (sheet_width - (cols - 1) * padding_x) // cols
                frame_height = (sheet_height - (rows - 1) * padding_y) // rows

                # Log for debugging
                logger.debug(f"Sheet: {sheet_width}x{sheet_height}, Grid: {cols}x{rows}, " +
                             f"Frame: {frame_width}x{frame_height}, Padding: {padding_x}x{padding_y}")

                # Extract all frames
                frames = []
                for row in range(rows):
                    for col in range(cols):
                        try:
                            # Calculate position with padding
                            x = col * (frame_width + padding_x)
                            y = row * (frame_height + padding_y)

                            # Ensure we don't exceed boundaries
                            if x + frame_width <= sheet_width and y + frame_height <= sheet_height:
                                # Create a new surface for this frame
                                frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)

                                # Copy the region from the sheet to the frame
                                frame.blit(sprite_sheet, (0, 0), (x, y, frame_width, frame_height))

                                # Scale the frame if needed
                                if scale != (frame_width, frame_height):
                                    frame = pygame.transform.scale(frame, scale)

                                frames.append(frame)
                            else:
                                logger.warning(f"Frame at ({col}, {row}) exceeds sprite sheet boundaries")
                                frames.append(self._create_fallback_sprite(scale, "boundary_error"))
                        except Exception as e:
                            logger.error(f"Error extracting frame at ({col}, {row}): {e}")
                            frames.append(self._create_fallback_sprite(scale, "extract_error"))

                # Cache the extracted frames
                self.cache[cache_key] = frames
                logger.debug(f"Successfully extracted {len(frames)} frames from {path}")

            except Exception as e:
                logger.error(f"Error loading sprite sheet {path}: {e}")
                # Return a list of fallback sprites
                self.cache[cache_key] = [self._create_fallback_sprite(scale, "load_error")
                                         for _ in range(cols * rows)]

        return self.cache[cache_key]

    def _create_fallback_sprite(self, size, error_type="unknown"):
        """Create a more informative fallback sprite that's less jarring than solid red"""
        # Create a transparent surface
        sprite = pygame.Surface(size, pygame.SRCALPHA)

        # Choose a color based on error type (less jarring than bright red)
        if error_type == "missing_file":
            color = (150, 150, 150, 180)  # Gray for missing files
        elif error_type == "load_error":
            color = (150, 100, 100, 180)  # Muted red for load errors
        elif error_type == "boundary_error":
            color = (100, 100, 150, 180)  # Muted blue for boundary errors
        elif error_type == "extract_error":
            color = (150, 150, 100, 180)  # Muted yellow for extract errors
        else:
            color = (120, 120, 120, 180)  # Default gray

        # Fill with semi-transparent color
        sprite.fill(color)

        # Add pattern or text to indicate it's a fallback (simple pattern)
        for i in range(0, size[0], 10):
            for j in range(0, size[1], 10):
                if (i + j) % 20 == 0:
                    pygame.draw.rect(sprite, (0, 0, 0, 100),
                                     (i, j, 5, 5))

        # Draw border
        pygame.draw.rect(sprite, (0, 0, 0, 100),
                         (0, 0, size[0], size[1]), 2)

        return sprite