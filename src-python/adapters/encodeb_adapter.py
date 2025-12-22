"""
encodeb 适配器
文件名编码修复工具 - 修复乱码文件名

功能：
- 扫描疑似乱码文件名
- 预览编码转换结果
- 批量修复文件名（原地重命名或复制）
- 支持多种编码预设（中文、日文、韩文等）
"""

from pathlib import Path
from typing import Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import BaseAdapter, AdapterOutput


class EncodebInput(BaseModel):
    """encodeb 输入参数"""
    action: str = Field(default="preview", description="操作类型: find, preview, recover")
    paths: List[str] = Field(default_factory=list, description="源路径列表")
    src_encoding: str = Field(default="cp437", description="源编码")
    dst_encoding: str = Field(default="cp936", description="目标编码")
    strategy: str = Field(default="replace", description="修复策略: replace, copy")
    limit: int = Field(default=200, description="最大结果数")


class EncodebOutput(AdapterOutput):
    """encodeb 输出结果"""
    mappings: List[Dict[str, str]] = Field(default_factory=list, description="映射列表")
    matches: List[str] = Field(default_factory=list, description="匹配的乱码文件")


class EncodebAdapter(BaseAdapter):
    """
    encodeb 适配器
    
    功能：文件名编码修复
    """
    
    name = "encodeb"
    display_name = "编码修复"
    description = "修复乱码文件名，支持多种编码预设"
    category = "file"
    icon = "📝"
    required_packages = ["encodeb"]
    input_schema = EncodebInput
    output_schema = EncodebOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入模块"""
        from encodeb.core import (
            Strategy,
            find_suspicious,
            preview_mappings,
            preview_file,
            recover_tree,
            recover_file,
        )
        return {
            "Strategy": Strategy,
            "find_suspicious": find_suspicious,
            "preview_mappings": preview_mappings,
            "preview_file": preview_file,
            "recover_tree": recover_tree,
            "recover_file": recover_file,
        }
    
    async def execute(
        self,
        input_data: EncodebInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> EncodebOutput:
        """执行编码修复操作"""
        action = input_data.action
        
        if action == "find":
            return await self._find_suspicious(input_data, on_progress, on_log)
        elif action == "preview":
            return await self._preview(input_data, on_progress, on_log)
        elif action == "recover":
            return await self._recover(input_data, on_progress, on_log)
        else:
            return EncodebOutput(
                success=False,
                message=f"未知操作: {action}"
            )
    
    async def _find_suspicious(
        self,
        input_data: EncodebInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> EncodebOutput:
        """扫描疑似乱码文件名"""
        mod = self.get_module()
        find_suspicious = mod["find_suspicious"]
        
        if not input_data.paths:
            return EncodebOutput(success=False, message="请提供路径")
        
        all_matches: List[str] = []
        
        for i, path_str in enumerate(input_data.paths):
            path = Path(path_str)
            if not path.exists():
                if on_log:
                    on_log(f"路径不存在: {path}")
                continue
            
            if on_progress:
                on_progress(int((i / len(input_data.paths)) * 100), f"扫描 {path.name}")
            
            try:
                matches = find_suspicious(
                    root=path,
                    include_files=True,
                    include_dirs=True,
                    limit=input_data.limit
                )
                for m in matches:
                    all_matches.append(str(m))
                    if on_log:
                        on_log(f"发现: {m.name}")
            except Exception as e:
                if on_log:
                    on_log(f"扫描失败 {path}: {e}")
        
        if on_progress:
            on_progress(100, "扫描完成")
        
        return EncodebOutput(
            success=True,
            message=f"发现 {len(all_matches)} 个疑似乱码文件名",
            matches=all_matches,
            data={"matches": all_matches}
        )
    
    async def _preview(
        self,
        input_data: EncodebInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> EncodebOutput:
        """预览编码转换结果"""
        mod = self.get_module()
        preview_mappings = mod["preview_mappings"]
        preview_file = mod["preview_file"]
        
        if not input_data.paths:
            return EncodebOutput(success=False, message="请提供路径")
        
        all_mappings: List[Dict[str, str]] = []
        
        for i, path_str in enumerate(input_data.paths):
            path = Path(path_str)
            if not path.exists():
                if on_log:
                    on_log(f"路径不存在: {path}")
                continue
            
            if on_progress:
                on_progress(int((i / len(input_data.paths)) * 100), f"预览 {path.name}")
            
            try:
                if path.is_dir():
                    mappings = preview_mappings(
                        root=path,
                        src_encoding=input_data.src_encoding,
                        dst_encoding=input_data.dst_encoding,
                        limit=input_data.limit
                    )
                else:
                    mappings = preview_file(
                        path=path,
                        src_encoding=input_data.src_encoding,
                        dst_encoding=input_data.dst_encoding
                    )
                
                for src, dst in mappings:
                    all_mappings.append({"src": str(src), "dst": str(dst)})
            except Exception as e:
                if on_log:
                    on_log(f"预览失败 {path}: {e}")
        
        if on_progress:
            on_progress(100, "预览完成")
        
        return EncodebOutput(
            success=True,
            message=f"预览完成，{len(all_mappings)} 个文件需要修复",
            mappings=all_mappings,
            data={"mappings": all_mappings}
        )
    
    async def _recover(
        self,
        input_data: EncodebInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> EncodebOutput:
        """执行编码修复"""
        mod = self.get_module()
        Strategy = mod["Strategy"]
        recover_tree = mod["recover_tree"]
        recover_file = mod["recover_file"]
        
        if not input_data.paths:
            return EncodebOutput(success=False, message="请提供路径")
        
        strategy = Strategy.REPLACE if input_data.strategy == "replace" else Strategy.COPY
        strategy_desc = "原地重命名" if strategy == Strategy.REPLACE else "复制到新目录"
        
        if on_log:
            on_log(f"策略: {strategy_desc}")
        
        success_count = 0
        
        for i, path_str in enumerate(input_data.paths):
            path = Path(path_str)
            if not path.exists():
                if on_log:
                    on_log(f"路径不存在: {path}")
                continue
            
            if on_progress:
                on_progress(int((i / len(input_data.paths)) * 100), f"处理 {path.name}")
            
            try:
                if path.is_dir():
                    dest = recover_tree(
                        root=path,
                        src_encoding=input_data.src_encoding,
                        dst_encoding=input_data.dst_encoding,
                        strategy=strategy
                    )
                    if on_log:
                        on_log(f"✅ 目录处理完成: {dest}")
                else:
                    dest = recover_file(
                        path=path,
                        src_encoding=input_data.src_encoding,
                        dst_encoding=input_data.dst_encoding,
                        strategy=strategy
                    )
                    if on_log:
                        on_log(f"✅ 文件处理完成: {dest}")
                
                success_count += 1
            except Exception as e:
                if on_log:
                    on_log(f"❌ 处理失败 {path}: {e}")
        
        if on_progress:
            on_progress(100, "修复完成")
        
        return EncodebOutput(
            success=True,
            message=f"修复完成，成功处理 {success_count} 个路径"
        )
