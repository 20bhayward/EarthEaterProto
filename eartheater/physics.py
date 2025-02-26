"""
Physics simulation for EarthEater
"""
from typing import List, Tuple, Set
import random
import math

from eartheater.constants import (
    MaterialType, GRAVITY, MATERIAL_FALLS, MATERIAL_LIQUIDITY, CHUNK_SIZE
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
        self.processed_positions: Set[Tuple[int, int]] = set()
        self.update_radius = 64  # Process tiles within this radius of player
        self.frame_counter = 0
    
    def update(self, player_x: float, player_y: float) -> None:
        """
        Update physics for one step
        
        Args:
            player_x: Player x-coordinate
            player_y: Player y-coordinate
        """
        # Clear pending updates and processed positions from previous step
        self.pending_updates = []
        self.processed_positions = set()
        
        # Increment frame counter for staggering updates
        self.frame_counter += 1
        
        # Get active chunks centered around player for processing
        active_chunks = self.world.get_active_chunks()
        
        # Process falling materials within active chunks
        # Only process a subset of positions each frame for performance
        for chunk in active_chunks:
            chunk_world_x = chunk.x * CHUNK_SIZE
            chunk_world_y = chunk.y * CHUNK_SIZE
            
            # Skip chunks that are too far from player
            chunk_center_x = chunk_world_x + CHUNK_SIZE / 2
            chunk_center_y = chunk_world_y + CHUNK_SIZE / 2
            dist_to_player = math.sqrt((chunk_center_x - player_x)**2 + (chunk_center_y - player_y)**2)
            
            if dist_to_player > self.update_radius:
                continue
                
            # Create list of positions in this chunk
            positions = []
            for local_y in range(CHUNK_SIZE):
                for local_x in range(CHUNK_SIZE):
                    # Stagger updates for performance (only process 1/4 of world each frame)
                    if (local_x + local_y + self.frame_counter) % 4 != 0:
                        continue
                        
                    world_x = chunk_world_x + local_x
                    world_y = chunk_world_y + local_y
                    
                    # Skip positions too far from player
                    dist_to_player = math.sqrt((world_x - player_x)**2 + (world_y - player_y)**2)
                    if dist_to_player > self.update_radius:
                        continue
                        
                    positions.append((world_x, world_y))
            
            # Randomize order to avoid directional bias
            random.shuffle(positions)
            
            # Process materials
            self._process_materials(positions)
        
        # Apply all queued updates at once to avoid cascade effects
        for x, y, material in self.pending_updates:
            self.world.set_tile(x, y, material)
    
    def _process_materials(self, positions: List[Tuple[int, int]]) -> None:
        """
        Process materials at the given positions
        
        Args:
            positions: List of (x, y) coordinates to process
        """
        for x, y in positions:
            # Skip already processed positions
            if (x, y) in self.processed_positions:
                continue
                
            material = self.world.get_tile(x, y)
            
            # Skip if this material doesn't fall or flow
            if not MATERIAL_FALLS.get(material, False):
                continue
                
            # Mark this position as processed
            self.processed_positions.add((x, y))
            
            # Get material liquidity (0 = solid, 1 = very liquid)
            liquidity = MATERIAL_LIQUIDITY.get(material, 0)
            
            # Check if there's air below
            below = self.world.get_tile(x, y + 1)
            
            # For liquid materials, they can displace AIR and WATER (if they're lava)
            can_displace_below = (below == MaterialType.AIR) or \
                                (liquidity > 0.5 and material == MaterialType.LAVA and below == MaterialType.WATER)
            
            if can_displace_below:
                # Move down
                self.pending_updates.append((x, y, MaterialType.AIR))
                self.pending_updates.append((x, y + 1, material))
                # Mark destination as processed
                self.processed_positions.add((x, y + 1))
            else:
                # Try to spread horizontally based on liquidity
                if liquidity > 0:
                    # Choose random direction first (more realistic)
                    directions = [(0, -1), (1, 0), (-1, 0)]  # Up, right, left
                    random.shuffle(directions)
                    
                    for dx, dy in directions:
                        flow_x, flow_y = x + dx, y + dy
                        
                        # Check if this space is air
                        if self.world.get_tile(flow_x, flow_y) == MaterialType.AIR:
                            # For very liquid materials, they can flow up a bit
                            if dy < 0 and liquidity < 0.7:
                                continue
                                
                            self.pending_updates.append((x, y, MaterialType.AIR))
                            self.pending_updates.append((flow_x, flow_y, material))
                            # Mark destination as processed
                            self.processed_positions.add((flow_x, flow_y))
                            break
                
                # If couldn't move, try to slide down diagonally
                if (x, y) not in self.processed_positions or self.world.get_tile(x, y) == material:
                    # Try both directions with randomized order
                    directions = [(-1, 1), (1, 1)]  # Down-left, down-right
                    random.shuffle(directions)
                    
                    for dx, dy in directions:
                        slide_x, slide_y = x + dx, y + dy
                        
                        # Check if diagonal and intermediate positions are air
                        if (self.world.get_tile(slide_x, slide_y) == MaterialType.AIR and
                            self.world.get_tile(x + dx, y) == MaterialType.AIR):
                            self.pending_updates.append((x, y, MaterialType.AIR))
                            self.pending_updates.append((slide_x, slide_y, material))
                            # Mark destination as processed
                            self.processed_positions.add((slide_x, slide_y))
                            break
    
    def check_collision(self, x: float, y: float, width: float, height: float) -> bool:
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
        # Get the integer bounds with a small buffer for better collision detection
        start_x = int(x)
        start_y = int(y)
        end_x = int(x + width)
        end_y = int(y + height)
        
        # Check all tiles overlapping with the entity
        for check_x in range(start_x, end_x + 1):
            for check_y in range(start_y, end_y + 1):
                tile = self.world.get_tile(check_x, check_y)
                
                # Air and water don't cause collisions (can swim through water)
                if tile != MaterialType.AIR and tile != MaterialType.WATER:
                    # Check if this tile actually overlaps with the entity bounding box
                    if (check_x < x + width and
                        check_x + 1 > x and
                        check_y < y + height and
                        check_y + 1 > y):
                        return True
        return False
    
    def check_feet_collision(self, x: float, y: float, width: float) -> bool:
        """
        Check if an entity's feet are touching solid ground
        
        Args:
            x: X-coordinate of entity's top-left corner
            y: Y-coordinate of entity's bottom edge
            width: Width of entity in tiles
            
        Returns:
            True if the entity's feet are on solid ground, False otherwise
        """
        # Check a small strip below the entity's feet
        feet_y = y + 0.1  # Just below feet
        
        start_x = int(x)
        end_x = int(x + width)
        
        for check_x in range(start_x, end_x + 1):
            tile = self.world.get_tile(check_x, int(feet_y))
            # Air and water don't provide ground support
            if tile != MaterialType.AIR and tile != MaterialType.WATER:
                return True
        return False
    
    def is_in_liquid(self, x: float, y: float, width: float, height: float) -> Tuple[bool, MaterialType]:
        """
        Check if an entity is in a liquid
        
        Args:
            x: X-coordinate of entity's top-left corner
            y: Y-coordinate of entity's top-left corner
            width: Width of entity in tiles
            height: Height of entity in tiles
            
        Returns:
            Tuple of (is in liquid, liquid type)
        """
        # Get the integer bounds
        start_x = int(x)
        start_y = int(y)
        end_x = int(x + width)
        end_y = int(y + height)
        
        # Count liquid tiles overlapping with entity
        liquid_count = 0
        liquid_tiles = []
        total_tiles = (end_x - start_x + 1) * (end_y - start_y + 1)
        
        for check_x in range(start_x, end_x + 1):
            for check_y in range(start_y, end_y + 1):
                tile = self.world.get_tile(check_x, check_y)
                
                if tile == MaterialType.WATER or tile == MaterialType.LAVA:
                    liquid_count += 1
                    liquid_tiles.append(tile)
        
        # If more than half of the entity is in liquid, consider it submerged
        if liquid_count > total_tiles / 2:
            # Determine dominant liquid type
            water_count = liquid_tiles.count(MaterialType.WATER)
            lava_count = liquid_tiles.count(MaterialType.LAVA)
            
            if lava_count > water_count:
                return True, MaterialType.LAVA
            else:
                return True, MaterialType.WATER
        
        return False, MaterialType.AIR
    
    def dig(self, x: int, y: int, radius: int = 2, destroy_all: bool = True) -> None:
        """
        Dig a hole at the specified position
        
        Args:
            x: X-coordinate
            y: Y-coordinate
            radius: Radius of the hole in tiles
            destroy_all: If True, destroy all material types, otherwise only dirt and sand
        """
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                # Get distance from center (circular shape)
                distance = math.sqrt(dx*dx + dy*dy)
                
                # Skip tiles outside the radius
                if distance > radius:
                    continue
                
                # Calculate target position
                target_x = x + dx
                target_y = y + dy
                
                # Get current material
                material = self.world.get_tile(target_x, target_y)
                
                # Skip air tiles
                if material == MaterialType.AIR:
                    continue
                
                # If not destroy_all, only remove certain materials
                if not destroy_all and material in [MaterialType.STONE, MaterialType.LAVA]:
                    continue
                
                # Destroy tile
                self.world.set_tile(target_x, target_y, MaterialType.AIR)