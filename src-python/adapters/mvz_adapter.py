"""
mvz 适配器
压缩包文件操作工具 - 对压缩包内的文件进行删除、提取、移动、重命名操作

支持功能：
1. delete: 从压缩包中删除文件
2. extract: 从压缩包中提取文件
3. move: 从压缩包中移动文件到目录（提取+删除）
4. rename: 重命名压缩包内的文件
"""

import os
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any, Tuple

from pydantic import Field

from .base import BaseAdapter, AdapterInput, AdapterOutput


class MvzInput(AdapterInput):
    """mvz 输入参数"""
    action: str = Field(default="extract", description="操作类型: delete/extract/move/rename")
    # 输入文件列表（格式：archive_path//internal_path）
    files: List[str] = Field(default_factory=list, description="文件列表（archive//internal 格式）")
    # 提取/移动选项
    output: str = Field(default=".", description="输出目录")
    near: bool = Field(default=False, description="提取到压缩包所在目录")
    auto_dir: bool = Field(default=False, description="自动创建以压缩包命名的子目录")
    flatten: bool = Field(default=False, description="扁平化提取（不保留目录结构）")
    # 重命名选项
    pattern: str = Field(default="", description="重命名的正则表达式模式")
    replacement: str = Field(default="", description="重命名的替换字符串")
    # 通用选项
    separator: str = Field(default="//", description="压缩包路径和内部路径的分隔符")
    dry_run: bool = Field(default=False, description="预览模式，不实际执行")
    confirm: bool = Field(default=True, description="是否需要确认")


class MvzOutput(AdapterOutput):
    """mvz 输出结果"""
    # 操作统计
    total_files: int = Field(default=0, description="总文件数")
    total_archives: int = Field(default=0, description="涉及的压缩包数")
    success_count: int = Field(default=0, description="成功操作的文件数")
    failed_count: int = Field(default=0, description="失败的文件数")
    # 详细结果
    results: List[Dict[str, Any]] = Field(default_factory=list, description="每个压缩包的操作结果")
    # 预览信息（dry_run 模式）
    preview: List[Dict[str, Any]] = Field(default_factory=list, description="预览信息")


class MvzAdapter(BaseAdapter):
    """mvz 适配器 - 压缩包文件操作工具"""
    
    name = "mvz"
    display_name = "压缩包操作"
    description = "对压缩包内的文件进行删除、提取、移动、重命名操作"
    category = "file"
    icon = "📦"
    required_packages = ["mvz"]
    input_schema = MvzInput
    output_schema = MvzOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入 mvz 模块"""
        from mvz.parser import parse_line, group_by_archive, ArchiveEntry
        from mvz.executor import (
            delete_files, extract_files, batch_rename, find_7z, ExecutionResult
        )
        
        return {
            'parse_line': parse_line,
            'group_by_archive': group_by_archive,
            'ArchiveEntry': ArchiveEntry,
            'delete_files': delete_files,
            'extract_files': extract_files,
            'batch_rename': batch_rename,
            'find_7z': find_7z,
            'ExecutionResult': ExecutionResult,
        }
    
    async def execute(
        self,
        input_data: MvzInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MvzOutput:
        """执行 mvz 操作"""
        action = input_data.action.lower()
        
        if action == "delete":
            return await self._delete(input_data, on_progress, on_log)
        elif action == "extract":
            return await self._extract(input_data, on_progress, on_log)
        elif action == "move":
            return await self._move(input_data, on_progress, on_log)
        elif action == "rename":
            return await self._rename(input_data, on_progress, on_log)
        else:
            return MvzOutput(success=False, message=f"未知操作: {action}")
    
    def _parse_files(self, files: List[str], separator: str, module: Dict) -> List:
        """解析文件列表"""
        parse_line = module['parse_line']
        entries = []
        
        for line in files:
            entry = parse_line(line, separator)
            if entry:
                entries.append(entry)
        
        return entries
    
    async def _delete(
        self,
        input_data: MvzInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MvzOutput:
        """删除压缩包内的文件"""
        try:
            if on_log:
                on_log(f"📦 导入 mvz 模块...")
            
            module = self._import_module()
            find_7z = module['find_7z']
            group_by_archive = module['group_by_archive']
            delete_files = module['delete_files']
            
            # 检查 7z
            if not find_7z():
                return MvzOutput(
                    success=False,
                    message="7-Zip (7z) 未找到，请安装 7-Zip"
                )
            
            if on_log:
                on_log(f"🔍 解析文件列表...")
            
            # 解析文件列表
            entries = self._parse_files(input_data.files, input_data.separator, module)
            
            if not entries:
                return MvzOutput(
                    success=False,
                    message="没有找到有效的压缩包文件条目"
                )
            
            # 按压缩包分组
            groups = group_by_archive(entries)
            
            if on_log:
                on_log(f"📊 找到 {len(entries)} 个文件，分布在 {len(groups)} 个压缩包中")
            
            if on_progress:
                on_progress(10, f"准备删除 {len(entries)} 个文件...")
            
            # 预览模式
            if input_data.dry_run:
                preview = []
                for archive_path, archive_entries in groups.items():
                    preview.append({
                        'archive': archive_path,
                        'files': [e.internal_path for e in archive_entries],
                        'count': len(archive_entries)
                    })
                
                return MvzOutput(
                    success=True,
                    message=f"[预览] 将删除 {len(entries)} 个文件",
                    total_files=len(entries),
                    total_archives=len(groups),
                    preview=preview
                )
            
            # 执行删除
            results = []
            success_count = 0
            failed_count = 0
            
            for idx, (archive_path, archive_entries) in enumerate(groups.items()):
                internal_paths = [e.internal_path for e in archive_entries]
                
                if on_progress:
                    progress = 10 + int(80 * (idx + 1) / len(groups))
                    on_progress(progress, f"删除 {Path(archive_path).name}...")
                
                if on_log:
                    on_log(f"🗑️ 从 {Path(archive_path).name} 删除 {len(internal_paths)} 个文件...")
                
                result = delete_files(archive_path, internal_paths, dry_run=False)
                
                results.append({
                    'archive': archive_path,
                    'success': result.success,
                    'message': result.message,
                    'files': internal_paths,
                    'count': len(internal_paths)
                })
                
                if result.success:
                    success_count += len(internal_paths)
                    if on_log:
                        on_log(f"✅ {result.message}")
                else:
                    failed_count += len(internal_paths)
                    if on_log:
                        on_log(f"❌ {result.message}")
            
            if on_progress:
                on_progress(100, "删除完成")
            
            return MvzOutput(
                success=failed_count == 0,
                message=f"删除完成: 成功 {success_count} 个，失败 {failed_count} 个",
                total_files=len(entries),
                total_archives=len(groups),
                success_count=success_count,
                failed_count=failed_count,
                results=results
            )
            
        except ImportError as e:
            return MvzOutput(success=False, message=f"mvz 模块未安装: {e}")
        except Exception as e:
            if on_log:
                on_log(f"❌ 删除失败: {e}")
            return MvzOutput(success=False, message=f"删除失败: {e}")
    
    async def _extract(
        self,
        input_data: MvzInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MvzOutput:
        """从压缩包中提取文件"""
        try:
            module = self._import_module()
            find_7z = module['find_7z']
            group_by_archive = module['group_by_archive']
            extract_files = module['extract_files']
            
            if not find_7z():
                return MvzOutput(success=False, message="7-Zip (7z) 未找到")
            
            entries = self._parse_files(input_data.files, input_data.separator, module)
            if not entries:
                return MvzOutput(success=False, message="没有找到有效的压缩包文件条目")
            
            groups = group_by_archive(entries)
            
            if on_log:
                on_log(f"📊 找到 {len(entries)} 个文件，分布在 {len(groups)} 个压缩包中")
            
            # 预览模式
            if input_data.dry_run:
                preview = []
                for archive_path, archive_entries in groups.items():
                    final_output = self._calculate_output_dir(
                        archive_path, input_data.output, input_data.near, input_data.auto_dir
                    )
                    preview.append({
                        'archive': archive_path,
                        'output': final_output,
                        'files': [e.internal_path for e in archive_entries],
                        'count': len(archive_entries)
                    })
                
                return MvzOutput(
                    success=True,
                    message=f"[预览] 将提取 {len(entries)} 个文件",
                    total_files=len(entries),
                    total_archives=len(groups),
                    preview=preview
                )
            
            # 执行提取
            results = []
            success_count = 0
            failed_count = 0
            
            for idx, (archive_path, archive_entries) in enumerate(groups.items()):
                internal_paths = [e.internal_path for e in archive_entries]
                final_output = self._calculate_output_dir(
                    archive_path, input_data.output, input_data.near, input_data.auto_dir
                )
                
                if on_progress:
                    progress = 10 + int(80 * (idx + 1) / len(groups))
                    on_progress(progress, f"提取 {Path(archive_path).name}...")
                
                if on_log:
                    on_log(f"📤 从 {Path(archive_path).name} 提取到 {final_output}...")
                
                result = extract_files(
                    archive_path, internal_paths, final_output,
                    dry_run=False, flatten=input_data.flatten
                )
                
                results.append({
                    'archive': archive_path,
                    'output': final_output,
                    'success': result.success,
                    'message': result.message,
                    'files': internal_paths,
                    'count': len(internal_paths)
                })
                
                if result.success:
                    success_count += len(internal_paths)
                    if on_log:
                        on_log(f"✅ {result.message}")
                else:
                    failed_count += len(internal_paths)
                    if on_log:
                        on_log(f"❌ {result.message}")
            
            if on_progress:
                on_progress(100, "提取完成")
            
            return MvzOutput(
                success=failed_count == 0,
                message=f"提取完成: 成功 {success_count} 个，失败 {failed_count} 个",
                total_files=len(entries),
                total_archives=len(groups),
                success_count=success_count,
                failed_count=failed_count,
                results=results
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 提取失败: {e}")
            return MvzOutput(success=False, message=f"提取失败: {e}")
    
    async def _move(
        self,
        input_data: MvzInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MvzOutput:
        """从压缩包中移动文件（提取+删除）"""
        try:
            module = self._import_module()
            find_7z = module['find_7z']
            group_by_archive = module['group_by_archive']
            extract_files = module['extract_files']
            delete_files = module['delete_files']
            
            if not find_7z():
                return MvzOutput(success=False, message="7-Zip (7z) 未找到")
            
            entries = self._parse_files(input_data.files, input_data.separator, module)
            if not entries:
                return MvzOutput(success=False, message="没有找到有效的压缩包文件条目")
            
            groups = group_by_archive(entries)
            
            if on_log:
                on_log(f"📊 找到 {len(entries)} 个文件，分布在 {len(groups)} 个压缩包中")
                on_log(f"🚚 移动操作 = 提取 + 删除")
            
            # 预览模式
            if input_data.dry_run:
                preview = []
                for archive_path, archive_entries in groups.items():
                    final_output = self._calculate_output_dir(
                        archive_path, input_data.output, input_data.near, input_data.auto_dir
                    )
                    preview.append({
                        'archive': archive_path,
                        'output': final_output,
                        'files': [e.internal_path for e in archive_entries],
                        'count': len(archive_entries),
                        'operation': 'extract + delete'
                    })
                
                return MvzOutput(
                    success=True,
                    message=f"[预览] 将移动 {len(entries)} 个文件",
                    total_files=len(entries),
                    total_archives=len(groups),
                    preview=preview
                )
            
            # 执行移动
            results = []
            success_count = 0
            failed_count = 0
            
            for idx, (archive_path, archive_entries) in enumerate(groups.items()):
                internal_paths = [e.internal_path for e in archive_entries]
                final_output = self._calculate_output_dir(
                    archive_path, input_data.output, input_data.near, input_data.auto_dir
                )
                
                if on_progress:
                    progress = 10 + int(80 * (idx + 1) / len(groups))
                    on_progress(progress, f"移动 {Path(archive_path).name}...")
                
                if on_log:
                    on_log(f"📤 从 {Path(archive_path).name} 提取到 {final_output}...")
                
                # 1. 提取
                ext_result = extract_files(
                    archive_path, internal_paths, final_output,
                    dry_run=False, flatten=input_data.flatten
                )
                
                if not ext_result.success:
                    if on_log:
                        on_log(f"❌ 提取失败，跳过删除: {ext_result.message}")
                    failed_count += len(internal_paths)
                    results.append({
                        'archive': archive_path,
                        'output': final_output,
                        'success': False,
                        'message': f"提取失败: {ext_result.message}",
                        'files': internal_paths,
                        'count': len(internal_paths)
                    })
                    continue
                
                if on_log:
                    on_log(f"✅ 提取成功")
                    on_log(f"🗑️ 从压缩包删除原文件...")
                
                # 2. 删除
                del_result = delete_files(archive_path, internal_paths, dry_run=False)
                
                if del_result.success:
                    success_count += len(internal_paths)
                    if on_log:
                        on_log(f"✅ 删除成功")
                    results.append({
                        'archive': archive_path,
                        'output': final_output,
                        'success': True,
                        'message': f"移动成功: {len(internal_paths)} 个文件",
                        'files': internal_paths,
                        'count': len(internal_paths)
                    })
                else:
                    failed_count += len(internal_paths)
                    if on_log:
                        on_log(f"⚠️ 文件已提取，但删除失败: {del_result.message}")
                    results.append({
                        'archive': archive_path,
                        'output': final_output,
                        'success': False,
                        'message': f"已提取但删除失败: {del_result.message}",
                        'files': internal_paths,
                        'count': len(internal_paths)
                    })
            
            if on_progress:
                on_progress(100, "移动完成")
            
            return MvzOutput(
                success=failed_count == 0,
                message=f"移动完成: 成功 {success_count} 个，失败 {failed_count} 个",
                total_files=len(entries),
                total_archives=len(groups),
                success_count=success_count,
                failed_count=failed_count,
                results=results
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 移动失败: {e}")
            return MvzOutput(success=False, message=f"移动失败: {e}")
    
    async def _rename(
        self,
        input_data: MvzInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> MvzOutput:
        """重命名压缩包内的文件"""
        try:
            module = self._import_module()
            find_7z = module['find_7z']
            group_by_archive = module['group_by_archive']
            batch_rename = module['batch_rename']
            
            if not find_7z():
                return MvzOutput(success=False, message="7-Zip (7z) 未找到")
            
            if not input_data.pattern:
                return MvzOutput(success=False, message="未指定重命名模式")
            
            entries = self._parse_files(input_data.files, input_data.separator, module)
            if not entries:
                return MvzOutput(success=False, message="没有找到有效的压缩包文件条目")
            
            groups = group_by_archive(entries)
            
            if on_log:
                on_log(f"📊 找到 {len(entries)} 个文件，分布在 {len(groups)} 个压缩包中")
                on_log(f"🔄 重命名模式: {input_data.pattern} -> {input_data.replacement}")
            
            # 生成重命名对
            all_rename_pairs = []
            total_renames = 0
            
            for archive_path, archive_entries in groups.items():
                pairs = []
                for entry in archive_entries:
                    new_name = re.sub(input_data.pattern, input_data.replacement, entry.internal_path)
                    if new_name != entry.internal_path:
                        pairs.append((entry.internal_path, new_name))
                
                if pairs:
                    all_rename_pairs.append((archive_path, pairs))
                    total_renames += len(pairs)
            
            if total_renames == 0:
                return MvzOutput(
                    success=False,
                    message="没有文件匹配重命名模式"
                )
            
            # 预览模式
            if input_data.dry_run:
                preview = []
                for archive_path, pairs in all_rename_pairs:
                    preview.append({
                        'archive': archive_path,
                        'renames': [{'old': old, 'new': new} for old, new in pairs],
                        'count': len(pairs)
                    })
                
                return MvzOutput(
                    success=True,
                    message=f"[预览] 将重命名 {total_renames} 个文件",
                    total_files=total_renames,
                    total_archives=len(all_rename_pairs),
                    preview=preview
                )
            
            # 执行重命名
            results = []
            success_count = 0
            failed_count = 0
            
            for idx, (archive_path, pairs) in enumerate(all_rename_pairs):
                if on_progress:
                    progress = 10 + int(80 * (idx + 1) / len(all_rename_pairs))
                    on_progress(progress, f"重命名 {Path(archive_path).name}...")
                
                if on_log:
                    on_log(f"✏️ 在 {Path(archive_path).name} 中重命名 {len(pairs)} 个文件...")
                
                result = batch_rename(archive_path, pairs, dry_run=False)
                
                results.append({
                    'archive': archive_path,
                    'success': result.success,
                    'message': result.message,
                    'renames': [{'old': old, 'new': new} for old, new in pairs],
                    'count': len(pairs)
                })
                
                if result.success:
                    success_count += len(pairs)
                    if on_log:
                        on_log(f"✅ {result.message}")
                else:
                    failed_count += len(pairs)
                    if on_log:
                        on_log(f"❌ {result.message}")
            
            if on_progress:
                on_progress(100, "重命名完成")
            
            return MvzOutput(
                success=failed_count == 0,
                message=f"重命名完成: 成功 {success_count} 个，失败 {failed_count} 个",
                total_files=total_renames,
                total_archives=len(all_rename_pairs),
                success_count=success_count,
                failed_count=failed_count,
                results=results
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 重命名失败: {e}")
            return MvzOutput(success=False, message=f"重命名失败: {e}")
    
    def _calculate_output_dir(
        self,
        archive_path: str,
        output: str,
        near: bool,
        auto_dir: bool
    ) -> str:
        """计算输出目录"""
        final_output = output
        
        if near:
            final_output = str(Path(archive_path).parent)
        
        if auto_dir:
            final_output = str(Path(final_output) / Path(archive_path).stem)
        
        return final_output
