"""
Main game module for EarthEater
"""
import pygame
import sys

from eartheater.constants import (
    FPS, PHYSICS_STEPS_PER_FRAME, WORLD_WIDTH, WORLD_HEIGHT,
    MaterialType
)
from eartheater.world import World
from eartheater.physics import PhysicsEngine
from eartheater.entities import Player
from eartheater.render import Renderer


class Game:
    """Main game class"""
    
    def __init__(self):
        """Initialize the game"""
        self.running = False
        self.world = World()
        self.physics = PhysicsEngine(self.world)
        
        # Place the player at the top of the world
        spawn_x = WORLD_WIDTH // 2
        spawn_y = 0
        
        # Find a safe spawn spot (move down until we're above ground)
        for y in range(WORLD_HEIGHT // 2):
            if self.world.get_tile(spawn_x, y + 3) != MaterialType.AIR:
                spawn_y = y
                break
        
        # Clear some space for the player
        for clear_y in range(spawn_y, spawn_y + 3):
            for clear_x in range(spawn_x - 1, spawn_x + 3):
                self.world.set_tile(clear_x, clear_y, MaterialType.AIR)
        
        self.player = Player(spawn_x, spawn_y)
        self.renderer = Renderer()
    
    def process_input(self) -> None:
        """Process user input"""
        # Reset movement flags
        self.player.move_left = False
        self.player.move_right = False
        
        # Process events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    self.player.jump = True
                elif event.key == pygame.K_e or event.key == pygame.K_LCTRL:
                    self.player.dig_action = True
        
        # Process held keys
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.player.move_left = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.player.move_right = True
        if keys[pygame.K_SPACE]:
            self.player.jump = True
        if keys[pygame.K_e] or keys[pygame.K_LCTRL]:
            self.player.dig_action = True
    
    def update(self) -> None:
        """Update game state"""
        # Update player
        self.player.update(self.physics)
        
        # Update physics multiple times per frame for stability
        for _ in range(PHYSICS_STEPS_PER_FRAME):
            self.physics.update()
    
    def render(self) -> None:
        """Render the game"""
        self.renderer.clear()
        self.renderer.update_camera(self.player)
        self.renderer.render_world(self.world)
        self.renderer.render_player(self.player)
        self.renderer.flip()
    
    def run(self) -> None:
        """Run the main game loop"""
        self.running = True
        
        while self.running:
            self.process_input()
            self.update()
            self.render()
        
        self.renderer.cleanup()