"""Game constants"""
from enum import Enum, auto
from typing import Tuple
import pygame

# Display settings
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
TILE_SIZE = 2  # Balanced for performance and resolution
FULLSCREEN = True
TERMINAL_GREEN = (0, 255, 128)  # Terminal green color
FPS = 60

# Physics settings
GRAVITY = 0.15  # Reduced gravity for fluid movement
PLAYER_MOVE_SPEED = 0.8  # More controlled movement
PLAYER_ACCELERATION = 0.1  # More gradual acceleration
PLAYER_FRICTION = 0.9  # More friction for tighter control
PLAYER_AIR_CONTROL = 0.6  # Reduced air control
PLAYER_JETPACK_STRENGTH = 0.15  # Reduced jetpack strength
PLAYER_JETPACK_MAX_FUEL = 300  # More fuel since it's weaker
PLAYER_JETPACK_REGEN_RATE = 0.6  # Slower regen
PLAYER_JUMP_STRENGTH = 2.5  # Reduced jump height
PHYSICS_STEPS_PER_FRAME = 1  # Single physics step for maximum performance
PHYSICS_UPDATE_FREQUENCY = 8  # Process 1/8 of the world each frame (higher value = better performance)

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

# Material hardness (higher = harder to dig)
MATERIAL_HARDNESS = {
    MaterialType.AIR: 0,
    MaterialType.DIRT: 1,
    MaterialType.STONE: 3,
    MaterialType.SAND: 1.2,
    MaterialType.GRAVEL: 2,
    MaterialType.WATER: 0,
    MaterialType.LAVA: 0,
    MaterialType.WOOD: 2.5,
}

# World generation
CHUNK_SIZE = 64  # Much larger chunks for better performance
ACTIVE_CHUNKS_RADIUS = 6  # More chunks to fill the larger screen
WORLD_SEED = 12345  # Seed for procedural generation
CAVE_DENSITY = 0.03  # Higher = more caves
WATER_LEVEL = 120  # Lower water level to avoid water at spawn
TERRAIN_AMPLITUDE = 30  # Controls the height of hills
DIRT_LAYER_DEPTH = 15  # Thicker dirt layer before stone
SAFE_ZONE_RADIUS = 60  # No water within this radius of spawn

# Sky settings
SKY_COLOR_TOP = (92, 148, 252)  # Brighter blue
SKY_COLOR_HORIZON = (210, 230, 255)  # Bright pale blue
UNDERGROUND_COLOR = (25, 20, 35)  # Lighter underground for better visibility

# Sun settings
SUN_COLOR = (255, 245, 180)  # Bright yellow/white
SUN_RADIUS = 45  # Larger sun size in pixels
SUN_RAY_LENGTH = 250  # Longer sun rays for better lighting
SUN_INTENSITY = 2.5  # Higher light intensity

# Controls
KEY_LEFT = pygame.K_a
KEY_RIGHT = pygame.K_d
KEY_UP = pygame.K_w
KEY_DOWN = pygame.K_s
KEY_JUMP = pygame.K_SPACE
KEY_JETPACK = pygame.K_SPACE
KEY_DIG = pygame.K_LCTRL  # Keep this as secondary option
KEY_DIG_MOUSE = 1  # Left mouse button (pygame.MOUSEBUTTONDOWN value)
KEY_QUIT = pygame.K_ESCAPE