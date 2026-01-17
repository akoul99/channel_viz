#!/home/utils/Python/3.8/3.8.6-20201102/bin/python3
"""
Channel Transaction Visualizer - Static Layout (Matplotlib version)
Creates a 2D schematic view of the memory channel structures.

This version uses matplotlib for compatibility on systems where pygame
might be difficult to install.

Usage:
    python3 channel_layout_static.py
    
This will display the layout and save it as channel_layout.png
"""

# Use non-interactive backend for headless environments
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as path_effects
import numpy as np

# ============================================================================
# Configuration
# ============================================================================

# Figure size (inches)
FIG_WIDTH = 14
FIG_HEIGHT = 10

# Colors
COLORS = {
    'background': '#141923',        # Dark blue-gray
    'wcache': '#4CAF50',            # Green
    'write_rs': '#FF9800',          # Orange  
    'read_rs': '#2196F3',           # Blue
    'dram': '#9C27B0',              # Purple
    'read_return': '#00BCD4',       # Cyan
    'boundary': '#505a64',          # Gray
    'text': '#dce6f0',              # Light gray
    'arrow': '#687080',             # Arrow gray
}

# Structure definitions: (x, y, width, height)
# Using a coordinate system where (0,0) is bottom-left, (100, 100) is top-right
STRUCTURES = {
    'wcache': {
        'x': 35, 'y': 75, 'width': 30, 'height': 12,
        'color': COLORS['wcache'],
        'label': 'WCache',
        'sublabel': 'Write Coalescing Cache',
    },
    'write_rs': {
        'x': 15, 'y': 50, 'width': 25, 'height': 15,
        'color': COLORS['write_rs'],
        'label': 'Write Row Sorter',
        'sublabel': 'Bank Queues',
    },
    'read_rs': {
        'x': 50, 'y': 50, 'width': 25, 'height': 15,
        'color': COLORS['read_rs'],
        'label': 'Read Row Sorter',
        'sublabel': 'Bank Queues',
    },
    'dram': {
        'x': 25, 'y': 10, 'width': 40, 'height': 20,
        'color': COLORS['dram'],
        'label': 'DRAM',
        'sublabel': 'Memory Banks',
    },
    'read_return': {
        'x': 78, 'y': 10, 'width': 15, 'height': 20,
        'color': COLORS['read_return'],
        'label': 'Read Data',
        'sublabel': 'Return Path',
    },
}

# Boundary line y-position
BOUNDARY_Y = 38


# ============================================================================
# Drawing Functions
# ============================================================================

def create_structure_box(ax, config):
    """Create a rounded rectangle for a structure."""
    x = config['x']
    y = config['y']
    width = config['width']
    height = config['height']
    color = config['color']
    label = config['label']
    sublabel = config.get('sublabel', '')
    
    # Create rounded rectangle
    box = FancyBboxPatch(
        (x, y), width, height,
        boxstyle="round,pad=0.02,rounding_size=1.5",
        facecolor=color,
        edgecolor='white',
        linewidth=2,
        alpha=0.85
    )
    ax.add_patch(box)
    
    # Add main label
    text = ax.text(
        x + width/2, y + height/2 + 1,
        label,
        fontsize=14, fontweight='bold',
        color='white',
        ha='center', va='center'
    )
    text.set_path_effects([
        path_effects.withStroke(linewidth=2, foreground='black')
    ])
    
    # Add sublabel
    if sublabel:
        subtext = ax.text(
            x + width/2, y + height/2 - 3,
            sublabel,
            fontsize=9,
            color='white',
            alpha=0.8,
            ha='center', va='center'
        )
        subtext.set_path_effects([
            path_effects.withStroke(linewidth=1, foreground='black')
        ])


def draw_arrow(ax, start, end, color=COLORS['arrow'], style='simple'):
    """Draw an arrow between two points."""
    arrow = FancyArrowPatch(
        start, end,
        arrowstyle='-|>',
        mutation_scale=15,
        color=color,
        linewidth=2,
        alpha=0.7
    )
    ax.add_patch(arrow)


def draw_boundary_line(ax):
    """Draw the interface boundary line."""
    # Dashed line
    ax.axhline(y=BOUNDARY_Y, xmin=0.05, xmax=0.95, 
               color=COLORS['boundary'], linestyle='--', linewidth=2, alpha=0.7)
    
    # Label
    ax.text(50, BOUNDARY_Y + 2, '── Interface Boundary ──',
            fontsize=10, color=COLORS['boundary'],
            ha='center', va='bottom', style='italic')


def draw_flow_arrows(ax):
    """Draw arrows showing transaction flow."""
    wcache = STRUCTURES['wcache']
    write_rs = STRUCTURES['write_rs']
    read_rs = STRUCTURES['read_rs']
    dram = STRUCTURES['dram']
    read_return = STRUCTURES['read_return']
    
    # WCache to Write RS
    start = (wcache['x'] + wcache['width']/3, wcache['y'])
    end = (write_rs['x'] + write_rs['width']/2, write_rs['y'] + write_rs['height'])
    draw_arrow(ax, start, end, COLORS['wcache'])
    
    # Write RS to DRAM
    start = (write_rs['x'] + write_rs['width']/2, write_rs['y'])
    end = (dram['x'] + dram['width']/3, dram['y'] + dram['height'])
    draw_arrow(ax, start, end, COLORS['write_rs'])
    
    # Read RS to DRAM
    start = (read_rs['x'] + read_rs['width']/2, read_rs['y'])
    end = (dram['x'] + 2*dram['width']/3, dram['y'] + dram['height'])
    draw_arrow(ax, start, end, COLORS['read_rs'])
    
    # DRAM to Read Return
    start = (dram['x'] + dram['width'], dram['y'] + dram['height']/2)
    end = (read_return['x'], read_return['y'] + read_return['height']/2)
    draw_arrow(ax, start, end, COLORS['read_return'])


def draw_input_arrows(ax):
    """Draw arrows showing requests entering the system."""
    wcache = STRUCTURES['wcache']
    read_rs = STRUCTURES['read_rs']
    read_return = STRUCTURES['read_return']
    
    # Write requests entering WCache
    ax.annotate('', xy=(wcache['x'] + wcache['width']/2, wcache['y'] + wcache['height']),
                xytext=(wcache['x'] + wcache['width']/2, 95),
                arrowprops=dict(arrowstyle='-|>', color=COLORS['wcache'], lw=2))
    ax.text(wcache['x'] + wcache['width']/2, 97, 'Write\nRequests',
            ha='center', va='bottom', fontsize=9, color=COLORS['wcache'])
    
    # Read requests entering Read RS
    ax.annotate('', xy=(read_rs['x'] + read_rs['width']/2, read_rs['y'] + read_rs['height']),
                xytext=(read_rs['x'] + read_rs['width']/2, 75),
                arrowprops=dict(arrowstyle='-|>', color=COLORS['read_rs'], lw=2))
    ax.text(read_rs['x'] + read_rs['width']/2, 77, 'Read\nRequests',
            ha='center', va='bottom', fontsize=9, color=COLORS['read_rs'])
    
    # Read data exiting
    ax.annotate('', xy=(read_return['x'] + read_return['width']/2, 95),
                xytext=(read_return['x'] + read_return['width']/2, read_return['y'] + read_return['height']),
                arrowprops=dict(arrowstyle='-|>', color=COLORS['read_return'], lw=2))
    ax.text(read_return['x'] + read_return['width']/2, 97, 'Read\nResponses',
            ha='center', va='bottom', fontsize=9, color=COLORS['read_return'])


def draw_legend(ax):
    """Draw a legend."""
    legend_items = [
        ('Write Path', COLORS['wcache']),
        ('Read Path', COLORS['read_rs']),
        ('DRAM', COLORS['dram']),
        ('Response', COLORS['read_return']),
    ]
    
    y = 3
    for i, (label, color) in enumerate(legend_items):
        x = 5 + i * 20
        box = FancyBboxPatch(
            (x, y), 3, 2,
            boxstyle="round,pad=0.01,rounding_size=0.5",
            facecolor=color,
            edgecolor='white',
            linewidth=1
        )
        ax.add_patch(box)
        ax.text(x + 4, y + 1, label, fontsize=9, color=COLORS['text'], va='center')


# ============================================================================
# Main
# ============================================================================

def main():
    # Create figure
    fig, ax = plt.subplots(1, 1, figsize=(FIG_WIDTH, FIG_HEIGHT))
    
    # Set background color
    fig.patch.set_facecolor(COLORS['background'])
    ax.set_facecolor(COLORS['background'])
    
    # Set axis limits and remove axes
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Title
    ax.text(50, 96, 'Memory Channel Transaction Flow',
            fontsize=20, fontweight='bold', color=COLORS['text'],
            ha='center', va='top')
    
    # Draw boundary line first (behind other elements)
    draw_boundary_line(ax)
    
    # Draw flow arrows
    draw_flow_arrows(ax)
    
    # Draw input/output arrows
    draw_input_arrows(ax)
    
    # Draw all structures
    for name, config in STRUCTURES.items():
        create_structure_box(ax, config)
    
    # Draw legend
    draw_legend(ax)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save to file
    output_file = 'channel_layout.png'
    plt.savefig(output_file, facecolor=COLORS['background'], 
                edgecolor='none', dpi=150, bbox_inches='tight')
    print(f"Saved layout to {output_file}")
    
    # Close the figure to free memory
    plt.close(fig)


if __name__ == "__main__":
    main()
