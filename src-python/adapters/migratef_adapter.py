"""
migratef 适配器
文件迁移工具 - 调用 migratef 包的接口

支持三种迁移模式：
1. preserve: 保持目录结构迁移
2. flat: 扁平迁移（只迁移文件，不保持目录结构）
3. direct: 直接迁移（类似mv命令，整个文件/文件夹作为单位）
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


class MigrateFInput(AdapterInput):
    """migratef 输入参数"""
    path: str = Field(default="", description="源路径")
    source_paths: List[str] = Field(default_factory=list, description="源路径列表")
    target_path: str = Field(default="", description="目标目录路径")
    mode: str = Field(default="preserve", description="迁移模式: preserve/flat/direct")
    action: str = Field(default="move", description="操作类型: copy/move")
    max_workers: int = Field(default=16, description="最大线程数")


class MigrateFOutput(AdapterOutput):
    """migratef 输出结果"""
    migrated_count: int = Field(default=0, description="成功迁移数量")
    skipped_count: int = Field(default=0, description="跳过数量")
    error_count: int = Field(default=0, description="失败数量")
    total_count: int = Field(default=0, description="总数量")


class MigrateFAdapter(BaseAdapter):
    """migratef 适配器 - 调用 migratef 包"""
    
    name = "migratef"
    display_name = "文件迁移"
    description = "保持目录结构迁移文件和文件夹"
    category = "file"
    icon = "📁"
    required_packages = ["migratef"]
    input_schema = MigrateFInput
    output_schema = MigrateFOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入 migratef 模块"""
        from migratef.core.migration_service import MigrationService
        return {
            'MigrationService': MigrationService
        }
    
    async def execute(
        self,
        input_data: MigrateFInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MigrateFOutput:
        """执行文件迁移"""
        
        # 收集源路径，去除引号
        source_paths = list(input_data.source_paths) if input_data.source_paths else []
        if input_data.path:
            path = input_data.path.strip().strip('"')
            if path not in source_paths:
                source_paths.append(path)
        
        # 处理所有路径的引号
        source_paths = [p.strip().strip('"') for p in source_paths]
        
        if not source_paths:
            return MigrateFOutput(success=False, message="未指定源路径")
        
        # 目标路径也去除引号
        target_path = input_data.target_path.strip().strip('"') if input_data.target_path else ""
        if not target_path:
            return MigrateFOutput(success=False, message="未指定目标路径")
        
        # 验证源路径存在
        from pathlib import Path
        valid_paths = []
        for p in source_paths:
            if Path(p).exists():
                valid_paths.append(p)
            elif on_log:
                on_log(f"跳过不存在: {p}")
        
        if not valid_paths:
            return MigrateFOutput(success=False, message="没有有效的源路径")
        
        mode = input_data.mode.lower()
        action = input_data.action.lower()
        action_text = "移动" if action == "move" else "复制"
        mode_text = {"preserve": "保持结构", "flat": "扁平", "direct": "直接"}.get(mode, mode)
        
        if on_log:
            on_log(f"目标: {target_path}")
            on_log(f"模式: {mode_text} ({action_text})")
            on_log(f"源路径: {len(valid_paths)} 个")
        
        if on_progress:
            on_progress(10, "正在迁移...")
        
        try:
            # 调用 migratef 的 MigrationService
            module = self.get_module()
            MigrationService = module['MigrationService']
            
            service = MigrationService()
            result = service.execute_migration(
                source_paths=valid_paths,
                target_dir=target_path,
                migration_mode=mode,
                action_type=action,
                max_workers=input_data.max_workers or 16
            )
            
            if on_progress:
                on_progress(100, "完成")
            
            migrated = result.get('migrated', 0)
            skipped = result.get('skipped', 0)
            error = result.get('error', 0)
            total = migrated + skipped + error
            
            if on_log:
                on_log(f"{action_text}完成: {migrated} 成功")
                if skipped > 0:
                    on_log(f"跳过: {skipped}")
                if error > 0:
                    on_log(f"错误: {error}")
            
            return MigrateFOutput(
                success=True,
                message=f"{action_text}完成: {migrated} 成功, {skipped} 跳过, {error} 失败",
                migrated_count=migrated,
                skipped_count=skipped,
                error_count=error,
                total_count=total,
                output_path=target_path,
                data={
                    'migrated_count': migrated,
                    'skipped_count': skipped,
                    'error_count': error,
                    'total_count': total
                }
            )
            
        except ImportError as e:
            return MigrateFOutput(
                success=False,
                message=f"migratef 模块未安装: {e}"
            )
        except Exception as e:
            import traceback
            if on_log:
                on_log(f"迁移失败: {e}")
                on_log(traceback.format_exc())
            return MigrateFOutput(
                success=False,
                message=f"迁移失败: {type(e).__name__}: {e}"
            )
