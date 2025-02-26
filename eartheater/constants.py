"""Game constants"""
from enum import Enum, auto
from typing import Tuple
import pygame

# Display settings
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TILE_SIZE = 4  # Smaller tiles for finer simulation
FPS = 60

# Physics settings
GRAVITY = 0.25
PLAYER_MOVE_SPEED = 0.7  # Slower for smoother movement
PLAYER_ACCELERATION = 0.1  # Acceleration for smoother movement
PLAYER_FRICTION = 0.9  # Friction for smoother movement
PLAYER_AIR_CONTROL = 0.7  # Less control in air
PLAYER_JETPACK_STRENGTH = 0.4
PLAYER_JETPACK_MAX_FUEL = 100
PLAYER_JETPACK_REGEN_RATE = 0.5
PLAYER_JUMP_STRENGTH = 5
PHYSICS_STEPS_PER_FRAME = 3  # More steps for better simulation

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (64, 108, 220)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BROWN = (139, 69, 19)
GRAY = (128, 128, 128)
SAND_COLOR = (194, 178, 128)
WATER_COLOR = (64, 164, 223, 180)  # Semi-transparent blue
LAVA_COLOR = (207, 16, 32, 200)

# Material types and properties
class MaterialType(Enum):
    AIR = auto()
    DIRT = auto()
    STONE = auto()
    SAND = auto()
    GRAVEL = auto()
    WATER = auto()
    LAVA = auto()
    WOOD = auto()
    
MATERIAL_COLORS = {
    MaterialType.AIR: BLACK,
    MaterialType.DIRT: BROWN,
    MaterialType.STONE: GRAY,
    MaterialType.SAND: SAND_COLOR,
    MaterialType.GRAVEL: (100, 100, 100),
    MaterialType.WATER: WATER_COLOR,
    MaterialType.LAVA: LAVA_COLOR,
    MaterialType.WOOD: (120, 81, 45),
}

# Material physics properties - higher = heavier
MATERIAL_DENSITY = {
    MaterialType.AIR: 0,
    MaterialType.DIRT: 2,
    MaterialType.STONE: 5,
    MaterialType.SAND: 3,
    MaterialType.GRAVEL: 4,
    MaterialType.WATER: 1,
    MaterialType.LAVA: 2,
    MaterialType.WOOD: 1,
}

# Material behavior flags
MATERIAL_FALLS = {
    MaterialType.AIR: False,
    MaterialType.DIRT: True,  # Now dirt can fall too
    MaterialType.STONE: False,
    MaterialType.SAND: True,
    MaterialType.GRAVEL: True,
    MaterialType.WATER: True,
    MaterialType.LAVA: True,
    MaterialType.WOOD: False,
}

# Material liquidity (0 = solid, 1 = very liquid)
MATERIAL_LIQUIDITY = {
    MaterialType.AIR: 0,
    MaterialType.DIRT: 0,
    MaterialType.STONE: 0,
    MaterialType.SAND: 0.3,  # Sand flows a bit
    MaterialType.GRAVEL: 0.2,
    MaterialType.WATER: 0.9,
    MaterialType.LAVA: 0.6,  # Lava flows more slowly
    MaterialType.WOOD: 0,
}

# World generation
CHUNK_SIZE = 32  # Larger chunks
ACTIVE_CHUNKS_RADIUS = 3  # Load only this many chunks around player
WORLD_SEED = 12345  # Seed for procedural generation
CAVE_DENSITY = 0.03  # Higher = more caves
WATER_LEVEL = 80  # Y-coordinate where water starts to appear

# Controls
KEY_LEFT = pygame.K_a
KEY_RIGHT = pygame.K_d
KEY_UP = pygame.K_w
KEY_DOWN = pygame.K_s
KEY_JUMP = pygame.K_SPACE
KEY_JETPACK = pygame.K_SPACE
KEY_DIG = pygame.K_LCTRL
KEY_QUIT = pygame.K_ESCAPE