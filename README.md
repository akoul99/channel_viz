# Memory Channel Transaction Visualizer

A tool for visualizing transaction flow through the memory channel (CBridge, WCache, Row Sorters, DRAM).

## Quick Start

```bash
cd /home/scratch.ashwink_mobile/channel_viz

# Generate static layout image
/home/utils/Python/3.8/3.8.6-20201102/bin/python3 channel_layout_static.py

# View the generated image
# Output: channel_layout.png
```

## Files

- `channel_layout_static.py` - Generates static layout image (matplotlib, headless)
- `channel_visualizer.py` - Interactive version (pygame, requires display)

## Layout

```
                ┌─────────┐
                │ WCache  │
                └─────────┘
        ┌─────────┐    ┌─────────┐
        │Write RS │    │ Read RS │
        └─────────┘    └─────────┘
        ════════════════════════════  (Interface Boundary)
            ┌─────────────┐         ┌──────────┐
            │    DRAM     │         │ Read Ret │
            └─────────────┘         └──────────┘
```

## Blender 3D Visualization (Recommended)

### Getting Blender
```bash
# Download (Linux portable version - no install needed)
cd /home/scratch.ashwink_mobile
wget https://download.blender.org/release/Blender4.0/blender-4.0.2-linux-x64.tar.xz
tar -xf blender-4.0.2-linux-x64.tar.xz

# Run Blender
./blender-4.0.2-linux-x64/blender
```

Or download from https://blender.org/download/

### Running the Scene Script
1. Open Blender
2. Click "Scripting" tab at the top
3. Click "Open" → select `blender_channel_scene.py`
4. Click ▶ "Run Script" (or press Alt+P)
5. Press Z → select "Rendered" to see the glow effects
6. Press F12 to render a frame, Ctrl+F12 for animation

### Visual Style
- **Theme**: Dark cyberpunk with neon glows
- **Camera**: Top-down isometric
- **Transactions**: Glowing spheres (cyan=read, orange=write)

## Files

- `blender_channel_scene.py` - **Main Blender scene generator**
- `channel_layout_static.py` - 2D matplotlib layout (reference)
- `channel_visualizer.py` - Pygame version (requires display)

## Roadmap

- [x] Step 1: Basic 2D layout design
- [x] Step 2: Blender 3D scene with cyberpunk style
- [x] Step 3: Sample transaction animations
- [ ] Step 4: Event log format definition
- [ ] Step 5: Log parser for real simulation data
- [ ] Step 6: Full animation generation pipeline
