"""
Main game module for Barren
"""
import pygame
import sys
import random
import math
import time
from enum import Enum, auto

from eartheater.constants import (
    FPS, PHYSICS_STEPS_PER_FRAME, SCREEN_WIDTH, SCREEN_HEIGHT,
    MaterialType, KEY_LEFT, KEY_RIGHT, KEY_UP, KEY_DOWN,
    KEY_JUMP, KEY_JETPACK, KEY_DIG, KEY_DIG_MOUSE, KEY_QUIT,
    BLACK, WHITE
)
from eartheater.world import World
from eartheater.physics import PhysicsEngine
from eartheater.entities import Player
from eartheater.render import Renderer
from eartheater.ui import Menu, LoadingScreen


class GameState(Enum):
    """Game state enumeration"""
    MENU = auto()
    LOADING = auto()
    PLAYING = auto()
    PAUSED = auto()

class Game:
    """Main game class"""
    
    def __init__(self):
        """Initialize the game"""
        self.running = False
        self.state = GameState.MENU
        
        # Initialize renderer first for UI
        self.renderer = Renderer()
        
        # Create menu system
        self.menu = Menu(
            title="BARREN",
            options=["Start Game", "Quit"],
            callback=self._handle_menu_selection
        )
        
        # World and physics are initialized during loading
        self.world = None
        self.physics = None
        self.player = None
        
        # Loading screen
        self.loading_screen = None
        
        # Debug flags
        self.show_debug = False
        self.paused = False
        
    def _handle_menu_selection(self, selection: int):
        """Handle menu selection
        
        Args:
            selection: Selected menu option index
        """
        if selection == 0:  # Start Game
            self._start_game()
        elif selection == 1:  # Quit
            self.running = False
    
    def _start_game(self):
        """Start a new game and show loading screen"""
        self.state = GameState.LOADING
        
        # Initialize loading screen
        self.loading_screen = LoadingScreen(self._finish_loading)
        
        # Initialize world in background
        self.world = World()
        self.physics = PhysicsEngine(self.world)
        
    def _finish_loading(self):
        """Complete game initialization after loading"""
        # Find a good spawn location
        spawn_x, spawn_y = self._find_spawn_location()
        
        # Create player at spawn location
        self.player = Player(spawn_x, spawn_y)
        
        # Switch to playing state
        self.state = GameState.PLAYING
    
    def _find_spawn_location(self) -> tuple:
        """
        Find a suitable spawn location for the player
        
        Returns:
            Tuple of (x, y) coordinates
        """
        # Start looking at the center top of the world
        spawn_x = 0
        spawn_y = 30  # Start above surface level
        
        # Generate initial chunks around origin
        self.world.update_active_chunks(spawn_x, spawn_y)
        
        # Find ground level
        while self.world.get_tile(spawn_x, spawn_y) == MaterialType.AIR and spawn_y < 100:
            spawn_y += 1
        
        # Move up to be above ground
        spawn_y -= 5
        
        # Clear space for player
        self._clear_spawn_area(spawn_x, spawn_y)
        
        return spawn_x, spawn_y
    
    def _clear_spawn_area(self, x: int, y: int) -> None:
        """
        Clear an area for the player to spawn safely
        
        Args:
            x: Center X-coordinate
            y: Center Y-coordinate
        """
        # Clear a safe area for the player
        for clear_y in range(y - 1, y + 4):
            for clear_x in range(x - 2, x + 3):
                self.world.set_tile(clear_x, clear_y, MaterialType.AIR)
        
        # Add a small platform
        for clear_x in range(x - 3, x + 4):
            self.world.set_tile(clear_x, y + 4, MaterialType.STONE)
    
    def process_input(self) -> None:
        """Process user input"""
        # Reset movement flags
        self.player.move_left = False
        self.player.move_right = False
        self.player.move_up = False
        self.player.move_down = False
        self.player.jetpack_active = False
        
        # Get mouse state
        mouse_buttons = pygame.mouse.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        
        # Update drill angle based on mouse position
        world_mouse_x, world_mouse_y = self.renderer.camera.screen_to_world(mouse_pos[0], mouse_pos[1])
        player_center_x = self.player.x + self.player.width / 2
        player_center_y = self.player.y + self.player.height / 2
        
        # Calculate angle from player to mouse
        dx = world_mouse_x - player_center_x
        dy = world_mouse_y - player_center_y
        self.player.drill_angle = math.atan2(dy, dx)
        
        # Process events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == KEY_QUIT:
                    self.running = False
                elif event.key == KEY_JUMP:
                    self.player.jump_pressed = True
                elif event.key == KEY_DIG:
                    self.player.dig_action = True  # Keep keyboard option
                elif event.key == pygame.K_F3:  # Debug toggle
                    self.show_debug = not self.show_debug
                    self.renderer.show_debug = self.show_debug  # Update renderer state
                elif event.key == pygame.K_p:  # Pause toggle
                    self.paused = not self.paused
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == KEY_DIG_MOUSE:  # Left mouse button
                    # Set drill as active
                    self.player.dig_action = True
        
        # Process held keys
        keys = pygame.key.get_pressed()
        
        # Movement
        if keys[KEY_LEFT]:
            self.player.move_left = True
        if keys[KEY_RIGHT]:
            self.player.move_right = True
        if keys[KEY_UP]:
            self.player.move_up = True
        if keys[KEY_DOWN]:
            self.player.move_down = True
        
        # Jumping and jetpack (reduced power)
        if keys[KEY_JUMP]:
            if not self.player.is_on_ground:
                self.player.jetpack_active = True
            else:
                self.player.jump_pressed = True
        
        # Mouse-based digging (continuous)
        if mouse_buttons[KEY_DIG_MOUSE - 1]:  # Adjust for 0-indexed array
            self.player.dig_action = True
    
    def update(self) -> None:
        """Update game state"""
        if self.paused:
            return
            
        # Update active chunks based on player position
        self.world.update_active_chunks(self.player.x, self.player.y)
        
        # Update player
        self.player.update(self.physics)
        
        # Update physics multiple times per frame for stability
        for _ in range(PHYSICS_STEPS_PER_FRAME):
            self.physics.update(self.player.x, self.player.y)
            
        # Add some ambient particles occasionally
        if random.random() < 0.05:
            self._add_ambient_particles()
    
    def _add_ambient_particles(self) -> None:
        """Add ambient particles for atmosphere"""
        # Add dust particles in caves
        screen_center_x = self.renderer.camera.target_x
        screen_center_y = self.renderer.camera.target_y
        
        # Random position within view
        x = screen_center_x + random.uniform(-10, 10)
        y = screen_center_y + random.uniform(-8, 8)
        
        # Only add particles in air or caves
        if self.world.get_tile(int(x), int(y)) == MaterialType.AIR:
            # Check if we're in a cave (underground with solid blocks nearby)
            is_cave = False
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if self.world.get_tile(int(x + dx), int(y + dy)) in [MaterialType.STONE, MaterialType.DIRT]:
                        is_cave = True
                        break
                if is_cave:
                    break
            
            if is_cave:
                # Create dust particle
                particle = {
                    'x': x,
                    'y': y,
                    'vx': random.uniform(-0.02, 0.02),
                    'vy': random.uniform(-0.02, 0.02),
                    'life': random.randint(30, 100),
                    'color': (180, 180, 180, 40),  # Semi-transparent dust
                    'size': random.uniform(0.1, 0.3)
                }
                self.renderer.particle_system.add_particle(particle)
    
    def render(self) -> None:
        """Render the game"""
        # Clear all rendering surfaces
        self.renderer.clear()
        
        # Update camera position
        self.renderer.update_camera(self.player)
        
        # Render world and entities
        self.renderer.render_world(self.world)
        self.renderer.render_player(self.player)
        
        # Render UI elements
        self.renderer.render_ui(self.player)
        
        # If paused, render pause message
        if self.paused:
            # Create pause text
            font = pygame.font.SysFont("Arial", 32)
            pause_text = font.render("PAUSED", True, (255, 255, 255))
            text_rect = pause_text.get_rect(center=(800/2, 600/2))
            
            # Add text to UI surface
            self.renderer.ui_surface.blit(pause_text, text_rect)
        
        # Update the display
        self.renderer.flip()
    
    def run(self) -> None:
        """Run the main game loop"""
        self.running = True
        
        # Track loading progress and time
        last_time = time.time()
        
        # Main game loop
        while self.running:
            # Calculate delta time
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time
            
            # Process input and rendering based on current state
            if self.state == GameState.MENU:
                # Process menu input
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.KEYDOWN and event.key == KEY_QUIT:
                        self.running = False
                    else:
                        self.menu.handle_event(event)
                
                # Update and render menu
                self.menu.update()
                self.menu.render(self.renderer.screen)
                
            elif self.state == GameState.LOADING:
                # Process basic input
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.KEYDOWN and event.key == KEY_QUIT:
                        self.running = False
                
                # Update loading progress
                if not self.world.preloaded:
                    # Start preloading chunks
                    self.world.preload_chunks(0, 0, 8)
                
                # Update loading screen
                self.loading_screen.set_progress(self.world.loading_progress)
                self.loading_screen.update()
                self.loading_screen.render(self.renderer.screen)
                
            elif self.state == GameState.PLAYING:
                # Process gameplay input
                self.process_input()
                
                # Update game state
                self.update()
                
                # Render game
                self.render()
            
            # Update display for all states
            pygame.display.flip()
            
            # Maintain frame rate
            self.renderer.clock.tick(FPS)
        
        # Clean up resources
        self.renderer.cleanup()