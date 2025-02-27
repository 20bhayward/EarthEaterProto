# EarthEaterProto

A 2D pixel-voxel game prototype where an alien digs through a destructible world with advanced physics simulation and stunning visual effects, inspired by games like Noita.

![Game Screenshot](screenshot.png)

## Features

- **Destructible Terrain**: Fully destructible terrain with realistic physics
- **Infinite Procedural World**: Explore a never-ending world with varied biomes and caves
- **Physics Simulation**: Advanced physics for realistic material interactions
  - Sand cascades and flows through gaps
  - Liquids (water, lava) flow realistically with surface tension
  - All terrain types including dirt can fall when unsupported
- **Particle Effects**: Detailed particle effects for digging, jetpack, and environment
- **Smooth Movement**: Fluid character movement with acceleration and friction
- **Jetpack**: Limited fuel jetpack for flying and exploring
- **Dynamic Lighting**: Real-time lighting effects including player light and ambient darkness
- **Chunk-Based World**: Efficient chunk-based world loading for optimal performance

## Materials

The world contains various materials with unique properties:
- **Air**: Empty space
- **Dirt**: Common terrain that falls when unsupported
- **Stone**: Hard material for cave walls and deep underground
- **Sand**: Flows and falls like real sand
- **Gravel**: Similar to sand but heavier
- **Water**: Flows freely, can be swum through
- **Lava**: Deadly liquid that emits light
- **Wood**: Sturdy material for structures

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/EarthEaterProto.git
   cd EarthEaterProto
   ```

2. Install the game in development mode:
   ```
   python -m pip install -e .
   ```

## Running the Game

Start the game with:

```
python -m eartheater
```

## Controls

- **W/A/S/D**: Movement (up, left, down, right)
- **Space**: Jump when on ground, activates jetpack when airborne
- **Ctrl**: Dig through terrain
- **F3**: Toggle debug overlay
- **P**: Pause game
- **Escape**: Quit game

## Development

This game focuses on creating a Noita-like experience with these core mechanics:
- Every pixel in the world is simulated
- Destruction alters the world permanently
- Materials interact realistically with each other
- Smooth movement through a dynamic environment

Future features may include:
- Enemies with AI behaviors
- More material interactions (fire, explosions, electricity)
- Environmental hazards
- Player upgrades and power-ups
- Sound effects and music

## Requirements

- Python 3.8+
- Pygame 2.0.0+
- NumPy 1.20.0+
- noise 1.2.2+ (for Perlin noise generation)

## Performance Notes

This prototype has different performance characteristics depending on your system:

### Linux
- The game may be laggy on VMs or systems with limited resources
- Performance optimizations have been implemented to help with Linux performance
- Try reducing window size if you experience lag
- Pygame's hardware acceleration may not work well on some Linux configurations

### Windows
- Generally better performance on Windows systems
- If the game crashes during generation, try the following:
  1. Install Python 3.8+ and the required dependencies manually
  2. Use a virtual environment
  3. Try a smaller initial chunk radius (edit constants.py)

### General Performance Tips
1. Reduce active chunks radius in constants.py (ACTIVE_CHUNKS_RADIUS)
2. Disable fullscreen mode in constants.py (set FULLSCREEN = False)
3. Reduce physics simulation frequency
4. For developers: Consider building pygame with AVX2 support if your CPU supports it
