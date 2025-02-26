"""
UI components for Barren game
"""
import pygame
import math
import random
from typing import List, Tuple, Dict, Any, Optional, Callable

from eartheater.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, BLACK
)

class Effect:
    """Base class for visual effects"""
    def __init__(self, duration: int = -1):
        """Initialize effect with optional duration
        
        Args:
            duration: Effect duration in frames (-1 for infinite)
        """
        self.duration = duration
        self.elapsed = 0
        self.active = True
    
    def update(self) -> None:
        """Update effect state"""
        if self.duration > 0:
            self.elapsed += 1
            if self.elapsed >= self.duration:
                self.active = False
    
    def render(self, surface: pygame.Surface) -> None:
        """Render effect to surface
        
        Args:
            surface: Surface to render to
        """
        pass

class ParticleEffect(Effect):
    """Particle system visual effect"""
    def __init__(self, 
                 count: int, 
                 pos: Tuple[int, int],
                 velocity_range: Tuple[float, float],
                 size_range: Tuple[float, float],
                 color: Tuple[int, int, int],
                 gravity: float = 0.0,
                 duration: int = 120):
        """Initialize particle effect
        
        Args:
            count: Number of particles
            pos: Position (x, y) for emission
            velocity_range: (min, max) velocity magnitude
            size_range: (min, max) particle size
            color: RGB color tuple
            gravity: Gravity effect on particles
            duration: Effect duration in frames
        """
        super().__init__(duration)
        self.particles: List[Dict[str, Any]] = []
        
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(velocity_range[0], velocity_range[1])
            size = random.uniform(size_range[0], size_range[1])
            life = random.randint(duration // 2, duration)
            
            self.particles.append({
                'x': pos[0],
                'y': pos[1],
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'size': size,
                'color': color,
                'life': life,
                'max_life': life
            })
        
        self.gravity = gravity
    
    def update(self) -> None:
        """Update all particles"""
        super().update()
        
        for p in self.particles:
            # Apply gravity
            p['vy'] += self.gravity
            
            # Move particle
            p['x'] += p['vx']
            p['y'] += p['vy']
            
            # Reduce life
            p['life'] -= 1
            
            # Update size and opacity based on life
            life_ratio = p['life'] / p['max_life']
            p['size'] *= 0.99
            p['alpha'] = int(255 * life_ratio)
        
        # Remove dead particles
        self.particles = [p for p in self.particles if p['life'] > 0]
        
        # Deactivate if all particles are gone
        if not self.particles:
            self.active = False
    
    def render(self, surface: pygame.Surface) -> None:
        """Render all particles
        
        Args:
            surface: Surface to render to
        """
        for p in self.particles:
            # Skip if too small
            if p['size'] < 0.5:
                continue
                
            # Create color with alpha
            color = p['color'] + (p.get('alpha', 255),)
            
            # Draw particle
            if p['size'] <= 1:
                surface.set_at((int(p['x']), int(p['y'])), color)
            else:
                pygame.draw.circle(
                    surface,
                    color,
                    (int(p['x']), int(p['y'])),
                    int(p['size'])
                )

class TextEffect(Effect):
    """Animated text effect"""
    def __init__(self, 
                 text: str,
                 pos: Tuple[int, int],
                 color: Tuple[int, int, int],
                 font_size: int = 32,
                 duration: int = 120,
                 fade_in: int = 30,
                 fade_out: int = 30,
                 motion: str = "none"):
        """Initialize text effect
        
        Args:
            text: Text to display
            pos: Position (x, y) for text
            color: RGB color tuple
            font_size: Font size in pixels
            duration: Effect duration in frames
            fade_in: Frames for fade in
            fade_out: Frames for fade out
            motion: Motion type (none, float, pulse)
        """
        super().__init__(duration)
        self.text = text
        self.pos = list(pos)
        self.color = color
        self.font_size = font_size
        self.fade_in = fade_in
        self.fade_out = fade_out
        self.motion = motion
        
        # Initialize font
        self.font = pygame.font.Font(None, font_size)
        
        # For float motion
        self.offset = 0
        self.float_speed = 0.5
        self.float_amplitude = 10
    
    def update(self) -> None:
        """Update text effect"""
        super().update()
        
        # Handle motion
        if self.motion == "float":
            self.offset += self.float_speed
            self.pos[1] = self.pos[1] - 0.2  # Slowly rise
    
    def render(self, surface: pygame.Surface) -> None:
        """Render text effect
        
        Args:
            surface: Surface to render to
        """
        # Calculate alpha based on fade in/out
        alpha = 255
        if self.elapsed < self.fade_in:
            alpha = int(255 * (self.elapsed / self.fade_in))
        elif self.duration > 0 and self.elapsed > self.duration - self.fade_out:
            remaining = self.duration - self.elapsed
            alpha = int(255 * (remaining / self.fade_out))
        
        # Render the text
        text_surface = self.font.render(self.text, True, self.color)
        
        # Create a surface with alpha
        alpha_surface = pygame.Surface(text_surface.get_size(), pygame.SRCALPHA)
        alpha_surface.fill((255, 255, 255, alpha))
        
        # Blit with alpha
        text_surface.blit(alpha_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
        # Calculate position with motion
        x = self.pos[0] - text_surface.get_width() // 2
        y = self.pos[1] - text_surface.get_height() // 2
        
        if self.motion == "float":
            y += math.sin(self.offset * 0.1) * self.float_amplitude
        elif self.motion == "pulse":
            scale = 1.0 + 0.1 * math.sin(self.elapsed * 0.1)
            scaled_surface = pygame.transform.scale(
                text_surface, 
                (int(text_surface.get_width() * scale),
                 int(text_surface.get_height() * scale))
            )
            x = self.pos[0] - scaled_surface.get_width() // 2
            y = self.pos[1] - scaled_surface.get_height() // 2
            text_surface = scaled_surface
        
        # Draw the text
        surface.blit(text_surface, (x, y))

class Menu:
    """Game menu with animated background"""
    def __init__(self, title: str, options: List[str], callback: Callable[[int], None]):
        """Initialize menu
        
        Args:
            title: Menu title
            options: List of option texts
            callback: Function to call with selected option index
        """
        self.title = title
        self.options = options
        self.callback = callback
        self.selected = 0
        
        # Fonts
        self.title_font = pygame.font.Font(None, 80)
        self.option_font = pygame.font.Font(None, 40)
        
        # Effects
        self.effects: List[Effect] = []
        self.next_particle_time = 0
        
        # Create title particles
        for _ in range(20):
            self.add_random_particle()
    
    def add_random_particle(self) -> None:
        """Add a random particle effect"""
        x = random.randint(0, SCREEN_WIDTH)
        y = random.randint(0, SCREEN_HEIGHT)
        
        # Random size and velocity
        size = random.uniform(1, 3)
        velocity = random.uniform(0.2, 1.0)
        
        # Create particle
        self.effects.append(ParticleEffect(
            count=1,
            pos=(x, y),
            velocity_range=(velocity * 0.5, velocity),
            size_range=(size * 0.8, size * 1.2),
            color=(255, 255, 255),
            gravity=0.01,
            duration=200
        ))
    
    def update(self) -> None:
        """Update menu state"""
        # Update effects
        for effect in self.effects[:]:
            effect.update()
            if not effect.active:
                self.effects.remove(effect)
        
        # Add new particles periodically
        self.next_particle_time -= 1
        if self.next_particle_time <= 0:
            self.add_random_particle()
            self.next_particle_time = random.randint(5, 15)
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle input event
        
        Args:
            event: Pygame event
            
        Returns:
            True if menu was closed, False otherwise
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.options)
                return False
            elif event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.options)
                return False
            elif event.key == pygame.K_RETURN:
                self.callback(self.selected)
                return True
        
        return False
    
    def render(self, surface: pygame.Surface) -> None:
        """Render menu
        
        Args:
            surface: Surface to render to
        """
        # Fill background
        surface.fill(BLACK)
        
        # Render effects
        for effect in self.effects:
            effect.render(surface)
        
        # Render title
        title_surface = self.title_font.render(self.title, True, WHITE)
        title_x = (SCREEN_WIDTH - title_surface.get_width()) // 2
        title_y = SCREEN_HEIGHT // 4
        surface.blit(title_surface, (title_x, title_y))
        
        # Render options
        option_y = SCREEN_HEIGHT // 2
        for i, option in enumerate(self.options):
            # Highlight selected option
            color = WHITE
            prefix = ""
            if i == self.selected:
                prefix = "> "
                # Pulse effect for selected option
                pulse = abs(math.sin(pygame.time.get_ticks() * 0.005)) * 0.5 + 0.5
                color = (255, int(200 + 55 * pulse), int(200 + 55 * pulse))
            
            # Render option
            option_surface = self.option_font.render(prefix + option, True, color)
            option_x = (SCREEN_WIDTH - option_surface.get_width()) // 2
            surface.blit(option_surface, (option_x, option_y))
            option_y += 50

class LoadingScreen:
    """Loading screen with progress bar"""
    def __init__(self, callback: Callable[[], None]):
        """Initialize loading screen
        
        Args:
            callback: Function to call when loading is done
        """
        self.callback = callback
        self.progress = 0.0
        self.target_progress = 0.0
        self.messages = [
            "Generating terrain...",
            "Digging caves...",
            "Adding resources...",
            "Calculating physics...",
            "Initializing drill systems...",
            "Calibrating jetpack...",
            "Ready to explore the Barren!"
        ]
        self.current_message = 0
        self.message_timer = 0
        
        # Font
        self.font = pygame.font.Font(None, 32)
        
        # Effects
        self.effects: List[Effect] = []
        
        # Add title effect
        self.effects.append(TextEffect(
            text="BARREN",
            pos=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4),
            color=WHITE,
            font_size=100,
            duration=-1,
            motion="pulse"
        ))
    
    def set_progress(self, progress: float) -> None:
        """Set current progress
        
        Args:
            progress: Progress value (0.0 to 1.0)
        """
        self.target_progress = progress
        
        # Update messages based on progress
        if progress > 0.15 and self.current_message == 0:
            self.advance_message()
        elif progress > 0.3 and self.current_message == 1:
            self.advance_message()
        elif progress > 0.5 and self.current_message == 2:
            self.advance_message()
        elif progress > 0.7 and self.current_message == 3:
            self.advance_message()
        elif progress > 0.85 and self.current_message == 4:
            self.advance_message()
        elif progress > 0.95 and self.current_message == 5:
            self.advance_message()
    
    def advance_message(self) -> None:
        """Advance to next loading message"""
        self.current_message += 1
        if self.current_message >= len(self.messages):
            self.current_message = len(self.messages) - 1
        
        # Add floating message effect
        self.effects.append(TextEffect(
            text=self.messages[self.current_message - 1] + " ✓",
            pos=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100),
            color=(100, 255, 100),
            font_size=24,
            duration=120,
            fade_in=10,
            fade_out=30,
            motion="float"
        ))
        
        # Reset message timer
        self.message_timer = 30
    
    def update(self) -> None:
        """Update loading screen state"""
        # Smoothly approach target progress
        if self.progress < self.target_progress:
            self.progress += min(0.01, self.target_progress - self.progress)
        
        # Complete loading when done
        if self.progress >= 1.0 and self.message_timer <= 0:
            self.callback()
        
        # Update message timer
        if self.message_timer > 0:
            self.message_timer -= 1
        
        # Update effects
        for effect in self.effects[:]:
            effect.update()
            if not effect.active:
                self.effects.remove(effect)
    
    def render(self, surface: pygame.Surface) -> None:
        """Render loading screen
        
        Args:
            surface: Surface to render to
        """
        # Fill background
        surface.fill(BLACK)
        
        # Render effects
        for effect in self.effects:
            effect.render(surface)
        
        # Render progress bar
        bar_width = SCREEN_WIDTH * 0.6
        bar_height = 20
        bar_x = (SCREEN_WIDTH - bar_width) // 2
        bar_y = SCREEN_HEIGHT * 0.7
        
        # Draw bar background
        pygame.draw.rect(surface, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
        
        # Draw progress
        fill_width = bar_width * self.progress
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, fill_width, bar_height))
        
        # Draw border
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 2)
        
        # Render current message
        message = self.messages[self.current_message]
        message_surface = self.font.render(message, True, WHITE)
        message_x = (SCREEN_WIDTH - message_surface.get_width()) // 2
        message_y = bar_y + bar_height + 20
        surface.blit(message_surface, (message_x, message_y))
        
        # Render progress percentage
        percent = int(self.progress * 100)
        percent_text = f"{percent}%"
        percent_surface = self.font.render(percent_text, True, WHITE)
        percent_x = bar_x + bar_width + 10
        percent_y = bar_y
        surface.blit(percent_surface, (percent_x, percent_y))