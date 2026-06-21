# ---------------------------------------------------------------------------------
# 运行方式：
# 请使用 Isaac Sim 5.1 自带的 Python 环境运行此脚本。
# 终端执行：
# ~/.local/share/ov/pkg/isaac-sim-5.1.0/python.sh convert_mjcf_to_usd.py
# ---------------------------------------------------------------------------------

import os
import sys

# 启动 Isaac Sim 无头模式（Headless）
from isaacsim import SimulationApp
simulation_app = SimulationApp({"headless": True})

import omni.kit.commands
import omni.usd
from omni.isaac.core.utils.extensions import enable_extension

# 启用必需的扩展插件
enable_extension("omni.importer.mjcf")
enable_extension("omni.isaac.core")

# 引入 MJCF 导入器配置模块
import omni.importer.mjcf as mjcf_importer

def convert_mjcf_to_usd(mjcf_file_path, output_usd_path):
    print(f"正在配置 MJCF 导入器...")
    
    # 实例化导入配置
    import_config = mjcf_importer.ImportConfig()
    
    # 核心物理参数映射配置
    import_config.import_inertia_tensor = True  # 导入我们在 MJCF 里写的 fullinertia
    import_config.fix_base = False              # 允许浮动基座 (Freejoint)
    import_config.distance_scale = 1.0          # 长度单位：米
    import_config.density = 0.0                 # 既然有明确 mass，就不使用密度估算
    import_config.import_sites = True           # 必须导入 site，因为闭链约束依赖它们
    import_config.create_body_for_multiple_shapes = False 
    import_config.make_default_prim = True      # 将机器人设为 USD 的默认 Prim

    print(f"正在解析并导入: {mjcf_file_path}")
    
    # 使用命令执行导入，这会在当前 USD Stage 中生成完整的物理树
    status, prim_path = omni.kit.commands.execute(
        "MjcfCreateAsset",
        mjcf_path=mjcf_file_path,
        import_config=import_config,
        prim_path="/World/wheel_leg"
    )

    if not status:
        print("错误: MJCF 导入失败！请检查 STL 路径是否正确。")
        simulation_app.close()
        sys.exit(1)

    print(f"导入成功！机器人的根节点位于: {prim_path}")
    print(f"正在保存为 USD 文件...")

    # 获取当前上下文并保存为 USD 文件
    ctx = omni.usd.get_context()
    ctx.save_as_stage(output_usd_path)

    print(f"\n✅ 转换完成！")
    print(f"USD 文件已保存至: {os.path.abspath(output_usd_path)}")
    print(f"你现在可以直接在 Isaac Sim 5.1 的 GUI 中打开这个 USD 文件进行仿真了。")

if __name__ == "__main__":
    # 配置你的 MJCF 文件路径（请确保和 XML 文件在同级目录运行此脚本）
    input_mjcf = "../wheel_leg.xml"
    output_usd = "wheel_leg.usd"
    
    # 检查输入文件是否存在
    if not os.path.exists(input_mjcf):
        print(f"找不到文件: {input_mjcf}。请确保脚本与 xml 文件在同一目录。")
        simulation_app.close()
        sys.exit(1)
        
    convert_mjcf_to_usd(input_mjcf, output_usd)
    
    # 优雅关闭仿真应用
    simulation_app.close()