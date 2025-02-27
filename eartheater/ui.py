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

class SettingsMenu:
    """World generation settings menu with terminal-style interface"""
    def __init__(self, title: str, settings, callback: Callable[[object], None]):
        """Initialize settings menu
        
        Args:
            title: Menu title
            settings: WorldGenSettings object to modify
            callback: Function to call with modified settings or None if canceled
        """
        self.title = title
        self.settings = settings
        self.callback = callback
        self.selected_setting = 0
        self.setting_values = {}  # For tracking slider positions
        
        # Keep track of mouse position for hover effects
        self.mouse_pos = (0, 0)
        self.setting_rects = []
        self.slider_rects = []
        self.toggle_rects = []
        self.button_rects = []
        
        # Fonts - use pixel sizes that scale with screen resolution
        # Calculate scaling factor based on screen resolution (1080p as baseline)
        self.scale_factor = min(SCREEN_WIDTH / 1920, SCREEN_HEIGHT / 1080)
        title_size = int(42 * self.scale_factor * TILE_SIZE)
        option_size = int(24 * self.scale_factor * TILE_SIZE)
        terminal_size = int(16 * self.scale_factor * TILE_SIZE)
        
        self.title_font = pygame.font.Font(None, title_size)
        self.option_font = pygame.font.Font(None, option_size)
        self.terminal_font = pygame.font.Font(None, terminal_size)
        self.line_height = int(TILE_SIZE * 10 * self.scale_factor)
        
        # Terminal effects
        self.effects: List[Effect] = []
        self.next_particle_time = 0
        
        # Define available settings
        self.create_settings_controls()
            
        # Computer terminal rectangle - scale with screen size
        padding = int(80 * self.scale_factor)
        self.terminal_rect = pygame.Rect(
            padding,
            padding,
            SCREEN_WIDTH - padding * 2,
            SCREEN_HEIGHT - padding * 2
        )
        
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
        
        # Animation timer for effects
        self.animation_timer = 0
        
        # Buttons for confirming/canceling
        self.buttons = ["Start Game", "Cancel"]
        self.selected_button = 0
    
    def create_settings_controls(self):
        """Create the settings controls (sliders & toggles)"""
        # Initialize value mapping for slider settings
        self.setting_values = {
            'seed': self.settings.seed / 100000,  # 0-1 scale
            'world_size': 0.5 if self.settings.world_size == "medium" else (0.0 if self.settings.world_size == "small" else 1.0),
            'terrain_roughness': self.settings.terrain_roughness,
            'ore_density': self.settings.ore_density,
            'water_level': self.settings.water_level,
            'cave_density': self.settings.cave_density,
        }
        
        # Define settings UI
        self.setting_controls = [
            {'type': 'slider', 'name': 'Seed', 'key': 'seed', 'min_label': 'Random', 'max_label': 'Fixed'},
            {'type': 'slider', 'name': 'World Size', 'key': 'world_size', 'min_label': 'Small', 'max_label': 'Large'},
            {'type': 'slider', 'name': 'Terrain Roughness', 'key': 'terrain_roughness', 'min_label': 'Flat', 'max_label': 'Jagged'},
            {'type': 'slider', 'name': 'Ore Density', 'key': 'ore_density', 'min_label': 'Sparse', 'max_label': 'Dense'},
            {'type': 'slider', 'name': 'Water Level', 'key': 'water_level', 'min_label': 'Low', 'max_label': 'High'},
            {'type': 'slider', 'name': 'Cave Density', 'key': 'cave_density', 'min_label': 'Few', 'max_label': 'Many'},
            {'type': 'toggle', 'name': 'Mountains', 'key': 'has_mountains', 'value': self.settings.has_mountains},
            {'type': 'toggle', 'name': 'Desert', 'key': 'has_desert', 'value': self.settings.has_desert},
            {'type': 'toggle', 'name': 'Forest', 'key': 'has_forest', 'value': self.settings.has_forest},
            {'type': 'toggle', 'name': 'Volcanic Zone', 'key': 'has_volcanic', 'value': self.settings.has_volcanic},
        ]
        
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
        """Update settings menu state"""
        # Animation timer for effects
        self.animation_timer += 1
        
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
            True if menu action was triggered, False otherwise
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_setting = max(0, self.selected_setting - 1)
                return False
            elif event.key == pygame.K_DOWN:
                self.selected_setting = min(len(self.setting_controls) + len(self.buttons) - 1, self.selected_setting + 1)
                return False
            elif event.key == pygame.K_LEFT:
                # Adjust slider value left
                if self.selected_setting < len(self.setting_controls):
                    control = self.setting_controls[self.selected_setting]
                    if control['type'] == 'slider':
                        self.setting_values[control['key']] = max(0.0, self.setting_values[control['key']] - 0.1)
                    elif control['type'] == 'toggle':
                        control['value'] = not control['value']
                return False
            elif event.key == pygame.K_RIGHT:
                # Adjust slider value right
                if self.selected_setting < len(self.setting_controls):
                    control = self.setting_controls[self.selected_setting]
                    if control['type'] == 'slider':
                        self.setting_values[control['key']] = min(1.0, self.setting_values[control['key']] + 0.1)
                    elif control['type'] == 'toggle':
                        control['value'] = not control['value']
                return False
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                # Toggle or confirm selection
                if self.selected_setting < len(self.setting_controls):
                    control = self.setting_controls[self.selected_setting]
                    if control['type'] == 'toggle':
                        control['value'] = not control['value']
                else:
                    # Button actions
                    button_index = self.selected_setting - len(self.setting_controls)
                    return self._handle_button_action(button_index)
                return False
            
        # Handle mouse events
        elif event.type == pygame.MOUSEMOTION:
            # Check if mouse is over any setting
            for i, rect in enumerate(self.setting_rects):
                if rect.collidepoint(event.pos):
                    self.selected_setting = i
                    break
                    
            # Check buttons
            for i, rect in enumerate(self.button_rects):
                if rect.collidepoint(event.pos):
                    self.selected_setting = len(self.setting_controls) + i
                    break
            
            # Check sliders for dragging
            for i, rect in enumerate(self.slider_rects):
                if rect.collidepoint(event.pos) and pygame.mouse.get_pressed()[0]:  # Left button pressed
                    # Calculate slider value from mouse position
                    control = self.setting_controls[i]
                    if control['type'] == 'slider':
                        x_pos = event.pos[0] - rect.left
                        slider_value = max(0.0, min(1.0, x_pos / rect.width))
                        self.setting_values[control['key']] = slider_value
                    break
                    
            # Check toggles
            for i, rect in enumerate(self.toggle_rects):
                if rect.collidepoint(event.pos):
                    control_index = i + sum(1 for c in self.setting_controls[:i] if c['type'] != 'toggle')
                    self.selected_setting = control_index
                    break
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                # Check if clicked on any control
                for i, rect in enumerate(self.setting_rects):
                    if rect.collidepoint(event.pos):
                        self.selected_setting = i
                        control = self.setting_controls[i]
                        if control['type'] == 'toggle':
                            control['value'] = not control['value']
                        break
                
                # Check if clicked on any button
                for i, rect in enumerate(self.button_rects):
                    if rect.collidepoint(event.pos):
                        self.selected_setting = len(self.setting_controls) + i
                        return self._handle_button_action(i)
                
                # Check if clicked on a slider
                for i, rect in enumerate(self.slider_rects):
                    if rect.collidepoint(event.pos):
                        # Set slider value based on click position
                        control = self.setting_controls[i]
                        if control['type'] == 'slider':
                            x_pos = event.pos[0] - rect.left
                            slider_value = max(0.0, min(1.0, x_pos / rect.width))
                            self.setting_values[control['key']] = slider_value
                        break
                        
                # Check toggles specifically
                for i, rect in enumerate(self.toggle_rects):
                    if rect.collidepoint(event.pos):
                        toggle_index = sum(1 for c in self.setting_controls if c['type'] == 'toggle' and self.setting_controls.index(c) < i)
                        control_index = next((idx for idx, c in enumerate(self.setting_controls) if c['type'] == 'toggle' and toggle_index == 0), None)
                        if control_index is not None:
                            control = self.setting_controls[control_index]
                            control['value'] = not control['value']
                        break
        
        return False
    
    def _handle_button_action(self, button_index: int) -> bool:
        """Handle button click actions
        
        Args:
            button_index: Index of the clicked button
            
        Returns:
            True if action performed, False otherwise
        """
        if button_index == 0:  # Start Game
            # Apply settings to the settings object
            self._apply_settings()
            self.callback(self.settings)
            return True
        elif button_index == 1:  # Cancel
            self.callback(None)
            return True
        return False
    
    def _apply_settings(self) -> None:
        """Apply UI values to the settings object"""
        # Apply slider values
        self.settings.seed = int(self.setting_values['seed'] * 100000)
        
        # World size (convert 0-1 to small/medium/large)
        size_value = self.setting_values['world_size']
        if size_value < 0.33:
            self.settings.world_size = "small"
        elif size_value < 0.66:
            self.settings.world_size = "medium"
        else:
            self.settings.world_size = "large"
        
        # Other numeric settings
        self.settings.terrain_roughness = self.setting_values['terrain_roughness']
        self.settings.ore_density = self.setting_values['ore_density']
        self.settings.water_level = self.setting_values['water_level']
        self.settings.cave_density = self.setting_values['cave_density']
        
        # Toggle values
        for control in self.setting_controls:
            if control['type'] == 'toggle':
                setattr(self.settings, control['key'], control['value'])
    
    def render(self, surface: pygame.Surface) -> None:
        """Render settings menu
        
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
            TILE_SIZE * 8
        )
        pygame.draw.rect(surface, (0, 60, 0), header_rect)
        pygame.draw.rect(surface, TERMINAL_GREEN, header_rect, 2)
        
        # Draw terminal title
        title_surface = self.terminal_font.render("NEW GAME CONFIGURATION", True, TERMINAL_GREEN)
        title_x = self.terminal_rect.left + 20
        title_y = self.terminal_rect.top + (header_rect.height - title_surface.get_height()) // 2
        surface.blit(title_surface, (title_x, title_y))
        
        # Draw terminal buttons in header
        button_size = TILE_SIZE * 3
        for i, color in enumerate([(255, 80, 80), (255, 255, 80), (80, 255, 80)]):
            button_x = self.terminal_rect.right - (button_size + 10) * (3 - i)
            button_y = self.terminal_rect.top + (header_rect.height - button_size) // 2
            pygame.draw.rect(surface, color, (button_x, button_y, button_size, button_size))
            pygame.draw.rect(surface, (0, 0, 0), (button_x, button_y, button_size, button_size), 1)
        
        # Calculate layout - two columns
        col_width = (self.terminal_rect.width - 120) // 2
        col1_x = self.terminal_rect.left + 40
        col2_x = col1_x + col_width + 40
        
        # Render settings
        content_y = self.terminal_rect.top + header_rect.height + 40
        
        # Draw main title centered in upper part of terminal
        title_surface = self.title_font.render("WORLD CONFIGURATION", True, TERMINAL_GREEN)
        title_x = self.terminal_rect.centerx - title_surface.get_width() // 2
        surface.blit(title_surface, (title_x, content_y))
        content_y += title_surface.get_height() + 40
        
        # Clear control rects lists
        self.setting_rects = []
        self.slider_rects = []
        self.toggle_rects = []
        
        # Render settings in two columns
        slider_width = int(col_width - 100)
        slider_height = TILE_SIZE * 3
        
        # Separate controls into columns
        col1_controls = self.setting_controls[:6]  # First 6 controls (sliders)
        col2_controls = self.setting_controls[6:]  # Remaining controls (toggles)
        
        # Draw first column (sliders)
        current_y = content_y
        for i, control in enumerate(col1_controls):
            # Check if this is the selected control
            is_selected = (i == self.selected_setting)
            
            # Draw setting name
            name_color = TERMINAL_GREEN
            if is_selected:
                name_color = (255, 255, 255)
                
            name_surface = self.option_font.render(control['name'], True, name_color)
            surface.blit(name_surface, (col1_x, current_y))
            
            # Store the clickable area for this control
            control_rect = pygame.Rect(col1_x, current_y, col_width, self.line_height)
            self.setting_rects.append(control_rect)
            
            # Draw slider
            slider_x = col1_x
            slider_y = current_y + name_surface.get_height() + 10
            
            # Track background
            track_rect = pygame.Rect(slider_x, slider_y, slider_width, slider_height)
            pygame.draw.rect(surface, (0, 80, 0), track_rect)
            pygame.draw.rect(surface, TERMINAL_GREEN, track_rect, 1)
            
            # Fill based on value
            value = self.setting_values[control['key']]
            fill_width = int(value * slider_width)
            fill_rect = pygame.Rect(slider_x, slider_y, fill_width, slider_height)
            
            # Pulse effect if selected
            if is_selected:
                pulse = math.sin(self.animation_timer * 0.1) * 0.2 + 0.8
                fill_color = (
                    int(TERMINAL_GREEN[0] * pulse),
                    int(TERMINAL_GREEN[1] * pulse),
                    int(TERMINAL_GREEN[2] * pulse)
                )
            else:
                fill_color = (0, 150, 50)
            
            pygame.draw.rect(surface, fill_color, fill_rect)
            
            # Draw slider handle
            handle_x = slider_x + fill_width - slider_height // 2
            handle_y = slider_y
            handle_rect = pygame.Rect(handle_x, handle_y, slider_height, slider_height)
            pygame.draw.rect(surface, WHITE if is_selected else (200, 200, 200), handle_rect)
            
            # Store slider rect for interaction
            self.slider_rects.append(track_rect)
            
            # Draw min/max labels
            min_surface = self.terminal_font.render(control['min_label'], True, TERMINAL_GREEN)
            max_surface = self.terminal_font.render(control['max_label'], True, TERMINAL_GREEN)
            
            # Position labels below slider at left and right
            min_x = slider_x
            max_x = slider_x + slider_width - max_surface.get_width()
            label_y = slider_y + slider_height + 8
            
            surface.blit(min_surface, (min_x, label_y))
            surface.blit(max_surface, (max_x, label_y))
            
            # Draw value text
            value_text = f"{int(value * 100)}%"
            value_surface = self.terminal_font.render(value_text, True, WHITE if is_selected else TERMINAL_GREEN)
            value_x = slider_x + (slider_width // 2) - (value_surface.get_width() // 2)
            value_y = slider_y + slider_height + 8
            surface.blit(value_surface, (value_x, value_y))
            
            # Move to next row with proper spacing
            current_y += self.line_height + 30
        
        # Draw second column (toggles) - biome options
        current_y = content_y
        
        # Draw Biomes subtitle
        biome_title = self.option_font.render("BIOME OPTIONS", True, TERMINAL_GREEN)
        biome_x = col2_x + (col_width // 2) - (biome_title.get_width() // 2)
        surface.blit(biome_title, (biome_x, current_y))
        current_y += biome_title.get_height() + 20
        
        for i, control in enumerate(col2_controls):
            # Calculate actual index in full list
            actual_index = i + len(col1_controls)
            
            # Check if this is the selected control
            is_selected = (actual_index == self.selected_setting)
            
            # Draw setting name
            name_color = TERMINAL_GREEN
            if is_selected:
                name_color = (255, 255, 255)
                
            name_surface = self.option_font.render(control['name'], True, name_color)
            surface.blit(name_surface, (col2_x, current_y))
            
            # Store the clickable area for this control
            control_rect = pygame.Rect(col2_x, current_y, col_width, self.line_height)
            self.setting_rects.append(control_rect)
            
            # Draw toggle switch
            toggle_x = col2_x + col_width - 100
            toggle_y = current_y + (name_surface.get_height() - slider_height) // 2
            toggle_width = slider_height * 2
            toggle_rect = pygame.Rect(toggle_x, toggle_y, toggle_width, slider_height)
            
            # Draw track
            pygame.draw.rect(surface, (0, 80, 0), toggle_rect)
            pygame.draw.rect(surface, TERMINAL_GREEN, toggle_rect, 1)
            
            # Draw switch position
            switch_x = toggle_x + (toggle_width // 2 if control['value'] else 0)
            switch_rect = pygame.Rect(switch_x, toggle_y, toggle_width // 2, slider_height)
            
            # Pulse effect if selected
            if is_selected:
                pulse = math.sin(self.animation_timer * 0.1) * 0.2 + 0.8
                switch_color = (
                    int(WHITE[0] * pulse),
                    int(WHITE[1] * pulse),
                    int(WHITE[2] * pulse)
                )
            else:
                switch_color = (200, 200, 200)
            
            pygame.draw.rect(surface, switch_color, switch_rect)
            
            # Draw status text
            status = "ON" if control['value'] else "OFF"
            status_color = (100, 255, 100) if control['value'] else (255, 100, 100)
            status_surface = self.terminal_font.render(status, True, status_color)
            status_x = toggle_x + toggle_width + 10
            status_y = toggle_y + (slider_height - status_surface.get_height()) // 2
            surface.blit(status_surface, (status_x, status_y))
            
            # Store toggle rect for interaction
            self.toggle_rects.append(toggle_rect)
            
            # Move to next row
            current_y += self.line_height
        
        # Calculate position for buttons at the bottom of screen
        button_y = self.terminal_rect.bottom - 80
        
        # Draw separator line
        separator_y = button_y - 30
        pygame.draw.line(
            surface,
            TERMINAL_GREEN,
            (self.terminal_rect.left + 20, separator_y),
            (self.terminal_rect.right - 20, separator_y),
            2
        )
        
        # Render buttons
        button_width = 250 
        button_height = self.line_height
        self.button_rects = []
        
        for i, button_text in enumerate(self.buttons):
            # Center buttons
            button_x = self.terminal_rect.centerx - button_width // 2
            button_x += (i - len(self.buttons) / 2 + 0.5) * (button_width + 80)
            
            button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
            self.button_rects.append(button_rect)
            
            # Check if selected
            is_selected = (i + len(self.setting_controls) == self.selected_setting)
            
            # Button background with pulse effect for selected button
            if is_selected:
                pulse = math.sin(self.animation_timer * 0.1) * 0.2 + 0.8
                bg_color = (
                    int(TERMINAL_GREEN[0] * 0.3 * pulse),
                    int(TERMINAL_GREEN[1] * 0.3 * pulse),
                    int(TERMINAL_GREEN[2] * 0.3 * pulse)
                )
                border_color = WHITE
            else:
                bg_color = (0, 60, 0)
                border_color = TERMINAL_GREEN
            
            # Draw button
            pygame.draw.rect(surface, bg_color, button_rect)
            pygame.draw.rect(surface, border_color, button_rect, 2)
            
            # Button text
            text_surface = self.option_font.render(button_text, True, WHITE if is_selected else TERMINAL_GREEN)
            text_x = button_rect.centerx - text_surface.get_width() // 2
            text_y = button_rect.centery - text_surface.get_height() // 2
            surface.blit(text_surface, (text_x, text_y))
        
        # Render effects on top
        for effect in self.effects:
            effect.render(surface)


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
        
        # Fonts - use pixel sizes that scale with screen resolution
        # Calculate scaling factor based on screen resolution (1080p as baseline)
        self.scale_factor = min(SCREEN_WIDTH / 1920, SCREEN_HEIGHT / 1080)
        title_size = int(36 * self.scale_factor * TILE_SIZE)
        option_size = int(18 * self.scale_factor * TILE_SIZE)
        terminal_size = int(12 * self.scale_factor * TILE_SIZE)
        
        self.title_font = pygame.font.Font(None, title_size)
        self.option_font = pygame.font.Font(None, option_size)
        self.terminal_font = pygame.font.Font(None, terminal_size)
        self.line_height = int(TILE_SIZE * 8 * self.scale_factor)

        
        # Terminal effects
        self.effects: List[Effect] = []
        self.next_particle_time = 0
        self.text_buffer = []
        self.cursor_visible = True
        self.cursor_blink_timer = 0
        self.typed_text = ""
        self.typing_speed = 1  # Characters per frame
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
            "ENTER NEXT OPERATION:",
            ""
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
            
        # Computer terminal rectangle - scale with screen size
        padding = int(80 * self.scale_factor)
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
        
        # Draw terminal rectangle - thicker border for larger screens
        border_width = max(2, int(self.scale_factor * 2.5))
        pygame.draw.rect(surface, TERMINAL_GREEN, self.terminal_rect, border_width)
        
        # Draw scanlines - space based on screen resolution
        scanline_spacing = max(2, int(TILE_SIZE * 3 * self.scale_factor))
        for y in range(self.terminal_rect.top, self.terminal_rect.bottom, scanline_spacing):
            pygame.draw.line(
                surface,
                (0, 50, 0),  # Dark green
                (self.terminal_rect.left, y),
                (self.terminal_rect.right, y),
                max(1, int(self.scale_factor * 1.5))  # Thicker lines on larger screens
            )
        
        # Draw terminal header
        header_rect = pygame.Rect(
            self.terminal_rect.left,
            self.terminal_rect.top,
            self.terminal_rect.width,
            TILE_SIZE * 16
        )
        pygame.draw.rect(surface, (0, 60, 0), header_rect)
        pygame.draw.rect(surface, TERMINAL_GREEN, header_rect, 2)
        
        # Draw terminal title
        title_surface = self.terminal_font.render("BARREN COMMAND INTERFACE", True, TERMINAL_GREEN)
        title_x = self.terminal_rect.left + 20
        title_y = self.terminal_rect.top + (header_rect.height - title_surface.get_height()) // 2
        surface.blit(title_surface, (title_x, title_y))
        
        # Draw terminal buttons in header
        button_size = TILE_SIZE * 8
        for i, color in enumerate([(255, 80, 80), (255, 255, 80), (80, 255, 80)]):
            button_x = self.terminal_rect.right - (button_size + 10) * (3 - i)
            button_y = self.terminal_rect.top + (header_rect.height - button_size) // 2
            pygame.draw.rect(surface, color, (button_x, button_y, button_size, button_size))
            pygame.draw.rect(surface, (0, 0, 0), (button_x, button_y, button_size, button_size), 1)
        
        # Render terminal content
        content_x = self.terminal_rect.left + 20
        content_y = self.terminal_rect.top + header_rect.height + 20
        line_height = int(TILE_SIZE * 12 * self.scale_factor)
        
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
            options_y = content_y + (len(self.text_buffer)) * line_height
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
    """Terminal-style loading screen with progress bar and world preview"""
    def __init__(self, callback: Callable[[], None], world=None):
        """Initialize loading screen
        
        Args:
            callback: Function to call when loading is done
            world: World reference for displaying preview chunks
        """
        self.callback = callback
        self.world = world  # Reference to world for preview visualization
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
        
        # Fonts - use pixel sizes that scale with screen resolution
        # Calculate scaling factor based on screen resolution (1080p as baseline)
        self.scale_factor = min(SCREEN_WIDTH / 1920, SCREEN_HEIGHT / 1080)
        title_size = int(36 * self.scale_factor * TILE_SIZE)
        message_size = int(12 * self.scale_factor * TILE_SIZE)
        
        self.title_font = pygame.font.Font(None, title_size)
        self.message_font = pygame.font.Font(None, message_size)
        
        # Terminal padding around screen edge - scale with screen size
        padding = int(60 * self.scale_factor)
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
        
        # World preview settings
        self.preview_surface = None
        self.preview_rect = None
        self.preview_border = 3
        self.preview_pixel_size = 3  # Size of each preview pixel
        
        # Add preview box rect at the right side of the terminal
        preview_width = int(self.terminal_rect.width * 0.4)
        preview_height = int(self.terminal_rect.height * 0.4)
        preview_x = self.terminal_rect.right - preview_width - 30
        # Calculate vertical position based on terminal rect
        preview_y = self.terminal_rect.top + int(self.terminal_rect.height * 0.25)
        self.preview_rect = pygame.Rect(preview_x, preview_y, preview_width, preview_height)
        
        # Create the preview surface after initializing the rect
        self.create_preview_surface()
        
        # Estimated time remaining
        self.start_time = pygame.time.get_ticks()
        self.estimated_time = 30000  # Initial estimate: 30 seconds
        self.last_progress = 0.0
        self.last_time = self.start_time
    
    def create_preview_surface(self) -> None:
        """Create surface for the world preview"""
        if self.preview_rect:
            self.preview_surface = pygame.Surface((
                self.preview_rect.width - self.preview_border*2,
                self.preview_rect.height - self.preview_border*2
            ))
    
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
        # Calculate estimated time remaining based on progress rate
        current_time = pygame.time.get_ticks()
        time_elapsed = current_time - self.last_time
        progress_delta = progress - self.last_progress
        
        # Only update if meaningful progress has been made
        if progress_delta > 0.01 and time_elapsed > 100:
            # Calculate time per 1% progress
            time_per_percent = time_elapsed / (progress_delta * 100)
            
            # Estimate remaining time
            remaining_percent = (1.0 - progress) * 100
            estimated_remaining = remaining_percent * time_per_percent
            
            # Update with some smoothing
            self.estimated_time = (self.estimated_time * 0.7) + (estimated_remaining * 0.3)
            
            # Update tracking values
            self.last_time = current_time
            self.last_progress = progress
        
        self.target_progress = progress
        
        # Update messages based on adaptive progress thresholds
        # Make thresholds more responsive to actual progress
        if len(self.messages) > 1:
            threshold_increment = 0.95 / (len(self.messages) - 1)
            message_thresholds = [i * threshold_increment for i in range(len(self.messages))]
            message_thresholds[-1] = 0.95  # Last message at 95%
            
            for i, threshold in enumerate(message_thresholds):
                if progress >= threshold and self.current_message_index <= i:
                    if not self.message_fade_out and self.current_message_index == i:
                        self.message_fade_out = True
                        self.message_alpha = 255
    
    def update(self) -> None:
        """Update loading screen state"""
        # Smoothly approach target progress
        if self.progress < self.target_progress:
            # Faster progress at the beginning, slower at the end for better visual feedback
            approach_speed = 0.01 if self.progress < 0.8 else 0.005
            self.progress += min(approach_speed, self.target_progress - self.progress)
        
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
    
    def render_world_preview(self, surface: pygame.Surface) -> None:
        """
        Render the world preview from generated chunk data
        
        Args:
            surface: Surface to render to
        """
        if self.world is None or not self.preview_surface:
            return
            
        # Clear preview surface
        self.preview_surface.fill((0, 30, 0))  # Dark green background
        
        # Check if we have preview data
        if hasattr(self.world, 'preview_chunks') and self.world.preview_chunks:
            # Calculate preview dimensions
            preview_width = self.preview_surface.get_width()
            preview_height = self.preview_surface.get_height()
            
            # Find min/max chunk coordinates to center the preview
            if self.world.preview_chunks:
                min_x = min(chunk[0] for chunk in self.world.preview_chunks)
                max_x = max(chunk[0] for chunk in self.world.preview_chunks)
                min_y = min(chunk[1] for chunk in self.world.preview_chunks)
                max_y = max(chunk[1] for chunk in self.world.preview_chunks)
                
                # Calculate world width and height in chunks
                world_width = max_x - min_x + 1
                world_height = max_y - min_y + 1
                
                # Calculate pixel size to fit the preview
                preview_chunk_size = min(preview_width // world_width, preview_height // world_height)
                
                # Downsampled chunk size (after 4x reduction)
                chunk_pixel_size = preview_chunk_size // 16
                if chunk_pixel_size < 1:
                    chunk_pixel_size = 1
                
                # Center offset
                offset_x = (preview_width - world_width * preview_chunk_size) // 2
                offset_y = (preview_height - world_height * preview_chunk_size) // 2
                
                # Render each preview chunk
                from eartheater.constants import MaterialType, MATERIAL_COLORS
                
                for chunk_x, chunk_y, preview_data in self.world.preview_chunks:
                    # Calculate position in preview
                    px = offset_x + (chunk_x - min_x) * preview_chunk_size
                    py = offset_y + (chunk_y - min_y) * preview_chunk_size
                    
                    # Render downsampled chunk data
                    for y in range(preview_data.shape[0]):
                        for x in range(preview_data.shape[1]):
                            # Get material value
                            material_val = preview_data[y, x]
                            
                            # Convert back to MaterialType
                            material = MaterialType(material_val)
                            
                            # Get material color
                            color = MATERIAL_COLORS.get(material, (0, 0, 0))
                            
                            # Skip air for performance
                            if material == MaterialType.AIR:
                                continue
                                
                            # Draw pixel
                            pixel_rect = pygame.Rect(
                                px + x * chunk_pixel_size, 
                                py + y * chunk_pixel_size,
                                chunk_pixel_size, 
                                chunk_pixel_size
                            )
                            pygame.draw.rect(self.preview_surface, color, pixel_rect)
            
            # Add a "blip" to show player position at center
            center_x = preview_width // 2
            center_y = preview_height // 2
            pygame.draw.circle(self.preview_surface, (255, 255, 255), (center_x, center_y), 3)
            
            # Add scan lines effect
            for y in range(0, preview_height, 4):
                pygame.draw.line(
                    self.preview_surface,
                    (0, 255, 0, 20),  # Green with low alpha
                    (0, y),
                    (preview_width, y),
                    1
                )
        
        # Draw to main surface
        # Draw the preview box with border
        pygame.draw.rect(surface, (0, 80, 0), self.preview_rect)
        pygame.draw.rect(surface, TERMINAL_GREEN, self.preview_rect, self.preview_border)
        
        # Draw the preview title
        preview_title = self.message_font.render("TERRAIN SCAN", True, TERMINAL_GREEN)
        title_x = self.preview_rect.centerx - preview_title.get_width() // 2
        title_y = self.preview_rect.top - preview_title.get_height() - 5
        surface.blit(preview_title, (title_x, title_y))
        
        # Draw preview content
        surface.blit(
            self.preview_surface, 
            (self.preview_rect.left + self.preview_border, 
             self.preview_rect.top + self.preview_border)
        )
    
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
        
        # Render world preview
        self.render_world_preview(surface)
        
        # Render terminal content - completed messages (on the left side)
        content_x = self.terminal_rect.left + 30
        start_y = subtitle_y + 80
        
        message_y = start_y
        for i, line in enumerate(self.completed_messages):
            text = f"[COMPLETED] {line}"
            message_surface = self.message_font.render(text, True, (100, 255, 100))
            surface.blit(message_surface, (content_x, message_y))
            message_y += int(TILE_SIZE * 12 * self.scale_factor)
            
        # Render current message with fading
        if self.current_message_index < len(self.messages):
            current_text = f"[IN PROGRESS] {self.messages[self.current_message_index]}"
            curr_message_surface = self.message_font.render(current_text, True, TERMINAL_GREEN)
            
            # Create alpha surface for fading
            alpha_surface = pygame.Surface(curr_message_surface.get_size(), pygame.SRCALPHA)
            alpha_surface.fill((255, 255, 255, self.message_alpha))
            curr_message_surface.blit(alpha_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            
            surface.blit(curr_message_surface, (content_x, message_y))
        
        # Calculate estimated time remaining
        time_remaining_ms = max(0, int(self.estimated_time * (1.0 - self.progress)))
        time_remaining_sec = time_remaining_ms // 1000
        
        # Draw estimated time
        time_text = f"ESTIMATED TIME REMAINING: {time_remaining_sec} SECONDS"
        time_surface = self.message_font.render(time_text, True, TERMINAL_GREEN)
        time_y = self.terminal_rect.bottom - 80
        time_x = self.terminal_rect.centerx - time_surface.get_width() // 2
        surface.blit(time_surface, (time_x, time_y))
            
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