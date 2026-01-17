"""
Memory Channel Visualizer - Blender Scene Generator
====================================================

Cyberpunk-style 3D visualization of memory channel transaction flow.

Compatible with Blender 2.83+ (tested on 2.83.20 and 4.0)

USAGE:
------
Option 1 - GUI:
  1. Open Blender
  2. Go to "Scripting" workspace (tab at top)
  3. Click "Open" and select this file
  4. Click "Run Script" (play button) or press Alt+P

Option 2 - Command line (headless render):
  blender --background --python blender_channel_scene.py

This will:
- Create the scene with all structures
- Set up cyberpunk lighting and materials
- Position camera for top-down isometric view
- Add a sample transaction animation

Author: Channel Viz Tool
Style: Dark Cyberpunk with neon glows
"""

import bpy
import bmesh
import math
import random
from mathutils import Vector

# ============================================================================
# CONFIGURATION
# ============================================================================

# Colors (RGB, 0-1 range) - Cyberpunk palette
COLORS = {
    'wcache': (0.2, 0.9, 0.3, 1.0),          # Neon green
    'write_rs': (1.0, 0.5, 0.0, 1.0),        # Neon orange
    'read_rs': (0.0, 0.6, 1.0, 1.0),         # Neon blue
    'dram': (0.8, 0.2, 0.9, 1.0),            # Neon purple/magenta
    'read_return': (0.0, 0.9, 0.9, 1.0),     # Neon cyan
    'background': (0.02, 0.02, 0.04, 1.0),   # Very dark blue
    'floor': (0.03, 0.03, 0.05, 1.0),        # Dark floor
    'grid': (0.1, 0.1, 0.15, 1.0),           # Grid lines
    'transaction_read': (0.0, 0.8, 1.0, 1.0),   # Cyan for reads
    'transaction_write': (1.0, 0.4, 0.0, 1.0),  # Orange for writes
}

# SIMPLE VERTICAL LAYOUT - boxes stacked top to bottom
# Balls fall down with gravity through the system
STRUCTURES = {
    'wcache': {
        'pos': (-3, 10, 0),     # TOP LEFT
        'size': (3, 2, 3),
        'color': 'wcache',
    },
    'read_rs': {
        'pos': (3, 10, 0),      # TOP RIGHT
        'size': (3, 2, 3),
        'color': 'read_rs',
    },
    'write_rs': {
        'pos': (-3, 5, 0),      # MIDDLE LEFT
        'size': (3, 2, 3),
        'color': 'write_rs',
    },
    'dram': {
        'pos': (0, 0, 0),       # BOTTOM CENTER
        'size': (5, 2, 3),
        'color': 'dram',
    },
    'read_return': {
        'pos': (3, 5, 0),       # MIDDLE RIGHT
        'size': (3, 2, 3),
        'color': 'read_return',
    },
}

# Animation settings
FPS = 30
TRANSACTION_SPEED = 0.5  # Units per frame


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def clear_scene():
    """Remove all objects from the scene - aggressive cleanup."""
    # Delete all objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # Also delete any remaining objects directly
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    
    # Clear materials
    for material in bpy.data.materials:
        bpy.data.materials.remove(material)
    
    # Clear meshes
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    
    # Clear curves
    for curve in bpy.data.curves:
        bpy.data.curves.remove(curve)
    
    # Clear cameras
    for camera in bpy.data.cameras:
        bpy.data.cameras.remove(camera)
    
    # Clear lights
    for light in bpy.data.lights:
        bpy.data.lights.remove(light)


def create_emission_material(name, color, emission_strength=5.0):
    """Create a glowing emission material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    nodes.clear()
    
    # Create nodes
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (300, 0)
    
    # Mix shader for glow + slight transparency
    mix = nodes.new('ShaderNodeMixShader')
    mix.location = (100, 0)
    mix.inputs[0].default_value = 0.1  # 90% emission, 10% transparent
    
    # Emission shader
    emission = nodes.new('ShaderNodeEmission')
    emission.location = (-100, 50)
    emission.inputs['Color'].default_value = color
    emission.inputs['Strength'].default_value = emission_strength
    
    # Transparent shader
    transparent = nodes.new('ShaderNodeBsdfTransparent')
    transparent.location = (-100, -50)
    
    # Connect
    links.new(emission.outputs['Emission'], mix.inputs[1])
    links.new(transparent.outputs['BSDF'], mix.inputs[2])
    links.new(mix.outputs['Shader'], output.inputs['Surface'])
    
    return mat


def create_glass_material(name, color, emission_strength=2.0):
    """Create a glassy material with edge glow."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.blend_method = 'BLEND'
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    nodes.clear()
    
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (400, 0)
    
    mix = nodes.new('ShaderNodeMixShader')
    mix.location = (200, 0)
    
    # Glass-like principled BSDF
    principled = nodes.new('ShaderNodeBsdfPrincipled')
    principled.location = (-100, 100)
    principled.inputs['Base Color'].default_value = color
    principled.inputs['Alpha'].default_value = 0.3
    principled.inputs['Roughness'].default_value = 0.1
    principled.inputs['Metallic'].default_value = 0.5
    
    # Emission for edges
    emission = nodes.new('ShaderNodeEmission')
    emission.location = (-100, -100)
    emission.inputs['Color'].default_value = color
    emission.inputs['Strength'].default_value = emission_strength
    
    # Fresnel for edge detection
    fresnel = nodes.new('ShaderNodeFresnel')
    fresnel.location = (-100, 0)
    fresnel.inputs['IOR'].default_value = 1.5
    
    # Connect
    links.new(fresnel.outputs['Fac'], mix.inputs[0])
    links.new(principled.outputs['BSDF'], mix.inputs[1])
    links.new(emission.outputs['Emission'], mix.inputs[2])
    links.new(mix.outputs['Shader'], output.inputs['Surface'])
    
    return mat


def create_structure_box(name, pos, size, color_name):
    """Create a structure box with cyberpunk styling - open top container for physics."""
    # Create the visible box (slightly smaller, for visuals only)
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    
    # Apply scale
    bpy.ops.object.transform_apply(scale=True)
    
    # Add bevel for rounded edges
    bpy.ops.object.modifier_add(type='BEVEL')
    obj.modifiers['Bevel'].width = 0.1
    obj.modifiers['Bevel'].segments = 3
    bpy.ops.object.modifier_apply(modifier='Bevel')
    
    # Create and assign material
    color = COLORS[color_name]
    mat = create_glass_material(f"mat_{name}", color)
    obj.data.materials.append(mat)
    
    return obj




def create_floor():
    """Create a dark floor with grid pattern."""
    # Main floor
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.name = "Floor"
    
    # Floor material
    mat = bpy.data.materials.new(name="FloorMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (300, 0)
    
    principled = nodes.new('ShaderNodeBsdfPrincipled')
    principled.location = (0, 0)
    principled.inputs['Base Color'].default_value = COLORS['floor']
    principled.inputs['Roughness'].default_value = 0.8
    principled.inputs['Metallic'].default_value = 0.2
    
    links.new(principled.outputs['BSDF'], output.inputs['Surface'])
    
    floor.data.materials.append(mat)
    
    return floor


def create_grid_lines():
    """Create subtle grid lines on the floor."""
    # Create a grid using curves
    grid_spacing = 2
    grid_extent = 12
    
    # Create line material
    mat = bpy.data.materials.new(name="GridMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    output = nodes.new('ShaderNodeOutputMaterial')
    emission = nodes.new('ShaderNodeEmission')
    emission.inputs['Color'].default_value = (0.1, 0.15, 0.2, 1.0)
    emission.inputs['Strength'].default_value = 0.5
    links.new(emission.outputs['Emission'], output.inputs['Surface'])
    
    # Create grid lines
    for i in range(-grid_extent, grid_extent + 1, grid_spacing):
        # X-direction lines
        bpy.ops.curve.primitive_bezier_curve_add()
        curve = bpy.context.active_object
        curve.name = f"GridLineX_{i}"
        curve.data.bevel_depth = 0.02
        
        # Set points
        spline = curve.data.splines[0]
        spline.bezier_points[0].co = Vector((-grid_extent, 0.01, i))
        spline.bezier_points[0].handle_left = Vector((-grid_extent, 0.01, i))
        spline.bezier_points[0].handle_right = Vector((-grid_extent, 0.01, i))
        spline.bezier_points[1].co = Vector((grid_extent, 0.01, i))
        spline.bezier_points[1].handle_left = Vector((grid_extent, 0.01, i))
        spline.bezier_points[1].handle_right = Vector((grid_extent, 0.01, i))
        
        curve.data.materials.append(mat)
        
        # Z-direction lines
        bpy.ops.curve.primitive_bezier_curve_add()
        curve = bpy.context.active_object
        curve.name = f"GridLineZ_{i}"
        curve.data.bevel_depth = 0.02
        
        spline = curve.data.splines[0]
        spline.bezier_points[0].co = Vector((i, 0.01, -grid_extent))
        spline.bezier_points[0].handle_left = Vector((i, 0.01, -grid_extent))
        spline.bezier_points[0].handle_right = Vector((i, 0.01, -grid_extent))
        spline.bezier_points[1].co = Vector((i, 0.01, grid_extent))
        spline.bezier_points[1].handle_left = Vector((i, 0.01, grid_extent))
        spline.bezier_points[1].handle_right = Vector((i, 0.01, grid_extent))
        
        curve.data.materials.append(mat)


def create_sphere_material_3d(name, color, emission_strength=5.0):
    """Create a 3D-looking sphere material with glow, specular, and depth."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (600, 0)
    
    # Mix emission with glossy for that 3D bouncy ball look
    mix_shader = nodes.new('ShaderNodeMixShader')
    mix_shader.location = (400, 0)
    mix_shader.inputs[0].default_value = 0.3  # 70% glossy, 30% emission
    
    # Glossy/reflective component for 3D depth
    glossy = nodes.new('ShaderNodeBsdfGlossy')
    glossy.location = (100, 100)
    glossy.inputs['Color'].default_value = color
    glossy.inputs['Roughness'].default_value = 0.15  # Shiny but not mirror
    
    # Emission for glow
    emission = nodes.new('ShaderNodeEmission')
    emission.location = (100, -100)
    emission.inputs['Color'].default_value = color
    emission.inputs['Strength'].default_value = emission_strength
    
    # Fresnel for edge glow effect (rim lighting)
    fresnel = nodes.new('ShaderNodeFresnel')
    fresnel.location = (-100, 0)
    fresnel.inputs['IOR'].default_value = 1.45
    
    # Another mix for fresnel-based rim glow
    mix_fresnel = nodes.new('ShaderNodeMixShader')
    mix_fresnel.location = (250, 50)
    
    # Bright rim emission
    rim_emission = nodes.new('ShaderNodeEmission')
    rim_emission.location = (100, -200)
    rim_emission.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)  # White rim
    rim_emission.inputs['Strength'].default_value = 3.0
    
    # Connect: glossy + rim -> then mix with core emission
    links.new(fresnel.outputs['Fac'], mix_fresnel.inputs[0])
    links.new(glossy.outputs['BSDF'], mix_fresnel.inputs[1])
    links.new(rim_emission.outputs['Emission'], mix_fresnel.inputs[2])
    
    links.new(mix_fresnel.outputs['Shader'], mix_shader.inputs[1])
    links.new(emission.outputs['Emission'], mix_shader.inputs[2])
    links.new(mix_shader.outputs['Shader'], output.inputs['Surface'])
    
    return mat


def create_transaction_sphere(name, color_name, location=(0, 1.5, 5)):
    """Create a glowing 3D transaction sphere with rigid body physics."""
    # Higher subdivision for smoother sphere
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.4, segments=24, ring_count=16, location=location)
    sphere = bpy.context.active_object
    sphere.name = name
    
    # Smooth shading
    bpy.ops.object.shade_smooth()
    
    # Create 3D material with specular and glow
    color = COLORS.get(color_name, COLORS['transaction_read'])
    mat = create_sphere_material_3d(f"mat_{name}", color, emission_strength=8.0)
    sphere.data.materials.append(mat)
    
    # Add rigid body physics
    bpy.context.view_layer.objects.active = sphere
    bpy.ops.rigidbody.object_add(type='ACTIVE')
    sphere.rigid_body.mass = 1.0
    sphere.rigid_body.collision_shape = 'SPHERE'
    sphere.rigid_body.friction = 0.5
    sphere.rigid_body.restitution = 0.65  # Good bounce
    sphere.rigid_body.linear_damping = 0.2
    sphere.rigid_body.angular_damping = 0.3
    # Start as kinematic (we control it)
    sphere.rigid_body.kinematic = True
    
    return sphere


def setup_physics_world():
    """Set up rigid body physics world."""
    scene = bpy.context.scene
    if scene.rigidbody_world is None:
        bpy.ops.rigidbody.world_add()
    
    rbw = scene.rigidbody_world
    rbw.enabled = True
    rbw.point_cache.frame_start = 1
    rbw.point_cache.frame_end = 600
    rbw.substeps_per_frame = 5
    rbw.solver_iterations = 15


def create_container_walls(name, pos, size):
    """Create invisible collision walls for a container (floor + 4 walls, open top)."""
    thickness = 0.15
    sx, sy, sz = size
    walls = []
    
    # Floor
    bpy.ops.mesh.primitive_cube_add(size=1, location=(pos[0], pos[1] - sy/2, pos[2]))
    floor = bpy.context.active_object
    floor.name = f"{name}_floor"
    floor.scale = (sx + 0.2, thickness, sz + 0.2)
    bpy.ops.object.transform_apply(scale=True)
    walls.append(floor)
    
    # Front wall (+Z)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(pos[0], pos[1], pos[2] + sz/2))
    w = bpy.context.active_object
    w.name = f"{name}_front"
    w.scale = (sx + 0.2, sy, thickness)
    bpy.ops.object.transform_apply(scale=True)
    walls.append(w)
    
    # Back wall (-Z)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(pos[0], pos[1], pos[2] - sz/2))
    w = bpy.context.active_object
    w.name = f"{name}_back"
    w.scale = (sx + 0.2, sy, thickness)
    bpy.ops.object.transform_apply(scale=True)
    walls.append(w)
    
    # Left wall (-X)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(pos[0] - sx/2, pos[1], pos[2]))
    w = bpy.context.active_object
    w.name = f"{name}_left"
    w.scale = (thickness, sy, sz + 0.2)
    bpy.ops.object.transform_apply(scale=True)
    walls.append(w)
    
    # Right wall (+X)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(pos[0] + sx/2, pos[1], pos[2]))
    w = bpy.context.active_object
    w.name = f"{name}_right"
    w.scale = (thickness, sy, sz + 0.2)
    bpy.ops.object.transform_apply(scale=True)
    walls.append(w)
    
    # Make walls passive rigid bodies, invisible
    for wall in walls:
        bpy.context.view_layer.objects.active = wall
        bpy.ops.rigidbody.object_add(type='PASSIVE')
        wall.rigid_body.collision_shape = 'BOX'
        wall.rigid_body.friction = 0.5
        wall.rigid_body.restitution = 0.7
        wall.hide_render = True
        wall.display_type = 'WIRE'
    
    return walls


def create_text_label(text, location, color, scale=0.5):
    """Create a simple text label facing forward (+Z)."""
    bpy.ops.object.text_add(location=location)
    text_obj = bpy.context.active_object
    text_obj.name = f"Label_{text}"
    text_obj.data.body = text
    
    text_obj.data.size = scale
    text_obj.data.align_x = 'CENTER'
    text_obj.data.align_y = 'CENTER'
    text_obj.data.extrude = 0.02
    
    # Face forward (toward camera which is on +Z)
    # No rotation needed - default text faces +Z
    
    # Bright emission material
    mat = create_emission_material(f"mat_label_{text}", (*color[:3], 1.0), emission_strength=12.0)
    text_obj.data.materials.append(mat)
    
    return text_obj


def create_tube(name, start_pos, end_pos, radius=0.5, color=(0.3, 0.3, 0.4, 1.0)):
    """Create a tube (cylinder) between two points for balls to roll through."""
    # Calculate tube properties
    dx = end_pos[0] - start_pos[0]
    dy = end_pos[1] - start_pos[1]
    dz = end_pos[2] - start_pos[2]
    length = math.sqrt(dx*dx + dy*dy + dz*dz)
    
    # Midpoint
    mid = ((start_pos[0] + end_pos[0])/2, (start_pos[1] + end_pos[1])/2, (start_pos[2] + end_pos[2])/2)
    
    # Create cylinder
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=length, location=mid)
    tube = bpy.context.active_object
    tube.name = name
    
    # Calculate rotation to point from start to end
    # Default cylinder points along Z axis
    direction = Vector((dx, dy, dz)).normalized()
    up = Vector((0, 0, 1))
    
    if direction.dot(up) < 0.999:
        rot_axis = up.cross(direction).normalized()
        rot_angle = math.acos(up.dot(direction))
        tube.rotation_mode = 'AXIS_ANGLE'
        tube.rotation_axis_angle = (rot_angle, rot_axis.x, rot_axis.y, rot_axis.z)
        bpy.context.view_layer.update()
        tube.rotation_mode = 'XYZ'
    
    # Apply transforms
    bpy.ops.object.transform_apply(rotation=True)
    
    # Make it hollow (tube, not solid cylinder) using boolean or solidify
    # For simplicity, we'll create an inner cylinder to subtract
    # Actually, let's use a different approach - create a curved path with bevel
    
    # For collision, make it a passive rigid body with MESH collision
    bpy.context.view_layer.objects.active = tube
    bpy.ops.rigidbody.object_add(type='PASSIVE')
    tube.rigid_body.collision_shape = 'MESH'
    tube.rigid_body.friction = 0.3
    tube.rigid_body.restitution = 0.5
    
    # Semi-transparent material
    mat = create_glass_material(f"mat_{name}", color, emission_strength=0.5)
    tube.data.materials.append(mat)
    
    return tube


def create_curved_tube(name, points, radius=0.6, segments=16):
    """Create a curved tube along a path using bezier curve with bevel."""
    # Create bezier curve
    curve_data = bpy.data.curves.new(name=f"curve_{name}", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.bevel_depth = radius
    curve_data.bevel_resolution = 4
    curve_data.fill_mode = 'FULL'
    
    # Create spline
    spline = curve_data.splines.new('BEZIER')
    spline.bezier_points.add(len(points) - 1)
    
    for i, pt in enumerate(points):
        bp = spline.bezier_points[i]
        bp.co = Vector(pt)
        bp.handle_type_left = 'AUTO'
        bp.handle_type_right = 'AUTO'
    
    # Create object
    tube_obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(tube_obj)
    bpy.context.view_layer.objects.active = tube_obj
    tube_obj.select_set(True)
    
    # Convert to mesh for rigid body
    bpy.ops.object.convert(target='MESH')
    
    # Make hollow by removing interior (use wireframe modifier approach)
    # Actually for collision we want the outer surface
    
    # Add rigid body
    bpy.ops.rigidbody.object_add(type='PASSIVE')
    tube_obj.rigid_body.collision_shape = 'MESH'
    tube_obj.rigid_body.friction = 0.2  # Low friction so balls slide
    tube_obj.rigid_body.restitution = 0.4
    tube_obj.rigid_body.use_margin = True
    tube_obj.rigid_body.collision_margin = 0.04
    
    # Semi-transparent material
    mat = create_glass_material(f"mat_{name}", (0.2, 0.4, 0.6, 1.0), emission_strength=0.8)
    tube_obj.data.materials.append(mat)
    
    return tube_obj


def create_ramp(name, start_pos, end_pos, width=1.5, color=(0.2, 0.3, 0.4, 1.0)):
    """Create a simple flat ramp between two points."""
    dx = end_pos[0] - start_pos[0]
    dy = end_pos[1] - start_pos[1]
    dz = end_pos[2] - start_pos[2]
    length = math.sqrt(dx*dx + dy*dy + dz*dz)
    mid = ((start_pos[0]+end_pos[0])/2, (start_pos[1]+end_pos[1])/2, (start_pos[2]+end_pos[2])/2)
    
    # Create a plane (flat ramp)
    bpy.ops.mesh.primitive_plane_add(size=1, location=mid)
    ramp = bpy.context.active_object
    ramp.name = name
    ramp.scale = (width, length, 1)
    bpy.ops.object.transform_apply(scale=True)
    
    # Calculate rotation to connect start to end
    # We need to rotate the plane so it slopes from start to end
    direction = Vector((dx, dy, dz)).normalized()
    
    # Calculate pitch (slope angle)
    horizontal_dist = math.sqrt(dx*dx + dz*dz)
    pitch = math.atan2(dy, horizontal_dist)
    
    # Calculate yaw (direction angle)
    yaw = math.atan2(dx, -dz)
    
    ramp.rotation_euler = (pitch + math.radians(90), 0, yaw)
    bpy.ops.object.transform_apply(rotation=True)
    
    # Add side rails (so balls don't fall off)
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=mid)
        rail = bpy.context.active_object
        rail.name = f"{name}_rail_{side}"
        rail.scale = (0.1, length, 0.3)
        bpy.ops.object.transform_apply(scale=True)
        
        # Position to side
        offset = Vector((side * width/2 * 0.9, 0, 0.15))
        rail.location = Vector(mid) + offset
        rail.rotation_euler = (pitch + math.radians(90), 0, yaw)
        bpy.ops.object.transform_apply(rotation=True)
        
        # Rigid body for rail
        bpy.context.view_layer.objects.active = rail
        bpy.ops.rigidbody.object_add(type='PASSIVE')
        rail.rigid_body.collision_shape = 'BOX'
        rail.rigid_body.friction = 0.3
        
        # Same material as ramp
        rail_mat = create_glass_material(f"mat_{name}_rail", color, emission_strength=0.5)
        rail.data.materials.append(rail_mat)
    
    # Rigid body for ramp
    bpy.context.view_layer.objects.active = ramp
    bpy.ops.rigidbody.object_add(type='PASSIVE')
    ramp.rigid_body.collision_shape = 'BOX'
    ramp.rigid_body.friction = 0.2
    ramp.rigid_body.restitution = 0.3
    
    # Material
    mat = create_glass_material(f"mat_{name}", color, emission_strength=1.0)
    ramp.data.materials.append(mat)
    
    return ramp


def setup_camera():
    """Camera looking at vertical layout from front."""
    bpy.ops.object.camera_add(location=(0, 5, 25))
    camera = bpy.context.active_object
    camera.name = "MainCamera"
    
    # Look straight at the scene
    camera.rotation_euler = (math.radians(10), 0, 0)
    
    bpy.context.scene.camera = camera
    camera.data.lens = 35
    camera.data.clip_end = 100
    
    return camera


def setup_lighting():
    """Set up cyberpunk-style lighting."""
    # Key light (main light, slight purple tint)
    bpy.ops.object.light_add(type='AREA', location=(5, 10, 8))
    key_light = bpy.context.active_object
    key_light.name = "KeyLight"
    key_light.data.energy = 500
    key_light.data.color = (0.9, 0.8, 1.0)
    key_light.data.size = 5
    
    # Fill light (cyan tint from the side)
    bpy.ops.object.light_add(type='AREA', location=(-8, 5, 4))
    fill_light = bpy.context.active_object
    fill_light.name = "FillLight"
    fill_light.data.energy = 200
    fill_light.data.color = (0.5, 0.8, 1.0)
    fill_light.data.size = 3
    
    # Rim light (orange/pink from behind)
    bpy.ops.object.light_add(type='AREA', location=(0, 8, -10))
    rim_light = bpy.context.active_object
    rim_light.name = "RimLight"
    rim_light.data.energy = 300
    rim_light.data.color = (1.0, 0.5, 0.7)
    rim_light.data.size = 4


def setup_world():
    """Set up world/background settings."""
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("CyberpunkWorld")
        bpy.context.scene.world = world
    
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    
    output = nodes.new('ShaderNodeOutputWorld')
    output.location = (300, 0)
    
    background = nodes.new('ShaderNodeBackground')
    background.location = (0, 0)
    background.inputs['Color'].default_value = COLORS['background']
    background.inputs['Strength'].default_value = 1.0
    
    links.new(background.outputs['Background'], output.inputs['Surface'])


def setup_render_settings():
    """Configure render settings for animation."""
    scene = bpy.context.scene
    
    # Choose render engine based on mode
    # Eevee needs display, Cycles works headless
    if bpy.app.background:
        # Headless mode - use Cycles
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'CPU'
        scene.cycles.samples = 64  # Lower for faster rendering
        print("Using Cycles renderer (headless mode)")
    else:
        # Interactive mode - use Eevee for speed
        scene.render.engine = 'BLENDER_EEVEE'
        # Eevee settings for nice glows (compatible with 2.83+)
        try:
            scene.eevee.use_bloom = True
            scene.eevee.bloom_threshold = 0.8
            scene.eevee.bloom_intensity = 0.5
            scene.eevee.bloom_radius = 6.0
        except AttributeError:
            pass
        print("Using Eevee renderer (interactive mode)")
    
    # Resolution
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    
    # Frame rate
    scene.render.fps = FPS
    
    # Output
    scene.render.image_settings.file_format = 'PNG'
    scene.frame_start = 1
    scene.frame_end = 120  # 4 seconds at 30fps


def animate_transaction(sphere, waypoints, start_frame=1, wait_times=None):
    """
    Animate a transaction sphere along waypoints with bouncy physics.
    
    waypoints: list of (x, y, z) tuples
    wait_times: list of frame counts to wait at each waypoint (None = no wait)
    
    Includes:
    - Bounce/overshoot when arriving at each waypoint
    - Squash and stretch effect for physics feel
    """
    frames_per_move = 18  # Frames to move between waypoints
    bounce_frames = 8     # Frames for the bounce settle
    
    if wait_times is None:
        wait_times = [0] * len(waypoints)
    
    current_frame = start_frame
    base_scale = (1.0, 1.0, 1.0)
    
    for i, pos in enumerate(waypoints):
        is_first = (i == 0)
        is_last = (i == len(waypoints) - 1)
        
        if not is_first:
            # --- ARRIVING: Squash effect (compressed on Y) ---
            # Slight overshoot position (bounce past target then back)
            overshoot_y = pos[1] - 0.15  # Dip below target
            sphere.location = (pos[0], overshoot_y, pos[2])
            sphere.scale = (1.15, 0.7, 1.15)  # Squashed
            sphere.keyframe_insert(data_path="location", frame=current_frame)
            sphere.keyframe_insert(data_path="scale", frame=current_frame)
            
            # --- BOUNCE BACK: Stretch then settle ---
            current_frame += int(bounce_frames * 0.4)
            sphere.location = (pos[0], pos[1] + 0.1, pos[2])  # Overshoot up
            sphere.scale = (0.85, 1.25, 0.85)  # Stretched
            sphere.keyframe_insert(data_path="location", frame=current_frame)
            sphere.keyframe_insert(data_path="scale", frame=current_frame)
            
            # --- SETTLE: Back to normal ---
            current_frame += int(bounce_frames * 0.6)
            sphere.location = pos
            sphere.scale = base_scale
            sphere.keyframe_insert(data_path="location", frame=current_frame)
            sphere.keyframe_insert(data_path="scale", frame=current_frame)
        else:
            # First waypoint - just set position
            sphere.location = pos
            sphere.scale = base_scale
            sphere.keyframe_insert(data_path="location", frame=current_frame)
            sphere.keyframe_insert(data_path="scale", frame=current_frame)
        
        # If there's a wait time, hold position
        wait = wait_times[i] if i < len(wait_times) else 0
        if wait > 0:
            current_frame += wait
            sphere.location = pos
            sphere.scale = base_scale
            sphere.keyframe_insert(data_path="location", frame=current_frame)
            sphere.keyframe_insert(data_path="scale", frame=current_frame)
        
        if not is_last:
            # --- LEAVING: Anticipation stretch ---
            current_frame += 3
            # Stretch in direction of movement
            sphere.scale = (0.9, 1.1, 0.9)
            sphere.keyframe_insert(data_path="scale", frame=current_frame)
        
        # Move to next segment
        current_frame += frames_per_move
    
    # Set interpolation to smooth bezier
    try:
        if sphere.animation_data and sphere.animation_data.action:
            fcurves = sphere.animation_data.action.fcurves
            for fcurve in fcurves:
                for keyframe in fcurve.keyframe_points:
                    keyframe.interpolation = 'BEZIER'
                    try:
                        keyframe.easing = 'EASE_IN_OUT'
                    except AttributeError:
                        pass
    except (AttributeError, TypeError):
        print(f"Note: Could not set smooth interpolation for {sphere.name}")


# ============================================================================
# MAIN SCENE CREATION
# ============================================================================



def create_hybrid_transaction(name, color_name, path_points, spawn_frame, physics_frames):
    """
    HYBRID transaction: keyframed travel + rigid body physics inside containers.
    
    - Balls travel between units with smooth keyframe animation
    - Inside units, balls DROP with physics (bounce, roll, collide with others!)
    
    path_points: list of (x, y, z) - center of each container to visit
    physics_frames: how long (frames) to let physics run at each stop
    """
    # Create sphere above first position
    start_pos = (path_points[0][0], path_points[0][1] + 4, path_points[0][2] + 3)
    sphere = create_transaction_sphere(name, color_name, start_pos)
    
    # Initially hidden
    sphere.hide_render = True
    sphere.hide_viewport = True
    sphere.keyframe_insert(data_path="hide_render", frame=spawn_frame - 1)
    sphere.keyframe_insert(data_path="hide_viewport", frame=spawn_frame - 1)
    
    # Visible at spawn
    sphere.hide_render = False
    sphere.hide_viewport = False  
    sphere.keyframe_insert(data_path="hide_render", frame=spawn_frame)
    sphere.keyframe_insert(data_path="hide_viewport", frame=spawn_frame)
    
    current_frame = spawn_frame
    travel_frames = 18
    
    for i, pos in enumerate(path_points):
        is_last = (i == len(path_points) - 1)
        
        # --- KINEMATIC: Travel to above container ---
        sphere.rigid_body.kinematic = True
        sphere.rigid_body.keyframe_insert(data_path="kinematic", frame=current_frame)
        
        # Position above container (entry point)
        above_pos = (pos[0] + random.uniform(-0.3, 0.3), pos[1] + 2.5, pos[2] + random.uniform(-0.2, 0.2))
        sphere.location = above_pos
        sphere.keyframe_insert(data_path="location", frame=current_frame)
        
        current_frame += 2
        
        # --- PHYSICS: Drop into container! ---
        sphere.rigid_body.kinematic = False
        sphere.rigid_body.keyframe_insert(data_path="kinematic", frame=current_frame)
        
        # Let physics simulate (ball falls, bounces, interacts with other balls)
        physics_time = physics_frames[i] if i < len(physics_frames) else 50
        current_frame += physics_time
        
        if not is_last:
            # --- KINEMATIC: Pick up and arc to next container ---
            sphere.rigid_body.kinematic = True
            sphere.rigid_body.keyframe_insert(data_path="kinematic", frame=current_frame)
            
            # Pick up from approximate resting position
            pickup_y = pos[1] - 1.0  # Near bottom of container
            sphere.location = (pos[0], pickup_y, pos[2])
            sphere.keyframe_insert(data_path="location", frame=current_frame)
            
            # Rise up out of container
            current_frame += 8
            sphere.location = (pos[0], pos[1] + 3, pos[2])
            sphere.keyframe_insert(data_path="location", frame=current_frame)
            
            # Arc to next container
            next_pos = path_points[i + 1]
            mid_x = (pos[0] + next_pos[0]) / 2
            mid_z = (pos[2] + next_pos[2]) / 2
            arc_height = 6
            
            current_frame += travel_frames // 2
            sphere.location = (mid_x, arc_height, mid_z)
            sphere.keyframe_insert(data_path="location", frame=current_frame)
            
            current_frame += travel_frames // 2
        else:
            # Last stop - exit upward
            sphere.rigid_body.kinematic = True
            sphere.rigid_body.keyframe_insert(data_path="kinematic", frame=current_frame)
            sphere.location = (pos[0], pos[1], pos[2])
            sphere.keyframe_insert(data_path="location", frame=current_frame)
            
            current_frame += 15
            sphere.location = (pos[0], pos[1] + 6, pos[2] + 5)
            sphere.keyframe_insert(data_path="location", frame=current_frame)
    
    # Smooth interpolation
    try:
        if sphere.animation_data and sphere.animation_data.action:
            for fc in sphere.animation_data.action.fcurves:
                for kf in fc.keyframe_points:
                    kf.interpolation = 'BEZIER'
    except:
        pass
    
    return sphere


def spawn_physics_ball(name, color_name, location, spawn_frame):
    """Spawn a ball with physics at a specific frame."""
    sphere = create_transaction_sphere(name, color_name, location)
    
    # Initially hidden and kinematic (frozen)
    sphere.hide_render = True
    sphere.hide_viewport = True
    sphere.rigid_body.kinematic = True
    
    sphere.keyframe_insert(data_path="hide_render", frame=spawn_frame - 1)
    sphere.keyframe_insert(data_path="hide_viewport", frame=spawn_frame - 1)
    sphere.rigid_body.keyframe_insert(data_path="kinematic", frame=spawn_frame - 1)
    
    # At spawn: visible and physics active
    sphere.hide_render = False
    sphere.hide_viewport = False
    sphere.rigid_body.kinematic = False
    
    sphere.keyframe_insert(data_path="hide_render", frame=spawn_frame)
    sphere.keyframe_insert(data_path="hide_viewport", frame=spawn_frame)
    sphere.rigid_body.keyframe_insert(data_path="kinematic", frame=spawn_frame)
    
    return sphere


def create_channel_scene():
    """Create memory channel visualization with TUBES and continuous physics."""
    print("Creating Memory Channel Visualization (TUBES + PHYSICS)...")
    print("=" * 50)
    
    # Clear existing scene
    print("Clearing scene...")
    clear_scene()
    
    # Set up world/background
    print("Setting up world...")
    setup_world()
    
    # Set up physics world
    print("Setting up physics...")
    setup_physics_world()
    
    # Create visual structures
    print("Creating structures...")
    for name, config in STRUCTURES.items():
        print(f"  - Creating {name}...")
        create_structure_box(
            name=name,
            pos=config['pos'],
            size=config['size'],
            color_name=config['color']
        )
    
    # Create collision containers
    print("Creating collision containers...")
    for name, config in STRUCTURES.items():
        create_container_walls(f"walls_{name}", config['pos'], config['size'])
    
    # Get structure positions
    wcache = STRUCTURES['wcache']['pos']
    read_rs = STRUCTURES['read_rs']['pos']
    write_rs = STRUCTURES['write_rs']['pos']
    dram = STRUCTURES['dram']['pos']
    read_return = STRUCTURES['read_return']['pos']
    
    # =========================================================================
    # CREATE SIMPLE VERTICAL CHUTES (just tilted planes)
    # =========================================================================
    print("Creating chutes...")
    
    # WCache -> Write RS (vertical drop on left side)
    create_ramp("chute_wc_wrs", 
                (wcache[0], wcache[1] - 1, 0),
                (write_rs[0], write_rs[1] + 1, 0),
                width=2.5, color=(1.0, 0.6, 0.2, 1.0))
    
    # Write RS -> DRAM (drop from mid-left to bottom-center)
    create_ramp("chute_wrs_dram",
                (write_rs[0], write_rs[1] - 1, 0),
                (dram[0] - 1.5, dram[1] + 1, 0),
                width=2.5, color=(1.0, 0.6, 0.2, 1.0))
    
    # Read RS -> Read Return (drop on right side)
    create_ramp("chute_rrs_rret",
                (read_rs[0], read_rs[1] - 1, 0),
                (read_return[0], read_return[1] + 1, 0),
                width=2.5, color=(0.2, 0.7, 1.0, 1.0))
    
    # Read Return -> DRAM
    create_ramp("chute_rret_dram",
                (read_return[0], read_return[1] - 1, 0),
                (dram[0] + 1.5, dram[1] + 1, 0),
                width=2.5, color=(0.2, 0.8, 0.8, 1.0))
    
    # Set up camera
    print("Setting up camera...")
    camera = setup_camera()
    
    # Add simple labels
    print("Adding labels...")
    label_color = (1.0, 1.0, 0.9, 1.0)
    label_names = {
        'wcache': 'WCache',
        'read_rs': 'Read RS', 
        'write_rs': 'Write RS',
        'dram': 'DRAM',
        'read_return': 'Read Return'
    }
    for name, config in STRUCTURES.items():
        pos = config['pos']
        label_pos = (pos[0], pos[1] + 2, pos[2] + 2)  # In front of box
        create_text_label(label_names[name], label_pos, label_color, scale=0.5)
    
    # Set up lighting
    print("Setting up lighting...")
    setup_lighting()
    
    # Set up render settings
    print("Configuring render settings...")
    setup_render_settings()
    
    # =========================================================================
    # SPAWN BALLS - drop from top, fall through system
    # =========================================================================
    print("Spawning transaction balls...")
    random.seed(42)
    
    # WRITE balls: drop into WCache at top-left
    for i in range(5):
        x = wcache[0] + random.uniform(-0.5, 0.5)
        y = wcache[1] + 4  # Above WCache
        z = 0
        spawn_frame = 1 + i * 20
        spawn_physics_ball(f"Write_{i}", "transaction_write", (x, y, z), spawn_frame)
    
    # READ balls: drop into Read RS at top-right
    for i in range(5):
        x = read_rs[0] + random.uniform(-0.5, 0.5)
        y = read_rs[1] + 4  # Above Read RS
        z = 0
        spawn_frame = 10 + i * 25
        spawn_physics_ball(f"Read_{i}", "transaction_read", (x, y, z), spawn_frame)
    
    bpy.context.scene.frame_end = 300
    
    print("=" * 50)
    print("SIMPLE VERTICAL LAYOUT")
    print("")
    print("  [WCache]    [Read RS]    <- TOP (balls enter)")
    print("     |            |")
    print("  [Write RS]  [Read Ret]   <- MIDDLE")
    print("      \\          /")
    print("        [DRAM]             <- BOTTOM (balls collect)")
    print("")
    print("Press SPACEBAR to watch balls fall!")


# ============================================================================
# RUN
# ============================================================================

def render_frame(output_path="//channel_frame.png", frame=1):
    """Render a single frame to file."""
    scene = bpy.context.scene
    scene.frame_set(frame)
    scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    print(f"Rendered frame {frame} to {output_path}")


def render_animation(output_path="//channel_anim_", start=1, end=120):
    """Render animation frames."""
    scene = bpy.context.scene
    scene.frame_start = start
    scene.frame_end = end
    scene.render.filepath = output_path
    bpy.ops.render.render(animation=True)
    print(f"Rendered animation frames {start}-{end}")


if __name__ == "__main__":
    import sys
    
    create_channel_scene()
    
    # Check for command line arguments
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    
    # If running in background mode with render flag, render output
    if bpy.app.background:
        if "--render-frame" in sys.argv or "-f" in sys.argv:
            # Render single frame
            render_frame("/home/scratch.ashwink_mobile/channel_viz/channel_frame.png", frame=60)
        elif "--render-anim" in argv:
            # Render animation
            render_animation("/home/scratch.ashwink_mobile/channel_viz/channel_anim_")
        else:
            # Default: render a single frame at frame 60 (mid-animation)
            print("\nTo render in headless mode, run:")
            print("  blender -b -P blender_channel_scene.py -- --render-frame")
            print("  blender -b -P blender_channel_scene.py -- --render-anim")
