# CLAUDE.md - Configuration for Claude AI Assistant

## Project: EarthEaterProto

A Noita-inspired 2D pixel-voxel game where an alien digs through an infinite procedurally generated destructible world with advanced physics simulation, dynamic lighting, and particle effects.

### Build, Lint & Test Commands
- Build: `python -m pip install -e .` (for development)
- Run: `python -m eartheater`
- Test: `pytest tests/`
- Single test: `pytest tests/[test_file.py] -k [test_name]`

### Code Style Guidelines
- **Language**: Python with Pygame for rendering and physics
- **Dependencies**: pygame, numpy, noise (for procedural generation)
- **Formatting**: 4 spaces indentation, 88 character line limit
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Types**: Use type hints for function parameters and return values
- **Documentation**: Docstrings for all functions and classes, following Google style guide
- **Module Structure**: 
  - Separate modules for physics, rendering, entities, and world generation
  - Follow a component-based approach where possible
  - Maintain clear boundaries between systems for easy modification

### World Architecture
- **Chunks**: World is divided into chunks for efficient loading/unloading
- **Procedural Generation**: Uses Perlin noise for terrain and cave generation
- **Materials**: Each material has properties like density, falling behavior, and liquidity
- **Physics**: Cellular automata-based physics with staggered updates for performance
- **Rendering**: Layer-based rendering with support for dynamic lighting and particles

### Player Mechanics
- **Movement**: Smooth movement with acceleration and friction
- **Jetpack**: Limited fuel jetpack for flying with particle effects
- **Digging**: Can destroy terrain, leaving realistic destruction

### Controls
- WASD: Movement
- Space: Jump/Jetpack
- Ctrl: Dig
- F3: Debug overlay
- P: Pause
- Escape: Quit