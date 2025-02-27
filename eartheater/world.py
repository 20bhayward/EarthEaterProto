"""
World management module for EarthEater
"""
import numpy as np
from typing import Dict, Tuple, Optional, List, Set
import random
import noise
import math

from eartheater.constants import (
    BiomeType, MaterialType, CHUNK_SIZE, ACTIVE_CHUNKS_RADIUS,
    WORLD_SEED, CAVE_DENSITY, MATERIAL_LIQUIDITY, WATER_LEVEL,
    TERRAIN_AMPLITUDE, DIRT_LAYER_DEPTH, SAFE_ZONE_RADIUS
)

class Chunk:
    """A chunk of the world grid"""
    
    def __init__(self, x: int, y: int):
        """
        Initialize a new chunk at the given position
        
        Args:
            x: Chunk x-coordinate
            y: Chunk y-coordinate
        """
        self.x = x
        self.y = y
        self.tiles = np.full((CHUNK_SIZE, CHUNK_SIZE), MaterialType.AIR)
        self.needs_update = True
        self.generated = False
    
    def set_tile(self, x: int, y: int, material: MaterialType) -> None:
        """
        Set a tile in this chunk to the specified material
        
        Args:
            x: Local x-coordinate within chunk (0 to CHUNK_SIZE-1)
            y: Local y-coordinate within chunk (0 to CHUNK_SIZE-1)
            material: Material type to set
        """
        if 0 <= x < CHUNK_SIZE and 0 <= y < CHUNK_SIZE:
            self.tiles[y, x] = material
            self.needs_update = True
    
    def get_tile(self, x: int, y: int) -> MaterialType:
        """
        Get the material at the specified position
        
        Args:
            x: Local x-coordinate within chunk (0 to CHUNK_SIZE-1)
            y: Local y-coordinate within chunk (0 to CHUNK_SIZE-1)
            
        Returns:
            The material type at the specified position
        """
        if 0 <= x < CHUNK_SIZE and 0 <= y < CHUNK_SIZE:
            return self.tiles[y, x]
        return MaterialType.AIR


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
        self.physics_radius = 3  # Smaller radius for physics simulation
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
    
    def initialize_world_parameters(self):
        """Initialize terrain generation parameters based on settings"""
        # Basic terrain scales
        self.terrain_scale = 0.03 + (0.04 * self.settings.terrain_roughness)  # 0.03 to 0.07
        self.terrain_octaves = 5 + int(self.settings.terrain_roughness * 4)   # 5 to 9 octaves
        self.terrain_amplitude = self.settings.get_terrain_amplitude()
        
        # Cave generation parameters
        self.cave_scale = 0.08 + (0.04 * self.settings.cave_density)  # 0.08 to 0.12
        self.cave_density = self.settings.get_cave_density()
        
        # Water level
        self.water_level = self.settings.get_water_level()
        
        # Ore generation parameters
        self.ore_frequency = self.settings.get_ore_frequency()
        
        # Layer transitions (depths from surface)
        self.topsoil_depth = 5
        self.dirt_layer_depth = 20
        self.underground_start = 25
        self.depths_start = 80
        self.abyss_start = 150
        self.volcanic_start = 200
        
        # Surface biomes - zones are:
        # - MEADOW: center (spawn area)
        # - DESERT: west (negative x)
        # - MOUNTAIN: east (positive x)
        # - FOREST: north (negative y) - if enabled
        self.spawn_point = (0, 20)
        self.biome_transition_distance = 150  # Distance to transition between surface biomes
        
        # Biome centers (in world coordinates)
        self.biome_centers = {
            BiomeType.MEADOW: (0, 0),
            BiomeType.DESERT: (-self.biome_transition_distance, 0),
            BiomeType.MOUNTAIN: (self.biome_transition_distance, 0),
        }
        
        if self.settings.has_forest:
            self.biome_centers[BiomeType.FOREST] = (0, -self.biome_transition_distance)
    
    def get_biome_at(self, world_x: int, world_y: int) -> BiomeType:
        """
        Determine the biome type at a given world coordinate
        Uses a combination of horizontal position and depth
        
        Args:
            world_x: X coordinate in world space
            world_y: Y coordinate in world space
            
        Returns:
            The biome type at the specified location
        """
        # Underground biomes are based on depth
        if world_y > self.abyss_start and self.settings.has_volcanic:
            return BiomeType.VOLCANIC
        elif world_y > self.depths_start:
            return BiomeType.DEPTHS
        elif world_y > self.underground_start:
            return BiomeType.UNDERGROUND
        
        # Surface biomes are based on horizontal position
        closest_biome = BiomeType.MEADOW
        min_distance = float('inf')
        
        for biome, center in self.biome_centers.items():
            # Only consider surface biomes
            if biome not in [BiomeType.MEADOW, BiomeType.DESERT, BiomeType.MOUNTAIN, BiomeType.FOREST]:
                continue
                
            # Skip disabled biomes
            if biome == BiomeType.DESERT and not self.settings.has_desert:
                continue
            if biome == BiomeType.MOUNTAIN and not self.settings.has_mountains:
                continue
            if biome == BiomeType.FOREST and not self.settings.has_forest:
                continue
            
            # Calculate horizontal distance to biome center
            dx = world_x - center[0]
            dy = 0  # Only use horizontal distance for surface biomes
            if biome == BiomeType.FOREST:
                dy = world_y - center[1]
                
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance < min_distance:
                min_distance = distance
                closest_biome = biome
        
        return closest_biome
    
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
        
        # Calculate distances to each biome center
        distances = {}
        total_weight = 0.0
        
        for biome, center in self.biome_centers.items():
            # Only consider surface biomes
            if biome not in [BiomeType.MEADOW, BiomeType.DESERT, BiomeType.MOUNTAIN, BiomeType.FOREST]:
                continue
                
            # Skip disabled biomes
            if biome == BiomeType.DESERT and not self.settings.has_desert:
                continue
            if biome == BiomeType.MOUNTAIN and not self.settings.has_mountains:
                continue
            if biome == BiomeType.FOREST and not self.settings.has_forest:
                continue
            
            # Calculate distance to biome center
            dx = world_x - center[0]
            dy = 0
            if biome == BiomeType.FOREST:
                dy = world_y - center[1]
                
            distance = math.sqrt(dx*dx + dy*dy)
            
            # Convert distance to weight using inverse square with falloff
            # 1.0 at center, decreasing as distance increases
            if distance < 1:
                weight = 1.0
            else:
                # We use inverse distance raised to a power for a smoother transition
                weight = 1.0 / (1.0 + (distance / self.biome_blending) ** 2)
            
            distances[biome] = weight
            total_weight += weight
        
        # Normalize weights
        if total_weight > 0:
            result = {biome: weight / total_weight for biome, weight in distances.items()}
            return result
        else:
            # Fallback to meadow if all weights are zero
            return {BiomeType.MEADOW: 1.0}
    
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
        
        Args:
            chunk: The chunk to generate
        """
        if chunk.generated:
            return
        
        # Cache biome information for this chunk
        chunk_center_x = chunk.x * CHUNK_SIZE + (CHUNK_SIZE // 2)
        chunk_center_y = chunk.y * CHUNK_SIZE + (CHUNK_SIZE // 2)
        chunk_biome = self.get_biome_at(chunk_center_x, chunk_center_y)
        
        # Each chunk cell gets material based on biome and height
        for local_x in range(CHUNK_SIZE):
            for local_y in range(CHUNK_SIZE):
                world_x = chunk.x * CHUNK_SIZE + local_x
                world_y = chunk.y * CHUNK_SIZE + local_y
                
                # Get biome weights at this position for blending
                biome_weights = self.get_biome_blend(world_x, world_y)
                
                # For each cell, we calculate height and materials based on biome blending
                material = self.generate_material_at(world_x, world_y, biome_weights)
                chunk.set_tile(local_x, local_y, material)
        
        # Mark the chunk as generated
        chunk.generated = True
        chunk.needs_update = True
    
    def get_terrain_height(self, world_x: int, biome: BiomeType) -> int:
        """
        Get terrain height for a specific biome
        
        Args:
            world_x: X-coordinate in world space
            biome: Biome type to generate height for
            
        Returns:
            Terrain height at the specified position for the given biome
        """
        # Base height level around which we'll add hills/mountains
        base_height = 60
        
        # Get noise seeds specific to this biome if not already generated
        if biome not in self.noise_maps:
            self.noise_maps[biome] = {
                'base': self.random.randint(0, 1000),
                'hills': self.random.randint(0, 1000),
                'details': self.random.randint(0, 1000)
            }
        
        noise_seeds = self.noise_maps[biome]
        
        # Adjust terrain generation parameters based on biome
        if biome == BiomeType.MEADOW:
            # Gentle rolling hills
            scale = self.terrain_scale * 0.8
            amplitude = self.terrain_amplitude * 0.7
            persistence = 0.5
            octaves = self.terrain_octaves - 1
        
        elif biome == BiomeType.DESERT:
            # Rolling dunes with occasional mesas
            scale = self.terrain_scale * 0.6
            amplitude = self.terrain_amplitude * 0.5
            persistence = 0.6
            octaves = self.terrain_octaves - 2
            
            # Add occasional mesas/plateaus
            mesa_noise = noise.pnoise2(
                world_x * 0.01, 
                0,
                octaves=1,
                persistence=0.5,
                lacunarity=2.0,
                repeatx=10000,
                repeaty=10000,
                base=noise_seeds['base'] + 500
            )
            
            if mesa_noise > 0.7:
                # Flat mesa
                amplitude *= 0.3
                base_height -= 10  # Lower base so mesas stand out
        
        elif biome == BiomeType.MOUNTAIN:
            # Jagged high peaks
            scale = self.terrain_scale * 1.2
            amplitude = self.terrain_amplitude * 2.0
            persistence = 0.65
            octaves = self.terrain_octaves + 1
            
            # Make mountains more jagged/rocky
            base_height += 15  # Higher base elevation
        
        elif biome == BiomeType.FOREST:
            # Gentle hills with occasional clearings
            scale = self.terrain_scale * 0.7
            amplitude = self.terrain_amplitude * 0.6
            persistence = 0.4
            octaves = self.terrain_octaves
        
        else:
            # Default parameters for other biomes
            scale = self.terrain_scale
            amplitude = self.terrain_amplitude
            persistence = 0.5
            octaves = self.terrain_octaves
        
        # Generate base terrain using Perlin noise
        base_terrain = noise.pnoise2(
            world_x * scale, 
            0,
            octaves=octaves, 
            persistence=persistence, 
            lacunarity=2.0, 
            repeatx=10000, 
            repeaty=10000, 
            base=noise_seeds['base']
        )
        
        # Add hills with lower frequency
        hill_noise = noise.pnoise2(
            world_x * scale * 0.3,
            0,
            octaves=3,
            persistence=0.7,
            lacunarity=2.0,
            repeatx=10000,
            repeaty=10000,
            base=noise_seeds['hills']
        )
        
        # Small details
        detail_noise = noise.pnoise2(
            world_x * scale * 3.0,
            0,
            octaves=2,
            persistence=0.3,
            lacunarity=2.0,
            repeatx=10000,
            repeaty=10000,
            base=noise_seeds['details']
        ) * 0.1
        
        # Combine noise layers with different weights
        combined_noise = (base_terrain * 0.6) + (hill_noise * 0.35) + detail_noise
        
        # Map noise value (-1 to 1) to terrain height with biome-specific variation
        terrain_height = int((combined_noise + 1) * amplitude) + base_height
        
        # Special adjustments for certain biomes
        if biome == BiomeType.DESERT:
            # Occasionally add canyons
            canyon_noise = noise.pnoise2(
                world_x * 0.008, 
                0,
                octaves=1,
                persistence=0.5,
                lacunarity=2.0,
                repeatx=10000,
                repeaty=10000,
                base=noise_seeds['base'] + 1000
            )
            
            if canyon_noise > 0.7 and canyon_noise < 0.8:
                # Deep canyon cut
                terrain_height += int((canyon_noise - 0.7) * 10 * amplitude)
        
        elif biome == BiomeType.MOUNTAIN:
            # Add occasional plateaus
            plateau_noise = noise.pnoise2(
                world_x * 0.005, 
                0,
                octaves=1,
                persistence=0.5,
                lacunarity=2.0,
                repeatx=10000,
                repeaty=10000,
                base=noise_seeds['base'] + 2000
            )
            
            if plateau_noise > 0.6:
                # Plateau - reduce height variation
                terrain_height = int(terrain_height * 0.8 + base_height * 1.5)
        
        return terrain_height
    
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
        # Get noise seeds specific to this biome if not already generated
        if biome not in self.noise_maps:
            self.noise_maps[biome] = {
                'base': self.random.randint(0, 1000),
                'hills': self.random.randint(0, 1000),
                'details': self.random.randint(0, 1000),
                'caves': self.random.randint(0, 1000)
            }
        
        noise_seeds = self.noise_maps[biome]
        
        # Adjust cave parameters based on biome and depth
        cave_scale = self.cave_scale
        cave_threshold = self.cave_density
        
        # Depth-based adjustments
        if world_y > self.abyss_start:
            # More caves in the abyss
            cave_threshold *= 1.5
            cave_scale *= 1.2
        elif world_y > self.depths_start:
            # More caves in the depths
            cave_threshold *= 1.2
            cave_scale *= 1.1
        
        # Biome-based adjustments
        if biome == BiomeType.UNDERGROUND:
            # Standard caves
            pass
        elif biome == BiomeType.DEPTHS:
            # Larger cave systems
            cave_scale *= 0.8
            cave_threshold *= 1.1
        elif biome == BiomeType.ABYSS:
            # Vast caverns
            cave_scale *= 0.7
            cave_threshold *= 1.3
        elif biome == BiomeType.VOLCANIC:
            # Lava tubes and magma chambers
            cave_scale *= 0.9
            cave_threshold *= 1.2
        
        # Generate 3D noise for caves
        cave_value = noise.pnoise3(
            world_x * cave_scale,
            world_y * cave_scale,
            (world_x + world_y) * 0.05,  # Z-coordinate for 3D variation
            octaves=3,
            persistence=0.5,
            lacunarity=2.0,
            repeatx=10000,
            repeaty=10000,
            repeatz=10000,
            base=noise_seeds.get('caves', 0)
        )
        
        # Adjust threshold based on depth to create more caves deeper down
        depth_factor = 1 + ((world_y - self.underground_start) / 100)
        depth_factor = max(1, min(depth_factor, 2))  # Clamp between 1 and 2
        adjusted_threshold = cave_threshold * depth_factor
        
        # Determine if there should be a cave
        is_cave = cave_value > 0.3 and cave_value < 0.3 + adjusted_threshold
        
        return is_cave
    
    # Cache for terrain height and ore noise to avoid redundant calculations
    _terrain_height_cache = {}
    _ore_noise_cache = {}
    _lava_noise_cache = {}
    
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
        # Default material is air
        material = MaterialType.AIR
        
        # Calculate blended terrain height from all biomes - with caching
        terrain_height = 0
        
        # Use cached terrain heights when possible
        for biome, weight in biome_weights.items():
            # Only consider surface biomes for terrain height
            if biome in [BiomeType.MEADOW, BiomeType.DESERT, BiomeType.MOUNTAIN, BiomeType.FOREST]:
                # Check cache first
                cache_key = (world_x, biome)
                if cache_key not in self._terrain_height_cache:
                    self._terrain_height_cache[cache_key] = self.get_terrain_height(world_x, biome)
                    
                # Get height from cache
                biome_height = self._terrain_height_cache[cache_key]
                terrain_height += biome_height * weight
        
        terrain_height = int(terrain_height)
        
        # Determine cave status based on primary biome for underground areas
        primary_biome = self.get_biome_at(world_x, world_y)
        is_cave = self.get_cave_at(world_x, world_y, primary_biome)
        
        # Air above terrain height, materials below
        if world_y <= terrain_height:
            # Above ground
            material = MaterialType.AIR
            
            # Calculate distance from origin squared (faster than sqrt)
            dist_sq_from_origin = world_x**2 + world_y**2
            
            # Add water in depressions but not in safe zone
            water_level = self.water_level
            if world_y > water_level and dist_sq_from_origin > SAFE_ZONE_RADIUS**2:
                # Create water pools in depressions
                is_depression = world_y > terrain_height - 3 and world_y < terrain_height + 5
                
                if is_depression:
                    material = MaterialType.WATER
        else:
            # Underground - determine material based on depth and biome

            # First check for caves
            if is_cave:
                # Cave - empty space with occasional lava
                if world_y > self.abyss_start:
                    # In the abyss/volcanic area, chance for lava
                    if self.random.random() < 0.2:
                        material = MaterialType.LAVA
                    else:
                        material = MaterialType.AIR
                else:
                    material = MaterialType.AIR
            else:
                # Solid material - determine based on depth and biome
                
                # Surface layer material depends on biome blend
                if world_y <= terrain_height + self.topsoil_depth:
                    # Top layer - blend between grass, sand, etc.
                    # Simplify by using highest weight biome directly
                    max_biome = max(biome_weights.items(), key=lambda x: x[1])[0]
                    
                    if max_biome == BiomeType.MEADOW:
                        material = MaterialType.GRASS
                    elif max_biome == BiomeType.DESERT:
                        material = MaterialType.SAND
                    elif max_biome == BiomeType.MOUNTAIN:
                        material = MaterialType.STONE
                    elif max_biome == BiomeType.FOREST:
                        # For forest, slight randomization between grass and dirt
                        material = MaterialType.GRASS if self.random.random() < 0.7 else MaterialType.DIRT
                
                # Dirt layer
                elif world_y <= terrain_height + self.underground_start:
                    material = MaterialType.DIRT
                    
                    # Add pockets of other materials - only do this sometimes for performance
                    if world_x % 3 == 0 and world_y % 3 == 0 and self.random.random() < 0.2:
                        # More clay in desert areas
                        desert_weight = biome_weights.get(BiomeType.DESERT, 0)
                        if desert_weight > 0.5 and self.random.random() < desert_weight:
                            material = MaterialType.CLAY
                        else:
                            material = MaterialType.GRAVEL
                
                # Underground - base stone with biome-specific materials
                elif world_y <= self.depths_start:
                    material = MaterialType.STONE
                    
                    # Use cached ore noise values
                    cache_key = (world_x//3, world_y//3, 1)  # Group by 3x3 blocks for caching
                    if cache_key not in self._ore_noise_cache:
                        # Calculate ore noise - simplified to fewer octaves
                        self._ore_noise_cache[cache_key] = noise.pnoise3(
                            world_x * 0.05, 
                            world_y * 0.05,
                            (world_x + world_y) * 0.01,
                            octaves=1,  # Reduced from 2
                            persistence=0.5,
                            lacunarity=2.0,
                            repeatx=10000,
                            repeaty=10000,
                            repeatz=10000,
                            base=self.settings.seed  # Use world seed for consistency
                        )
                    
                    ore_noise = self._ore_noise_cache[cache_key]
                    
                    # Check for ore based on frequency and depth
                    ore_chance = self.ore_frequency * (world_y - terrain_height) / 100
                    ore_chance = min(0.3, ore_chance)  # Cap at 30%
                    
                    if ore_noise > 0.7 and self.random.random() < ore_chance:
                        # Common ore: coal
                        material = MaterialType.COAL
                        
                        # Rarer ores deeper down
                        if world_y > terrain_height + 50 and self.random.random() < 0.3:
                            material = MaterialType.IRON
                
                # Depths - tougher stone and more valuable ores
                elif world_y <= self.abyss_start:
                    material = MaterialType.GRANITE
                    
                    # Add more valuable ores - use ore noise cache
                    cache_key = (world_x//4, world_y//4, 2)  # Group by 4x4 blocks for depths
                    if cache_key not in self._ore_noise_cache:
                        self._ore_noise_cache[cache_key] = noise.pnoise3(
                            world_x * 0.04, 
                            world_y * 0.04,
                            (world_x + world_y) * 0.01,
                            octaves=1,  # Reduced from 2
                            persistence=0.5,
                            lacunarity=2.0,
                            repeatx=10000,
                            repeaty=10000,
                            repeatz=10000,
                            base=self.settings.seed + 1000
                        )
                    
                    ore_noise = self._ore_noise_cache[cache_key]
                    
                    # Higher chance of valuable ores
                    if ore_noise > 0.75:
                        ore_roll = self.random.random()
                        if ore_roll < 0.6:
                            material = MaterialType.IRON
                        elif ore_roll < 0.85:
                            material = MaterialType.GOLD
                        else:
                            material = MaterialType.MARBLE
                
                # Abyss/Volcanic - obsidian and valuable ores
                else:
                    if self.settings.has_volcanic:
                        # Volcanic zone
                        material = MaterialType.OBSIDIAN
                        
                        # Lava pockets - use cache for lava noise
                        cache_key = (world_x//5, world_y//5)
                        if cache_key not in self._lava_noise_cache:
                            self._lava_noise_cache[cache_key] = noise.pnoise3(
                                world_x * 0.03, 
                                world_y * 0.03,
                                (world_x + world_y) * 0.005,
                                octaves=1,  # Reduced from 2
                                persistence=0.5,
                                lacunarity=2.0,
                                repeatx=10000,
                                repeaty=10000,
                                repeatz=10000,
                                base=self.settings.seed + 2000
                            )
                        
                        lava_noise = self._lava_noise_cache[cache_key]
                        
                        if lava_noise > 0.6:
                            if self.random.random() < 0.5:
                                material = MaterialType.LAVA
                            else:
                                material = MaterialType.OBSIDIAN
                                
                        # Gold veins
                        if lava_noise < -0.6 and self.random.random() < 0.3:
                            material = MaterialType.GOLD
                    else:
                        # Normal abyss without volcanic activity
                        material = MaterialType.GRANITE
                        
                        if self.random.random() < 0.1:
                            # Rare materials
                            ore_roll = self.random.random()
                            if ore_roll < 0.7:
                                material = MaterialType.IRON
                            else:
                                material = MaterialType.GOLD
        
        return material
    
    def create_world_preview(self, chunks_list):
        """
        Create a quick preview of the entire world for the loading screen.
        Only creates biome-based preview without actual chunk generation.
        
        Args:
            chunks_list: List of (x, y, dist) tuples for all chunks to be generated
        """
        # Clear preview chunks
        self.preview_chunks = []
        preview_size = CHUNK_SIZE // 4
        
        # Pre-populate biome materials map for quick lookups
        biome_materials = {
            BiomeType.MEADOW: MaterialType.GRASS,
            BiomeType.DESERT: MaterialType.SAND,
            BiomeType.MOUNTAIN: MaterialType.STONE,
            BiomeType.UNDERGROUND: MaterialType.STONE,
            BiomeType.DEPTHS: MaterialType.GRANITE,
            BiomeType.ABYSS: MaterialType.OBSIDIAN,
            BiomeType.VOLCANIC: MaterialType.LAVA,
            BiomeType.FOREST: MaterialType.WOOD
        }
        
        # Create preview for all chunks
        for chunk_x, chunk_y, _ in chunks_list:
            # Create empty preview
            preview_data = np.zeros((preview_size, preview_size), dtype=np.int8)
            
            # Quick biome lookup
            chunk_center_x = chunk_x * CHUNK_SIZE + (CHUNK_SIZE // 2)
            chunk_center_y = chunk_y * CHUNK_SIZE + (CHUNK_SIZE // 2)
            biome = self.get_biome_at(chunk_center_x, chunk_center_y)
            
            # Get material for this biome
            biome_material = biome_materials.get(biome, MaterialType.AIR)
            
            # Quick fill the preview
            preview_data.fill(biome_material.value)
            
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
        Creates preview data for loading screen visualization.
        
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
                    chunks_to_process.append((center_x + dx, center_y + dy))
        
        total_chunks = len(chunks_to_process)
        chunks_loaded = 0
        
        # Clear preview chunks
        self.preview_chunks = []
        
        # Pre-populate biome materials map for quick lookups
        biome_materials = {
            BiomeType.MEADOW: MaterialType.GRASS,
            BiomeType.DESERT: MaterialType.SAND,
            BiomeType.MOUNTAIN: MaterialType.STONE,
            BiomeType.UNDERGROUND: MaterialType.STONE,
            BiomeType.DEPTHS: MaterialType.GRANITE,
            BiomeType.ABYSS: MaterialType.OBSIDIAN,
            BiomeType.VOLCANIC: MaterialType.LAVA,
            BiomeType.FOREST: MaterialType.WOOD
        }
        
        # First pass: create low-resolution preview immediately
        preview_size = CHUNK_SIZE // 4
        
        # Create all preview chunks at once to show complete world outline
        for chunk_x, chunk_y in chunks_to_process:
            # Create biome visualization in the preview first to give immediate feedback
            preview_data = np.zeros((preview_size, preview_size), dtype=np.int8)
            
            # Quick calculation of biome for center of chunk
            chunk_center_x = chunk_x * CHUNK_SIZE + (CHUNK_SIZE // 2)
            chunk_center_y = chunk_y * CHUNK_SIZE + (CHUNK_SIZE // 2)
            biome = self.get_biome_at(chunk_center_x, chunk_center_y)
            
            # Get material for biome (default to AIR if not found)
            biome_material = biome_materials.get(biome, MaterialType.AIR)
            
            # Quick fill of preview with biome material
            preview_data.fill(biome_material.value)
            
            # Store preview immediately
            self.preview_chunks.append((chunk_x, chunk_y, preview_data))
            
            # Update loading progress for first pass (first 25%)
            chunks_loaded += 0.25
            self.loading_progress = chunks_loaded / total_chunks
        
        # Second pass: actually generate the chunks (more computationally intensive)
        # We use a spiral pattern to prioritize chunks near the center
        spiral_chunks = sorted(chunks_to_process, 
                              key=lambda c: (c[0] - center_x)**2 + (c[1] - center_y)**2)
        
        # Process chunks in spiral order (center to outside)
        for i, (chunk_x, chunk_y) in enumerate(spiral_chunks):
            # Generate the actual chunk
            chunk = self.ensure_chunk_exists(chunk_x, chunk_y)
            if not chunk.generated:
                self.generate_chunk(chunk)
            
            # Only update preview for every few chunks (optimization)
            # Still generate all chunks, but don't always update preview
            if i % 3 == 0 and chunk.generated:
                # Create a simplified preview instead of calculating dominant material
                # This is much faster than the previous approach
                preview_data = np.zeros((preview_size, preview_size), dtype=np.int8)
                
                # Sample a grid of points from the chunk instead of processing every tile
                for py in range(preview_size):
                    for px in range(preview_size):
                        # Sample center point of each 4x4 block
                        y, x = py*4 + 2, px*4 + 2
                        if 0 <= y < CHUNK_SIZE and 0 <= x < CHUNK_SIZE:
                            material = chunk.tiles[y, x]
                            preview_data[py, px] = material.value
                
                # Find and update existing preview
                for i, (cx, cy, _) in enumerate(self.preview_chunks):
                    if cx == chunk_x and cy == chunk_y:
                        self.preview_chunks[i] = (chunk_x, chunk_y, preview_data)
                        break
            
            # Update progress (remaining 75%)
            chunks_loaded += 0.75
            self.loading_progress = min(0.99, chunks_loaded / total_chunks)
        
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