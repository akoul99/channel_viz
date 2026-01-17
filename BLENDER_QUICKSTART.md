# Blender Quick Start Guide 🎬

Never used Blender? No problem! Here's everything you need to know.

## 1. Getting Blender

### Option A: Download Portable (Recommended for Linux)
```bash
cd /home/scratch.ashwink_mobile
wget https://download.blender.org/release/Blender4.0/blender-4.0.2-linux-x64.tar.xz
tar -xf blender-4.0.2-linux-x64.tar.xz
./blender-4.0.2-linux-x64/blender
```

### Option B: Download for Your Desktop
Go to https://blender.org/download/ and get the version for your OS.

---

## 2. Blender Interface Overview

When you open Blender, you'll see:

```
┌─────────────────────────────────────────────────────────────┐
│  File  Edit  Render  Window  Help     [Layout][Modeling]... │  ← Top menu + Workspaces
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                    3D VIEWPORT                              │  ← Main view
│                    (your scene)                             │
│                                                             │
├──────────────────────────────┬──────────────────────────────┤
│        Timeline              │        Properties            │  ← Animation & settings
└──────────────────────────────┴──────────────────────────────┘
```

---

## 3. Running Our Script

### Step-by-Step:

1. **Open Blender**

2. **Switch to Scripting workspace**
   - Click "Scripting" tab at the very top of the window

3. **Open our script**
   - In the text editor panel, click "Open"
   - Navigate to `/home/scratch.ashwink_mobile/channel_viz/`
   - Select `blender_channel_scene.py`

4. **Run the script**
   - Click the ▶ (Play) button, OR
   - Press `Alt + P`

5. **See the result**
   - The 3D viewport will now show the channel visualization
   - Press `Z` → select "Rendered" to see the glow effects

---

## 4. Essential Controls

### Navigation (in 3D Viewport)
| Action | Control |
|--------|---------|
| Rotate view | Middle mouse button drag |
| Pan view | Shift + Middle mouse drag |
| Zoom | Scroll wheel |
| Reset view | Numpad 0 (camera view) |
| Top view | Numpad 7 |
| Front view | Numpad 1 |

### Viewport Shading (Press Z for pie menu)
| Mode | Description |
|------|-------------|
| Solid | Basic preview (fast) |
| Material | Shows colors |
| **Rendered** | Shows glows/effects ← Use this! |
| Wireframe | See-through |

### Useful Shortcuts
| Action | Shortcut |
|--------|----------|
| Render image | F12 |
| Render animation | Ctrl + F12 |
| Play animation | Spacebar |
| Go to frame 1 | Shift + Left Arrow |
| Select object | Left click |
| Delete selected | X |
| Undo | Ctrl + Z |

---

## 5. Rendering

### Quick Preview
- Press `Spacebar` to play the animation in viewport
- Use "Rendered" shading mode (Z key) for accurate preview

### Render Single Frame
- Press `F12`
- Image appears in a new window
- Save with Image → Save As

### Render Full Animation
- Press `Ctrl + F12`
- Output goes to `/tmp/` by default
- Change output path in: Properties → Output → Output Path

### Render Settings Location
Right side panel → Output Properties (printer icon):
- Resolution: 1920 x 1080
- Frame Rate: 30 fps
- Output format: PNG or FFmpeg Video

---

## 6. Customizing the Scene

### Move Structures
1. Select an object (left click)
2. Press `G` to grab/move
3. Press `X`, `Y`, or `Z` to constrain to axis
4. Click to confirm, or `Esc` to cancel

### Change Colors
1. Select an object
2. Go to Material Properties (sphere icon, right panel)
3. Expand the node tree and adjust color values

### Adjust Camera
1. Select the camera (or press Numpad 0 for camera view)
2. Press `G` to move, `R` to rotate
3. Or adjust in Properties → Object Properties

---

## 7. Exporting Video

### Method 1: FFmpeg (Direct to MP4)
1. Output Properties → Output → set path (e.g., `//channel_anim`)
2. File Format → FFmpeg Video
3. Encoding → Container: MPEG-4
4. Render → Render Animation (Ctrl+F12)

### Method 2: PNG Sequence → FFmpeg
1. Render as PNG sequence (default)
2. Use command line:
```bash
ffmpeg -framerate 30 -i '/tmp/%04d.png' -c:v libx264 -pix_fmt yuv420p channel_animation.mp4
```

---

## 8. Troubleshooting

### "Nothing appears after running script"
- Make sure you clicked "Run Script" (▶ button)
- Check the console for errors (Window → Toggle System Console)

### "I can't see the glows"
- Press Z → select "Rendered" 
- Or switch render engine to Eevee (Render Properties)

### "Animation doesn't play"
- Press Spacebar in the viewport
- Make sure timeline shows frames 1-120

### "Rendering is slow"
- Use Eevee instead of Cycles (Render Properties → Render Engine)
- Reduce resolution temporarily

---

## 9. Next Steps

Once comfortable:
1. Adjust the camera angle to your liking
2. Tweak colors in materials
3. Add more transaction spheres
4. We'll add event log parsing to animate real data!

---

## Quick Reference Card

```
NAVIGATION          ACTIONS             RENDERING
─────────────       ─────────────       ─────────────
MMB: Rotate         G: Grab/Move        F12: Render frame
Shift+MMB: Pan      R: Rotate           Ctrl+F12: Render anim
Scroll: Zoom        S: Scale            Space: Play preview
Numpad 0: Camera    X: Delete           
Z: Shading menu     Ctrl+Z: Undo        
```

Happy Blending! 🎨
