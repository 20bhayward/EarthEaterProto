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
    WORLD_SEED, CAVE_DENSITY, MATERIAL_LIQUIDITY, WATER_LEVEL
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
        self.player_chunk = (0, 0)
        self.random = random.Random(WORLD_SEED)
        
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
                
                # Generate terrain height using Perlin noise
                terrain_value = noise.pnoise2(
                    world_x * self.terrain_scale, 
                    0,
                    octaves=self.terrain_octaves, 
                    persistence=0.5, 
                    lacunarity=2.0, 
                    repeatx=10000, 
                    repeaty=10000, 
                    base=self.random.randint(0, 1000)
                )
                
                # Map noise value (-1 to 1) to terrain height
                terrain_height = int((terrain_value + 1) * 30) + 60
                
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
                    
                    # Add stone below surface
                    if world_y > terrain_height + 5:
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
                
                # Add water below water level
                if material == MaterialType.AIR and world_y > WATER_LEVEL:
                    material = MaterialType.WATER
                
                # Add lava deep underground in caves
                if material == MaterialType.AIR and world_y > terrain_height + 80:
                    if self.random.random() < 0.2:
                        material = MaterialType.LAVA
                
                chunk.set_tile(local_x, local_y, material)
        
        # Mark the chunk as generated
        chunk.generated = True
        chunk.needs_update = True
    
    def update_active_chunks(self, player_world_x: float, player_world_y: float) -> None:
        """
        Update which chunks are active based on player position
        
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
            
            # Clear the set of active chunks
            self.active_chunks.clear()
            
            # Add chunks within radius to active set
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