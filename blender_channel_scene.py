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

# Structure positions and sizes (x, y, z)
# Y is vertical (height), X-Z is the ground plane
# Taller boxes (Y=2-3) to look like 3D containers that hold balls
STRUCTURES = {
    'wcache': {
        'pos': (0, 1.5, 4),
        'size': (5, 3, 2),
        'color': 'wcache',
        'label': 'WCache',
    },
    'write_rs': {
        'pos': (-3.5, 1.5, 0),
        'size': (4, 3, 2.5),
        'color': 'write_rs',
        'label': 'Write RS',
    },
    'read_rs': {
        'pos': (3.5, 1.5, 0),
        'size': (4, 3, 2.5),
        'color': 'read_rs',
        'label': 'Read RS',
    },
    'dram': {
        'pos': (0, 1.5, -5),
        'size': (8, 3, 3),
        'color': 'dram',
        'label': 'DRAM',
    },
    'read_return': {
        'pos': (7, 1.5, -5),
        'size': (2.5, 3, 3),
        'color': 'read_return',
        'label': 'Read Return',
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


def create_collision_container(name, pos, size):
    """Create invisible open-top collision container for rigid body physics."""
    thickness = 0.1
    sx, sy, sz = size
    
    collision_objs = []
    
    # Floor of container
    bpy.ops.mesh.primitive_cube_add(size=1, location=(pos[0], pos[1] - sy/2 + thickness/2, pos[2]))
    floor = bpy.context.active_object
    floor.name = f"{name}_floor"
    floor.scale = (sx, thickness, sz)
    bpy.ops.object.transform_apply(scale=True)
    collision_objs.append(floor)
    
    # Four walls (no top - open container)
    # Front wall (positive Z)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(pos[0], pos[1], pos[2] + sz/2 - thickness/2))
    wall = bpy.context.active_object
    wall.name = f"{name}_wall_front"
    wall.scale = (sx, sy, thickness)
    bpy.ops.object.transform_apply(scale=True)
    collision_objs.append(wall)
    
    # Back wall (negative Z)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(pos[0], pos[1], pos[2] - sz/2 + thickness/2))
    wall = bpy.context.active_object
    wall.name = f"{name}_wall_back"
    wall.scale = (sx, sy, thickness)
    bpy.ops.object.transform_apply(scale=True)
    collision_objs.append(wall)
    
    # Left wall (negative X)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(pos[0] - sx/2 + thickness/2, pos[1], pos[2]))
    wall = bpy.context.active_object
    wall.name = f"{name}_wall_left"
    wall.scale = (thickness, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    collision_objs.append(wall)
    
    # Right wall (positive X)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(pos[0] + sx/2 - thickness/2, pos[1], pos[2]))
    wall = bpy.context.active_object
    wall.name = f"{name}_wall_right"
    wall.scale = (thickness, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    collision_objs.append(wall)
    
    # Make all collision objects passive rigid bodies and invisible
    for obj in collision_objs:
        # Set up rigid body
        bpy.context.view_layer.objects.active = obj
        bpy.ops.rigidbody.object_add(type='PASSIVE')
        obj.rigid_body.collision_shape = 'BOX'
        obj.rigid_body.friction = 0.5
        obj.rigid_body.restitution = 0.6  # Bounciness
        
        # Make invisible but keep collision
        obj.hide_render = True
        obj.display_type = 'WIRE'
    
    return collision_objs


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


def create_transaction_sphere(name, color_name, location=(0, 1.5, 5), use_physics=True):
    """Create a glowing 3D transaction sphere with rigid body physics."""
    # Higher subdivision for smoother sphere
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.35, segments=24, ring_count=16, location=location)
    sphere = bpy.context.active_object
    sphere.name = name
    
    # Smooth shading
    bpy.ops.object.shade_smooth()
    
    # Create 3D material with specular and glow
    color = COLORS.get(color_name, COLORS['transaction_read'])
    mat = create_sphere_material_3d(f"mat_{name}", color, emission_strength=6.0)
    sphere.data.materials.append(mat)
    
    # Add rigid body physics
    if use_physics:
        bpy.context.view_layer.objects.active = sphere
        bpy.ops.rigidbody.object_add(type='ACTIVE')
        sphere.rigid_body.mass = 1.0
        sphere.rigid_body.collision_shape = 'SPHERE'
        sphere.rigid_body.friction = 0.4
        sphere.rigid_body.restitution = 0.7  # Bouncy!
        sphere.rigid_body.linear_damping = 0.1
        sphere.rigid_body.angular_damping = 0.2
    
    return sphere


def create_text_label(text, location, color, scale=0.4):
    """Create a 3D text label."""
    # Create text object
    bpy.ops.object.text_add(location=location)
    text_obj = bpy.context.active_object
    text_obj.name = f"Label_{text}"
    text_obj.data.body = text
    
    # Set text properties
    text_obj.data.size = scale
    text_obj.data.align_x = 'CENTER'
    text_obj.data.align_y = 'CENTER'
    
    # Rotate to face camera (flat on XZ plane, facing up)
    text_obj.rotation_euler = (math.radians(90), 0, 0)
    
    # Create emission material for the text (bright glow for visibility)
    mat = create_emission_material(f"mat_label_{text}", (*color[:3], 1.0), emission_strength=8.0)
    text_obj.data.materials.append(mat)
    
    return text_obj


def setup_camera():
    """Set up camera for 3D isometric view - shows depth of boxes."""
    # Create camera - positioned to see the 3D depth
    # Further back and higher to see the whole scene with depth
    bpy.ops.object.camera_add(location=(18, 18, 12))
    camera = bpy.context.active_object
    camera.name = "MainCamera"
    
    # Isometric-ish angle: ~55 degrees down, rotated 45 degrees around Z
    # This shows the 3D nature of the boxes nicely
    camera.rotation_euler = (math.radians(55), 0, math.radians(135))
    
    # Set as active camera
    bpy.context.scene.camera = camera
    
    # Camera settings - wider lens for more dramatic perspective
    camera.data.lens = 35
    camera.data.clip_end = 200
    
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

def setup_rigid_body_world():
    """Set up the rigid body physics world."""
    scene = bpy.context.scene
    
    # Create rigid body world if it doesn't exist
    if scene.rigidbody_world is None:
        bpy.ops.rigidbody.world_add()
    
    # Configure physics settings
    rbw = scene.rigidbody_world
    rbw.enabled = True
    rbw.point_cache.frame_start = 1
    rbw.point_cache.frame_end = 500
    rbw.substeps_per_frame = 10  # More accurate simulation
    rbw.solver_iterations = 20


def spawn_ball_at_frame(name, color_name, location, spawn_frame):
    """Create a ball that appears at a specific frame using animated visibility and kinematic switching."""
    sphere = create_transaction_sphere(name, color_name, location, use_physics=True)
    
    # Start as kinematic (frozen) and invisible
    sphere.rigid_body.kinematic = True
    sphere.hide_render = True
    sphere.hide_viewport = True
    
    # Keyframe: hidden and kinematic before spawn
    sphere.keyframe_insert(data_path="hide_render", frame=spawn_frame - 1)
    sphere.keyframe_insert(data_path="hide_viewport", frame=spawn_frame - 1)
    sphere.rigid_body.keyframe_insert(data_path="kinematic", frame=spawn_frame - 1)
    
    # Keyframe: visible and active physics at spawn
    sphere.hide_render = False
    sphere.hide_viewport = False
    sphere.rigid_body.kinematic = False
    sphere.keyframe_insert(data_path="hide_render", frame=spawn_frame)
    sphere.keyframe_insert(data_path="hide_viewport", frame=spawn_frame)
    sphere.rigid_body.keyframe_insert(data_path="kinematic", frame=spawn_frame)
    
    return sphere


def create_channel_scene():
    """Create the complete memory channel visualization scene with PHYSICS."""
    print("Creating Memory Channel Visualization Scene (PHYSICS MODE)...")
    print("=" * 50)
    
    # Clear existing scene
    print("Clearing scene...")
    clear_scene()
    
    # Set up world/background
    print("Setting up world...")
    setup_world()
    
    # Set up rigid body physics world
    print("Setting up physics world...")
    setup_rigid_body_world()
    
    # Create visual structures (the nice looking boxes)
    print("Creating structures...")
    for name, config in STRUCTURES.items():
        print(f"  - Creating {name}...")
        create_structure_box(
            name=name,
            pos=config['pos'],
            size=config['size'],
            color_name=config['color']
        )
    
    # Create collision containers for physics (invisible walls)
    print("Creating physics collision containers...")
    for name, config in STRUCTURES.items():
        print(f"  - Creating collision for {name}...")
        create_collision_container(
            name=f"collision_{name}",
            pos=config['pos'],
            size=config['size']
        )
    
    # Add labels for each structure
    print("Adding labels...")
    label_height = 3.5
    label_color = (1.0, 1.0, 0.9, 1.0)
    labels = [
        ("WCache", (0, label_height, 4)),
        ("Write RS", (-3.5, label_height, 0)),
        ("Read RS", (3.5, label_height, 0)),
        ("DRAM", (0, label_height, -5)),
        ("Read Return", (7, label_height, -5)),
    ]
    for text, pos in labels:
        create_text_label(text, pos, label_color, scale=0.8)
    
    # Set up camera
    print("Setting up camera...")
    setup_camera()
    
    # Set up lighting
    print("Setting up lighting...")
    setup_lighting()
    
    # Set up render settings
    print("Configuring render settings...")
    setup_render_settings()
    
    # =========================================================================
    # SPAWN BALLS WITH PHYSICS - they drop into containers and bounce!
    # =========================================================================
    print("Spawning transaction balls with physics...")
    random.seed(42)
    
    # Drop balls into Read RS (cyan)
    for i in range(8):
        x = 3.5 + random.uniform(-1.2, 1.2)
        z = 0 + random.uniform(-0.8, 0.8)
        y = 6 + random.uniform(0, 3)  # Drop from above
        spawn_frame = 1 + i * 12  # Stagger spawns
        spawn_ball_at_frame(f"ReadTx_{i:03d}", "transaction_read", (x, y, z), spawn_frame)
    
    # Drop balls into Write RS (orange) 
    for i in range(6):
        x = -3.5 + random.uniform(-1.2, 1.2)
        z = 0 + random.uniform(-0.8, 0.8)
        y = 6 + random.uniform(0, 3)
        spawn_frame = 10 + i * 15
        spawn_ball_at_frame(f"WriteTx_{i:03d}", "transaction_write", (x, y, z), spawn_frame)
    
    # Drop balls into WCache (green)
    for i in range(5):
        x = 0 + random.uniform(-1.5, 1.5)
        z = 4 + random.uniform(-0.6, 0.6)
        y = 6 + random.uniform(0, 2)
        spawn_frame = 5 + i * 18
        spawn_ball_at_frame(f"WCacheTx_{i:03d}", "wcache", (x, y, z), spawn_frame)
    
    # Drop balls into DRAM (purple)
    for i in range(10):
        x = 0 + random.uniform(-2.5, 2.5)
        z = -5 + random.uniform(-1, 1)
        y = 6 + random.uniform(0, 4)
        spawn_frame = 1 + i * 10
        spawn_ball_at_frame(f"DRAMTx_{i:03d}", "dram", (x, y, z), spawn_frame)
    
    # Drop balls into Read Return (cyan)
    for i in range(4):
        x = 7 + random.uniform(-0.8, 0.8)
        z = -5 + random.uniform(-1, 1)
        y = 6 + random.uniform(0, 2)
        spawn_frame = 30 + i * 20
        spawn_ball_at_frame(f"ReturnTx_{i:03d}", "read_return", (x, y, z), spawn_frame)
    
    # Animation length
    bpy.context.scene.frame_end = 500
    
    print("=" * 50)
    print("Scene created successfully with PHYSICS!")
    print("")
    print("NEXT STEPS:")
    print("1. Press SPACEBAR to play and watch balls bounce!")
    print("2. The physics will simulate automatically")
    print("3. Press F12 to render a frame")
    print("")
    print("TIP: Switch to 'Rendered' viewport (Z key) for full glow effects!")


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
