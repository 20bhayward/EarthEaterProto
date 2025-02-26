"""
Physics simulation for EarthEater
"""
from typing import List, Tuple
import random

from eartheater.constants import (
    MaterialType, GRAVITY, MATERIAL_FALLS, WORLD_WIDTH, WORLD_HEIGHT
)
from eartheater.world import World


class PhysicsEngine:
    """Simulates physical interactions in the world"""
    
    def __init__(self, world: World):
        """
        Initialize physics engine
        
        Args:
            world: The game world to simulate physics for
        """
        self.world = world
        self.pending_updates: List[Tuple[int, int, MaterialType]] = []
    
    def update(self) -> None:
        """Update physics for one step"""
        # Clear pending updates from previous step
        self.pending_updates = []
        
        # Process falling materials
        self._process_falling_materials()
        
        # Apply all queued updates at once to avoid cascade effects
        for x, y, material in self.pending_updates:
            self.world.set_tile(x, y, material)
    
    def _process_falling_materials(self) -> None:
        """Process all materials that are affected by gravity"""
        # Process world in random order to avoid directional bias
        positions = [(x, y) for x in range(WORLD_WIDTH) for y in range(WORLD_HEIGHT)]
        random.shuffle(positions)
        
        for x, y in positions:
            material = self.world.get_tile(x, y)
            
            # Skip if this material doesn't fall
            if not MATERIAL_FALLS.get(material, False):
                continue
            
            # Check if there's air below
            below = self.world.get_tile(x, y + 1)
            if below == MaterialType.AIR:
                # Move down
                self.pending_updates.append((x, y, MaterialType.AIR))
                self.pending_updates.append((x, y + 1, material))
            else:
                # Try to slide down diagonally
                left_below = self.world.get_tile(x - 1, y + 1)
                right_below = self.world.get_tile(x + 1, y + 1)
                
                if left_below == MaterialType.AIR and self.world.get_tile(x - 1, y) == MaterialType.AIR:
                    # Slide down-left
                    self.pending_updates.append((x, y, MaterialType.AIR))
                    self.pending_updates.append((x - 1, y + 1, material))
                elif right_below == MaterialType.AIR and self.world.get_tile(x + 1, y) == MaterialType.AIR:
                    # Slide down-right
                    self.pending_updates.append((x, y, MaterialType.AIR))
                    self.pending_updates.append((x + 1, y + 1, material))
    
    def check_collision(self, x: int, y: int, width: int, height: int) -> bool:
        """
        Check if an entity collides with solid terrain
        
        Args:
            x: X-coordinate of entity's top-left corner
            y: Y-coordinate of entity's top-left corner
            width: Width of entity in tiles
            height: Height of entity in tiles
            
        Returns:
            True if there is a collision, False otherwise
        """
        for check_x in range(int(x), int(x + width)):
            for check_y in range(int(y), int(y + height)):
                tile = self.world.get_tile(check_x, check_y)
                if tile != MaterialType.AIR:
                    return True
        return False
    
    def dig(self, x: int, y: int, radius: int = 1) -> None:
        """
        Dig a hole at the specified position
        
        Args:
            x: X-coordinate
            y: Y-coordinate
            radius: Radius of the hole in tiles
        """
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                # Skip corners for a more circular shape
                if dx*dx + dy*dy > radius*radius:
                    continue
                    
                self.world.set_tile(x + dx, y + dy, MaterialType.AIR)