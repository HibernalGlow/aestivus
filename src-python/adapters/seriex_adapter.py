"""
seriex 适配器
漫画压缩包系列提取工具 - 自动识别并整理同一系列的漫画压缩包

直接调用 seriex 源码的核心函数
"""

import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

from pydantic import BaseModel, Field

from .base import BaseAdapter, AdapterOutput


class SeriexInput(BaseModel):
    """seriex 输入参数"""
    action: str = Field(default="plan", description="操作类型: plan, execute, apply")
    directory_path: str = Field(default="", description="要处理的目录路径")
    # 相似度配置
    threshold: float = Field(default=75.0, description="基本相似度阈值(0-100)")
    ratio_threshold: float = Field(default=75.0, description="完全匹配阈值(0-100)")
    partial_threshold: float = Field(default=85.0, description="部分匹配阈值(0-100)")
    token_threshold: float = Field(default=80.0, description="标记匹配阈值(0-100)")
    length_diff_max: float = Field(default=0.3, description="长度差异最大值(0-1)")
    # 配置选项
    add_prefix: bool = Field(default=True, description="是否为系列文件夹添加前缀")
    prefix: str = Field(default="[#s]", description="系列前缀")
    known_series_dirs: List[str] = Field(default_factory=list, description="已知系列目录列表")


class SeriexOutput(AdapterOutput):
    """seriex 输出结果"""
    plan: Dict[str, Dict[str, List[str]]] = Field(default_factory=dict, description="移动计划")
    summary: Dict[str, Dict[str, List[str]]] = Field(default_factory=dict, description="执行结果")
    total_series: int = Field(default=0, description="系列总数")
    total_files: int = Field(default=0, description="文件总数")


class SeriexAdapter(BaseAdapter):
    """
    seriex 适配器 - 直接调用源码函数
    
    功能：漫画压缩包系列提取工具，自动识别并整理同一系列的漫画压缩包
    """
    
    name = "seriex"
    display_name = "Seriex"
    description = "漫画压缩包系列提取工具，自动识别并整理同一系列的漫画压缩包"
    category = "file"
    icon = "📚"
    required_packages = []
    input_schema = SeriexInput
    output_schema = SeriexOutput
    
    _extractor_class = None
    
    def _import_module(self) -> type:
        """导入 seriex 源码模块"""
        if SeriexAdapter._extractor_class is not None:
            return SeriexAdapter._extractor_class
        
        # 添加源码路径
        seriex_src = Path(__file__).parent.parent.parent.parent / "ImageAll" / "MangaClassify" / "ArtistPreview" / "src"
        if str(seriex_src) not in sys.path:
            sys.path.insert(0, str(seriex_src))
        
        try:
            from seriex.extractor import SeriesExtractor
            SeriexAdapter._extractor_class = SeriesExtractor
            return SeriesExtractor
        except Exception as e:
            raise ImportError(f"无法导入 seriex 模块: {e}")
    
    def _create_extractor(self, input_data: SeriexInput):
        """创建提取器实例"""
        SeriesExtractor = self._import_module()
        
        # 构建相似度配置
        similarity_config = {
            'THRESHOLD': input_data.threshold,
            'RATIO_THRESHOLD': input_data.ratio_threshold,
            'PARTIAL_THRESHOLD': input_data.partial_threshold,
            'TOKEN_THRESHOLD': input_data.token_threshold,
            'LENGTH_DIFF_MAX': input_data.length_diff_max
        }
        
        # 创建提取器
        extractor = SeriesExtractor(
            similarity_config=similarity_config,
            add_prefix=input_data.add_prefix
        )
        
        # 设置前缀
        if input_data.prefix:
            extractor.config["prefix"] = input_data.prefix
        
        # 设置已知系列目录
        if input_data.known_series_dirs:
            extractor.reload_known_series_dirs(input_data.known_series_dirs)
        
        return extractor
    
    async def execute(
        self,
        input_data: SeriexInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> SeriexOutput:
        """执行 seriex 操作"""
        action = input_data.action
        
        if action == "plan":
            return await self._prepare_plan(input_data, on_progress, on_log)
        elif action == "execute":
            return await self._execute_plan(input_data, on_progress, on_log)
        elif action == "apply":
            return await self._apply_plan(input_data, on_progress, on_log)
        else:
            return SeriexOutput(success=False, message=f"未知操作: {action}")
    
    async def _prepare_plan(
        self,
        input_data: SeriexInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> SeriexOutput:
        """预处理，生成移动计划"""
        directory_path = input_data.directory_path
        
        if not directory_path:
            return SeriexOutput(success=False, message="请输入目录路径")
        
        import os
        if not os.path.isdir(directory_path):
            return SeriexOutput(success=False, message=f"目录不存在: {directory_path}")
        
        if on_progress:
            on_progress(10, "创建提取器...")
        
        if on_log:
            on_log(f"📂 准备扫描目录: {directory_path}")
        
        try:
            extractor = self._create_extractor(input_data)
            
            if on_progress:
                on_progress(30, "扫描文件...")
            
            if on_log:
                on_log("🔍 开始分析文件...")
            
            # 调用源码的 prepare_directory 方法
            plan = extractor.prepare_directory(directory_path)
            
            if on_progress:
                on_progress(100, "计划生成完成")
            
            # 统计
            total_series = sum(len(groups) for groups in plan.values())
            total_files = sum(
                len(files) 
                for groups in plan.values() 
                for files in groups.values()
            )
            
            if on_log:
                if plan:
                    on_log(f"✅ 计划生成完成")
                    on_log(f"📊 找到 {total_series} 个系列，共 {total_files} 个文件")
                    for dir_path, groups in plan.items():
                        on_log(f"📁 {os.path.basename(dir_path)}:")
                        for folder, files in groups.items():
                            on_log(f"  └─ {folder}: {len(files)} 个文件")
                else:
                    on_log("ℹ️ 没有找到可提取的系列")
            
            return SeriexOutput(
                success=True,
                message=f"计划生成完成，找到 {total_series} 个系列",
                plan=plan,
                total_series=total_series,
                total_files=total_files,
                data={
                    "plan": plan,
                    "total_series": total_series,
                    "total_files": total_files
                }
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 计划生成失败: {e}")
            return SeriexOutput(success=False, message=f"计划生成失败: {e}")
    
    async def _apply_plan(
        self,
        input_data: SeriexInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> SeriexOutput:
        """应用已生成的计划"""
        directory_path = input_data.directory_path
        
        if not directory_path:
            return SeriexOutput(success=False, message="请输入目录路径")
        
        if on_progress:
            on_progress(10, "创建提取器...")
        
        if on_log:
            on_log(f"📂 准备执行计划: {directory_path}")
        
        try:
            extractor = self._create_extractor(input_data)
            
            if on_progress:
                on_progress(20, "生成计划...")
            
            # 先生成计划
            plan = extractor.prepare_directory(directory_path)
            
            if not plan:
                if on_log:
                    on_log("ℹ️ 没有可执行的计划")
                return SeriexOutput(
                    success=True,
                    message="没有可执行的计划",
                    plan={},
                    summary={}
                )
            
            if on_progress:
                on_progress(50, "执行移动...")
            
            if on_log:
                on_log("🚀 开始执行移动...")
            
            # 执行计划
            summary = extractor.apply_prepared_plan(directory_path)
            
            if on_progress:
                on_progress(100, "执行完成")
            
            # 统计
            total_series = sum(len(groups) for groups in summary.values())
            total_files = sum(
                len(files) 
                for groups in summary.values() 
                for files in groups.values()
            )
            
            if on_log:
                on_log(f"✅ 执行完成")
                on_log(f"📊 移动了 {total_files} 个文件到 {total_series} 个系列文件夹")
            
            return SeriexOutput(
                success=True,
                message=f"执行完成，移动了 {total_files} 个文件",
                plan=plan,
                summary=summary,
                total_series=total_series,
                total_files=total_files,
                data={
                    "plan": plan,
                    "summary": summary,
                    "total_series": total_series,
                    "total_files": total_files
                }
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 执行失败: {e}")
            return SeriexOutput(success=False, message=f"执行失败: {e}")
    
    async def _execute_plan(
        self,
        input_data: SeriexInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> SeriexOutput:
        """直接执行（扫描+移动）"""
        directory_path = input_data.directory_path
        
        if not directory_path:
            return SeriexOutput(success=False, message="请输入目录路径")
        
        if on_progress:
            on_progress(10, "创建提取器...")
        
        if on_log:
            on_log(f"📂 开始处理目录: {directory_path}")
        
        try:
            extractor = self._create_extractor(input_data)
            
            if on_progress:
                on_progress(30, "处理中...")
            
            # 调用源码的 process_directory 方法
            success = extractor.process_directory(directory_path)
            
            if on_progress:
                on_progress(100, "处理完成")
            
            summary = extractor.last_summary
            
            # 统计
            total_series = sum(len(groups) for groups in summary.values())
            total_files = sum(
                len(files) 
                for groups in summary.values() 
                for files in groups.values()
            )
            
            if on_log:
                if success:
                    on_log(f"✅ 处理完成")
                    on_log(f"📊 移动了 {total_files} 个文件到 {total_series} 个系列文件夹")
                else:
                    on_log("❌ 处理失败")
            
            return SeriexOutput(
                success=success,
                message=f"处理完成，移动了 {total_files} 个文件" if success else "处理失败",
                summary=summary,
                total_series=total_series,
                total_files=total_files,
                data={
                    "summary": summary,
                    "total_series": total_series,
                    "total_files": total_files
                }
            )
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 处理失败: {e}")
            return SeriexOutput(success=False, message=f"处理失败: {e}")
