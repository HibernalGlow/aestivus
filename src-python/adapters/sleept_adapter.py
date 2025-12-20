"""
sleept 适配器
系统定时器工具 - 支持倒计时、指定时间、网速监控、CPU监控触发电源操作

功能：
- 倒计时模式：设定时间后执行电源操作
- 指定时间模式：在指定时间点执行电源操作
- 网速监控模式：网速低于阈值持续一段时间后执行
- CPU监控模式：CPU使用率低于阈值持续一段时间后执行
- 支持休眠、关机、重启三种电源操作
"""

import os
import sys
import time
import asyncio
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import BaseAdapter, AdapterOutput


class SleeptInput(BaseModel):
    """sleept 输入参数"""
    action: str = Field(default="status", description="操作类型: status, countdown, specific_time, netspeed, cpu, cancel, get_stats")
    
    # 电源操作: sleep, shutdown, restart
    power_mode: str = Field(default="sleep", description="电源操作类型")
    
    # 倒计时模式参数
    hours: int = Field(default=0, description="小时数")
    minutes: int = Field(default=0, description="分钟数")
    seconds: int = Field(default=5, description="秒数")
    
    # 指定时间模式参数
    target_datetime: Optional[str] = Field(default=None, description="目标时间 (YYYY-MM-DD HH:MM:SS)")
    
    # 网速监控参数
    upload_threshold: float = Field(default=242, description="上传阈值 (KB/s)")
    download_threshold: float = Field(default=242, description="下载阈值 (KB/s)")
    net_duration: float = Field(default=2, description="持续时间 (分钟)")
    net_trigger_mode: str = Field(default="both", description="触发模式: both, any")
    
    # CPU监控参数
    cpu_threshold: float = Field(default=10, description="CPU阈值 (%)")
    cpu_duration: float = Field(default=2, description="持续时间 (分钟)")
    
    # 通用参数
    dryrun: bool = Field(default=True, description="演练模式，不实际执行电源操作")


class SleeptOutput(AdapterOutput):
    """sleept 输出结果"""
    timer_status: str = Field(default="idle", description="定时器状态: idle, running, completed, cancelled")
    remaining_seconds: int = Field(default=0, description="剩余秒数")
    current_upload: float = Field(default=0, description="当前上传速度 (KB/s)")
    current_download: float = Field(default=0, description="当前下载速度 (KB/s)")
    current_cpu: float = Field(default=0, description="当前CPU使用率 (%)")
    target_time: Optional[str] = Field(default=None, description="目标时间")


class SleeptAdapter(BaseAdapter):
    """
    sleept 适配器
    
    功能：系统定时器，支持多种触发模式
    """
    
    name = "sleept"
    display_name = "系统定时器"
    description = "定时休眠/关机/重启，支持倒计时、指定时间、网速监控、CPU监控"
    category = "system"
    icon = "⏰"
    required_packages = ["psutil"]
    input_schema = SleeptInput
    output_schema = SleeptOutput
    
    def _import_module(self) -> Dict:
        """懒加载导入模块"""
        import psutil
        return {"psutil": psutil}
    
    async def execute(
        self,
        input_data: SleeptInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> SleeptOutput:
        """执行定时器操作"""
        action = input_data.action
        
        if action == "status":
            return await self._get_status(on_log)
        elif action == "countdown":
            return await self._run_countdown(input_data, on_progress, on_log)
        elif action == "specific_time":
            return await self._run_specific_time(input_data, on_progress, on_log)
        elif action == "netspeed":
            return await self._run_netspeed_monitor(input_data, on_progress, on_log)
        elif action == "cpu":
            return await self._run_cpu_monitor(input_data, on_progress, on_log)
        elif action == "get_stats":
            return await self._get_stats(on_log)
        else:
            return SleeptOutput(
                success=False,
                message=f"未知操作: {action}"
            )
    
    async def _get_status(self, on_log: Optional[Callable[[str], None]] = None) -> SleeptOutput:
        """获取当前系统状态"""
        current_cpu = 0
        current_upload = 0
        current_download = 0
        
        try:
            psutil = self.get_module()["psutil"]
            current_cpu = psutil.cpu_percent(interval=0.1)
        except:
            pass
        
        return SleeptOutput(
            success=True,
            message="状态获取成功",
            timer_status="idle",
            current_cpu=current_cpu,
            current_upload=current_upload,
            current_download=current_download
        )
    
    async def _run_countdown(
        self,
        input_data: SleeptInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> SleeptOutput:
        """运行倒计时（同步阻塞直到完成）"""
        total_seconds = input_data.hours * 3600 + input_data.minutes * 60 + input_data.seconds
        
        if total_seconds <= 0:
            return SleeptOutput(success=False, message="倒计时时间必须大于0")
        
        power_mode = input_data.power_mode
        dryrun = input_data.dryrun
        
        if on_log:
            on_log(f"⏰ 开始倒计时 {input_data.hours}时{input_data.minutes}分{input_data.seconds}秒")
            on_log(f"⚡ 电源操作: {power_mode}, dryrun: {dryrun}")
        
        target_time = datetime.now() + timedelta(seconds=total_seconds)
        
        # 同步倒计时循环
        remaining = total_seconds
        while remaining > 0:
            hours, remainder = divmod(remaining, 3600)
            minutes, seconds = divmod(remainder, 60)
            progress = int((1 - remaining / total_seconds) * 100)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            if on_progress:
                on_progress(progress, f"剩余 {time_str}")
            
            # 使用 asyncio.sleep 让出控制权
            await asyncio.sleep(1)
            remaining -= 1
        
        # 倒计时结束
        if on_progress:
            on_progress(100, "时间到！")
        
        if on_log:
            on_log("⏰ 倒计时结束")
        
        # 执行电源操作
        self._execute_power_action(power_mode, dryrun, on_log)
        
        return SleeptOutput(
            success=True,
            message=f"倒计时完成，已执行 {power_mode}" if not dryrun else f"[dryrun] 倒计时完成，模拟执行 {power_mode}",
            timer_status="completed",
            remaining_seconds=0,
            target_time=target_time.strftime("%Y-%m-%d %H:%M:%S")
        )
    
    async def _run_specific_time(
        self,
        input_data: SleeptInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> SleeptOutput:
        """运行指定时间模式"""
        if not input_data.target_datetime:
            return SleeptOutput(success=False, message="请指定目标时间")
        
        try:
            target = datetime.strptime(input_data.target_datetime, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return SleeptOutput(success=False, message="时间格式错误，请使用 YYYY-MM-DD HH:MM:SS")
        
        now = datetime.now()
        if target <= now:
            return SleeptOutput(success=False, message="目标时间必须在当前时间之后")
        
        total_seconds = int((target - now).total_seconds())
        power_mode = input_data.power_mode
        dryrun = input_data.dryrun
        
        if on_log:
            on_log(f"📅 定时到 {input_data.target_datetime}")
            on_log(f"⚡ 电源操作: {power_mode}, dryrun: {dryrun}")
        
        # 同步倒计时循环
        remaining = total_seconds
        while remaining > 0:
            hours, remainder = divmod(remaining, 3600)
            minutes, seconds = divmod(remainder, 60)
            progress = int((1 - remaining / total_seconds) * 100)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            if on_progress:
                on_progress(progress, f"剩余 {time_str}")
            
            await asyncio.sleep(1)
            remaining -= 1
        
        if on_progress:
            on_progress(100, "时间到！")
        
        if on_log:
            on_log("⏰ 到达指定时间")
        
        self._execute_power_action(power_mode, dryrun, on_log)
        
        return SleeptOutput(
            success=True,
            message=f"定时完成，已执行 {power_mode}" if not dryrun else f"[dryrun] 定时完成，模拟执行 {power_mode}",
            timer_status="completed",
            remaining_seconds=0,
            target_time=input_data.target_datetime
        )
    
    async def _run_netspeed_monitor(
        self,
        input_data: SleeptInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> SleeptOutput:
        """运行网速监控模式"""
        psutil = self.get_module()["psutil"]
        
        power_mode = input_data.power_mode
        dryrun = input_data.dryrun
        duration_seconds = input_data.net_duration * 60
        
        if on_log:
            on_log(f"📡 网速监控启动 - 上传阈值: {input_data.upload_threshold}KB/s, 下载阈值: {input_data.download_threshold}KB/s")
            on_log(f"⏱️ 持续时间: {input_data.net_duration}分钟, 触发模式: {input_data.net_trigger_mode}")
        
        last = psutil.net_io_counters()
        last_time = time.time()
        low_start = None
        max_wait = 3600  # 最多等待1小时
        elapsed_total = 0
        
        while elapsed_total < max_wait:
            await asyncio.sleep(1)
            elapsed_total += 1
            
            now = psutil.net_io_counters()
            now_time = time.time()
            interval = now_time - last_time
            
            up_speed = (now.bytes_sent - last.bytes_sent) / interval / 1024
            down_speed = (now.bytes_recv - last.bytes_recv) / interval / 1024
            
            low_up = up_speed < input_data.upload_threshold
            low_down = down_speed < input_data.download_threshold
            
            trigger = False
            if input_data.net_trigger_mode == "both":
                trigger = low_up and low_down
            else:
                trigger = low_up or low_down
            
            if trigger:
                if low_start is None:
                    low_start = now_time
                    if on_log:
                        on_log(f"📉 网速低于阈值 (↑{up_speed:.1f} ↓{down_speed:.1f} KB/s)，开始计时...")
                
                elapsed = now_time - low_start
                progress = min(99, int(elapsed / duration_seconds * 100))
                
                if on_progress:
                    on_progress(progress, f"低速 {int(elapsed)}s/{int(duration_seconds)}s (↑{up_speed:.1f} ↓{down_speed:.1f})")
                
                if elapsed >= duration_seconds:
                    if on_log:
                        on_log(f"⏰ 网速低于阈值已持续 {input_data.net_duration} 分钟")
                    
                    if on_progress:
                        on_progress(100, "触发条件达成！")
                    
                    self._execute_power_action(power_mode, dryrun, on_log)
                    
                    return SleeptOutput(
                        success=True,
                        message=f"网速监控触发，已执行 {power_mode}" if not dryrun else f"[dryrun] 网速监控触发，模拟执行 {power_mode}",
                        timer_status="completed",
                        current_upload=up_speed,
                        current_download=down_speed
                    )
            else:
                if low_start is not None:
                    if on_log:
                        on_log(f"📈 网速恢复 (↑{up_speed:.1f} ↓{down_speed:.1f} KB/s)")
                    low_start = None
                
                if on_progress:
                    on_progress(0, f"监控中 ↑{up_speed:.1f} ↓{down_speed:.1f} KB/s")
            
            last = now
            last_time = now_time
        
        return SleeptOutput(
            success=False,
            message="监控超时（1小时），未触发条件",
            timer_status="cancelled"
        )
    
    async def _run_cpu_monitor(
        self,
        input_data: SleeptInput,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> SleeptOutput:
        """运行CPU监控模式"""
        psutil = self.get_module()["psutil"]
        
        power_mode = input_data.power_mode
        dryrun = input_data.dryrun
        duration_seconds = input_data.cpu_duration * 60
        
        if on_log:
            on_log(f"💻 CPU监控启动 - 阈值: {input_data.cpu_threshold}%, 持续: {input_data.cpu_duration}分钟")
        
        low_start = None
        max_wait = 3600  # 最多等待1小时
        elapsed_total = 0
        
        while elapsed_total < max_wait:
            await asyncio.sleep(1)
            elapsed_total += 1
            
            cpu_percent = psutil.cpu_percent(interval=None)
            now_time = time.time()
            
            if cpu_percent < input_data.cpu_threshold:
                if low_start is None:
                    low_start = now_time
                    if on_log:
                        on_log(f"📉 CPU {cpu_percent:.1f}% 低于阈值，开始计时...")
                
                elapsed = now_time - low_start
                progress = min(99, int(elapsed / duration_seconds * 100))
                
                if on_progress:
                    on_progress(progress, f"CPU {cpu_percent:.1f}% - 低使用率 {int(elapsed)}s/{int(duration_seconds)}s")
                
                if elapsed >= duration_seconds:
                    if on_log:
                        on_log(f"⏰ CPU低使用率已持续 {input_data.cpu_duration} 分钟")
                    
                    if on_progress:
                        on_progress(100, "触发条件达成！")
                    
                    self._execute_power_action(power_mode, dryrun, on_log)
                    
                    return SleeptOutput(
                        success=True,
                        message=f"CPU监控触发，已执行 {power_mode}" if not dryrun else f"[dryrun] CPU监控触发，模拟执行 {power_mode}",
                        timer_status="completed",
                        current_cpu=cpu_percent
                    )
            else:
                if low_start is not None:
                    if on_log:
                        on_log(f"📈 CPU使用率恢复 ({cpu_percent:.1f}%)")
                    low_start = None
                
                if on_progress:
                    on_progress(0, f"监控中 CPU {cpu_percent:.1f}%")
        
        return SleeptOutput(
            success=False,
            message="监控超时（1小时），未触发条件",
            timer_status="cancelled"
        )
    
    def _execute_power_action(
        self, 
        power_mode: str, 
        dryrun: bool, 
        on_log: Optional[Callable[[str], None]] = None
    ):
        """执行电源操作"""
        action_text = {"sleep": "休眠", "shutdown": "关机", "restart": "重启"}.get(power_mode, power_mode)
        
        if dryrun:
            if on_log:
                on_log(f"🔔 [dryrun] 模拟执行: {action_text}")
            return
        
        if on_log:
            on_log(f"⚡ 执行电源操作: {action_text}")
        
        if sys.platform == 'win32':
            if power_mode == "sleep":
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            elif power_mode == "shutdown":
                os.system("shutdown /s /t 1")
            elif power_mode == "restart":
                os.system("shutdown /r /t 1")
        elif sys.platform == 'darwin':
            if power_mode == "sleep":
                os.system("pmset sleepnow")
            elif power_mode == "shutdown":
                os.system("osascript -e 'tell app \"System Events\" to shut down'")
            elif power_mode == "restart":
                os.system("osascript -e 'tell app \"System Events\" to restart'")
        else:
            if power_mode == "sleep":
                os.system("systemctl suspend")
            elif power_mode == "shutdown":
                os.system("systemctl poweroff")
            elif power_mode == "restart":
                os.system("systemctl reboot")
    
    async def _get_stats(self, on_log: Optional[Callable[[str], None]] = None) -> SleeptOutput:
        """获取系统状态统计"""
        psutil = self.get_module()["psutil"]
        
        # 获取网速
        net1 = psutil.net_io_counters()
        await asyncio.sleep(0.5)
        net2 = psutil.net_io_counters()
        
        up_speed = (net2.bytes_sent - net1.bytes_sent) / 0.5 / 1024
        down_speed = (net2.bytes_recv - net1.bytes_recv) / 0.5 / 1024
        cpu = psutil.cpu_percent(interval=0.1)
        
        return SleeptOutput(
            success=True,
            message=f"CPU: {cpu:.1f}%, 上传: {up_speed:.1f}KB/s, 下载: {down_speed:.1f}KB/s",
            timer_status="idle",
            current_upload=up_speed,
            current_download=down_speed,
            current_cpu=cpu
        )
