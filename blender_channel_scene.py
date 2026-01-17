"""
Memory Channel Visualizer - Hybrid Physics
===========================================

Clean 2D top-down view with HYBRID animation:
- Keyframes for travel BETWEEN units
- Rigid body physics INSIDE units (balls bounce/roll)

To revert to pure keyframes, use: blender_channel_scene_backup_nophysics.py

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
# PHYSICS CONFIGURATION
# Toggle this to easily disable physics and revert to pure keyframes
# ============================================================================
USE_PHYSICS = True
FRAMES_IN_UNIT = 80   # Longer time in units for physics to settle
FRAMES_TRAVEL = 15    # Fast travel between units

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def setup_physics_world():
    """Initialize rigid body world for physics simulation."""
    scene = bpy.context.scene
    if scene.rigidbody_world is None:
        bpy.ops.rigidbody.world_add()
    scene.rigidbody_world.point_cache.frame_end = 600


def clear_scene():
    """Remove everything from scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for m in bpy.data.materials:
        bpy.data.materials.remove(m)
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)


def create_material(name, color, emission=2.0, transparent=False):
    """Create a glowing material, optionally transparent."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    
    if transparent:
        try:
            mat.blend_method = 'BLEND'
        except:
            pass
    
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    output = nodes.new('ShaderNodeOutputMaterial')
    
    if transparent:
        # Mix emission with transparent for see-through effect
        mix = nodes.new('ShaderNodeMixShader')
        mix.inputs[0].default_value = 0.8  # 80% transparent, 20% colored
        
        emission_node = nodes.new('ShaderNodeEmission')
        emission_node.inputs['Color'].default_value = color
        emission_node.inputs['Strength'].default_value = emission
        
        transparent_node = nodes.new('ShaderNodeBsdfTransparent')
        
        links.new(transparent_node.outputs['BSDF'], mix.inputs[1])
        links.new(emission_node.outputs['Emission'], mix.inputs[2])
        links.new(mix.outputs['Shader'], output.inputs['Surface'])
    else:
        emission_node = nodes.new('ShaderNodeEmission')
        emission_node.inputs['Color'].default_value = color
        emission_node.inputs['Strength'].default_value = emission
        links.new(emission_node.outputs['Emission'], output.inputs['Surface'])
    
    return mat


def create_box(name, pos, size, color_name):
    """Create a glowing wireframe container with semi-transparent fill."""
    color = COLORS[color_name]
    sx, sy, sz = size
    px, py, pz = pos
    hx, hy, hz = sx/2, sy/2, sz/2
    
    # 1. Create semi-transparent fill box
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    fill_box = bpy.context.active_object
    fill_box.name = f"{name}_fill"
    fill_box.scale = (sx * 0.98, sy * 0.98, sz * 0.98)  # Slightly smaller
    bpy.ops.object.transform_apply(scale=True)
    
    # Semi-transparent material (80% transparent)
    fill_mat = create_material(f"mat_{name}_fill", color, emission=1.0, transparent=True)
    fill_box.data.materials.append(fill_mat)
    
    # Create invisible collision walls (floor + 4 sides) inside the box
    # The fill_box is visual only - we need actual planes for physics
    if USE_PHYSICS:
        try:
            # Floor plane (bottom of box)
            floor_z = pz - hz + 0.1  # Slightly above bottom edge
            bpy.ops.mesh.primitive_plane_add(size=1, location=(px, py, floor_z))
            floor = bpy.context.active_object
            floor.name = f"{name}_floor"
            floor.scale = (sx * 0.9, sy * 0.9, 1)
            bpy.ops.object.transform_apply(scale=True)
            # Make invisible
            floor.hide_render = True
            floor.display_type = 'WIRE'
            bpy.ops.rigidbody.object_add(type='PASSIVE')
            floor.rigid_body.collision_shape = 'BOX'
            floor.rigid_body.friction = 0.8
            floor.rigid_body.restitution = 0.3
            
            # Left wall
            bpy.ops.mesh.primitive_plane_add(size=1, location=(px - hx + 0.1, py, pz))
            wall = bpy.context.active_object
            wall.name = f"{name}_wall_left"
            wall.rotation_euler = (0, math.radians(90), 0)
            wall.scale = (sz * 0.9, sy * 0.9, 1)
            bpy.ops.object.transform_apply(rotation=True, scale=True)
            wall.hide_render = True
            wall.display_type = 'WIRE'
            bpy.ops.rigidbody.object_add(type='PASSIVE')
            wall.rigid_body.collision_shape = 'BOX'
            wall.rigid_body.friction = 0.5
            wall.rigid_body.restitution = 0.4
            
            # Right wall
            bpy.ops.mesh.primitive_plane_add(size=1, location=(px + hx - 0.1, py, pz))
            wall = bpy.context.active_object
            wall.name = f"{name}_wall_right"
            wall.rotation_euler = (0, math.radians(90), 0)
            wall.scale = (sz * 0.9, sy * 0.9, 1)
            bpy.ops.object.transform_apply(rotation=True, scale=True)
            wall.hide_render = True
            wall.display_type = 'WIRE'
            bpy.ops.rigidbody.object_add(type='PASSIVE')
            wall.rigid_body.collision_shape = 'BOX'
            wall.rigid_body.friction = 0.5
            wall.rigid_body.restitution = 0.4
            
            # Front wall (towards camera)
            bpy.ops.mesh.primitive_plane_add(size=1, location=(px, py - hy + 0.1, pz))
            wall = bpy.context.active_object
            wall.name = f"{name}_wall_front"
            wall.rotation_euler = (math.radians(90), 0, 0)
            wall.scale = (sx * 0.9, sz * 0.9, 1)
            bpy.ops.object.transform_apply(rotation=True, scale=True)
            wall.hide_render = True
            wall.display_type = 'WIRE'
            bpy.ops.rigidbody.object_add(type='PASSIVE')
            wall.rigid_body.collision_shape = 'BOX'
            wall.rigid_body.friction = 0.5
            wall.rigid_body.restitution = 0.4
            
            # Back wall
            bpy.ops.mesh.primitive_plane_add(size=1, location=(px, py + hy - 0.1, pz))
            wall = bpy.context.active_object
            wall.name = f"{name}_wall_back"
            wall.rotation_euler = (math.radians(90), 0, 0)
            wall.scale = (sx * 0.9, sz * 0.9, 1)
            bpy.ops.object.transform_apply(rotation=True, scale=True)
            wall.hide_render = True
            wall.display_type = 'WIRE'
            bpy.ops.rigidbody.object_add(type='PASSIVE')
            wall.rigid_body.collision_shape = 'BOX'
            wall.rigid_body.friction = 0.5
            wall.rigid_body.restitution = 0.4
            
        except Exception as e:
            print(f"Physics setup failed for {name}: {e}")
    
    # 2. Create glowing wireframe edges
    corners = [
        (px-hx, py-hy, pz-hz), (px+hx, py-hy, pz-hz),
        (px+hx, py-hy, pz+hz), (px-hx, py-hy, pz+hz),
        (px-hx, py+hy, pz-hz), (px+hx, py+hy, pz-hz),
        (px+hx, py+hy, pz+hz), (px-hx, py+hy, pz+hz),
    ]
    
    edges = [
        (0,1), (1,2), (2,3), (3,0),  # Bottom
        (4,5), (5,6), (6,7), (7,4),  # Top
        (0,4), (1,5), (2,6), (3,7),  # Verticals
    ]
    
    edge_mat = create_material(f"mat_{name}_edge", color, emission=6.0)
    
    for i, (a, b) in enumerate(edges):
        p1, p2 = corners[a], corners[b]
        mid = ((p1[0]+p2[0])/2, (p1[1]+p2[1])/2, (p1[2]+p2[2])/2)
        dx, dy, dz = p2[0]-p1[0], p2[1]-p1[1], p2[2]-p1[2]
        length = (dx**2 + dy**2 + dz**2) ** 0.5
        
        bpy.ops.mesh.primitive_cylinder_add(radius=0.06, depth=length, location=mid)
        edge_obj = bpy.context.active_object
        edge_obj.name = f"{name}_edge_{i}"
        
        from mathutils import Vector
        direction = Vector((dx, dy, dz)).normalized()
        up = Vector((0, 0, 1))
        if abs(direction.dot(up)) < 0.999:
            rot_axis = up.cross(direction).normalized()
            rot_angle = math.acos(direction.dot(up))
            edge_obj.rotation_mode = 'AXIS_ANGLE'
            edge_obj.rotation_axis_angle = (rot_angle, rot_axis.x, rot_axis.y, rot_axis.z)
        elif direction.z < 0:
            edge_obj.rotation_euler = (math.radians(180), 0, 0)
        
        edge_obj.data.materials.append(edge_mat)
    
    # 3. Corner spheres
    for i, corner in enumerate(corners):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=corner)
        sphere = bpy.context.active_object
        sphere.name = f"{name}_corner_{i}"
        sphere.data.materials.append(edge_mat)
    
    return fill_box


def create_label(text, pos):
    """Create a text label visible from top-down camera."""
    bpy.ops.object.text_add(location=pos)
    obj = bpy.context.active_object
    obj.data.body = text
    obj.data.size = 0.5
    obj.data.align_x = 'CENTER'
    obj.data.align_y = 'CENTER'
    # Lie flat, rotated to read correctly from camera at +Y looking down
    obj.rotation_euler = (math.radians(-90), math.radians(180), 0)
    
    mat = create_material(f"mat_label_{text}", (1, 1, 0.9, 1), emission=10.0)
    obj.data.materials.append(mat)
    
    return obj


def create_ball(name, color_name, pos):
    """Create a transaction ball with optional physics."""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.35, location=pos)
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.shade_smooth()
    
    color = COLORS[color_name]
    mat = create_material(f"mat_{name}", color, emission=8.0)
    obj.data.materials.append(mat)
    
    # Add rigid body for physics
    if USE_PHYSICS:
        try:
            bpy.ops.rigidbody.object_add(type='ACTIVE')
            obj.rigid_body.collision_shape = 'SPHERE'
            obj.rigid_body.mass = 0.5
            obj.rigid_body.friction = 0.8
            obj.rigid_body.restitution = 0.4   # Moderate bounce
            obj.rigid_body.linear_damping = 0.5  # Settle quickly
            obj.rigid_body.angular_damping = 0.5
            obj.rigid_body.collision_margin = 0.04
            # CRITICAL: Start kinematic so it follows keyframes initially
            obj.rigid_body.kinematic = True
            # Set initial keyframe to ensure kinematic from frame 1
            obj.keyframe_insert(data_path="rigid_body.kinematic", frame=1)
        except:
            pass
    
    return obj


def animate_ball_hybrid(ball, waypoints, start_frame):
    """
    Hybrid animation: keyframes for ALL movement, physics only inside units.
    
    waypoints: list of (position, is_unit) tuples
               is_unit=True means enable physics briefly for bouncing
    """
    frame = start_frame
    
    # First pass: set ALL location keyframes for the complete path
    # This ensures the ball always has a defined position
    keyframe_times = []
    
    for i, (pos, is_unit) in enumerate(waypoints):
        keyframe_times.append((frame, pos, is_unit))
        
        if is_unit:
            frame += FRAMES_IN_UNIT  # Long pause in unit
        else:
            frame += FRAMES_TRAVEL   # Quick travel
    
    # Set all location keyframes first (ball always knows where to be)
    for f, pos, _ in keyframe_times:
        ball.location = pos
        ball.keyframe_insert(data_path="location", frame=f)
    
    # Second pass: set kinematic keyframes (when to enable physics)
    if USE_PHYSICS and ball.rigid_body:
        for i, (f, pos, is_unit) in enumerate(keyframe_times):
            if is_unit:
                # Arrive at unit - kinematic ON (follow keyframe to exact position)
                ball.rigid_body.kinematic = True
                ball.keyframe_insert(data_path="rigid_body.kinematic", frame=f)
                
                # After settling in position, enable physics for 30 frames
                physics_start = f + 5
                ball.rigid_body.kinematic = False
                ball.keyframe_insert(data_path="rigid_body.kinematic", frame=physics_start)
                
                # Before leaving, disable physics so keyframes take over again
                physics_end = f + FRAMES_IN_UNIT - 10
                ball.rigid_body.kinematic = True
                ball.keyframe_insert(data_path="rigid_body.kinematic", frame=physics_end)
            else:
                # Traveling - always kinematic (pure keyframe)
                ball.rigid_body.kinematic = True
                ball.keyframe_insert(data_path="rigid_body.kinematic", frame=f)
    
    # Smooth interpolation for location, constant for kinematic switches
    try:
        if ball.animation_data and ball.animation_data.action:
            fcurves = getattr(ball.animation_data.action, 'fcurves', None)
            if fcurves:
                for fc in fcurves:
                    if 'location' in fc.data_path:
                        for kf in fc.keyframe_points:
                            kf.interpolation = 'BEZIER'
                    elif 'kinematic' in fc.data_path:
                        for kf in fc.keyframe_points:
                            kf.interpolation = 'CONSTANT'
    except:
        pass


def animate_ball(ball, waypoints, start_frame, frames_per_stop=30):
    """Simple keyframe animation (used when USE_PHYSICS=False)."""
    frame = start_frame
    
    for pos in waypoints:
        ball.location = pos
        ball.keyframe_insert(data_path="location", frame=frame)
        frame += frames_per_stop
    
    try:
        if ball.animation_data and ball.animation_data.action:
            fcurves = getattr(ball.animation_data.action, 'fcurves', None)
            if fcurves:
                for fc in fcurves:
                    for kf in fc.keyframe_points:
                        kf.interpolation = 'BEZIER'
    except:
        pass


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
    print("Creating Hybrid Physics Scene...")
    print(f"USE_PHYSICS = {USE_PHYSICS}")
    
    clear_scene()
    setup_world()
    setup_camera()
    setup_lighting()
    
    # Set up physics world
    if USE_PHYSICS:
        setup_physics_world()
    
    # Create all structure boxes (these become collision objects)
    print("Creating structures...")
    for name, cfg in STRUCTURES.items():
        create_box(name, cfg['pos'], cfg['size'], cfg['color'])
        label_pos = (cfg['pos'][0], cfg['pos'][1] + 0.6, cfg['pos'][2])
        create_label(cfg['label'], label_pos)
    
    # Create animated transactions
    print("Creating transactions...")
    
    # Unit center positions (balls drop slightly into top of box)
    wcache_center = (0, 0.5, 6)
    write_rs_center = (-4, 0.5, 2)
    read_rs_center = (4, 0.5, 2)
    dram_center = (0, 0.5, -3)
    read_return_center = (8, 0.5, -3)
    
    def get_slot_offset(slot_index, max_slots=4):
        """Get X,Z offset for ball slot - spread balls out in units."""
        offsets = [(-0.7, 0.3), (-0.2, 0.3), (0.3, 0.3), (0.8, 0.3),
                   (-0.7, -0.3), (-0.2, -0.3), (0.3, -0.3), (0.8, -0.3)]
        return offsets[slot_index % len(offsets)]
    
    # WRITE transactions (6 balls)
    # Path: Enter -> WCache -> Write RS -> DRAM
    # Waypoints: (position, is_unit) - is_unit=True means physics happens here
    num_writes = 6
    for i in range(num_writes):
        x_off, z_off = get_slot_offset(i)
        
        if USE_PHYSICS:
            waypoints = [
                ((0 + x_off, 0.5, 12), False),                                     # Enter
                ((wcache_center[0] + x_off, 0.5, wcache_center[2] + z_off), True), # WCache - physics
                ((write_rs_center[0] + x_off, 0.5, write_rs_center[2] + z_off), True), # Write RS - physics
                ((dram_center[0] - 1.5 + x_off, 0.5, dram_center[2] + z_off), True),  # DRAM - physics
            ]
            ball = create_ball(f"write_{i}", "write_ball", waypoints[0][0])
            start = 1 + i * 40  # More stagger for physics to work
            animate_ball_hybrid(ball, waypoints, start_frame=start)
        else:
            waypoints = [
                (0 + x_off, 0.5, 12),
                (wcache_center[0] + x_off, 0.5, wcache_center[2]),
                (write_rs_center[0] + x_off, 0.5, write_rs_center[2]),
                (dram_center[0] - 1.5 + x_off, 0.5, dram_center[2]),
            ]
            ball = create_ball(f"write_{i}", "write_ball", waypoints[0])
            start = 1 + i * 25
            animate_ball(ball, waypoints, start_frame=start, frames_per_stop=40)
    
    # READ transactions (6 balls)
    # Path: Enter -> Read RS -> DRAM -> Read Return -> Exit
    num_reads = 6
    for i in range(num_reads):
        x_off, z_off = get_slot_offset(i)
        
        if USE_PHYSICS:
            waypoints = [
                ((4 + x_off, 0.5, 12), False),                                     # Enter
                ((read_rs_center[0] + x_off, 0.5, read_rs_center[2] + z_off), True),  # Read RS - physics
                ((dram_center[0] + 1.5 + x_off, 0.5, dram_center[2] + z_off), True),  # DRAM - physics
                ((read_return_center[0] + x_off, 0.5, read_return_center[2] + z_off), True), # Read Return - physics
                ((read_return_center[0] + x_off, 0.5, 12), False),                 # Exit
            ]
            ball = create_ball(f"read_{i}", "read_ball", waypoints[0][0])
            start = 10 + i * 50
            animate_ball_hybrid(ball, waypoints, start_frame=start)
        else:
            waypoints = [
                (4 + x_off, 0.5, 12),
                (read_rs_center[0] + x_off, 0.5, read_rs_center[2]),
                (dram_center[0] + 1.5 + x_off, 0.5, dram_center[2]),
                (read_return_center[0] + x_off, 0.5, read_return_center[2]),
                (read_return_center[0] + x_off, 0.5, 12),
            ]
            ball = create_ball(f"read_{i}", "read_ball", waypoints[0])
            start = 10 + i * 30
            animate_ball(ball, waypoints, start_frame=start, frames_per_stop=45)
    
    # Render settings
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    bpy.context.scene.frame_end = 600
    
    print("=" * 50)
    if USE_PHYSICS:
        print("HYBRID PHYSICS MODE")
        print("- Balls travel via keyframes between units")
        print("- Inside units: physics kicks in (bounce/roll)")
        print("")
        print("To disable physics, set USE_PHYSICS = False at top of script")
    else:
        print("PURE KEYFRAME MODE (no physics)")
    print("")
    print("12 transactions created (6 writes, 6 reads)")
    print("Press SPACEBAR to play.")


# Run
if __name__ == "__main__":
    create_scene()
