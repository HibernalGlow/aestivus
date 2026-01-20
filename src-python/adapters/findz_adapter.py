"""
findz 适配器
文件搜索工具 - 使用 SQL-like WHERE 语法搜索文件（包括压缩包内部）

支持功能：
1. search: 使用 WHERE 语法搜索文件
2. nested: 查找包含嵌套压缩包的外层压缩包
3. archives_only: 只搜索压缩包本身
"""

import io
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

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


class FindzInput(AdapterInput):
    """findz 输入参数"""
    path: str = Field(default="", description="搜索路径")
    paths: List[str] = Field(default_factory=list, description="搜索路径列表")
    where: str = Field(default="1", description="WHERE 过滤表达式 (SQL 或 JSON)")
    filter_config: Optional[Dict] = Field(default=None, description="JSON 格式的过滤器配置")
    filter_mode: str = Field(default="auto", description="过滤器模式: auto/sql/json")
    action: str = Field(default="search", description="操作类型: search/nested/archives_only/interactive")
    long_format: bool = Field(default=True, description="显示详细信息（日期、大小）")
    follow_symlinks: bool = Field(default=False, description="跟随符号链接")
    no_archive: bool = Field(default=False, description="禁用压缩包搜索")
    max_results: int = Field(default=0, description="最大结果数量，0表示无限制")
    max_return_files: int = Field(default=5000, description="最大返回文件数（用于前端显示），0表示全部返回")
    continue_on_error: bool = Field(default=True, description="遇到错误继续搜索")
    with_image_meta: bool = Field(default=False, description="启用图片元数据读取（width, height, resolution 等）")


class FindzOutput(AdapterOutput):
    """findz 输出结果"""
    # 搜索结果
    total_count: int = Field(default=0, description="总文件数")
    file_count: int = Field(default=0, description="普通文件数")
    dir_count: int = Field(default=0, description="目录数")
    archive_count: int = Field(default=0, description="压缩包数")
    nested_count: int = Field(default=0, description="嵌套压缩包数")
    # 文件列表
    files: List[Dict[str, Any]] = Field(default_factory=list, description="文件列表")
    # 按类型分组
    by_extension: Dict[str, int] = Field(default_factory=dict, description="按扩展名统计")
    by_archive: Dict[str, int] = Field(default_factory=dict, description="按压缩包统计")
    # 错误信息
    errors: List[str] = Field(default_factory=list, description="错误列表")


class FindzAdapter(BaseAdapter):
    """findz 适配器 - 文件搜索工具"""
    
    name = "findz"
    display_name = "文件搜索"
    description = "使用 SQL-like WHERE 语法或可视化配置搜索文件（支持压缩包内部）"
    category = "file"
    icon = "🔍"
    required_packages = ["findz"]
    input_schema = FindzInput
    output_schema = FindzOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入 findz 模块"""
        from findz.filter.filter import create_filter
        from findz.filter.size import format_size
        from findz.find.find import FileInfo, FIELDS, IMAGE_FIELDS
        from findz.find.walk import WalkParams, walk, is_archive
        from findz.find.index_cache import get_global_cache
        
        # 尝试导入统一过滤器（可能不存在）
        try:
            from findz.filter.unified import create_unified_filter
        except ImportError:
            create_unified_filter = None
        
        return {
            'create_filter': create_filter,
            'create_unified_filter': create_unified_filter,
            'format_size': format_size,
            'FileInfo': FileInfo,
            'FIELDS': FIELDS,
            'IMAGE_FIELDS': IMAGE_FIELDS,
            'WalkParams': WalkParams,
            'walk': walk,
            'is_archive': is_archive,
            'get_global_cache': get_global_cache,
        }
    
    def _create_filter(self, input_data: FindzInput, module: Dict):
        """
        创建过滤器表达式
        支持 SQL 字符串和 JSON 配置两种模式
        """
        create_unified_filter = module.get('create_unified_filter')
        create_filter = module['create_filter']
        
        # 优先使用 JSON 配置
        if input_data.filter_config and create_unified_filter:
            return create_unified_filter(input_data.filter_config, mode='json')
        
        # 使用统一过滤器（自动检测模式）
        if create_unified_filter:
            return create_unified_filter(
                input_data.where or "1",
                mode=input_data.filter_mode
            )
        
        # 回退到原始 SQL 过滤器
        return create_filter(input_data.where or "1")
    
    async def execute(
        self,
        input_data: FindzInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> FindzOutput:
        """执行 findz 操作"""
        action = input_data.action.lower()
        
        if action == "search":
            return await self._search(input_data, on_progress, on_log)
        elif action == "nested":
            return await self._find_nested(input_data, on_progress, on_log)
        elif action == "archives_only":
            return await self._archives_only(input_data, on_progress, on_log)
        elif action == "interactive":
            return await self._interactive_help(input_data, on_progress, on_log)
        else:
            return FindzOutput(success=False, message=f"未知操作: {action}")
    
    def _collect_paths(self, input_data: FindzInput) -> List[str]:
        """收集并验证路径"""
        paths = list(input_data.paths) if input_data.paths else []
        if input_data.path:
            path = input_data.path.strip().strip('"')
            if path and path not in paths:
                paths.append(path)
        # 去除引号并验证存在
        valid_paths = []
        for p in paths:
            p = p.strip().strip('"')
            if Path(p).exists():
                valid_paths.append(p)
        return valid_paths if valid_paths else ["."]
    
    def _file_info_to_dict(self, file_info, format_size, with_image_meta: bool = False) -> Dict[str, Any]:
        """将 FileInfo 转换为字典"""
        result = {
            'name': file_info.name,
            'path': file_info.path,
            'size': file_info.size,
            'size_formatted': format_size(file_info.size),
            'mod_time': file_info.mod_time.isoformat(),
            'date': file_info.mod_time.strftime("%Y-%m-%d"),
            'time': file_info.mod_time.strftime("%H:%M:%S"),
            'type': file_info.file_type,
            'container': file_info.container or '',
            'archive': file_info.archive or '',
            'ext': os.path.splitext(file_info.name)[1].lstrip('.'),
        }
        
        # 添加图片元数据（如果启用）
        if with_image_meta:
            dims = file_info._get_image_dimensions()
            if dims:
                result['width'] = dims.width
                result['height'] = dims.height
                result['resolution'] = dims.resolution
                result['megapixels'] = round(dims.megapixels, 2)
                result['aspect_ratio'] = round(dims.aspect_ratio, 2)
        
        return result

    async def _search(
        self,
        input_data: FindzInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> FindzOutput:
        """
        执行文件搜索
        
        优化策略：
        1. 批量处理：每 BATCH_SIZE 个文件处理一次，减少 UI 更新频率
        2. 实时进度：基于扫描文件数动态计算进度
        3. 异步让出：定期让出控制权，避免阻塞事件循环
        """
        import asyncio
        import time
        
        # 性能配置
        BATCH_SIZE = 500  # 每批处理文件数
        PROGRESS_INTERVAL = 0.1  # 进度更新最小间隔（秒）
        YIELD_INTERVAL = 1000  # 每处理多少文件让出一次控制权
        
        paths = self._collect_paths(input_data)
        where = input_data.where or "1"
        
        try:
            if on_log:
                on_log(f"📦 导入 findz 模块...")
            
            module = self._import_module()
            format_size = module['format_size']
            WalkParams = module['WalkParams']
            walk = module['walk']
            is_archive = module['is_archive']
            get_global_cache = module['get_global_cache']
            FileInfo = module['FileInfo']
            
            # 启用图片元数据（如果需要）
            if input_data.with_image_meta:
                FileInfo.enable_image_meta(True)
                if on_log:
                    on_log(f"🖼️ 图片元数据已启用")
            
            if on_log:
                on_log(f"🔍 开始搜索: {', '.join(paths)}")
                if input_data.filter_config:
                    on_log(f"📝 过滤配置: JSON 模式")
                else:
                    on_log(f"📝 过滤条件: {where}")
                on_log(f"⚙️ 选项: no_archive={input_data.no_archive}, max_results={input_data.max_results}, with_image_meta={input_data.with_image_meta}")
            
            if on_progress:
                on_progress(5, "解析过滤器...")
            
            # 创建过滤器（支持 SQL 和 JSON 两种模式）
            try:
                if on_log:
                    on_log(f"🔧 创建过滤器...")
                filter_expr = self._create_filter(input_data, module)
                if on_log:
                    on_log(f"✅ 过滤器创建成功")
            except Exception as e:
                if on_log:
                    on_log(f"❌ 过滤器语法错误: {e}")
                return FindzOutput(success=False, message=f"过滤器语法错误: {e}")
            
            # 错误收集
            errors = []
            def error_handler(msg: str) -> None:
                if len(errors) < 100:  # 限制错误数量
                    errors.append(msg)
                if not input_data.continue_on_error:
                    raise RuntimeError(msg)
            
            if on_progress:
                on_progress(10, "搜索文件...")
            
            # 执行搜索
            all_results = []
            by_extension: Dict[str, int] = {}
            by_archive: Dict[str, int] = {}
            file_count = 0
            dir_count = 0
            archive_count = 0
            scanned_files = 0
            scanned_archives = 0
            
            # 进度控制
            last_progress_time = time.time()
            last_log_count = 0
            start_time = time.time()
            
            # 进度回调
            def progress_cb(scanned_val: int, matched_val: int, current_path: str):
                nonlocal scanned_files, last_progress_time
                scanned_files = scanned_val
                
                current_time = time.time()
                if current_time - last_progress_time >= PROGRESS_INTERVAL:
                    progress = min(10 + int(80 * (1 - 1 / (1 + scanned_val / 10000))), 90)
                    if on_progress:
                        on_progress(progress, f"扫描中: {scanned_val} 文件, {matched_val} 匹配")
                    last_progress_time = current_time

            for search_path in paths:
                if on_log:
                    on_log(f"📂 扫描目录: {search_path}")
                
                params = WalkParams(
                    filter_expr=filter_expr,
                    follow_symlinks=input_data.follow_symlinks,
                    no_archive=input_data.no_archive,
                    archives_only=False,
                    use_cache=True,
                    max_workers=4,
                    error_handler=error_handler,
                    progress_callback=progress_cb,
                )
                
                try:
                    for file_info in walk(search_path, params):
                        # 定期让出控制权，避免阻塞
                        if len(all_results) % 100 == 0:
                            await asyncio.sleep(0)
                        
                        # 批量日志（每 BATCH_SIZE 个文件记录一次）
                        if scanned_files - last_log_count >= BATCH_SIZE:
                            if on_log:
                                speed = scanned_files / max(current_time - start_time, 0.1)
                                on_log(f"📊 已扫描 {scanned_files} 文件 ({speed:.0f}/s)，找到 {len(all_results)} 匹配")
                            last_log_count = scanned_files
                        
                        # 限制结果数量（0表示无限制）
                        if input_data.max_results > 0 and len(all_results) >= input_data.max_results:
                            if on_log:
                                on_log(f"⚠️ 结果已达上限 {input_data.max_results}")
                            break
                        
                        # 转换为字典
                        file_dict = self._file_info_to_dict(file_info, format_size, input_data.with_image_meta)
                        all_results.append(file_dict)
                        
                        # 统计
                        ext = file_dict['ext'].lower()
                        by_extension[ext] = by_extension.get(ext, 0) + 1
                        
                        if file_info.archive:
                            by_archive[file_info.archive] = by_archive.get(file_info.archive, 0) + 1
                            archive_count += 1
                            if file_info.archive not in by_archive or by_archive[file_info.archive] == 1:
                                scanned_archives += 1
                        
                        if file_info.file_type == 'dir':
                            dir_count += 1
                        else:
                            file_count += 1
                    
                except Exception as e:
                    if on_log:
                        on_log(f"❌ 搜索异常: {type(e).__name__}: {e}")
                    if input_data.continue_on_error:
                        errors.append(f"{search_path}: {e}")
                    else:
                        return FindzOutput(success=False, message=f"搜索失败: {e}")
            
            # 保存缓存
            if on_log:
                on_log(f"💾 保存缓存...")
            cache = get_global_cache()
            cache.flush()
            
            if on_progress:
                on_progress(100, "搜索完成")
            
            # 计算总耗时
            total_time = time.time() - start_time
            
            if on_log:
                on_log(f"✅ 搜索完成: 扫描 {scanned_files} 文件，{scanned_archives} 压缩包，耗时 {total_time:.1f}s")
                on_log(f"📊 找到 {len(all_results)} 匹配 (文件:{file_count}, 目录:{dir_count}, 压缩包内:{archive_count})")
                if errors:
                    on_log(f"⚠️ {len(errors)} 个错误")
            
            # 限制返回的文件数量（避免前端卡顿）
            max_return = input_data.max_return_files
            return_files = all_results[:max_return] if max_return > 0 else all_results
            truncated = len(all_results) > len(return_files)
            
            if truncated and on_log:
                on_log(f"📋 返回前 {len(return_files)} 条记录（共 {len(all_results)} 条）")
            
            return FindzOutput(
                success=True,
                message=f"找到 {len(all_results)} 个文件 ({total_time:.1f}s)",
                total_count=len(all_results),
                file_count=file_count,
                dir_count=dir_count,
                archive_count=archive_count,
                files=return_files,  # 只返回部分文件
                by_extension=by_extension,
                by_archive=by_archive,
                errors=errors[:20],
                data={
                    'total_count': len(all_results),
                    'file_count': file_count,
                    'dir_count': dir_count,
                    'archive_count': archive_count,
                    'files': return_files,  # 只返回部分文件
                    'by_extension': by_extension,
                    'by_archive': by_archive,
                    'errors': errors[:20],
                    'paths': paths,
                    'where': where,
                    'scanned_files': scanned_files,
                    'elapsed_time': total_time,
                    'truncated': truncated,
                    'returned_count': len(return_files),
                }
            )
            
        except ImportError as e:
            if on_log:
                on_log(f"❌ findz 模块未安装: {e}")
            return FindzOutput(success=False, message=f"findz 模块未安装: {e}")
        except Exception as e:
            import traceback
            if on_log:
                on_log(f"❌ 搜索失败: {type(e).__name__}: {e}")
                on_log(f"📋 堆栈: {traceback.format_exc()[:500]}")
            return FindzOutput(success=False, message=f"搜索失败: {type(e).__name__}: {e}")
    
    async def _find_nested(
        self,
        input_data: FindzInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> FindzOutput:
        """查找包含嵌套压缩包的外层压缩包"""
        paths = self._collect_paths(input_data)
        
        try:
            module = self._import_module()
            create_filter = module['create_filter']
            format_size = module['format_size']
            WalkParams = module['WalkParams']
            walk = module['walk']
            is_archive = module['is_archive']
            get_global_cache = module['get_global_cache']
            
            if on_log:
                on_log(f"🔍 搜索嵌套压缩包: {', '.join(paths)}")
            if on_progress:
                on_progress(10, "搜索嵌套压缩包...")
            
            # 创建匹配所有文件的过滤器
            filter_expr = create_filter("1")
            
            # 错误收集
            errors = []
            def error_handler(msg: str) -> None:
                if input_data.continue_on_error:
                    errors.append(msg)
            
            # 收集包含嵌套压缩包的外层压缩包
            nested_containers = set()
            
            # 进度回调
            def progress_cb(scanned, matched, current_path):
                if on_progress:
                    progress = min(10 + int(80 * (1 - 1 / (1 + scanned / 10000))), 90)
                    on_progress(progress, f"扫描嵌套中: {scanned} 文件, {len(nested_containers)} 匹配")

            for search_path in paths:
                params = WalkParams(
                    filter_expr=filter_expr,
                    follow_symlinks=input_data.follow_symlinks,
                    no_archive=False,  # 必须扫描压缩包内部
                    archives_only=False,
                    use_cache=True,
                    max_workers=4,
                    error_handler=error_handler,
                    progress_callback=progress_cb,
                )
                
                try:
                    for file_info in walk(search_path, params):
                        # 检查是否在压缩包内（archive 不为空）
                        if file_info.archive:
                            # 检查文件本身是否是压缩包
                            if is_archive(file_info.name):
                                nested_containers.add(file_info.archive)
                except Exception as e:
                    if input_data.continue_on_error:
                        errors.append(f"{search_path}: {e}")
            
            # 转换为列表并排序
            result_archives = sorted(nested_containers)
            
            # 构建结果
            files = []
            for archive_path in result_archives:
                if os.path.exists(archive_path):
                    try:
                        stat = os.stat(archive_path)
                        files.append({
                            'name': os.path.basename(archive_path),
                            'path': archive_path,
                            'size': stat.st_size,
                            'size_formatted': format_size(stat.st_size),
                            'mod_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            'date': datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
                            'time': datetime.fromtimestamp(stat.st_mtime).strftime("%H:%M:%S"),
                            'type': 'file',
                            'container': '',
                            'archive': '',
                            'ext': os.path.splitext(archive_path)[1].lstrip('.'),
                            'has_nested': True,
                        })
                    except Exception:
                        files.append({
                            'name': os.path.basename(archive_path),
                            'path': archive_path,
                            'size': 0,
                            'size_formatted': '0',
                            'type': 'file',
                            'has_nested': True,
                        })
            
            # 保存缓存
            cache = get_global_cache()
            cache.flush()
            
            if on_progress:
                on_progress(100, "搜索完成")
            
            if on_log:
                on_log(f"✅ 找到 {len(files)} 个包含嵌套压缩包的外层压缩包")
            
            return FindzOutput(
                success=True,
                message=f"找到 {len(files)} 个包含嵌套压缩包的外层压缩包",
                total_count=len(files),
                nested_count=len(files),
                files=files,
                errors=errors[:20],
                data={
                    'nested_count': len(files),
                    'files': files,
                    'errors': errors[:20],
                    'paths': paths,
                }
            )
            
        except ImportError as e:
            return FindzOutput(success=False, message=f"findz 模块未安装: {e}")
        except Exception as e:
            if on_log:
                on_log(f"❌ 搜索失败: {e}")
            return FindzOutput(success=False, message=f"搜索失败: {type(e).__name__}: {e}")

    async def _archives_only(
        self,
        input_data: FindzInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> FindzOutput:
        """只搜索压缩包本身"""
        paths = self._collect_paths(input_data)
        where = input_data.where or "1"
        
        try:
            module = self._import_module()
            create_filter = module['create_filter']
            format_size = module['format_size']
            WalkParams = module['WalkParams']
            walk = module['walk']
            get_global_cache = module['get_global_cache']
            
            if on_log:
                on_log(f"🔍 搜索压缩包: {', '.join(paths)}")
                on_log(f"📝 过滤条件: {where}")
            if on_progress:
                on_progress(10, "搜索压缩包...")
            
            # 创建过滤器
            try:
                filter_expr = create_filter(where)
            except Exception as e:
                return FindzOutput(success=False, message=f"过滤器语法错误: {e}")
            
            # 错误收集
            errors = []
            def error_handler(msg: str) -> None:
                if input_data.continue_on_error:
                    errors.append(msg)
            
            # 执行搜索
            all_results = []
            by_extension: Dict[str, int] = {}
            
            # 进度回调
            def progress_cb(scanned, matched, current_path):
                if on_progress:
                    progress = min(10 + int(80 * (1 - 1 / (1 + scanned / 10000))), 90)
                    on_progress(progress, f"扫描压缩包中: {scanned} 文件, {len(all_results)} 匹配")

            for search_path in paths:
                params = WalkParams(
                    filter_expr=filter_expr,
                    follow_symlinks=input_data.follow_symlinks,
                    no_archive=True,  # 不进入压缩包内部
                    archives_only=True,  # 只搜索压缩包
                    use_cache=True,
                    max_workers=4,
                    error_handler=error_handler,
                    progress_callback=progress_cb,
                )
                
                try:
                    for file_info in walk(search_path, params):
                        # 限制结果数量（0表示无限制）
                        if input_data.max_results > 0 and len(all_results) >= input_data.max_results:
                            if on_log:
                                on_log(f"⚠️ 结果已达上限 {input_data.max_results}")
                            break
                        
                        file_dict = self._file_info_to_dict(file_info, format_size)
                        all_results.append(file_dict)
                        
                        ext = file_dict['ext'].lower()
                        by_extension[ext] = by_extension.get(ext, 0) + 1
                        
                except Exception as e:
                    if input_data.continue_on_error:
                        errors.append(f"{search_path}: {e}")
            
            if on_progress:
                on_progress(100, "搜索完成")
            
            if on_log:
                on_log(f"✅ 找到 {len(all_results)} 个压缩包")
            
            return FindzOutput(
                success=True,
                message=f"找到 {len(all_results)} 个压缩包",
                total_count=len(all_results),
                archive_count=len(all_results),
                files=all_results,
                by_extension=by_extension,
                errors=errors[:20],
                data={
                    'archive_count': len(all_results),
                    'files': all_results,
                    'by_extension': by_extension,
                    'errors': errors[:20],
                    'paths': paths,
                    'where': where,
                }
            )
            
        except ImportError as e:
            return FindzOutput(success=False, message=f"findz 模块未安装: {e}")
        except Exception as e:
            if on_log:
                on_log(f"❌ 搜索失败: {e}")
            return FindzOutput(success=False, message=f"搜索失败: {type(e).__name__}: {e}")
    
    async def _interactive_help(
        self,
        input_data: FindzInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> FindzOutput:
        """返回交互式帮助信息"""
        help_text = """
# findz 过滤语法

findz 使用类似 SQL WHERE 子句的语法进行文件搜索。

## 示例

```
# 查找小于 10KB 的文件
size < 10k

# 查找大小在 1M 到 1G 之间的文件
size between 1M and 1G

# 查找 2010 年之前修改的压缩包内文件
date < "2010" and archive <> ""

# 查找名为 foo* 且今天修改的文件
name like "foo%" and date = today

# 使用正则表达式查找
name rlike "(.*-){2}"

# 按扩展名查找
ext in ("jpg", "jpeg", "png")

# 查找目录
type = "dir"
```

## 文件属性

- **name** - 文件名
- **path** - 完整路径
- **size** - 文件大小（未压缩）
- **date** - 修改日期 (YYYY-MM-DD)
- **time** - 修改时间 (HH:MM:SS)
- **ext** - 短扩展名 (如 'txt')
- **ext2** - 长扩展名 (如 'tar.gz')
- **type** - file|dir|link
- **archive** - 压缩包类型 (tar|zip|7z|rar)
- **container** - 容器路径

## 辅助属性

- **today** - 今天的日期
- **mo, tu, we, th, fr, sa, su** - 上一个工作日日期

## 运算符

- **比较**: =, !=, <>, <, >, <=, >=
- **逻辑**: AND, OR, NOT
- **模式**: LIKE, ILIKE (不区分大小写), RLIKE (正则)
- **范围**: BETWEEN, IN
"""
        
        return FindzOutput(
            success=True,
            message="过滤语法帮助",
            data={'help': help_text}
        )
