"""Game constants"""
from enum import Enum, auto
import random
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
    GRASS = auto()
    CLAY = auto()
    SANDSTONE = auto()
    GRANITE = auto()
    COAL = auto()
    IRON = auto()
    GOLD = auto()
    MARBLE = auto()
    OBSIDIAN = auto()
    ICE = auto()
    MOSS = auto()
    
MATERIAL_COLORS = {
    MaterialType.AIR: BLACK,
    MaterialType.DIRT: BROWN,
    MaterialType.STONE: GRAY,
    MaterialType.SAND: SAND_COLOR,
    MaterialType.GRAVEL: (100, 100, 100),
    MaterialType.WATER: WATER_COLOR,
    MaterialType.LAVA: LAVA_COLOR,
    MaterialType.WOOD: (120, 81, 45),
    MaterialType.GRASS: (67, 160, 71),
    MaterialType.CLAY: (136, 84, 11),
    MaterialType.SANDSTONE: (220, 195, 160),
    MaterialType.GRANITE: (120, 110, 120),
    MaterialType.COAL: (45, 45, 45),
    MaterialType.IRON: (165, 156, 148),
    MaterialType.GOLD: (212, 175, 55),
    MaterialType.MARBLE: (225, 225, 235),
    MaterialType.OBSIDIAN: (35, 25, 40),
    MaterialType.ICE: (164, 220, 250),
    MaterialType.MOSS: (80, 130, 70),
}

# Biome types
class BiomeType(Enum):
    MEADOW = auto()
    MOUNTAIN = auto()
    DESERT = auto()
    FOREST = auto()
    UNDERGROUND = auto()
    DEPTHS = auto()
    ABYSS = auto()
    VOLCANIC = auto()
    CRYSTAL_CAVES = auto()
    FROZEN_CAVES = auto()

# World generation settings
class WorldGenSettings:
    def __init__(self):
        self.seed = random.randint(1, 100000)
        self.world_size = "medium"  # small, medium, large
        self.terrain_roughness = 0.5  # 0.0 to 1.0
        self.ore_density = 0.5  # 0.0 to 1.0
        self.water_level = 0.4  # 0.0 to 1.0
        self.cave_density = 0.5  # 0.0 to 1.0
        self.has_mountains = True
        self.has_desert = True
        self.has_forest = False
        self.has_volcanic = True
        self.has_ice = False
        
    def get_terrain_amplitude(self):
        """Get terrain amplitude based on roughness"""
        base = 30  # Base amplitude
        return int(base + (base * self.terrain_roughness))
        
    def get_water_level(self):
        """Get water level based on setting"""
        return int(70 + (self.water_level * 50))
        
    def get_cave_density(self):
        """Get cave density factor"""
        return 0.02 + (self.cave_density * 0.08)  # 0.02 to 0.1
        
    def get_ore_frequency(self):
        """Get ore spawn frequency multiplier"""
        return self.ore_density
        
    def get_size_multiplier(self):
        """Get size multiplier for world dimensions"""
        if self.world_size == "small":
            return 0.7
        elif self.world_size == "large":
            return 1.5
        else:  # medium
            return 1.0

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
    MaterialType.GRASS: 2,
    MaterialType.CLAY: 3,
    MaterialType.SANDSTONE: 4,
    MaterialType.GRANITE: 6,
    MaterialType.COAL: 4,
    MaterialType.IRON: 7,
    MaterialType.GOLD: 8,
    MaterialType.MARBLE: 5,
    MaterialType.OBSIDIAN: 9,
    MaterialType.ICE: 3,
    MaterialType.MOSS: 1,
}

# Material behavior flags
MATERIAL_FALLS = {
    MaterialType.AIR: False,
    MaterialType.DIRT: True,
    MaterialType.STONE: False,
    MaterialType.SAND: True,
    MaterialType.GRAVEL: True,
    MaterialType.WATER: True,
    MaterialType.LAVA: True,
    MaterialType.WOOD: False,
    MaterialType.GRASS: False,
    MaterialType.CLAY: True,
    MaterialType.SANDSTONE: False,
    MaterialType.GRANITE: False,
    MaterialType.COAL: False,
    MaterialType.IRON: False,
    MaterialType.GOLD: False,
    MaterialType.MARBLE: False,
    MaterialType.OBSIDIAN: False,
    MaterialType.ICE: False,
    MaterialType.MOSS: False,
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
    MaterialType.GRASS: 0,
    MaterialType.CLAY: 0.1,  # Slightly muddy
    MaterialType.SANDSTONE: 0,
    MaterialType.GRANITE: 0,
    MaterialType.COAL: 0,
    MaterialType.IRON: 0,
    MaterialType.GOLD: 0,
    MaterialType.MARBLE: 0,
    MaterialType.OBSIDIAN: 0,
    MaterialType.ICE: 0.1,  # Can slightly slide
    MaterialType.MOSS: 0,
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
    MaterialType.GRASS: 0.8,  # Easier than dirt
    MaterialType.CLAY: 1.5,
    MaterialType.SANDSTONE: 2.5,
    MaterialType.GRANITE: 4,
    MaterialType.COAL: 2.8,
    MaterialType.IRON: 5,
    MaterialType.GOLD: 4,  # Soft but dense
    MaterialType.MARBLE: 3.5,
    MaterialType.OBSIDIAN: 7,
    MaterialType.ICE: 2,
    MaterialType.MOSS: 0.5,  # Very soft
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