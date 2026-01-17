#!/usr/bin/env python3
"""
Channel Transaction Visualizer - Step 1: Basic Layout
Creates a 2D schematic view of the memory channel structures.

Layout:
                ┌─────────┐
                │ WCache  │
                └─────────┘
        ┌─────────┐    ┌─────────┐
        │Write RS │    │ Read RS │
        └─────────┘    └─────────┘
        ════════════════════════════  (boundary)
            ┌─────────────┐         ┌──────────┐
            │    DRAM     │         │ Read Ret │
            └─────────────┘         └──────────┘
"""

import pygame
import sys

# ============================================================================
# Configuration
# ============================================================================

# Window settings
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 900
WINDOW_TITLE = "Memory Channel Visualizer"

# Colors (RGB)
COLORS = {
    'background': (20, 25, 35),        # Dark blue-gray
    'structure_fill': (45, 55, 72),    # Slightly lighter
    'structure_border': (100, 120, 150), # Border color
    'wcache': (76, 175, 80),           # Green
    'write_rs': (255, 152, 0),         # Orange
    'read_rs': (33, 150, 243),         # Blue
    'dram': (156, 39, 176),            # Purple
    'read_return': (0, 188, 212),      # Cyan
    'boundary_line': (80, 90, 100),    # Gray for boundary
    'text': (220, 230, 240),           # Light gray for text
    'text_dark': (40, 50, 60),         # Dark text for light backgrounds
}

# Structure dimensions and positions
# All positions are (x, y) for top-left corner
STRUCTURES = {
    'wcache': {
        'x': 450,
        'y': 50,
        'width': 300,
        'height': 120,
        'color': COLORS['wcache'],
        'label': 'WCache',
        'sublabel': 'Write Coalescing Cache',
    },
    'write_rs': {
        'x': 200,
        'y': 220,
        'width': 250,
        'height': 150,
        'color': COLORS['write_rs'],
        'label': 'Write Row Sorter',
        'sublabel': 'Bank Queues',
    },
    'read_rs': {
        'x': 550,
        'y': 220,
        'width': 250,
        'height': 150,
        'color': COLORS['read_rs'],
        'label': 'Read Row Sorter',
        'sublabel': 'Bank Queues',
    },
    'dram': {
        'x': 300,
        'y': 480,
        'width': 400,
        'height': 200,
        'color': COLORS['dram'],
        'label': 'DRAM',
        'sublabel': 'Memory Banks',
    },
    'read_return': {
        'x': 850,
        'y': 480,
        'width': 180,
        'height': 200,
        'color': COLORS['read_return'],
        'label': 'Read Data',
        'sublabel': 'Return Path',
    },
}

# Boundary line position (y-coordinate)
BOUNDARY_Y = 430

# ============================================================================
# Drawing Functions
# ============================================================================

def draw_rounded_rect(surface, color, rect, border_radius=10, border_color=None, border_width=2):
    """Draw a rounded rectangle with optional border."""
    x, y, width, height = rect
    
    # Draw filled rounded rectangle
    pygame.draw.rect(surface, color, rect, border_radius=border_radius)
    
    # Draw border if specified
    if border_color:
        pygame.draw.rect(surface, border_color, rect, width=border_width, border_radius=border_radius)


def draw_structure(surface, font_large, font_small, name, config):
    """Draw a single structure box with label."""
    x = config['x']
    y = config['y']
    width = config['width']
    height = config['height']
    color = config['color']
    label = config['label']
    sublabel = config.get('sublabel', '')
    
    # Draw the box with slightly transparent fill
    # Create a semi-transparent surface
    box_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    
    # Fill with semi-transparent color
    fill_color = (*color, 180)  # Add alpha
    pygame.draw.rect(box_surface, fill_color, (0, 0, width, height), border_radius=12)
    
    # Draw border
    border_color = tuple(min(c + 50, 255) for c in color)
    pygame.draw.rect(box_surface, border_color, (0, 0, width, height), width=3, border_radius=12)
    
    # Blit to main surface
    surface.blit(box_surface, (x, y))
    
    # Draw label (centered)
    label_surface = font_large.render(label, True, COLORS['text'])
    label_rect = label_surface.get_rect(center=(x + width // 2, y + height // 2 - 10))
    surface.blit(label_surface, label_rect)
    
    # Draw sublabel if present
    if sublabel:
        sublabel_surface = font_small.render(sublabel, True, (*COLORS['text'][:3], 180))
        sublabel_rect = sublabel_surface.get_rect(center=(x + width // 2, y + height // 2 + 20))
        surface.blit(sublabel_surface, sublabel_rect)


def draw_boundary_line(surface, y, width):
    """Draw the boundary line between row sorters and DRAM."""
    # Draw dashed line
    dash_length = 20
    gap_length = 10
    x = 100
    end_x = width - 100
    
    while x < end_x:
        pygame.draw.line(
            surface, 
            COLORS['boundary_line'], 
            (x, y), 
            (min(x + dash_length, end_x), y), 
            2
        )
        x += dash_length + gap_length
    
    # Draw label
    font = pygame.font.Font(None, 24)
    label = font.render("── Interface Boundary ──", True, COLORS['boundary_line'])
    label_rect = label.get_rect(center=(width // 2, y - 15))
    surface.blit(label, label_rect)


def draw_flow_arrows(surface):
    """Draw arrows indicating transaction flow."""
    arrow_color = (100, 110, 130)
    
    # Helper to draw an arrow
    def draw_arrow(start, end, color=arrow_color):
        pygame.draw.line(surface, color, start, end, 2)
        # Arrowhead
        import math
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        arrow_size = 10
        arrow_angle = math.pi / 6
        
        left = (
            end[0] - arrow_size * math.cos(angle - arrow_angle),
            end[1] - arrow_size * math.sin(angle - arrow_angle)
        )
        right = (
            end[0] - arrow_size * math.cos(angle + arrow_angle),
            end[1] - arrow_size * math.sin(angle + arrow_angle)
        )
        pygame.draw.polygon(surface, color, [end, left, right])
    
    # WCache to Write RS
    wcache = STRUCTURES['wcache']
    write_rs = STRUCTURES['write_rs']
    start = (wcache['x'] + wcache['width'] // 3, wcache['y'] + wcache['height'])
    end = (write_rs['x'] + write_rs['width'] // 2, write_rs['y'])
    draw_arrow(start, end, COLORS['wcache'])
    
    # Write RS to DRAM
    dram = STRUCTURES['dram']
    start = (write_rs['x'] + write_rs['width'] // 2, write_rs['y'] + write_rs['height'])
    end = (dram['x'] + dram['width'] // 3, dram['y'])
    draw_arrow(start, end, COLORS['write_rs'])
    
    # Read RS to DRAM
    read_rs = STRUCTURES['read_rs']
    start = (read_rs['x'] + read_rs['width'] // 2, read_rs['y'] + read_rs['height'])
    end = (dram['x'] + 2 * dram['width'] // 3, dram['y'])
    draw_arrow(start, end, COLORS['read_rs'])
    
    # DRAM to Read Return
    read_return = STRUCTURES['read_return']
    start = (dram['x'] + dram['width'], dram['y'] + dram['height'] // 2)
    end = (read_return['x'], read_return['y'] + read_return['height'] // 2)
    draw_arrow(start, end, COLORS['dram'])


def draw_title(surface, font):
    """Draw the title at the top."""
    title = font.render("Memory Channel Transaction Flow", True, COLORS['text'])
    title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 25))
    surface.blit(title, title_rect)


def draw_legend(surface, font):
    """Draw a legend explaining the structures."""
    legend_x = 50
    legend_y = WINDOW_HEIGHT - 100
    
    items = [
        ('Write Path', COLORS['wcache']),
        ('Read Path', COLORS['read_rs']),
        ('DRAM', COLORS['dram']),
        ('Response', COLORS['read_return']),
    ]
    
    for i, (label, color) in enumerate(items):
        x = legend_x + i * 150
        # Draw color box
        pygame.draw.rect(surface, color, (x, legend_y, 20, 20), border_radius=4)
        # Draw label
        text = font.render(label, True, COLORS['text'])
        surface.blit(text, (x + 30, legend_y + 2))


# ============================================================================
# Main
# ============================================================================

def main():
    # Initialize Pygame
    pygame.init()
    
    # Create window
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption(WINDOW_TITLE)
    
    # Fonts
    try:
        font_title = pygame.font.Font(None, 36)
        font_large = pygame.font.Font(None, 32)
        font_small = pygame.font.Font(None, 24)
        font_legend = pygame.font.Font(None, 22)
    except:
        font_title = pygame.font.SysFont('arial', 28)
        font_large = pygame.font.SysFont('arial', 24)
        font_small = pygame.font.SysFont('arial', 18)
        font_legend = pygame.font.SysFont('arial', 16)
    
    # Clock for controlling frame rate
    clock = pygame.time.Clock()
    
    # Main loop
    running = True
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_s:
                    # Save screenshot
                    pygame.image.save(screen, "channel_layout.png")
                    print("Screenshot saved as channel_layout.png")
        
        # Clear screen
        screen.fill(COLORS['background'])
        
        # Draw title
        draw_title(screen, font_title)
        
        # Draw flow arrows (behind structures)
        draw_flow_arrows(screen)
        
        # Draw boundary line
        draw_boundary_line(screen, BOUNDARY_Y, WINDOW_WIDTH)
        
        # Draw all structures
        for name, config in STRUCTURES.items():
            draw_structure(screen, font_large, font_small, name, config)
        
        # Draw legend
        draw_legend(screen, font_legend)
        
        # Draw instructions
        instructions = font_small.render("Press 'S' to save screenshot, 'ESC' to quit", True, (100, 110, 130))
        screen.blit(instructions, (WINDOW_WIDTH - 350, WINDOW_HEIGHT - 30))
        
        # Update display
        pygame.display.flip()
        
        # Cap frame rate
        clock.tick(60)
    
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
