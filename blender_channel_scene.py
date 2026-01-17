"""
Memory Channel Visualizer - Simple 2D Schematic
================================================

Clean 2D top-down view with animated transactions.
NO physics - just simple keyframe animation.

Layout matches original schematic:
    
           [WCache]
              |
    [Write RS]    [Read RS]
         \          /
           [DRAM] --> [Read Return]
"""

import bpy
import math

# ============================================================================
# COLORS
# ============================================================================
COLORS = {
    'wcache': (0.2, 0.9, 0.3, 1.0),          # Green
    'write_rs': (1.0, 0.5, 0.0, 1.0),        # Orange
    'read_rs': (0.0, 0.6, 1.0, 1.0),         # Blue
    'dram': (0.8, 0.2, 0.9, 1.0),            # Purple
    'read_return': (0.0, 0.9, 0.9, 1.0),     # Cyan
    'read_ball': (0.0, 0.8, 1.0, 1.0),       # Cyan ball
    'write_ball': (1.0, 0.5, 0.0, 1.0),      # Orange ball
}

# ============================================================================
# 2D SCHEMATIC LAYOUT (Top-down view, all at Y=0.5)
# Z is vertical in view, X is horizontal
# ============================================================================
#
#                 [WCache]           Z = 6
#                    |
#     [Write RS]          [Read RS]  Z = 2  
#          \                /
#              [DRAM]                Z = -3
#                    \
#                [Read Return]       Z = -3, X = 8
#
STRUCTURES = {
    'wcache': {
        'pos': (0, 0.5, 6),
        'size': (4, 1, 2),
        'color': 'wcache',
        'label': 'WCache',
    },
    'write_rs': {
        'pos': (-4, 0.5, 2),
        'size': (3, 1, 2),
        'color': 'write_rs',
        'label': 'Write RS',
    },
    'read_rs': {
        'pos': (4, 0.5, 2),
        'size': (3, 1, 2),
        'color': 'read_rs',
        'label': 'Read RS',
    },
    'dram': {
        'pos': (0, 0.5, -3),
        'size': (6, 1, 2.5),
        'color': 'dram',
        'label': 'DRAM',
    },
    'read_return': {
        'pos': (8, 0.5, -3),
        'size': (3, 1, 2),
        'color': 'read_return',
        'label': 'Read Return',
    },
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def clear_scene():
    """Remove everything from scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for m in bpy.data.materials:
        bpy.data.materials.remove(m)
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)


def create_material(name, color, emission=2.0):
    """Create a glowing material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    output = nodes.new('ShaderNodeOutputMaterial')
    emission_node = nodes.new('ShaderNodeEmission')
    emission_node.inputs['Color'].default_value = color
    emission_node.inputs['Strength'].default_value = emission
    links.new(emission_node.outputs['Emission'], output.inputs['Surface'])
    
    return mat


def create_box(name, pos, size, color_name):
    """Create a simple box."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(scale=True)
    
    color = COLORS[color_name]
    mat = create_material(f"mat_{name}", color, emission=3.0)
    obj.data.materials.append(mat)
    
    return obj


def create_label(text, pos):
    """Create a text label."""
    bpy.ops.object.text_add(location=pos)
    obj = bpy.context.active_object
    obj.data.body = text
    obj.data.size = 0.6
    obj.data.align_x = 'CENTER'
    obj.rotation_euler = (math.radians(90), 0, 0)  # Face up
    
    mat = create_material(f"mat_label_{text}", (1, 1, 0.9, 1), emission=8.0)
    obj.data.materials.append(mat)
    
    return obj


def create_ball(name, color_name, pos):
    """Create a transaction ball."""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.4, location=pos)
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.shade_smooth()
    
    color = COLORS[color_name]
    mat = create_material(f"mat_{name}", color, emission=8.0)
    obj.data.materials.append(mat)
    
    return obj


def animate_ball(ball, waypoints, start_frame, frames_per_stop=30):
    """Animate a ball along waypoints with simple keyframes."""
    frame = start_frame
    
    for pos in waypoints:
        ball.location = pos
        ball.keyframe_insert(data_path="location", frame=frame)
        frame += frames_per_stop
    
    # Smooth interpolation
    if ball.animation_data and ball.animation_data.action:
        for fc in ball.animation_data.action.fcurves:
            for kf in fc.keyframe_points:
                kf.interpolation = 'BEZIER'


def setup_camera():
    """Top-down camera."""
    bpy.ops.object.camera_add(location=(0, 20, 0))
    cam = bpy.context.active_object
    cam.rotation_euler = (math.radians(90), 0, 0)
    cam.data.lens = 25
    bpy.context.scene.camera = cam


def setup_lighting():
    """Simple lighting."""
    bpy.ops.object.light_add(type='SUN', location=(0, 10, 5))
    light = bpy.context.active_object
    light.data.energy = 3


def setup_world():
    """Dark background."""
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    if bg:
        bg.inputs['Color'].default_value = (0.02, 0.02, 0.05, 1)


# ============================================================================
# MAIN
# ============================================================================

def create_scene():
    print("Creating 2D Schematic...")
    
    clear_scene()
    setup_world()
    setup_camera()
    setup_lighting()
    
    # Create all structure boxes
    print("Creating structures...")
    for name, cfg in STRUCTURES.items():
        create_box(name, cfg['pos'], cfg['size'], cfg['color'])
        # Label above box
        label_pos = (cfg['pos'][0], cfg['pos'][1] + 1, cfg['pos'][2])
        create_label(cfg['label'], label_pos)
    
    # Create animated transactions
    print("Creating transactions...")
    
    # WRITE PATH: Enter -> WCache -> Write RS -> DRAM
    write_waypoints = [
        (0, 0.5, 10),       # Enter from top
        (0, 0.5, 6),        # WCache
        (-4, 0.5, 2),       # Write RS
        (0, 0.5, -3),       # DRAM
    ]
    for i in range(3):
        ball = create_ball(f"write_{i}", "write_ball", write_waypoints[0])
        animate_ball(ball, write_waypoints, start_frame=1 + i*40, frames_per_stop=25)
    
    # READ PATH: Enter -> Read RS -> DRAM -> Read Return -> Exit
    read_waypoints = [
        (4, 0.5, 10),       # Enter from top-right
        (4, 0.5, 2),        # Read RS
        (0, 0.5, -3),       # DRAM
        (8, 0.5, -3),       # Read Return
        (8, 0.5, 10),       # Exit upward
    ]
    for i in range(3):
        ball = create_ball(f"read_{i}", "read_ball", read_waypoints[0])
        animate_ball(ball, read_waypoints, start_frame=20 + i*50, frames_per_stop=25)
    
    # Render settings
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    bpy.context.scene.frame_end = 300
    
    print("=" * 50)
    print("Done! Press SPACEBAR to play animation.")
    print("")
    print("Layout:")
    print("         [WCache]")
    print("            |")
    print("[Write RS]      [Read RS]")
    print("      \\          /")
    print("        [DRAM] --> [Read Return]")


# Run
if __name__ == "__main__":
    create_scene()
