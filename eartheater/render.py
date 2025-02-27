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
        
        # Create player sprites
        self.player_sprite = {
            'idle': self._create_player_sprite((64, 100, 220)),
            'dig': self._create_player_sprite((220, 100, 64))
        }
        
        # Sun position
        self.sun_x = SCREEN_WIDTH * 0.75
        self.sun_y = SCREEN_HEIGHT * 0.25
        self.time_of_day = 0  # 0 to 1, representing time of day
        
        # Debug overlay
        self.show_debug = False
    
    def _create_player_sprite(self, color: Tuple[int, int, int]) -> pygame.Surface:
        """
        Create a simple player sprite
        
        Args:
            color: Base color for the sprite
            
        Returns:
            Surface with the player sprite
        """
        # Create a surface for the sprite
        width = int(2 * TILE_SIZE)
        height = int(3 * TILE_SIZE)
        sprite = pygame.Surface((width, height), pygame.SRCALPHA)
        
        # Draw a simple alien character
        # Body
        pygame.draw.ellipse(sprite, color, (0, height//3, width, height*2//3))
        
        # Head
        pygame.draw.ellipse(sprite, color, (width//4, 0, width//2, height//2))
        
        # Eyes
        eye_color = (255, 255, 255)
        pygame.draw.circle(sprite, eye_color, (width//3, height//4), width//10)
        pygame.draw.circle(sprite, eye_color, (width*2//3, height//4), width//10)
        
        # Pupils
        pygame.draw.circle(sprite, (0, 0, 0), (width//3, height//4), width//20)
        pygame.draw.circle(sprite, (0, 0, 0), (width*2//3, height//4), width//20)
        
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
        
        if camera_world_y < 70:  # Above ground 
            # Get sky colors for this biome
            sky_colors = world.get_sky_color(primary_biome)
            sky_top = sky_colors[0]
            sky_horizon = sky_colors[1]
            
            # Draw sky gradient
            for y in range(SCREEN_HEIGHT):
                # Calculate ratio (0 at top, 1 at horizon)
                t = min(1.0, y / (SCREEN_HEIGHT * 0.7))
                
                # Interpolate between top and horizon color
                r = int(sky_top[0] * (1-t) + sky_horizon[0] * t)
                g = int(sky_top[1] * (1-t) + sky_horizon[1] * t)
                b = int(sky_top[2] * (1-t) + sky_horizon[2] * t)
                
                # Draw horizontal line
                pygame.draw.line(self.background_surface, (r, g, b), (0, y), (SCREEN_WIDTH, y))
            
            # Add sun to the sky
            self._render_sun()
        else:
            # # Underground - biome-specific dark background
            # if primary_biome in [BiomeType.UNDERGROUND, BiomeType.DEPTHS, BiomeType.ABYSS, BiomeType.VOLCANIC]:
            #     # Get darker underground colors for this biome
            #     if primary_biome in BIOME_SKY_COLORS:
            #         underground_color = BIOME_SKY_COLORS[primary_biome]['top']
            #     else:
            #         underground_color = UNDERGROUND_COLOR
            # else:
            # Default underground color
            underground_color = UNDERGROUND_COLOR
            
            self.background_surface.fill(underground_color)
            
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
            if chunk.needs_update or (chunk.x, chunk.y) not in self.chunk_surfaces:
                self._update_chunk_surface(chunk)
                chunk.needs_update = False
        
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
            self.chunk_surfaces[(chunk.x, chunk.y)] = pygame.Surface(
                (CHUNK_SIZE * TILE_SIZE, CHUNK_SIZE * TILE_SIZE), pygame.HWSURFACE | pygame.SRCALPHA
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
        Render the player and their drill
        
        Args:
            player: The player entity to render
        """
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
        
        # Scale sprite to match player size
        sprite = pygame.transform.scale(sprite, (width_px, height_px))
        
        # Draw player sprite
        self.entity_surface.blit(sprite, (screen_x, screen_y))
        
        # Draw the drill with improved visuals
        drill_length_px = int(player.drill_length * TILE_SIZE)
        drill_width_px = int(player.drill_width * TILE_SIZE)
        
        # Calculate drill end point
        drill_end_x = player_center_x + int(math.cos(player.drill_angle) * drill_length_px)
        drill_end_y = player_center_y + int(math.sin(player.drill_angle) * drill_length_px)
        
        # Draw drill base with animation effects
        if player.dig_animation_active:
            # Active drill with pulsing hot colors and random variation
            base_r = 230
            base_g = 50 + random.randint(0, 30)
            base_b = 20 + random.randint(0, 20)
            drill_color = (base_r, base_g, base_b)
            
            # Draw energy glow around drill when active
            glow_radius = drill_width_px * 3
            for r in range(glow_radius, 0, -2):
                # Fade out glow
                alpha = 150 * (r / glow_radius)
                glow_color = (255, 150, 50, alpha)
                pygame.draw.circle(
                    self.entity_surface,
                    glow_color,
                    (drill_end_x, drill_end_y),
                    r
                )
        else:
            # Normal drill color (metallic gray with slight blue tint)
            drill_color = (180, 180, 200)
        
        # Draw drill shaft with segment marks for mechanical look
        num_segments = 5
        for i in range(num_segments):
            start_pct = i / num_segments
            end_pct = (i + 1) / num_segments
            
            segment_start_x = player_center_x + int(math.cos(player.drill_angle) * drill_length_px * start_pct)
            segment_start_y = player_center_y + int(math.sin(player.drill_angle) * drill_length_px * start_pct)
            segment_end_x = player_center_x + int(math.cos(player.drill_angle) * drill_length_px * end_pct)
            segment_end_y = player_center_y + int(math.sin(player.drill_angle) * drill_length_px * end_pct)
            
            # Alternate segment colors for mechanical look
            segment_color = drill_color if i % 2 == 0 else (min(drill_color[0]-20, 255), min(drill_color[1]-20, 255), min(drill_color[2]-20, 255))
            
            pygame.draw.line(
                self.entity_surface,
                segment_color,
                (segment_start_x, segment_start_y),
                (segment_end_x, segment_end_y),
                drill_width_px
            )
        
        # Draw drill tip - larger when active
        tip_radius = drill_width_px + (2 if player.dig_animation_active else 1)
        tip_color = (150, 150, 160) if not player.dig_animation_active else (255, 100, 50)
        
        pygame.draw.circle(
            self.entity_surface,
            tip_color, 
            (drill_end_x, drill_end_y),
            tip_radius
        )
        
        # Add mechanical details to drill tip when active
        if player.dig_animation_active:
            # Draw spinning drill blades
            spin_angle = (pygame.time.get_ticks() / 50) % (2 * math.pi)  # Rotating effect
            for i in range(4):  # 4 blades
                blade_angle = spin_angle + (i * math.pi / 2)
                blade_length = tip_radius * 1.2
                
                blade_end_x = drill_end_x + int(math.cos(blade_angle) * blade_length)
                blade_end_y = drill_end_y + int(math.sin(blade_angle) * blade_length)
                
                pygame.draw.line(
                    self.entity_surface,
                    (220, 220, 240),
                    (drill_end_x, drill_end_y),
                    (blade_end_x, blade_end_y),
                    2
                )
        
        # Add a light source at the player position
        self.light_system.add_light(
            player.x + player.width/2, 
            player.y + player.height/2, 
            20.0,  # Much larger light radius for better visibility
            (255, 235, 190),  # Warmer light color
            2.0  # Higher intensity for brighter light
        )
        
        # Add a drill light when active
        if player.dig_animation_active:
            # Calculate drill tip position in world space
            drill_tip_x = player.x + player.width/2 + math.cos(player.drill_angle) * player.drill_length
            drill_tip_y = player.y + player.height/2 + math.sin(player.drill_angle) * player.drill_length
            
            # Add a more intense flickering fire-type light at the drill tip
            self.light_system.add_light(
                drill_tip_x,
                drill_tip_y,
                8.0,  # Larger radius for more dramatic effect
                (255, 150, 50),  # Orange/yellow light for drilling
                2.0,  # Higher intensity
                "fire"  # Use flickering fire type
            )
            
            # Add a second, smaller more intense light for the hot drill tip
            self.light_system.add_light(
                drill_tip_x,
                drill_tip_y,
                3.0,  # Very small focused light
                (255, 220, 180),  # Whiter/hotter center
                2.5,  # Very bright
                "point"
            )
        
        # Render player particles
        for particle in player.trail_particles:
            screen_particle_x, screen_particle_y = self.camera.world_to_screen(
                particle['x'], particle['y']
            )
            
            # Calculate particle size in pixels
            size = int(particle['size'] * TILE_SIZE)
            if size < 1:
                size = 1
            
            # Draw particle
            if size <= 1:
                if 0 <= screen_particle_x < SCREEN_WIDTH and 0 <= screen_particle_y < SCREEN_HEIGHT:
                    self.entity_surface.set_at((int(screen_particle_x), int(screen_particle_y)), particle['color'])
            else:
                pygame.draw.circle(self.entity_surface, particle['color'], 
                                (int(screen_particle_x), int(screen_particle_y)), size)
        
        # Render jetpack flame when active
        if player.jetpack_active and player.jetpack_fuel > 0:
            flame_x = screen_x + width_px // 2
            flame_y = screen_y + height_px
            
            # Draw flame as a triangle
            flame_height = random.randint(10, 15)
            points = [
                (flame_x, flame_y),
                (flame_x - 5, flame_y + flame_height),
                (flame_x + 5, flame_y + flame_height)
            ]
            
            # Outer flame (yellowish)
            pygame.draw.polygon(self.entity_surface, (255, 200, 50), points)
            
            # Inner flame (white)
            inner_points = [
                (flame_x, flame_y + 2),
                (flame_x - 2, flame_y + flame_height - 4),
                (flame_x + 2, flame_y + flame_height - 4)
            ]
            pygame.draw.polygon(self.entity_surface, (255, 255, 200), inner_points)
            
            # Add a light for the flame
            self.light_system.add_light(
                player.x + player.width/2,
                player.y + player.height + 1,
                3.0,  # Smaller light radius
                (255, 150, 50),  # Orange flame color
                0.8  # Intensity
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
        fill_width = int((player.jetpack_fuel / 100.0) * bar_width)
        pygame.draw.rect(self.ui_surface, (200, 200, 50), (bar_x, bar_y, fill_width, bar_height))
        
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
        
        # Calculate and display FPS, use busy loop for better timing precision
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