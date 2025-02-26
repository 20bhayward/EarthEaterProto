"""
UI components for Barren game
"""
import pygame
import math
import random
from typing import List, Tuple, Dict, Any, Optional, Callable

from eartheater.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, BLACK, TERMINAL_GREEN, TILE_SIZE
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
    """Game menu with terminal-style interface"""
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
        
        # Keep track of mouse position for hover effects
        self.mouse_pos = (0, 0)
        self.option_rects = []
        
        # Fonts - use pixel sizes that are multiples of TILE_SIZE
        title_size = 12 * TILE_SIZE
        option_size = 6 * TILE_SIZE
        self.title_font = pygame.font.Font(None, title_size)
        self.option_font = pygame.font.Font(None, option_size)
        self.terminal_font = pygame.font.Font(None, 4 * TILE_SIZE)
        
        # Terminal effects
        self.effects: List[Effect] = []
        self.next_particle_time = 0
        self.text_buffer = []
        self.cursor_visible = True
        self.cursor_blink_timer = 0
        self.typed_text = ""
        self.typing_speed = 2  # Characters per frame
        self.typing_progress = 0
        self.current_line = 0
        
        # Terminal text content
        self.terminal_lines = [
            "SYSTEM V1.22.1 BOOT SEQUENCE INITIATED",
            "LOADING KERNEL MODULES...",
            "MOUNTING FILESYSTEM...",
            "INITIALIZING BARREN TERRAIN SCANNER...",
            "STARTING USER INTERFACE...",
            "",
            "BARREN PLANETARY EXPLORATION SYSTEM READY.",
            "",
            "SELECT OPERATION MODE:"
        ]
        
        # Pixel grid effect
        self.pixel_grid = []
        for _ in range(200):
            x = random.randint(0, SCREEN_WIDTH // TILE_SIZE - 1) * TILE_SIZE
            y = random.randint(0, SCREEN_HEIGHT // TILE_SIZE - 1) * TILE_SIZE
            size = TILE_SIZE
            alpha = random.randint(40, 180)
            self.pixel_grid.append({
                'x': x, 
                'y': y, 
                'size': size, 
                'alpha': alpha,
                'flicker_speed': random.uniform(0.02, 0.2)
            })
            
        # Computer terminal rectangle
        padding = 80
        self.terminal_rect = pygame.Rect(
            padding,
            padding,
            SCREEN_WIDTH - padding * 2,
            SCREEN_HEIGHT - padding * 2
        )
    
    def add_terminal_effect(self) -> None:
        """Add terminal glitch effect"""
        # Random position within terminal area
        x = random.randint(self.terminal_rect.left + 20, self.terminal_rect.right - 20)
        y = random.randint(self.terminal_rect.top + 20, self.terminal_rect.bottom - 20)
        
        # Random size and velocity for digital effect
        size = random.uniform(1, 3) * TILE_SIZE
        velocity = random.uniform(0.1, 0.4) * TILE_SIZE
        
        # Create particle with green terminal color
        self.effects.append(ParticleEffect(
            count=1,
            pos=(x, y),
            velocity_range=(velocity * 0.5, velocity),
            size_range=(size * 0.8, size * 1.2),
            color=TERMINAL_GREEN,
            gravity=0.005 * TILE_SIZE,
            duration=60
        ))
    
    def update(self) -> None:
        """Update menu state"""
        # Get mouse position
        self.mouse_pos = pygame.mouse.get_pos()
        
        # Update effects
        for effect in self.effects[:]:
            effect.update()
            if not effect.active:
                self.effects.remove(effect)
        
        # Add new terminal effects periodically
        self.next_particle_time -= 1
        if self.next_particle_time <= 0:
            self.add_terminal_effect()
            self.next_particle_time = random.randint(2, 8)
        
        # Update cursor blinking
        self.cursor_blink_timer += 1
        if self.cursor_blink_timer >= 30:
            self.cursor_visible = not self.cursor_visible
            self.cursor_blink_timer = 0
            
        # Update typing effect
        if self.current_line < len(self.terminal_lines):
            current_text = self.terminal_lines[self.current_line]
            if self.typing_progress < len(current_text):
                # Add characters at typing speed
                chars_to_add = min(self.typing_speed, len(current_text) - self.typing_progress)
                self.typing_progress += chars_to_add
                self.typed_text = current_text[:self.typing_progress]
            else:
                # Move to next line
                self.text_buffer.append(self.typed_text)
                self.current_line += 1
                self.typing_progress = 0
                self.typed_text = ""
                
        # Update pixel grid flicker
        for pixel in self.pixel_grid:
            # Apply random flickering
            if random.random() < pixel['flicker_speed']:
                pixel['alpha'] = random.randint(40, 180)
    
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
        
        # Handle mouse events
        elif event.type == pygame.MOUSEMOTION:
            # Check if mouse is over any option
            for i, rect in enumerate(self.option_rects):
                if rect.collidepoint(event.pos):
                    self.selected = i
                    break
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                # Check if clicked on any option
                for i, rect in enumerate(self.option_rects):
                    if rect.collidepoint(event.pos):
                        self.callback(i)
                        return True
        
        return False
    
    def render(self, surface: pygame.Surface) -> None:
        """Render menu
        
        Args:
            surface: Surface to render to
        """
        # Fill background
        surface.fill(BLACK)
        
        # Render pixel grid background
        for pixel in self.pixel_grid:
            # Create pixel with alpha
            pixel_surface = pygame.Surface((pixel['size'], pixel['size']))
            pixel_surface.fill(TERMINAL_GREEN)
            pixel_surface.set_alpha(pixel['alpha'])
            surface.blit(pixel_surface, (pixel['x'], pixel['y']))
        
        # Draw terminal rectangle
        pygame.draw.rect(surface, TERMINAL_GREEN, self.terminal_rect, 2)
        
        # Draw scanlines
        for y in range(self.terminal_rect.top, self.terminal_rect.bottom, TILE_SIZE * 2):
            pygame.draw.line(
                surface,
                (0, 50, 0),  # Dark green
                (self.terminal_rect.left, y),
                (self.terminal_rect.right, y),
                1
            )
        
        # Draw terminal header
        header_rect = pygame.Rect(
            self.terminal_rect.left,
            self.terminal_rect.top,
            self.terminal_rect.width,
            TILE_SIZE * 6
        )
        pygame.draw.rect(surface, (0, 60, 0), header_rect)
        pygame.draw.rect(surface, TERMINAL_GREEN, header_rect, 2)
        
        # Draw terminal title
        title_surface = self.terminal_font.render("BARREN COMMAND INTERFACE", True, TERMINAL_GREEN)
        title_x = self.terminal_rect.left + 20
        title_y = self.terminal_rect.top + (header_rect.height - title_surface.get_height()) // 2
        surface.blit(title_surface, (title_x, title_y))
        
        # Draw terminal buttons in header
        button_size = TILE_SIZE * 2
        for i, color in enumerate([(255, 80, 80), (255, 255, 80), (80, 255, 80)]):
            button_x = self.terminal_rect.right - (button_size + 10) * (3 - i)
            button_y = self.terminal_rect.top + (header_rect.height - button_size) // 2
            pygame.draw.rect(surface, color, (button_x, button_y, button_size, button_size))
            pygame.draw.rect(surface, (0, 0, 0), (button_x, button_y, button_size, button_size), 1)
        
        # Render terminal content
        content_x = self.terminal_rect.left + 20
        content_y = self.terminal_rect.top + header_rect.height + 20
        line_height = TILE_SIZE * 4
        
        # Render buffered text
        for i, line in enumerate(self.text_buffer):
            text_surface = self.terminal_font.render(line, True, TERMINAL_GREEN)
            surface.blit(text_surface, (content_x, content_y + i * line_height))
        
        # Render current typing line
        if self.current_line < len(self.terminal_lines):
            # Show typed text with cursor
            cursor_text = self.typed_text
            if self.cursor_visible:
                cursor_text += "█"
            
            typed_surface = self.terminal_font.render(cursor_text, True, TERMINAL_GREEN)
            surface.blit(typed_surface, (content_x, content_y + len(self.text_buffer) * line_height))
        
        # Render menu options only when terminal is "fully loaded"
        if len(self.text_buffer) >= len(self.terminal_lines) - 1:
            options_y = content_y + (len(self.text_buffer) + 2) * line_height
            self.option_rects = []
            
            for i, option in enumerate(self.options):
                # Check if mouse is hovering
                color = TERMINAL_GREEN
                prefix = " > "
                
                if i == self.selected:
                    # Pulse effect for selected option
                    pulse = abs(math.sin(pygame.time.get_ticks() * 0.01)) * 0.3 + 0.7
                    color = (int(TERMINAL_GREEN[0] * pulse), 
                             int(TERMINAL_GREEN[1] * pulse), 
                             int(TERMINAL_GREEN[2] * pulse))
                
                # Render option
                option_text = prefix + option
                option_surface = self.terminal_font.render(option_text, True, color)
                option_x = content_x + TILE_SIZE * 2
                option_rect = option_surface.get_rect(topleft=(option_x, options_y))
                
                # Store option rect for mouse interaction
                self.option_rects.append(option_rect)
                
                # Draw option
                surface.blit(option_surface, (option_x, options_y))
                
                # Draw selection rectangle
                if i == self.selected:
                    pygame.draw.rect(surface, color, option_rect.inflate(10, 4), 1)
                
                options_y += line_height
        
        # Render effects on top
        for effect in self.effects:
            effect.render(surface)

class LoadingScreen:
    """Terminal-style loading screen with progress bar"""
    def __init__(self, callback: Callable[[], None]):
        """Initialize loading screen
        
        Args:
            callback: Function to call when loading is done
        """
        self.callback = callback
        self.progress = 0.0
        self.target_progress = 0.0
        self.messages = [
            "SCANNING PLANETARY SURFACE...",
            "GENERATING TERRAIN MAP...",
            "CREATING SUBTERRANEAN CAVE SYSTEMS...",
            "CALCULATING MATERIAL PHYSICS...",
            "INITIALIZING DRILL SYSTEMS...",
            "CALIBRATING JETPACK PARAMETERS...",
            "READY TO EXPLORE BARREN WORLD."
        ]
        self.current_message_index = 0
        self.completed_messages = []
        self.message_alpha = 255
        self.message_fade_out = False
        
        # Font - use pixel sizes that are multiples of TILE_SIZE
        self.title_font = pygame.font.Font(None, 12 * TILE_SIZE)
        self.message_font = pygame.font.Font(None, 4 * TILE_SIZE)
        
        # Terminal padding around screen edge
        padding = 60
        self.terminal_rect = pygame.Rect(
            padding,
            padding,
            SCREEN_WIDTH - padding * 2,
            SCREEN_HEIGHT - padding * 2
        )
        
        # Pixel grid effect (aligned to tiles)
        self.pixel_grid = []
        for _ in range(200):
            x = random.randint(0, SCREEN_WIDTH // TILE_SIZE - 1) * TILE_SIZE
            y = random.randint(0, SCREEN_HEIGHT // TILE_SIZE - 1) * TILE_SIZE
            size = TILE_SIZE
            alpha = random.randint(40, 180)
            self.pixel_grid.append({
                'x': x, 
                'y': y, 
                'size': size, 
                'alpha': alpha,
                'flicker_speed': random.uniform(0.02, 0.2)
            })
        
        # Effects
        self.effects: List[Effect] = []
        self.next_effect_time = 0
        
        # Add title effect
        self.title_text = "BARREN"
        self.subtitle_text = "PLANETARY EXPLORATION SYSTEM"
    
    def add_terminal_effect(self) -> None:
        """Add terminal glitch effect"""
        # Random position within terminal area
        x = random.randint(self.terminal_rect.left + 20, self.terminal_rect.right - 20)
        y = random.randint(self.terminal_rect.top + 20, self.terminal_rect.bottom - 20)
        
        # Random size and velocity for digital effect
        size = random.uniform(1, 3) * TILE_SIZE
        velocity = random.uniform(0.1, 0.4) * TILE_SIZE
        
        # Create particle with green terminal color
        self.effects.append(ParticleEffect(
            count=1,
            pos=(x, y),
            velocity_range=(velocity * 0.5, velocity),
            size_range=(size * 0.8, size * 1.2),
            color=TERMINAL_GREEN,
            gravity=0.005 * TILE_SIZE,
            duration=60
        ))
    
    def set_progress(self, progress: float) -> None:
        """Set current progress
        
        Args:
            progress: Progress value (0.0 to 1.0)
        """
        self.target_progress = progress
        
        # Update messages based on progress thresholds
        message_thresholds = [0.05, 0.2, 0.4, 0.6, 0.75, 0.9, 0.98]
        
        for i, threshold in enumerate(message_thresholds):
            if progress >= threshold and self.current_message_index <= i:
                if not self.message_fade_out and self.current_message_index == i:
                    self.message_fade_out = True
                    self.message_alpha = 255
    
    def update(self) -> None:
        """Update loading screen state"""
        # Smoothly approach target progress
        if self.progress < self.target_progress:
            self.progress += min(0.005, self.target_progress - self.progress)
        
        # Add terminal effects periodically
        self.next_effect_time -= 1
        if self.next_effect_time <= 0:
            self.add_terminal_effect()
            self.next_effect_time = random.randint(2, 8)
            
        # Update effects
        for effect in self.effects[:]:
            effect.update()
            if not effect.active:
                self.effects.remove(effect)
        
        # Update message transitions
        if self.message_fade_out:
            self.message_alpha -= 8
            if self.message_alpha <= 0:
                self.message_alpha = 0
                self.message_fade_out = False
                # Move to next message
                if self.current_message_index < len(self.messages):
                    # Add completed message
                    self.completed_messages.append(self.messages[self.current_message_index])
                    self.current_message_index += 1
        
        # Update pixel grid flicker
        for pixel in self.pixel_grid:
            # Apply random flickering
            if random.random() < pixel['flicker_speed']:
                pixel['alpha'] = random.randint(40, 180)
        
        # Complete loading when done
        if self.progress >= 1.0 and self.current_message_index >= len(self.messages):
            self.callback()
    
    def render(self, surface: pygame.Surface) -> None:
        """Render loading screen
        
        Args:
            surface: Surface to render to
        """
        # Fill background
        surface.fill(BLACK)
        
        # Render pixel grid background
        for pixel in self.pixel_grid:
            # Create pixel with alpha
            pixel_surface = pygame.Surface((pixel['size'], pixel['size']))
            pixel_surface.fill(TERMINAL_GREEN)
            pixel_surface.set_alpha(pixel['alpha'])
            surface.blit(pixel_surface, (pixel['x'], pixel['y']))
        
        # Draw terminal rectangle
        pygame.draw.rect(surface, TERMINAL_GREEN, self.terminal_rect, 2)
        
        # Draw scanlines
        for y in range(self.terminal_rect.top, self.terminal_rect.bottom, TILE_SIZE * 2):
            pygame.draw.line(
                surface,
                (0, 50, 0),  # Dark green
                (self.terminal_rect.left, y),
                (self.terminal_rect.right, y),
                1
            )
        
        # Draw terminal header
        header_rect = pygame.Rect(
            self.terminal_rect.left,
            self.terminal_rect.top,
            self.terminal_rect.width,
            TILE_SIZE * 6
        )
        pygame.draw.rect(surface, (0, 60, 0), header_rect)
        pygame.draw.rect(surface, TERMINAL_GREEN, header_rect, 2)
        
        # Draw terminal title
        title_surface = self.message_font.render("INITIALIZATION SEQUENCE", True, TERMINAL_GREEN)
        title_x = self.terminal_rect.left + 20
        title_y = self.terminal_rect.top + (header_rect.height - title_surface.get_height()) // 2
        surface.blit(title_surface, (title_x, title_y))
        
        # Draw main title centered in upper part of terminal
        title_y = self.terminal_rect.top + header_rect.height + 40
        title_surface = self.title_font.render(self.title_text, True, TERMINAL_GREEN)
        title_x = self.terminal_rect.centerx - title_surface.get_width() // 2
        surface.blit(title_surface, (title_x, title_y))
        
        # Draw subtitle
        subtitle_y = title_y + title_surface.get_height() + 10
        subtitle_surface = self.message_font.render(self.subtitle_text, True, TERMINAL_GREEN)
        subtitle_x = self.terminal_rect.centerx - subtitle_surface.get_width() // 2
        surface.blit(subtitle_surface, (subtitle_x, subtitle_y))
        
        # Draw terminal buttons in header
        button_size = TILE_SIZE * 2
        for i, color in enumerate([(255, 80, 80), (255, 255, 80), (80, 255, 80)]):
            button_x = self.terminal_rect.right - (button_size + 10) * (3 - i)
            button_y = self.terminal_rect.top + (header_rect.height - button_size) // 2
            pygame.draw.rect(surface, color, (button_x, button_y, button_size, button_size))
            pygame.draw.rect(surface, (0, 0, 0), (button_x, button_y, button_size, button_size), 1)
        
        # Render terminal content - completed messages
        content_x = self.terminal_rect.left + 30
        start_y = subtitle_y + 80
        line_height = TILE_SIZE * 4
        
        message_y = start_y
        for i, line in enumerate(self.completed_messages):
            text = f"[COMPLETED] {line}"
            message_surface = self.message_font.render(text, True, (100, 255, 100))
            surface.blit(message_surface, (content_x, message_y))
            message_y += line_height
            
        # Render current message with fading
        if self.current_message_index < len(self.messages):
            current_text = f"[IN PROGRESS] {self.messages[self.current_message_index]}"
            curr_message_surface = self.message_font.render(current_text, True, TERMINAL_GREEN)
            
            # Create alpha surface for fading
            alpha_surface = pygame.Surface(curr_message_surface.get_size(), pygame.SRCALPHA)
            alpha_surface.fill((255, 255, 255, self.message_alpha))
            curr_message_surface.blit(alpha_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            
            surface.blit(curr_message_surface, (content_x, message_y))
            
        # Draw progress indicator at the bottom
        progress_text = f"INITIALIZATION PROGRESS: {int(self.progress * 100)}%"
        progress_surface = self.message_font.render(progress_text, True, TERMINAL_GREEN)
        progress_y = self.terminal_rect.bottom - 60
        progress_x = self.terminal_rect.centerx - progress_surface.get_width() // 2
        surface.blit(progress_surface, (progress_x, progress_y))
        
        # Render progress bar
        bar_width = self.terminal_rect.width * 0.8
        bar_height = TILE_SIZE
        bar_x = self.terminal_rect.left + (self.terminal_rect.width - bar_width) // 2
        bar_y = progress_y + progress_surface.get_height() + 10
        
        # Draw bar background
        pygame.draw.rect(surface, (0, 80, 0), (bar_x, bar_y, bar_width, bar_height))
        
        # Draw progress segments
        segment_width = bar_width / 40
        segments = int(self.progress * 40)
        for i in range(segments):
            # Calculate pulse based on segment position
            pulse_offset = i * 0.2
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.005 + pulse_offset)) * 0.5 + 0.5
            segment_color = (int(TERMINAL_GREEN[0] * pulse),
                             int(TERMINAL_GREEN[1] * pulse),
                             int(TERMINAL_GREEN[2] * pulse))
            
            # Draw segment
            segment_x = bar_x + i * segment_width
            pygame.draw.rect(surface, segment_color, 
                            (segment_x, bar_y, segment_width - 1, bar_height))
        
        # Draw border
        pygame.draw.rect(surface, TERMINAL_GREEN, (bar_x, bar_y, bar_width, bar_height), 1)
        
        # Render effects on top
        for effect in self.effects:
            effect.render(surface)