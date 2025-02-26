"""
Entity definitions for the game
"""
from typing import Tuple

from eartheater.constants import (
    GRAVITY, PLAYER_MOVE_SPEED, PLAYER_JUMP_STRENGTH, MaterialType
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
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.width = 1.0
        self.height = 1.0
    
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
        self.width = 2.0
        self.height = 3.0
        self.is_on_ground = False
        self.move_left = False
        self.move_right = False
        self.jump = False
        self.dig_action = False
        self.dig_radius = 2
    
    def update(self, physics: PhysicsEngine) -> None:
        """
        Update player position and handle physics
        
        Args:
            physics: Physics engine for collision detection
        """
        # Apply horizontal movement based on input
        self.vx = 0
        if self.move_left:
            self.vx = -PLAYER_MOVE_SPEED
        if self.move_right:
            self.vx = PLAYER_MOVE_SPEED
        
        # Apply gravity
        self.vy += GRAVITY
        
        # Check if we're on the ground
        was_on_ground = self.is_on_ground
        self.is_on_ground = physics.check_collision(
            self.x, self.y + 0.1, self.width, self.height
        )
        
        # Handle jumping
        if self.jump and self.is_on_ground:
            self.vy = -PLAYER_JUMP_STRENGTH
            self.is_on_ground = False
        
        # Reset jump input after it's processed
        self.jump = False
        
        # Apply vertical movement
        old_y = self.y
        self.y += self.vy
        
        # Check for vertical collision
        if physics.check_collision(self.x, self.y, self.width, self.height):
            # Move back and stop vertical momentum
            self.y = old_y
            if self.vy > 0:
                self.is_on_ground = True
            self.vy = 0
        
        # Apply horizontal movement
        old_x = self.x
        self.x += self.vx
        
        # Check for horizontal collision
        if physics.check_collision(self.x, self.y, self.width, self.height):
            # Move back and stop horizontal momentum
            self.x = old_x
            self.vx = 0
            
        # Handle digging if the action is activated
        if self.dig_action:
            # Get the position in front of the player
            dig_x = int(self.x + self.width / 2)
            dig_y = int(self.y + self.height / 2)
            physics.dig(dig_x, dig_y, self.dig_radius)
            
        # Reset dig action after it's processed
        self.dig_action = False