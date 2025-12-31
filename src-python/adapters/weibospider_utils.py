"""
weiboSpider 工具函数
Cookie 获取和验证相关功能
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Callable, Dict, Optional, Any

import requests


async def validate_cookie_online(
    cookie: str,
    on_log: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    联网验证 Cookie 是否有效
    
    Returns:
        {"valid": bool, "message": str}
    """
    if not cookie:
        return {"valid": False, "message": "未提供 Cookie"}
    
    # 先检查本地字段
    has_sub = "SUB=" in cookie
    has_alf = "ALF=" in cookie
    
    if on_log:
        on_log("🔍 检查 Cookie 字段...")
        on_log(f"  SUB: {'✅' if has_sub else '❌'}")
        on_log(f"  ALF: {'✅' if has_alf else '❌'}")
    
    if not has_sub:
        return {"valid": False, "message": "Cookie 缺少 SUB 字段，无效"}
    
    # 联网验证
    if on_log:
        on_log("🌐 联网验证 Cookie...")
    
    try:
        headers = {
            'Cookie': cookie,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        resp = requests.get(
            'https://weibo.cn/account/setting',
            headers=headers,
            timeout=10,
            allow_redirects=False
        )
        
        # 302 跳转到登录页说明 cookie 无效
        if resp.status_code == 302:
            location = resp.headers.get('Location', '')
            if 'login' in location or 'passport' in location:
                if on_log:
                    on_log("❌ Cookie 已过期，需要重新登录")
                return {"valid": False, "message": "Cookie 已过期，请重新获取"}
        
        if resp.status_code == 200:
            content = resp.text
            if '设置' in content or '账号' in content:
                if on_log:
                    on_log("✅ Cookie 有效，已登录")
                return {"valid": True, "message": "Cookie 有效"}
            if '登录' in content:
                if on_log:
                    on_log("❌ Cookie 无效，未登录状态")
                return {"valid": False, "message": "Cookie 无效，请重新获取"}
        
        # 备用验证
        if on_log:
            on_log("⚠️ 尝试备用验证...")
        
        resp2 = requests.get('https://weibo.cn/', headers=headers, timeout=10)
        if '我的首页' in resp2.text:
            if on_log:
                on_log("✅ Cookie 有效")
            return {"valid": True, "message": "Cookie 有效"}
        
        return {"valid": True, "message": "Cookie 状态不确定，建议测试爬取"}
        
    except requests.exceptions.Timeout:
        if on_log:
            on_log("⚠️ 网络超时")
        return {"valid": True, "message": "网络超时，本地字段检查通过"}
    except Exception as e:
        if on_log:
            on_log(f"⚠️ 验证出错: {e}")
        return {"valid": True, "message": f"验证出错: {e}"}


async def get_cookie_via_remote_debug(
    browser: str,
    on_log: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    通过浏览器远程调试获取 Cookie（无需管理员权限）
    
    Returns:
        {"success": bool, "cookie": str, "message": str}
    """
    import subprocess
    
    DEBUG_PORT = 9222
    
    # 确定浏览器路径
    if browser == "edge":
        browser_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
        process_name = "msedge.exe"
    elif browser == "firefox":
        return {"success": False, "cookie": "", "message": "Firefox 暂不支持远程调试方式"}
    else:
        browser_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
        process_name = "chrome.exe"
    
    browser_path = None
    for p in browser_paths:
        if os.path.exists(p):
            browser_path = p
            break
    
    if not browser_path:
        return {"success": False, "cookie": "", "message": f"未找到 {browser} 浏览器"}
    
    # 获取用户数据目录
    local_app_data = os.getenv('LOCALAPPDATA', '')
    if browser == "edge":
        user_data_dir = os.path.join(local_app_data, 'Microsoft', 'Edge', 'User Data')
    else:
        user_data_dir = os.path.join(local_app_data, 'Google', 'Chrome', 'User Data')
    
    if not os.path.exists(user_data_dir):
        return {"success": False, "cookie": "", "message": f"未找到 {browser} 用户数据目录"}
    
    browser_process = None
    try:
        if on_log:
            on_log(f"  启动 {browser} 远程调试模式...")
        
        # 关闭现有浏览器
        subprocess.run(f'taskkill /F /IM {process_name}', shell=True,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await asyncio.sleep(1)
        
        # 启动调试模式浏览器
        browser_process = subprocess.Popen(
            [browser_path, f'--remote-debugging-port={DEBUG_PORT}',
             '--remote-allow-origins=*', '--headless=new', f'--user-data-dir={user_data_dir}'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        await asyncio.sleep(2)
        
        # 获取调试 URL
        try:
            res = requests.get(f'http://localhost:{DEBUG_PORT}/json', timeout=5)
            debug_info = res.json()
            if not debug_info:
                raise Exception("无调试目标")
            ws_url = debug_info[0].get('webSocketDebuggerUrl', '').strip()
        except Exception as e:
            return {"success": False, "cookie": "", "message": f"无法连接调试端口: {e}"}
        
        if not ws_url:
            return {"success": False, "cookie": "", "message": "无法获取 WebSocket URL"}
        
        if on_log:
            on_log("  连接调试接口...")
        
        # 获取 Cookie
        import websocket
        ws = websocket.create_connection(ws_url, timeout=10)
        ws.send(json.dumps({'id': 1, 'method': 'Network.getAllCookies'}))
        response = json.loads(ws.recv())
        ws.close()
        
        all_cookies = response.get('result', {}).get('cookies', [])
        
        # 筛选微博 Cookie
        weibo_cookies = {}
        for cookie in all_cookies:
            domain = cookie.get('domain', '')
            if 'weibo.cn' in domain or 'weibo.com' in domain:
                weibo_cookies[cookie['name']] = cookie['value']
        
        if not weibo_cookies:
            return {"success": False, "cookie": "", "message": "未找到微博 Cookie，请先登录 weibo.cn"}
        
        cookie_string = '; '.join(f'{k}={v}' for k, v in weibo_cookies.items())
        
        has_mlogin = weibo_cookies.get("MLOGIN", "0") == "1"
        has_sub = "SUB" in weibo_cookies
        is_valid = has_mlogin and has_sub
        
        if on_log:
            on_log(f"✅ 获取到 {len(weibo_cookies)} 个微博 Cookie")
        
        if not is_valid:
            return {"success": False, "cookie": cookie_string, 
                    "message": "Cookie 无效，请登录 weibo.cn 后重试"}
        
        return {"success": True, "cookie": cookie_string, "message": "Cookie 获取成功"}
        
    except ImportError as e:
        missing = str(e).split("'")[-2] if "'" in str(e) else str(e)
        return {"success": False, "cookie": "", 
                "message": f"缺少依赖: {missing}，请运行 pip install websocket-client"}
    except Exception as e:
        return {"success": False, "cookie": "", "message": f"远程调试获取失败: {e}"}
    finally:
        if browser_process:
            browser_process.terminate()
            try:
                browser_process.wait(timeout=3)
            except:
                browser_process.kill()


async def get_cookie_via_browser_cookie3(
    browser: str,
    on_log: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    通过 browser_cookie3 获取 Cookie（可能需要管理员权限）
    
    Returns:
        {"success": bool, "cookie": str, "message": str}
    """
    try:
        import browser_cookie3
        
        browsers_to_try = []
        if browser == "edge":
            browsers_to_try = [("edge", browser_cookie3.edge), ("chrome", browser_cookie3.chrome)]
        elif browser == "chrome":
            browsers_to_try = [("chrome", browser_cookie3.chrome), ("edge", browser_cookie3.edge)]
        elif browser == "firefox":
            browsers_to_try = [("firefox", browser_cookie3.firefox)]
        else:
            browsers_to_try = [("edge", browser_cookie3.edge), ("chrome", browser_cookie3.chrome)]
        
        cookies = None
        used_browser = None
        
        for browser_name, browser_func in browsers_to_try:
            try:
                if on_log:
                    on_log(f"  尝试 {browser_name}...")
                cookies = browser_func(domain_name='weibo.cn')
                used_browser = browser_name
                break
            except Exception as e:
                error_msg = str(e)
                if on_log:
                    if "admin" in error_msg.lower():
                        on_log(f"  {browser_name}: 需要管理员权限")
                    else:
                        on_log(f"  {browser_name}: {error_msg[:50]}")
                continue
        
        if cookies is None:
            if on_log:
                on_log("❌ 无法从浏览器获取 Cookie")
                on_log("💡 请手动复制 Cookie")
            return {"success": False, "cookie": "", "message": "无法获取 Cookie，请手动复制"}
        
        cookies_dict = {cookie.name: cookie.value for cookie in cookies}
        cookie_string = '; '.join(f'{name}={value}' for name, value in cookies_dict.items())
        
        if not cookie_string:
            return {"success": False, "cookie": "", "message": "未找到 Cookie，请先登录 weibo.cn"}
        
        has_mlogin = cookies_dict.get("MLOGIN", "0") == "1"
        has_sub = "SUB" in cookies_dict
        is_valid = has_mlogin and has_sub
        
        if on_log:
            on_log(f"✅ 从 {used_browser} 获取到 {len(cookies_dict)} 个 Cookie")
        
        if not is_valid:
            return {"success": False, "cookie": cookie_string,
                    "message": "Cookie 无效，请登录 weibo.cn 后重试"}
        
        return {"success": True, "cookie": cookie_string, "message": "Cookie 获取成功"}
        
    except ImportError:
        return {"success": False, "cookie": "", 
                "message": "缺少 browser_cookie3，请运行 pip install browser_cookie3"}
    except Exception as e:
        return {"success": False, "cookie": "", "message": f"获取 Cookie 失败: {e}"}
