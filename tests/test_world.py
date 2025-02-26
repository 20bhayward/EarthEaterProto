"""
Tests for the world module
"""
import pytest
import numpy as np

from eartheater.world import World, Chunk
from eartheater.constants import MaterialType, CHUNK_SIZE


def test_chunk_creation():
    """Test that a chunk can be created with the correct dimensions"""
    chunk = Chunk(0, 0)
    assert chunk.x == 0
    assert chunk.y == 0
    assert chunk.tiles.shape == (CHUNK_SIZE, CHUNK_SIZE)
    assert chunk.needs_update is True


def test_chunk_set_get_tile():
    """Test setting and getting tiles in a chunk"""
    chunk = Chunk(0, 0)
    
    # Initially all tiles should be air
    assert chunk.get_tile(0, 0) == MaterialType.AIR
    
    # Set and check a tile
    chunk.set_tile(5, 7, MaterialType.DIRT)
    assert chunk.get_tile(5, 7) == MaterialType.DIRT
    assert chunk.needs_update is True
    
    # Set another tile
    chunk.set_tile(10, 8, MaterialType.STONE)
    assert chunk.get_tile(10, 8) == MaterialType.STONE


def test_world_creation():
    """Test that a world can be created and has the expected chunks"""
    world = World()
    
    # Check that chunks exist
    assert len(world.chunks) > 0
    
    # Test getting a chunk
    first_chunk = world.get_chunk(0, 0)
    assert first_chunk is not None
    assert isinstance(first_chunk, Chunk)
    assert first_chunk.x == 0
    assert first_chunk.y == 0


def test_world_get_set_tile():
    """Test setting and getting tiles in the world"""
    world = World()
    
    # Set and check a tile
    world.set_tile(5, 7, MaterialType.DIRT)
    assert world.get_tile(5, 7) == MaterialType.DIRT
    
    # Set another tile
    world.set_tile(20, 15, MaterialType.STONE)
    assert world.get_tile(20, 15) == MaterialType.STONE
    
    # Check out of bounds
    assert world.get_tile(-1, -1) == MaterialType.AIR
    
    # Setting out of bounds should not raise an error
    world.set_tile(-1, -1, MaterialType.DIRT)


def test_world_active_chunks():
    """Test getting active chunks"""
    world = World()
    active_chunks = world.get_active_chunks()
    
    # All chunks should be active
    assert len(active_chunks) == len(world.chunks)
    
    # All chunks should be instances of Chunk
    for chunk in active_chunks:
        assert isinstance(chunk, Chunk)