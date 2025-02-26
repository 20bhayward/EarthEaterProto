"""Game constants"""
from enum import Enum, auto
from typing import Tuple

# Display settings
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TILE_SIZE = 8
FPS = 60

# Physics settings
GRAVITY = 0.5
PLAYER_MOVE_SPEED = 3
PLAYER_JUMP_STRENGTH = 8
PHYSICS_STEPS_PER_FRAME = 1

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BROWN = (139, 69, 19)
GRAY = (128, 128, 128)

# Material types and properties
class MaterialType(Enum):
    AIR = auto()
    DIRT = auto()
    STONE = auto()
    SAND = auto()
    
MATERIAL_COLORS = {
    MaterialType.AIR: BLACK,
    MaterialType.DIRT: BROWN,
    MaterialType.STONE: GRAY,
    MaterialType.SAND: (194, 178, 128),
}

# Material physics properties
MATERIAL_DENSITY = {
    MaterialType.AIR: 0,
    MaterialType.DIRT: 2,
    MaterialType.STONE: 5,
    MaterialType.SAND: 3,
}

# Material behavior flags
MATERIAL_FALLS = {
    MaterialType.AIR: False,
    MaterialType.DIRT: False,
    MaterialType.STONE: False,
    MaterialType.SAND: True,
}

# World generation
CHUNK_SIZE = 16
WORLD_WIDTH_CHUNKS = 10
WORLD_HEIGHT_CHUNKS = 8
WORLD_WIDTH = WORLD_WIDTH_CHUNKS * CHUNK_SIZE
WORLD_HEIGHT = WORLD_HEIGHT_CHUNKS * CHUNK_SIZE