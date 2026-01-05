"""
bandia 适配器
批量解压工具 - 使用 Bandizip (bz.exe) 进行批量解压

功能：
- 从路径列表批量解压压缩包
- 支持解压后删除源文件（可选移入回收站）
- 支持 .zip .7z .rar .tar .gz .bz2 .xz 格式
- 支持 WebSocket 实时进度推送（带节流，减少性能影响）
"""

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
    parallel: bool = Field(default=False, description="是否启用并行解压")
    workers: Optional[int] = Field(default=None, description="并行工作线程数")


class BandiaOutput(AdapterOutput):
    """bandia 输出结果"""
    extracted_count: int = Field(default=0, description="成功解压的数量")
    failed_count: int = Field(default=0, description="失败的数量")
    total_count: int = Field(default=0, description="总数量")
    results: List[Dict] = Field(default_factory=list, description="每个文件的处理结果")


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
        module = self.get_module()
        extract_batch = module["extract_batch"]
        ProgressCallback = module["ProgressCallback"]
        
        # 转换路径
        paths = [Path(p.strip().strip('"\'')) for p in input_data.paths if p.strip()]
        
        if not paths:
            return BandiaOutput(
                success=False,
                message="没有有效的压缩包路径"
            )
        
        # 创建进度回调（带节流，150ms 间隔）
        def progress_wrapper(value: int, message: str, current_file: str = ""):
            if on_progress:
                # 格式: "message|current_file" 供前端解析
                full_msg = f"{message}|{current_file}" if current_file else message
                on_progress(value, full_msg)
        
        callback = ProgressCallback(
            on_progress=progress_wrapper,
            on_log=on_log,
            throttle_interval=0.15  # 150ms 节流，减少对解压速度的影响
        )
        
        # 执行解压
        result = extract_batch(
            paths=paths,
            delete=input_data.delete_after,
            use_trash=input_data.use_trash,
            overwrite_mode=input_data.overwrite_mode,
            callback=callback,
            parallel=input_data.parallel,
            workers=input_data.workers
        )
        
        # 转换结果
        results = [
            {
                'path': str(r.path),
                'success': r.success,
                'duration': r.duration,
                'file_size': r.file_size,
                'error': r.error
            }
            for r in result.results
        ]
        
        return BandiaOutput(
            success=result.success,
            message=result.message,
            extracted_count=result.extracted,
            failed_count=result.failed,
            total_count=result.total,
            results=results,
            data={
                'extracted_count': result.extracted,
                'failed_count': result.failed,
                'total_count': result.total
            }
        )
