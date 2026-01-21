"""
bandia 适配器
批量解压工具 - 使用 Bandizip (bz.exe) 进行批量解压

功能：
- 从路径列表批量解压压缩包
- 支持解压后删除源文件（可选移入回收站）
- 支持 .zip .7z .rar .tar .gz .bz2 .xz 格式
- 支持 WebSocket 实时进度推送（带节流，减少性能影响）
"""

import asyncio
from pathlib import Path
from typing import Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import BaseAdapter, AdapterOutput


class BandiaInput(BaseModel):
    """bandia 输入参数"""
    action: str = Field(default="extract", description="操作类型: extract")
    paths: List[str] = Field(default_factory=list, description="压缩包路径列表")
    delete_after: bool = Field(default=True, description="解压成功后删除源文件")
    use_trash: bool = Field(default=True, description="使用回收站而非物理删除")
    overwrite_mode: str = Field(default="overwrite", description="冲突处理: overwrite/skip/rename")
    parallel: bool = Field(default=True, description="是否启用并行解压")
    workers: Optional[int] = Field(default=None, description="并行工作线程数")


class BandiaOutput(AdapterOutput):
    """bandia 输出结果"""
    extracted_count: int = Field(default=0, description="成功解压的数量")
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
    使用 Bandizip 批量解压压缩包，调用 bandia 源码模块
    """
    
    name = "bandia"
    display_name = "批量解压"
    description = "使用 Bandizip 批量解压压缩包，支持解压后删除源文件"
    category = "file"
    icon = "📦"
    required_packages = ["bandia"]
    input_schema = BandiaInput
    output_schema = BandiaOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入 bandia 模块"""
        from bandia.main import extract_batch, ProgressCallback
        return {
            "extract_batch": extract_batch,
            "ProgressCallback": ProgressCallback
        }
    
    async def execute(
        self,
        input_data: BandiaInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> BandiaOutput:
        """执行批量解压"""
        import queue
        import threading
        from concurrent.futures import ThreadPoolExecutor
        
        module = self.get_module()
        extract_batch = module["extract_batch"]
        ProgressCallback = module["ProgressCallback"]
        
        if input_data.action == "stop":
            from bandia.main import _shutdown_event
            _shutdown_event.set()
            return BandiaOutput(success=True, message="已发送停止信号")
        
        # 转换路径
        paths = [Path(p.strip().strip('"\'')) for p in input_data.paths if p.strip()]
        
        if not paths:
            return BandiaOutput(
                success=False,
                message="没有有效的压缩包路径"
            )
        
        # 使用队列在线程间传递进度消息
        progress_queue: queue.Queue = queue.Queue()
        result_holder = [None]  # 用于存储结果
        
        def progress_wrapper(value: int, message: str, current_file: str = ""):
            full_msg = f"{message}|{current_file}" if current_file else message
            progress_queue.put(("progress", value, full_msg))
        
        def log_wrapper(message: str):
            progress_queue.put(("log", message))
        
        callback = ProgressCallback(
            on_progress=progress_wrapper,
            on_log=log_wrapper,
            throttle_interval=0.1  # 更快的更新频率
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
        
        # 启动后台线程执行解压
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(run_extraction)
        
        # 主协程轮询队列，发送进度消息
        is_done = False
        while not is_done:
            # 批量拉取当前所有进度消息并处理
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
                # 让出控制权，同时给予队列填充时间
                await asyncio.sleep(0.05)
        
        executor.shutdown(wait=True)
        
        # 处理结果
        result = result_holder[0]
        if isinstance(result, Exception):
            return BandiaOutput(
                success=False,
                message=f"解压异常: {result}"
            )
        
        if result is None:
            return BandiaOutput(
                success=False,
                message="解压未返回结果"
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
        
        # 生成路径映射（仅成功的解压）
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
