# CLAUDE.md - Configuration for Claude AI Assistant

## Project: EarthEaterProto

A 2D pixel-voxel game where an alien digs through a destructible world with physics simulation and gravity.

### Build, Lint & Test Commands
- Build: `python -m pip install -e .` (for development)
- Run: `python -m eartheater`
- Test: `pytest tests/`
- Single test: `pytest tests/[test_file.py] -k [test_name]`

### Code Style Guidelines
- **Language**: Python with Pygame for rendering and physics
- **Formatting**: 4 spaces indentation, 88 character line limit
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Types**: Use type hints for function parameters and return values
- **Module Structure**: Separate modules for physics, rendering, entities, and world generation
- **World Design**: Chunk-based storage of world tiles for efficient memory usage
- **Physics**: Simple cellular automata for material physics simulation
- **Game Loop**: Fixed timestep for consistent physics simulation

### Project Organization
- `eartheater/` - Main package
  - `world.py` - World and chunk management
  - `physics.py` - Physics simulation
  - `entities.py` - Player and other entities
  - `render.py` - Drawing and display