"""Game constants"""
from enum import Enum, auto
import random
from typing import Tuple, Dict
import pygame

# Display settings
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
TILE_SIZE = 4  # Increased for better visibility
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

# New material and block system
class BlockType(Enum):
    """Defines the block type - foreground, background, etc."""
    FOREGROUND = auto()  # Solid foreground block that player collides with
    BACKGROUND = auto()  # Background decorative block
    FLUID = auto()       # Fluid block (water, lava)

# Material types and properties
class MaterialType(Enum):
    # Special materials
    AIR = auto()
    VOID = auto()  # For out-of-bounds or unloaded areas
    
    # Surface materials
    GRASS_LIGHT = auto()
    GRASS_MEDIUM = auto()
    GRASS_DARK = auto()
    
    # Soil layers
    DIRT_LIGHT = auto()
    DIRT_MEDIUM = auto()
    DIRT_DARK = auto()
    CLAY_LIGHT = auto()
    CLAY_DARK = auto()
    
    # Stone layers
    STONE_LIGHT = auto()
    STONE_MEDIUM = auto()
    STONE_DARK = auto()
    DEEP_STONE_LIGHT = auto()
    DEEP_STONE_MEDIUM = auto()
    DEEP_STONE_DARK = auto()
    
    # Special materials
    GRAVEL_LIGHT = auto()
    GRAVEL_DARK = auto()
    SAND_LIGHT = auto()
    SAND_DARK = auto()
    
    # Fluids
    WATER = auto()
    LAVA = auto()
    
    # Resources
    COAL = auto()
    IRON_ORE = auto()
    GOLD_ORE = auto()
    CRYSTAL = auto()
    
    # Other biome materials
    SANDSTONE = auto()
    GRANITE = auto()
    MARBLE = auto()
    OBSIDIAN = auto()
    ICE = auto()
    MOSS = auto()
    WOOD = auto()

# Define bright, varied colors for materials
MATERIAL_COLORS = {
    # Special materials
    MaterialType.AIR: BLACK,
    MaterialType.VOID: (10, 10, 12),
    
    # Grass variations
    MaterialType.GRASS_LIGHT: (133, 235, 87),
    MaterialType.GRASS_MEDIUM: (110, 210, 70),
    MaterialType.GRASS_DARK: (85, 180, 55),
    
    # Dirt variations
    MaterialType.DIRT_LIGHT: (160, 110, 70),
    MaterialType.DIRT_MEDIUM: (140, 95, 60),
    MaterialType.DIRT_DARK: (120, 80, 50),
    
    # Clay variations
    MaterialType.CLAY_LIGHT: (170, 120, 80),
    MaterialType.CLAY_DARK: (150, 100, 70),
    
    # Stone variations
    MaterialType.STONE_LIGHT: (150, 150, 160),
    MaterialType.STONE_MEDIUM: (130, 130, 140),
    MaterialType.STONE_DARK: (110, 110, 120),
    
    # Deep stone variations
    MaterialType.DEEP_STONE_LIGHT: (90, 90, 105),
    MaterialType.DEEP_STONE_MEDIUM: (75, 75, 90),
    MaterialType.DEEP_STONE_DARK: (60, 60, 75),
    
    # Special materials
    MaterialType.GRAVEL_LIGHT: (120, 120, 125),
    MaterialType.GRAVEL_DARK: (100, 100, 105),
    MaterialType.SAND_LIGHT: (220, 200, 150),
    MaterialType.SAND_DARK: (200, 180, 130),
    
    # Fluids
    MaterialType.WATER: (64, 180, 230, 180),
    MaterialType.LAVA: (230, 90, 20, 200),
    
    # Resources
    MaterialType.COAL: (45, 45, 45),
    MaterialType.IRON_ORE: (190, 170, 160),
    MaterialType.GOLD_ORE: (230, 190, 60),
    MaterialType.CRYSTAL: (180, 240, 255),
    
    # Other biome materials
    MaterialType.SANDSTONE: (220, 195, 160),
    MaterialType.GRANITE: (120, 110, 120),
    MaterialType.MARBLE: (225, 225, 235),
    MaterialType.OBSIDIAN: (35, 25, 40),
    MaterialType.ICE: (164, 220, 250),
    MaterialType.MOSS: (80, 130, 70),
    MaterialType.WOOD: (120, 81, 45),
}

# Background colors (slightly darker, more muted versions of the materials)
BACKGROUND_COLORS = {material: tuple(max(0, c - 30) for c in color[:3]) + ((color[3],) if len(color) > 3 else ())
                    for material, color in MATERIAL_COLORS.items()}

# Biome types
class BiomeType(Enum):
    HILLS = auto()    # Only biome we're implementing for now
    # Other biomes disabled until core gameplay is stable
    # CHASM = auto()
    # MOUNTAIN = auto()
    # DESERT = auto()
    # FOREST = auto()
    # UNDERGROUND = auto()
    # DEPTHS = auto()
    # ABYSS = auto()
    # VOLCANIC = auto()
    # CRYSTAL_CAVES = auto()
    # FROZEN_CAVES = auto()

# Default sky colors
SKY_COLOR_TOP = (92, 148, 252)      # Default bright blue
SKY_COLOR_HORIZON = (210, 230, 255) # Default pale blue

# Underground color
UNDERGROUND_COLOR = (25, 20, 35)    # Dark underground

# Sun settings
SUN_COLOR = (255, 245, 180)         # Bright yellow/white
SUN_RADIUS = 45                     # Sun size in pixels
SUN_RAY_LENGTH = 250                # Length of sun rays
SUN_INTENSITY = 2.5                 # Light intensity

# Sky colors for each biome
BIOME_SKY_COLORS = {
    BiomeType.HILLS: {
        'top': (92, 148, 252),          # Bright blue
        'horizon': (210, 230, 255)      # Pale blue
     } #,
    # BiomeType.CHASM: {
    #     'top': (70, 120, 220),          # Deeper blue
    #     'horizon': (180, 200, 240)      # Muted blue
    # },
    # BiomeType.MOUNTAIN: {
    #     'top': (100, 160, 255),         # Bright high-altitude blue
    #     'horizon': (220, 240, 255)      # Almost white
    # },
    # BiomeType.DESERT: {
    #     'top': (120, 180, 250),         # Washed out blue
    #     'horizon': (250, 220, 170)      # Sandy horizon
    # },
    # BiomeType.FOREST: {
    #     'top': (80, 140, 230),          # Deeper forest blue
    #     'horizon': (140, 210, 180)      # Green-tinted
    # },
    # BiomeType.UNDERGROUND: {
    #     'top': (40, 40, 60),            # Dark cave
    #     'horizon': (50, 50, 70)
    # },
    # BiomeType.DEPTHS: {
    #     'top': (30, 30, 45),            # Darker
    #     'horizon': (35, 35, 50)
    # },
    # BiomeType.ABYSS: {
    #     'top': (20, 20, 30),            # Very dark
    #     'horizon': (25, 25, 35)
    # },
    # BiomeType.VOLCANIC: {
    #     'top': (50, 20, 20),            # Dark red
    #     'horizon': (70, 30, 20)         # Reddish
    # }
}

# World generation settings
class WorldGenSettings:
    def __init__(self):
        self.seed = random.randint(1, 100000)
        self.world_size = "medium"      # small, medium, large
        self.terrain_roughness = 0.7    # 0.0 to 1.0, increased for more pronounced hills
        self.ore_density = 0.5          # 0.0 to 1.0
        self.water_level = 0.2          # 0.0 to 1.0, reduced to show more land
        self.cave_density = 0.4         # 0.0 to 1.0
        
        # Feature toggles - disabled for now, only using hills
        self.has_mountains = False
        self.has_desert = False
        self.has_forest = False
        self.has_chasm = False
        self.has_volcanic = False
        self.has_ice = False
        
        # Layer settings
        self.grass_layer_thickness = 3   # Thin grass layer
        self.dirt_layer_thickness = 40   # Thick dirt layer
        self.stone_transition_depth = 50 # Where stone begins
        self.deep_stone_depth = 150      # Where deep stone begins
        
    def get_terrain_amplitude(self):
        """Get terrain amplitude based on roughness"""
        base = 40  # Increased base amplitude for more dramatic hills
        return int(base + (base * self.terrain_roughness * 1.5))
        
    def get_water_level(self):
        """Get water level based on setting"""
        return int(50 + (self.water_level * 80))
        
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
    # Special materials
    MaterialType.AIR: 0,
    MaterialType.VOID: 0,
    
    # Grass variations
    MaterialType.GRASS_LIGHT: 2,
    MaterialType.GRASS_MEDIUM: 2,
    MaterialType.GRASS_DARK: 2,
    
    # Dirt variations
    MaterialType.DIRT_LIGHT: 2,
    MaterialType.DIRT_MEDIUM: 2, 
    MaterialType.DIRT_DARK: 2,
    MaterialType.CLAY_LIGHT: 3,
    MaterialType.CLAY_DARK: 3,
    
    # Stone variations
    MaterialType.STONE_LIGHT: 5,
    MaterialType.STONE_MEDIUM: 5,
    MaterialType.STONE_DARK: 5,
    MaterialType.DEEP_STONE_LIGHT: 6,
    MaterialType.DEEP_STONE_MEDIUM: 6,
    MaterialType.DEEP_STONE_DARK: 6,
    
    # Special materials
    MaterialType.GRAVEL_LIGHT: 4,
    MaterialType.GRAVEL_DARK: 4,
    MaterialType.SAND_LIGHT: 3,
    MaterialType.SAND_DARK: 3,
    
    # Fluids
    MaterialType.WATER: 1,
    MaterialType.LAVA: 2,
    
    # Resources
    MaterialType.COAL: 4,
    MaterialType.IRON_ORE: 7,
    MaterialType.GOLD_ORE: 8, 
    MaterialType.CRYSTAL: 4,
    
    # Other biome materials
    MaterialType.SANDSTONE: 4,
    MaterialType.GRANITE: 6,
    MaterialType.MARBLE: 5,
    MaterialType.OBSIDIAN: 9,
    MaterialType.ICE: 3,
    MaterialType.MOSS: 1,
    MaterialType.WOOD: 1,
}

# Material behavior flags - which materials can fall
MATERIAL_FALLS = {material: False for material in MaterialType}
# Update only the ones that can fall
for material in [
    MaterialType.DIRT_LIGHT, MaterialType.DIRT_MEDIUM, MaterialType.DIRT_DARK,
    MaterialType.SAND_LIGHT, MaterialType.SAND_DARK,
    MaterialType.GRAVEL_LIGHT, MaterialType.GRAVEL_DARK,
    MaterialType.CLAY_LIGHT, MaterialType.CLAY_DARK,
    MaterialType.WATER, MaterialType.LAVA
]:
    MATERIAL_FALLS[material] = True

# Material liquidity (0 = solid, 1 = very liquid)
MATERIAL_LIQUIDITY = {material: 0 for material in MaterialType}
# Update specific materials with liquidity
MATERIAL_LIQUIDITY.update({
    MaterialType.SAND_LIGHT: 0.3,
    MaterialType.SAND_DARK: 0.3,
    MaterialType.GRAVEL_LIGHT: 0.2,
    MaterialType.GRAVEL_DARK: 0.2,
    MaterialType.WATER: 0.9,
    MaterialType.LAVA: 0.6,
    MaterialType.CLAY_LIGHT: 0.1,
    MaterialType.CLAY_DARK: 0.1,
    MaterialType.ICE: 0.1,
})

# Material hardness (higher = harder to dig)
MATERIAL_HARDNESS = {material: 1.0 for material in MaterialType}
# Set hardness for all materials
MATERIAL_HARDNESS.update({
    # Special materials
    MaterialType.AIR: 0,
    MaterialType.VOID: 100,  # Cannot dig void
    
    # Grass variations (soft)
    MaterialType.GRASS_LIGHT: 0.8,
    MaterialType.GRASS_MEDIUM: 0.8,
    MaterialType.GRASS_DARK: 0.8,
    
    # Dirt variations
    MaterialType.DIRT_LIGHT: 1.0,
    MaterialType.DIRT_MEDIUM: 1.0,
    MaterialType.DIRT_DARK: 1.0,
    MaterialType.CLAY_LIGHT: 1.5,
    MaterialType.CLAY_DARK: 1.5,
    
    # Stone variations
    MaterialType.STONE_LIGHT: 3.0,
    MaterialType.STONE_MEDIUM: 3.0,
    MaterialType.STONE_DARK: 3.0,
    MaterialType.DEEP_STONE_LIGHT: 4.0,
    MaterialType.DEEP_STONE_MEDIUM: 4.0,
    MaterialType.DEEP_STONE_DARK: 4.0,
    
    # Special materials
    MaterialType.GRAVEL_LIGHT: 2.0,
    MaterialType.GRAVEL_DARK: 2.0,
    MaterialType.SAND_LIGHT: 1.2,
    MaterialType.SAND_DARK: 1.2,
    
    # Fluids
    MaterialType.WATER: 0,
    MaterialType.LAVA: 0,
    
    # Resources
    MaterialType.COAL: 2.8,
    MaterialType.IRON_ORE: 5.0,
    MaterialType.GOLD_ORE: 4.0,
    MaterialType.CRYSTAL: 3.5,
    
    # Other biome materials
    MaterialType.SANDSTONE: 2.5,
    MaterialType.GRANITE: 4.0,
    MaterialType.MARBLE: 3.5,
    MaterialType.OBSIDIAN: 7.0,
    MaterialType.ICE: 2.0,
    MaterialType.MOSS: 0.5,
    MaterialType.WOOD: 2.5,
})

# Material groups for easier reference
GRASS_MATERIALS = [MaterialType.GRASS_LIGHT, MaterialType.GRASS_MEDIUM, MaterialType.GRASS_DARK]
DIRT_MATERIALS = [MaterialType.DIRT_LIGHT, MaterialType.DIRT_MEDIUM, MaterialType.DIRT_DARK]
CLAY_MATERIALS = [MaterialType.CLAY_LIGHT, MaterialType.CLAY_DARK]
STONE_MATERIALS = [MaterialType.STONE_LIGHT, MaterialType.STONE_MEDIUM, MaterialType.STONE_DARK]
DEEP_STONE_MATERIALS = [MaterialType.DEEP_STONE_LIGHT, MaterialType.DEEP_STONE_MEDIUM, MaterialType.DEEP_STONE_DARK]
SAND_MATERIALS = [MaterialType.SAND_LIGHT, MaterialType.SAND_DARK]
GRAVEL_MATERIALS = [MaterialType.GRAVEL_LIGHT, MaterialType.GRAVEL_DARK]

# World generation
CHUNK_SIZE = 64  # Much larger chunks for better performance
ACTIVE_CHUNKS_RADIUS = 8  # Increased for better visibility with larger tiles
WORLD_SEED = 12345  # Seed for procedural generation
CAVE_DENSITY = 0.05  # Cave density
WATER_LEVEL = 150  # Adjusted water level
TERRAIN_AMPLITUDE = 80  # Terrain variation amount
DIRT_LAYER_DEPTH = 40  # Thicker dirt layer before stone
SAFE_ZONE_RADIUS = 100  # Increased safe zone around spawn

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