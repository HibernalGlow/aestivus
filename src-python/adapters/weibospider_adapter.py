"""
weiboSpider 适配器
微博爬虫工具 - 爬取指定用户的微博数据、图片、视频
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

from pydantic import BaseModel, Field

from .base import BaseAdapter, AdapterOutput
from .weibospider_utils import (
    validate_cookie_online,
    get_cookie_via_remote_debug,
    get_cookie_via_browser_cookie3
)


class WeiboSpiderInput(BaseModel):
    """weiboSpider 输入参数"""
    action: str = Field(default="status", description="操作类型")
    user_ids: List[str] = Field(default_factory=list, description="用户ID列表")
    filter_original: bool = Field(default=True, description="只爬取原创")
    since_date: str = Field(default="", description="起始日期")
    end_date: str = Field(default="now", description="结束日期")
    pic_download: bool = Field(default=True, description="下载图片")
    video_download: bool = Field(default=True, description="下载视频")
    write_mode: List[str] = Field(default=["json"], description="输出格式")
    output_dir: str = Field(default="", description="输出目录")
    cookie: str = Field(default="", description="微博Cookie")
    browser: str = Field(default="edge", description="浏览器类型")
    random_wait_pages: List[int] = Field(default=[1, 5])
    random_wait_seconds: List[int] = Field(default=[6, 10])


class WeiboSpiderOutput(AdapterOutput):
    """weiboSpider 输出结果"""
    crawled_users: int = Field(default=0)
    crawled_weibos: int = Field(default=0)
    cookie_valid: bool = Field(default=False)
    config_data: Dict[str, Any] = Field(default_factory=dict)


class WeiboSpiderAdapter(BaseAdapter):
    """weiboSpider 适配器"""
    
    name = "weibospider"
    display_name = "微博爬虫"
    description = "爬取微博用户数据，支持下载图片和视频"
    category = "crawler"
    icon = "🕷️"
    required_packages = []
    input_schema = WeiboSpiderInput
    output_schema = WeiboSpiderOutput
    
    _spider_module = None
    _weibo_spider_path = None
    
    def _import_module(self) -> Dict:
        """导入 weiboSpider 模块"""
        if WeiboSpiderAdapter._spider_module is not None:
            return {"spider": WeiboSpiderAdapter._spider_module, 
                    "path": WeiboSpiderAdapter._weibo_spider_path}
        
        weibo_spider_src = Path(__file__).parent.parent.parent.parent / "ImageAll" / "weiboSpider"
        if str(weibo_spider_src) not in sys.path:
            sys.path.insert(0, str(weibo_spider_src))
        
        WeiboSpiderAdapter._weibo_spider_path = weibo_spider_src
        
        try:
            from absl import flags
            try:
                flags.FLAGS.mark_as_parsed()
            except:
                pass
            from weibo_spider import spider
            WeiboSpiderAdapter._spider_module = spider
            return {"spider": spider, "path": weibo_spider_src}
        except Exception as e:
            return {"path": weibo_spider_src, "error": str(e)}
    
    async def execute(
        self,
        input_data: WeiboSpiderInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> WeiboSpiderOutput:
        """执行操作"""
        action = input_data.action
        modules = self._import_module()
        
        actions = {
            "status": self._get_status,
            "load_config": self._load_config,
            "save_config": lambda m, l: self._save_config(input_data, m, l),
            "validate_cookie": lambda m, l: self._validate_cookie(input_data, m, l),
            "get_browser_cookie": lambda m, l: self._get_browser_cookie(input_data, m, l),
            "crawl": lambda m, l: self._crawl(input_data, m, on_progress, l),
        }
        
        handler = actions.get(action)
        if handler:
            if action in ["status", "load_config"]:
                return await handler(modules, on_log)
            return await handler(modules, on_log)
        return WeiboSpiderOutput(success=False, message=f"未知操作: {action}")
    
    async def _get_status(self, modules: Dict, on_log) -> WeiboSpiderOutput:
        """获取状态"""
        weibo_path = modules.get("path")
        config_file = weibo_path / "config.json" if weibo_path else None
        return WeiboSpiderOutput(
            success=True, message="状态获取成功",
            data={"path": str(weibo_path), "has_config": config_file and config_file.exists()}
        )
    
    async def _load_config(self, modules: Dict, on_log) -> WeiboSpiderOutput:
        """加载配置"""
        weibo_path = modules.get("path")
        config_file = weibo_path / "config.json" if weibo_path else None
        
        if not config_file or not config_file.exists():
            return WeiboSpiderOutput(success=False, message="配置文件不存在")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            if on_log:
                on_log("✅ 配置加载成功")
            return WeiboSpiderOutput(success=True, message="配置加载成功", 
                                     config_data=config, data=config)
        except Exception as e:
            return WeiboSpiderOutput(success=False, message=f"加载失败: {e}")
    
    async def _save_config(self, input_data, modules: Dict, on_log) -> WeiboSpiderOutput:
        """保存配置"""
        weibo_path = modules.get("path")
        config_file = weibo_path / "config.json" if weibo_path else None
        
        if not config_file:
            return WeiboSpiderOutput(success=False, message="无法确定配置路径")
        
        try:
            existing = {}
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            
            config = {
                **existing,
                "user_id_list": input_data.user_ids or existing.get("user_id_list", []),
                "filter": 1 if input_data.filter_original else 0,
                "since_date": input_data.since_date or existing.get("since_date", "2018-01-01"),
                "end_date": input_data.end_date or "now",
                "pic_download": 1 if input_data.pic_download else 0,
                "video_download": 1 if input_data.video_download else 0,
                "write_mode": input_data.write_mode or ["json"],
            }
            if input_data.cookie:
                config["cookie"] = input_data.cookie
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            if on_log:
                on_log("✅ 配置保存成功")
            return WeiboSpiderOutput(success=True, message="配置保存成功", config_data=config)
        except Exception as e:
            return WeiboSpiderOutput(success=False, message=f"保存失败: {e}")
    
    async def _validate_cookie(self, input_data, modules: Dict, on_log) -> WeiboSpiderOutput:
        """验证 Cookie"""
        cookie = input_data.cookie
        
        if not cookie:
            weibo_path = modules.get("path")
            config_file = weibo_path / "config.json" if weibo_path else None
            if config_file and config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    cookie = json.load(f).get("cookie", "")
        
        if not cookie:
            return WeiboSpiderOutput(success=False, message="未提供 Cookie", cookie_valid=False)
        
        result = await validate_cookie_online(cookie, on_log)
        return WeiboSpiderOutput(
            success=True, message=result["message"], cookie_valid=result["valid"]
        )
    
    async def _get_browser_cookie(self, input_data, modules: Dict, on_log) -> WeiboSpiderOutput:
        """从浏览器获取 Cookie"""
        browser = input_data.browser.lower()
        
        if on_log:
            on_log(f"🔍 从 {browser} 浏览器获取 Cookie...")
        
        # 优先远程调试方式
        result = await get_cookie_via_remote_debug(browser, on_log)
        if not result["success"]:
            if on_log:
                on_log("⚠️ 远程调试失败，尝试直接读取...")
            result = await get_cookie_via_browser_cookie3(browser, on_log)
        
        if result["success"] and result["cookie"]:
            # 保存到配置
            weibo_path = modules.get("path")
            config_file = weibo_path / "config.json" if weibo_path else None
            if config_file and config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                config["cookie"] = result["cookie"]
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                if on_log:
                    on_log("✅ Cookie 已保存到配置文件")
        
        return WeiboSpiderOutput(
            success=result["success"],
            message=result["message"],
            cookie_valid=result["success"],
            data={"cookie": result.get("cookie", "")}
        )
    
    async def _crawl(self, input_data, modules: Dict, on_progress, on_log) -> WeiboSpiderOutput:
        """执行爬取"""
        if "error" in modules:
            return WeiboSpiderOutput(success=False, message=f"模块加载失败: {modules['error']}")
        
        spider_module = modules.get("spider")
        if not spider_module:
            return WeiboSpiderOutput(success=False, message="Spider 模块未加载")
        
        weibo_path = modules.get("path")
        await self._save_config(input_data, modules, on_log)
        
        config_file = weibo_path / "config.json"
        if not config_file.exists():
            return WeiboSpiderOutput(success=False, message="配置文件不存在")
        
        if on_log:
            on_log("🕷️ 开始爬取微博...")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if input_data.output_dir:
                os.environ['OUTPUT_DIR'] = input_data.output_dir
            
            wb = spider_module.Spider(config)
            total_users = len(wb.user_config_list)
            crawled_users = 0
            total_weibos = 0
            
            if on_log:
                on_log(f"📋 待爬取用户数: {total_users}")
            
            for user_config in wb.user_config_list:
                crawled_users += 1
                user_uri = user_config['user_uri']
                
                if on_progress:
                    progress = 10 + int(crawled_users / max(total_users, 1) * 80)
                    on_progress(progress, f"爬取 {user_uri} ({crawled_users}/{total_users})")
                
                if on_log:
                    on_log(f"👤 爬取用户: {user_uri}")
                
                try:
                    wb.get_user_info(user_uri)
                    if not wb.user or not getattr(wb.user, 'id', None):
                        if on_log:
                            on_log(f"⚠️ 无法获取用户信息，Cookie 可能已过期")
                        continue
                    
                    wb.initialize_info(user_config)
                    wb.write_user(wb.user)
                    
                    for weibos in wb.get_weibo_info():
                        wb.write_weibo(weibos)
                        wb.got_num += len(weibos)
                        total_weibos += len(weibos)
                        await asyncio.sleep(0.01)
                    
                    if on_log:
                        on_log(f"✅ 用户 {getattr(wb.user, 'nickname', user_uri)} 完成")
                        
                except Exception as e:
                    if on_log:
                        on_log(f"❌ 用户 {user_uri} 失败: {e}")
                    continue
            
            if on_progress:
                on_progress(100, "爬取完成")
            
            return WeiboSpiderOutput(
                success=True,
                message=f"完成，共 {crawled_users} 用户，{total_weibos} 微博",
                crawled_users=crawled_users,
                crawled_weibos=total_weibos
            )
            
        except Exception as e:
            return WeiboSpiderOutput(success=False, message=f"爬取失败: {e}")
