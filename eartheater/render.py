"""
Rendering system for EarthEater
"""
import pygame
import random
import math
from typing import Tuple, Dict, List, Optional
import numpy as np

from eartheater.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, BLACK, BLUE, WHITE,
    MaterialType, BlockType, BiomeType, MATERIAL_COLORS, BACKGROUND_COLORS, 
    CHUNK_SIZE, FPS, FULLSCREEN, BIOME_SKY_COLORS,
    UNDERGROUND_COLOR, SUN_COLOR, SUN_RADIUS, SUN_RAY_LENGTH, SUN_INTENSITY
)
from eartheater.world import World
from eartheater.entities import Player


class Camera:
    """Camera that follows the player"""
    
    def __init__(self, width: int, height: int):
        """
        Initialize camera
        
        Args:
            width: Screen width in pixels
            height: Screen height in pixels
        """
        self.x = 0
        self.y = 0
        self.width = width
        self.height = height
        self.target_x = 0
        self.target_y = 0
        self.smoothing = 0.08  # Reduced for smoother camera movement
        self.zoom = 1.0  # Added zoom capability for future use
    
    def follow(self, target_x: float, target_y: float) -> None:
        """
        Update camera position to follow a target with smoothing
        
        Args:
            target_x: Target x-coordinate in world space
            target_y: Target y-coordinate in world space
        """
        # Set the target position
        self.target_x = target_x
        self.target_y = target_y
        
        # Smoothly move camera toward target
        target_cam_x = int(target_x * TILE_SIZE - self.width / 2)
        target_cam_y = int(target_y * TILE_SIZE - self.height / 2)
        
        # Interpolate current position toward target position
        self.x += (target_cam_x - self.x) * self.smoothing
        self.y += (target_cam_y - self.y) * self.smoothing
    
    def world_to_screen(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """
        Convert world coordinates to screen coordinates
        
        Args:
            world_x: X-coordinate in world space
            world_y: Y-coordinate in world space
            
        Returns:
            Tuple of (screen_x, screen_y) coordinates
        """
        screen_x = int(world_x * TILE_SIZE - self.x)
        screen_y = int(world_y * TILE_SIZE - self.y)
        return screen_x, screen_y
    
    def screen_to_world(self, screen_x: int, screen_y: int) -> Tuple[float, float]:
        """
        Convert screen coordinates to world coordinates
        
        Args:
            screen_x: X-coordinate on screen
            screen_y: Y-coordinate on screen
            
        Returns:
            Tuple of (world_x, world_y) coordinates
        """
        world_x = (screen_x + self.x) / TILE_SIZE
        world_y = (screen_y + self.y) / TILE_SIZE
        return world_x, world_y


class ParticleSystem:
    """Manages particle effects"""
    
    def __init__(self, camera: Camera):
        """
        Initialize particle system
        
        Args:
            camera: Camera used for coordinate transformation
        """
        self.camera = camera
        self.particles = []
        
    def add_particle(self, particle: Dict) -> None:
        """
        Add a particle to the system
        
        Args:
            particle: Dictionary with particle properties
        """
        self.particles.append(particle)
    
    def update(self) -> None:
        """Update all particles"""
        # Remove expired particles
        self.particles = [p for p in self.particles if p['life'] > 0]
        
    def render(self, surface: pygame.Surface) -> None:
        """
        Render all particles
        
        Args:
            surface: Surface to render to
        """
        for particle in self.particles:
            # Get screen coordinates
            screen_x, screen_y = self.camera.world_to_screen(particle['x'], particle['y'])
            
            # Get particle size in pixels
            size = int(particle['size'] * TILE_SIZE)
            if size < 1:
                size = 1
                
            # Skip if offscreen
            if (screen_x < -size or screen_x > SCREEN_WIDTH + size or
                screen_y < -size or screen_y > SCREEN_HEIGHT + size):
                continue
            
            # Draw particle
            if size <= 1:
                surface.set_at((int(screen_x), int(screen_y)), particle['color'])
            else:
                pygame.draw.circle(surface, particle['color'], (int(screen_x), int(screen_y)), size)


class LightSystem:
    """Manages dynamic lighting effects"""
    
    def __init__(self, camera: Camera):
        """
        Initialize lighting system
        
        Args:
            camera: Camera used for coordinate transformation
        """
        self.camera = camera
        self.lights = []
        self.ambient_light = 120  # Higher ambient light for better visibility (0-255)
        
        # Create surfaces for lighting
        self.light_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.temp_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    
    def add_light(self, x: float, y: float, radius: float, color: Tuple[int, int, int], intensity: float = 1.0, 
                   light_type: str = "point") -> None:
        """
        Add a light source
        
        Args:
            x: X-coordinate in world space
            y: Y-coordinate in world space
            radius: Radius of light in world units
            color: RGB color tuple
            intensity: Light intensity multiplier
            light_type: Type of light ("point", "radial", "directional")
        """
        self.lights.append({
            'x': x,
            'y': y,
            'radius': radius,
            'color': color,
            'intensity': intensity,
            'type': light_type,
            'flicker': 0 if light_type != "fire" else random.uniform(0.8, 1.2)
        })
    
    def clear_lights(self) -> None:
        """Clear all dynamic lights"""
        self.lights = []
    
    def render(self, surface: pygame.Surface) -> None:
        """
        Apply lighting effects to the scene
        
        Args:
            surface: Surface to apply lighting to
        """
        # Clear the light surface with ambient light
        self.light_surface.fill((self.ambient_light, self.ambient_light, self.ambient_light, 255))
        
        # Draw each light onto the light surface
        for light in self.lights:
            # Get light type and apply flicker if needed
            light_type = light.get('type', 'point')
            intensity_mult = 1.0
            
            # Apply flickering for fire-type lights
            if light_type == 'fire':
                light['flicker'] = light['flicker'] * 0.8 + random.uniform(0.7, 1.3) * 0.2
                intensity_mult = light['flicker']
            
            # Convert light position to screen coordinates
            screen_x, screen_y = self.camera.world_to_screen(light['x'], light['y'])
            
            # Convert light radius to screen pixels
            screen_radius = int(light['radius'] * TILE_SIZE)
            
            # Skip if light is off-screen
            if (screen_x + screen_radius < 0 or screen_x - screen_radius > SCREEN_WIDTH or
                screen_y + screen_radius < 0 or screen_y - screen_radius > SCREEN_HEIGHT):
                continue
            
            # Create a radial gradient for the light
            self.temp_surface.fill((0, 0, 0, 0))
            
            # Draw light based on type
            if light_type in ['point', 'fire']:
                # Draw light with a radial gradient
                for r in range(screen_radius, 0, -1):
                    intensity = (r / screen_radius) * 255 * light['intensity'] * intensity_mult
                    intensity = 255 - intensity  # Invert so center is brightest
                    
                    if intensity > 255:
                        intensity = 255
                    if intensity < 0:
                        intensity = 0
                        
                    color = (
                        int(light['color'][0] * intensity / 255),
                        int(light['color'][1] * intensity / 255),
                        int(light['color'][2] * intensity / 255),
                        int(intensity)
                    )
                    
                    pygame.draw.circle(self.temp_surface, color, (screen_x, screen_y), r)
            
            elif light_type == 'directional':
                # For sun-like directional light
                # Create a gradient that's stronger in one direction
                for r in range(screen_radius, 0, -1):
                    intensity = (r / screen_radius) * 255 * light['intensity']
                    intensity = 255 - intensity  # Invert so center is brightest
                    
                    if intensity > 255:
                        intensity = 255
                    if intensity < 0:
                        intensity = 0
                        
                    color = (
                        int(light['color'][0] * intensity / 255),
                        int(light['color'][1] * intensity / 255),
                        int(light['color'][2] * intensity / 255),
                        int(intensity)
                    )
                    
                    # Make an elliptical light
                    pygame.draw.ellipse(
                        self.temp_surface, 
                        color, 
                        (screen_x - r, screen_y - r//2, r*2, r)
                    )
            
            # Add the light to the light surface
            self.light_surface.blit(self.temp_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MAX)
        
        # Apply lighting to the main surface
        surface.blit(self.light_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)


class Renderer:
    """Handles rendering the game world and entities"""
    
    def __init__(self):
        """Initialize the renderer"""
        pygame.init()
        
        # Enable multicore support
        try:
            pygame.display.set_allow_busy_loop(True)
        except:
            pass
        
        # Set up display with fullscreen if enabled - using FULLSCREEN from constants
        if FULLSCREEN:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
        else:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.HWSURFACE | pygame.DOUBLEBUF)
        pygame.display.set_caption("Barren")
        self.clock = pygame.time.Clock()
        
        # Create camera
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)
        
        # Create particle and lighting systems
        self.particle_system = ParticleSystem(self.camera)
        self.light_system = LightSystem(self.camera)
        
        # Layer surfaces for composite rendering - use hardware acceleration when possible
        self.background_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.HWSURFACE)
        self.world_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.HWSURFACE | pygame.SRCALPHA)
        self.entity_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.HWSURFACE | pygame.SRCALPHA)
        self.sky_objects_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.HWSURFACE | pygame.SRCALPHA)
        self.ui_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.HWSURFACE | pygame.SRCALPHA)
        
        # Create chunk surface cache
        self.chunk_surfaces = {}
        
        # Font for UI
        self.font = pygame.font.SysFont("Arial", 16)
        
        # Frames for performance measurement
        self.frame_times = []
        self.fps_display = 0
        self.fps_update_timer = 0
        
        # Store player and entity references
        self.entities = []
        
        # Create player sprites
        self.player_sprite = {
            'idle': None,  # Will be created when player is first seen
            'dig': None
        }
        
        # Sun position
        self.sun_x = SCREEN_WIDTH * 0.75
        self.sun_y = SCREEN_HEIGHT * 0.25
        self.time_of_day = 0  # 0 to 1, representing time of day
        
        # Debug overlay
        self.show_debug = False
        
        # Setup particle presets for optimization
        self.particle_presets = {
            'jetpack_flame': [(255, 200, 50, a) for a in range(0, 200, 10)],
            'jetpack_core': [(255, 255, 200, a) for a in range(0, 240, 10)],
            'dig_dust': [(180, 180, 180, a) for a in range(0, 200, 10)],
        }
    
    def _create_player_sprite(self, color: Tuple[int, int, int]) -> pygame.Surface:
        """
        Create a voxel-based humanoid player sprite with ragged pants
        
        Args:
            color: Base color for the sprite
            
        Returns:
            Surface with the voxel player sprite
        """
        # Get player model properties from player object if available
        try:
            from eartheater.entities import Player
            player_instance = None
            for entity in self.entities:
                if isinstance(entity, Player):
                    player_instance = entity
                    break
                    
            # Use custom colors if available
            skin_color = getattr(player_instance, 'skin_color', (210, 160, 120))
            pants_color = getattr(player_instance, 'pants_color', (60, 70, 120))
        except:
            # Fallback colors if we can't get player properties
            skin_color = (210, 160, 120)  # Natural skin tone
            pants_color = (60, 70, 120)   # Ragged blue pants
        
        # Create a surface for the sprite - larger for more detail
        scale_factor = 2.5
        width = int(6 * TILE_SIZE * scale_factor)
        height = int(10 * TILE_SIZE * scale_factor)
        sprite = pygame.Surface((width, height), pygame.SRCALPHA)
        
        # Define voxel size
        voxel_size = max(2, int(TILE_SIZE * 0.5))
        
        # Voxel-based body structure (naked man with ragged pants)
        # Draw in layers from back to front
        
        # -- LEGS --
        # Left leg
        leg_width = width // 5
        leg_height = height // 3
        leg_x = width // 3 - leg_width // 2
        leg_y = height - leg_height
        
        # Create ragged edges for pants (right leg)
        pants_right = []
        for y in range(leg_y, leg_y + leg_height, voxel_size):
            # Random width variation for ragged look
            leg_right_width = leg_width + random.randint(-1, 1) * voxel_size
            pants_right.append((width - leg_x - leg_right_width, y, leg_right_width, voxel_size))
            
        # Ragged pants (left leg)
        for y in range(leg_y, leg_y + leg_height, voxel_size):
            # Random width variation for ragged look
            leg_variation = random.randint(-1, 1) * voxel_size
            left_width = leg_width + leg_variation
            # Draw voxel row
            pygame.draw.rect(sprite, pants_color, (leg_x, y, left_width, voxel_size))
            
            # Draw right leg
            right_data = pants_right[((y - leg_y) // voxel_size) % len(pants_right)]
            pygame.draw.rect(sprite, pants_color, right_data)
            
        # -- TORSO --
        torso_width = width // 2
        torso_height = height // 2
        torso_x = width // 2 - torso_width // 2
        torso_y = height // 3
        
        # Draw torso with voxel detail
        for y in range(torso_y, torso_y + torso_height, voxel_size):
            # Add slight curvature to torso
            if y < torso_y + torso_height // 3:  # Upper chest
                row_width = int(torso_width * 0.9)
            elif y > torso_y + torso_height * 2 // 3:  # Waist
                row_width = int(torso_width * 0.8)
            else:  # Middle
                row_width = torso_width
                
            row_x = width // 2 - row_width // 2
            pygame.draw.rect(sprite, skin_color, (row_x, y, row_width, voxel_size))
            
        # -- ARMS --
        arm_width = width // 6
        arm_length = height // 2.2
        
        # Left arm position
        left_arm_x = torso_x - arm_width + voxel_size
        left_arm_y = torso_y + voxel_size * 2
        
        # Right arm position
        right_arm_x = torso_x + torso_width - voxel_size
        right_arm_y = torso_y + voxel_size * 2
        
        # Draw arms with slight angle
        for i in range(int(arm_length // voxel_size)):
            offset_y = i * voxel_size
            # Left arm gets progressively thinner and angles slightly
            left_width = max(arm_width - i, arm_width // 2)
            left_offset_x = int(i * 0.3) * voxel_size  # Angle the arm slightly
            
            # Right arm similar but mirrored
            right_width = max(arm_width - i, arm_width // 2)
            right_offset_x = int(i * 0.3) * voxel_size  # Angle the arm slightly
            
            # Draw arm voxels
            pygame.draw.rect(sprite, skin_color, 
                           (left_arm_x + left_offset_x, left_arm_y + offset_y, 
                            left_width, voxel_size))
            pygame.draw.rect(sprite, skin_color, 
                           (right_arm_x - right_offset_x - right_width, right_arm_y + offset_y, 
                            right_width, voxel_size))
        
        # -- HEAD --
        head_size = width // 3
        head_x = width // 2 - head_size // 2
        head_y = torso_y - head_size + voxel_size
        
        # Draw voxel head
        for y in range(head_y, head_y + head_size, voxel_size):
            for x in range(head_x, head_x + head_size, voxel_size):
                # Make corners more rounded by skipping corner voxels
                corner_distance = math.sqrt((x - (head_x + head_size//2))**2 + 
                                         (y - (head_y + head_size//2))**2)
                if corner_distance <= head_size // 2:
                    pygame.draw.rect(sprite, skin_color, (x, y, voxel_size, voxel_size))
        
        # -- FACE DETAILS --
        # Eyes (2 pixels wide for each eye, black)
        eye_y = head_y + head_size // 3
        eye_size = voxel_size
        pygame.draw.rect(sprite, (30, 30, 30), 
                       (head_x + head_size // 3 - eye_size // 2, eye_y, 
                        eye_size, eye_size))
        pygame.draw.rect(sprite, (30, 30, 30), 
                       (head_x + head_size * 2 // 3 - eye_size // 2, eye_y, 
                        eye_size, eye_size))
        
        # Simple mouth line
        mouth_y = head_y + head_size * 2 // 3
        mouth_width = head_size // 2
        pygame.draw.rect(sprite, (150, 90, 80), 
                       (head_x + head_size // 2 - mouth_width // 2, mouth_y, 
                        mouth_width, voxel_size // 2))
        
        # Hair - random short voxel tufts on top of head
        hair_color = (60, 40, 20)  # Dark brown
        for i in range(head_size // voxel_size):
            hair_x = head_x + i * voxel_size
            hair_height = random.randint(1, 3) * (voxel_size // 2)
            if random.random() < 0.7:  # 70% chance of hair at each position
                pygame.draw.rect(sprite, hair_color, 
                               (hair_x, head_y - hair_height, voxel_size, hair_height))
        
        return sprite
    
    def _render_sun(self) -> None:
        """Render the sun and its rays"""
        # Clear the surface
        self.sky_objects_surface.fill((0, 0, 0, 0))
        
        # Update time of day (cycle sun position)
        self.time_of_day = (self.time_of_day + 0.0003) % 1.0
        
        # Calculate sun position based on time of day
        sun_angle = self.time_of_day * 2 * math.pi
        orbit_x = math.cos(sun_angle) * (SCREEN_WIDTH * 0.4)
        orbit_y = math.sin(sun_angle) * (SCREEN_HEIGHT * 0.3)
        
        self.sun_x = SCREEN_WIDTH / 2 + orbit_x
        self.sun_y = SCREEN_HEIGHT * 0.3 - orbit_y * 0.6
        
        # Only draw sun if it's above the horizon
        if self.sun_y < SCREEN_HEIGHT:
            # Draw sun glow (outer)
            for r in range(SUN_RADIUS + 20, SUN_RADIUS, -2):
                alpha = 100 - (SUN_RADIUS + 20 - r) * 5
                if alpha < 0:
                    alpha = 0
                color = SUN_COLOR + (alpha,)
                pygame.draw.circle(self.sky_objects_surface, color, (int(self.sun_x), int(self.sun_y)), r)
            
            # Draw sun body
            pygame.draw.circle(self.sky_objects_surface, SUN_COLOR, (int(self.sun_x), int(self.sun_y)), SUN_RADIUS)
            
            # Add rays
            num_rays = 12
            for i in range(num_rays):
                angle = i * (2 * math.pi / num_rays)
                ray_length = SUN_RADIUS + random.randint(10, 30)
                end_x = self.sun_x + math.cos(angle) * ray_length
                end_y = self.sun_y + math.sin(angle) * ray_length
                
                # Draw ray
                pygame.draw.line(
                    self.sky_objects_surface, 
                    SUN_COLOR, 
                    (int(self.sun_x), int(self.sun_y)),
                    (int(end_x), int(end_y)),
                    3
                )
            
            # Add sun light to the light system as directional light
            self.light_system.add_light(
                self.camera.screen_to_world(int(self.sun_x), int(self.sun_y))[0],
                self.camera.screen_to_world(int(self.sun_x), int(self.sun_y))[1],
                SUN_RAY_LENGTH / TILE_SIZE,
                SUN_COLOR,
                SUN_INTENSITY,
                "directional"
            )

    def clear(self, world: World) -> None:
        """
        Clear all rendering surfaces and draw the sky based on biome
        
        Args:
            world: The world to render sky for
        """
        # Create a gradient sky background
        # Get camera position to determine if we're underground and current biome
        camera_world_x = self.camera.target_x
        camera_world_y = self.camera.target_y
        
        # Determine the primary biome at camera position
        primary_biome = world.get_biome_at(int(camera_world_x), int(camera_world_y))
        
        # Always force surface biome for now to ensure sky is visible
        primary_biome = BiomeType.HILLS
            
        # Get sky colors for this biome
        sky_colors = world.get_sky_color(primary_biome)
        sky_top = sky_colors[0]
        sky_horizon = sky_colors[1]
            
        # Draw sky gradient more efficiently (every 4 pixels)
        for y in range(0, SCREEN_HEIGHT, 4):
            # Calculate ratio (0 at top, 1 at horizon)
            t = min(1.0, y / (SCREEN_HEIGHT * 0.7))
            
            # Interpolate between top and horizon color
            r = int(sky_top[0] * (1-t) + sky_horizon[0] * t)
            g = int(sky_top[1] * (1-t) + sky_horizon[1] * t)
            b = int(sky_top[2] * (1-t) + sky_horizon[2] * t)
            
            # Draw horizontal rect instead of line (more efficient)
            pygame.draw.rect(self.background_surface, (r, g, b), (0, y, SCREEN_WIDTH, 4))
        
        # Add sun to the sky
        self._render_sun()
            
        # Clear other surfaces
        self.world_surface.fill((0, 0, 0, 0))
        self.entity_surface.fill((0, 0, 0, 0))
        self.ui_surface.fill((0, 0, 0, 0))
    
    def render_world(self, world: World) -> None:
        """
        Render the game world
        
        Args:
            world: The world to render
        """
        # Update chunk surfaces if needed
        for chunk in world.get_active_chunks():
            if chunk.needs_render_update or (chunk.x, chunk.y) not in self.chunk_surfaces:
                self._update_chunk_surface(chunk)
                chunk.needs_render_update = False
        
        # Render visible chunks
        for chunk in world.get_active_chunks():
            chunk_screen_x, chunk_screen_y = self.camera.world_to_screen(
                chunk.x * CHUNK_SIZE, chunk.y * CHUNK_SIZE
            )
            
            # Skip chunks that are completely off-screen
            if (chunk_screen_x + CHUNK_SIZE * TILE_SIZE < 0 or
                chunk_screen_x > SCREEN_WIDTH or
                chunk_screen_y + CHUNK_SIZE * TILE_SIZE < 0 or
                chunk_screen_y > SCREEN_HEIGHT):
                continue
            
            # Draw the chunk
            self.world_surface.blit(self.chunk_surfaces[(chunk.x, chunk.y)], (chunk_screen_x, chunk_screen_y))
    
    def _update_chunk_surface(self, chunk) -> None:
        """
        Update the cached surface for a chunk
        
        Args:
            chunk: The chunk to update
        """
        # Create or reuse a surface for this chunk
        if (chunk.x, chunk.y) not in self.chunk_surfaces:
            # Create a smaller surface for better performance
            self.chunk_surfaces[(chunk.x, chunk.y)] = pygame.Surface(
                (CHUNK_SIZE * TILE_SIZE, CHUNK_SIZE * TILE_SIZE), pygame.SRCALPHA
            )
        
        # Fill with appropriate colors
        surface = self.chunk_surfaces[(chunk.x, chunk.y)]
        surface.fill((0, 0, 0, 0))  # Clear with transparency
        
        # First render the background blocks
        for y in range(CHUNK_SIZE):
            for x in range(CHUNK_SIZE):
                background_material = chunk.get_block(x, y, BlockType.BACKGROUND)
                
                # Skip void/air backgrounds
                if background_material == MaterialType.VOID or background_material == MaterialType.AIR:
                    continue
                
                # Get background material color (darker version of the regular color)
                bg_color = BACKGROUND_COLORS.get(background_material, BLACK)
                
                # Draw the background tile with alpha for depth effect
                rect = (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                
                # Apply semi-transparency for background blocks
                if isinstance(bg_color, tuple):
                    if len(bg_color) == 3:
                        bg_color = bg_color + (180,)  # Add alpha
                    elif len(bg_color) == 4:
                        r, g, b, a = bg_color
                        bg_color = (r, g, b, min(a, 180))  # Limit alpha
                
                pygame.draw.rect(surface, bg_color, rect)
        
        # Now render the foreground blocks
        for y in range(CHUNK_SIZE):
            for x in range(CHUNK_SIZE):
                foreground_material = chunk.get_block(x, y, BlockType.FOREGROUND)
                
                # Skip drawing air for performance
                if foreground_material == MaterialType.AIR:
                    continue
                
                # Get material color
                color = MATERIAL_COLORS.get(foreground_material, BLACK)
                
                # Add subtle color variation for natural materials to create more visual interest
                # We don't use random here to keep the variations consistent
                world_x = chunk.x * CHUNK_SIZE + x
                world_y = chunk.y * CHUNK_SIZE + y
                variation_seed = (world_x * 17 + world_y * 31) % 30 - 15  # -15 to +15 range
                
                # Apply variation to natural materials
                if foreground_material in [
                    MaterialType.DIRT_LIGHT, MaterialType.DIRT_MEDIUM, MaterialType.DIRT_DARK,
                    MaterialType.STONE_LIGHT, MaterialType.STONE_MEDIUM, MaterialType.STONE_DARK,
                    MaterialType.DEEP_STONE_LIGHT, MaterialType.DEEP_STONE_MEDIUM, MaterialType.DEEP_STONE_DARK,
                    MaterialType.SAND_LIGHT, MaterialType.SAND_DARK,
                    MaterialType.GRAVEL_LIGHT, MaterialType.GRAVEL_DARK,
                    MaterialType.GRASS_LIGHT, MaterialType.GRASS_MEDIUM, MaterialType.GRASS_DARK,
                    MaterialType.CLAY_LIGHT, MaterialType.CLAY_DARK
                ]:
                    if isinstance(color, tuple) and len(color) >= 3:
                        r = max(0, min(255, color[0] + variation_seed))
                        g = max(0, min(255, color[1] + variation_seed))
                        b = max(0, min(255, color[2] + variation_seed))
                        
                        if len(color) == 4:  # With alpha
                            color = (r, g, b, color[3])
                        else:
                            color = (r, g, b)
                
                # Draw the foreground tile
                rect = (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(surface, color, rect)
                
                # Add edge highlights/shadows for non-air tiles to create a more 3D effect
                if foreground_material != MaterialType.AIR:
                    # Check adjacent tiles
                    has_air_above = y > 0 and chunk.get_block(x, y-1, BlockType.FOREGROUND) == MaterialType.AIR
                    has_air_below = y < CHUNK_SIZE-1 and chunk.get_block(x, y+1, BlockType.FOREGROUND) == MaterialType.AIR
                    has_air_left = x > 0 and chunk.get_block(x-1, y, BlockType.FOREGROUND) == MaterialType.AIR
                    has_air_right = x < CHUNK_SIZE-1 and chunk.get_block(x+1, y, BlockType.FOREGROUND) == MaterialType.AIR
                    
                    # Add subtle edge highlights/shadows
                    if has_air_above:
                        pygame.draw.line(surface, (255, 255, 255, 60), 
                                        (x * TILE_SIZE, y * TILE_SIZE), 
                                        ((x+1) * TILE_SIZE, y * TILE_SIZE))
                    
                    if has_air_below:
                        pygame.draw.line(surface, (0, 0, 0, 60), 
                                        (x * TILE_SIZE, (y+1) * TILE_SIZE), 
                                        ((x+1) * TILE_SIZE, (y+1) * TILE_SIZE))
                    
                    if has_air_left:
                        pygame.draw.line(surface, (255, 255, 255, 40), 
                                        (x * TILE_SIZE, y * TILE_SIZE), 
                                        (x * TILE_SIZE, (y+1) * TILE_SIZE))
                    
                    if has_air_right:
                        pygame.draw.line(surface, (0, 0, 0, 40), 
                                        ((x+1) * TILE_SIZE, y * TILE_SIZE), 
                                        ((x+1) * TILE_SIZE, (y+1) * TILE_SIZE))
    
    def render_player(self, player: Player) -> None:
        """
        Render the player and their staff drill with voxel art style
        
        Args:
            player: The player entity to render
        """
        # Track this player in the entity list for future reference
        if player not in self.entities:
            self.entities.append(player)
            
        # Create or update player sprites if needed
        if self.player_sprite['idle'] is None:
            self.player_sprite['idle'] = self._create_player_sprite((210, 160, 120))
            self.player_sprite['dig'] = self._create_player_sprite((220, 170, 140))
        
        # Get screen coordinates
        screen_x, screen_y = self.camera.world_to_screen(player.x, player.y)
        
        # Calculate player dimensions in pixels
        width_px = int(player.width * TILE_SIZE)
        height_px = int(player.height * TILE_SIZE)
        
        # Calculate player center
        player_center_x = screen_x + width_px // 2
        player_center_y = screen_y + height_px // 2
        
        # Choose sprite based on player state
        sprite = self.player_sprite['idle']
        if player.dig_animation_active:
            sprite = self.player_sprite['dig']
        
        # Flip sprite if facing left
        face_left = player.drill_angle > math.pi/2 or player.drill_angle < -math.pi/2
        if face_left:
            sprite = pygame.transform.flip(sprite, True, False)
            player.facing_right = False
        else:
            player.facing_right = True
        
        # Scale sprite to match player size (only if needed)
        if sprite.get_width() != width_px or sprite.get_height() != height_px:
            sprite = pygame.transform.scale(sprite, (width_px, height_px))
        
        # Draw player sprite
        self.entity_surface.blit(sprite, (screen_x, screen_y))
        
        # Render the staff-drill in voxel style
        staff_length_px = int(player.drill_length * TILE_SIZE)
        staff_width_px = max(2, int(player.drill_width * TILE_SIZE))
        
        # Get staff colors from player, or use defaults
        staff_color = getattr(player, 'staff_color', (120, 80, 40))
        drill_tip_color = getattr(player, 'drill_tip_color', (220, 220, 240))
        
        # Calculate staff and drill tip positions
        staff_end_x = player_center_x + int(math.cos(player.drill_angle) * staff_length_px * 0.75)
        staff_end_y = player_center_y + int(math.sin(player.drill_angle) * staff_length_px * 0.75)
        
        drill_end_x = player_center_x + int(math.cos(player.drill_angle) * staff_length_px)
        drill_end_y = player_center_y + int(math.sin(player.drill_angle) * staff_length_px)
        
        # Draw staff with voxel-style segments
        voxel_size = max(2, int(staff_width_px * 0.7))  # Size of each voxel
        
        # Staff connecting points along the path
        num_voxels = int(staff_length_px * 0.75 / voxel_size)
        
        # Draw wooden staff shaft with voxel style
        for i in range(num_voxels):
            # Position along staff
            t = i / num_voxels
            pos_x = int(player_center_x + math.cos(player.drill_angle) * staff_length_px * 0.75 * t)
            pos_y = int(player_center_y + math.sin(player.drill_angle) * staff_length_px * 0.75 * t)
            
            # Vary the staff color slightly for wood grain effect
            color_variation = random.randint(-15, 15)
            wood_color = (
                min(255, max(0, staff_color[0] + color_variation)),
                min(255, max(0, staff_color[1] + color_variation * 0.7)),
                min(255, max(0, staff_color[2] + color_variation * 0.5))
            )
            
            # Make the staff thinner at the end for better visual 
            segment_size = int(voxel_size * (1.0 - t * 0.3))
            if segment_size < 1:
                segment_size = 1
                
            # Draw the voxel
            pygame.draw.rect(
                self.entity_surface,
                wood_color,
                (pos_x - segment_size//2, pos_y - segment_size//2, 
                 segment_size, segment_size)
            )
            
            # Add decorative voxel wrappings at intervals
            if i > 0 and i % 4 == 0 and i < num_voxels - 2:
                wrap_color = (60, 40, 30)  # Dark leather wrap
                pygame.draw.rect(
                    self.entity_surface,
                    wrap_color,
                    (pos_x - segment_size//2 - 1, pos_y - segment_size//2 - 1, 
                     segment_size + 2, segment_size + 2)
                )
        
        # Draw drill mechanism with voxel style
        # Drill base connection
        drill_base_size = voxel_size * 2
        pygame.draw.rect(
            self.entity_surface,
            (80, 80, 100),  # Metallic color
            (staff_end_x - drill_base_size//2, staff_end_y - drill_base_size//2,
             drill_base_size, drill_base_size)
        )
        
        # Draw the drill tip with voxel design
        drill_active = player.dig_animation_active
        
        # Draw spinning drill head
        drill_radius = voxel_size * 1.5
        if drill_active:
            # Glowing active drill (brighter colors)
            spin_angle = (pygame.time.get_ticks() / 30) % (2 * math.pi)  # Faster spinning
            
            # Draw multiple rotating drill components
            for i in range(5):  # Multiple drill segments
                angle_offset = spin_angle + i * (2 * math.pi / 5)
                
                # Calculate positions for drill components
                dx = int(math.cos(angle_offset) * drill_radius)
                dy = int(math.sin(angle_offset) * drill_radius)
                
                # Draw glowing drill bits
                drill_bit_color = (
                    min(255, drill_tip_color[0] + 40),
                    min(255, drill_tip_color[1] + random.randint(0, 40)),
                    min(255, drill_tip_color[2] + random.randint(0, 30))
                )
                
                # Main drill component
                pygame.draw.rect(
                    self.entity_surface,
                    drill_bit_color,
                    (drill_end_x + dx - voxel_size//2, drill_end_y + dy - voxel_size//2,
                     voxel_size, voxel_size)
                )
                
                # Draw connecting piece
                pygame.draw.line(
                    self.entity_surface,
                    (160, 160, 180),
                    (drill_end_x, drill_end_y),
                    (drill_end_x + dx, drill_end_y + dy),
                    max(1, voxel_size // 3)
                )
        else:
            # Inactive drill (compact design)
            pygame.draw.rect(
                self.entity_surface,
                drill_tip_color,
                (drill_end_x - drill_radius, drill_end_y - drill_radius,
                 drill_radius * 2, drill_radius * 2)
            )
            
            # Drill detail
            inner_size = max(2, int(drill_radius * 0.6))
            pygame.draw.rect(
                self.entity_surface,
                (100, 100, 120),  # Darker inner color
                (drill_end_x - inner_size, drill_end_y - inner_size,
                 inner_size * 2, inner_size * 2)
            )
        
        # Add lights based on player state
        # Main player light
        self.light_system.add_light(
            player.x + player.width/2, 
            player.y + player.height/2, 
            20.0,  # Large light radius for good visibility
            (255, 235, 190),  # Warm light color
            2.0  # Higher intensity
        )
        
        # Add drill light when active
        if drill_active:
            # Calculate world space position for the drill tip
            drill_tip_x = player.x + player.width/2 + math.cos(player.drill_angle) * player.drill_length
            drill_tip_y = player.y + player.height/2 + math.sin(player.drill_angle) * player.drill_length
            
            # Flickering hot drill light
            self.light_system.add_light(
                drill_tip_x,
                drill_tip_y,
                8.0,  # Larger radius
                (255, 150, 50),  # Orange light
                1.5,  # Brightness
                "fire"  # Flickering type
            )
            
            # Focused core drill light
            self.light_system.add_light(
                drill_tip_x,
                drill_tip_y,
                3.0,  # Small focused light
                (255, 220, 180),  # Hot white-orange
                2.0,  # Very bright
                "point"
            )
            
            # Create drill particles at the tip for active drilling
            if random.random() < 0.3:  # Only some frames for performance
                for _ in range(3):  # Limited particle count
                    # Directional spray of particles
                    spread = 0.6  # Narrower spread
                    particle_angle = player.drill_angle + math.pi + random.uniform(-spread, spread)
                    speed = random.uniform(0.3, 0.6)
                    
                    # Pre-calculated colors for better performance
                    color_idx = min(len(self.particle_presets['dig_dust'])-1, 
                                  int(random.random() * len(self.particle_presets['dig_dust'])))
                    
                    self.particle_system.add_particle({
                        'x': drill_tip_x,
                        'y': drill_tip_y,
                        'vx': math.cos(particle_angle) * speed,
                        'vy': math.sin(particle_angle) * speed,
                        'life': random.randint(15, 25),
                        'color': self.particle_presets['dig_dust'][color_idx],
                        'size': random.uniform(0.3, 0.5)
                    })
        
        # Render optimized particle effects for player
        self._render_player_particles(player)
        
        # Render pure particle-based jetpack effect (no triangle)
        if player.jetpack_active and player.jetpack_fuel > 0:
            self._render_jetpack_particles(player, screen_x, screen_y, width_px, height_px)
    
    def _render_player_particles(self, player: Player) -> None:
        """
        Render player particles with optimized drawing
        
        Args:
            player: The player entity
        """
        # Skip if no particles
        if not player.trail_particles:
            return
            
        # Batch similar particles together for faster rendering
        # Group by size for more efficient drawing
        particle_batches = {}
        
        for particle in player.trail_particles:
            # Get screen coordinates
            screen_x, screen_y = self.camera.world_to_screen(particle['x'], particle['y'])
            
            # Skip if offscreen
            if (screen_x < -10 or screen_x > SCREEN_WIDTH + 10 or
                screen_y < -10 or screen_y > SCREEN_HEIGHT + 10):
                continue
                
            # Calculate particle size in pixels
            size = max(1, int(particle['size'] * TILE_SIZE))
            
            # Create batch key based on size
            batch_key = size
            
            # Add to appropriate batch
            if batch_key not in particle_batches:
                particle_batches[batch_key] = []
            
            # Store screen coordinates and color
            particle_batches[batch_key].append((
                int(screen_x), 
                int(screen_y), 
                particle['color']
            ))
        
        # Draw each batch of particles
        for size, particles in particle_batches.items():
            if size <= 1:
                # Draw single pixels efficiently
                for x, y, color in particles:
                    if 0 <= x < SCREEN_WIDTH and 0 <= y < SCREEN_HEIGHT:
                        self.entity_surface.set_at((x, y), color)
            else:
                # Draw circles
                for x, y, color in particles:
                    pygame.draw.circle(
                        self.entity_surface, 
                        color, 
                        (x, y), 
                        size
                    )
    
    def _render_jetpack_particles(self, player: Player, screen_x: int, screen_y: int, 
                                width_px: int, height_px: int) -> None:
        """
        Render particle-based jetpack effects
        
        Args:
            player: The player entity
            screen_x: Player's screen x coordinate
            screen_y: Player's screen y coordinate
            width_px: Player width in pixels
            height_px: Player height in pixels
        """
        # Calculate jetpack position relative to player
        jetpack_x = screen_x + width_px // 2
        jetpack_y = screen_y + height_px
        
        # Create varied particles for flame effect
        for _ in range(4):  # Use fewer particles for performance
            # Randomize particle parameters
            offset_x = random.uniform(-width_px/4, width_px/4)
            size = random.uniform(0.4, 0.8)
            
            # Determine particle speed based on position (center particles faster)
            center_factor = 1.0 - (abs(offset_x) / (width_px/4))
            speed_y = random.uniform(0.4, 0.8) * center_factor
            speed_x = random.uniform(-0.1, 0.1)
            
            # Vary particle color based on position in flame
            if abs(offset_x) < width_px/8:  # Central particles are hotter
                color_key = 'jetpack_core'
            else:  # Outer particles are cooler
                color_key = 'jetpack_flame'
            
            # Get color from presets for efficiency
            color_idx = min(len(self.particle_presets[color_key])-1, 
                          int(random.random() * len(self.particle_presets[color_key])))
            color = self.particle_presets[color_key][color_idx]
            
            # Convert screen position to world coordinates
            world_x, world_y = self.camera.screen_to_world(
                jetpack_x + offset_x, 
                jetpack_y
            )
            
            # Add the particle
            self.particle_system.add_particle({
                'x': world_x,
                'y': world_y,
                'vx': speed_x,
                'vy': speed_y,
                'life': random.randint(10, 20),
                'color': color,
                'size': size
            })
        
        # Add a light at the jetpack position
        self.light_system.add_light(
            player.x + player.width/2,
            player.y + player.height + 1,
            5.0,  # Larger light radius
            (255, 150, 50),  # Orange flame color
            1.2  # Higher intensity
        )
        
    def render_ui(self, player: Player) -> None:
        """
        Render the game UI
        
        Args:
            player: The player entity
        """
        # Draw jetpack fuel bar
        bar_width = 100
        bar_height = 10
        bar_x = 20
        bar_y = 20
        
        # Bar outline
        pygame.draw.rect(self.ui_surface, (100, 100, 100), (bar_x - 2, bar_y - 2, bar_width + 4, bar_height + 4))
        
        # Bar background
        pygame.draw.rect(self.ui_surface, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
        
        # Bar fill
        fill_width = int((player.jetpack_fuel / PLAYER_JETPACK_MAX_FUEL) * bar_width)
        
        # Gradient color based on fuel level
        if player.jetpack_fuel > PLAYER_JETPACK_MAX_FUEL * 0.6:
            fuel_color = (100, 200, 50)  # Green for high fuel
        elif player.jetpack_fuel > PLAYER_JETPACK_MAX_FUEL * 0.3:
            fuel_color = (200, 200, 50)  # Yellow for medium fuel
        else:
            # Flashing red for low fuel
            if pygame.time.get_ticks() % 1000 < 500:
                fuel_color = (220, 100, 50)  # Bright red
            else:
                fuel_color = (180, 80, 40)  # Darker red
        
        pygame.draw.rect(self.ui_surface, fuel_color, (bar_x, bar_y, fill_width, bar_height))
        
        # Jetpack label
        fuel_text = self.font.render("Jetpack", True, (255, 255, 255))
        self.ui_surface.blit(fuel_text, (bar_x, bar_y - 20))
        
        # Draw FPS counter
        if self.show_debug:
            fps_text = self.font.render(f"FPS: {self.fps_display:.1f}", True, (255, 255, 255))
            self.ui_surface.blit(fps_text, (SCREEN_WIDTH - 100, 20))
            
            # Draw player position
            pos_text = self.font.render(f"Pos: ({int(player.x)}, {int(player.y)})", True, (255, 255, 255))
            self.ui_surface.blit(pos_text, (SCREEN_WIDTH - 150, 40))
            
            # Draw controls hint
            controls_text = self.font.render("WASD: Move | SPACE: Jump/Jetpack | CTRL: Dig", True, (200, 200, 200))
            self.ui_surface.blit(controls_text, (20, SCREEN_HEIGHT - 30))
    
    def update_camera(self, player: Player) -> None:
        """
        Update the camera to follow the player
        
        Args:
            player: The player to follow
        """
        self.camera.follow(player.x + player.width / 2, player.y + player.height / 2)
    
    def flip(self) -> None:
        """Update the display and measure FPS"""
        # Composite all layers
        self.screen.blit(self.background_surface, (0, 0))
        self.screen.blit(self.sky_objects_surface, (0, 0))  # Add sun and sky objects
        self.screen.blit(self.world_surface, (0, 0))
        self.light_system.render(self.screen)  # Apply lighting
        self.screen.blit(self.entity_surface, (0, 0))
        self.particle_system.render(self.screen)  # Render particles
        self.screen.blit(self.ui_surface, (0, 0))
        
        # Update display efficiently
        pygame.display.flip()
        
        # Use tick_busy_loop for more accurate timing
        dt = self.clock.tick_busy_loop(FPS) / 1000.0  # Time since last frame in seconds
        
        # Keep a running average of frame times
        self.frame_times.append(dt)
        if len(self.frame_times) > 30:
            self.frame_times.pop(0)
        
        # Update FPS display every 30 frames
        self.fps_update_timer += 1
        if self.fps_update_timer >= 30:
            if self.frame_times:
                avg_frame_time = sum(self.frame_times) / len(self.frame_times)
                self.fps_display = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
            self.fps_update_timer = 0
        
        # Clear dynamic effects for next frame
        self.light_system.clear_lights()
        self.particle_system.update()
    
    def cleanup(self) -> None:
        """Clean up resources"""
        pygame.quit()
        
    def toggle_debug(self) -> None:
        """Toggle debug information display"""
        self.show_debug = not self.show_debug