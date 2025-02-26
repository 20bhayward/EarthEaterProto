"""
Rendering system for EarthEater
"""
import pygame
from typing import Tuple

from eartheater.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, BLACK, BLUE,
    MaterialType, MATERIAL_COLORS, CHUNK_SIZE
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
    
    def follow(self, target_x: float, target_y: float) -> None:
        """
        Update camera position to follow a target
        
        Args:
            target_x: Target x-coordinate in world space
            target_y: Target y-coordinate in world space
        """
        # Center camera on target
        self.x = int(target_x * TILE_SIZE - self.width / 2)
        self.y = int(target_y * TILE_SIZE - self.height / 2)
    
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


class Renderer:
    """Handles rendering the game world and entities"""
    
    def __init__(self):
        """Initialize the renderer"""
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("EarthEater")
        self.clock = pygame.time.Clock()
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)
        
        # Create chunk surface cache
        self.chunk_surfaces = {}
    
    def clear(self) -> None:
        """Clear the screen"""
        self.screen.fill(BLACK)
    
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
            self.screen.blit(self.chunk_surfaces[(chunk.x, chunk.y)], (chunk_screen_x, chunk_screen_y))
    
    def _update_chunk_surface(self, chunk) -> None:
        """
        Update the cached surface for a chunk
        
        Args:
            chunk: The chunk to update
        """
        # Create or reuse a surface for this chunk
        if (chunk.x, chunk.y) not in self.chunk_surfaces:
            self.chunk_surfaces[(chunk.x, chunk.y)] = pygame.Surface(
                (CHUNK_SIZE * TILE_SIZE, CHUNK_SIZE * TILE_SIZE)
            )
        
        # Fill with appropriate colors
        surface = self.chunk_surfaces[(chunk.x, chunk.y)]
        
        for y in range(CHUNK_SIZE):
            for x in range(CHUNK_SIZE):
                material = chunk.get_tile(x, y)
                color = MATERIAL_COLORS.get(material, BLACK)
                
                # Skip drawing air for performance
                if material == MaterialType.AIR:
                    continue
                
                pygame.draw.rect(
                    surface,
                    color,
                    (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                )
    
    def render_player(self, player: Player) -> None:
        """
        Render the player
        
        Args:
            player: The player entity to render
        """
        # Get screen coordinates
        screen_x, screen_y = self.camera.world_to_screen(player.x, player.y)
        
        # Draw player as a rectangle
        width_px = int(player.width * TILE_SIZE)
        height_px = int(player.height * TILE_SIZE)
        pygame.draw.rect(self.screen, BLUE, (screen_x, screen_y, width_px, height_px))
    
    def update_camera(self, player: Player) -> None:
        """
        Update the camera to follow the player
        
        Args:
            player: The player to follow
        """
        self.camera.follow(player.x + player.width / 2, player.y + player.height / 2)
    
    def flip(self) -> None:
        """Update the display"""
        pygame.display.flip()
        self.clock.tick(60)
    
    def cleanup(self) -> None:
        """Clean up resources"""
        pygame.quit()