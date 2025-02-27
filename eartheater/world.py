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
        Uses a combination of horizontal position and depth to create three distinct zones:
        sky, surface, and underground
        
        Args:
            world_x: X coordinate in world space
            world_y: Y coordinate in world space
            
        Returns:
            The biome type at the specified location
        """
        # Sky biomes (future expansion)
        # Currently we don't have specific sky biomes, but this structure allows for future addition
        
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
        
        # We want more natural biome boundaries with larger continuous areas
        # Use a larger scale noise map to create more natural boundaries
        biome_noise = noise.pnoise2(
            world_x * 0.005,  # Very large scale for major biome regions
            world_y * 0.005,  # Include Y coordinate for more varied transitions
            octaves=2,
            persistence=0.5,
            lacunarity=2.0,
            repeatx=10000,
            repeaty=10000,
            base=self.settings.seed + 5000  # Different base for biome noise
        )
        
        # For surface biomes, still use distance-based approach but modify with noise
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
                
            # Use noise to make borders more natural
            # Modify the effective distance based on noise value
            noise_factor = 1.0 + (biome_noise * 0.5)  # Range from 0.5 to 1.5
            
            # Different biomes can have different "pull" or influence based on type
            biome_factor = 1.0
            if biome == BiomeType.MOUNTAIN:
                biome_factor = 0.8  # Mountains have stronger influence
            elif biome == BiomeType.DESERT:
                biome_factor = 1.1  # Desert slightly less influential
            
            # Final effective distance with noise variation
            distance = math.sqrt(dx*dx + dy*dy) * noise_factor * biome_factor
            
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
        
        # Calculate distances to each biome center with added noise variation
        distances = {}
        total_weight = 0.0
        
        # Get noise for biome transitions similar to the one used in get_biome_at
        # But use it differently here for blending
        try:
            biome_noise = noise.pnoise2(
                world_x * 0.005,
                world_y * 0.005,
                octaves=2,
                persistence=0.5,
                lacunarity=2.0,
                repeatx=10000,
                repeaty=10000,
                base=self.settings.seed + 5000
            )
        except Exception:
            # Fallback if noise calculation fails
            biome_noise = 0.0
        
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
                
            # Basic distance calculation
            distance = math.sqrt(dx*dx + dy*dy)
            
            # Convert distance to weight using inverse square with falloff
            # 1.0 at center, decreasing as distance increases
            if distance < 1:
                weight = 1.0
            else:
                # We use inverse distance raised to a power for a smoother transition
                # Add noise factor but ensure we don't create numerical issues
                noise_factor = 1.0
                try:
                    noise_factor = 1.0 + (biome_noise * 0.3)  # Milder effect in blending than in biome selection
                except Exception:
                    # Keep default factor if calculation fails
                    pass
                
                # Calculate weight with noise modulation
                distance_mod = max(1.0, distance * noise_factor)  # Avoid division by zero
                weight = 1.0 / (1.0 + (distance_mod / self.biome_blending) ** 2)
            
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
                'details': self.random.randint(0, 1000),
                'large_features': self.random.randint(0, 1000),
                'material_splotches': self.random.randint(0, 1000)
            }
        
        noise_seeds = self.noise_maps[biome]
        
        # Adjust terrain generation parameters based on biome
        if biome == BiomeType.MEADOW:
            # Hills with significant elevation changes
            scale = self.terrain_scale * 0.6
            amplitude = self.terrain_amplitude * 1.2
            persistence = 0.65
            octaves = self.terrain_octaves
            base_height += 10  # Higher base elevation for hills
        
        elif biome == BiomeType.DESERT:
            # Large rolling dunes with deep valleys
            scale = self.terrain_scale * 0.4
            amplitude = self.terrain_amplitude * 0.9
            persistence = 0.7
            octaves = self.terrain_octaves - 1
            
            # Add large mesas/plateaus
            mesa_noise = noise.pnoise2(
                world_x * 0.005, 
                0,
                octaves=1,
                persistence=0.7,
                lacunarity=2.0,
                repeatx=10000,
                repeaty=10000,
                base=noise_seeds['large_features']
            )
            
            if mesa_noise > 0.6:
                # Large flat mesa
                amplitude *= 0.4
                base_height += int(mesa_noise * 20)  # Raise mesa height
        
        elif biome == BiomeType.MOUNTAIN:
            # Very tall jagged peaks
            scale = self.terrain_scale * 0.8
            amplitude = self.terrain_amplitude * 4.0  # Much higher mountains
            persistence = 0.75
            octaves = self.terrain_octaves + 2
            
            # Make mountains significantly taller
            base_height += 30  # Much higher base elevation
        
        elif biome == BiomeType.FOREST:
            # Rolling hills with varied elevation
            scale = self.terrain_scale * 0.55
            amplitude = self.terrain_amplitude * 1.1
            persistence = 0.6
            octaves = self.terrain_octaves
            base_height += 5  # Slightly higher base elevation
        
        else:
            # Default parameters for other biomes
            scale = self.terrain_scale
            amplitude = self.terrain_amplitude
            persistence = 0.5
            octaves = self.terrain_octaves
        
        # Generate large-scale terrain features using Perlin noise
        large_scale_terrain = noise.pnoise2(
            world_x * scale * 0.2,  # Much larger scale for major landforms
            0,
            octaves=2,
            persistence=0.8,
            lacunarity=2.0,
            repeatx=10000,
            repeaty=10000,
            base=noise_seeds['large_features']
        )
        
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
        
        # Add hills with lower frequency but higher amplitude
        hill_noise = noise.pnoise2(
            world_x * scale * 0.3,
            0,
            octaves=3,
            persistence=0.8,  # Higher persistence for more pronounced hills
            lacunarity=2.0,
            repeatx=10000,
            repeaty=10000,
            base=noise_seeds['hills']
        ) * 1.5  # Amplify hill effect
        
        # Small details
        detail_noise = noise.pnoise2(
            world_x * scale * 3.0,
            0,
            octaves=2,
            persistence=0.4,
            lacunarity=2.0,
            repeatx=10000,
            repeaty=10000,
            base=noise_seeds['details']
        ) * 0.2  # Slightly more detail
        
        # Combine noise layers with different weights
        # Give much more weight to large-scale features and hills
        combined_noise = (large_scale_terrain * 0.4) + (base_terrain * 0.3) + (hill_noise * 0.25) + detail_noise
        
        # Map noise value (-1 to 1) to terrain height with biome-specific variation
        terrain_height = int((combined_noise + 1) * amplitude) + base_height
        
        # Special adjustments for certain biomes
        if biome == BiomeType.DESERT:
            # Add large canyons
            canyon_noise = noise.pnoise2(
                world_x * 0.004,  # Larger scale for wider canyons
                0,
                octaves=1,
                persistence=0.7,
                lacunarity=2.0,
                repeatx=10000,
                repeaty=10000,
                base=noise_seeds['base'] + 1000
            )
            
            if canyon_noise > 0.6 and canyon_noise < 0.8:
                # Deep canyon cut
                canyon_depth = int((canyon_noise - 0.6) * 30 * amplitude)
                terrain_height -= canyon_depth
        
        elif biome == BiomeType.MOUNTAIN:
            # Add mountain ranges and valleys
            mountain_range_noise = noise.pnoise2(
                world_x * 0.003,  
                0,
                octaves=1,
                persistence=0.7,
                lacunarity=2.0,
                repeatx=10000,
                repeaty=10000,
                base=noise_seeds['large_features'] + 500
            )
            
            # Create mountain ranges
            if mountain_range_noise > 0.2:
                # Higher mountains in the range center
                range_factor = (mountain_range_noise - 0.2) * 2  # 0 to 1.6
                terrain_height += int(range_factor * amplitude * 0.5)
            
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
            
            if plateau_noise > 0.7:
                # Plateau - flatter terrain but kept at high elevation
                plateau_height = terrain_height
                terrain_height = int(base_height + amplitude * 2.5 + (plateau_noise - 0.7) * amplitude * 5)
                
        elif biome == BiomeType.MEADOW:
            # Add distinct hills and valleys
            hill_feature_noise = noise.pnoise2(
                world_x * 0.01, 
                0,
                octaves=2,
                persistence=0.6,
                lacunarity=2.0,
                repeatx=10000,
                repeaty=10000,
                base=noise_seeds['large_features'] + 1500
            )
            
            # Amplify hills and valleys
            if hill_feature_noise > 0.3:
                terrain_height += int((hill_feature_noise - 0.3) * amplitude * 1.5)
            elif hill_feature_noise < -0.3:
                terrain_height -= int((-hill_feature_noise - 0.3) * amplitude * 1.0)
        
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
                'caves': self.random.randint(0, 1000),
                'cave_system': self.random.randint(0, 1000),
                'cave_size': self.random.randint(0, 1000)
            }
        
        noise_seeds = self.noise_maps[biome]
        
        # Adjust cave parameters based on biome and depth
        cave_scale = self.cave_scale
        cave_threshold = self.cave_density
        
        # Depth-based adjustments
        if world_y > self.abyss_start:
            # More caves in the abyss
            cave_threshold *= 1.8  # Significantly more caves in the abyss
            cave_scale *= 0.8  # Larger cave structures
        elif world_y > self.depths_start:
            # More caves in the depths
            cave_threshold *= 1.5  # More caves in the depths
            cave_scale *= 0.9  # Larger cave structures
        elif world_y > self.underground_start:
            # Standard underground caves
            cave_threshold *= 1.2
            cave_scale *= 1.0
        
        # Biome-based adjustments
        if biome == BiomeType.UNDERGROUND:
            # Standard caves - winding and varied
            pass
        elif biome == BiomeType.DEPTHS:
            # Larger cave systems with connected caverns
            cave_scale *= 0.8
            cave_threshold *= 1.3
        elif biome == BiomeType.ABYSS:
            # Vast caverns, more open spaces
            cave_scale *= 0.6
            cave_threshold *= 1.6
        elif biome == BiomeType.VOLCANIC:
            # Lava tubes and magma chambers - more vertical
            cave_scale *= 0.7
            cave_threshold *= 1.4
        
        # Generate large-scale cave system noise - this creates large connected cave networks
        cave_system_noise = noise.pnoise3(
            world_x * cave_scale * 0.5,  # Larger scale for cave systems
            world_y * cave_scale * 0.5,
            (world_x + world_y) * 0.02,  # Slower variation for more continuous caves
            octaves=2, 
            persistence=0.6,
            lacunarity=2.0,
            repeatx=10000,
            repeaty=10000,
            repeatz=10000,
            base=noise_seeds.get('cave_system', 0)
        )
        
        # Generate cave size variation noise - this modulates cave size
        cave_size_noise = noise.pnoise2(
            world_x * cave_scale * 0.3,
            world_y * cave_scale * 0.3,
            octaves=2,
            persistence=0.5,
            lacunarity=2.0,
            repeatx=10000,
            repeaty=10000,
            base=noise_seeds.get('cave_size', 0)
        )
        
        # Generate detailed cave shape noise - this creates the actual cave boundaries
        cave_detail_noise = noise.pnoise3(
            world_x * cave_scale,
            world_y * cave_scale,
            (world_x * 0.5 + world_y * 0.5) * 0.05,  # Z-coordinate for 3D variation
            octaves=3,
            persistence=0.5,
            lacunarity=2.0,
            repeatx=10000,
            repeaty=10000,
            repeatz=10000,
            base=noise_seeds.get('caves', 0)
        )
        
        # Adjust threshold based on depth to create more caves deeper down
        depth_factor = 1 + ((world_y - self.underground_start) / 80)
        depth_factor = max(1, min(depth_factor, 2.5))  # Clamp between 1 and 2.5
        
        # Combine noise layers to create caves
        # Use cave system noise to define where cave systems exist
        # Use size noise to modulate cave size within systems
        # Use detail noise for the exact cave boundaries
        
        # Areas with high system noise value are cave systems
        if cave_system_noise > 0.1:
            # Calculate cave threshold based on system noise value
            # Higher system noise = more likely to be a cave
            system_factor = (cave_system_noise - 0.1) * 3  # Range 0-2.7
            system_factor = min(system_factor, 1.0)  # Cap at 1.0
            
            # Adjust size based on size noise
            size_factor = (cave_size_noise * 0.5) + 0.5  # Range 0-1
            
            # Final threshold calculation
            cave_size_threshold = cave_threshold * depth_factor * (1.0 + size_factor)
            
            # Determine if there should be a cave based on detail noise
            # This creates the exact cave boundaries with varied shapes
            is_cave = cave_detail_noise > 0.3 - (system_factor * 0.3) and cave_detail_noise < 0.3 + cave_size_threshold
            
            # Create occasional large caverns at depth
            if world_y > self.depths_start and cave_system_noise > 0.7 and cave_size_noise > 0.6:
                is_cave = True
                
            return is_cave
        else:
            # Outside of cave systems, still allow for isolated caves
            # but with much lower probability
            isolated_cave_threshold = cave_threshold * 0.3 * depth_factor
            return cave_detail_noise > 0.4 and cave_detail_noise < 0.4 + isolated_cave_threshold
    
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
                
                # Surface layer material depends on biome blend with large-scale noise variation
                if world_y <= terrain_height + self.topsoil_depth:
                    # Generate large-scale material variation noise
                    # This will create large splotches of different materials
                    material_variation_noise = noise.pnoise3(
                        world_x * 0.02,  # Large scale for big splotches
                        world_y * 0.02,
                        0.5,  # Fixed third coordinate for 2D variation
                        octaves=2,
                        persistence=0.5,
                        lacunarity=2.0,
                        repeatx=10000,
                        repeaty=10000,
                        repeatz=10000,
                        base=self.settings.seed + 3000  # Different seed for material variation
                    )
                    
                    # Get the dominant biome from weights
                    max_biome = max(biome_weights.items(), key=lambda x: x[1])[0]
                    
                    # Use noise to create material variations within biomes
                    if max_biome == BiomeType.MEADOW:
                        # Meadow: mix of grass, dirt, and occasional stone
                        if material_variation_noise > 0.4:
                            material = MaterialType.GRASS
                        elif material_variation_noise > 0.0:
                            material = MaterialType.DIRT
                        elif material_variation_noise > -0.6:
                            material = MaterialType.GRASS
                        else:
                            material = MaterialType.STONE
                            
                    elif max_biome == BiomeType.DESERT:
                        # Desert: mix of sand, sandstone, and clay
                        if material_variation_noise > 0.2:
                            material = MaterialType.SAND
                        elif material_variation_noise > -0.2:
                            material = MaterialType.SANDSTONE
                        else:
                            material = MaterialType.CLAY
                            
                    elif max_biome == BiomeType.MOUNTAIN:
                        # Mountain: mix of stone, gravel, and occasional dirt
                        if material_variation_noise > 0.3:
                            material = MaterialType.STONE
                        elif material_variation_noise > -0.4:
                            material = MaterialType.GRAVEL
                        else:
                            material = MaterialType.DIRT
                            
                    elif max_biome == BiomeType.FOREST:
                        # Forest: mix of grass, dirt, and wood
                        if material_variation_noise > 0.4:
                            material = MaterialType.GRASS
                        elif material_variation_noise > 0.0:
                            material = MaterialType.DIRT
                        elif material_variation_noise > -0.5:
                            material = MaterialType.GRASS
                        else:
                            material = MaterialType.MOSS
                
                # Dirt layer with distinct variations
                elif world_y <= terrain_height + self.underground_start:
                    # Get large-scale material variation for underground layers
                    underground_material_noise = noise.pnoise3(
                        world_x * 0.015,  # Large scale for big material clusters
                        world_y * 0.015,
                        0.5,  # Fixed third coordinate for 2D variation
                        octaves=2,
                        persistence=0.6,
                        lacunarity=2.0,
                        repeatx=10000,
                        repeaty=10000,
                        repeatz=10000,
                        base=self.settings.seed + 4000  # Different seed for underground variation
                    )
                    
                    # Create distinct layers of materials with large-scale variations
                    if underground_material_noise > 0.4:
                        material = MaterialType.DIRT
                    elif underground_material_noise > 0.0:
                        # Biome-influenced secondary material
                        desert_weight = biome_weights.get(BiomeType.DESERT, 0)
                        mountain_weight = biome_weights.get(BiomeType.MOUNTAIN, 0)
                        
                        if desert_weight > 0.4:
                            material = MaterialType.CLAY
                        elif mountain_weight > 0.4:
                            material = MaterialType.GRAVEL
                        else:
                            material = MaterialType.DIRT
                    elif underground_material_noise > -0.4:
                        material = MaterialType.GRAVEL
                    else:
                        material = MaterialType.CLAY
                
                # Underground - base stone with large ore veins and material variation
                elif world_y <= self.depths_start:
                    # Base material is stone
                    material = MaterialType.STONE
                    
                    # Large-scale ore veins instead of small isolated deposits
                    # This creates proper ore veins instead of scattered deposits
                    cache_key = (world_x//6, world_y//6, 1)  # Group by 6x6 blocks for large veins
                    if cache_key not in self._ore_noise_cache:
                        # Calculate ore noise for large veins
                        self._ore_noise_cache[cache_key] = noise.pnoise3(
                            world_x * 0.03,  # Larger scale for bigger veins
                            world_y * 0.03,
                            (world_x + world_y) * 0.005,  # Slow variation in third dimension
                            octaves=2,
                            persistence=0.6,
                            lacunarity=2.0,
                            repeatx=10000,
                            repeaty=10000,
                            repeatz=10000,
                            base=self.settings.seed  # Use world seed for consistency
                        )
                    
                    ore_noise = self._ore_noise_cache[cache_key]
                    
                    # Secondary material noise for variation between ores
                    secondary_noise = noise.pnoise2(
                        world_x * 0.04,
                        world_y * 0.04,
                        octaves=1,
                        persistence=0.5,
                        lacunarity=2.0,
                        repeatx=10000,
                        repeaty=10000,
                        base=self.settings.seed + 6000
                    )
                    
                    # Create distinctly shaped ore veins
                    # High noise values create ore veins
                    ore_chance = self.ore_frequency * (world_y - terrain_height) / 80
                    ore_chance = min(0.5, ore_chance)  # Cap at 50% for more ore
                    
                    if ore_noise > 0.65 and self.random.random() < ore_chance:
                        # Use secondary noise to determine ore type in this vein
                        if secondary_noise > 0.3:
                            material = MaterialType.COAL
                        elif secondary_noise > -0.3:
                            # Deeper parts more likely to have iron
                            depth_factor = (world_y - terrain_height) / 50  # 0 to ~1+
                            if self.random.random() < 0.3 + (depth_factor * 0.3):
                                material = MaterialType.IRON
                            else:
                                material = MaterialType.COAL
                        else:
                            # Bottom of this layer occasionally has gold
                            if world_y > self.depths_start - 10 and self.random.random() < 0.2:
                                material = MaterialType.GOLD
                            else:
                                material = MaterialType.IRON
                
                # Depths - tougher stone and more valuable ores
                elif world_y <= self.abyss_start:
                    # Base material is granite
                    material = MaterialType.GRANITE
                    
                    # Large-scale material variation for depths
                    cache_key = (world_x//8, world_y//8, 2)  # Group by 8x8 blocks for depths
                    if cache_key not in self._ore_noise_cache:
                        self._ore_noise_cache[cache_key] = noise.pnoise3(
                            world_x * 0.025,  # Larger scale for bigger features
                            world_y * 0.025,
                            (world_x + world_y) * 0.004,
                            octaves=2,
                            persistence=0.6,
                            lacunarity=2.0,
                            repeatx=10000,
                            repeaty=10000,
                            repeatz=10000,
                            base=self.settings.seed + 1000
                        )
                    
                    ore_noise = self._ore_noise_cache[cache_key]
                    
                    # Material variation noise
                    variation_noise = noise.pnoise2(
                        world_x * 0.03,
                        world_y * 0.03,
                        octaves=1,
                        persistence=0.5,
                        lacunarity=2.0,
                        repeatx=10000,
                        repeaty=10000,
                        base=self.settings.seed + 7000
                    )
                    
                    # Create distinct material regions in the depths
                    if ore_noise > 0.7:
                        if variation_noise > 0.2:
                            material = MaterialType.IRON
                        elif variation_noise > -0.2:
                            material = MaterialType.GOLD
                        else:
                            material = MaterialType.MARBLE
                    elif ore_noise < -0.7:
                        # Special rare materials in distinct areas
                        material = MaterialType.MARBLE
                
                # Abyss/Volcanic - obsidian and valuable ores
                else:
                    if self.settings.has_volcanic:
                        # Volcanic zone - base material is obsidian
                        material = MaterialType.OBSIDIAN
                        
                        # Large lava chambers and pockets
                        cache_key = (world_x//10, world_y//10, 3)
                        if cache_key not in self._lava_noise_cache:
                            self._lava_noise_cache[cache_key] = noise.pnoise3(
                                world_x * 0.015,  # Larger scale for big features
                                world_y * 0.015,
                                (world_x + world_y) * 0.003,
                                octaves=2,
                                persistence=0.7,
                                lacunarity=2.0,
                                repeatx=10000,
                                repeaty=10000,
                                repeatz=10000,
                                base=self.settings.seed + 2000
                            )
                        
                        lava_noise = self._lava_noise_cache[cache_key]
                        
                        # Secondary variation noise
                        secondary_noise = noise.pnoise2(
                            world_x * 0.025,
                            world_y * 0.025,
                            octaves=1,
                            persistence=0.5,
                            lacunarity=2.0,
                            repeatx=10000,
                            repeaty=10000,
                            base=self.settings.seed + 8000
                        )
                        
                        # Create large lava chambers with obsidian borders
                        if lava_noise > 0.5:
                            if secondary_noise > 0.0:
                                material = MaterialType.LAVA
                            else:
                                material = MaterialType.OBSIDIAN
                                
                        # Rich gold veins in specific areas
                        elif lava_noise < -0.6:
                            material = MaterialType.GOLD
                    else:
                        # Normal abyss without volcanic activity
                        material = MaterialType.GRANITE
                        
                        # Large-scale material variation
                        abyss_material_noise = noise.pnoise3(
                            world_x * 0.02,
                            world_y * 0.02,
                            0.5,
                            octaves=2,
                            persistence=0.6,
                            lacunarity=2.0,
                            repeatx=10000,
                            repeaty=10000,
                            repeatz=10000,
                            base=self.settings.seed + 9000
                        )
                        
                        # Create distinct material regions in the abyss
                        if abyss_material_noise > 0.6:
                            material = MaterialType.GOLD
                        elif abyss_material_noise > 0.2:
                            material = MaterialType.IRON
                        elif abyss_material_noise < -0.6:
                            material = MaterialType.MARBLE
        
        return material
    
    def create_world_preview(self, chunks_list):
        """
        Create a quick preview of the entire world for the loading screen.
        Uses terrain height to visualize the landscape accurately.
        
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
        
        # Material colors for underground visualization
        underground_materials = [
            MaterialType.STONE,
            MaterialType.DIRT,
            MaterialType.GRANITE,
            MaterialType.OBSIDIAN
        ]
        
        # Create preview for all chunks with actual terrain heights
        for chunk_x, chunk_y, _ in chunks_list:
            # Create empty preview
            preview_data = np.zeros((preview_size, preview_size), dtype=np.int8)
            
            # Generate an accurate preview by sampling terrain height
            for px in range(preview_size):
                # Map preview pixel to world coordinates
                world_x = chunk_x * CHUNK_SIZE + (px * 4) + 2  # Center of each 4x4 block
                
                # Calculate terrain height at this x-position
                # Use blended biome heights
                biome_weights = self.get_biome_blend(world_x, 0)
                terrain_height = 0
                
                for biome, weight in biome_weights.items():
                    if biome in [BiomeType.MEADOW, BiomeType.DESERT, BiomeType.MOUNTAIN, BiomeType.FOREST]:
                        biome_height = self.get_terrain_height(world_x, biome)
                        terrain_height += biome_height * weight
                
                terrain_height = int(terrain_height)
                
                # Map terrain height to preview space
                terrain_height_scaled = max(0, min(preview_size - 1, terrain_height // 4))
                
                # Fill in the preview data
                for py in range(preview_size):
                    # Calculate world y-coordinate
                    world_y = chunk_y * CHUNK_SIZE + (py * 4) + 2
                    
                    if py < terrain_height_scaled:
                        # Above ground - air
                        preview_data[py, px] = MaterialType.AIR.value
                    elif py == terrain_height_scaled:
                        # Surface - based on biome
                        biome = self.get_biome_at(world_x, world_y)
                        biome_material = biome_materials.get(biome, MaterialType.GRASS)
                        preview_data[py, px] = biome_material.value
                    else:
                        # Underground - determine based on depth
                        depth = py - terrain_height_scaled
                        if depth < 3:
                            # Near surface layer
                            preview_data[py, px] = MaterialType.DIRT.value
                        elif depth < 6:
                            # Upper underground
                            preview_data[py, px] = MaterialType.STONE.value
                        elif depth < 10: 
                            # Deeper underground
                            preview_data[py, px] = MaterialType.GRANITE.value
                        else:
                            # Deep underground
                            preview_data[py, px] = MaterialType.OBSIDIAN.value
                            
                            # Occasionally add lava/special materials
                            if world_y > self.depths_start and self.random.random() < 0.2:
                                preview_data[py, px] = MaterialType.LAVA.value
                
                # Add water where appropriate
                if terrain_height > self.water_level:
                    water_height_scaled = max(0, min(preview_size - 1, self.water_level // 4))
                    # Make sure we're not trying to add water above the terrain
                    if water_height_scaled > terrain_height_scaled:
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
            BiomeType.MEADOW: MaterialType.GRASS,
            BiomeType.DESERT: MaterialType.SAND,
            BiomeType.MOUNTAIN: MaterialType.STONE,
            BiomeType.UNDERGROUND: MaterialType.STONE,
            BiomeType.DEPTHS: MaterialType.GRANITE,
            BiomeType.ABYSS: MaterialType.OBSIDIAN,
            BiomeType.VOLCANIC: MaterialType.LAVA,
            BiomeType.FOREST: MaterialType.WOOD
        }
        
        # First pass: create accurate terrain preview immediately
        preview_size = CHUNK_SIZE // 4
        
        # Create all preview chunks with terrain visualization
        # Sort chunks by distance from center for prioritized loading
        chunks_to_process.sort(key=lambda c: c[2])
        
        # Generate initial terrain preview for all chunks
        self.create_world_preview(chunks_to_process)
            
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
                            material = chunk.tiles[y, x]
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