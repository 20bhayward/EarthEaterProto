"""World generation and management module"""
import random
import math
import numpy as np
from typing import Dict, Tuple, List, Optional, Set, Any
import noise

from eartheater.constants import (
    CHUNK_SIZE, ACTIVE_CHUNKS_RADIUS, 
    MaterialType, BiomeType, BlockType,
    DIRT_MATERIALS, GRASS_MATERIALS, STONE_MATERIALS, DEEP_STONE_MATERIALS,
    WorldGenSettings
)

class Chunk:
    """A chunk of the world containing blocks and entities"""
    def __init__(self, x: int, y: int, size: int = CHUNK_SIZE):
        self.x = x  # Chunk x coordinate in chunk space
        self.y = y  # Chunk y coordinate in chunk space
        self.size = size
        self.blocks = np.full((size, size), MaterialType.AIR, dtype=object)
        self.block_types = np.full((size, size), BlockType.FOREGROUND, dtype=object)
        self.last_physics_update = 0
        self.active = False
        self.needs_render_update = True
        
    def world_to_chunk_coords(self, world_x: int, world_y: int) -> Tuple[int, int]:
        """Convert world coordinates to local chunk coordinates"""
        local_x = world_x - (self.x * self.size)
        local_y = world_y - (self.y * self.size)
        return local_x, local_y
        
    def get_block(self, local_x: int, local_y: int) -> MaterialType:
        """Get a block at local coordinates"""
        if 0 <= local_x < self.size and 0 <= local_y < self.size:
            return self.blocks[local_y][local_x]
        return MaterialType.VOID
        
    def set_block(self, local_x: int, local_y: int, material: MaterialType,
                 block_type: BlockType = BlockType.FOREGROUND) -> bool:
        """Set a block at local coordinates"""
        if 0 <= local_x < self.size and 0 <= local_y < self.size:
            self.blocks[local_y][local_x] = material
            self.block_types[local_y][local_x] = block_type
            self.needs_render_update = True
            return True
        return False
        
    def is_empty(self) -> bool:
        """Check if chunk is completely empty (all air)"""
        return np.all(self.blocks == MaterialType.AIR)

class World:
    """The game world containing all chunks, terrain, and game state"""
    def __init__(self, settings: WorldGenSettings = None):
        """Initialize the world with given settings"""
        self.chunks: Dict[Tuple[int, int], Chunk] = {}
        self.active_chunks: Set[Tuple[int, int]] = set()
        self.settings = settings or WorldGenSettings()
        random.seed(self.settings.seed)
        np.random.seed(self.settings.seed)
        
        # World generation parameters
        self.terrain_height_cache = {}
        self.terrain_amplitude = self.settings.get_terrain_amplitude()
        self.spawn_position = (0, 0)  # Will be set in generate_initial_chunks
        
        # Initialize noise functions for terrain generation
        self.noise_seed = self.settings.seed
        
    def world_to_chunk_coords(self, world_x: int, world_y: int) -> Tuple[int, int]:
        """Convert world coordinates to chunk coordinates"""
        chunk_x = math.floor(world_x / CHUNK_SIZE)
        chunk_y = math.floor(world_y / CHUNK_SIZE)
        return chunk_x, chunk_y
    
    def get_block(self, world_x: int, world_y: int) -> MaterialType:
        """Get a block at world coordinates"""
        chunk_x, chunk_y = self.world_to_chunk_coords(world_x, world_y)
        chunk = self.get_chunk(chunk_x, chunk_y)
        
        if chunk:
            local_x, local_y = chunk.world_to_chunk_coords(world_x, world_y)
            return chunk.get_block(local_x, local_y)
        return MaterialType.VOID
    
    def set_block(self, world_x: int, world_y: int, material: MaterialType,
                 block_type: BlockType = BlockType.FOREGROUND) -> bool:
        """Set a block at world coordinates"""
        chunk_x, chunk_y = self.world_to_chunk_coords(world_x, world_y)
        chunk = self.get_chunk(chunk_x, chunk_y)
        
        if chunk:
            local_x, local_y = chunk.world_to_chunk_coords(world_x, world_y)
            return chunk.set_block(local_x, local_y, material, block_type)
        return False
    
    def get_chunk(self, chunk_x: int, chunk_y: int) -> Optional[Chunk]:
        """Get a chunk at given chunk coordinates, generate if needed"""
        chunk_key = (chunk_x, chunk_y)
        
        if chunk_key not in self.chunks:
            # Create new chunk
            self.chunks[chunk_key] = self.generate_chunk(chunk_x, chunk_y)
        
        return self.chunks.get(chunk_key)
    
    def update_active_chunks(self, center_x: int, center_y: int, radius: int = ACTIVE_CHUNKS_RADIUS):
        """Update which chunks are active based on player position"""
        center_chunk_x, center_chunk_y = self.world_to_chunk_coords(center_x, center_y)
        
        # Calculate new active chunks
        new_active_chunks = set()
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                chunk_key = (center_chunk_x + dx, center_chunk_y + dy)
                new_active_chunks.add(chunk_key)
                
                # Generate chunk if it doesn't exist
                if chunk_key not in self.chunks:
                    self.chunks[chunk_key] = self.generate_chunk(chunk_key[0], chunk_key[1])
        
        # Update active status
        for chunk_key in new_active_chunks:
            if chunk_key in self.chunks:
                self.chunks[chunk_key].active = True
        
        for chunk_key in self.active_chunks - new_active_chunks:
            if chunk_key in self.chunks:
                self.chunks[chunk_key].active = False
        
        self.active_chunks = new_active_chunks
        
    def get_chunks_in_radius(self, center_x: int, center_y: int, radius: int) -> List[Chunk]:
        """Get a list of chunks within a radius of the center position
        
        Args:
            center_x: Center x coordinate in world space
            center_y: Center y coordinate in world space
            radius: Radius in chunks
            
        Returns:
            List of chunks within the radius
        """
        center_chunk_x, center_chunk_y = self.world_to_chunk_coords(center_x, center_y)
        chunks = []
        
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                chunk_key = (center_chunk_x + dx, center_chunk_y + dy)
                if chunk_key in self.chunks:
                    chunks.append(self.chunks[chunk_key])
        
        return chunks
    
    def get_terrain_height(self, x: int) -> int:
        """Get terrain height at a given x coordinate with caching"""
        if x in self.terrain_height_cache:
            return self.terrain_height_cache[x]
        
        # Generate terrain height using simplex noise
        # Use a scale of 0.01 for large hills
        large_scale_noise = noise.pnoise1(x * 0.01, octaves=1, persistence=0.5, lacunarity=2.0, base=self.noise_seed)
        
        # Add some smaller details with a higher frequency
        small_scale_noise = noise.pnoise1(x * 0.05, octaves=2, persistence=0.5, lacunarity=2.0, base=self.noise_seed + 1) * 0.2
        
        # Calculate height (0-1 range * amplitude + base height)
        # Adjusted for ground level to be around y=100 (more space above ground)
        height = int(((large_scale_noise + small_scale_noise) * 0.5 + 0.5) * self.terrain_amplitude + 100)
        
        # Cache and return
        self.terrain_height_cache[x] = height
        return height
    
    def generate_chunk(self, chunk_x: int, chunk_y: int) -> Chunk:
        """Generate a new chunk with terrain"""
        chunk = Chunk(chunk_x, chunk_y)
        
        # Calculate world coordinates for this chunk
        world_x_start = chunk_x * CHUNK_SIZE
        world_y_start = chunk_y * CHUNK_SIZE
        
        # Generate terrain for each column in the chunk
        for local_x in range(CHUNK_SIZE):
            world_x = world_x_start + local_x
            terrain_height = self.get_terrain_height(world_x)
            
            # Fill blocks in this column
            for local_y in range(CHUNK_SIZE):
                world_y = world_y_start + local_y
                
                # Default to air
                material = MaterialType.AIR
                
                # Layered terrain generation
                if world_y > terrain_height:
                    # Above terrain is air
                    material = MaterialType.AIR
                elif world_y == terrain_height:
                    # Grass on top layer
                    material = random.choice(GRASS_MATERIALS)
                elif world_y > terrain_height - self.settings.grass_layer_thickness:
                    # Just below grass is thin top soil
                    material = MaterialType.DIRT_LIGHT
                elif world_y > terrain_height - self.settings.dirt_layer_thickness:
                    # Thick dirt layer
                    material = random.choice(DIRT_MATERIALS)
                elif world_y > terrain_height - self.settings.stone_transition_depth:
                    # Upper stone layer
                    material = random.choice(STONE_MATERIALS)
                else:
                    # Deep stone layer
                    material = random.choice(DEEP_STONE_MATERIALS)
                
                # Set the block in the chunk
                chunk.set_block(local_x, local_y, material)
        
        return chunk
    
    def generate_initial_chunks(self, radius: int = ACTIVE_CHUNKS_RADIUS):
        """Generate initial chunks around spawn point"""
        # Generate chunks in a square around (0,0)
        for chunk_x in range(-radius, radius + 1):
            for chunk_y in range(-radius, radius + 1):
                self.get_chunk(chunk_x, chunk_y)
        
        # Find a suitable spawn point
        self.find_spawn_point()
    
    def find_spawn_point(self):
        """Find a suitable spawn point on the surface"""
        # Start at x=0 and find the terrain height
        spawn_x = 0
        spawn_y = self.get_terrain_height(spawn_x) - 3  # Position player above ground
        
        # Save the spawn position
        self.spawn_position = (spawn_x, spawn_y)