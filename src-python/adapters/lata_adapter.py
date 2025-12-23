"""
lata 适配器
Taskfile 任务启动器 - 使用 lata 包进行交互式任务选择和执行

功能：
- 加载并解析 Taskfile.yml
- 列出所有可用任务
- 执行指定任务
- 支持任务参数输入
"""

from pathlib import Path
from typing import Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import BaseAdapter, AdapterOutput


class LataInput(BaseModel):
    """lata 输入参数"""
    action: str = Field(default="list", description="操作类型: list/execute")
    taskfile_path: Optional[str] = Field(default=None, description="Taskfile.yml 路径")
    task_name: Optional[str] = Field(default=None, description="要执行的任务名称")
    task_args: str = Field(default="", description="任务参数")


class LataOutput(AdapterOutput):
    """lata 输出结果"""
    tasks: List[Dict] = Field(default_factory=list, description="任务列表")
    task_name: Optional[str] = Field(default=None, description="执行的任务名称")
    exit_code: int = Field(default=0, description="任务退出码")


class LataAdapter(BaseAdapter):
    """
    lata 适配器
    使用 lata 包进行 Taskfile 任务管理和执行
    """
    
    name = "lata"
    display_name = "任务启动器"
    description = "Taskfile 任务启动器，支持列出和执行 Taskfile 中定义的任务"
    category = "other"
    icon = "🚀"
    required_packages = ["lata"]
    input_schema = LataInput
    output_schema = LataOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入 lata 模块"""
        from lata import get_launcher
        return {
            "get_launcher": get_launcher,
            "TaskfileLauncher": get_launcher()
        }
    
    async def execute(
        self,
        input_data: LataInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> LataOutput:
        """执行 lata 操作"""
        module = self.get_module()
        TaskfileLauncher = module["TaskfileLauncher"]
        
        # 解析 Taskfile 路径
        taskfile_path = None
        if input_data.taskfile_path:
            taskfile_path = Path(input_data.taskfile_path)
            # 检查文件是否存在
            if not taskfile_path.exists():
                return LataOutput(
                    success=False,
                    message=f"Taskfile 不存在: {taskfile_path}"
                )
        
        try:
            launcher = TaskfileLauncher(taskfile_path)
        except SystemExit:
            # lata 在加载失败时会调用 sys.exit(1)
            return LataOutput(
                success=False,
                message=f"加载 Taskfile 失败: 文件不存在或格式错误"
            )
        except Exception as e:
            return LataOutput(
                success=False,
                message=f"加载 Taskfile 失败: {str(e)}"
            )
        
        if input_data.action == "list":
            # 列出所有任务
            tasks = []
            for name, info in launcher.tasks.items():
                if name != 'default':
                    tasks.append({
                        'name': name,
                        'desc': info.get('desc', ''),
                        'prompt': info.get('prompt', None)
                    })
            
            if on_log:
                on_log(f"找到 {len(tasks)} 个任务")
            
            return LataOutput(
                success=True,
                message=f"找到 {len(tasks)} 个任务",
                tasks=tasks,
                data={'taskfile': str(launcher.taskfile_path)}
            )
        
        elif input_data.action == "execute":
            # 执行指定任务
            if not input_data.task_name:
                return LataOutput(
                    success=False,
                    message="未指定要执行的任务名称"
                )
            
            if on_progress:
                on_progress(0, f"准备执行任务: {input_data.task_name}")
            
            if on_log:
                on_log(f"执行任务: {input_data.task_name}")
            
            # 执行任务
            exit_code = launcher._run_task(input_data.task_name, input_data.task_args)
            
            if on_progress:
                on_progress(100, "任务执行完成")
            
            success = exit_code == 0
            message = f"任务 '{input_data.task_name}' 执行{'成功' if success else '失败'}"
            
            return LataOutput(
                success=success,
                message=message,
                task_name=input_data.task_name,
                exit_code=exit_code
            )
        
        else:
            return LataOutput(
                success=False,
                message=f"未知操作类型: {input_data.action}"
            )
