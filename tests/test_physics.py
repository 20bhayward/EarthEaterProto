"""
Tests for the physics module
"""
import pytest

from eartheater.world import World
from eartheater.physics import PhysicsEngine
from eartheater.constants import MaterialType


def test_physics_engine_creation():
    """Test that a physics engine can be created"""
    world = World()
    physics = PhysicsEngine(world)
    assert physics.world == world
    assert len(physics.pending_updates) == 0


def test_physics_falling_materials():
    """Test that materials with gravity actually fall"""
    world = World()
    physics = PhysicsEngine(world)
    
    # Create a sand block floating in air
    x, y = 10, 10
    world.set_tile(x, y, MaterialType.SAND)
    
    # Make sure blocks below are air
    for i in range(1, 4):
        world.set_tile(x, y + i, MaterialType.AIR)
    
    # Run physics for a few steps
    for _ in range(3):
        physics.update()
    
    # The sand should have moved down
    assert world.get_tile(x, y) == MaterialType.AIR
    assert world.get_tile(x, y + 1) == MaterialType.SAND or world.get_tile(x, y + 2) == MaterialType.SAND or world.get_tile(x, y + 3) == MaterialType.SAND


def test_physics_blocked_materials():
    """Test that materials don't fall through solid blocks"""
    world = World()
    physics = PhysicsEngine(world)
    
    # Create a sand block
    x, y = 10, 10
    world.set_tile(x, y, MaterialType.SAND)
    
    # Create a solid block below
    world.set_tile(x, y + 1, MaterialType.STONE)
    
    # Run physics for a few steps
    for _ in range(3):
        physics.update()
    
    # The sand should not have moved
    assert world.get_tile(x, y) == MaterialType.SAND
    assert world.get_tile(x, y + 1) == MaterialType.STONE


def test_physics_collision_detection():
    """Test collision detection"""
    world = World()
    physics = PhysicsEngine(world)
    
    # Create an empty area
    for x in range(5, 15):
        for y in range(5, 15):
            world.set_tile(x, y, MaterialType.AIR)
    
    # No collision in empty space
    assert not physics.check_collision(10, 10, 2, 2)
    
    # Create a block
    world.set_tile(11, 11, MaterialType.STONE)
    
    # Should collide now
    assert physics.check_collision(10, 10, 2, 2)
    
    # No collision if we're not overlapping
    assert not physics.check_collision(8, 8, 2, 2)


def test_physics_dig():
    """Test digging functionality"""
    world = World()
    physics = PhysicsEngine(world)
    
    # Create a solid area
    for x in range(8, 13):
        for y in range(8, 13):
            world.set_tile(x, y, MaterialType.STONE)
    
    # Dig at the center
    physics.dig(10, 10, 1)
    
    # Check that the center and adjacent tiles are now air
    assert world.get_tile(10, 10) == MaterialType.AIR
    assert world.get_tile(9, 10) == MaterialType.AIR
    assert world.get_tile(11, 10) == MaterialType.AIR
    assert world.get_tile(10, 9) == MaterialType.AIR
    assert world.get_tile(10, 11) == MaterialType.AIR
    
    # Diagonal corners should still be stone (radius=1)
    assert world.get_tile(9, 9) == MaterialType.STONE