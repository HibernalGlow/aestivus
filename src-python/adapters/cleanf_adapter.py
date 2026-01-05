"""
cleanf 适配器
文件清理工具 - 删除空文件夹和备份文件
"""

from pathlib import Path
from typing import Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import BaseAdapter, AdapterOutput


class CleanfInput(BaseModel):
    """cleanf 输入参数"""
    paths: List[str] = Field(default_factory=list, description="要处理的路径列表")
    presets: List[str] = Field(default_factory=lambda: ["empty_folders", "backup_files"], description="清理预设")
    exclude: Optional[str] = Field(default=None, description="排除关键词，逗号分隔")
    preview: bool = Field(default=False, description="是否预览模式")


class CleanfOutput(AdapterOutput):
    """cleanf 输出结果"""
    total_removed: int = Field(default=0, description="总删除数量")
    removed_details: Dict[str, int] = Field(default_factory=dict, description="各预设删除详情")
    preview_files: List[str] = Field(default_factory=list, description="预览模式下的待删除文件")


class CleanfAdapter(BaseAdapter):
    """cleanf 适配器"""
    
    name = "cleanf"
    display_name = "文件清理"
    description = "删除空文件夹和备份文件，支持多种预设"
    category = "file"
    icon = "🧹"
    required_packages = ["cleanf"]
    input_schema = CleanfInput
    output_schema = CleanfOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入 cleanf 模块"""
        from cleanf.empty import remove_empty_folders
        from cleanf.backup import remove_backup_and_temp
        from cleanf.config import CLEANING_PRESETS
        return {
            "remove_empty_folders": remove_empty_folders,
            "remove_backup_and_temp": remove_backup_and_temp,
            "CLEANING_PRESETS": CLEANING_PRESETS
        }
    
    async def execute(
        self,
        input_data: CleanfInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> CleanfOutput:
        """执行清理"""
        module = self.get_module()
        remove_empty_folders = module["remove_empty_folders"]
        remove_backup_and_temp = module["remove_backup_and_temp"]
        CLEANING_PRESETS = module["CLEANING_PRESETS"]
        
        paths = [Path(p.strip().strip('"\'')) for p in input_data.paths if p.strip()]
        if not paths:
            return CleanfOutput(success=False, message="没有有效的路径")
            
        exclude_keywords = input_data.exclude.split(",") if input_data.exclude else []
        exclude_keywords = [k.strip() for k in exclude_keywords if k.strip()]
        
        total_removed = 0
        removed_details = {}
        preview_files = []
        
        # 扫描阶段（预览或执行前）
        if input_data.preview:
            if on_log:
                on_log("🔍 正在扫描待删除项...")
            
            for path in paths:
                for preset_key in input_data.presets:
                    if preset_key not in CLEANING_PRESETS:
                        continue
                    
                    preset = CLEANING_PRESETS[preset_key]
                    try:
                        files_to_delete = []
                        if preset["function"] == "remove_empty_folders":
                            files_to_delete, _ = remove_empty_folders(path, exclude_keywords=exclude_keywords, preview_mode=True)
                        elif preset["function"] == "remove_backup_and_temp":
                            patterns = preset.get("patterns", [])
                            files_to_delete, _ = remove_backup_and_temp(
                                path, 
                                exclude_keywords=exclude_keywords,
                                custom_patterns=patterns,
                                preview_mode=True
                            )
                        
                        for f in files_to_delete:
                            preview_files.append(str(f))
                    except Exception as e:
                        if on_log:
                            on_log(f"⚠️ 扫描 {preset['name']} 时出错: {e}")
            
            return CleanfOutput(
                success=True,
                message=f"预览完成，共发现 {len(preview_files)} 个待删除项",
                total_removed=len(preview_files),
                preview_files=preview_files
            )
        
        # 执行阶段
        total_steps = len(paths) * len(input_data.presets)
        current_step = 0
        
        for i, path in enumerate(paths):
            if on_log:
                on_log(f"📁 处理目录: {path}")
            
            for preset_key in input_data.presets:
                if preset_key not in CLEANING_PRESETS:
                    continue
                
                preset = CLEANING_PRESETS[preset_key]
                if on_log:
                    on_log(f"  🧹 执行: {preset['name']}...")
                
                try:
                    removed = 0
                    if preset["function"] == "remove_empty_folders":
                        removed, _ = remove_empty_folders(path, exclude_keywords=exclude_keywords)
                    elif preset["function"] == "remove_backup_and_temp":
                        patterns = preset.get("patterns", [])
                        removed, _ = remove_backup_and_temp(
                            path, 
                            exclude_keywords=exclude_keywords,
                            custom_patterns=patterns
                        )
                    
                    removed_details[preset_key] = removed_details.get(preset_key, 0) + removed
                    total_removed += removed
                    
                    if on_log and removed > 0:
                        on_log(f"  ✅ 已删除 {removed} 个项目")
                except Exception as e:
                    if on_log:
                        on_log(f"  ❌ 执行 {preset['name']} 时出错: {e}")
                
                current_step += 1
                if on_progress:
                    on_progress(int(current_step / total_steps * 100), f"处理中: {preset['name']}")
                    
        return CleanfOutput(
            success=True,
            message=f"清理完成，总计删除 {total_removed} 个项目",
            total_removed=total_removed,
            removed_details=removed_details
        )
