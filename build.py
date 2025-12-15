#!/usr/bin/env python3
"""
aestival 构建脚本
支持 pywebview 桌面应用打包
"""
import json
import sys
import subprocess
import platform
import shutil
from pathlib import Path


def run_command(command, description, cwd=None):
    """运行命令并显示状态"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            cwd=cwd,
            capture_output=True,
            text=True
        )
        print(f"✅ {description} 完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 失败!")
        print(f"错误: {e.stderr}")
        return False


def check_dependencies():
    """检查必要的依赖"""
    print("🔍 检查依赖...")
    
    required_tools = {
        "yarn": "yarn --version",
        "python": "python --version",
        "pip": "pip --version"
    }
    
    missing_tools = []
    for tool, check_cmd in required_tools.items():
        try:
            subprocess.run(check_cmd, shell=True, check=True, capture_output=True)
            print(f"  ✅ {tool}")
        except subprocess.CalledProcessError:
            print(f"  ❌ {tool} 未安装")
            missing_tools.append(tool)
    
    if missing_tools:
        print(f"\n❌ 缺少必要工具: {', '.join(missing_tools)}")
        sys.exit(1)
    
    print("✅ 所有依赖已就绪")


def detect_platform():
    """检测当前平台"""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux"
    elif system == "windows":
        return "windows"
    else:
        print(f"⚠️  未知平台: {system}，默认使用 linux")
        return "linux"


def build_frontend():
    """构建 SvelteKit 前端"""
    return run_command("yarn build", "构建前端")


def install_python_deps():
    """安装 Python 依赖"""
    return run_command(
        "pip install -r requirements.txt",
        "安装 Python 依赖",
        cwd="src-python"
    )


def build_pywebview_app():
    """使用 PyInstaller 打包 pywebview 应用"""
    platform_name = detect_platform()
    
    # 检查 PyInstaller
    try:
        subprocess.run("pyinstaller --version", shell=True, check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("📦 安装 PyInstaller...")
        if not run_command("pip install pyinstaller", "安装 PyInstaller"):
            return False
    
    # 构建目录
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)
    
    # PyInstaller 参数
    app_name = "aestival"
    if platform_name == "windows":
        app_name += ".exe"
    
    # 构建命令
    pyinstaller_cmd = [
        "pyinstaller",
        "--name", "aestival",
        "--onefile",
        "--windowed",  # 无控制台窗口
        "--clean",
        "--distpath", str(dist_dir),
        "--add-data", f"../build{';' if platform_name == 'windows' else ':'}build",  # 包含前端构建
        "launcher.py"
    ]
    
    # 添加图标（如果存在）
    icon_path = Path("static/app-icon.ico" if platform_name == "windows" else "static/app-icon.png")
    if icon_path.exists():
        pyinstaller_cmd.extend(["--icon", str(icon_path)])
    
    cmd_str = " ".join(pyinstaller_cmd)
    return run_command(cmd_str, f"打包 pywebview 应用 ({platform_name})", cwd="src-python")


def copy_frontend_to_python():
    """复制前端构建到 Python 目录"""
    print("📁 复制前端构建文件...")
    
    src = Path("build")
    dst = Path("src-python/build")
    
    if not src.exists():
        print("❌ 前端构建目录不存在，请先运行 yarn build")
        return False
    
    # 清理旧的构建
    if dst.exists():
        shutil.rmtree(dst)
    
    # 复制
    shutil.copytree(src, dst)
    print("✅ 前端文件已复制")
    return True


def show_build_results():
    """显示构建结果"""
    print("\n🎉 构建完成!")
    print("\n📦 构建产物:")
    
    dist_dir = Path("dist")
    if dist_dir.exists():
        for item in dist_dir.iterdir():
            if item.is_file():
                size = item.stat().st_size / (1024 * 1024)
                print(f"   📄 {item.name} ({size:.1f} MB)")
    
    print("\n🚀 运行方式:")
    print("   开发模式: yarn dev:standalone")
    print("   pywebview: yarn dev:pywebview 或 cd src-python && python launcher.py")
    print("   打包应用: 运行 dist/ 目录下的可执行文件")


def main():
    """主函数"""
    print("🏗️  aestival 构建")
    print("=" * 50)
    
    args = sys.argv[1:]
    
    # 解析参数
    only_frontend = "--frontend" in args
    only_backend = "--backend" in args
    
    check_dependencies()
    print("")
    
    if only_frontend:
        print("🚀 仅构建前端...")
        if not build_frontend():
            sys.exit(1)
        return
    
    if only_backend:
        print("🚀 仅打包后端...")
        if not install_python_deps():
            sys.exit(1)
        if not build_pywebview_app():
            sys.exit(1)
        return
    
    # 完整构建
    print("🚀 开始完整构建...\n")
    
    build_steps = [
        ("前端构建", build_frontend),
        ("复制前端文件", copy_frontend_to_python),
        ("Python 依赖", install_python_deps),
        ("pywebview 打包", build_pywebview_app)
    ]
    
    for step_name, step_func in build_steps:
        print(f"📋 步骤: {step_name}")
        if not step_func():
            print(f"\n❌ 构建失败: {step_name}")
            sys.exit(1)
        print("")
    
    show_build_results()


if __name__ == "__main__":
    main()
