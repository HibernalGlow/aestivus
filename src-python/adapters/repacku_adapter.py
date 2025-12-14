"""
repacku 适配器
文件重打包工具 - 分析目录结构并打包为压缩文件
"""

import os
from pathlib import Path
from typing import Callable, Dict, List, Optional

from pydantic import Field

from .base import BaseAdapter, AdapterInput, AdapterOutput


class RepackuInput(AdapterInput):
    """repacku 输入参数"""
    path: str = Field(..., description="要处理的目录路径")
    types: List[str] = Field(default_factory=list, description="文件类型过滤，如 ['image', 'document']")
    delete_after: bool = Field(default=False, description="压缩成功后删除源文件")
    display_tree: bool = Field(default=True, description="显示目录树结构")


class RepackuOutput(AdapterOutput):
    """repacku 输出结果"""
    config_path: str = Field(default="", description="生成的配置文件路径")
    compressed_count: int = Field(default=0, description="成功压缩的数量")
    failed_count: int = Field(default=0, description="失败的数量")
    total_folders: int = Field(default=0, description="分析的文件夹总数")


class RepackuAdapter(BaseAdapter):
    """
    repacku 适配器
    
    功能：分析目录结构并打包为压缩文件
    """
    
    name = "repacku"
    display_name = "文件重打包"
    description = "分析目录结构并打包为压缩文件，支持类型过滤"
    category = "file"
    icon = "📦"
    input_schema = RepackuInput
    output_schema = RepackuOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入 repacku 模块"""
        from repacku.core.folder_analyzer import analyze_folder
        from repacku.core.zip_compressor import ZipCompressor
        
        return {
            'analyze_folder': analyze_folder,
            'ZipCompressor': ZipCompressor
        }
    
    async def execute(
        self,
        input_data: RepackuInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> RepackuOutput:
        """
        执行 repacku 功能
        
        流程：
        1. 分析目录结构，生成配置文件
        2. 根据配置文件执行压缩
        """
        # 验证路径
        path = Path(input_data.path)
        if not path.exists():
            return RepackuOutput(
                success=False,
                message=f"路径不存在: {input_data.path}"
            )
        
        if not path.is_dir():
            return RepackuOutput(
                success=False,
                message=f"路径不是目录: {input_data.path}"
            )
        
        try:
            module = self.get_module()
            analyze_folder = module['analyze_folder']
            ZipCompressor = module['ZipCompressor']
            
            # 阶段 1: 分析目录
            if on_log:
                on_log(f"开始分析目录: {input_data.path}")
            if on_progress:
                on_progress(10, "正在分析目录结构...")
            
            # 准备类型过滤参数
            target_types = input_data.types if input_data.types else None
            
            # 执行分析
            config_path = analyze_folder(
                str(path),
                target_file_types=target_types,
                display=input_data.display_tree
            )
            
            if on_log:
                on_log(f"分析完成，配置文件: {config_path}")
            if on_progress:
                on_progress(50, "分析完成，开始压缩...")
            
            # 阶段 2: 执行压缩
            compressor = ZipCompressor()
            results = compressor.compress_from_json(
                config_path,
                delete_after_success=input_data.delete_after
            )
            
            # 统计结果
            success_count = sum(1 for r in results if r.success)
            fail_count = len(results) - success_count
            
            if on_progress:
                on_progress(100, "压缩完成")
            
            if on_log:
                on_log(f"压缩完成: {success_count} 成功, {fail_count} 失败")
            
            return RepackuOutput(
                success=True,
                message=f"压缩完成: {success_count} 成功, {fail_count} 失败",
                config_path=str(config_path),
                compressed_count=success_count,
                failed_count=fail_count,
                total_folders=len(results),
                output_path=input_data.path,  # 输出路径与输入相同
                stats={
                    'success': success_count,
                    'failed': fail_count,
                    'total': len(results)
                }
            )
            
        except ImportError as e:
            return RepackuOutput(
                success=False,
                message=f"repacku 模块未安装: {str(e)}"
            )
        except Exception as e:
            if on_log:
                on_log(f"执行失败: {str(e)}")
            return RepackuOutput(
                success=False,
                message=f"执行失败: {type(e).__name__}: {str(e)}"
            )
