# CLAUDE.md - Configuration for Claude AI Assistant

## Project: EarthEaterProto

A Noita-inspired 2D pixel-voxel game where an alien digs through an infinite procedurally generated destructible world with advanced physics simulation, dynamic lighting, and particle effects.

## Development Environment

### Build & Run Commands
- Build: `python -m pip install -e .` (for development)
- Run: `python -m eartheater`
- Test: `pytest tests/`
- Single test: `pytest tests/[test_file.py] -k [test_name]`

### Project Structure
- **eartheater/**: Main package
  - **constants.py**: Game constants, enums, and configuration
  - **game.py**: Main game loop and state management
  - **world.py**: World generation and chunk management
  - **physics.py**: Physics simulation and material behavior
  - **render.py**: Rendering logic and camera system
  - **entities.py**: Player and other game entities
  - **ui.py**: UI components and game interface

## Code Style Guidelines

### General
- **Language**: Python 3.8+ with Pygame for rendering and physics
- **Dependencies**: pygame, numpy, noise (for procedural generation)
- **Formatting**: 4 spaces indentation, 88 character line limit
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Types**: Use type hints for function parameters and return values
- **Documentation**: Docstrings for all functions and classes, following Google style guide
- **Error Handling**: Wrap complex operations (especially world generation) in try/except blocks

### System Design
- **Module Structure**: 
  - Separate modules for physics, rendering, entities, and world generation
  - Follow a component-based approach where possible
  - Maintain clear boundaries between systems for easy modification
- **Performance**: 
  - Use caching for noise calculations and terrain heights
  - Limit physics simulation to chunks near the player
  - Use object pooling for particles and other frequently created objects

## World Generation Architecture

### Core Concepts
- **Chunks**: World is divided into 64x64 chunks for efficient loading/unloading
- **Biome System**: 
  - 3-layer system: sky, surface, underground
  - Surface: meadow, desert, mountain, forest
  - Underground: underground, depths, abyss, volcanic
  - Uses noise-based blending for natural biome transitions

### Generation Techniques
- **Procedural Generation**: 
  - Multi-layered Perlin noise for terrain shapes
  - Large-scale noise for major landforms and biome transitions
  - Medium-scale noise for hills and terrain features
  - Small-scale noise for surface details
- **Cave Generation**:
  - Uses 3D Perlin noise for connected cave networks
  - Dynamic cave density based on depth and biome
  - Special formations in deeper biomes

### Material System
- **Material Properties**: Each material has specific attributes
  - Density: Determines falling behavior and weight
  - Liquidity: Controls flow behavior for liquids and semi-solids
  - Hardness: Affects digging difficulty
- **Material Distribution**:
  - Surface materials based on biome (grass, sand, stone)
  - Underground materials with large-scale variation (dirt, clay, stone, ores)
  - Distinct ore veins and material deposits using noise patterns

## Game Systems

### Physics System
- **Material Simulation**: Cellular automata-based physics
- **Staggered Updates**: Only process fractions of the world each frame
- **Physics Radius**: Smaller active radius than rendering for performance
- **Material Interactions**: Support for liquids, falling materials, and destruction

### Rendering System
- **Layer-Based Rendering**: Multiple render passes for different elements
- **Dynamic Lighting**: Support for ambient, directional, and point lights
- **Particle System**: Handles visual effects like dust, debris, and jetpack exhaust
- **Camera**: Smooth follow camera with configurable parameters

### Player Mechanics
- **Movement**: Smooth movement with acceleration and friction
- **Jetpack**: Limited fuel jetpack for flying with particle effects
- **Digging**: Can destroy terrain, leaving realistic destruction
- **Physics Interaction**: Player interacts with materials and is affected by liquids/gravity

### Controls
- WASD: Movement
- Space: Jump/Jetpack
- Left Mouse: Dig
- Ctrl: Alternate dig method
- F3: Debug overlay
- P: Pause
- Escape: Quit

## Known Issues & Optimizations

### Performance Considerations
- World generation is CPU-intensive, particularly with large radius settings
- Loading screen uses progressive loading to prevent freezing
- Heavy physics simulation can cause slowdown with many active materials
- Use reduced rendering detail when FPS drops below target

### Bug Workarounds
- Fix for loading screen crashes by limiting chunk batch size to 1
- Added error handling for noise function exceptions
- Use try/except blocks for critical world generation functions
- Keep a smaller initial chunk radius to ensure stable loading
- Water generation logic adjusted to prevent out-of-bounds errors

### Future Improvements
- Better multi-threading support for world generation
- GPU acceleration for particle effects and material simulation
- More robust error recovery mechanisms
- Memory optimization for large worlds
- Enhanced biome transitions and feature generation