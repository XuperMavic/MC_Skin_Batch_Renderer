import bpy
import os
import sys

"""
Blender Skin Rendering Script
Used to replace skin textures of Minecraft character models and render output

Usage:
blender --background [blender_file] --python blender_render_script.py -- [skin_path] [output_path] [width] [height]
"""

# Get command line arguments
argv = sys.argv
argv = argv[argv.index('--') + 1:]  # Skip arguments before --

if len(argv) < 2:
    print("Error: Missing parameters")
    print("Usage: blender --background [blender_file] --python blender_render_script.py -- [skin_path] [output_path] [width] [height] [device] [bg_color]")
    sys.exit(1)

skin_path = argv[0]
output_path = argv[1]

# Check current blend file
current_blend_file = bpy.data.filepath
print(f"Current blend file: {current_blend_file}")

# Set default dimensions
width = 1024
height = 1024

# Set default device to CPU
device = "CPU"

# Set default background color
bg_color = (0, 0, 0, 0)  # Default transparent background

# Get width and height parameters (if provided)
if len(argv) >= 4:
    try:
        width = int(argv[2])
        height = int(argv[3])
        print(f"Using custom dimensions: {width}x{height}")
    except ValueError:
        print("Warning: Width/height parameters are not valid integers, using default size 1024x1024")

# Get device parameter (if provided)
if len(argv) >= 5:
    device = argv[4].upper()
    if device not in ["CPU", "GPU"]:
        print(f"Warning: Invalid device '{device}', using default 'CPU'")
        device = "CPU"

# Get background color parameter (if provided)
if len(argv) >= 6:
    try:
        bg_color = tuple(map(float, argv[5].split(',')))
        if len(bg_color) == 3:
            bg_color = bg_color + (1.0,)  # If only RGB, add Alpha channel
        elif len(bg_color) == 4:
            pass  # Already contains Alpha channel
        else:
            print("Warning: Invalid background color format, using default transparent background")
            bg_color = (0, 0, 0, 0)
    except:
        print("Warning: Invalid background color format, using default transparent background")
        bg_color = (0, 0, 0, 0)

print(f"Using render device: {device}")
print(f"Background color: {bg_color}")

print(f"Skin path: {skin_path}")
print(f"Output path: {output_path}")

# Check if file exists
if not os.path.exists(skin_path):
    print(f"Error: Skin file not found: {skin_path}")
    sys.exit(1)

# Set up rendering parameters
def setup_rendering(scene, device, bg_color):
    """Set up rendering parameters"""
    # Set render engine
    if bpy.app.version >= (2, 80, 0):
        scene.render.engine = 'CYCLES' if 'CYCLES' in scene.render.engine else 'BLENDER_EEVEE'
    else:
        scene.render.engine = 'CYCLES' if 'CYCLES' in bpy.context.user_preferences.addons else 'BLENDER_RENDER'
    
    # Set background color
    if bpy.app.version >= (2, 80, 0):
        # Blender 2.8+ uses world nodes for background color
        if not scene.world:
            scene.world = bpy.data.worlds.new("World")
        scene.world.use_nodes = True
        nodes = scene.world.node_tree.nodes
        background_node = None
        
        # Find background node
        for node in nodes:
            if node.type == 'BACKGROUND':
                background_node = node
                break
        
        # Create background node if not found
        if not background_node:
            background_node = nodes.new(type='ShaderNodeBackground')
            # Connect to world output node
            output_node = nodes.get('World Output')
            if output_node:
                links = scene.world.node_tree.links
                links.new(background_node.outputs['Background'], output_node.inputs['Surface'])
        
        # Set background color
        background_node.inputs['Color'].default_value = bg_color
    else:
        # Blender 2.79 and earlier
        if not scene.world:
            scene.world = bpy.data.worlds.new("World")
        scene.world.horizon_color = bg_color[:3]  # Only use RGB part
    
    # Set output format
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'  # Include transparency
    scene.render.image_settings.compression = 90  # Compression quality
    
    # Enable transparent rendering based on background color alpha value
    if bg_color[3] < 1.0:
        scene.render.film_transparent = True  # Enable transparent rendering for Blender 2.8+
    else:
        scene.render.film_transparent = False  # Disable transparent rendering for opaque background
    
    # Set render resolution
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    
    # Set sampling (if using Cycles)
    if scene.render.engine == 'CYCLES':
        scene.cycles.samples = 128  # Balance quality and speed
        scene.cycles.use_adaptive_sampling = True
        
        # Set render device (CPU or GPU)
        if device == "GPU":
            # Enable GPU rendering
            scene.cycles.device = 'GPU'
            
            # Configure GPU devices
            prefs = bpy.context.preferences
            cycles_preferences = prefs.addons['cycles'].preferences
            
            # Update device list (in some Blender versions manual refresh is needed)
            cycles_preferences.refresh_devices()
            
            # Ensure GPU rendering is enabled
            if cycles_preferences.compute_device_type in ['NONE', 'CPU']:
                # Try different methods to get available device types based on Blender version
                try:
                    # Method for newer Blender versions
                    compute_device_types = cycles_preferences.get_compute_device_types()
                except AttributeError:
                    # Fallback method for older Blender versions
                    compute_device_types = ['CUDA', 'OPTIX', 'OPENCL']
                
                # Try CUDA first
                if 'CUDA' in compute_device_types:
                    cycles_preferences.compute_device_type = 'CUDA'
                    print("Using CUDA for GPU rendering")
                # Then try OPTIX if CUDA is not available
                elif 'OPTIX' in compute_device_types:
                    cycles_preferences.compute_device_type = 'OPTIX'
                    print("Using OPTIX for GPU rendering")
                # Then try OPENCL if available
                elif 'OPENCL' in compute_device_types:
                    cycles_preferences.compute_device_type = 'OPENCL'
                    print("Using OPENCL for GPU rendering")
                # Fallback to CPU if no GPU compute device found
                else:
                    scene.cycles.device = 'CPU'
                    print("Warning: No GPU compute devices found, falling back to CPU")
                    return
            
            # Enable all available GPU devices
            for compute_device in cycles_preferences.devices:
                if compute_device.type in ['CUDA', 'OPTIX']:
                    compute_device.use = True
                    print(f"Enabled {compute_device.type} device: {compute_device.name}")
        else:
            # Enable CPU rendering
            scene.cycles.device = 'CPU'
            print("Using CPU for rendering")

# Replace skin texture
def replace_skin_texture(skin_file_path):
    """Replace the model's skin texture"""
    texture_updated = False
    
    # Load new skin image
    new_skin = bpy.data.images.load(skin_file_path)
    
    # Check if it's model a (original model 4), only replace player character skin materials
    current_blend_file = bpy.data.filepath
    is_modela = "modela" in current_blend_file.lower() or "model_a" in current_blend_file.lower()
    
    # Player material names
    player_material_names = ['Steve皮肤', 'Alex皮肤', 'Steve Skin', 'Alex Skin']
    
    # Iterate through all materials
    for material in bpy.data.materials:
        print(f"Checking material: {material.name}")
        
        # For model a, only process player character materials
        # For other models (including model 5), process all materials
        if is_modela:
            # Only process player character materials, not village/villager materials
            if any(player_mat in material.name for player_mat in player_material_names):
                print(f"  Processing player material: {material.name}")
                process_material = True
            else:
                print(f"  Skipping non-player material: {material.name}")
                process_material = False
        else:
            # For other models, process all materials
            print(f"  Processing material: {material.name}")
            process_material = True
        
        if process_material:
            # Check if using nodes (Blender 2.8+)
            if material.use_nodes:
                nodes = material.node_tree.nodes
                
                # Iterate through nodes to find texture image nodes
                for node in nodes:
                    if node.type == 'TEX_IMAGE':
                        print(f"    Found texture node: {node.name}")
                        print(f"    Updating skin texture: {node.name}")
                        node.image = new_skin
                        texture_updated = True
                        break

            # Material system for Blender 2.79 and earlier
            else:
                if hasattr(material, 'texture_slots'):
                    for slot in material.texture_slots:
                        if slot and slot.texture and slot.texture.type == 'IMAGE':
                            print(f"    Updating legacy material texture: {slot.texture.name}")
                            slot.texture.image = new_skin
                            texture_updated = True
                            break
    
    return texture_updated

# Get current scene
scene = bpy.context.scene

# Set render parameters
setup_rendering(scene, device, bg_color)

# Set output path
scene.render.filepath = output_path

# Replace skin texture
if replace_skin_texture(skin_path):
    print("Skin texture updated successfully")
else:
    print("Warning: No skin texture nodes found, you may need to check the Blender file manually")

# Execute rendering
print("Starting rendering...")
bpy.ops.render.render(write_still=True)
print(f"Rendering completed, output to: {output_path}")

# Clean up temporary data
for img in bpy.data.images:
    if img.name != bpy.data.images[0].name:  # Keep original image
        bpy.data.images.remove(img)

print("Script execution completed")