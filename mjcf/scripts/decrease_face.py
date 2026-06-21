import os
import trimesh
import fast_simplification

mesh_path = '/home/felix/wheel_leg_description/mjcf/meshes/base_link.STL'

print("正在加载大模型文件，330万面需要些时间，请稍候...")
mesh = trimesh.load(mesh_path)

current_faces = len(mesh.faces)
target_faces = 30000

print(f"当前面数: {current_faces}")

# 核心修复：手动计算缩减比例，直接调用 fast_simplification 绕过 trimesh 的 Bug 接口
# 例如：(330万 - 3万) / 330万 ≈ 0.9909 (即减去 99.09% 的面)
reduction_rate = (current_faces - target_faces) / current_faces

if reduction_rate > 0:
    print(f"开始减面，缩减比例: {reduction_rate:.4f}...")
    
    # 直接将 trimesh 读出的顶点和面传给 fast_simplification
    out_vertices, out_faces = fast_simplification.simplify(
        mesh.vertices, 
        mesh.faces, 
        target_reduction=reduction_rate
    )
    
    # 将减面后的结果重新打包回 trimesh 对象
    simplified_mesh = trimesh.Trimesh(vertices=out_vertices, faces=out_faces)
    
    print(f"减面完成！当前面数: {len(simplified_mesh.faces)}")

    # 覆盖保存为标准的二进制 STL
    simplified_mesh.export(mesh_path)
    print(f"已成功覆盖并保存二进制轻量化模型: {mesh_path}")
else:
    print("当前面数已低于目标面数，无需减面。")