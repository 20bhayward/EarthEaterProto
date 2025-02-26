# EarthEaterProto

A 2D pixel-voxel game prototype where an alien digs through a destructible world with physics simulation and gravity.

## Features

- Destructible terrain using a tile-based world
- Simple physics simulation with gravity
- Falling sand and materials
- Player character that can move, jump, and dig
- Chunk-based world generation for performance

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

- **A/Left Arrow**: Move left
- **D/Right Arrow**: Move right  
- **Space**: Jump
- **E/Ctrl**: Dig through terrain
- **Escape**: Quit game

## Development

This is a prototype for a larger game. Future improvements may include:

- More material types with different properties
- Enemies and NPCs
- Resource collection and crafting
- More elaborate world generation
- Improved graphics and animations

## Requirements

- Python 3.8+
- Pygame 2.0.0+
- NumPy 1.20.0+
