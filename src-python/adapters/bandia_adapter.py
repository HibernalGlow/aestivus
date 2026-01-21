"""
bandia 适配器
批量解压/压缩工具 - 使用 Bandizip (bz.exe)

功能：
- 从路径列表批量解压压缩包
- 支持解压后删除源文件（可选移入回收站）
- 支持 .zip .7z .rar .tar .gz .bz2 .xz 格式
- 支持批量压缩（根据路径映射恢复压缩）
- 支持 WebSocket 实时进度推送（带节流，减少性能影响）
"""

import asyncio
import json
from pathlib import Path
from typing import Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import BaseAdapter, AdapterOutput


class BandiaInput(BaseModel):
    """bandia 输入参数"""
    action: str = Field(default="extract", description="操作类型: extract/compress/repack")
    # 解压参数
    paths: List[str] = Field(default_factory=list, description="压缩包路径列表（解压用）")
    delete_after: bool = Field(default=True, description="解压成功后删除源文件")
    use_trash: bool = Field(default=True, description="使用回收站而非物理删除")
    overwrite_mode: str = Field(default="overwrite", description="冲突处理: overwrite/skip/rename")
    parallel: bool = Field(default=True, description="是否启用并行处理")
    workers: Optional[int] = Field(default=None, description="并行工作线程数")
    # 压缩参数
    mappings: List[Dict[str, str]] = Field(default_factory=list, description="路径映射列表（压缩用）")
    compress_format: str = Field(default="zip", description="压缩格式: zip/7z")
    delete_source: bool = Field(default=True, description="压缩后删除源目录")


class BandiaOutput(AdapterOutput):
    """bandia 输出结果"""
    # 通用字段
    action: str = Field(default="extract", description="执行的操作类型")
    # 解压字段
    extracted_count: int = Field(default=0, description="成功解压的数量")
    # 压缩字段
    compressed_count: int = Field(default=0, description="成功压缩的数量")
    # 通用字段
    failed_count: int = Field(default=0, description="失败的数量")
    total_count: int = Field(default=0, description="总数量")
    results: List[Dict] = Field(default_factory=list, description="每个文件的处理结果")
    path_mappings: List[Dict[str, str]] = Field(
        default_factory=list, 
        description="压缩包路径到解压目录的映射列表"
    )


class BandiaAdapter(BaseAdapter):
    """
    bandia 适配器
    使用 Bandizip 批量解压/压缩，调用 bandia 模块
    """
    
    name = "bandia"
    display_name = "批量解压/压缩"
    description = "使用 Bandizip 批量解压压缩包或压缩目录，支持路径映射恢复"
    category = "file"
    icon = "📦"
    required_packages = ["bandia"]
    input_schema = BandiaInput
    output_schema = BandiaOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入 bandia 模块"""
        from bandia import (
            extract_batch, compress_batch, 
            ProgressCallback, PathMapping,
            get_shutdown_event
        )
        return {
            "extract_batch": extract_batch,
            "compress_batch": compress_batch,
            "ProgressCallback": ProgressCallback,
            "PathMapping": PathMapping,
            "get_shutdown_event": get_shutdown_event
        }
    
    async def execute(
        self,
        input_data: BandiaInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> BandiaOutput:
        """执行操作"""
        import queue
        import threading
        from concurrent.futures import ThreadPoolExecutor
        
        module = self.get_module()
        extract_batch = module["extract_batch"]
        compress_batch = module["compress_batch"]
        ProgressCallback = module["ProgressCallback"]
        PathMapping = module["PathMapping"]
        get_shutdown_event = module["get_shutdown_event"]
        
        # 处理停止命令
        if input_data.action == "stop":
            shutdown_event = get_shutdown_event()
            shutdown_event.set()
            return BandiaOutput(success=True, message="已发送停止信号", action="stop")
        
        # 解压操作
        if input_data.action == "extract":
            return await self._execute_extract(
                input_data, extract_batch, ProgressCallback, on_progress, on_log
            )
        
        # 压缩/重压缩操作
        elif input_data.action in ("compress", "repack"):
            return await self._execute_compress(
                input_data, compress_batch, ProgressCallback, PathMapping, on_progress, on_log
            )
        
        return BandiaOutput(
            success=False,
            message=f"未知操作: {input_data.action}",
            action=input_data.action
        )
    
    async def _execute_extract(
        self,
        input_data: BandiaInput,
        extract_batch,
        ProgressCallback,
        on_progress: Optional[Callable[[int, str], None]],
        on_log: Optional[Callable[[str], None]]
    ) -> BandiaOutput:
        """执行解压操作"""
        import queue
        from concurrent.futures import ThreadPoolExecutor
        
        paths = [Path(p.strip().strip('"\'')) for p in input_data.paths if p.strip()]
        
        if not paths:
            return BandiaOutput(
                success=False,
                message="没有有效的压缩包路径",
                action="extract"
            )
        
        progress_queue: queue.Queue = queue.Queue()
        result_holder = [None]
        
        def progress_wrapper(value: int, message: str, current_file: str = ""):
            full_msg = f"{message}|{current_file}" if current_file else message
            progress_queue.put(("progress", value, full_msg))
        
        def log_wrapper(message: str):
            progress_queue.put(("log", message))
        
        callback = ProgressCallback(
            on_progress=progress_wrapper,
            on_log=log_wrapper,
            throttle_interval=0.1
        )
        
        def run_extraction():
            try:
                result_holder[0] = extract_batch(
                    paths=paths,
                    delete=input_data.delete_after,
                    use_trash=input_data.use_trash,
                    overwrite_mode=input_data.overwrite_mode,
                    callback=callback,
                    parallel=input_data.parallel,
                    workers=input_data.workers
                )
            except Exception as e:
                result_holder[0] = e
            finally:
                progress_queue.put(("done", None))
        
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(run_extraction)
        
        is_done = False
        while not is_done:
            while True:
                try:
                    msg = progress_queue.get_nowait()
                    msg_type = msg[0]
                    
                    if msg_type == "done":
                        is_done = True
                        break
                    elif msg_type == "progress":
                        _, value, text = msg
                        if on_progress:
                            on_progress(value, text)
                    elif msg_type == "log":
                        _, log_text = msg
                        if on_log:
                            on_log(log_text)
                except queue.Empty:
                    break
            
            if not is_done:
                await asyncio.sleep(0.05)
        
        executor.shutdown(wait=True)
        
        result = result_holder[0]
        if isinstance(result, Exception):
            return BandiaOutput(
                success=False,
                message=f"解压异常: {result}",
                action="extract"
            )
        
        if result is None:
            return BandiaOutput(
                success=False,
                message="解压未返回结果",
                action="extract"
            )
        
        # 转换结果
        results = [
            {
                'path': str(r.path),
                'output_path': str(r.output_path) if r.output_path else None,
                'success': r.success,
                'duration': r.duration,
                'file_size': r.file_size,
                'error': r.error
            }
            for r in result.results
        ]
        
        path_mappings = [
            {
                'archive_path': str(r.path),
                'extracted_path': str(r.output_path)
            }
            for r in result.results
            if r.success and r.output_path
        ]
        
        return BandiaOutput(
            success=result.success,
            message=result.message,
            action="extract",
            extracted_count=result.extracted,
            failed_count=result.failed,
            total_count=result.total,
            results=results,
            path_mappings=path_mappings,
            data={
                'extracted_count': result.extracted,
                'failed_count': result.failed,
                'total_count': result.total,
                'path_mappings': path_mappings
            }
        )
    
    async def _execute_compress(
        self,
        input_data: BandiaInput,
        compress_batch,
        ProgressCallback,
        PathMapping,
        on_progress: Optional[Callable[[int, str], None]],
        on_log: Optional[Callable[[str], None]]
    ) -> BandiaOutput:
        """执行压缩操作"""
        import queue
        from concurrent.futures import ThreadPoolExecutor
        
        if not input_data.mappings:
            return BandiaOutput(
                success=False,
                message="没有路径映射",
                action=input_data.action
            )
        
        # 转换映射
        mappings = [
            PathMapping(
                archive_path=m.get("archive_path", ""),
                extracted_path=m.get("extracted_path", "")
            )
            for m in input_data.mappings
            if m.get("archive_path") and m.get("extracted_path")
        ]
        
        if not mappings:
            return BandiaOutput(
                success=False,
                message="没有有效的路径映射",
                action=input_data.action
            )
        
        progress_queue: queue.Queue = queue.Queue()
        result_holder = [None]
        
        def progress_wrapper(value: int, message: str, current_file: str = ""):
            full_msg = f"{message}|{current_file}" if current_file else message
            progress_queue.put(("progress", value, full_msg))
        
        def log_wrapper(message: str):
            progress_queue.put(("log", message))
        
        callback = ProgressCallback(
            on_progress=progress_wrapper,
            on_log=log_wrapper,
            throttle_interval=0.1
        )
        
        def run_compress():
            try:
                result_holder[0] = compress_batch(
                    mappings=mappings,
                    delete_source=input_data.delete_source,
                    format=input_data.compress_format,
                    callback=callback
                )
            except Exception as e:
                result_holder[0] = e
            finally:
                progress_queue.put(("done", None))
        
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(run_compress)
        
        is_done = False
        while not is_done:
            while True:
                try:
                    msg = progress_queue.get_nowait()
                    msg_type = msg[0]
                    
                    if msg_type == "done":
                        is_done = True
                        break
                    elif msg_type == "progress":
                        _, value, text = msg
                        if on_progress:
                            on_progress(value, text)
                    elif msg_type == "log":
                        _, log_text = msg
                        if on_log:
                            on_log(log_text)
                except queue.Empty:
                    break
            
            if not is_done:
                await asyncio.sleep(0.05)
        
        executor.shutdown(wait=True)
        
        result = result_holder[0]
        if isinstance(result, Exception):
            return BandiaOutput(
                success=False,
                message=f"压缩异常: {result}",
                action=input_data.action
            )
        
        if result is None:
            return BandiaOutput(
                success=False,
                message="压缩未返回结果",
                action=input_data.action
            )
        
        # 转换结果
        results = [
            {
                'source_path': str(r.source_path),
                'archive_path': str(r.archive_path),
                'success': r.success,
                'duration': r.duration,
                'error': r.error
            }
            for r in result.results
        ]
        
        return BandiaOutput(
            success=result.success,
            message=result.message,
            action=input_data.action,
            compressed_count=result.compressed,
            failed_count=result.failed,
            total_count=result.total,
            results=results,
            data={
                'compressed_count': result.compressed,
                'failed_count': result.failed,
                'total_count': result.total
            }
        )
