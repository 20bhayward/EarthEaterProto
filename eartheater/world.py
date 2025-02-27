"""
World management module for EarthEater
"""
import numpy as np
from typing import Dict, Tuple, Optional, List, Set, Any
import random
import noise
import math

from eartheater.constants import (
    BiomeType, MaterialType, BlockType, CHUNK_SIZE, ACTIVE_CHUNKS_RADIUS,
    WORLD_SEED, CAVE_DENSITY, MATERIAL_LIQUIDITY, WATER_LEVEL,
    TERRAIN_AMPLITUDE, DIRT_LAYER_DEPTH, SAFE_ZONE_RADIUS,
    GRASS_MATERIALS, DIRT_MATERIALS, STONE_MATERIALS, DEEP_STONE_MATERIALS,
    SAND_MATERIALS, GRAVEL_MATERIALS, CLAY_MATERIALS,
    BIOME_SKY_COLORS, WorldGenSettings
)

class Block:
    """Represents a single block in the world with material and block type"""
    
    def __init__(self, material: MaterialType = MaterialType.AIR, block_type: BlockType = BlockType.FOREGROUND):
        """
        Initialize a new block
        
        Args:
            material: The material type of this block
            block_type: The block type (foreground, background, etc.)
        """
        self.material = material
        self.block_type = block_type
        
    def __eq__(self, other):
        if isinstance(other, Block):
            return self.material == other.material and self.block_type == other.block_type
        return False
        
    def __repr__(self):
        return f"Block({self.material}, {self.block_type})"

class Chunk:
    """A chunk of the world grid, now with background layers"""
    
    def __init__(self, x: int, y: int):
        """
        Initialize a new chunk at the given position
        
        Args:
            x: Chunk x-coordinate
            y: Chunk y-coordinate
        """
        self.x = x
        self.y = y
        # Initialize with air blocks for foreground layer
        self.foreground = np.full((CHUNK_SIZE, CHUNK_SIZE), MaterialType.AIR)
        # Initialize with void blocks for background layer
        self.background = np.full((CHUNK_SIZE, CHUNK_SIZE), MaterialType.VOID)
        self.needs_update = True
        self.generated = False
    
    def set_block(self, x: int, y: int, material: MaterialType, block_type: BlockType = BlockType.FOREGROUND) -> None:
        """
        Set a block in this chunk to the specified material and type
        
        Args:
            x: Local x-coordinate within chunk (0 to CHUNK_SIZE-1)
            y: Local y-coordinate within chunk (0 to CHUNK_SIZE-1)
            material: Material type to set
            block_type: Block type (foreground, background, etc.)
        """
        if 0 <= x < CHUNK_SIZE and 0 <= y < CHUNK_SIZE:
            if block_type == BlockType.FOREGROUND:
                self.foreground[y, x] = material
            elif block_type == BlockType.BACKGROUND:
                self.background[y, x] = material
            self.needs_update = True
    
    def get_block(self, x: int, y: int, block_type: BlockType = BlockType.FOREGROUND) -> MaterialType:
        """
        Get the material at the specified position
        
        Args:
            x: Local x-coordinate within chunk (0 to CHUNK_SIZE-1)
            y: Local y-coordinate within chunk (0 to CHUNK_SIZE-1)
            block_type: Block type to get (foreground, background, etc.)
            
        Returns:
            The material type at the specified position
        """
        if 0 <= x < CHUNK_SIZE and 0 <= y < CHUNK_SIZE:
            if block_type == BlockType.FOREGROUND:
                return self.foreground[y, x]
            elif block_type == BlockType.BACKGROUND:
                return self.background[y, x]
        return MaterialType.AIR if block_type == BlockType.FOREGROUND else MaterialType.VOID
        
    # Compatibility with old code
    def set_tile(self, x: int, y: int, material: MaterialType) -> None:
        """Compatibility with old code - sets a foreground block"""
        self.set_block(x, y, material, BlockType.FOREGROUND)
        
    def get_tile(self, x: int, y: int) -> MaterialType:
        """Compatibility with old code - gets a foreground block"""
        return self.get_block(x, y, BlockType.FOREGROUND)


class World:
    """Manages the game world with biome-based terrain generation"""
    
    def __init__(self, settings=None):
        """
        Initialize an empty world
        
        Args:
            settings: Optional WorldGenSettings object for customizing generation
        """
        # Initialize settings or use defaults
        self.settings = settings or WorldGenSettings()
        
        # Map chunks
        self.chunks: Dict[Tuple[int, int], Chunk] = {}
        self.active_chunks: Set[Tuple[int, int]] = set()
        self.physics_chunks: Set[Tuple[int, int]] = set()  # Chunks that need physics simulation
        self.physics_radius = 5  # Increased to handle more gameplay area
        self.player_chunk = (0, 0)
        
        # Initialize RNG with the seed
        self.random = random.Random(self.settings.seed)
        
        # Loading state
        self.preloaded = False  # Flag to indicate if initial chunks have been preloaded
        self.loading_progress = 0.0  # Progress for loading screen
        self.preview_chunks: List[Tuple[int, int, np.ndarray]] = []  # For loading visualization
        
        # Generate world configuration based on settings
        self.initialize_world_parameters()
        
        # Biome map for large-scale structure
        self.biome_map = {}        # Maps chunk coords to biome type
        self.biome_noise_scale = 0.005  # Large scale biome maps
        self.biome_blending = 20   # Distance for biome blending
        
        # Per-biome noise maps
        self.noise_maps = {}
        
        # Material variation caching
        self._material_variant_cache = {}
    
    def initialize_world_parameters(self):
        """Initialize terrain generation parameters based on settings"""
        # Basic terrain scales - increased variation for prominent hills
        self.terrain_scale = 0.01 + (0.03 * self.settings.terrain_roughness)  # Lower scale for larger features
        self.terrain_octaves = 4 + int(self.settings.terrain_roughness * 3)   # 4 to 7 octaves
        self.terrain_amplitude = self.settings.get_terrain_amplitude()
        
        # Hill scales for different terrain features
        self.hill_scale = 0.01  # Base scale for hills
        self.hill_detail_scale = 0.03  # Scale for medium details 
        self.hill_micro_scale = 0.09  # Scale for small details
        
        # Cave generation parameters
        self.cave_scale = 0.04 + (0.05 * self.settings.cave_density)  # 0.04 to 0.09
        self.cave_density = self.settings.get_cave_density()
        
        # Water level
        self.water_level = self.settings.get_water_level()
        
        # Ore generation parameters
        self.ore_frequency = self.settings.get_ore_frequency()
        
        # Layer transitions (depths from surface)
        self.grass_layer_thickness = self.settings.grass_layer_thickness  # Thin grass layer
        self.dirt_layer_thickness = self.settings.dirt_layer_thickness    # Thick dirt layer
        self.stone_transition = self.settings.stone_transition_depth      # Where stone begins
        self.deep_stone_depth = self.settings.deep_stone_depth            # Where deep stone begins
        
        # Layer noise scales
        self.material_noise_scale = 0.1  # Medium scale variations for material types
        self.detail_noise_scale = 0.3    # Smaller scale for subtle variations
        
        # Surface biomes - updated layout:
        # - HILLS: center (spawn area) - renamed from MEADOW
        # - CHASM: west (negative x) - new mini-biome
        # - MOUNTAIN: east (positive x)
        # - DESERT: south (positive y)
        # - FOREST: north (negative y) - if enabled
        self.spawn_point = (0, 20)
        self.biome_transition_distance = 150  # Increased for more spacious biomes
        
        # Biome centers (in world coordinates)
        self.biome_centers = {
            BiomeType.HILLS: (0, 0),
            BiomeType.MOUNTAIN: (self.biome_transition_distance, 0),
        }
        
        # Add chasm mini-biome to the west
        if self.settings.has_chasm:
            self.biome_centers[BiomeType.CHASM] = (-self.biome_transition_distance // 2, 0)
            
        # Add other biomes based on settings
        if self.settings.has_desert:
            self.biome_centers[BiomeType.DESERT] = (0, self.biome_transition_distance)
            
        if self.settings.has_forest:
            self.biome_centers[BiomeType.FOREST] = (0, -self.biome_transition_distance)
            
        # Underground depths - adjusted for deeper world
        self.underground_start = self.stone_transition + 20
        self.depths_start = self.deep_stone_depth + 30
        self.abyss_start = self.deep_stone_depth + 100
        self.volcanic_start = self.deep_stone_depth + 200
        
        # Hill generation parameters
        self.hill_scale = 0.005    # Very large hills
        self.hill_detail_scale = 0.02  # Medium-scale details on hills
        self.hill_micro_scale = 0.1    # Small details for natural terrain
    
    def get_biome_at(self, world_x: int, world_y: int) -> BiomeType:
        """
        Determine the biome type at a given world coordinate
        
        Args:
            world_x: X coordinate in world space
            world_y: Y coordinate in world space
            
        Returns:
            The biome type at the specified location
        """
        # Simplified: only use HILLS biome for now
        return BiomeType.HILLS
    
    def is_in_chasm(self, world_x: int, world_y: int) -> bool:
        """
        Check if the given coordinates are within the chasm biome
        The chasm is a special vertical biome that cuts through the world
        
        Args:
            world_x: X coordinate in world space
            world_y: Y coordinate in world space
            
        Returns:
            True if in chasm, False otherwise
        """
        if not self.settings.has_chasm or BiomeType.CHASM not in self.biome_centers:
            return False
            
        chasm_center_x = self.biome_centers[BiomeType.CHASM][0]
        
        # Basic width of the chasm
        base_width = 50  # Base width in blocks
        
        # Use noise to make the edges irregular
        try:
            edge_noise = noise.pnoise1(
                world_y * 0.01,  # Vertical variation of chasm width
                octaves=3,
                persistence=0.6,
                lacunarity=2.0,
                repeatx=10000,
                base=self.settings.seed + 3000
            )
        except Exception:
            edge_noise = 0.0
            
        # Widen the chasm as it goes deeper (create a V shape)
        depth_factor = max(0, min(1, world_y / 400))  # 0 at surface, 1 at y=400
        depth_width = base_width * (1 + depth_factor * 2)  # Up to 3x wider at depth
        
        # Calculate final width with noise variation
        width = depth_width * (1 + edge_noise * 0.4)  # ±40% variation based on noise
        
        # Check if within the chasm boundary
        distance_from_center = abs(world_x - chasm_center_x)
        return distance_from_center < width / 2
    
    def get_sky_color(self, biome: BiomeType) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
        """
        Get the sky colors (top and horizon) for the specified biome
        
        Args:
            biome: The biome to get colors for
            
        Returns:
            Tuple of (top_color, horizon_color)
        """
        if biome in BIOME_SKY_COLORS:
            return (BIOME_SKY_COLORS[biome]['top'], BIOME_SKY_COLORS[biome]['horizon'])
        else:
            # Default sky colors for unspecified biomes
            return ((92, 148, 252), (210, 230, 255))
    
    def get_biome_blend(self, world_x: int, world_y: int) -> Dict[BiomeType, float]:
        """
        Get biome influence weights at a position for smooth transitions
        
        Args:
            world_x: X coordinate in world space
            world_y: Y coordinate in world space
            
        Returns:
            Dictionary mapping biome types to influence weights (0.0 to 1.0)
        """
        # Underground biomes have no blending
        if world_y > self.underground_start:
            biome = self.get_biome_at(world_x, world_y)
            return {biome: 1.0}
            
        # Chasm is a special case - no blending on the edges
        if self.settings.has_chasm and self.is_in_chasm(world_x, world_y):
            return {BiomeType.CHASM: 1.0}
        
        # Calculate distances to each biome center with added noise variation
        distances = {}
        total_weight = 0.0
        
        # Get noise for biome transitions
        try:
            biome_noise = noise.pnoise2(
                world_x * 0.004,
                world_y * 0.004,
                octaves=2,
                persistence=0.5,
                lacunarity=2.0,
                repeatx=10000,
                repeaty=10000,
                base=self.settings.seed + 5000
            )
        except Exception:
            biome_noise = 0.0
        
        for biome, center in self.biome_centers.items():
            # Skip underground biomes and chasm (handled separately)
            if biome in [BiomeType.UNDERGROUND, BiomeType.DEPTHS, BiomeType.ABYSS, 
                        BiomeType.VOLCANIC, BiomeType.CHASM]:
                continue
                
            # Calculate distance to biome center
            dx = world_x - center[0]
            dy = world_y - center[1]
            distance = math.sqrt(dx*dx + dy*dy)
            
            # Convert distance to weight using inverse square with falloff
            if distance < 1:
                weight = 1.0
            else:
                # Apply noise factor for natural transitions
                noise_factor = 1.0 + (biome_noise * 0.3)  # Range from 0.7 to 1.3
                
                # Calculate weight with noise modulation
                distance_mod = max(1.0, distance * noise_factor)
                weight = 1.0 / (1.0 + (distance_mod / self.biome_blending) ** 2)
            
            distances[biome] = weight
            total_weight += weight
        
        # Normalize weights
        if total_weight > 0:
            result = {biome: weight / total_weight for biome, weight in distances.items()}
            return result
        else:
            # Fallback to hills biome if all weights are zero
            return {BiomeType.HILLS: 1.0}
    
    def ensure_chunk_exists(self, cx: int, cy: int) -> Chunk:
        """
        Ensure a chunk exists at the specified coordinates
        
        Args:
            cx: Chunk x-coordinate
            cy: Chunk y-coordinate
            
        Returns:
            The chunk at the specified position
        """
        if (cx, cy) not in self.chunks:
            self.chunks[(cx, cy)] = Chunk(cx, cy)
        return self.chunks[(cx, cy)]
    
    def generate_chunk(self, chunk: Chunk) -> None:
        """
        Generate terrain for a chunk using biome-based generation
        Now supports foreground and background blocks
        
        Args:
            chunk: The chunk to generate
        """
        if chunk.generated:
            return
        
        # Cache biome information for this chunk
        chunk_center_x = chunk.x * CHUNK_SIZE + (CHUNK_SIZE // 2)
        chunk_center_y = chunk.y * CHUNK_SIZE + (CHUNK_SIZE // 2)
        chunk_biome = self.get_biome_at(chunk_center_x, chunk_center_y)
        
        # Each chunk cell gets materials based on biome and height
        for local_x in range(CHUNK_SIZE):
            for local_y in range(CHUNK_SIZE):
                world_x = chunk.x * CHUNK_SIZE + local_x
                world_y = chunk.y * CHUNK_SIZE + local_y
                
                # Get biome weights at this position for blending
                biome_weights = self.get_biome_blend(world_x, world_y)
                
                # Generate both foreground and background blocks
                blocks = self.generate_blocks(world_x, world_y, biome_weights)
                
                # Set foreground and background blocks separately
                chunk.set_block(local_x, local_y, blocks[BlockType.FOREGROUND], BlockType.FOREGROUND)
                chunk.set_block(local_x, local_y, blocks[BlockType.BACKGROUND], BlockType.BACKGROUND)
        
        # Mark the chunk as generated
        chunk.generated = True
        chunk.needs_update = True
    
    def get_terrain_height(self, world_x: int, biome=None) -> int:
        """
        Get terrain height for a specific biome
        
        Args:
            world_x: X-coordinate in world space
            biome: Biome type to generate height for (optional, will be determined if not provided)
            
        Returns:
            Terrain height at the specified position for the given biome
        """
        # Simplified terrain generator - only for HILLS biome
        
        # Get noise seeds specific to this biome if not already generated
        if BiomeType.HILLS not in self.noise_maps:
            self.noise_maps[BiomeType.HILLS] = {
                'base': self.random.randint(0, 1000),
                'hills': self.random.randint(0, 1000),
                'details': self.random.randint(0, 1000)
            }
        
        noise_seeds = self.noise_maps[BiomeType.HILLS]
        
        # Base parameters for hills biome
        base_height = 75  # Base terrain height
        amplitude = self.terrain_amplitude  # Height variation
        
        # Simple terrain generation with two noise layers
        try:
            # Large hills
            large_scale = noise.pnoise2(
                world_x * 0.005,  # Large scale for overall terrain
                0,  # Fixed y-coordinate for 1D terrain
                octaves=2,
                persistence=0.6,
                lacunarity=2.0,
                repeatx=10000,
                repeaty=10000,
                base=noise_seeds['base']
            )
            
            # Small details
            small_scale = noise.pnoise2(
                world_x * 0.02,  # Small scale for terrain details
                0,
                octaves=3,
                persistence=0.5,
                lacunarity=2.0,
                repeatx=10000,
                repeaty=10000,
                base=noise_seeds['details']
            )
        except Exception:
            # Fallback if noise generation fails
            return base_height
        
        # Combine noise layers (mostly large scale with a bit of small scale detail)
        combined_noise = (large_scale * 0.8) + (small_scale * 0.2)
        
        # Convert noise (-1 to 1) to terrain height
        terrain_height = int((combined_noise + 1) * amplitude) + base_height
        
        # Ensure minimum height
        return max(20, terrain_height)
    
    def get_cave_at(self, world_x: int, world_y: int, biome: BiomeType) -> bool:
        """
        Determine if there should be a cave at the given position
        
        Args:
            world_x: X-coordinate in world space
            world_y: Y-coordinate in world space
            biome: Biome type
            
        Returns:
            True if there should be a cave, False otherwise
        """
        # Simplified cave generation - very basic caves for HILLS biome
        
        # Only create caves below a certain depth from the surface
        terrain_height = self.get_terrain_height(world_x)
        depth_below_surface = world_y - terrain_height
        
        # Don't create caves too close to the surface
        if depth_below_surface < 15:
            return False
            
        # Get basic cave noise
        try:
            # Simple 3D noise for cave shape
            cave_noise = noise.pnoise3(
                world_x * 0.04,
                world_y * 0.04,
                (world_x + world_y) * 0.02,
                octaves=2,
                persistence=0.5,
                lacunarity=2.0,
                repeatx=10000,
                repeaty=10000,
                repeatz=10000,
                base=self.settings.seed + 2000
            )
        except Exception:
            # Fallback if noise fails
            return False
            
        # Simple threshold for cave generation
        # More caves as you go deeper
        depth_factor = min(1.0, depth_below_surface / 100) * 0.05
        threshold = 0.25 + depth_factor
        
        # Create cave if noise value is above threshold
        return cave_noise > threshold
    
    # Cache for terrain height and ore noise to avoid redundant calculations
    _terrain_height_cache = {}
    _ore_noise_cache = {}
    _lava_noise_cache = {}
    
    def get_material_variant(self, material_type_group, world_x: int, world_y: int, seed_offset: int = 0) -> MaterialType:
        """
        Get a variant from a group of material types (like different shades of grass)
        Uses deterministic noise to ensure consistent variations
        
        Args:
            material_type_group: List of material variants to choose from
            world_x: X-coordinate in world space
            world_y: Y-coordinate in world space
            seed_offset: Additional seed offset to create different patterns
            
        Returns:
            A selected material variant from the group
        """
        # Return first option if only one is provided
        if len(material_type_group) == 1:
            return material_type_group[0]
            
        # Use cache to avoid recomputing
        cache_key = (tuple(material_type_group), world_x // 3, world_y // 3, seed_offset)
        if cache_key in self._material_variant_cache:
            return self._material_variant_cache[cache_key]
            
        # Use noise to select variant - ensures same block always gives same variant at same coordinates
        try:
            variant_noise = noise.pnoise2(
                world_x * 0.2,  # High frequency for local variations
                world_y * 0.2,
                octaves=1,  # Simple noise for this purpose
                persistence=0.5,
                lacunarity=2.0,
                repeatx=10000,
                repeaty=10000,
                base=self.settings.seed + 7000 + seed_offset
            )
            
            # Map noise (-1 to 1) to index in material group
            noise_mapped = (variant_noise + 1) / 2  # 0 to 1
            index = min(len(material_type_group) - 1, int(noise_mapped * len(material_type_group)))
            
            # Store in cache and return
            self._material_variant_cache[cache_key] = material_type_group[index]
            return material_type_group[index]
            
        except Exception:
            # Fallback to random selection if noise fails
            return material_type_group[self.random.randint(0, len(material_type_group) - 1)]
    
    def get_chasm_depth(self, world_x: int, world_y: int) -> int:
        """
        Get the depth of the chasm at a specific point
        Determines how far down the chasm goes
        
        Args:
            world_x: X-coordinate in world space
            world_y: Y-coordinate in world space
            
        Returns:
            The depth of the chasm at this point
        """
        # Safety checks
        if not self.settings.has_chasm or not self.is_in_chasm(world_x, world_y):
            return 0
        
        # Extra safety check for biome center existence    
        if BiomeType.CHASM not in self.biome_centers:
            return 0
            
        # Base depth increases with distance from surface
        base_depth = 300  # Very deep chasm
        
        # Get chasm center
        chasm_center_x = self.biome_centers[BiomeType.CHASM][0]
        
        # Calculate distance from the center of the chasm (horizontally)
        distance = abs(world_x - chasm_center_x)
        
        # Get center line of chasm
        max_width = 50  # Base chasm width
        # Avoid division by zero
        if max_width == 0:
            max_width = 1
            
        center_factor = max(0.0, min(1.0, 1.0 - (distance / (max_width / 2))))
        
        # Deeper in the center, shallower at edges
        depth_factor = center_factor ** 0.5  # Non-linear curve
        
        # Add noise for natural unevenness
        depth_noise = 0.0  # Default if noise calculation fails
        try:
            depth_noise = noise.pnoise2(
                world_x * 0.02,
                world_y * 0.005,  # Slower variation vertically
                octaves=2,
                persistence=0.5,
                lacunarity=2.0,
                repeatx=10000,
                repeaty=10000,
                base=self.settings.seed + 6000
            )
        except Exception:
            # Just keep default noise value if there's an error
            pass
            
        # Scale noise influence by depth (more variation at greater depths)
        # Ensure world_y is non-negative to avoid negative factors
        depth_y = max(0, world_y)
        noise_factor = 0.2 + (depth_y / 500) * 0.3  # 0.2 to 0.5
        depth_adjustment = depth_noise * noise_factor
        
        # Apply noise to base depth with bounds check to prevent negative values
        # Ensure depth_factor is positive to prevent negative depths
        depth_factor = max(0.1, depth_factor)  # Minimum 0.1 depth factor
        depth = int(base_depth * depth_factor * max(0.5, 1 + depth_adjustment))
        
        # Ensure minimum depth and reasonable maximum
        return max(100, min(500, depth))  # Between 100 and 500 blocks deep
    
    def generate_blocks(self, world_x: int, world_y: int, biome_weights: Dict[BiomeType, float]) -> Dict[BlockType, MaterialType]:
        """
        Generate blocks (foreground and background) for a specific world position
        
        Args:
            world_x: X-coordinate in world space
            world_y: Y-coordinate in world space
            biome_weights: Dictionary mapping biome types to influence weights
            
        Returns:
            Dictionary with block types mapping to material types
        """
        # Start with air for foreground and void for background
        blocks = {
            BlockType.FOREGROUND: MaterialType.AIR,
            BlockType.BACKGROUND: MaterialType.VOID
        }
        
        # Simplified: just use hills biome terrain height
        terrain_height = self.get_terrain_height(world_x)
        
        # We only use HILLS biome now (primary_biome will always be HILLS)
        
        # Check for caves in HILLS biome
        is_cave = self.get_cave_at(world_x, world_y, BiomeType.HILLS)
        
        # Check if we're above ground level (air)
        if world_y < terrain_height:
            # Above ground - empty space
            blocks[BlockType.FOREGROUND] = MaterialType.AIR
            blocks[BlockType.BACKGROUND] = MaterialType.AIR
            return blocks
            
        # Check if we're in a cave
        if is_cave:
            # Cave - empty space with background material
            blocks[BlockType.FOREGROUND] = MaterialType.AIR
            
            # Background material depends on depth from surface
            depth = world_y - terrain_height
            if depth < self.dirt_layer_thickness:
                blocks[BlockType.BACKGROUND] = MaterialType.DIRT_MEDIUM
            else:
                blocks[BlockType.BACKGROUND] = MaterialType.STONE_MEDIUM
                
            return blocks
            
        # We're underground (below terrain height) and not in a cave
        # Generate material based on depth from surface
        depth = world_y - terrain_height
        
        # Surface layer - Grass (top 3 blocks)
        if depth < self.grass_layer_thickness:
            blocks[BlockType.FOREGROUND] = MaterialType.GRASS_MEDIUM
            blocks[BlockType.BACKGROUND] = MaterialType.DIRT_MEDIUM
        
        # Dirt layer (next ~40 blocks)
        elif depth < self.stone_transition:
            # Simple dirt with occasional variations
            roll = self.random.random()
            if roll < 0.7:
                blocks[BlockType.FOREGROUND] = MaterialType.DIRT_MEDIUM
            elif roll < 0.9:
                blocks[BlockType.FOREGROUND] = MaterialType.DIRT_LIGHT
            else:
                blocks[BlockType.FOREGROUND] = MaterialType.DIRT_DARK
            
            # Background is always medium dirt
            blocks[BlockType.BACKGROUND] = MaterialType.DIRT_MEDIUM
        
        # Stone layer (next ~100 blocks)
        elif depth < self.deep_stone_depth:
            # Stone with variations
            roll = self.random.random()
            if roll < 0.7:
                blocks[BlockType.FOREGROUND] = MaterialType.STONE_MEDIUM
            elif roll < 0.9:
                blocks[BlockType.FOREGROUND] = MaterialType.STONE_LIGHT
            else:
                blocks[BlockType.FOREGROUND] = MaterialType.STONE_DARK
            
            # Background is always medium stone
            blocks[BlockType.BACKGROUND] = MaterialType.STONE_MEDIUM
            
            # Add some basic ores
            ore_roll = self.random.random()
            ore_depth = depth - self.stone_transition
            
            # Coal in upper stone layer
            if ore_depth < 30 and ore_roll > 0.97:
                blocks[BlockType.FOREGROUND] = MaterialType.COAL
            # Iron deeper
            elif ore_depth >= 30 and ore_roll > 0.98:
                blocks[BlockType.FOREGROUND] = MaterialType.IRON_ORE
        
        # Deep stone layer (everything below)
        else:
            # Deep stone with variations
            roll = self.random.random()
            if roll < 0.7:
                blocks[BlockType.FOREGROUND] = MaterialType.DEEP_STONE_MEDIUM
            elif roll < 0.9:
                blocks[BlockType.FOREGROUND] = MaterialType.DEEP_STONE_LIGHT
            else:
                blocks[BlockType.FOREGROUND] = MaterialType.DEEP_STONE_DARK
            
            # Background is always medium deep stone
            blocks[BlockType.BACKGROUND] = MaterialType.DEEP_STONE_MEDIUM
            
            # Add some basic ores
            ore_roll = self.random.random()
            
            # Iron and gold in deep stone
            if ore_roll > 0.98:
                blocks[BlockType.FOREGROUND] = MaterialType.IRON_ORE
            elif ore_roll > 0.99:
                blocks[BlockType.FOREGROUND] = MaterialType.GOLD_ORE
        
        return blocks
    
    def generate_material_at(self, world_x: int, world_y: int, biome_weights: Dict[BiomeType, float]) -> MaterialType:
        """
        Generate material for a specific world position using biome blending
        
        Args:
            world_x: X-coordinate in world space
            world_y: Y-coordinate in world space
            biome_weights: Dictionary mapping biome types to influence weights
            
        Returns:
            Material type for the specified position
        """
        # Use the new block generation system but only return the foreground material
        # This maintains compatibility with the old code
        blocks = self.generate_blocks(world_x, world_y, biome_weights)
        return blocks[BlockType.FOREGROUND]
    
    def create_world_preview(self, chunks_list):
        """
        Create a detailed preview of the entire world for the loading screen.
        Uses terrain height to visualize the landscape accurately with biome variations.
        
        Args:
            chunks_list: List of (x, y, dist) tuples for all chunks to be generated
        """
        # Clear preview chunks
        self.preview_chunks = []
        preview_size = CHUNK_SIZE // 4  # Each preview cell represents 4x4 tiles
        
        # Pre-populate biome materials map for quick lookups
        biome_materials = {
            BiomeType.HILLS: MaterialType.GRASS_MEDIUM,
            BiomeType.DESERT: MaterialType.SAND_LIGHT,
            BiomeType.MOUNTAIN: MaterialType.STONE_MEDIUM,
            BiomeType.FOREST: MaterialType.GRASS_DARK,
            BiomeType.CHASM: MaterialType.AIR,
            BiomeType.UNDERGROUND: MaterialType.STONE_MEDIUM,
            BiomeType.DEPTHS: MaterialType.DEEP_STONE_MEDIUM,
            BiomeType.ABYSS: MaterialType.DEEP_STONE_DARK,
            BiomeType.VOLCANIC: MaterialType.OBSIDIAN
        }
        
        # Create preview for all chunks with actual terrain heights
        for chunk_x, chunk_y, _ in chunks_list:
            # Create empty preview
            preview_data = np.zeros((preview_size, preview_size), dtype=np.int8)
            
            # Generate an accurate preview by sampling terrain height at multiple points
            for px in range(preview_size):
                # Map preview pixel to world coordinates
                world_x = chunk_x * CHUNK_SIZE + (px * 4) + 2  # Center of each 4x4 block
                
                # Calculate terrain height with accurate biome blending
                biome_weights = self.get_biome_blend(world_x, 0)
                terrain_height = 0
                
                # Apply biome blending for more accurate height
                for biome, weight in biome_weights.items():
                    if biome in [BiomeType.HILLS, BiomeType.DESERT, BiomeType.MOUNTAIN, BiomeType.FOREST, BiomeType.CHASM]:
                        biome_height = self.get_terrain_height(world_x, biome)
                        terrain_height += biome_height * weight
                
                terrain_height = int(terrain_height)
                
                # Map terrain height to preview space (accounting for greater detail)
                terrain_height_scaled = max(0, min(preview_size - 1, terrain_height // 4))
                
                # Fill in the preview data with more material variation
                for py in range(preview_size):
                    # Calculate world y-coordinate
                    world_y = chunk_y * CHUNK_SIZE + (py * 4) + 2
                    
                    # Determine biome at this point for accurate material display
                    biome = self.get_biome_at(world_x, world_y)
                    
                    # Adjust for chasm - cutting through terrain
                    if biome == BiomeType.CHASM and world_y > terrain_height:
                        # Calculate chasm depth
                        chasm_depth = self.get_chasm_depth(world_x, world_y)
                        
                        # Check if within chasm depth
                        if world_y <= terrain_height + chasm_depth:
                            preview_data[py, px] = MaterialType.AIR.value
                            continue
                            
                    # Normal terrain generation for preview
                    if py < terrain_height_scaled:
                        # Above ground - air
                        preview_data[py, px] = MaterialType.AIR.value
                    elif py == terrain_height_scaled:
                        # Surface - based on biome with proper blending
                        biome_material = biome_materials.get(biome, MaterialType.GRASS_MEDIUM)
                        preview_data[py, px] = biome_material.value
                    else:
                        # Underground - determine based on depth and biome
                        depth = py - terrain_height_scaled
                        
                        # Check for caves to show actual cave system in preview
                        if world_y > self.underground_start and self.get_cave_at(world_x, world_y, biome):
                            if world_y > self.abyss_start and self.random.random() < 0.3:
                                preview_data[py, px] = MaterialType.LAVA.value  # Sometimes lava in deep caves
                            else:
                                preview_data[py, px] = MaterialType.AIR.value  # Cave
                        else:
                            # Underground material layers with proper transition
                            if depth < 3:
                                # Near surface layer - thin grass layer
                                if biome == BiomeType.HILLS:
                                    preview_data[py, px] = MaterialType.DIRT_LIGHT.value
                                elif biome == BiomeType.DESERT:
                                    preview_data[py, px] = MaterialType.SAND_LIGHT.value
                                elif biome == BiomeType.MOUNTAIN:
                                    preview_data[py, px] = MaterialType.STONE_LIGHT.value
                                else:
                                    preview_data[py, px] = MaterialType.DIRT_MEDIUM.value
                            elif depth < 10:
                                # Thick dirt layer
                                if self.random.random() < 0.7:
                                    preview_data[py, px] = MaterialType.DIRT_MEDIUM.value
                                else:
                                    # Occasional clay or gravel
                                    if self.random.random() < 0.5:
                                        preview_data[py, px] = MaterialType.CLAY_LIGHT.value
                                    else:
                                        preview_data[py, px] = MaterialType.GRAVEL_LIGHT.value
                            elif depth < 18:
                                # Stone layer
                                preview_data[py, px] = MaterialType.STONE_MEDIUM.value
                                
                                # Show ores in stone layer
                                if depth > 12 and self.random.random() < 0.15:
                                    preview_data[py, px] = MaterialType.COAL.value
                                elif depth > 15 and self.random.random() < 0.1:
                                    preview_data[py, px] = MaterialType.IRON_ORE.value
                            else:
                                # Deep stone layer
                                preview_data[py, px] = MaterialType.DEEP_STONE_MEDIUM.value
                                
                                # Add ores in deep layers
                                if world_y > self.depths_start:
                                    if self.random.random() < 0.12:
                                        preview_data[py, px] = MaterialType.IRON_ORE.value
                                    elif self.random.random() < 0.08:
                                        preview_data[py, px] = MaterialType.GOLD_ORE.value
                                    
                                # Add lava in volcanic zone
                                if world_y > self.abyss_start and self.random.random() < 0.15:
                                    preview_data[py, px] = MaterialType.LAVA.value
                
                # Add water in depressions
                if terrain_height > self.water_level:
                    water_height_scaled = max(0, min(preview_size - 1, self.water_level // 4))
                    # Make sure we're not trying to add water above the terrain
                    if water_height_scaled > terrain_height_scaled:
                        # Skip water near spawn for safe zone
                        dist_from_spawn = math.sqrt(world_x ** 2)
                        if dist_from_spawn > SAFE_ZONE_RADIUS // 4:
                            for py in range(terrain_height_scaled, water_height_scaled):
                                preview_data[py, px] = MaterialType.WATER.value
            
            # Add to preview list
            self.preview_chunks.append((chunk_x, chunk_y, preview_data))
            
        # Update loading progress
        self.loading_progress = 0.1
    
    def update_active_chunks(self, player_world_x: float, player_world_y: float) -> None:
        """
        Update which chunks are active based on player position.
        Separates chunks into rendering and physics simulation sets.
        
        Args:
            player_world_x: Player x-coordinate in world space
            player_world_y: Player y-coordinate in world space
        """
        # Calculate player's chunk coordinates
        player_cx = int(player_world_x) // CHUNK_SIZE
        player_cy = int(player_world_y) // CHUNK_SIZE
        
        # If player has moved to a new chunk, update active chunks
        if (player_cx, player_cy) != self.player_chunk:
            self.player_chunk = (player_cx, player_cy)
            
            # Clear the sets of active chunks
            self.active_chunks.clear()
            self.physics_chunks.clear()
            
            # Use squared distance comparisons for better performance
            active_radius_sq = ACTIVE_CHUNKS_RADIUS * ACTIVE_CHUNKS_RADIUS
            physics_radius_sq = self.physics_radius * self.physics_radius
            
            # Add chunks within radius to active set (for rendering)
            for dx in range(-ACTIVE_CHUNKS_RADIUS, ACTIVE_CHUNKS_RADIUS + 1):
                for dy in range(-ACTIVE_CHUNKS_RADIUS, ACTIVE_CHUNKS_RADIUS + 1):
                    # Skip chunks that are too far (use circular radius)
                    dist_sq = dx*dx + dy*dy
                    if dist_sq > active_radius_sq:
                        continue
                        
                    cx = player_cx + dx
                    cy = player_cy + dy
                    self.active_chunks.add((cx, cy))
                    
                    # Ensure the chunk exists and is generated
                    chunk = self.ensure_chunk_exists(cx, cy)
                    if not chunk.generated:
                        self.generate_chunk(chunk)
                    
                    # Also add to physics chunks if within physics radius
                    if dist_sq <= physics_radius_sq:
                        self.physics_chunks.add((cx, cy))
    
    def get_physics_chunks(self) -> List[Chunk]:
        """Get a list of chunks that need physics simulation"""
        physics_chunks = []
        for cx, cy in self.physics_chunks:
            chunk = self.get_chunk(cx, cy)
            if chunk is not None:
                physics_chunks.append(chunk)
        return physics_chunks
    
    def preload_chunks(self, center_x: int, center_y: int, radius: int) -> float:
        """
        Preload a larger area of chunks for initial loading.
        Creates detailed preview data for loading screen visualization that accurately
        represents the terrain heights and underground features.
        
        Args:
            center_x: Center chunk x-coordinate
            center_y: Center chunk y-coordinate
            radius: Radius of chunks to preload
            
        Returns:
            Progress value between 0.0 and 1.0
        """
        # Calculate actual number of chunks to process (only those within radius)
        chunks_to_process = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if dx*dx + dy*dy <= radius*radius:
                    # Store with distance for priority
                    dist = math.sqrt(dx*dx + dy*dy)
                    chunks_to_process.append((center_x + dx, center_y + dy, dist))
        
        total_chunks = len(chunks_to_process)
        chunks_loaded = 0
        
        # Clear preview chunks
        self.preview_chunks = []
        
        # Pre-populate biome materials map for quick lookups
        biome_materials = {
            BiomeType.HILLS: MaterialType.GRASS_MEDIUM,
            BiomeType.DESERT: MaterialType.SAND_LIGHT,
            BiomeType.MOUNTAIN: MaterialType.STONE_MEDIUM,
            BiomeType.UNDERGROUND: MaterialType.STONE_MEDIUM,
            BiomeType.DEPTHS: MaterialType.DEEP_STONE_MEDIUM,
            BiomeType.ABYSS: MaterialType.DEEP_STONE_DARK,
            BiomeType.VOLCANIC: MaterialType.LAVA,
            BiomeType.FOREST: MaterialType.WOOD,
            BiomeType.CHASM: MaterialType.STONE_DARK,
            BiomeType.CRYSTAL_CAVES: MaterialType.CRYSTAL
        }
        
        # First pass: create accurate terrain preview immediately
        preview_size = CHUNK_SIZE // 4
        
        # Create all preview chunks with terrain visualization
        # Sort chunks by distance from center for prioritized loading
        chunks_to_process.sort(key=lambda c: c[2])
        
        # Generate initial terrain preview for all chunks
        try:
            # Define various world layer boundaries for preview generation
            preview_size = CHUNK_SIZE // 4
            surface_level = 100  # Approximate default surface level
            
            # Process a subset of chunks for preview
            for chunk_x, chunk_y, _ in chunks_to_process[:5]:  
                # Generate a simple low-res heightmap for this chunk
                preview_data = np.zeros((preview_size, preview_size), dtype=np.int8)
                
                # Generate terrain across the chunk
                for px in range(preview_size):
                    # Calculate world coordinates
                    world_x = chunk_x * CHUNK_SIZE + px * 4
                    
                    # Generate basic terrain heightmap with sin wave for simple preview
                    terrain_height = 100 + int(math.sin(world_x * 0.05) * 20)
                    
                    # Fill in the column with appropriate materials
                    for py in range(preview_size):
                        world_y = chunk_y * CHUNK_SIZE + py * 4
                        
                        # Simple material determination
                        if world_y < terrain_height - 5:
                            # This is air/sky
                            preview_data[py, px] = MaterialType.AIR.value
                        elif world_y < terrain_height:
                            # Surface - grass
                            preview_data[py, px] = MaterialType.GRASS_MEDIUM.value
                        elif world_y < terrain_height + 40:
                            # Dirt layer
                            preview_data[py, px] = MaterialType.DIRT_MEDIUM.value
                        else:
                            # Stone
                            preview_data[py, px] = MaterialType.STONE_MEDIUM.value
                
                # Add to preview chunks list
                self.preview_chunks.append((chunk_x, chunk_y, preview_data))
        
        except Exception as e:
            # Fallback to much simpler preview if anything fails
            print(f"Error generating preview: {e}")
            preview_size = CHUNK_SIZE // 4
            for chunk_x, chunk_y, _ in chunks_to_process[:3]:
                preview_data = np.zeros((preview_size, preview_size), dtype=np.int8)
                # Create a simple flat surface
                for py in range(preview_size):
                    for px in range(preview_size):
                        if py < preview_size // 2:
                            preview_data[py, px] = MaterialType.AIR.value
                        elif py == preview_size // 2:
                            preview_data[py, px] = MaterialType.GRASS_MEDIUM.value
                        else:
                            preview_data[py, px] = MaterialType.DIRT_MEDIUM.value
                
                self.preview_chunks.append((chunk_x, chunk_y, preview_data))
            
        # Update loading progress for first pass (first 30%)
        self.loading_progress = 0.3
        
        # Second pass: actually generate the chunks
        # We use a spiral pattern to prioritize chunks near the center
        spiral_chunks = [(x, y) for x, y, _ in chunks_to_process]
        
        # Process chunks in spiral order (center to outside)
        for i, (chunk_x, chunk_y) in enumerate(spiral_chunks):
            # Generate the actual chunk
            chunk = self.ensure_chunk_exists(chunk_x, chunk_y)
            if not chunk.generated:
                self.generate_chunk(chunk)
            
            # Update preview with actual chunk data every few chunks
            if i % 2 == 0 and chunk.generated:  # More frequent updates for better visualization
                # Create an accurate preview from the actual chunk data
                preview_data = np.zeros((preview_size, preview_size), dtype=np.int8)
                
                # Sample chunk data with higher resolution
                for py in range(preview_size):
                    for px in range(preview_size):
                        # Sample center point of each 4x4 block
                        y, x = py*4 + 2, px*4 + 2
                        if 0 <= y < CHUNK_SIZE and 0 <= x < CHUNK_SIZE:
                            material = chunk.foreground[y, x]
                            preview_data[py, px] = material.value
                
                # Find and update existing preview
                found = False
                for j, (cx, cy, _) in enumerate(self.preview_chunks):
                    if cx == chunk_x and cy == chunk_y:
                        self.preview_chunks[j] = (chunk_x, chunk_y, preview_data)
                        found = True
                        break
                        
                # Add if not found (shouldn't happen but just in case)
                if not found:
                    self.preview_chunks.append((chunk_x, chunk_y, preview_data))
            
            # Update progress for second pass (remaining 70%)
            progress_increment = 0.7 / len(spiral_chunks)
            self.loading_progress = min(0.99, 0.3 + (i + 1) * progress_increment)
        
        # Skip the enhancement pass for better performance
        # This pass was causing crashes with noise exceptions
                                    
        # Mark as preloaded and return full progress
        self.preloaded = True
        self.loading_progress = 1.0
        return 1.0
    
    def get_chunk(self, cx: int, cy: int) -> Optional[Chunk]:
        """
        Get the chunk at the specified chunk coordinates
        
        Args:
            cx: Chunk x-coordinate
            cy: Chunk y-coordinate
            
        Returns:
            The chunk at the specified position, or None if not loaded
        """
        return self.chunks.get((cx, cy))
    
    def get_tile(self, x: int, y: int) -> MaterialType:
        """
        Get the material at the specified world position
        
        Args:
            x: World x-coordinate
            y: World y-coordinate
            
        Returns:
            The material type at the specified position, AIR if not loaded
        """
        cx, local_x = divmod(int(x), CHUNK_SIZE)
        cy, local_y = divmod(int(y), CHUNK_SIZE)
        
        chunk = self.get_chunk(cx, cy)
        if chunk is None:
            return MaterialType.AIR
        
        return chunk.get_tile(local_x, local_y)
    
    def set_tile(self, x: int, y: int, material: MaterialType) -> None:
        """
        Set the material at the specified world position
        
        Args:
            x: World x-coordinate
            y: World y-coordinate
            material: Material type to set
        """
        cx, local_x = divmod(int(x), CHUNK_SIZE)
        cy, local_y = divmod(int(y), CHUNK_SIZE)
        
        # Ensure chunk exists
        chunk = self.ensure_chunk_exists(cx, cy)
        chunk.set_tile(local_x, local_y, material)
    
    def get_active_chunks(self) -> List[Chunk]:
        """Get a list of all chunks that need to be processed/rendered"""
        active_chunks = []
        for cx, cy in self.active_chunks:
            chunk = self.get_chunk(cx, cy)
            if chunk is not None:
                active_chunks.append(chunk)
        return active_chunks