"""
World management module for EarthEater
"""
import numpy as np
from typing import Dict, Tuple, Optional
import random

from eartheater.constants import (
    MaterialType, CHUNK_SIZE, WORLD_WIDTH, WORLD_HEIGHT,
    WORLD_WIDTH_CHUNKS, WORLD_HEIGHT_CHUNKS
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
    
    def set_tile(self, x: int, y: int, material: MaterialType) -> None:
        """
        Set a tile in this chunk to the specified material
        
        Args:
            x: Local x-coordinate within chunk (0 to CHUNK_SIZE-1)
            y: Local y-coordinate within chunk (0 to CHUNK_SIZE-1)
            material: Material type to set
        """
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
        return self.tiles[y, x]


class World:
    """Manages the game world"""
    
    def __init__(self):
        """Initialize an empty world"""
        self.chunks: Dict[Tuple[int, int], Chunk] = {}
        self.generate_world()
    
    def generate_world(self) -> None:
        """Generate a basic world with terrain"""
        # Create all chunks
        for cx in range(WORLD_WIDTH_CHUNKS):
            for cy in range(WORLD_HEIGHT_CHUNKS):
                self.chunks[(cx, cy)] = Chunk(cx, cy)
        
        # Generate simple terrain
        ground_height = WORLD_HEIGHT // 2
        
        for x in range(WORLD_WIDTH):
            # Vary the ground height slightly
            height_variation = random.randint(-2, 2)
            current_ground = ground_height + height_variation
            
            # Generate ground column
            for y in range(WORLD_HEIGHT):
                # Calculate which chunk and local coordinates this belongs to
                cx, local_x = divmod(x, CHUNK_SIZE)
                cy, local_y = divmod(y, CHUNK_SIZE)
                
                chunk = self.chunks.get((cx, cy))
                if chunk is None:
                    continue
                
                if y > current_ground:
                    # Underground
                    if y > current_ground + 5:
                        chunk.set_tile(local_x, local_y, MaterialType.STONE)
                    else:
                        chunk.set_tile(local_x, local_y, MaterialType.DIRT)
                    
                    # Add some sand pockets
                    if random.random() < 0.05 and y > current_ground + 3:
                        chunk.set_tile(local_x, local_y, MaterialType.SAND)
    
    def get_chunk(self, cx: int, cy: int) -> Optional[Chunk]:
        """
        Get the chunk at the specified chunk coordinates
        
        Args:
            cx: Chunk x-coordinate
            cy: Chunk y-coordinate
            
        Returns:
            The chunk at the specified position, or None if out of bounds
        """
        return self.chunks.get((cx, cy))
    
    def get_tile(self, x: int, y: int) -> MaterialType:
        """
        Get the material at the specified world position
        
        Args:
            x: World x-coordinate
            y: World y-coordinate
            
        Returns:
            The material type at the specified position, AIR if out of bounds
        """
        if not (0 <= x < WORLD_WIDTH and 0 <= y < WORLD_HEIGHT):
            return MaterialType.AIR
        
        cx, local_x = divmod(x, CHUNK_SIZE)
        cy, local_y = divmod(y, CHUNK_SIZE)
        
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
        if not (0 <= x < WORLD_WIDTH and 0 <= y < WORLD_HEIGHT):
            return
        
        cx, local_x = divmod(x, CHUNK_SIZE)
        cy, local_y = divmod(y, CHUNK_SIZE)
        
        chunk = self.get_chunk(cx, cy)
        if chunk is not None:
            chunk.set_tile(local_x, local_y, material)
    
    def get_active_chunks(self) -> list:
        """Get a list of all chunks that need to be processed/rendered"""
        return list(self.chunks.values())