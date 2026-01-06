"""
marku 适配器
Markdown 模块化处理工具箱 - 支持直接文本输入/输出和 Diff 对比
"""

import difflib
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

from pydantic import BaseModel, Field

from .base import BaseAdapter, AdapterOutput


class MarkuInput(BaseModel):
    """marku 输入参数"""
    action: str = Field(default="run", description="操作类型: run, undo, history, text")
    module: str = Field(default="markt", description="处理模块名")
    paths: List[str] = Field(default_factory=list, description="要处理的路径列表")
    input_text: Optional[str] = Field(default=None, description="直接输入的 Markdown 文本")
    step_config: Dict[str, Any] = Field(default_factory=dict, description="模块配置")
    recursive: bool = Field(default=False, description="是否递归处理")
    dry_run: bool = Field(default=True, description="预览模式")
    enable_undo: bool = Field(default=True, description="启用 Git 撤销")


class MarkuOutput(AdapterOutput):
    """marku 输出结果"""
    files_processed: int = Field(default=0, description="处理的文件数")
    files_changed: int = Field(default=0, description="变更的文件数")
    input_text: Optional[str] = Field(default=None, description="原始输入文本")
    output_text: Optional[str] = Field(default=None, description="处理后的文本")
    diff_text: Optional[str] = Field(default=None, description="Unified Diff 文本")
    diffs: List[Dict[str, Any]] = Field(default_factory=list, description="文件 Diff 列表")
    undo_sha: Optional[str] = Field(default=None, description="撤销提交 SHA")


class MarkuAdapter(BaseAdapter):
    """marku 适配器"""
    
    name = "marku"
    display_name = "Marku Markdown 处理"
    description = "模块化 Markdown 处理工具箱，支持标题转换、表格转换、去重等"
    category = "text"
    icon = "📝"
    required_packages = ["marku"]
    input_schema = MarkuInput
    output_schema = MarkuOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入 marku 模块"""
        from marku.core.base import ModuleContext
        from marku.core.registry import REGISTRY, create
        try:
            from marku.core.undo_git import GitUndoManager
        except ImportError:
            GitUndoManager = None
        return {
            "ModuleContext": ModuleContext,
            "REGISTRY": REGISTRY,
            "create": create,
            "GitUndoManager": GitUndoManager,
        }
    
    def _generate_unified_diff(self, original: str, processed: str, filename: str = "input.md") -> str:
        """生成 Unified Diff 格式的差异"""
        orig_lines = original.splitlines(keepends=True)
        proc_lines = processed.splitlines(keepends=True)
        diff = difflib.unified_diff(orig_lines, proc_lines, fromfile=f"a/{filename}", tofile=f"b/{filename}")
        return "".join(diff)
    
    async def execute(
        self,
        input_data: MarkuInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MarkuOutput:
        """执行 marku 处理"""
        module = self.get_module()
        ModuleContext = module["ModuleContext"]
        REGISTRY = module["REGISTRY"]
        create = module["create"]
        GitUndoManager = module["GitUndoManager"]
        
        # 处理撤销操作
        if input_data.action == "undo":
            if on_log:
                on_log("⏪ 执行撤销...")
            try:
                if GitUndoManager is None:
                    return MarkuOutput(success=False, message="Git 撤销模块未安装")
                mgr = GitUndoManager(Path.cwd())
                success = mgr.undo_latest()
                if success:
                    return MarkuOutput(success=True, message="撤销成功")
                else:
                    return MarkuOutput(success=False, message="无可撤销的操作")
            except Exception as e:
                return MarkuOutput(success=False, message=f"撤销失败: {e}")
        
        # 处理 history 操作
        if input_data.action == "history":
            try:
                if GitUndoManager is None:
                    return MarkuOutput(success=False, message="Git 撤销模块未安装")
                mgr = GitUndoManager(Path.cwd())
                records = mgr.get_history(10)
                history_text = "\n".join([f"{r['id']}: {r['summary']}" for r in records])
                if on_log:
                    on_log(f"📜 历史记录:\n{history_text}")
                return MarkuOutput(success=True, message=f"找到 {len(records)} 条记录")
            except Exception as e:
                return MarkuOutput(success=False, message=f"获取历史失败: {e}")
        
        # 检查模块是否存在
        if input_data.module not in REGISTRY:
            return MarkuOutput(success=False, message=f"未知模块: {input_data.module}")
        
        # ========== 文本直接处理模式 ==========
        if input_data.input_text:
            original_text = input_data.input_text
            if on_log:
                on_log(f"📝 处理文本输入 ({len(original_text)} 字符)")
            
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8')
            temp_file.write(original_text)
            temp_file.close()
            temp_path = Path(temp_file.name)
            
            try:
                # 创建上下文 (文本模式下始终 dry_run=False 以便获取结果)
                ctx = ModuleContext(root=temp_path.parent)
                
                mod = create(input_data.module)
                config = {
                    "input": str(temp_path),
                    "recursive": False,
                    "verbose": False,
                    **input_data.step_config,
                }
                
                mod.run(ctx, config)
                
                # 读取处理后的内容
                processed_text = temp_path.read_text(encoding='utf-8')
                
                # 生成 Diff
                diff_text = self._generate_unified_diff(original_text, processed_text)
                
                if on_progress:
                    on_progress(100, "完成")
                
                changed = original_text != processed_text
                if on_log:
                    if changed:
                        on_log(f"✅ 文本已处理，有变更")
                    else:
                        on_log(f"✅ 文本已处理，无变更")
                
                return MarkuOutput(
                    success=True,
                    message="文本处理完成" + (" (有变更)" if changed else " (无变更)"),
                    files_processed=1,
                    files_changed=1 if changed else 0,
                    input_text=original_text,
                    output_text=processed_text,
                    diff_text=diff_text if changed else None,
                )
            except Exception as e:
                if on_log:
                    on_log(f"❌ 处理失败: {e}")
                return MarkuOutput(success=False, message=f"处理失败: {e}")
            finally:
                temp_path.unlink(missing_ok=True)
        
        # ========== 文件处理模式 ==========
        paths = [Path(p.strip().strip('"\'')) for p in input_data.paths if p.strip()]
        
        if not paths:
            return MarkuOutput(success=False, message="没有有效的输入路径或文本")
        
        # 创建上下文
        root = paths[0].parent if paths[0].is_file() else paths[0]
        ctx = ModuleContext(root=root)
        
        if input_data.dry_run:
            ctx.shared['__dry_run'] = True
        
        # 启用 Git 撤销
        if input_data.enable_undo and not input_data.dry_run and GitUndoManager:
            try:
                ctx.undo_manager = GitUndoManager(root)
                if ctx.undo_manager.is_dirty():
                    ctx.undo_manager.save_state("Auto-save before marku run")
            except Exception as e:
                if on_log:
                    on_log(f"⚠️ Git 撤销初始化失败: {e}")
        
        # 执行模块
        total_files = 0
        total_changed = 0
        all_diffs = []
        
        try:
            mod = create(input_data.module)
            
            for i, path in enumerate(paths):
                if on_progress:
                    on_progress(int((i / len(paths)) * 80), f"处理: {path.name}")
                if on_log:
                    on_log(f"📄 处理: {path}")
                
                config = {
                    "input": str(path),
                    "recursive": input_data.recursive,
                    "verbose": True,
                    **input_data.step_config,
                }
                
                mod.run(ctx, config)
                
                # 收集结果
                result = ctx.shared.get(input_data.module, {})
                total_files += result.get("files", 0)
                total_changed += result.get("changed", 0)
                
                # 收集 diffs
                diffs = result.get("diffs", [])
                for d in diffs:
                    all_diffs.append({
                        "file": d.get("file", ""),
                        "diff": d.get("diff", [])[:100]
                    })
            
            # 保存撤销点
            undo_sha = None
            if hasattr(ctx, 'undo_manager') and ctx.undo_manager and not input_data.dry_run:
                undo_sha = ctx.undo_manager.save_state(f"marku run: {input_data.module}")
                if undo_sha and on_log:
                    on_log(f"💾 已保存撤销点: {undo_sha[:8]}")
            
            if on_progress:
                on_progress(100, "完成")
            
            return MarkuOutput(
                success=True,
                message=f"处理完成: {total_files} 个文件, {total_changed} 个变更{' (预览)' if input_data.dry_run else ''}",
                files_processed=total_files,
                files_changed=total_changed,
                diffs=all_diffs,
                undo_sha=undo_sha,
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 处理失败: {e}")
            return MarkuOutput(success=False, message=f"处理失败: {e}")

