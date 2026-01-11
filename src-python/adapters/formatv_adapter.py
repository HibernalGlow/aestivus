"""
formatv 适配器
视频格式过滤器 - 添加/移除 .nov 后缀，检查重复项

支持三种操作：
1. add_nov: 为普通视频文件添加 .nov 后缀
2. remove_nov: 移除 .nov 后缀恢复原始文件名
3. check_duplicates: 检查带前缀文件对应的无前缀重复文件
"""

import io
import os
import sys
from typing import Callable, Dict, List, Optional

from pydantic import Field

from .base import BaseAdapter, AdapterInput, AdapterOutput


def _ensure_utf8_output():
    """确保 stdout/stderr 使用 UTF-8 编码"""
    if sys.platform == 'win32':
        os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer, 
                encoding='utf-8', 
                errors='replace',
                line_buffering=True
            )
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer, 
                encoding='utf-8', 
                errors='replace',
                line_buffering=True
            )


_ensure_utf8_output()


class FormatVInput(AdapterInput):
    """formatv 输入参数"""
    path: str = Field(default="", description="扫描路径")
    paths: List[str] = Field(default_factory=list, description="扫描路径列表")
    action: str = Field(default="scan", description="操作类型: scan/add_nov/remove_nov/check_duplicates")
    recursive: bool = Field(default=False, description="是否递归扫描子目录")
    prefix_name: str = Field(default="hb", description="检查重复时使用的前缀名称")


class FormatVOutput(AdapterOutput):
    """formatv 输出结果"""
    # 扫描结果
    normal_count: int = Field(default=0, description="普通视频文件数量")
    nov_count: int = Field(default=0, description=".nov 文件数量")
    prefixed_counts: Dict[str, int] = Field(default_factory=dict, description="各前缀文件数量")
    # 文件列表（用于树形预览）
    normal_files: List[str] = Field(default_factory=list, description="普通视频文件列表")
    nov_files: List[str] = Field(default_factory=list, description=".nov 文件列表")
    prefixed_files: Dict[str, List[str]] = Field(default_factory=dict, description="各前缀文件列表")
    # 操作结果
    success_count: int = Field(default=0, description="成功处理数量")
    error_count: int = Field(default=0, description="失败数量")
    duplicate_count: int = Field(default=0, description="重复文件数量")
    duplicates: List[str] = Field(default_factory=list, description="重复文件路径列表")
    prefixed_larger: List[Dict] = Field(default_factory=list, description="前缀文件更大的列表")


class FormatVAdapter(BaseAdapter):
    """formatv 适配器 - 视频格式过滤器"""
    
    name = "formatv"
    display_name = "视频格式过滤"
    description = "添加/移除 .nov 后缀，检查重复项"
    category = "video"
    icon = "🎬"
    required_packages = ["formatv"]
    input_schema = FormatVInput
    output_schema = FormatVOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入 formatv 模块"""
        from formatv.scan import scan_directories, find_video_files
        from formatv.execute import (
            add_nov_extension_to_files,
            remove_nov_extension_from_files,
            check_and_save_duplicates
        )
        from formatv.config import get_prefix_list, get_default_path
        
        return {
            'scan_directories': scan_directories,
            'find_video_files': find_video_files,
            'add_nov_extension_to_files': add_nov_extension_to_files,
            'remove_nov_extension_from_files': remove_nov_extension_from_files,
            'check_and_save_duplicates': check_and_save_duplicates,
            'get_prefix_list': get_prefix_list,
            'get_default_path': get_default_path,
        }
    
    async def execute(
        self,
        input_data: FormatVInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> FormatVOutput:
        """执行 formatv 操作"""
        action = input_data.action.lower()
        
        if action == "scan":
            return await self._scan(input_data, on_progress, on_log)
        elif action == "add_nov":
            return await self._add_nov(input_data, on_progress, on_log)
        elif action == "remove_nov":
            return await self._remove_nov(input_data, on_progress, on_log)
        elif action == "check_duplicates":
            return await self._check_duplicates(input_data, on_progress, on_log)
        else:
            return FormatVOutput(success=False, message=f"未知操作: {action}")
    
    def _collect_paths(self, input_data: FormatVInput) -> List[str]:
        """收集并验证路径"""
        paths = list(input_data.paths) if input_data.paths else []
        if input_data.path:
            path = input_data.path.strip().strip('"')
            if path and path not in paths:
                paths.append(path)
        # 去除引号并验证存在
        from pathlib import Path
        valid_paths = []
        for p in paths:
            p = p.strip().strip('"')
            if Path(p).exists():
                valid_paths.append(p)
        return valid_paths
    
    async def _scan(
        self,
        input_data: FormatVInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> FormatVOutput:
        """扫描目录"""
        paths = self._collect_paths(input_data)
        if not paths:
            return FormatVOutput(success=False, message="未指定有效路径")
        
        try:
            module = self._import_module()
            find_video_files = module['find_video_files']
            get_prefix_list = module['get_prefix_list']
            
            if on_log:
                on_log(f"开始扫描 {len(paths)} 个目录...")
            if on_progress:
                on_progress(10, "正在扫描...")
            
            # 合并扫描结果
            total_normal = 0
            total_nov = 0
            prefixed_counts: Dict[str, int] = {}
            all_normal_files: List[str] = []
            all_nov_files: List[str] = []
            all_prefixed_files: Dict[str, List[str]] = {}
            
            # 初始化前缀计数
            prefixes = get_prefix_list()
            for p in prefixes:
                name = p.get("name", "")
                prefixed_counts[name] = 0
                all_prefixed_files[name] = []
            
            for i, path in enumerate(paths):
                if on_progress:
                    progress = 10 + int(80 * (i + 1) / len(paths))
                    on_progress(progress, f"扫描: {path}")
                
                result = find_video_files(path)
                normal_files = result.get("normal_files", [])
                nov_files = result.get("nov_files", [])
                
                total_normal += len(normal_files)
                total_nov += len(nov_files)
                all_normal_files.extend(normal_files)
                all_nov_files.extend(nov_files)
                
                for name, files in result.get("prefixed_files", {}).items():
                    prefixed_counts[name] = prefixed_counts.get(name, 0) + len(files)
                    if name not in all_prefixed_files:
                        all_prefixed_files[name] = []
                    all_prefixed_files[name].extend(files)
                
                if on_log:
                    on_log(f"✓ {path}: {len(normal_files)} 普通, {len(nov_files)} .nov")
            
            if on_progress:
                on_progress(100, "扫描完成")
            
            if on_log:
                on_log(f"✅ 扫描完成: {total_normal} 普通, {total_nov} .nov")
                for name, count in prefixed_counts.items():
                    if count > 0:
                        on_log(f"  [{name}]: {count} 个")
            
            # 转换前缀配置为可序列化格式
            prefix_configs = [
                {
                    'name': p.get('name', ''),
                    'prefix': p.get('prefix', ''),
                    'description': p.get('description', '')
                }
                for p in prefixes
            ]
            
            return FormatVOutput(
                success=True,
                message=f"扫描完成: {total_normal} 普通, {total_nov} .nov",
                normal_count=total_normal,
                nov_count=total_nov,
                prefixed_counts=prefixed_counts,
                normal_files=all_normal_files,
                nov_files=all_nov_files,
                prefixed_files=all_prefixed_files,
                data={
                    'normal_count': total_normal,
                    'nov_count': total_nov,
                    'prefixed_counts': prefixed_counts,
                    'normal_files': all_normal_files,
                    'nov_files': all_nov_files,
                    'prefixed_files': all_prefixed_files,
                    'paths': paths,
                    'prefixes': prefix_configs
                }
            )
            
        except ImportError as e:
            return FormatVOutput(success=False, message=f"formatv 模块未安装: {e}")
        except Exception as e:
            if on_log:
                on_log(f"❌ 扫描失败: {e}")
            return FormatVOutput(success=False, message=f"扫描失败: {type(e).__name__}: {e}")
    
    async def _add_nov(
        self,
        input_data: FormatVInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> FormatVOutput:
        """添加 .nov 后缀"""
        paths = self._collect_paths(input_data)
        if not paths:
            return FormatVOutput(success=False, message="未指定有效路径")
        
        try:
            module = self._import_module()
            find_video_files = module['find_video_files']
            add_nov_extension_to_files = module['add_nov_extension_to_files']
            
            if on_log:
                on_log("收集普通视频文件...")
            if on_progress:
                on_progress(10, "收集文件...")
            
            # 收集所有普通视频文件
            all_normal_files = []
            for path in paths:
                result = find_video_files(path)
                all_normal_files.extend(result.get("normal_files", []))
            
            if not all_normal_files:
                return FormatVOutput(
                    success=True,
                    message="没有找到需要添加 .nov 后缀的文件",
                    normal_count=0
                )
            
            if on_log:
                on_log(f"找到 {len(all_normal_files)} 个文件，开始添加 .nov...")
            if on_progress:
                on_progress(30, "添加 .nov...")
            
            success_count, errors = add_nov_extension_to_files(all_normal_files)
            
            if on_progress:
                on_progress(100, "完成")
            
            if on_log:
                on_log(f"✅ 成功: {success_count}, 失败: {len(errors)}")
            
            return FormatVOutput(
                success=True,
                message=f"添加 .nov 完成: {success_count} 成功, {len(errors)} 失败",
                success_count=success_count,
                error_count=len(errors),
                data={
                    'success_count': success_count,
                    'error_count': len(errors),
                    'errors': errors
                }
            )
            
        except ImportError as e:
            return FormatVOutput(success=False, message=f"formatv 模块未安装: {e}")
        except Exception as e:
            if on_log:
                on_log(f"❌ 操作失败: {e}")
            return FormatVOutput(success=False, message=f"操作失败: {type(e).__name__}: {e}")
    
    async def _remove_nov(
        self,
        input_data: FormatVInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> FormatVOutput:
        """移除 .nov 后缀"""
        paths = self._collect_paths(input_data)
        if not paths:
            return FormatVOutput(success=False, message="未指定有效路径")
        
        try:
            module = self._import_module()
            find_video_files = module['find_video_files']
            remove_nov_extension_from_files = module['remove_nov_extension_from_files']
            
            if on_log:
                on_log("收集 .nov 文件...")
            if on_progress:
                on_progress(10, "收集文件...")
            
            # 收集所有 .nov 文件
            all_nov_files = []
            for path in paths:
                result = find_video_files(path)
                all_nov_files.extend(result.get("nov_files", []))
            
            if not all_nov_files:
                return FormatVOutput(
                    success=True,
                    message="没有找到 .nov 文件",
                    nov_count=0
                )
            
            if on_log:
                on_log(f"找到 {len(all_nov_files)} 个 .nov 文件，开始移除...")
            if on_progress:
                on_progress(30, "移除 .nov...")
            
            success_count, errors = remove_nov_extension_from_files(all_nov_files)
            
            if on_progress:
                on_progress(100, "完成")
            
            if on_log:
                on_log(f"✅ 成功: {success_count}, 失败: {len(errors)}")
            
            return FormatVOutput(
                success=True,
                message=f"移除 .nov 完成: {success_count} 成功, {len(errors)} 失败",
                success_count=success_count,
                error_count=len(errors),
                data={
                    'success_count': success_count,
                    'error_count': len(errors),
                    'errors': errors
                }
            )
            
        except ImportError as e:
            return FormatVOutput(success=False, message=f"formatv 模块未安装: {e}")
        except Exception as e:
            if on_log:
                on_log(f"❌ 操作失败: {e}")
            return FormatVOutput(success=False, message=f"操作失败: {type(e).__name__}: {e}")
    
    async def _check_duplicates(
        self,
        input_data: FormatVInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> FormatVOutput:
        """检查重复项"""
        paths = self._collect_paths(input_data)
        if not paths:
            return FormatVOutput(success=False, message="未指定有效路径")
        
        try:
            module = self._import_module()
            find_video_files = module['find_video_files']
            check_and_save_duplicates = module['check_and_save_duplicates']
            get_prefix_list = module['get_prefix_list']
            
            prefix_name = input_data.prefix_name or "hb"
            
            if on_log:
                on_log(f"检查 [{prefix_name}] 前缀的重复项...")
            if on_progress:
                on_progress(10, "扫描文件...")
            
            # 合并扫描结果
            merged_results = {
                "nov_files": [],
                "normal_files": [],
                "prefixed_files": {}
            }
            
            # 初始化前缀
            prefixes = get_prefix_list()
            for p in prefixes:
                merged_results["prefixed_files"][p.get("name", "")] = []
            
            for path in paths:
                result = find_video_files(path)
                merged_results["nov_files"].extend(result.get("nov_files", []))
                merged_results["normal_files"].extend(result.get("normal_files", []))
                for name, files in result.get("prefixed_files", {}).items():
                    merged_results["prefixed_files"][name].extend(files)
            
            if on_progress:
                on_progress(50, "检查重复...")
            
            # 使用第一个路径作为输出目录
            output_dir = paths[0]
            dup_result = check_and_save_duplicates(output_dir, merged_results, prefix_name)
            
            if on_progress:
                on_progress(100, "完成")
            
            duplicates = dup_result.get("duplicates", [])
            prefixed_larger = dup_result.get("prefixed_larger", [])
            
            if on_log:
                on_log(f"✅ 发现 {len(duplicates)} 个重复文件")
                if prefixed_larger:
                    on_log(f"⚠️ {len(prefixed_larger)} 个前缀文件体积更大")
            
            # 转换 prefixed_larger 为可序列化格式
            larger_list = []
            for item in prefixed_larger:
                if isinstance(item, tuple) and len(item) >= 4:
                    larger_list.append({
                        'prefixed': str(item[0]),
                        'original': str(item[1]),
                        'prefixed_size': item[2],
                        'original_size': item[3]
                    })
            
            return FormatVOutput(
                success=True,
                message=f"检查完成: {len(duplicates)} 个重复文件",
                duplicate_count=len(duplicates),
                duplicates=duplicates,
                prefixed_larger=larger_list,
                data={
                    'duplicate_count': len(duplicates),
                    'duplicates': duplicates,
                    'prefixed_larger': larger_list,
                    'output_dir': output_dir
                }
            )
            
        except ImportError as e:
            return FormatVOutput(success=False, message=f"formatv 模块未安装: {e}")
        except Exception as e:
            if on_log:
                on_log(f"❌ 检查失败: {e}")
            return FormatVOutput(success=False, message=f"检查失败: {type(e).__name__}: {e}")
