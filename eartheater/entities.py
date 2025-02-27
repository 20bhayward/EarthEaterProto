"""
Entity definitions for the game
"""
from typing import Tuple
import math
import random
import pygame

from eartheater.constants import (
    GRAVITY, PLAYER_MOVE_SPEED, PLAYER_ACCELERATION, PLAYER_FRICTION, 
    PLAYER_AIR_CONTROL, PLAYER_JUMP_STRENGTH, PLAYER_JETPACK_STRENGTH,
    PLAYER_JETPACK_MAX_FUEL, PLAYER_JETPACK_REGEN_RATE,
    MaterialType, MATERIAL_HARDNESS
)
from eartheater.physics import PhysicsEngine


class Entity:
    """Base class for all game entities"""
    
    def __init__(self, x: float, y: float):
        """
        Initialize an entity at the given position
        
        Args:
            x: Initial x-coordinate
            y: Initial y-coordinate
        """
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.ax = 0.0  # Acceleration
        self.ay = 0.0
        self.width = 1.0
        self.height = 1.0
        self.facing_right = True
    
    def update(self, physics: PhysicsEngine) -> None:
        """
        Update the entity state
        
        Args:
            physics: Physics engine for collision detection
        """
        pass
    
    def get_position(self) -> Tuple[float, float]:
        """
        Get the entity's current position
        
        Returns:
            Tuple of (x, y) coordinates
        """
        return (self.x, self.y)


class Player(Entity):
    """Player entity controlled by the user"""
    
    def __init__(self, x: float, y: float):
        """
        Initialize the player at the given position
        
        Args:
            x: Initial x-coordinate
            y: Initial y-coordinate
        """
        super().__init__(x, y)
        self.width = 5.0  # Slimmer player width for better navigation
        self.height = 12.0  # Taller player height for better proportions
        self.is_voxel_based = True  # Flag for voxel-based player physics
        self.drill_angle = 0  # Angle of staff-drill in radians
        self.drill_length = 12.0  # Longer staff-drill reach
        self.drill_width = 1.5  # Thinner staff width for more elegant look
        # Store reference to physics engine for particles
        self.physics = None
        
        # Collision improvements
        self.ground_tolerance = 0.4  # Higher tolerance for smoother hill climbing
        self.edge_buffer = 1.5  # Buffer for sliding over edges
        
        # Movement state
        self.is_on_ground = False
        self.is_jumping = False
        self.is_in_liquid = False
        self.liquid_type = MaterialType.AIR
        self.move_left = False
        self.move_right = False
        self.move_up = False
        self.move_down = False
        self.jetpack_active = False
        self.last_safe_position = (x, y)  # Store last known safe position
        
        # Actions
        self.jump_pressed = False
        self.dig_action = False
        self.dig_radius = 2
        self.dig_target_x = 0  # Target X for mouse digging
        self.dig_target_y = 0  # Target Y for mouse digging
        self.dig_all_materials = True
        
        # Jetpack
        self.jetpack_fuel = PLAYER_JETPACK_MAX_FUEL
        self.jetpack_sound_timer = 0
        
        # Animation and visual states
        self.facing_right = True
        self.animation_frame = 0
        self.animation_timer = 0
        self.dig_animation_active = False
        self.dig_animation_timer = 0
        
        # Visual model properties
        self.skin_color = (210, 160, 120)  # Natural skin tone
        self.pants_color = (60, 70, 120)  # Ragged blue pants
        self.staff_color = (120, 80, 40)  # Wooden staff base
        self.drill_tip_color = (220, 220, 240)  # Metallic drill tip
        
        # Particles
        self.trail_particles = []
        self.particle_timer = 0
        
        # Auto-digging
        self.auto_dig_enabled = True
        self.dig_cooldown = 0
        self.dig_cooldown_max = 5  # Frames between automatic digging
        self.last_dig_positions = set()  # Recently dug positions
    
    def update(self, physics: PhysicsEngine, dt: float = 1/60) -> None:
        """
        Update player position and handle physics
        
        Args:
            physics: Physics engine for collision detection
            dt: Delta time (time since last frame in seconds)
        """
        # Reset acceleration
        self.ax = 0
        self.ay = 0
        
        # Store reference to physics engine for particle effects
        self.physics = physics
        
        # Store dt for time-based calculations - ensure it's never zero
        self.dt = max(dt, 0.001)
        
        # Check if player is in liquid
        self.is_in_liquid, self.liquid_type = physics.is_in_liquid(
            self.x, self.y, self.width, self.height
        )
        
        # Handle horizontal movement
        self.ax = 0
        self.ay = 0
        
        # Apply horizontal movement with acceleration (properly scaled by dt)
        if self.move_left:
            if self.is_on_ground:
                self.ax = -PLAYER_ACCELERATION * self.dt
            else:
                # Less control in air
                self.ax = -PLAYER_ACCELERATION * PLAYER_AIR_CONTROL * self.dt
            self.facing_right = False
        
        if self.move_right:
            if self.is_on_ground:
                self.ax = PLAYER_ACCELERATION * self.dt
            else:
                # Less control in air
                self.ax = PLAYER_ACCELERATION * PLAYER_AIR_CONTROL * self.dt
            self.facing_right = True
        
        # Apply friction based on time delta
        if not self.move_left and not self.move_right:
            # More friction on ground than in air
            base_friction = PLAYER_FRICTION if self.is_on_ground else (PLAYER_FRICTION * 0.5)
            # Calculate time-adjusted friction factor (higher dt = more friction applied)
            friction = base_friction ** self.dt
            self.vx *= friction
        
        # Update velocity based on acceleration
        self.vx += self.ax
        
        # Cap horizontal speed
        max_speed = PLAYER_MOVE_SPEED
        if self.is_in_liquid:
            max_speed *= 0.7  # Slower in liquid
        
        if abs(self.vx) > max_speed:
            self.vx = math.copysign(max_speed, self.vx)
        
        # Check if we're on the ground
        self.is_on_ground = physics.check_feet_collision(
            self.x, self.y + self.height, self.width
        )
        
        # Apply gravity scaled by dt for proper physics
        gravity_modifier = 0.3 if self.is_in_liquid else 1.0
        self.ay += GRAVITY * gravity_modifier * self.dt
        
        # Handle jumping
        if self.jump_pressed and self.is_on_ground:
            self.vy = -PLAYER_JUMP_STRENGTH
            self.is_on_ground = False
            self.is_jumping = True
        
        # Handle jetpack
        if self.jetpack_active and self.jetpack_fuel > 0:
            # Apply upward force scaled by dt
            jetpack_force = PLAYER_JETPACK_STRENGTH * self.dt
            
            # Stronger push when in liquid
            if self.is_in_liquid:
                jetpack_force *= 1.5
                
            self.ay -= jetpack_force
            
            # Consume fuel
            self.jetpack_fuel -= 1
            
            # Create jetpack particles
            self.particle_timer += 1
            if self.particle_timer >= 3:  # Reduced particle frequency
                self.create_jetpack_particles()
                self.particle_timer = 0
                
            # Play sound occasionally
            self.jetpack_sound_timer += 1
            if self.jetpack_sound_timer >= 10:
                # Would play sound here
                self.jetpack_sound_timer = 0
        else:
            # Regenerate fuel when not using jetpack
            if self.jetpack_fuel < PLAYER_JETPACK_MAX_FUEL:
                self.jetpack_fuel += PLAYER_JETPACK_REGEN_RATE
                if self.jetpack_fuel > PLAYER_JETPACK_MAX_FUEL:
                    self.jetpack_fuel = PLAYER_JETPACK_MAX_FUEL
        
        # Update vertical velocity
        self.vy += self.ay
        
        # Cap fall speed
        max_fall_speed = 12.0
        if self.is_in_liquid:
            max_fall_speed = 4.0  # Slower falling in liquid
            
        if self.vy > max_fall_speed:
            self.vy = max_fall_speed
        
        # Apply movement with collision detection
        self.apply_movement(physics)
        
        # Disable auto-digging completely to prevent terrain destruction when walking
        # if self.dig_cooldown > 0:
        #     self.dig_cooldown -= 1
        # self.check_auto_dig(physics)
        
        # Handle explicit digging if the action is activated
        if self.dig_action:
            self.perform_dig(physics)
        
        # Update animation frames
        self.update_animation()
        
        # Reset actions
        self.jump_pressed = False
        self.dig_action = False
        
        # Update particle effects
        self.update_particles()
        
        # Clean up remembered dig positions periodically
        if random.random() < 0.01:  # 1% chance per frame
            self.last_dig_positions.clear()
    
    def apply_movement(self, physics: PhysicsEngine) -> None:
        """
        Apply movement with collision detection and improved terrain navigation
        
        Args:
            physics: Physics engine for collision detection
        """
        # Store initial position for safety
        initial_x, initial_y = self.x, self.y
        
        # Apply horizontal movement with sub-pixel precision, scaled by dt
        if abs(self.vx) > 0.001:
            move_dir = math.copysign(1, self.vx)
            # Scale movement by dt
            remaining_move = abs(self.vx) * self.dt
            
            # Move in small steps for smoother collision response
            while remaining_move > 0:
                step = min(0.08, remaining_move)  # Smaller step size for smoother movement
                old_x = self.x
                self.x += move_dir * step
                
                # Check for collision
                if physics.check_collision(self.x, self.y, self.width, self.height):
                    # Try step climbing (move up slightly to handle small bumps)
                    can_step_up = False
                    
                    # Check if we can step up (only when on ground or close to it)
                    step_height = 1.5  # Maximum step height in tiles
                    if self.is_on_ground or self.vy > -0.2:  # Only step up when moving down or on ground
                        # Try to step up
                        old_y = self.y
                        self.y -= step_height  # Move up
                        
                        # If we can move up and forward, we've stepped up
                        if not physics.check_collision(self.x, self.y, self.width, self.height):
                            # Success - we've stepped up
                            can_step_up = True
                            
                            # Now gradually move back down to find the ground
                            ground_found = False
                            for i in range(int(step_height * 10)):
                                self.y += 0.1  # Move down in small increments
                                if physics.check_collision(self.x, self.y, self.width, self.height):
                                    self.y -= 0.1  # Move back up
                                    ground_found = True
                                    break
                            
                            # If we didn't find ground, revert to original position
                            if not ground_found:
                                self.x = old_x
                                self.y = old_y
                                can_step_up = False
                        else:
                            # Can't step up, revert position
                            self.y = old_y
                    
                    # If we couldn't step up, handle wall collision
                    if not can_step_up:
                        # Try to slide along walls by checking diagonal movement
                        if physics.check_collision(self.x, self.y - 0.2, self.width, self.height):
                            # Wall slopes upward - reset position
                            self.x = old_x
                            self.vx *= 0.5  # Reduce horizontal velocity when hitting walls
                        else:
                            # Wall slopes downward - we can move along it
                            self.y -= 0.2  # Move up slightly to slide over small obstacles
                            
                            # If still colliding, revert position
                            if physics.check_collision(self.x, self.y, self.width, self.height):
                                self.x = old_x
                                self.y += 0.2  # Reset y position
                                self.vx *= 0.5  # Reduce horizontal velocity
                            
                    # Update our last safe position if we're on ground
                    if self.is_on_ground and not physics.check_collision(self.x, self.y, self.width, self.height):
                        self.last_safe_position = (self.x, self.y)
                
                remaining_move -= step
        
        # Apply vertical movement with sub-pixel precision, scaled by dt
        if abs(self.vy) > 0.001:
            move_dir = math.copysign(1, self.vy)
            # Scale movement by dt
            remaining_move = abs(self.vy) * self.dt
            
            while remaining_move > 0:
                step = min(0.08, remaining_move)  # Smaller step size for smoother movement
                old_y = self.y
                self.y += move_dir * step
                
                # Check for collision
                if physics.check_collision(self.x, self.y, self.width, self.height):
                    self.y = old_y
                    
                    # If moving down, we've hit the ground
                    if self.vy > 0:
                        self.is_on_ground = True
                        self.is_jumping = False
                        
                        # Update safe position when touching ground
                        self.last_safe_position = (self.x, self.y)
                        
                    # If moving up, we've hit the ceiling
                    self.vy = 0
                    break
                    
                # If falling, check for ledges we can grab onto
                if move_dir > 0 and not self.is_on_ground:
                    # Check for solid blocks near feet that we might be able to step onto
                    feet_y = self.y + self.height
                    ledge_check_distance = 1.0  # Distance to check for ledges
                    
                    # Check if there's a ledge to the left or right
                    left_ledge = physics.world.get_block(int(self.x - ledge_check_distance), int(feet_y)) != MaterialType.AIR
                    right_ledge = physics.world.get_block(int(self.x + self.width + ledge_check_distance), int(feet_y)) != MaterialType.AIR
                    
                    # If we find a ledge and we're moving toward it, try to grab it
                    if (left_ledge and self.vx < 0) or (right_ledge and self.vx > 0):
                        # Reduce falling speed to make it easier to land on edges
                        if self.vy > 1.0:
                            self.vy = max(self.vy * 0.8, 1.0)
                
                remaining_move -= step
                
        # Safety check - if we're fully embedded in solid blocks, reset to last safe position
        if physics.check_collision(self.x, self.y, self.width, self.height):
            collision_density = physics.get_collision_density(self.x, self.y, self.width, self.height)
            
            # If we're deeply embedded (more than 60% of body in solid material)
            if collision_density > 0.6:
                # Reset to last safe position
                self.x, self.y = self.last_safe_position
                self.vx, self.vy = 0, 0
    
    def perform_dig(self, physics: PhysicsEngine) -> None:
        """
        Perform digging action using a drill that extends from the player
        
        Args:
            physics: Physics engine for collision detection
        """
        # Calculate player center
        player_center_x = self.x + self.width / 2
        player_center_y = self.y + self.height / 2
        
        # Calculate drill tip position based on angle and length
        drill_tip_x = player_center_x + math.cos(self.drill_angle) * self.drill_length
        drill_tip_y = player_center_y + math.sin(self.drill_angle) * self.drill_length
        
        # Dig at the drill tip
        dig_x = int(drill_tip_x)
        dig_y = int(drill_tip_y)
        
        # Dig along the drill path with focus at the tip
        steps = int(self.drill_length / 2)  # Fewer steps for performance, focus on the tip
        hit_material = False  # Track if we hit any material
        
        # Start from the tip and work backward - gives priority to the tip
        for i in range(steps):
            # Calculate position along the drill, focusing more on the tip area
            t = (steps - i) / steps  # Start from tip (t=1) and work backward (t→0)
            dist = self.drill_length * (0.5 + t * 0.5)  # Focus more on the last half of the drill
            
            pos_x = int(player_center_x + math.cos(self.drill_angle) * dist)
            pos_y = int(player_center_y + math.sin(self.drill_angle) * dist)
            
            # Check material hardness at this point
            material = physics.world.get_tile(pos_x, pos_y)
            
            # Skip air
            if material == MaterialType.AIR:
                continue
                
            # Get material hardness
            hardness = MATERIAL_HARDNESS.get(material, 1)
            
            # Adjust dig radius based on material hardness
            effective_radius = max(1, self.dig_radius - int(hardness/2))  # Less reduction in radius
            
            # Perform dig action
            physics.dig(pos_x, pos_y, effective_radius, self.dig_all_materials)
            hit_material = True
            
            # Create dig particles - always create particles at the tip for better feedback
            # More particles near the tip, fewer along the shaft
            particle_chance = 0.8 if i < 3 else 0.3  # Higher chance near the tip
            if random.random() < particle_chance:
                self.create_dig_particles(pos_x, pos_y)
                
            # Remember this dig position
            self.last_dig_positions.add((pos_x, pos_y))
        
        # Start dig animation if we hit something
        if hit_material:
            self.dig_animation_active = True
            self.dig_animation_timer = 8  # Longer animation time
        else:
            # Brief animation even when missing, for better feedback
            self.dig_animation_active = True
            self.dig_animation_timer = 3
        
    def check_auto_dig(self, physics: PhysicsEngine) -> None:
        """
        Check if player is colliding with blocks and auto-dig if needed
        
        Args:
            physics: Physics engine for collision detection
        """
        if not self.auto_dig_enabled or self.dig_cooldown > 0:
            return
            
        # Get player bounds
        x1 = int(self.x)
        y1 = int(self.y)
        x2 = int(self.x + self.width)
        y2 = int(self.y + self.height)
        
        # Check if player is colliding with solid blocks
        # Focus on direction of movement
        dig_positions = []
        
        if self.move_left:
            for y in range(y1, y2 + 1):
                if physics.world.get_tile(x1, y) != MaterialType.AIR:
                    dig_positions.append((x1, y))
        elif self.move_right:
            for y in range(y1, y2 + 1):
                if physics.world.get_tile(x2, y) != MaterialType.AIR:
                    dig_positions.append((x2, y))
                    
        if self.move_up:
            for x in range(x1, x2 + 1):
                if physics.world.get_tile(x, y1) != MaterialType.AIR:
                    dig_positions.append((x, y1))
        elif self.move_down:
            for x in range(x1, x2 + 1):
                if physics.world.get_tile(x, y2) != MaterialType.AIR:
                    dig_positions.append((x, y2))
        
        # If we found solid blocks, auto-dig
        if dig_positions:
            for x, y in dig_positions:
                # Skip if recently dug
                if (x, y) in self.last_dig_positions:
                    continue
                    
                # Check material hardness
                material = physics.world.get_tile(x, y)
                hardness = MATERIAL_HARDNESS.get(material, 1)
                
                # Skip if too hard (need explicit digging)
                if hardness > 2:
                    continue
                
                # Dig with smaller radius
                effective_radius = 1
                physics.dig(x, y, effective_radius, destroy_all=False)
                
                # Add minimal particles
                if random.random() < 0.3:
                    self.create_dig_particles(x, y)
                
                # Add to recent positions
                self.last_dig_positions.add((x, y))
            
            # Set cooldown
            self.dig_cooldown = self.dig_cooldown_max
    
    def update_animation(self) -> None:
        """Update animation state"""
        # Update animation timer
        self.animation_timer += 1
        
        # Idle animation is slow
        if abs(self.vx) < 0.1 and not self.is_jumping and not self.jetpack_active:
            if self.animation_timer >= 15:
                self.animation_frame = (self.animation_frame + 1) % 4
                self.animation_timer = 0
        # Movement animation is faster
        elif abs(self.vx) > 0.1:
            if self.animation_timer >= 8:
                self.animation_frame = (self.animation_frame + 1) % 4
                self.animation_timer = 0
        # Jumping animation
        elif self.is_jumping or self.jetpack_active:
            if self.vy < 0:
                self.animation_frame = 4  # Jump up frame
            else:
                self.animation_frame = 5  # Fall down frame
        
        # Update dig animation timer
        if self.dig_animation_active:
            self.dig_animation_timer -= 1
            if self.dig_animation_timer <= 0:
                self.dig_animation_active = False
    
    def create_jetpack_particles(self) -> None:
        """Create jetpack particles - now more optimized with fewer particles"""
        # Particles now primarily handled by the renderer for improved visuals and performance
        # This method now only creates trail particles, not the main flame burst
        particle = {
            'x': self.x + random.uniform(0.3 * self.width, 0.7 * self.width),
            'y': self.y + self.height,
            'vx': random.uniform(-0.1, 0.1),
            'vy': random.uniform(0.1, 0.3),
            'life': random.randint(15, 25),  # Shorter life for performance
            'color': (255, 200, 50, random.randint(120, 200)),  # Semi-transparent
            'size': random.uniform(0.3, 0.5)  # Smaller size
        }
        self.trail_particles.append(particle)
    
    def create_dig_particles(self, x: int, y: int) -> None:
        """
        Create particles for digging effect that match the material being dug
        
        Args:
            x: X-coordinate of dig center
            y: Y-coordinate of dig center
        """
        # Get the material being dug
        material = None
        try:
            from eartheater.constants import MATERIAL_COLORS
            material = self.physics.world.get_tile(x, y)
            
            # Get base particle color from material (default to gray if not found)
            base_color = MATERIAL_COLORS.get(material, (180, 180, 180))
        except:
            # Fallback if for some reason we can't get the material
            base_color = (180, 180, 180)  # Default gray
        
        # Create more particles for a more dramatic effect
        for _ in range(8):
            # For particles, use an angle biased away from the drill angle (more realistic)
            # This makes particles fly away from the drill direction
            base_angle = self.drill_angle + math.pi  # Opposite of drill direction
            spread = 0.8  # Narrower spread for more focused effect
            angle = base_angle + random.uniform(-spread, spread)
            
            # Faster particles for more dynamic effect
            speed = random.uniform(0.4, 1.0)
            
            # Vary the particle color slightly for visual interest
            color_variation = random.randint(-20, 20)
            r = max(0, min(255, base_color[0] + color_variation))
            g = max(0, min(255, base_color[1] + color_variation))
            b = max(0, min(255, base_color[2] + color_variation))
            particle_color = (r, g, b)
            
            # Create particle with longer life and larger size
            particle = {
                'x': x + random.uniform(-0.3, 0.3),
                'y': y + random.uniform(-0.3, 0.3),
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'life': random.randint(20, 35),  # Longer life
                'color': particle_color,
                'size': random.uniform(0.3, 0.6)  # Larger particles
            }
            self.trail_particles.append(particle)
    
    def update_particles(self) -> None:
        """Update particle effects"""
        # Update existing particles
        for particle in self.trail_particles:
            # Apply gravity
            particle['vy'] += 0.01
            
            # Apply movement
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            
            # Reduce lifetime
            particle['life'] -= 1
            
            # Reduce size as it ages
            if particle['life'] < 10:
                particle['size'] *= 0.9
                
            # Fade out alpha if available
            if 'color' in particle and len(particle['color']) > 3:
                alpha = particle['color'][3]
                if alpha > 10:
                    # Create new color tuple with reduced alpha
                    r, g, b, a = particle['color']
                    particle['color'] = (r, g, b, max(0, a - 15))
        
        # Remove dead particles - more aggressively to prevent buildup
        self.trail_particles = [p for p in self.trail_particles if p['life'] > 0 and len(self.trail_particles) < 50]
        
        # Force clear if too many particles
        if len(self.trail_particles) > 100:
            self.trail_particles = self.trail_particles[-50:]  # Keep only newest 50