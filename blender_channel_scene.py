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
    """Create a text label visible from top-down camera."""
    bpy.ops.object.text_add(location=pos)
    obj = bpy.context.active_object
    obj.data.body = text
    obj.data.size = 0.5
    obj.data.align_x = 'CENTER'
    obj.data.align_y = 'CENTER'
    # Rotate to lie flat on XZ plane, readable from above (camera at +Y)
    obj.rotation_euler = (math.radians(-90), 0, 0)
    
    mat = create_material(f"mat_label_{text}", (1, 1, 0.9, 1), emission=10.0)
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
    
    # Smooth interpolation (with version compatibility)
    try:
        if ball.animation_data and ball.animation_data.action:
            fcurves = getattr(ball.animation_data.action, 'fcurves', None)
            if fcurves:
                for fc in fcurves:
                    for kf in fc.keyframe_points:
                        kf.interpolation = 'BEZIER'
    except:
        pass  # Skip if not supported


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
        # Label ON TOP of box (higher Y so visible from top-down camera)
        label_pos = (cfg['pos'][0], cfg['pos'][1] + 0.6, cfg['pos'][2])
        create_label(cfg['label'], label_pos)
    
    # Create animated transactions
    print("Creating transactions...")
    
    # Unit center positions
    wcache_center = (0, 0.5, 6)
    write_rs_center = (-4, 0.5, 2)
    read_rs_center = (4, 0.5, 2)
    dram_center = (0, 0.5, -3)
    read_return_center = (8, 0.5, -3)
    
    # Offset positions within units (so balls don't overlap)
    # Returns position offset for ball index i within a unit
    def get_slot_offset(slot_index, max_slots=4):
        """Get X offset for a ball slot within a unit."""
        offsets = [-0.9, -0.3, 0.3, 0.9]  # 4 slots side by side
        return offsets[slot_index % max_slots]
    
    # WRITE transactions (6 balls)
    # Path: Enter -> WCache -> Write RS -> DRAM
    num_writes = 6
    for i in range(num_writes):
        # Each ball gets its own slot offset
        x_off = get_slot_offset(i % 4)
        
        waypoints = [
            (0 + x_off, 0.5, 12),                          # Enter
            (wcache_center[0] + x_off, 0.5, wcache_center[2]),     # WCache
            (write_rs_center[0] + x_off, 0.5, write_rs_center[2]), # Write RS
            (dram_center[0] - 1.5 + x_off, 0.5, dram_center[2]),   # DRAM (left side)
        ]
        
        ball = create_ball(f"write_{i}", "write_ball", waypoints[0])
        # Stagger starts, longer wait times so balls accumulate
        start = 1 + i * 25
        animate_ball(ball, waypoints, start_frame=start, frames_per_stop=40)
    
    # READ transactions (6 balls)
    # Path: Enter -> Read RS -> DRAM -> Read Return -> Exit
    num_reads = 6
    for i in range(num_reads):
        x_off = get_slot_offset(i % 4)
        
        waypoints = [
            (4 + x_off, 0.5, 12),                          # Enter
            (read_rs_center[0] + x_off, 0.5, read_rs_center[2]),   # Read RS
            (dram_center[0] + 1.5 + x_off, 0.5, dram_center[2]),   # DRAM (right side)
            (read_return_center[0] + x_off, 0.5, read_return_center[2]), # Read Return
            (read_return_center[0] + x_off, 0.5, 12),      # Exit
        ]
        
        ball = create_ball(f"read_{i}", "read_ball", waypoints[0])
        start = 10 + i * 30
        animate_ball(ball, waypoints, start_frame=start, frames_per_stop=45)
    
    # Render settings
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    bpy.context.scene.frame_end = 450
    
    print("=" * 50)
    print("Done! 12 transactions created (6 writes, 6 reads)")
    print("")
    print("Balls are offset within each unit so you can count them!")
    print("Watch units fill up as balls arrive and wait.")
    print("")
    print("Press SPACEBAR to play.")


# Run
if __name__ == "__main__":
    create_scene()
