"""
weiboSpider 适配器
微博爬虫工具 - 爬取指定用户的微博数据、图片、视频

直接调用 weiboSpider 源码的核心函数
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any
from datetime import datetime, date, timedelta

from pydantic import BaseModel, Field

from .base import BaseAdapter, AdapterOutput


class WeiboSpiderInput(BaseModel):
    """weiboSpider 输入参数"""
    action: str = Field(default="status", description="操作类型: status, crawl, validate_cookie, load_config, save_config, get_browser_cookie")
    
    # 用户配置
    user_ids: List[str] = Field(default_factory=list, description="要爬取的用户ID列表")
    
    # 爬取配置
    filter_original: bool = Field(default=True, description="只爬取原创微博")
    since_date: str = Field(default="", description="起始日期 (YYYY-MM-DD)")
    end_date: str = Field(default="now", description="结束日期 (YYYY-MM-DD 或 now)")
    
    # 下载配置
    pic_download: bool = Field(default=True, description="下载图片")
    video_download: bool = Field(default=True, description="下载视频")
    
    # 输出配置
    write_mode: List[str] = Field(default=["json"], description="输出格式: txt, csv, json")
    output_dir: str = Field(default="", description="输出目录")
    
    # Cookie
    cookie: str = Field(default="", description="微博Cookie")
    browser: str = Field(default="edge", description="浏览器类型: chrome, edge, firefox")
    
    # 等待配置
    random_wait_pages: List[int] = Field(default=[1, 5], description="随机等待页数范围")
    random_wait_seconds: List[int] = Field(default=[6, 10], description="随机等待秒数范围")


class WeiboSpiderOutput(AdapterOutput):
    """weiboSpider 输出结果"""
    crawled_users: int = Field(default=0, description="已爬取用户数")
    crawled_weibos: int = Field(default=0, description="已爬取微博数")
    downloaded_pics: int = Field(default=0, description="已下载图片数")
    downloaded_videos: int = Field(default=0, description="已下载视频数")
    current_user: str = Field(default="", description="当前爬取用户")
    current_progress: int = Field(default=0, description="当前进度")
    cookie_valid: bool = Field(default=False, description="Cookie是否有效")
    config_data: Dict[str, Any] = Field(default_factory=dict, description="配置数据")


class WeiboSpiderAdapter(BaseAdapter):
    """
    weiboSpider 适配器 - 直接调用源码函数
    
    功能：微博爬虫，爬取指定用户的微博数据、图片、视频
    """
    
    name = "weibospider"
    display_name = "微博爬虫"
    description = "爬取微博用户数据，支持下载图片和视频"
    category = "crawler"
    icon = "🕷️"
    required_packages = []
    input_schema = WeiboSpiderInput
    output_schema = WeiboSpiderOutput
    
    _spider_module = None
    _config_util_module = None
    _weibo_spider_path = None
    
    def _import_module(self) -> Dict:
        """导入 weiboSpider 源码模块"""
        if WeiboSpiderAdapter._spider_module is not None:
            return {
                "spider": WeiboSpiderAdapter._spider_module,
                "config_util": WeiboSpiderAdapter._config_util_module,
                "path": WeiboSpiderAdapter._weibo_spider_path
            }
        
        # 添加源码路径
        weibo_spider_src = Path(__file__).parent.parent.parent.parent / "ImageAll" / "weiboSpider"
        if str(weibo_spider_src) not in sys.path:
            sys.path.insert(0, str(weibo_spider_src))
        
        WeiboSpiderAdapter._weibo_spider_path = weibo_spider_src
        
        try:
            # 先初始化 absl flags，避免 "flags not parsed" 错误
            from absl import flags
            try:
                flags.FLAGS.mark_as_parsed()
            except:
                # 如果已经解析过，忽略错误
                pass
            
            from weibo_spider import spider, config_util
            WeiboSpiderAdapter._spider_module = spider
            WeiboSpiderAdapter._config_util_module = config_util
            return {
                "spider": spider,
                "config_util": config_util,
                "path": weibo_spider_src
            }
        except Exception as e:
            # 模块导入失败时返回路径信息
            return {"path": weibo_spider_src, "error": str(e)}
    
    async def execute(
        self,
        input_data: WeiboSpiderInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> WeiboSpiderOutput:
        """执行 weiboSpider 操作"""
        action = input_data.action
        
        modules = self._import_module()
        
        if action == "status":
            return await self._get_status(modules, on_log)
        elif action == "load_config":
            return await self._load_config(modules, on_log)
        elif action == "save_config":
            return await self._save_config(input_data, modules, on_log)
        elif action == "validate_cookie":
            return await self._validate_cookie(input_data, modules, on_log)
        elif action == "get_browser_cookie":
            return await self._get_browser_cookie(input_data, modules, on_log)
        elif action == "crawl":
            return await self._crawl(input_data, modules, on_progress, on_log)
        else:
            return WeiboSpiderOutput(success=False, message=f"未知操作: {action}")
    
    async def _get_status(
        self,
        modules: Dict,
        on_log: Optional[Callable[[str], None]] = None
    ) -> WeiboSpiderOutput:
        """获取状态"""
        weibo_path = modules.get("path")
        config_file = weibo_path / "config.json" if weibo_path else None
        
        has_config = config_file and config_file.exists()
        has_module = "spider" in modules
        
        if on_log:
            on_log(f"📂 weiboSpider 路径: {weibo_path}")
            on_log(f"📄 配置文件: {'存在' if has_config else '不存在'}")
            on_log(f"📦 模块状态: {'已加载' if has_module else '未加载'}")
        
        return WeiboSpiderOutput(
            success=True,
            message="状态获取成功",
            data={
                "path": str(weibo_path),
                "has_config": has_config,
                "has_module": has_module
            }
        )
    
    async def _load_config(
        self,
        modules: Dict,
        on_log: Optional[Callable[[str], None]] = None
    ) -> WeiboSpiderOutput:
        """加载配置文件"""
        weibo_path = modules.get("path")
        config_file = weibo_path / "config.json" if weibo_path else None
        
        if not config_file or not config_file.exists():
            return WeiboSpiderOutput(
                success=False,
                message="配置文件不存在"
            )
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if on_log:
                on_log(f"✅ 配置加载成功")
                on_log(f"👤 用户列表: {config.get('user_id_list', [])}")
            
            return WeiboSpiderOutput(
                success=True,
                message="配置加载成功",
                config_data=config,
                data=config
            )
        except Exception as e:
            return WeiboSpiderOutput(
                success=False,
                message=f"配置加载失败: {e}"
            )
    
    async def _save_config(
        self,
        input_data: WeiboSpiderInput,
        modules: Dict,
        on_log: Optional[Callable[[str], None]] = None
    ) -> WeiboSpiderOutput:
        """保存配置文件"""
        weibo_path = modules.get("path")
        config_file = weibo_path / "config.json" if weibo_path else None
        
        if not config_file:
            return WeiboSpiderOutput(success=False, message="无法确定配置文件路径")
        
        try:
            # 读取现有配置
            existing_config = {}
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    existing_config = json.load(f)
            
            # 更新配置
            config = {
                **existing_config,
                "user_id_list": input_data.user_ids if input_data.user_ids else existing_config.get("user_id_list", []),
                "filter": 1 if input_data.filter_original else 0,
                "since_date": input_data.since_date or existing_config.get("since_date", "2018-01-01"),
                "end_date": input_data.end_date or "now",
                "pic_download": 1 if input_data.pic_download else 0,
                "video_download": 1 if input_data.video_download else 0,
                "write_mode": input_data.write_mode or ["json"],
                "random_wait_pages": input_data.random_wait_pages,
                "random_wait_seconds": input_data.random_wait_seconds,
            }
            
            if input_data.cookie:
                config["cookie"] = input_data.cookie
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            if on_log:
                on_log(f"✅ 配置保存成功")
            
            return WeiboSpiderOutput(
                success=True,
                message="配置保存成功",
                config_data=config
            )
        except Exception as e:
            return WeiboSpiderOutput(
                success=False,
                message=f"配置保存失败: {e}"
            )
    
    async def _validate_cookie(
        self,
        input_data: WeiboSpiderInput,
        modules: Dict,
        on_log: Optional[Callable[[str], None]] = None
    ) -> WeiboSpiderOutput:
        """验证 Cookie"""
        cookie = input_data.cookie
        
        if not cookie:
            # 尝试从配置文件读取
            weibo_path = modules.get("path")
            config_file = weibo_path / "config.json" if weibo_path else None
            if config_file and config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    cookie = config.get("cookie", "")
        
        if not cookie:
            return WeiboSpiderOutput(
                success=False,
                message="未提供 Cookie",
                cookie_valid=False
            )
        
        # 检查 Cookie 中的关键字段
        has_mlogin = "MLOGIN=1" in cookie
        has_sub = "SUB=" in cookie
        
        if on_log:
            on_log(f"🔍 检查 Cookie...")
            on_log(f"  MLOGIN: {'✅' if has_mlogin else '❌'}")
            on_log(f"  SUB: {'✅' if has_sub else '❌'}")
        
        is_valid = has_mlogin and has_sub
        
        return WeiboSpiderOutput(
            success=True,
            message="Cookie 有效" if is_valid else "Cookie 无效或已过期",
            cookie_valid=is_valid
        )
    
    async def _get_browser_cookie(
        self,
        input_data: WeiboSpiderInput,
        modules: Dict,
        on_log: Optional[Callable[[str], None]] = None
    ) -> WeiboSpiderOutput:
        """从浏览器获取 Cookie - 使用远程调试方式绕过权限限制"""
        browser = input_data.browser.lower()
        
        if on_log:
            on_log(f"🔍 从 {browser} 浏览器获取 Cookie...")
        
        # 优先使用远程调试方式（无需管理员权限）
        result = await self._get_cookie_via_remote_debug(browser, modules, on_log)
        if result.success:
            return result
        
        # 回退到 browser_cookie3（可能需要管理员权限）
        if on_log:
            on_log("⚠️ 远程调试方式失败，尝试直接读取...")
        
        return await self._get_cookie_via_browser_cookie3(browser, modules, on_log)
    
    async def _get_cookie_via_remote_debug(
        self,
        browser: str,
        modules: Dict,
        on_log: Optional[Callable[[str], None]] = None
    ) -> WeiboSpiderOutput:
        """通过浏览器远程调试获取 Cookie（无需管理员权限）"""
        import subprocess
        import time
        
        DEBUG_PORT = 9222
        
        # 确定浏览器路径
        if browser == "edge":
            browser_paths = [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            ]
            process_name = "msedge.exe"
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
            return WeiboSpiderOutput(
                success=False,
                message=f"未找到 {browser} 浏览器",
                cookie_valid=False
            )
        
        # 获取用户数据目录
        local_app_data = os.getenv('LOCALAPPDATA', '')
        if browser == "edge":
            user_data_dir = os.path.join(local_app_data, 'Microsoft', 'Edge', 'User Data')
        else:
            user_data_dir = os.path.join(local_app_data, 'Google', 'Chrome', 'User Data')
        
        if not os.path.exists(user_data_dir):
            return WeiboSpiderOutput(
                success=False,
                message=f"未找到 {browser} 用户数据目录",
                cookie_valid=False
            )
        
        browser_process = None
        try:
            if on_log:
                on_log(f"  启动 {browser} 远程调试模式...")
            
            # 先关闭现有浏览器进程
            subprocess.run(
                f'taskkill /F /IM {process_name}',
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            await asyncio.sleep(1)
            
            # 启动带调试端口的浏览器（headless 模式）
            browser_process = subprocess.Popen(
                [
                    browser_path,
                    f'--remote-debugging-port={DEBUG_PORT}',
                    '--remote-allow-origins=*',
                    '--headless=new',
                    f'--user-data-dir={user_data_dir}'
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # 等待浏览器启动
            await asyncio.sleep(2)
            
            # 获取调试 WebSocket URL
            import requests
            try:
                res = requests.get(f'http://localhost:{DEBUG_PORT}/json', timeout=5)
                debug_info = res.json()
                if not debug_info:
                    raise Exception("无调试目标")
                ws_url = debug_info[0].get('webSocketDebuggerUrl', '').strip()
            except Exception as e:
                return WeiboSpiderOutput(
                    success=False,
                    message=f"无法连接调试端口: {e}",
                    cookie_valid=False
                )
            
            if not ws_url:
                return WeiboSpiderOutput(
                    success=False,
                    message="无法获取 WebSocket 调试 URL",
                    cookie_valid=False
                )
            
            if on_log:
                on_log("  连接调试接口...")
            
            # 通过 WebSocket 获取所有 Cookie
            import websocket
            ws = websocket.create_connection(ws_url, timeout=10)
            ws.send(json.dumps({'id': 1, 'method': 'Network.getAllCookies'}))
            response = json.loads(ws.recv())
            ws.close()
            
            all_cookies = response.get('result', {}).get('cookies', [])
            
            # 筛选 weibo.cn 的 Cookie
            weibo_cookies = {}
            for cookie in all_cookies:
                domain = cookie.get('domain', '')
                if 'weibo.cn' in domain or 'weibo.com' in domain:
                    weibo_cookies[cookie['name']] = cookie['value']
            
            if not weibo_cookies:
                if on_log:
                    on_log("❌ 未找到微博 Cookie，请先在浏览器登录 weibo.cn")
                return WeiboSpiderOutput(
                    success=False,
                    message="未找到微博 Cookie，请先登录 weibo.cn",
                    cookie_valid=False
                )
            
            # 转换为字符串格式
            cookie_string = '; '.join(f'{k}={v}' for k, v in weibo_cookies.items())
            
            # 检查是否已登录
            has_mlogin = weibo_cookies.get("MLOGIN", "0") == "1"
            has_sub = "SUB" in weibo_cookies
            is_valid = has_mlogin and has_sub
            
            if on_log:
                on_log(f"✅ 获取到 {len(weibo_cookies)} 个微博 Cookie")
                on_log(f"  MLOGIN: {'✅ 已登录' if has_mlogin else '❌ 未登录'}")
            
            if not is_valid:
                return WeiboSpiderOutput(
                    success=False,
                    message="Cookie 无效，请在浏览器登录 weibo.cn 后重试",
                    cookie_valid=False,
                    data={"cookie": cookie_string}
                )
            
            # 保存到配置文件
            weibo_path = modules.get("path")
            config_file = weibo_path / "config.json" if weibo_path else None
            if config_file and config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                config["cookie"] = cookie_string
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                if on_log:
                    on_log("✅ Cookie 已保存到配置文件")
            
            return WeiboSpiderOutput(
                success=True,
                message="Cookie 获取成功",
                cookie_valid=True,
                data={"cookie": cookie_string}
            )
            
        except ImportError as e:
            missing = str(e).split("'")[-2] if "'" in str(e) else str(e)
            return WeiboSpiderOutput(
                success=False,
                message=f"缺少依赖: {missing}，请运行 pip install websocket-client requests",
                cookie_valid=False
            )
        except Exception as e:
            return WeiboSpiderOutput(
                success=False,
                message=f"远程调试获取失败: {e}",
                cookie_valid=False
            )
        finally:
            # 关闭调试浏览器进程
            if browser_process:
                browser_process.terminate()
                try:
                    browser_process.wait(timeout=3)
                except:
                    browser_process.kill()
    
    async def _get_cookie_via_browser_cookie3(
        self,
        browser: str,
        modules: Dict,
        on_log: Optional[Callable[[str], None]] = None
    ) -> WeiboSpiderOutput:
        """通过 browser_cookie3 获取 Cookie（可能需要管理员权限）"""
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
                    on_log("💡 请手动复制 Cookie：")
                    on_log("   1. 打开 Edge 访问 weibo.cn 并登录")
                    on_log("   2. 按 F12 打开开发者工具")
                    on_log("   3. 切换到 Network 标签，刷新页面")
                    on_log("   4. 点击任意请求，复制 Cookie 头的值")
                return WeiboSpiderOutput(
                    success=False,
                    message="无法获取 Cookie，请手动复制",
                    cookie_valid=False
                )
            
            cookies_dict = {cookie.name: cookie.value for cookie in cookies}
            cookie_string = '; '.join(f'{name}={value}' for name, value in cookies_dict.items())
            
            if not cookie_string:
                return WeiboSpiderOutput(
                    success=False,
                    message="未找到 Cookie，请先登录 weibo.cn",
                    cookie_valid=False
                )
            
            has_mlogin = cookies_dict.get("MLOGIN", "0") == "1"
            has_sub = "SUB" in cookies_dict
            is_valid = has_mlogin and has_sub
            
            if on_log:
                on_log(f"✅ 从 {used_browser} 获取到 {len(cookies_dict)} 个 Cookie")
            
            if not is_valid:
                return WeiboSpiderOutput(
                    success=False,
                    message="Cookie 无效，请登录 weibo.cn 后重试",
                    cookie_valid=False,
                    data={"cookie": cookie_string}
                )
            
            # 保存到配置文件
            weibo_path = modules.get("path")
            config_file = weibo_path / "config.json" if weibo_path else None
            if config_file and config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                config["cookie"] = cookie_string
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                if on_log:
                    on_log("✅ Cookie 已保存到配置文件")
            
            return WeiboSpiderOutput(
                success=True,
                message="Cookie 获取成功",
                cookie_valid=True,
                data={"cookie": cookie_string}
            )
            
        except ImportError:
            return WeiboSpiderOutput(
                success=False,
                message="缺少 browser_cookie3，请运行 pip install browser_cookie3",
                cookie_valid=False
            )
        except Exception as e:
            return WeiboSpiderOutput(
                success=False,
                message=f"获取 Cookie 失败: {e}",
                cookie_valid=False
            )
    
    async def _crawl(
        self,
        input_data: WeiboSpiderInput,
        modules: Dict,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> WeiboSpiderOutput:
        """执行爬取"""
        weibo_path = modules.get("path")
        
        if "error" in modules:
            return WeiboSpiderOutput(
                success=False,
                message=f"模块加载失败: {modules['error']}"
            )
        
        spider_module = modules.get("spider")
        if not spider_module:
            return WeiboSpiderOutput(
                success=False,
                message="Spider 模块未加载"
            )
        
        # 先保存配置
        await self._save_config(input_data, modules, on_log)
        
        config_file = weibo_path / "config.json"
        if not config_file.exists():
            return WeiboSpiderOutput(
                success=False,
                message="配置文件不存在"
            )
        
        if on_log:
            on_log("🕷️ 开始爬取微博...")
        
        if on_progress:
            on_progress(5, "初始化爬虫...")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 设置输出目录
            if input_data.output_dir:
                os.environ['OUTPUT_DIR'] = input_data.output_dir
            
            # 创建爬虫实例
            wb = spider_module.Spider(config)
            
            total_users = len(wb.user_config_list)
            crawled_users = 0
            total_weibos = 0
            
            if on_log:
                on_log(f"📋 待爬取用户数: {total_users}")
            
            if on_progress:
                on_progress(10, f"准备爬取 {total_users} 个用户...")
            
            for user_config in wb.user_config_list:
                crawled_users += 1
                user_uri = user_config['user_uri']
                
                base_progress = 10 + int((crawled_users - 1) / max(total_users, 1) * 80)
                
                if on_progress:
                    on_progress(base_progress, f"爬取用户 {user_uri} ({crawled_users}/{total_users})")
                
                if on_log:
                    on_log(f"👤 开始爬取用户: {user_uri}")
                
                try:
                    # 获取用户信息
                    wb.get_user_info(user_config['user_uri'])
                    
                    # 检查是否成功获取用户信息
                    if not wb.user or not hasattr(wb.user, 'id') or not wb.user.id:
                        if on_log:
                            on_log(f"⚠️ 无法获取用户 {user_uri} 信息，可能 Cookie 已过期")
                        continue
                    
                    wb.initialize_info(user_config)
                    wb.write_user(wb.user)
                    
                    nickname = getattr(wb.user, 'nickname', user_uri)
                    weibo_num = getattr(wb.user, 'weibo_num', '未知')
                    
                    if on_log:
                        on_log(f"  昵称: {nickname}")
                        on_log(f"  微博数: {weibo_num}")
                    
                    if on_progress:
                        on_progress(base_progress + 5, f"获取 {nickname} 的微博...")
                    
                    # 爬取微博
                    page_count = 0
                    for weibos in wb.get_weibo_info():
                        wb.write_weibo(weibos)
                        wb.got_num += len(weibos)
                        total_weibos += len(weibos)
                        page_count += 1
                        
                        if on_log and page_count % 5 == 0:
                            on_log(f"  已获取 {wb.got_num} 条微博...")
                        
                        # 更新进度
                        if on_progress:
                            sub_progress = min(base_progress + 40, 90)
                            on_progress(sub_progress, f"{nickname}: {wb.got_num} 条微博")
                        
                        # 让出控制权，避免阻塞
                        await asyncio.sleep(0.01)
                    
                    if on_log:
                        on_log(f"✅ 用户 {nickname} 爬取完成，共 {wb.got_num} 条")
                    
                except Exception as e:
                    error_msg = str(e)
                    # 检查是否是 Cookie 相关错误
                    if 'cookie' in error_msg.lower() or '过期' in error_msg or '登录' in error_msg:
                        if on_log:
                            on_log(f"⚠️ Cookie 可能已过期，请重新获取")
                        return WeiboSpiderOutput(
                            success=False,
                            message="Cookie 已过期，请重新获取并更新",
                            crawled_users=crawled_users,
                            crawled_weibos=total_weibos
                        )
                    if on_log:
                        on_log(f"❌ 用户 {user_uri} 爬取失败: {error_msg}")
                    # 继续爬取下一个用户
                    continue
            
            if on_progress:
                on_progress(100, "爬取完成")
            
            if on_log:
                on_log(f"🎉 全部完成！共 {crawled_users} 个用户，{total_weibos} 条微博")
            
            return WeiboSpiderOutput(
                success=True,
                message=f"爬取完成，共 {crawled_users} 个用户，{total_weibos} 条微博",
                crawled_users=crawled_users,
                crawled_weibos=total_weibos
            )
            
        except Exception as e:
            error_msg = str(e)
            if on_log:
                on_log(f"❌ 爬取失败: {error_msg}")
            return WeiboSpiderOutput(
                success=False,
                message=f"爬取失败: {error_msg}"
            )
