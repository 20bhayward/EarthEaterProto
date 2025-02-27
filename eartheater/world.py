"""
World management module for EarthEater
"""
import numpy as np
from typing import Dict, Tuple, Optional, List, Set
import random
import noise
import math

from eartheater.constants import (
    MaterialType, CHUNK_SIZE, ACTIVE_CHUNKS_RADIUS,
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
    """Manages the game world"""
    
    def __init__(self):
        """Initialize an empty world"""
        self.chunks: Dict[Tuple[int, int], Chunk] = {}
        self.active_chunks: Set[Tuple[int, int]] = set()
        self.physics_chunks: Set[Tuple[int, int]] = set()  # Chunks that need physics simulation
        self.physics_radius = 3  # Smaller radius for physics simulation
        self.player_chunk = (0, 0)
        self.random = random.Random(WORLD_SEED)
        self.preloaded = False  # Flag to indicate if initial chunks have been preloaded
        self.loading_progress = 0.0  # Progress for loading screen
        self.preview_chunks: List[Tuple[int, int, np.ndarray]] = []  # For loading visualization
        
        # Initialize perlin noise for terrain generation
        self.terrain_scale = 0.05  # Controls how large terrain features are
        self.terrain_octaves = 6   # More octaves = more detail
        self.cave_scale = 0.1      # Controls cave size
    
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
        Generate terrain for a chunk
        
        Args:
            chunk: The chunk to generate
        """
        if chunk.generated:
            return
            
        for local_x in range(CHUNK_SIZE):
            for local_y in range(CHUNK_SIZE):
                world_x = chunk.x * CHUNK_SIZE + local_x
                world_y = chunk.y * CHUNK_SIZE + local_y
                
                # Generate terrain height using multiple layers of Perlin noise for hills
                # Base terrain
                base_terrain = noise.pnoise2(
                    world_x * self.terrain_scale, 
                    0,
                    octaves=self.terrain_octaves, 
                    persistence=0.5, 
                    lacunarity=2.0, 
                    repeatx=10000, 
                    repeaty=10000, 
                    base=self.random.randint(0, 1000)
                )
                
                # Add hills with lower frequency
                hill_noise = noise.pnoise2(
                    world_x * self.terrain_scale * 0.3,
                    0,
                    octaves=3,
                    persistence=0.7,
                    lacunarity=2.0,
                    repeatx=10000,
                    repeaty=10000,
                    base=self.random.randint(0, 1000)
                )
                
                # Small details
                detail_noise = noise.pnoise2(
                    world_x * self.terrain_scale * 3.0,
                    0,
                    octaves=2,
                    persistence=0.3,
                    lacunarity=2.0,
                    repeatx=10000,
                    repeaty=10000,
                    base=self.random.randint(0, 1000)
                ) * 0.1
                
                # Combine noise layers with different weights
                combined_noise = (base_terrain * 0.6) + (hill_noise * 0.35) + detail_noise
                
                # Map noise value (-1 to 1) to terrain height with more variation
                terrain_height = int((combined_noise + 1) * TERRAIN_AMPLITUDE) + 60
                
                # Generate caves using 3D Perlin noise
                cave_value = noise.pnoise3(
                    world_x * self.cave_scale,
                    world_y * self.cave_scale,
                    chunk.x * 0.1,  # Use chunk coords for 3D variation
                    octaves=3,
                    persistence=0.5,
                    lacunarity=2.0,
                    repeatx=10000,
                    repeaty=10000,
                    repeatz=10000,
                    base=self.random.randint(0, 1000)
                )
                
                # Determine material type based on depth and noise
                material = MaterialType.AIR
                
                # If below terrain height, add terrain
                if world_y > terrain_height:
                    # Base material is dirt
                    material = MaterialType.DIRT
                    
                    # Add stone below surface (thicker dirt layer)
                    if world_y > terrain_height + DIRT_LAYER_DEPTH:
                        material = MaterialType.STONE
                    
                    # Create caves (more common deeper down)
                    cave_threshold = CAVE_DENSITY * (1 + (world_y - terrain_height) / 100)
                    if cave_value > 0.3 and cave_value < 0.3 + cave_threshold:
                        material = MaterialType.AIR
                
                    # Add ore/material pockets
                    if material == MaterialType.STONE:
                        ore_noise = self.random.random()
                        if ore_noise < 0.07:
                            material = MaterialType.SAND
                        elif ore_noise < 0.12:
                            material = MaterialType.GRAVEL
                
                # Calculate distance from origin (for safe zone around spawn)
                dist_from_origin = math.sqrt(world_x**2 + world_y**2)
                
                # Add water below water level, but not in safe zone
                if material == MaterialType.AIR and world_y > WATER_LEVEL and dist_from_origin > SAFE_ZONE_RADIUS:
                    # Create water pools in depressions
                    # Check if surrounded by terrain (in a depression)
                    is_depression = world_y > terrain_height - 3 and world_y < terrain_height + 5
                    
                    if is_depression or world_y > WATER_LEVEL + 20:
                        material = MaterialType.WATER
                
                # Add lava deep underground in caves
                if material == MaterialType.AIR and world_y > terrain_height + 100:
                    if self.random.random() < 0.2:
                        material = MaterialType.LAVA
                
                # Add pockets of stone near the surface (for varied terrain)
                if material == MaterialType.DIRT:
                    stone_noise = noise.pnoise2(
                        world_x * 0.1, 
                        world_y * 0.1,
                        octaves=2,
                        persistence=0.5,
                        lacunarity=2.0,
                        repeatx=10000,
                        repeaty=10000,
                        base=self.random.randint(0, 1000)
                    )
                    
                    if stone_noise > 0.7 and world_y > terrain_height + 8:
                        material = MaterialType.STONE
                
                chunk.set_tile(local_x, local_y, material)
        
        # Mark the chunk as generated
        chunk.generated = True
        chunk.needs_update = True
    
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
            
            # Add chunks within radius to active set (for rendering)
            for dx in range(-ACTIVE_CHUNKS_RADIUS, ACTIVE_CHUNKS_RADIUS + 1):
                for dy in range(-ACTIVE_CHUNKS_RADIUS, ACTIVE_CHUNKS_RADIUS + 1):
                    cx = player_cx + dx
                    cy = player_cy + dy
                    
                    # Skip chunks that are too far (use circular radius)
                    if dx*dx + dy*dy > ACTIVE_CHUNKS_RADIUS*ACTIVE_CHUNKS_RADIUS:
                        continue
                        
                    self.active_chunks.add((cx, cy))
                    
                    # Ensure the chunk exists and is generated
                    chunk = self.ensure_chunk_exists(cx, cy)
                    if not chunk.generated:
                        self.generate_chunk(chunk)
            
            # Add a smaller set of chunks for physics simulation
            for dx in range(-self.physics_radius, self.physics_radius + 1):
                for dy in range(-self.physics_radius, self.physics_radius + 1):
                    cx = player_cx + dx
                    cy = player_cy + dy
                    
                    # Skip chunks that are too far (use circular radius)
                    if dx*dx + dy*dy > self.physics_radius*self.physics_radius:
                        continue
                    
                    # Add to physics chunks set
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
        total_chunks = (2 * radius + 1) ** 2
        chunks_loaded = 0
        
        # Clear preview chunks
        self.preview_chunks = []
        
        # Calculate total steps including generation and saving preview data
        total_steps = total_chunks * 2  # Generate + preview for each chunk
        current_step = 0
        
        # First pass: generate the chunks
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                # Skip chunks that are too far (use circular radius)
                if dx*dx + dy*dy > radius*radius:
                    continue
                    
                chunk_x = center_x + dx
                chunk_y = center_y + dy
                
                # Ensure this chunk exists and is generated
                chunk = self.ensure_chunk_exists(chunk_x, chunk_y)
                if not chunk.generated:
                    self.generate_chunk(chunk)
                
                chunks_loaded += 1
                current_step += 1
                self.loading_progress = current_step / total_steps
                
                # Create a downsampled preview of the chunk for loading visualization
                if chunk.generated:
                    # Create a thumbnail of the chunk data (4x downsampled)
                    preview_size = CHUNK_SIZE // 4
                    preview_data = np.zeros((preview_size, preview_size), dtype=np.int8)
                    
                    # Downsample the chunk data by taking max material value in each 4x4 block
                    for py in range(preview_size):
                        for px in range(preview_size):
                            # Sample from 4x4 block
                            material_values = []
                            for sy in range(4):
                                for sx in range(4):
                                    y, x = py*4 + sy, px*4 + sx
                                    if 0 <= y < CHUNK_SIZE and 0 <= x < CHUNK_SIZE:
                                        material_values.append(int(chunk.tiles[y, x].value))
                            
                            # Use most common material
                            if material_values:
                                # Can't use mode directly on enums, so we use values
                                preview_data[py, px] = max(material_values)
                    
                    # Store preview
                    self.preview_chunks.append((chunk_x, chunk_y, preview_data))
                    
                    # Update progress again for preview creation
                    current_step += 1
                    self.loading_progress = current_step / total_steps
        
        self.preloaded = True
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