"""
anode - 快速启动单个 Node 的 CLI

用法:
    anode sleept          # 启动 sleept node
    anode sleept --tui    # 使用 TUI 模式 (无需浏览器)
    anode --list          # 列出所有可用的 nodes

原理:
    1. 启动轻量级本地 API (仅加载指定 adapter)
    2. 用 webview 打开单个 node 页面
"""

import argparse
import sys
import os
import asyncio
import threading
import webbrowser
from pathlib import Path
from typing import Optional


def get_available_nodes() -> list[str]:
    """获取所有可用的 node 名称"""
    adapters_dir = Path(__file__).parent.parent / "adapters"
    nodes = []
    for f in adapters_dir.glob("*_adapter.py"):
        name = f.stem.replace("_adapter", "")
        if name != "base":
            nodes.append(name)
    return sorted(nodes)


def run_node_tui(node_name: str):
    """以 TUI 模式运行 node (直接调用 adapter)"""
    # 动态导入 adapter
    try:
        # 添加 adapters 目录到 path
        adapters_dir = Path(__file__).parent.parent / "adapters"
        sys.path.insert(0, str(adapters_dir.parent))
        
        adapter_module = __import__(f"adapters.{node_name}_adapter", fromlist=[f"{node_name.title()}Adapter"])
        
        # 查找 Adapter 类
        adapter_class = None
        for name in dir(adapter_module):
            if name.lower() == f"{node_name}adapter":
                adapter_class = getattr(adapter_module, name)
                break
        
        if not adapter_class:
            print(f"❌ 未找到 {node_name} 的 Adapter 类")
            return
        
        adapter = adapter_class()
        print(f"✅ 已加载: {adapter.display_name}")
        print(f"   {adapter.description}")
        print()
        
        # 简单的交互式 CLI
        run_adapter_interactive(adapter, node_name)
        
    except ImportError as e:
        print(f"❌ 无法加载 {node_name} adapter: {e}")
        sys.exit(1)


def run_adapter_interactive(adapter, node_name: str):
    """交互式运行 adapter"""
    # 根据 node 类型提供不同的交互逻辑
    if node_name == "sleept":
        run_sleept_interactive(adapter)
    elif node_name == "recycleu":
        run_recycleu_interactive(adapter)
    else:
        print(f"ℹ️  {node_name} 暂不支持 TUI 模式，请使用 web 模式")
        print(f"   运行: anode {node_name}")


def run_sleept_interactive(adapter):
    """sleept 交互式模式"""
    from adapters.sleept_adapter import SleeptInput
    
    print("=" * 50)
    print("🕐 Sleept - 系统定时器")
    print("=" * 50)
    print()
    print("模式选择:")
    print("  1. 倒计时模式")
    print("  2. 网速监控模式") 
    print("  3. CPU 监控模式")
    print("  4. 获取系统状态")
    print("  q. 退出")
    print()
    
    while True:
        choice = input("请选择 [1-4/q]: ").strip()
        
        if choice == "q":
            break
        elif choice == "1":
            # 倒计时模式
            try:
                h = int(input("小时 [0]: ") or "0")
                m = int(input("分钟 [0]: ") or "0")
                s = int(input("秒数 [5]: ") or "5")
                dryrun = input("演练模式? [Y/n]: ").strip().lower() != "n"
                
                input_data = SleeptInput(
                    action="countdown",
                    hours=h, minutes=m, seconds=s,
                    dryrun=dryrun
                )
                
                def on_progress(p, msg):
                    print(f"\r⏱️  [{p:3d}%] {msg}", end="", flush=True)
                
                def on_log(msg):
                    print(f"\n📋 {msg}")
                
                result = asyncio.run(adapter.execute(input_data, on_progress, on_log))
                print(f"\n\n{'✅' if result.success else '❌'} {result.message}")
                
            except ValueError:
                print("❌ 请输入有效的数字")
            except KeyboardInterrupt:
                print("\n⏹️  已取消")
                
        elif choice == "2":
            # 网速监控
            try:
                up = float(input("上传阈值 KB/s [242]: ") or "242")
                down = float(input("下载阈值 KB/s [242]: ") or "242")
                dur = float(input("持续时间(分钟) [2]: ") or "2")
                dryrun = input("演练模式? [Y/n]: ").strip().lower() != "n"
                
                input_data = SleeptInput(
                    action="netspeed",
                    upload_threshold=up,
                    download_threshold=down,
                    net_duration=dur,
                    dryrun=dryrun
                )
                
                def on_progress(p, msg):
                    print(f"\r📡 [{p:3d}%] {msg}", end="", flush=True)
                
                def on_log(msg):
                    print(f"\n📋 {msg}")
                
                print("开始监控... (Ctrl+C 取消)")
                result = asyncio.run(adapter.execute(input_data, on_progress, on_log))
                print(f"\n\n{'✅' if result.success else '❌'} {result.message}")
                
            except ValueError:
                print("❌ 请输入有效的数字")
            except KeyboardInterrupt:
                print("\n⏹️  已取消")
                
        elif choice == "3":
            # CPU 监控
            try:
                cpu_th = float(input("CPU阈值% [10]: ") or "10")
                dur = float(input("持续时间(分钟) [2]: ") or "2")
                dryrun = input("演练模式? [Y/n]: ").strip().lower() != "n"
                
                input_data = SleeptInput(
                    action="cpu",
                    cpu_threshold=cpu_th,
                    cpu_duration=dur,
                    dryrun=dryrun
                )
                
                def on_progress(p, msg):
                    print(f"\r💻 [{p:3d}%] {msg}", end="", flush=True)
                
                def on_log(msg):
                    print(f"\n📋 {msg}")
                
                print("开始监控... (Ctrl+C 取消)")
                result = asyncio.run(adapter.execute(input_data, on_progress, on_log))
                print(f"\n\n{'✅' if result.success else '❌'} {result.message}")
                
            except ValueError:
                print("❌ 请输入有效的数字")
            except KeyboardInterrupt:
                print("\n⏹️  已取消")
                
        elif choice == "4":
            # 获取状态
            from adapters.sleept_adapter import SleeptInput
            input_data = SleeptInput(action="get_stats")
            result = asyncio.run(adapter.execute(input_data))
            print(f"💻 CPU: {result.current_cpu:.1f}%")
            print(f"📤 上传: {result.current_upload:.1f} KB/s")
            print(f"📥 下载: {result.current_download:.1f} KB/s")
            print()


def run_recycleu_interactive(adapter):
    """recycleu 交互式模式"""
    from adapters.recycleu_adapter import RecycleuInput
    
    print("=" * 50)
    print("🗑️  Recycleu - 回收站自动清理")
    print("=" * 50)
    print()
    print("操作选择:")
    print("  1. 立即清空回收站")
    print("  2. 启动定时清理")
    print("  q. 退出")
    print()
    
    while True:
        choice = input("请选择 [1-2/q]: ").strip()
        
        if choice == "q":
            break
        elif choice == "1":
            input_data = RecycleuInput(action="clean_now")
            
            def on_log(msg):
                print(f"📋 {msg}")
            
            result = asyncio.run(adapter.execute(input_data, on_log=on_log))
            print(f"{'✅' if result.success else '❌'} {result.message}")
            print()
            
        elif choice == "2":
            try:
                interval = int(input("清理间隔(秒) [10]: ") or "10")
                
                input_data = RecycleuInput(action="start", interval=interval)
                
                def on_progress(p, msg):
                    print(f"\r🗑️  [{p:3d}%] {msg}", end="", flush=True)
                
                def on_log(msg):
                    print(f"\n📋 {msg}")
                
                print("开始定时清理... (Ctrl+C 停止)")
                result = asyncio.run(adapter.execute(input_data, on_progress, on_log))
                print(f"\n\n{'✅' if result.success else '❌'} {result.message}")
                
            except ValueError:
                print("❌ 请输入有效的数字")
            except KeyboardInterrupt:
                print("\n⏹️  已停止")


def run_node_web(node_name: str, port: int = 8019):
    """以 Web 模式运行 node"""
    project_root = Path(__file__).parent.parent.parent
    src_python = project_root / "src-python"
    
    # 构建 URL，直接打开 node 的全屏页面
    url = f"http://localhost:1096/node/{node_name}"
    
    print(f"🚀 启动 {node_name} node...")
    print(f"   后端: http://localhost:{port}")
    print(f"   前端: {url}")
    print()
    
    # 添加 src-python 到 path
    sys.path.insert(0, str(src_python))
    os.chdir(src_python)
    
    import uvicorn
    import importlib.util
    
    # 动态加载 main.py
    spec = importlib.util.spec_from_file_location("main", src_python / "main.py")
    main_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main_module)
    app = main_module.app
    
    # 在后台线程启动服务器
    def run_server():
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # 等待服务器启动
    import time
    time.sleep(1)
    
    # 打开浏览器
    webbrowser.open(url)
    
    print("按 Ctrl+C 退出...")
    try:
        server_thread.join()
    except KeyboardInterrupt:
        print("\n👋 再见!")


def main():
    parser = argparse.ArgumentParser(
        description="anode - 快速启动单个 Node",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例子:
  anode sleept          启动 sleept node (web 模式)
  anode sleept --tui    启动 sleept node (TUI 模式)
  anode --list          列出所有可用的 nodes
        """
    )
    
    parser.add_argument("node", nargs="?", help="要启动的 node 名称")
    parser.add_argument("--list", "-l", action="store_true", help="列出所有可用的 nodes")
    parser.add_argument("--tui", "-t", action="store_true", help="使用 TUI 模式 (无需浏览器)")
    parser.add_argument("--port", "-p", type=int, default=8019, help="后端端口 (默认: 8019)")
    
    args = parser.parse_args()
    
    if args.list:
        nodes = get_available_nodes()
        print("可用的 Nodes:")
        for n in nodes:
            print(f"  - {n}")
        return
    
    if not args.node:
        parser.print_help()
        return
    
    node_name = args.node.lower()
    available = get_available_nodes()
    
    if node_name not in available:
        print(f"❌ 未知的 node: {node_name}")
        print(f"   可用: {', '.join(available[:10])}...")
        sys.exit(1)
    
    if args.tui:
        run_node_tui(node_name)
    else:
        run_node_web(node_name, args.port)


if __name__ == "__main__":
    main()
