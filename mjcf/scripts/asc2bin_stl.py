import os
import trimesh

mesh_dir = '/home/felix/wheel_leg_description/mjcf/meshes/'

for filename in os.listdir(mesh_dir):
    if filename.lower().endswith('.stl'):
        filepath = os.path.join(mesh_dir, filename)
        try:
            # Trimesh 读取后重新导出，默认会保存为标准的二进制 STL
            mesh = trimesh.load(filepath)
            # 如果面数太多，可以考虑在这里添加减面逻辑，不过通常转成二进制就够了
            if len(mesh.faces) > 200000:
                print(f"警告: {filename} 面数超标 ({len(mesh.faces)})，可能需要进 Blender 减面")
            mesh.export(filepath)
            print(f"已修复: {filename}")
        except Exception as e:
            print(f"处理 {filename} 时出错: {e}")