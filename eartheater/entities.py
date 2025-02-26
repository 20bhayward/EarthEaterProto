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
        self.width = 1.5  # Smaller player for better navigation
        self.height = 2.5
        
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
        
        # Actions
        self.jump_pressed = False
        self.dig_action = False
        self.dig_radius = 2
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
        
        # Trail particles
        self.trail_particles = []
        self.particle_timer = 0
        
        # Auto-digging
        self.auto_dig_enabled = True
        self.dig_cooldown = 0
        self.dig_cooldown_max = 5  # Frames between automatic digging
        self.last_dig_positions = set()  # Recently dug positions
    
    def update(self, physics: PhysicsEngine) -> None:
        """
        Update player position and handle physics
        
        Args:
            physics: Physics engine for collision detection
        """
        # Check if player is in liquid
        self.is_in_liquid, self.liquid_type = physics.is_in_liquid(
            self.x, self.y, self.width, self.height
        )
        
        # Reset acceleration
        self.ax = 0
        self.ay = 0
        
        # Apply horizontal movement with acceleration
        if self.move_left:
            if self.is_on_ground:
                self.ax = -PLAYER_ACCELERATION
            else:
                # Less control in air
                self.ax = -PLAYER_ACCELERATION * PLAYER_AIR_CONTROL
            self.facing_right = False
        
        if self.move_right:
            if self.is_on_ground:
                self.ax = PLAYER_ACCELERATION
            else:
                # Less control in air
                self.ax = PLAYER_ACCELERATION * PLAYER_AIR_CONTROL
            self.facing_right = True
        
        # Apply friction
        if not self.move_left and not self.move_right:
            # More friction on ground than in air
            friction = PLAYER_FRICTION if self.is_on_ground else (PLAYER_FRICTION * 0.5)
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
        
        # Apply gravity (reduced in liquid)
        gravity_modifier = 0.3 if self.is_in_liquid else 1.0
        self.ay += GRAVITY * gravity_modifier
        
        # Handle jumping
        if self.jump_pressed and self.is_on_ground:
            self.vy = -PLAYER_JUMP_STRENGTH
            self.is_on_ground = False
            self.is_jumping = True
        
        # Handle jetpack
        if self.jetpack_active and self.jetpack_fuel > 0:
            # Apply upward force
            jetpack_force = PLAYER_JETPACK_STRENGTH
            
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
        
        # Handle auto-digging (when moving into blocks)
        if self.dig_cooldown > 0:
            self.dig_cooldown -= 1
        self.check_auto_dig(physics)
        
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
        Apply movement with collision detection
        
        Args:
            physics: Physics engine for collision detection
        """
        # Apply horizontal movement with sub-pixel precision
        if abs(self.vx) > 0.001:
            move_dir = math.copysign(1, self.vx)
            remaining_move = abs(self.vx)
            
            # Move in small steps to prevent getting stuck
            while remaining_move > 0:
                step = min(0.1, remaining_move)
                old_x = self.x
                self.x += move_dir * step
                
                # Check for collision
                if physics.check_collision(self.x, self.y, self.width, self.height):
                    self.x = old_x
                    self.vx = 0
                    break
                
                remaining_move -= step
        
        # Apply vertical movement with sub-pixel precision
        if abs(self.vy) > 0.001:
            move_dir = math.copysign(1, self.vy)
            remaining_move = abs(self.vy)
            
            while remaining_move > 0:
                step = min(0.1, remaining_move)
                old_y = self.y
                self.y += move_dir * step
                
                # Check for collision
                if physics.check_collision(self.x, self.y, self.width, self.height):
                    self.y = old_y
                    
                    # If moving down, we've hit the ground
                    if self.vy > 0:
                        self.is_on_ground = True
                        self.is_jumping = False
                        
                    # If moving up, we've hit the ceiling
                    self.vy = 0
                    break
                
                remaining_move -= step
    
    def perform_dig(self, physics: PhysicsEngine) -> None:
        """
        Perform digging action
        
        Args:
            physics: Physics engine for collision detection
        """
        # Get the position in front of the player (or where they're pointing)
        dig_x = int(self.x + self.width / 2)
        dig_y = int(self.y + self.height / 2)
        
        # Adjust position based on movement
        if self.move_up:
            dig_y -= 3
        elif self.move_down:
            dig_y += 3
        
        if self.move_left:
            dig_x -= 3
        elif self.move_right:
            dig_x += 3
        
        # Check material hardness at the dig location
        material = physics.world.get_tile(dig_x, dig_y)
        hardness = MATERIAL_HARDNESS.get(material, 1)
        
        # Adjust dig radius based on material hardness
        effective_radius = max(1, self.dig_radius - int(hardness))
        
        # Perform dig action
        physics.dig(dig_x, dig_y, effective_radius, self.dig_all_materials)
        
        # Start dig animation
        self.dig_animation_active = True
        self.dig_animation_timer = 10  # Animation frames
        
        # Create dig particles (fewer particles for better performance)
        for _ in range(5):
            self.create_dig_particles(dig_x, dig_y)
            
        # Remember this dig position
        self.last_dig_positions.add((dig_x, dig_y))
        
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
        """Create jetpack particles"""
        # Add particles beneath the player
        for _ in range(2):
            particle = {
                'x': self.x + random.uniform(0, self.width),
                'y': self.y + self.height,
                'vx': random.uniform(-0.2, 0.2),
                'vy': random.uniform(0.2, 0.5),
                'life': random.randint(20, 30),
                'color': (255, 200, 50),  # Yellow flame
                'size': random.uniform(0.3, 0.6)
            }
            self.trail_particles.append(particle)
    
    def create_dig_particles(self, x: int, y: int) -> None:
        """
        Create particles for digging effect
        
        Args:
            x: X-coordinate of dig center
            y: Y-coordinate of dig center
        """
        for _ in range(5):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.2, 0.8)
            
            particle = {
                'x': x + random.uniform(-0.5, 0.5),
                'y': y + random.uniform(-0.5, 0.5),
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed - 0.2,  # Slight upward bias
                'life': random.randint(15, 30),
                'color': (180, 180, 180),  # Gray dust
                'size': random.uniform(0.2, 0.4)
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
        
        # Remove dead particles
        self.trail_particles = [p for p in self.trail_particles if p['life'] > 0]