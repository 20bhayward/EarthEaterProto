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
    DIRT_MATERIALS, FPS, PHYSICS_STEPS_PER_FRAME, SCREEN_WIDTH, SCREEN_HEIGHT, STONE_MATERIALS,
    MaterialType, KEY_LEFT, KEY_RIGHT, KEY_UP, KEY_DOWN,
    KEY_JUMP, KEY_JETPACK, KEY_DIG, KEY_DIG_MOUSE, KEY_QUIT,
    BLACK, WHITE, BiomeType, WorldGenSettings, MATERIAL_COLORS,
    SKY_COLOR_TOP, SKY_COLOR_HORIZON, UNDERGROUND_COLOR,
    SUN_COLOR, SUN_RADIUS, SUN_RAY_LENGTH, SUN_INTENSITY
)
from eartheater.world import World
from eartheater.physics import PhysicsEngine
from eartheater.entities import Player
from eartheater.render import Renderer
from eartheater.ui import Menu, LoadingScreen, SettingsMenu


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
        
        # World settings
        self.world_settings = WorldGenSettings()
        self.settings_menu = None
        
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
            # Skip settings menu and go directly to game
            self._start_game()
        elif selection == 1:  # Quit
            self.running = False
    
    def _start_game(self):
        """Start a new game and show loading screen"""
        self.state = GameState.LOADING
        
        # Initialize world first with current settings
        self.world = World(settings=self.world_settings)
        self.physics = PhysicsEngine(self.world)
        
        # Initialize loading screen with world reference for preview
        self.loading_screen = LoadingScreen(self._finish_loading, self.world)
        
    def _finish_loading(self):
        """Complete game initialization after loading"""
        try:
            # Force world to be preloaded
            self.world.preloaded = True
            self.world.loading_progress = 1.0
            
            # Find a good spawn location - use the center of the world
            spawn_x, spawn_y = self.world.width // 2, 80  # Centered spawn
            
            # Create player at spawn location with ultra-minimal model
            try:
                # Create player
                self.player = Player(spawn_x, spawn_y)
                
                # Set initial properties for stability
                self.player.trail_particles = []  # Ensure empty particles list
                self.player.last_safe_position = (spawn_x, 50)
                
                # Store player reference in renderer
                if self.player not in self.renderer.entities:
                    self.renderer.entities.append(self.player)
                    
                # Use the minimal player sprite by default - much more stable
                # Don't attempt to create detailed sprites until game is running
                print("Using minimal player model for stability")
            except Exception as player_err:
                # Fallback to extremely simple player initialization
                print(f"Error creating player: {player_err}")
                self.player = Player(100, 80)  # Fallback position
                self.player.trail_particles = []  # Empty particle list
                self.player.last_safe_position = (100, 50)
            
            # Generate just enough chunks for starting
            try:
                # Get single spawn chunk
                spawn_chunk_x, spawn_chunk_y = self.world.world_to_chunk_coords(spawn_x, spawn_y)
                self.world.get_chunk(spawn_chunk_x, spawn_chunk_y)
                print(f"Generated spawn chunk at {spawn_chunk_x}, {spawn_chunk_y}")
            except Exception as chunk_err:
                print(f"Error generating spawn chunk: {chunk_err}")
            
            # Clear spawn area for safety
            try:
                self._clear_spawn_area(spawn_x, spawn_y)
            except Exception as clear_err:
                print(f"Error clearing spawn area: {clear_err}")
                # Fallback: Manual air blocks around player
                for dx in range(-5, 6):
                    for dy in range(-5, 6):
                        try:
                            self.world.set_block(spawn_x + dx, spawn_y + dy, MaterialType.AIR)
                        except:
                            pass
            
            # Force player to a safe position above ground
            self.player.y = 50  # Higher position
            self.player.x = spawn_x
            self.player.last_safe_position = (spawn_x, 50)
            
            # Initialize camera zoom to a default value
            self.renderer.camera.zoom = 1.0
            self.renderer.camera.target_zoom = 1.0
            
            # Switch to playing state
            self.state = GameState.PLAYING
            
            # Debug output
            print(f"Successfully finished loading! Player at {self.player.x}, {self.player.y}")
            
        except Exception as e:
            # If anything fails, print the error but continue anyway
            print(f"Critical error during loading: {e}")
            
            # Force into playing state with emergency fallbacks
            self.state = GameState.PLAYING
            
            # Emergency player creation
            if not hasattr(self, 'player') or self.player is None:
                print("Creating emergency player")
                self.player = Player(100, 50)
                self.player.trail_particles = []
                
                # Force add to renderer entities
                if hasattr(self, 'renderer') and hasattr(self.renderer, 'entities'):
                    if self.player not in self.renderer.entities:
                        self.renderer.entities.append(self.player)
                        
            # Emergency world creation if needed
            if not self.world.preloaded:
                self.world.preloaded = True
            
            # Still try to create player and switch state
            if not hasattr(self, 'player'):
                self.player = Player(0, 80)
                
            self.state = GameState.PLAYING
    
    def _find_spawn_location(self) -> tuple:
        """
        Find a suitable spawn location for the player
        
        Returns:
            Tuple of (x, y) coordinates
        """
        # Initialize progress monitoring
        self.world.loading_progress = 0.1
        
        # Generate initial chunks around origin
        self.world.generate_initial_chunks()
        self.world.loading_progress = 0.8
        
        # Use the spawn position determined by the world generation
        spawn_x, spawn_y = self.world.spawn_position
        self.world.loading_progress = 1.0
        
        # Clear a larger area for player
        self._clear_spawn_area(spawn_x, spawn_y)
        
        return spawn_x, spawn_y
    
    def _clear_spawn_area(self, x: int, y: int) -> None:
        """
        Clear an area for the player to spawn safely
        
        Args:
            x: Center X-coordinate
            y: Center Y-coordinate
        """
        # Player height and width estimates (must be hardcoded as player doesn't exist yet)
        player_height = 10  # Matches the height in Player class
        player_width = 6    # Matches the width in Player class
        
        # Clear a larger safe area for the player
        for clear_y in range(y - 2, y + player_height + 2):
            for clear_x in range(x - 4, x + player_width + 4):
                self.world.set_block(clear_x, clear_y, MaterialType.AIR)
        
        # Add a wider platform
        for clear_x in range(x - 6, x + 7):
            self.world.set_block(clear_x, y + player_height + 2, MaterialType.STONE_MEDIUM)
            
        # Add some visual elements to the platform
        for clear_x in range(x - 5, x + 6, 2):
            self.world.set_block(clear_x, y + player_height + 1, MaterialType.GRASS_MEDIUM)
    
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
                
                # Camera zoom controls
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    self.renderer.camera.adjust_zoom(0.1)  # Zoom in
                elif event.key == pygame.K_MINUS:
                    self.renderer.camera.adjust_zoom(-0.1)  # Zoom out
                elif event.key == pygame.K_0:
                    self.renderer.camera.target_zoom = 1.0  # Reset zoom to 100%
                    
                # Toggle player randomization (for testing purposes)
                elif event.key == pygame.K_r:
                    if hasattr(self.renderer, 'randomize_player'):
                        self.renderer.randomize_player = not self.renderer.randomize_player
                        print(f"Randomize player: {self.renderer.randomize_player}")
                    else:
                        self.renderer.randomize_player = True
                        print("Randomize player enabled")
                        
            # Mouse wheel for zoom
            elif event.type == pygame.MOUSEWHEEL:
                zoom_amount = event.y * 0.05  # Smaller increments for smoother zoom
                self.renderer.camera.adjust_zoom(zoom_amount)
                
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
    
    def update(self, dt: float) -> None:
        """
        Update game state with optimized physics
        
        Args:
            dt: Delta time (time since last frame in seconds)
        """
        if self.paused:
            return
            
        # Update active chunks based on player position
        # This method now separates rendering chunks from physics simulation chunks
        self.world.update_active_chunks(self.player.x, self.player.y)
        
        # Scale player movement by delta time for consistent speed
        self.player.update(self.physics, dt)
        
        # Update physics only for nearby chunks with fewer steps
        for _ in range(PHYSICS_STEPS_PER_FRAME):
            self.physics.update(self.player.x, self.player.y)
    
    def _add_ambient_particles(self) -> None:
        """Add ambient particles for atmosphere"""
        # Add dust particles in caves
        screen_center_x = self.renderer.camera.target_x
        screen_center_y = self.renderer.camera.target_y
        
        # Random position within view
        x = screen_center_x + random.uniform(-10, 10)
        y = screen_center_y + random.uniform(-8, 8)
        
        # Only add particles in air or caves
        if self.world.get_block(int(x), int(y)) == MaterialType.AIR:
            # Check if we're in a cave (underground with solid blocks nearby)
            is_cave = False
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    tile_material = self.world.get_block(int(x + dx), int(y + dy))
                    if (tile_material in STONE_MATERIALS or tile_material in DIRT_MATERIALS):
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
        # Clear all rendering surfaces - pass the world to get biome-specific sky colors
        self.renderer.clear(self.world)
        
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
        """Run the main game loop with fixed timestep physics"""
        self.running = True
        
        # Track loading progress and time
        last_time = time.time()
        accumulated_time = 0
        physics_timestep = 1.0 / FPS  # Fixed timestep (e.g., 1/60 seconds)
        
        # Main game loop
        while self.running:
            # Calculate how much time has passed
            current_time = time.time()
            frame_time = current_time - last_time
            last_time = current_time
            
            # Limit frame_time to prevent spiral of death during debug/lag
            if frame_time > 0.25:
                frame_time = 0.25
                
            # Accumulate time for physics steps
            accumulated_time += frame_time
            
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
                
                # Make sure menu is displayed properly
                pygame.display.flip()
            
            # Settings state removed - we go directly to loading from menu now
                
            elif self.state == GameState.LOADING:
                # Process basic input
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.KEYDOWN and event.key == KEY_QUIT:
                        self.running = False
                
                # # Update loading progress
                # if not self.world.preloaded:
                #     # Preload a smaller area first to improve loading speed
                #     # Preload radius based on world size
                #     preload_radius = 4  # Default for medium
                #     if self.world_settings.world_size == "small":
                #         preload_radius = 3  # Smaller radius for small worlds
                #     elif self.world_settings.world_size == "large":
                #         preload_radius = 5  # Still reduced from original for performance
                        
                #     # Process a few chunks each frame to keep UI responsive
                #     chunk_batch_size = 1  # Process 1 chunk per frame for stability
                    
                #     if not hasattr(self, '_chunks_to_preload'):
                #         # First time - initialize chunk loading system
                #         self._chunks_to_preload = []
                #         self._preload_started = False
                #         self._loading_chunks_processed = 0
                        
                #         # Set additional safety flags
                #         self._preview_created = False
                #         self._load_error = False
                        
                #         # Calculate chunks that need loading
                #         # Use a smaller radius for the initial version to ensure stability
                #         reduced_radius = max(2, preload_radius - 1)  # Ensure at least 2x2 chunks around player
                #         for dx in range(-reduced_radius, reduced_radius + 1):
                #             for dy in range(-reduced_radius, reduced_radius + 1):
                #                 if dx*dx + dy*dy <= reduced_radius*reduced_radius:
                #                     # Store as tuple with distance from center (for priority)
                #                     dist = math.sqrt(dx*dx + dy*dy)
                #                     self._chunks_to_preload.append((0 + dx, 0 + dy, dist))
                        
                #         # Sort by distance for spiral loading (center first)
                #         self._chunks_to_preload.sort(key=lambda c: c[2])
                #         self._total_preload_chunks = len(self._chunks_to_preload)
                        
                #         # Mark preview as created (we do this in preload_chunks now)
                #         self._preview_created = True
                            
                #         self._preload_started = True
                        
                #     if self._preload_started and self._chunks_to_preload and not self._load_error:
                #         try:
                #             # Process a batch of chunks
                #             chunks_this_frame = min(chunk_batch_size, len(self._chunks_to_preload))
                #             for _ in range(chunks_this_frame):
                #                 if self._chunks_to_preload:
                #                     chunk_x, chunk_y, _ = self._chunks_to_preload.pop(0)
                #                     chunk = self.world.ensure_chunk_exists(chunk_x, chunk_y)
                #                     if not chunk.generated:
                #                         self.world.generate_chunk(chunk)
                #                     self._loading_chunks_processed += 1
                            
                #             # Update loading progress based on chunks processed
                #             self.world.loading_progress = min(0.98, 
                #                                           self._loading_chunks_processed / self._total_preload_chunks)
                #         except Exception as e:
                #             print(f"Error during chunk generation: {e}")
                #             self._load_error = True
                    
                #     # Check if loading is complete or error occurred
                #     if (self._preload_started and not self._chunks_to_preload) or self._load_error:
                #         # All chunks processed or error encountered
                #         self.world.loading_progress = 1.0
                #         self.world.preloaded = True
                        
                #         # If there was an error, we'll still continue, but some chunks may be missing
                #         if self._load_error:
                #             print("Warning: Some chunks failed to generate. Continuing anyway.")
                            
                #         # Clean up
                #         del self._chunks_to_preload
                #         del self._preload_started
                #         del self._loading_chunks_processed
                #         del self._total_preload_chunks
                #         del self._preview_created
                #         del self._load_error
                
                # Update loading screen with progress from world generation
                self.loading_screen.set_progress(self.world.loading_progress)
                self.loading_screen.update()
                self.loading_screen.render(self.renderer.screen)
                
                # Make sure loading screen is displayed properly
                pygame.display.flip()
                
            elif self.state == GameState.PLAYING:
                # Process gameplay input once per frame
                self.process_input()
                
                # Run physics updates at fixed timestep, may run 0, 1, or several updates depending on timing
                while accumulated_time >= physics_timestep:
                    # Update game state with fixed physics step
                    self.update(physics_timestep)
                    accumulated_time -= physics_timestep
                    
                    # Prevent spiral of death by not letting simulation get too far behind
                    if accumulated_time > 10 * physics_timestep:
                        accumulated_time = 0
                        break
                
                # Render at whatever framerate the system can handle
                self.render()
            
            # Remove redundant display flip and frame rate limiting
            # This is already handled in the renderer
        
        # Clean up resources
        self.renderer.cleanup()