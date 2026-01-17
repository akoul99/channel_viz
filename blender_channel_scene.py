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

# Structure positions and sizes (x, y, z) - top-down layout
# Y is "up" in our view, structures laid out on X-Z plane
STRUCTURES = {
    'wcache': {
        'pos': (0, 0.5, 3),
        'size': (4, 1, 1.5),
        'color': 'wcache',
        'label': 'WCache',
    },
    'write_rs': {
        'pos': (-2.5, 0.5, 0),
        'size': (3, 1, 2),
        'color': 'write_rs',
        'label': 'Write RS',
    },
    'read_rs': {
        'pos': (2.5, 0.5, 0),
        'size': (3, 1, 2),
        'color': 'read_rs',
        'label': 'Read RS',
    },
    'dram': {
        'pos': (0, 0.5, -4),
        'size': (6, 1, 2.5),
        'color': 'dram',
        'label': 'DRAM',
    },
    'read_return': {
        'pos': (6, 0.5, -4),
        'size': (2, 1, 2.5),
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
    """Remove all objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # Clear materials
    for material in bpy.data.materials:
        bpy.data.materials.remove(material)
    
    # Clear meshes
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)


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
    """Create a structure box with cyberpunk styling."""
    # Create cube
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
    
    # Apply modifier
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


def create_transaction_sphere(name, color_name, location=(0, 1.5, 5)):
    """Create a glowing transaction sphere."""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, location=location)
    sphere = bpy.context.active_object
    sphere.name = name
    
    # Smooth shading
    bpy.ops.object.shade_smooth()
    
    # Create emission material
    color = COLORS.get(color_name, COLORS['transaction_read'])
    mat = create_emission_material(f"mat_{name}", color, emission_strength=10.0)
    sphere.data.materials.append(mat)
    
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
    
    # Create emission material for the text
    mat = create_emission_material(f"mat_label_{text}", (*color[:3], 1.0), emission_strength=3.0)
    text_obj.data.materials.append(mat)
    
    return text_obj


def setup_camera():
    """Set up camera for top-down isometric view."""
    # Create camera
    bpy.ops.object.camera_add(location=(0, 20, 5))
    camera = bpy.context.active_object
    camera.name = "MainCamera"
    
    # Point camera down at scene center
    camera.rotation_euler = (math.radians(70), 0, 0)
    
    # Set as active camera
    bpy.context.scene.camera = camera
    
    # Camera settings
    camera.data.lens = 50
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


def animate_transaction(sphere, waypoints, start_frame=1):
    """
    Animate a transaction sphere along waypoints.
    
    waypoints: list of (x, y, z) tuples
    """
    frames_per_segment = 20
    
    for i, pos in enumerate(waypoints):
        frame = start_frame + i * frames_per_segment
        
        sphere.location = pos
        sphere.keyframe_insert(data_path="location", frame=frame)
    
    # Set interpolation to smooth (compatible with multiple Blender versions)
    try:
        if sphere.animation_data and sphere.animation_data.action:
            fcurves = sphere.animation_data.action.fcurves
            for fcurve in fcurves:
                for keyframe in fcurve.keyframe_points:
                    keyframe.interpolation = 'BEZIER'
                    # easing attribute may not exist in all versions
                    try:
                        keyframe.easing = 'EASE_IN_OUT'
                    except AttributeError:
                        pass
    except (AttributeError, TypeError):
        # Skip smooth interpolation if API is incompatible
        print(f"Note: Could not set smooth interpolation for {sphere.name}")


# ============================================================================
# MAIN SCENE CREATION
# ============================================================================

def create_channel_scene():
    """Create the complete memory channel visualization scene."""
    print("Creating Memory Channel Visualization Scene...")
    print("=" * 50)
    
    # Clear existing scene
    print("Clearing scene...")
    clear_scene()
    
    # Set up world/background
    print("Setting up world...")
    setup_world()
    
    # Create floor and grid
    print("Creating floor and grid...")
    create_floor()
    create_grid_lines()
    
    # Create structures
    print("Creating structures...")
    for name, config in STRUCTURES.items():
        print(f"  - Creating {name}...")
        create_structure_box(
            name=name,
            pos=config['pos'],
            size=config['size'],
            color_name=config['color']
        )
    
    # Add labels for each structure
    print("Adding labels...")
    label_height = 1.3  # Height above structures
    labels = [
        ("WCache", (0, label_height, 3), COLORS['wcache']),
        ("Write RS", (-2.5, label_height, 0), COLORS['write_rs']),
        ("Read RS", (2.5, label_height, 0), COLORS['read_rs']),
        ("DRAM", (0, label_height, -4), COLORS['dram']),
        ("Read Return", (6, label_height, -4), COLORS['read_return']),
    ]
    for text, pos, color in labels:
        create_text_label(text, pos, color, scale=0.5)
    
    # Set up camera
    print("Setting up camera...")
    setup_camera()
    
    # Set up lighting
    print("Setting up lighting...")
    setup_lighting()
    
    # Set up render settings
    print("Configuring render settings...")
    setup_render_settings()
    
    # Create sample transactions
    print("Creating sample transactions...")
    
    # Read transaction path
    # Read enters, goes to Read RS, then DRAM, then Read Return, then exits UPWARD (back out of channel)
    read_waypoints = [
        (3, 1.5, 6),      # Start (entering from top)
        (2.5, 1.5, 0),    # Read RS
        (2, 1.5, -4),     # DRAM
        (6, 1.5, -4),     # Read Return
        (6, 1.5, 6),      # Exit (upward, back out the channel boundary)
        (6, 1.5, 10),     # Continue up and out
    ]
    read_tx = create_transaction_sphere("ReadTx_001", "transaction_read", read_waypoints[0])
    animate_transaction(read_tx, read_waypoints, start_frame=1)
    
    # Write transaction path
    write_waypoints = [
        (-1, 1.5, 6),     # Start (entering)
        (0, 1.5, 3),      # WCache
        (-2.5, 1.5, 0),   # Write RS
        (-1, 1.5, -4),    # DRAM
    ]
    write_tx = create_transaction_sphere("WriteTx_001", "transaction_write", write_waypoints[0])
    animate_transaction(write_tx, write_waypoints, start_frame=30)
    
    print("=" * 50)
    print("Scene created successfully!")
    print("")
    print("NEXT STEPS:")
    print("1. Press F12 to render a single frame")
    print("2. Press Ctrl+F12 to render the animation")
    print("3. Use View > Viewport Render Animation for quick preview")
    print("")
    print("TIP: Switch to 'Rendered' viewport shading (Z key) to see the glows!")


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
