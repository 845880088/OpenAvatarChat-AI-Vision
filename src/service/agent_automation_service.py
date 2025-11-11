# -*- coding: utf-8 -*-
"""
AI代理自动化服务
用于通过Web API调用 agent_function_call.py 执行自动化任务

作者：廖伟杰
创建时间：2025.11.10
"""

import asyncio
import json
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Dict, Optional
from loguru import logger
from fastapi import WebSocket, WebSocketDisconnect

# 添加项目根目录到Python路径
project_dir = Path(__file__).parent.parent.parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

# 导入agent_function_call模块
try:
    from agent_function_call.agent_function_call import (
        ComputerUse, Messages, get_qwen3_vl_action, StatusWindow
    )
    from agent_function_call.config import (
        DASHSCOPE_API_KEY,
        DASHSCOPE_URL,
        DEFAULT_MODEL,
        DISPLAY_WIDTH,
        DISPLAY_HEIGHT,
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        MAX_STEPS,
    )
    AGENT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"无法导入agent_function_call模块: {e}")
    AGENT_AVAILABLE = False
    DASHSCOPE_API_KEY = None
    DASHSCOPE_URL = None
    DEFAULT_MODEL = "qwen-vl-max"
    DISPLAY_WIDTH = 1000
    DISPLAY_HEIGHT = 1000
    SCREEN_WIDTH = 1920
    SCREEN_HEIGHT = 1080
    MAX_STEPS = 100

try:
    import pyautogui
    SCREENSHOT_AVAILABLE = True
except ImportError:
    logger.warning("pyautogui未安装，截图功能不可用")
    SCREENSHOT_AVAILABLE = False


class AgentTask:
    """AI代理任务类"""
    
    def __init__(self, task_id: str, user_query: str):
        """
        初始化任务
        
        Args:
            task_id: 任务唯一标识符
            user_query: 用户输入的任务指令
        """
        self.task_id = task_id
        self.user_query = user_query
        self.is_running = False
        self.is_stopped = False
        self.current_step = 0
        self.max_steps = MAX_STEPS
        self.websocket: Optional[WebSocket] = None
        self.screenshot_path = os.path.join(tempfile.gettempdir(), f"agent_screenshot_{task_id}.png")
        self.status_window: Optional[StatusWindow] = None
        
    async def send_message(self, msg_type: str, data: dict):
        """发送WebSocket消息"""
        if self.websocket:
            try:
                message = {
                    "type": msg_type,
                    **data
                }
                await self.websocket.send_json(message)
            except Exception as e:
                logger.error(f"发送WebSocket消息失败: {e}")
    
    async def run(self):
        """执行任务"""
        if not AGENT_AVAILABLE:
            await self.send_message("error", {
                "step": 0,
                "text": "AI代理模块未正确安装"
            })
            return
        
        if not SCREENSHOT_AVAILABLE:
            await self.send_message("error", {
                "step": 0,
                "text": "截图模块未安装，请安装 pyautogui"
            })
            return
        
        try:
            self.is_running = True
            logger.info(f"开始执行任务 {self.task_id}: {self.user_query}")
            
            # 设置环境变量
            if DASHSCOPE_API_KEY:
                os.environ["DASHSCOPE_API_KEY"] = DASHSCOPE_API_KEY
            if DASHSCOPE_URL:
                os.environ["DASHSCOPE_URL"] = DASHSCOPE_URL
            
            # 检查API配置
            if not os.getenv("DASHSCOPE_API_KEY"):
                await self.send_message("error", {
                    "step": 0,
                    "text": "未配置 DASHSCOPE_API_KEY，请在 agent_function_call/config.py 中配置"
                })
                return
            
            # 初始化ComputerUse工具
            computer_use = ComputerUse(
                cfg={"display_width_px": DISPLAY_WIDTH, "display_height_px": DISPLAY_HEIGHT}
            )
            
            # 创建消息管理器
            messages = Messages(user_query=self.user_query, computer_use_instance=computer_use)
            
            # 启动桌面状态窗口
            try:
                self.status_window = StatusWindow()
                self.status_window.start(max_steps=self.max_steps, user_query=self.user_query)
                logger.info("桌面状态窗口已启动")
            except Exception as e:
                logger.warning(f"无法启动桌面状态窗口: {e}")
                self.status_window = None
            
            # 截取初始屏幕
            await self.send_message("command", {
                "step": 0,
                "command": "正在截取屏幕..."
            })
            
            screenshot = pyautogui.screenshot()
            screenshot.save(self.screenshot_path)
            messages.add_image_message(self.screenshot_path)
            
            await self.send_message("result", {
                "step": 0,
                "text": "屏幕截取完成"
            })
            
            # 执行循环
            step = 1
            while step <= self.max_steps and not self.is_stopped:
                self.current_step = step
                
                # 更新步骤
                await self.send_message("step", {
                    "step": step,
                    "max_steps": self.max_steps
                })
                
                # 更新桌面状态窗口
                if self.status_window:
                    self.status_window.update_step(step, self.max_steps)
                
                try:
                    # 调用API获取操作指令
                    await self.send_message("command", {
                        "step": step,
                        "command": "正在调用AI分析屏幕..."
                    })
                    
                    output_text, action, computer_use_obj = get_qwen3_vl_action(
                        messages=messages.messages,
                        model_id=DEFAULT_MODEL,
                        display_width=DISPLAY_WIDTH,
                        display_height=DISPLAY_HEIGHT,
                        screen_width=SCREEN_WIDTH,
                        screen_height=SCREEN_HEIGHT
                    )
                    
                    # 发送AI回复
                    await self.send_message("ai_response", {
                        "step": step,
                        "text": output_text
                    })
                    
                    # 添加AI回复到历史
                    messages.add_qwen_response(output_text)
                    
                    # 生成命令描述
                    action_name = action["arguments"]["action"]
                    command_desc = f"{action_name}"
                    
                    if "coordinate" in action["arguments"]:
                        coord = action["arguments"]["coordinate"]
                        command_desc += f" at ({coord[0]}, {coord[1]})"
                    elif "text" in action["arguments"]:
                        text = action["arguments"]["text"][:50]
                        command_desc += f": {text}..."
                    elif "keys" in action["arguments"]:
                        command_desc += f": {action['arguments']['keys']}"
                    elif "pixels" in action["arguments"]:
                        command_desc += f": {action['arguments']['pixels']}px"
                    
                    # 检查是否终止
                    if action["arguments"]["action"] == "terminate":
                        status = action["arguments"].get("status", "unknown")
                        await self.send_message("command", {
                            "step": step,
                            "command": f"任务终止: {status}"
                        })
                        await self.send_message("complete", {
                            "step": step,
                            "status": status
                        })
                        break
                    
                    # 检查是否为answer
                    if action["arguments"]["action"] == "answer":
                        answer_text = action["arguments"].get("text", "")
                        await self.send_message("command", {
                            "step": step,
                            "command": f"回答: {answer_text}"
                        })
                        await self.send_message("complete", {
                            "step": step,
                            "status": "success"
                        })
                        break
                    
                    # 发送当前命令
                    await self.send_message("command", {
                        "step": step,
                        "command": f"执行: {command_desc}"
                    })
                    
                    # 更新桌面状态窗口
                    if self.status_window:
                        self.status_window.update_command(f"执行: {command_desc}")
                        self.status_window.add_history(step, command_desc)
                    
                    # 执行操作
                    result = computer_use_obj.call(action["arguments"])
                    
                    await self.send_message("result", {
                        "step": step,
                        "text": result
                    })
                    
                    # 等待操作生效
                    await asyncio.sleep(2)
                    
                    # 截取新的屏幕
                    screenshot = pyautogui.screenshot()
                    screenshot.save(self.screenshot_path)
                    messages.add_image_message(self.screenshot_path)
                    
                    step += 1
                    
                except Exception as e:
                    logger.error(f"步骤 {step} 执行出错: {e}")
                    await self.send_message("error", {
                        "step": step,
                        "text": str(e)
                    })
                    break
            
            if step > self.max_steps:
                await self.send_message("complete", {
                    "step": step,
                    "status": "达到最大步数限制"
                })
            
            logger.info(f"任务 {self.task_id} 执行完成")
            
        except Exception as e:
            logger.error(f"任务执行失败: {e}")
            await self.send_message("error", {
                "step": self.current_step,
                "text": f"任务执行失败: {str(e)}"
            })
        finally:
            self.is_running = False
            
            # 关闭桌面状态窗口
            if self.status_window:
                try:
                    time.sleep(2)  # 等待2秒让用户看到最终状态
                    self.status_window.close()
                except Exception as e:
                    logger.warning(f"关闭状态窗口失败: {e}")
            
            # 清理截图文件
            try:
                if os.path.exists(self.screenshot_path):
                    os.remove(self.screenshot_path)
            except Exception:
                pass
    
    def stop(self):
        """停止任务"""
        self.is_stopped = True
        logger.info(f"任务 {self.task_id} 已停止")
        
        # 关闭桌面状态窗口
        if self.status_window:
            try:
                self.status_window.close()
            except Exception as e:
                logger.warning(f"关闭状态窗口失败: {e}")


class AgentAutomationService:
    """AI代理自动化服务管理器"""
    
    def __init__(self):
        """初始化服务"""
        self.tasks: Dict[str, AgentTask] = {}
        logger.info("AI代理自动化服务已初始化")
    
    def create_task(self, user_query: str) -> str:
        """
        创建新任务
        
        Args:
            user_query: 用户输入的任务指令
            
        Returns:
            task_id: 任务ID
        """
        task_id = str(uuid.uuid4())
        task = AgentTask(task_id, user_query)
        self.tasks[task_id] = task
        logger.info(f"创建任务 {task_id}: {user_query}")
        return task_id
    
    def get_task(self, task_id: str) -> Optional[AgentTask]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def stop_task(self, task_id: str) -> bool:
        """停止任务"""
        task = self.tasks.get(task_id)
        if task:
            task.stop()
            return True
        return False
    
    def cleanup_task(self, task_id: str):
        """清理任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info(f"清理任务 {task_id}")
    
    async def handle_websocket(self, websocket: WebSocket, task_id: str):
        """
        处理WebSocket连接
        
        Args:
            websocket: WebSocket连接
            task_id: 任务ID
        """
        await websocket.accept()
        
        task = self.get_task(task_id)
        if not task:
            await websocket.send_json({
                "type": "error",
                "text": "任务不存在"
            })
            await websocket.close()
            return
        
        # 绑定WebSocket到任务
        task.websocket = websocket
        
        try:
            # 启动任务
            await task.run()
            
            # 保持连接直到任务完成
            while task.is_running:
                await asyncio.sleep(0.5)
            
        except WebSocketDisconnect:
            logger.info(f"WebSocket断开连接: {task_id}")
            task.stop()
        except Exception as e:
            logger.error(f"WebSocket错误: {e}")
            task.stop()
        finally:
            # 清理任务
            self.cleanup_task(task_id)


# 全局服务实例
agent_service = AgentAutomationService()

