"""
Physics simulation for EarthEater
"""
from typing import List, Tuple, Set
import random
import math

from eartheater.constants import (
    MaterialType, BlockType, GRAVITY, MATERIAL_FALLS, MATERIAL_LIQUIDITY, CHUNK_SIZE,
    PHYSICS_UPDATE_FREQUENCY
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
        Only processes physics in chunks near the player and prioritizes interactive materials
        
        Args:
            player_x: Player x-coordinate
            player_y: Player y-coordinate
        """
        # Clear pending updates and processed positions from previous step
        self.pending_updates = []
        self.processed_positions = set()
        
        # Increment frame counter for staggering updates
        self.frame_counter += 1
        
        # Get chunks that need physics simulation (smaller radius)
        physics_chunks = self.world.get_chunks_in_radius(player_x, player_y, self.update_radius // CHUNK_SIZE)
        
        # First pass: process interactive materials near player (sand, water, etc)
        player_int_x, player_int_y = int(player_x), int(player_y)
        interactive_positions = []
        
        # Define a much smaller radius for interactive materials
        interactive_radius = min(15, self.update_radius // 3)
        interactive_radius_sq = interactive_radius * interactive_radius
        
        # Pre-allocate arrays to reduce memory allocations in tight loops
        dx_values = list(range(-interactive_radius, interactive_radius + 1))
        dy_values = list(range(-interactive_radius, interactive_radius + 1))
        
        # Collect positions with interactive materials near player
        for dy in dy_values:
            for dx in dx_values:
                # Skip if too far - use squared distance comparison to avoid sqrt
                dist_sq = dx*dx + dy*dy
                if dist_sq > interactive_radius_sq:
                    continue
                    
                world_x = player_int_x + dx
                world_y = player_int_y + dy
                
                # Check if this is an interactive material (prioritize liquids)
                material = self.world.get_block(world_x, world_y)
                
                # Fast path using direct boolean lookup instead of dictionary get
                if material in (MaterialType.WATER, MaterialType.LAVA, MaterialType.SAND_LIGHT, 
                              MaterialType.SAND_DARK, MaterialType.GRAVEL_LIGHT, MaterialType.GRAVEL_DARK):
                    interactive_positions.append((world_x, world_y))
        
        # Process interactive materials with high priority - limit the number for performance
        if interactive_positions:
            # Process maximum of 200 interactive materials per frame
            if len(interactive_positions) > 200:
                random.shuffle(interactive_positions)
                interactive_positions = interactive_positions[:200]
            else:
                random.shuffle(interactive_positions)
                
            self._process_materials(interactive_positions)
        
        # Second pass: process normal physics in nearby chunks with staggering
        for chunk in physics_chunks:
            chunk_world_x = chunk.x * CHUNK_SIZE
            chunk_world_y = chunk.y * CHUNK_SIZE
            
            # Skip chunks that are too far from player (using squared distance)
            chunk_center_x = chunk_world_x + CHUNK_SIZE / 2
            chunk_center_y = chunk_world_y + CHUNK_SIZE / 2
            dx = chunk_center_x - player_x
            dy = chunk_center_y - player_y
            dist_sq = dx*dx + dy*dy
            
            if dist_sq > self.update_radius * self.update_radius:
                continue
                
            # Extremely aggressive staggering for better performance
            # Only process 1/16 of positions in each chunk per frame
            # Process different parts of the chunk each frame using frame counter
            positions = []
            
            # Compute positions in this chunk that need processing this frame
            # We'll use a grid pattern based on frame counter
            grid_size = 4  # 4x4 grid = 16 cells
            grid_x = self.frame_counter % grid_size
            grid_y = (self.frame_counter // grid_size) % grid_size
            
            # Process only grid cells that match our current position in the pattern
            for local_y in range(grid_y, CHUNK_SIZE, grid_size):
                for local_x in range(grid_x, CHUNK_SIZE, grid_size):
                    world_x = chunk_world_x + local_x
                    world_y = chunk_world_y + local_y
                    
                    # Skip positions already processed as interactive or outside update radius
                    if (world_x, world_y) in self.processed_positions:
                        continue
                    
                    # Only process positions with materials that can move
                    material = self.world.get_block(world_x, world_y)
                    if not MATERIAL_FALLS.get(material, False):
                        continue
                        
                    positions.append((world_x, world_y))
            
            # Only process a limited number of positions per chunk for performance
            if positions:
                # Cap at 64 positions per chunk per frame
                if len(positions) > 64:
                    random.shuffle(positions)
                    positions = positions[:64]
                    
                # Process materials without additional shuffling (positions are already semi-random)
                self._process_materials(positions)
        
        # Apply all queued updates at once to avoid cascade effects
        for x, y, material in self.pending_updates:
            self.world.set_block(x, y, material)
    
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
                
            material = self.world.get_block(x, y)
            
            # Skip if this material doesn't fall or flow
            if not MATERIAL_FALLS.get(material, False):
                continue
                
            # Mark this position as processed
            self.processed_positions.add((x, y))
            
            # Get material liquidity (0 = solid, 1 = very liquid)
            liquidity = MATERIAL_LIQUIDITY.get(material, 0)
            
            # Check if there's air below
            below = self.world.get_block(x, y + 1)
            
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
                # Try to spread horizontally based on liquidity - fix for water overlap issue
                if liquidity > 0:
                    # Special case for water: don't allow it to stack horizontally
                    # This prevents water from building up unrealistically
                    if material == MaterialType.WATER:
                        # Limit water horizontal spreading to prevent clustering
                        water_left = self.world.get_block(x - 1, y) == MaterialType.WATER
                        water_right = self.world.get_block(x + 1, y) == MaterialType.WATER
                        water_count = sum([water_left, water_right])
                        
                        # If there's already water on both sides, don't try to flow sideways
                        if water_count >= 2:
                            continue
                    
                    # Choose random direction first (more realistic)
                    directions = [(0, -1), (1, 0), (-1, 0)]  # Up, right, left
                    random.shuffle(directions)
                    
                    flow_success = False
                    for dx, dy in directions:
                        flow_x, flow_y = x + dx, y + dy
                        
                        # Check if destination is out of bounds
                        if flow_x < 0 or flow_y < 0:
                            continue
                            
                        # Check if this space is air
                        target_material = self.world.get_block(flow_x, flow_y)
                        if target_material == MaterialType.AIR:
                            # For very liquid materials, they can flow up a bit
                            if dy < 0 and liquidity < 0.7:
                                continue
                                
                            # Water shouldn't displace existing water (prevents overlap)
                            if material == MaterialType.WATER and target_material == MaterialType.WATER:
                                continue
                                
                            self.pending_updates.append((x, y, MaterialType.AIR))
                            self.pending_updates.append((flow_x, flow_y, material))
                            # Mark destination as processed
                            self.processed_positions.add((flow_x, flow_y))
                            flow_success = True
                            break
                    
                    # If flowing succeeded, don't try diagonal movement
                    if flow_success:
                        continue
                
                # If couldn't move horizontally, try to slide down diagonally
                if (x, y) not in self.processed_positions or self.world.get_block(x, y) == material:
                    # Try both directions with randomized order
                    directions = [(-1, 1), (1, 1)]  # Down-left, down-right
                    random.shuffle(directions)
                    
                    for dx, dy in directions:
                        slide_x, slide_y = x + dx, y + dy
                        
                        # Check if diagonal and intermediate positions are air
                        if (self.world.get_block(slide_x, slide_y) == MaterialType.AIR and
                            self.world.get_block(x + dx, y) == MaterialType.AIR):
                            self.pending_updates.append((x, y, MaterialType.AIR))
                            self.pending_updates.append((slide_x, slide_y, material))
                            # Mark destination as processed
                            self.processed_positions.add((slide_x, slide_y))
                            break
    
    def check_collision(self, x: float, y: float, width: float, height: float) -> bool:
        """
        Check if an entity collides with solid terrain.
        Uses a threshold approach to allow small numbers of voxels to not block the player.
        
        Args:
            x: X-coordinate of entity's top-left corner
            y: Y-coordinate of entity's top-left corner
            width: Width of entity in tiles
            height: Height of entity in tiles
            
        Returns:
            True if there is a collision, False otherwise
        """
        # Get the integer bounds
        start_x = int(x)
        start_y = int(y)
        end_x = int(x + width)
        end_y = int(y + height)
        
        # Count solid tiles
        solid_count = 0
        total_points = 0
        
        # Sample a grid of points within entity's bounds
        sample_step = 2  # Check every few voxels for performance
        collision_threshold = 0.2  # Only block if 20% or more of voxels are solid
        
        for check_x in range(start_x, end_x + 1, sample_step):
            for check_y in range(start_y, end_y + 1, sample_step):
                tile = self.world.get_block(check_x, check_y)
                total_points += 1
                
                # Air and water don't cause collisions
                # Check by specific material to avoid issues with new material types
                if (tile == MaterialType.AIR or 
                    tile == MaterialType.WATER or 
                    tile == MaterialType.VOID):
                    continue
                    
                # All other materials cause collisions
                solid_count += 1
        
        # Prevent division by zero
        if total_points == 0:
            return False
            
        # Calculate solid density and check against threshold
        solid_density = solid_count / total_points
        return solid_density >= collision_threshold
    
    def check_feet_collision(self, x: float, y: float, width: float) -> bool:
        """
        Check if an entity's feet are touching solid ground.
        Uses a threshold approach to require a minimum amount of solid ground.
        
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
        
        # Count solid tiles
        solid_count = 0
        total_checked = 0
        
        # Sample points along entity's width
        sample_step = 2  # Check every few voxels
        ground_threshold = 0.3  # Need at least 30% solid ground beneath feet
        
        for check_x in range(start_x, end_x + 1, sample_step):
            total_checked += 1
            tile = self.world.get_block(check_x, int(feet_y))
            
            # Air, water, and void don't provide ground support
            # Explicitly check for non-ground materials to avoid issues with new material types
            if (tile == MaterialType.AIR or 
                tile == MaterialType.WATER or 
                tile == MaterialType.VOID):
                continue
                
            # All other materials count as ground
            solid_count += 1
        
        # Prevent division by zero
        if total_checked == 0:
            return False
            
        # Calculate ground density and check against threshold
        ground_density = solid_count / total_checked
        return ground_density >= ground_threshold
    
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
        
        # Ensure total_tiles is at least 1 to avoid division by zero
        total_tiles = max(1, total_tiles)
        
        for check_x in range(start_x, end_x + 1):
            for check_y in range(start_y, end_y + 1):
                tile = self.world.get_block(check_x, check_y)
                
                # Only these specific materials count as liquids
                # This ensures safety against new material types
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
        Now supports leaving background blocks intact when digging
        
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
                
                # Get current material in foreground
                material = self.world.get_block(target_x, target_y)
                
                # Skip air tiles
                if material == MaterialType.AIR:
                    continue
                
                # If not destroy_all, only remove certain materials
                if not destroy_all:
                    # Skip harder materials that need a stronger drill
                    if material in [
                        MaterialType.STONE_LIGHT, MaterialType.STONE_MEDIUM, MaterialType.STONE_DARK,
                        MaterialType.DEEP_STONE_LIGHT, MaterialType.DEEP_STONE_MEDIUM, MaterialType.DEEP_STONE_DARK,
                        MaterialType.OBSIDIAN, MaterialType.LAVA
                    ]:
                        continue
                
                # Only destroy foreground - leave background intact for caves
                self.world.set_block(target_x, target_y, MaterialType.AIR, BlockType.FOREGROUND)