"""
Aestivus CLI 入口点
- aestiv: 仅启动后端 API 服务
- aestiva: 同时启动后端 + 前端开发服务器
"""
import subprocess
import sys
import os
from pathlib import Path


def get_project_root() -> Path:
    """获取项目根目录 (aestivus/)"""
    # cli.py 在 src-python/aestiv/ 下，往上两级是 aestivus/
    return Path(__file__).parent.parent.parent


def run_backend():
    """启动后端 API 服务 (uvicorn)"""
    src_python = get_project_root() / "src-python"
    os.chdir(src_python)
    
    cmd = [
        sys.executable, "-m", "uvicorn",
        "main:app",
        "--host", "127.0.0.1",
        "--port", "8009",
        "--reload"
    ]
    subprocess.run(cmd)


def run_full():
    """同时启动后端 + 前端开发服务器"""
    project_root = get_project_root()
    src_python = project_root / "src-python"
    
    # 使用 concurrently 同时运行两个服务
    # 等效于: concurrently "cd src-python && uvicorn main:app --host 127.0.0.1 --port 8009 --reload" "vite dev --port 1096"
    backend_cmd = f"cd {src_python} && uvicorn main:app --host 127.0.0.1 --port 8009 --reload"
    frontend_cmd = f"cd {project_root} && vite dev --port 1096"
    
    try:
        # 尝试使用 concurrently (需要 yarn 安装)
        subprocess.run(
            ["npx", "concurrently", backend_cmd, frontend_cmd],
            cwd=project_root,
            shell=True
        )
    except FileNotFoundError:
        # 如果没有 concurrently，手动启动两个进程
        import threading
        
        def run_backend_thread():
            os.chdir(src_python)
            subprocess.run([
                sys.executable, "-m", "uvicorn",
                "main:app", "--host", "127.0.0.1", "--port", "8009", "--reload"
            ])
        
        def run_frontend_thread():
            subprocess.run(["npx", "vite", "dev", "--port", "1096"], cwd=project_root, shell=True)
        
        backend_thread = threading.Thread(target=run_backend_thread, daemon=True)
        frontend_thread = threading.Thread(target=run_frontend_thread, daemon=True)
        
        backend_thread.start()
        frontend_thread.start()
        
        try:
            backend_thread.join()
            frontend_thread.join()
        except KeyboardInterrupt:
            print("\n停止服务...")


if __name__ == "__main__":
    # 直接运行时默认启动完整服务
    run_full()
