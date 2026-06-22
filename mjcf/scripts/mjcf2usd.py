# ---------------------------------------------------------------------------------
# 运行方式：
# ~/.local/share/ov/pkg/isaac-sim-5.1.0/python.sh convert_mjcf_to_usd.py
# ---------------------------------------------------------------------------------

import os
import sys

print("=====================================================")
print("⏳ [阶段 1/4] 正在启动 Isaac Sim 物理引擎内核...")
print("=====================================================")

# 使用无头模式
from isaacsim import SimulationApp
simulation_app = SimulationApp({"headless": True})

print("✅ [阶段 1/4] 引擎内核启动成功！\n")

import omni.kit.commands
import omni.usd
import omni.kit.app
import importlib

# 尝试兼容不同版本的 enable_extension 路径
try:
    from isaacsim.core.utils.extensions import enable_extension
except ImportError:
    from omni.isaac.core.utils.extensions import enable_extension

print("⏳ [阶段 2/4] 正在全盘扫描系统内的 MJCF 扩展包...")

# --------------------------------------------------------------------------------
# 【核心修复区】：智能全盘搜索并匹配真实的 MJCF 扩展名称
# --------------------------------------------------------------------------------
manager = omni.kit.app.get_app().get_extension_manager()
mjcf_module_name = None

# 获取系统中所有已注册的扩展包
extensions = manager.get_extensions()
for ext in extensions:
    try:
        # 获取扩展的名字和 ID (容错处理)
        ext_name = ext.get("name", "") if isinstance(ext, dict) else getattr(ext, "name", "")
        ext_id = ext.get("id", "") if isinstance(ext, dict) else getattr(ext, "id", "")
        
        search_target = f"{ext_name} {ext_id}".lower()
        
        # 只要带有 mjcf 且具有 importer 性质就锁定它
        if "mjcf" in search_target:
            mjcf_module_name = ext_name if ext_name else ext_id.split('-')[0]
            # 优先匹配带有 importer 字样的模块
            if "importer" in search_target:
                break 
    except Exception:
        continue

if not mjcf_module_name:
    print("\n❌ 严重错误：在你的 Isaac Sim 中扫描了所有扩展包，依然找不到任何与 'mjcf' 相关的包！")
    print("原因：你的 Isaac Sim 5.1 安装包可能严重缺失（精简版），或者你没有下载对应的 Asset Importers 扩展包。")
    simulation_app.close()
    sys.exit(1)

print(f"✅ [阶段 2/4] 智能探测成功！找到 MJCF 真实扩展名: {mjcf_module_name}")

# 启用动态找到的扩展包
enable_extension(mjcf_module_name)

# 【关键修复 1】：必须强制引擎刷新事件循环！
# 启用扩展是异步的，必须让引擎 "Tick" 几次，扩展内的命令才能来得及注册完毕。
for _ in range(10):
    simulation_app.update()

# 动态加载其 ImportConfig 类
ImportConfig = None
try:
    mjcf_importer = importlib.import_module(mjcf_module_name)
    ImportConfig = mjcf_importer.ImportConfig
except AttributeError:
    try:
        # 很多内部类放在 _mjcf 隐藏域下
        mjcf_importer = importlib.import_module(f"{mjcf_module_name}._mjcf")
        ImportConfig = mjcf_importer.ImportConfig
    except Exception as e:
        print(f"❌ 无法从模块 {mjcf_module_name} 中解析 ImportConfig，报错: {e}")
        simulation_app.close()
        sys.exit(1)

# --------------------------------------------------------------------------------

def convert_mjcf_to_usd(mjcf_file_path, output_usd_path):
    # 【最关键的修复】：强制将路径转为绝对路径，防止 Isaac Sim C++ 底层解析相对路径时崩溃
    abs_mjcf_path = os.path.abspath(mjcf_file_path)
    abs_output_path = os.path.abspath(output_usd_path)
    
    print(f"\n⏳ [阶段 3/4] 正在解析并导入 MJCF 物理与闭链约束: {abs_mjcf_path}")
    
    # 配置你的 MJCF 转换参数
    import_config = ImportConfig()
    
    # 安全地设置属性，防止新版 API 删除某些属性导致报错
    if hasattr(import_config, "import_inertia_tensor"):
        import_config.import_inertia_tensor = True  
        
    if hasattr(import_config, "fix_base"):
        import_config.fix_base = False              
        
    if hasattr(import_config, "distance_scale"):
        import_config.distance_scale = 1.0          
        
    if hasattr(import_config, "import_sites"):
        import_config.import_sites = True           
        
    if hasattr(import_config, "make_default_prim"):
        import_config.make_default_prim = True      
    
    # 【关键修复 2】：动态探寻真正的命令名字
    available_cmds = omni.kit.commands.get_commands().keys()
    target_cmd = "MjcfCreateAsset" 
    
    if target_cmd not in available_cmds:
        # 模糊搜寻：找出含有 mjcf 并且大概率是导入的命令
        mjcf_cmds = [cmd for cmd in available_cmds if "mjcf" in cmd.lower() and ("import" in cmd.lower() or "create" in cmd.lower())]
        if mjcf_cmds:
            target_cmd = mjcf_cmds[0]
        else:
            print(f"❌ 系统内依然未注册 MJCF 命令！可用的带 mjcf 的命令有: {[c for c in available_cmds if 'mjcf' in c.lower()]}")
            simulation_app.close()
            sys.exit(1)
            
    print(f"✅ 将调用底层注册命令: {target_cmd}")

    # 核心转换指令 (附带参数回退机制)
    try:
        status, prim_path = omni.kit.commands.execute(
            target_cmd,
            mjcf_path=abs_mjcf_path,
            import_config=import_config,
            prim_path="/World/wheel_leg"
        )
    except TypeError:
        # 【关键修复 3】：兼容部分版本的参数变动（prim_path 改为 dest_path）
        print("⚠️ 捕获到参数不匹配，正在尝试切换参数模式(dest_path)...")
        status, prim_path = omni.kit.commands.execute(
            target_cmd,
            mjcf_path=abs_mjcf_path,
            import_config=import_config,
            dest_path="/World/wheel_leg"
        )

    if not status:
        print("❌ 错误: MJCF 导入失败！请检查 XML 文件和 STL 路径是否有误。")
        simulation_app.close()
        sys.exit(1)

    print(f"✅ [阶段 3/4] 成功导入！机器人在引擎内的根节点位于: {prim_path}")
    print(f"\n⏳ [阶段 4/4] 正在将场景固化并导出为 USD 文件...")

    # 保存 USD
    ctx = omni.usd.get_context()
    ctx.save_as_stage(abs_output_path)

    print(f"✅ [阶段 4/4] 转换彻底完成！")
    print(f"USD 文件已生成完毕: {abs_output_path}")
    print(f"请将此 USD 文件拷贝回 Windows 本地，即可畅快预览。")

if __name__ == "__main__":
    # 配置路径（确保这里写的是你带有 <equality> 等闭链约束的那个 XML 文件）
    # 在这里可以继续用相对路径，程序会在上面将其转换为安全的绝对路径
    input_mjcf = "../wheel_leg.xml" 
    output_usd = "../wheel_leg_from_mjcf.usd"
    
    if not os.path.exists(input_mjcf):
        print(f"找不到文件: {input_mjcf}。请确保脚本与 xml 文件在同一目录。")
        simulation_app.close()
        sys.exit(1)
        
    convert_mjcf_to_usd(input_mjcf, output_usd)
    
    # 优雅退出
    simulation_app.close()