import bpy
import os
import sys

"""
Blender皮肤渲染脚本
用于替换Minecraft角色模型的皮肤纹理并渲染输出

使用方法:
blender --background [blender_file] --python blender_render_script.py -- [skin_path] [output_path] [width] [height] [device]
"""

# 获取命令行参数
argv = sys.argv
argv = argv[argv.index('--') + 1:]  # 跳过--之前的参数

if len(argv) < 2:
    print("错误: 缺少参数")
    print("用法: blender --background [blender_file] --python blender_render_script.py -- [skin_path] [output_path] [width] [height] [device] [bg_color]")
    sys.exit(1)

skin_path = argv[0]
output_path = argv[1]

# 检查当前Blend文件
current_blend_file = bpy.data.filepath
print(f"当前Blend文件: {current_blend_file}")

# 设置默认尺寸
width = 1024
height = 1024
# 设置默认渲染设备
device = "CPU"
# 设置默认背景颜色
bg_color = (0, 0, 0, 0)  # 默认透明背景

# 获取宽高参数（如果提供）
if len(argv) >= 4:
    try:
        width = int(argv[2])
        height = int(argv[3])
        print(f"使用自定义尺寸: {width}x{height}")
    except ValueError:
        print("警告: 宽高参数不是有效的整数，使用默认尺寸 1024x1024")

# 获取渲染设备参数（如果提供）
if len(argv) >= 5:
    device = argv[4].upper()
    if device not in ["CPU", "GPU"]:
        print("警告: 渲染设备参数无效，使用默认设备 CPU")
        device = "CPU"

# 获取背景颜色参数（如果提供）
if len(argv) >= 6:
    try:
        bg_color = tuple(map(float, argv[5].split(',')))
        if len(bg_color) == 3:
            bg_color = bg_color + (1.0,)  # 如果只有RGB，添加Alpha通道
        elif len(bg_color) == 4:
            pass  # 已经包含Alpha通道
        else:
            print("警告: 背景颜色参数格式无效，使用默认透明背景")
            bg_color = (0, 0, 0, 0)
    except:
        print("警告: 背景颜色参数格式无效，使用默认透明背景")
        bg_color = (0, 0, 0, 0)

print(f"皮肤路径: {skin_path}")
print(f"输出路径: {output_path}")
print(f"渲染设备: {device}")
print(f"背景颜色: {bg_color}")

# 检查文件是否存在
if not os.path.exists(skin_path):
    print(f"错误: 皮肤文件不存在: {skin_path}")
    sys.exit(1)

# 设置渲染参数
def setup_rendering(scene, device, bg_color):
    """设置渲染参数"""
    # 设置渲染引擎
    if bpy.app.version >= (2, 80, 0):
        scene.render.engine = 'CYCLES' if 'CYCLES' in scene.render.engine else 'BLENDER_EEVEE'
    else:
        scene.render.engine = 'CYCLES' if 'CYCLES' in bpy.context.user_preferences.addons else 'BLENDER_RENDER'
    
    # 设置背景颜色
    if bpy.app.version >= (2, 80, 0):
        # Blender 2.8+ 使用世界节点设置背景颜色
        if not scene.world:
            scene.world = bpy.data.worlds.new("World")
        scene.world.use_nodes = True
        nodes = scene.world.node_tree.nodes
        background_node = None
        
        # 查找背景节点
        for node in nodes:
            if node.type == 'BACKGROUND':
                background_node = node
                break
        
        # 如果没有找到背景节点，创建一个
        if not background_node:
            background_node = nodes.new(type='ShaderNodeBackground')
            # 连接到世界输出节点
            output_node = nodes.get('World Output')
            if output_node:
                links = scene.world.node_tree.links
                links.new(background_node.outputs['Background'], output_node.inputs['Surface'])
        
        # 设置背景颜色
        background_node.inputs['Color'].default_value = bg_color
    else:
        # Blender 2.79及以下版本
        if not scene.world:
            scene.world = bpy.data.worlds.new("World")
        scene.world.horizon_color = bg_color[:3]  # 只使用RGB部分
    
    # 设置输出格式
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'  # 包含透明度
    scene.render.image_settings.compression = 90  # 压缩质量
    
    # 根据背景颜色的Alpha值决定是否启用透明渲染
    if bg_color[3] < 1.0:
        scene.render.film_transparent = True  # 对于Blender 2.8+版本，启用透明渲染
    else:
        scene.render.film_transparent = False  # 背景不透明时关闭透明渲染
    
    # 设置渲染尺寸
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    
    # 设置采样（如果使用Cycles）
    if scene.render.engine == 'CYCLES':
        scene.cycles.samples = 128  # 平衡质量和速度
        scene.cycles.use_adaptive_sampling = True
        
        # 设置渲染设备
        if device == "GPU":
            scene.cycles.device = 'GPU'
            # 启用CUDA或OPTIX渲染器（根据实际情况）
            if bpy.app.version >= (2, 80, 0):
                prefs = bpy.context.preferences
                cycles_preferences = prefs.addons['cycles'].preferences
                
                # 更新设备列表（在某些Blender版本中需要手动刷新）
                cycles_preferences.refresh_devices()
                
                # 获取所有可用的计算设备类型
                try:
                    # 新Blender版本的方法
                    compute_device_types = cycles_preferences.get_compute_device_types()
                except AttributeError:
                    # 旧Blender版本的回退方法
                    compute_device_types = ['CUDA', 'OPTIX', 'OPENCL']
                
                # 确保GPU渲染已启用
                if cycles_preferences.compute_device_type in ['NONE', 'CPU']:
                    # 优先尝试CUDA
                    if 'CUDA' in compute_device_types:
                        cycles_preferences.compute_device_type = 'CUDA'
                        print("使用CUDA进行GPU渲染")
                    # 如果CUDA不可用，尝试OPTIX
                    elif 'OPTIX' in compute_device_types:
                        cycles_preferences.compute_device_type = 'OPTIX'
                        print("使用OPTIX进行GPU渲染")
                    # 如果CUDA和OPTIX都不可用，尝试OPENCL
                    elif 'OPENCL' in compute_device_types:
                        cycles_preferences.compute_device_type = 'OPENCL'
                        print("使用OPENCL进行GPU渲染")
                    # 如果没有找到GPU计算设备，回退到CPU
                    else:
                        scene.cycles.device = 'CPU'
                        print("警告：未找到GPU计算设备，回退到CPU渲染")
                        return
                
                # 启用所有可用的GPU设备
                for compute_device in cycles_preferences.devices:
                    if compute_device.type in ['CUDA', 'OPTIX']:
                        compute_device.use = True
                        print(f"已启用{compute_device.type}设备：{compute_device.name}")
        else:
            scene.cycles.device = 'CPU'
            print("已设置CPU渲染设备")

# 替换皮肤纹理
def replace_skin_texture(skin_file_path):
    """替换模型的皮肤纹理"""
    texture_updated = False
    
    # 加载新的皮肤图像
    new_skin = bpy.data.images.load(skin_file_path)
    
    # 检查是否为模型a（原模型4），只替换玩家角色的皮肤材质
    current_blend_file = bpy.data.filepath
    is_modela = "modela" in current_blend_file.lower() or "model_a" in current_blend_file.lower()
    
    # 玩家材质名称
    player_material_names = ['Steve皮肤', 'Alex皮肤', 'Steve Skin', 'Alex Skin']
    
    # 遍历所有材质
    for material in bpy.data.materials:
        print(f"检查材质: {material.name}")
        
        # 对于模型a，只处理玩家角色材质
        # 对于其他模型（包括模型5），处理所有材质
        if is_modela:
            # 只处理玩家角色材质，不处理村民材质
            if any(player_mat in material.name for player_mat in player_material_names):
                print(f"  处理玩家材质: {material.name}")
                process_material = True
            else:
                print(f"  跳过非玩家材质: {material.name}")
                process_material = False
        else:
            # 对于其他模型，处理所有材质
            print(f"  处理材质: {material.name}")
            process_material = True
        
        if process_material:
            # 检查是否使用节点（Blender 2.8+）
            if material.use_nodes:
                nodes = material.node_tree.nodes
                
                # 遍历节点查找纹理图像节点
                for node in nodes:
                    if node.type == 'TEX_IMAGE':
                        print(f"    找到纹理节点: {node.name}")
                        print(f"    更新皮肤纹理: {node.name}")
                        node.image = new_skin
                        texture_updated = True
                        break

            # Blender 2.79及以下版本的材质系统
            else:
                if hasattr(material, 'texture_slots'):
                    for slot in material.texture_slots:
                        if slot and slot.texture and slot.texture.type == 'IMAGE':
                            print(f"    更新旧版材质纹理: {slot.texture.name}")
                            slot.texture.image = new_skin
                            texture_updated = True
                            break
    
    return texture_updated

# 获取当前场景
scene = bpy.context.scene

# 设置渲染参数
setup_rendering(scene, device, bg_color)

# 设置输出路径
scene.render.filepath = output_path

# 替换皮肤纹理
if replace_skin_texture(skin_path):
    print("皮肤纹理更新成功")
else:
    print("警告: 未找到皮肤纹理节点，可能需要手动检查Blender文件")

# 执行渲染
print("开始渲染...")
bpy.ops.render.render(write_still=True)
print(f"渲染完成，输出到: {output_path}")

# 清理临时数据
for img in bpy.data.images:
    if img.name != bpy.data.images[0].name:  # 保留原始图像
        bpy.data.images.remove(img)

print("脚本执行完成")