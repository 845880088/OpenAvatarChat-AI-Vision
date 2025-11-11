# -*- coding: utf-8 -*-
"""
计算机自动化控制工具

这个模块实现了一个用于AI代理的计算机控制工具，可以模拟鼠标和键盘操作。
主要功能包括：
- 鼠标操作：点击、拖拽、滚动
- 键盘操作：按键、文本输入
- 等待和任务控制

作者：廖伟杰
创建时间：2025.11.10
"""

from typing import Union, Tuple, List
import base64  # 用于图片编码
from pathlib import Path  # 用于路径处理
import os  # 用于环境变量
import json  # 用于JSON解析
import tempfile  # 用于临时文件

from openai import OpenAI  # 用于API调用
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.llm.schema import Message, ContentItem  # 用于消息格式化
try:
    from qwen_agent.prompts import NousFnCallPrompt  # 用于函数调用提示词处理
except ImportError:
    NousFnCallPrompt = None  # 如果导入失败，设置为None
from pynput import mouse, keyboard  # 用于控制鼠标和键盘
from pynput.mouse import Button     # 修复：form -> from
import time  # 用于等待操作
import pyautogui  # 用于自动截图
import tkinter as tk  # 用于状态窗口
from tkinter import ttk  # 用于状态窗口组件
import threading  # 用于线程管理

# 尝试导入配置文件
try:
    from config import (
        DASHSCOPE_API_KEY, 
        DASHSCOPE_URL, 
        DEFAULT_MODEL,
        DISPLAY_WIDTH,
        DISPLAY_HEIGHT,
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        MAX_STEPS,
    )
    CONFIG_LOADED = True
except ImportError:
    CONFIG_LOADED = False
    DASHSCOPE_API_KEY = None
    DASHSCOPE_URL = None
    DEFAULT_MODEL = "qwen-vl-max"
    DISPLAY_WIDTH = 1000
    DISPLAY_HEIGHT = 1000
    SCREEN_WIDTH = 1920
    SCREEN_HEIGHT = 1080
    MAX_STEPS = 100

@register_tool("computer_use")
class ComputerUse(BaseTool):
    """
    计算机使用工具类
    
    这个类提供了通过鼠标和键盘与计算机桌面GUI交互的功能。
    它是一个AI代理工具，可以被AI模型调用来执行各种计算机操作。
    
    支持的操作包括：
    - 鼠标操作：移动、点击、拖拽、滚动
    - 键盘操作：按键组合、文本输入
    - 控制操作：等待、终止任务、回答问题
    """
    @property
    def description(self):
        """
        返回工具的描述信息
        
        Returns:
            str: 包含工具使用说明的描述文本
        """
        return f"""
Use a mouse and keyboard to interact with a computer, and take screenshots.
* This is an interface to a desktop GUI. You do not have access to a terminal or applications menu. You must click on desktop icons to start applications.
* Some applications may take time to start or process actions, so you may need to wait and take successive screenshots to see the results of your actions. E.g. if you click on Firefox and a window doesn't open, try wait and taking another screenshot.
* The screen's resolution is {self.display_width_px}x{self.display_height_px}.
* Whenever you intend to move the cursor to click on an element like an icon, you should consult a screenshot to determine the coordinates of the element before moving the cursor.
* If you tried clicking on a program or link but it failed to load, even after waiting, try adjusting your cursor position so that the tip of the cursor visually falls on the element that you want to click.
* Make sure to click any buttons, links, icons, etc with the cursor tip in the center of the element. Don't click boxes on their edges.
""".strip()

    parameters = {
        "properties": {
            "action": {
                "description": """
The action to perform. The available actions are:
* `key`: Performs key down presses on the arguments passed in order, then performs key releases in reverse order.
* `type`: Type a string of text on the keyboard.
* `mouse_move`: Move the cursor to a specified (x, y) pixel coordinate on the screen.
* `left_click`: Click the left mouse button at a specified (x, y) pixel coordinate on the screen.
* `left_click_drag`: Click and drag the cursor to a specified (x, y) pixel coordinate on the screen.
* `right_click`: Click the right mouse button at a specified (x, y) pixel coordinate on the screen.
* `middle_click`: Click the middle mouse button at a specified (x, y) pixel coordinate on the screen.
* `double_click`: Double-click the left mouse button at a specified (x, y) pixel coordinate on the screen.
* `triple_click`: Triple-click the left mouse button at a specified (x, y) pixel coordinate on the screen (simulated as double-click since it's the closest action).
* `scroll`: Performs a scroll of the mouse scroll wheel.
* `hscroll`: Performs a horizontal scroll (mapped to regular scroll).
* `wait`: Wait specified seconds for the change to happen.
* `terminate`: Terminate the current task and report its completion status.
* `answer`: Answer a question.
""".strip(),
                "enum": [
                    "key",
                    "type",
                    "mouse_move",
                    "left_click",
                    "left_click_drag",
                    "right_click",
                    "middle_click",
                    "double_click",
                    "triple_click",
                    "scroll",
                    "hscroll",
                    "wait",
                    "terminate",
                    "answer",
                ],
                "type": "string",
            },
            "keys": {
                "description": "Required only by `action=key`.",
                "type": "array",
            },
            "text": {
                "description": "Required only by `action=type` and `action=answer`.",
                "type": "string",
            },
            "coordinate": {
                "description": "(x, y): The x (pixels from the left edge) and y (pixels from the top edge) coordinates to move the mouse to.",
                "type": "array",
            },
            "pixels": {
                "description": "The amount of scrolling to perform. Positive values scroll up, negative values scroll down. Required only by `action=scroll` and `action=hscroll`.",
                "type": "number",
            },
            "time": {
                "description": "The seconds to wait. Required only by `action=wait`.",
                "type": "number",
            },
            "status": {
                "description": "The status of the task. Required only by `action=terminate`.",
                "type": "string",
                "enum": ["success", "failure"],
            },
        },
        "required": ["action"],
        "type": "object",
    }

    def __init__(self, cfg=None):
        """
        初始化计算机使用工具
        
        Args:
            cfg (dict): 配置字典，包含显示器分辨率等信息
        """
        # 从配置中获取显示器分辨率
        self.display_width_px = cfg["display_width_px"] if cfg else 1920
        self.display_height_px = cfg["display_height_px"] if cfg else 1080
        
        # 调用父类初始化
        super().__init__(cfg)
        
        # 初始化鼠标和键盘控制器
        self.mouse_controller = mouse.Controller()
        self.keyboard_controller = keyboard.Controller()

    def call(self, params: Union[str, dict], **kwargs):
        """
        执行指定的操作
        
        Args:
            params (Union[str, dict]): 操作参数，包含action和相关参数
            **kwargs: 额外的关键字参数
            
        Returns:
            str: 操作执行结果的描述
            
        Raises:
            ValueError: 当提供无效的action时抛出
        """
        # 验证并解析参数格式
        params = self._verify_json_format_args(params)
        action = params["action"]
        
        # 根据不同的action执行相应的操作
        if action in ["left_click", "right_click", "middle_click", "double_click", "triple_click"]:
            return self._mouse_click(action, params.get("coordinate"))
        elif action == "key":
            # 兼容两种格式：keys数组 或 text字符串
            keys = params.get("keys") or [params.get("text", "")]
            if isinstance(keys, str):
                keys = [keys]
            return self._key(keys)
        elif action == "type":
            return self._type(params["text"])
        elif action == "mouse_move":
            return self._mouse_move(params["coordinate"])
        elif action == "left_click_drag":
            return self._left_click_drag(params["coordinate"])
        elif action == "scroll":
            return self._scroll(params["pixels"])
        elif action == "hscroll":
            return self._hscroll(params["pixels"])
        elif action == "answer":
            return self._answer(params["text"])
        elif action == "wait":
            return self._wait(params["time"])
        elif action == "terminate":
            return self._terminate(params["status"])
        else:
            raise ValueError(f"无效的操作类型: {action}")

    def _mouse_click(self, button: str, coordinate: Tuple[int, int] = None):
        """
        执行鼠标点击操作
        
        Args:
            button (str): 点击类型，支持left_click, right_click, middle_click, double_click, triple_click
            coordinate (Tuple[int, int], optional): 点击坐标(x, y)，如果提供则先移动到该位置
            
        Returns:
            str: 操作执行结果描述
        """
        # 按钮映射：将字符串按钮名称映射到pynput的Button枚举
        button_map = {
            "left_click": Button.left,
            "right_click": Button.right,
            "middle_click": Button.middle,
            "double_click": Button.left,
            "triple_click": Button.left,
        }
        
        try:
            # 如果提供了坐标，先移动鼠标到指定位置
            if coordinate:
                self.mouse_controller.position = (coordinate[0], coordinate[1])
                
            # 根据不同的按钮类型执行相应的点击操作
            if button in ['left_click', 'right_click', 'middle_click']:
                print(f"尝试执行 {button} 操作")
                self.mouse_controller.click(button_map[button])
                print(f"成功执行 {button} 操作")
            elif button == 'double_click':
                print(f"尝试执行 {button} 操作")
                self.mouse_controller.click(button_map[button])
                self.mouse_controller.click(button_map[button])
                print(f"成功执行 {button} 操作")
            elif button == 'triple_click':
                # Triple click simulated with three clicks
                print(f"尝试执行 {button} 操作")
                self.mouse_controller.click(button_map[button])
                self.mouse_controller.click(button_map[button])
                self.mouse_controller.click(button_map[button])
                print(f"成功执行 {button} 操作")
        except Exception as e:
            print(f"执行鼠标点击失败: {e}")
            return f"Failed to click mouse: {e}"
            
        return f"Successfully performed {button} operation"

    def _key(self, keys: List[str]):
        """
        执行键盘按键操作
        
        Args:
            keys (List[str]): 要按下的按键列表，支持组合键
            
        Returns:
            str: 操作执行结果描述
        """
        try:
            print(f"尝试执行按键操作: {keys}")
            # 按下所有按键（按顺序）
            for key in keys:
                if hasattr(keyboard.Key, key):
                    # 特殊按键（如ctrl, alt, shift等）
                    self.keyboard_controller.press(getattr(keyboard.Key, key))
                else:
                    # 普通字符按键
                    self.keyboard_controller.press(key)
            
            # 释放所有按键（逆序）
            for key in reversed(keys):
                if hasattr(keyboard.Key, key):
                    self.keyboard_controller.release(getattr(keyboard.Key, key))
                else:
                    self.keyboard_controller.release(key)
            
            print(f"成功执行按键操作: {keys}")
            return f"Successfully pressed keys: {keys}"
        except Exception as e:
            print(f"执行按键操作失败: {e}")
            return f"Failed to press keys: {e}"

    def _type(self, text: str):
        """
        输入文本内容
        
        Args:
            text (str): 要输入的文本内容
            
        Returns:
            str: 操作执行结果描述
        """
        try:
            print(f"尝试输入文本: {text[:50]}...")  # 只显示前50个字符
            self.keyboard_controller.type(text)
            print(f"成功输入文本，长度: {len(text)}")
            return f"Successfully typed text of length {len(text)}"
        except Exception as e:
            print(f"输入文本失败: {e}")
            return f"Failed to type text: {e}"

    def _mouse_move(self, coordinate: Tuple[int, int]):
        """
        移动鼠标到指定坐标
        
        Args:
            coordinate (Tuple[int, int]): 目标坐标(x, y)
            
        Returns:
            str: 操作执行结果描述
        """
        try:
            x, y = coordinate[0], coordinate[1]
            print(f"尝试移动鼠标到坐标: ({x}, {y})")
            
            # 检查坐标是否在屏幕范围内
            if 0 <= x <= self.display_width_px and 0 <= y <= self.display_height_px:
                self.mouse_controller.position = (x, y)
                print(f"成功移动鼠标到坐标: ({x}, {y})")
                return f"Successfully moved mouse to ({x}, {y})"
            else:
                error_msg = f"坐标超出屏幕范围: ({x}, {y}), 屏幕大小: {self.display_width_px}x{self.display_height_px}"
                print(error_msg)
                return f"Coordinate out of bounds: {error_msg}"
        except Exception as e:
            print(f"移动鼠标失败: {e}")
            return f"Failed to move mouse: {e}"

    def _left_click_drag(self, coordinate: Tuple[int, int]):
        """
        执行鼠标拖拽操作（从当前位置拖拽到目标位置）
        
        Args:
            coordinate (Tuple[int, int]): 拖拽的目标坐标(x, y)
            
        Returns:
            str: 操作执行结果描述
        """
        try:
            x, y = coordinate[0], coordinate[1]
            current_pos = self.mouse_controller.position
            print(f"尝试从 {current_pos} 拖拽到 ({x}, {y})")
            
            # 按下左键
            self.mouse_controller.press(Button.left)
            # 移动到目标位置
            self.mouse_controller.position = (x, y)
            # 释放左键
            self.mouse_controller.release(Button.left)
            
            print(f"成功拖拽到坐标: ({x}, {y})")
            return f"Successfully dragged from {current_pos} to ({x}, {y})"
        except Exception as e:
            print(f"拖拽操作失败: {e}")
            return f"Failed to drag: {e}"

    def _scroll(self, pixels: int):
        """
        执行鼠标滚轮滚动操作
        
        Args:
            pixels (int): 滚动的像素数，正值向上滚动，负值向下滚动
            
        Returns:
            str: 操作执行结果描述
        """
        try:
            print(f"尝试滚动 {pixels} 像素")
            # pynput的scroll方法：正值向上，负值向下
            scroll_direction = "向上" if pixels > 0 else "向下"
            self.mouse_controller.scroll(0, pixels)
            print(f"成功{scroll_direction}滚动 {abs(pixels)} 像素")
            return f"Successfully scrolled {pixels} pixels"
        except Exception as e:
            print(f"滚动操作失败: {e}")
            return f"Failed to scroll: {e}"

    def _hscroll(self, pixels: int):
        """
        执行水平滚动操作（映射到普通滚动）
        
        Args:
            pixels (int): 滚动的像素数，正值向右滚动，负值向左滚动
            
        Returns:
            str: 操作执行结果描述
        """
        try:
            print(f"尝试水平滚动 {pixels} 像素")
            # 水平滚动映射到普通滚动
            scroll_direction = "向右" if pixels > 0 else "向左"
            self.mouse_controller.scroll(pixels, 0)
            print(f"成功{scroll_direction}滚动 {abs(pixels)} 像素")
            return f"Successfully horizontal scrolled {pixels} pixels"
        except Exception as e:
            print(f"水平滚动操作失败: {e}")
            return f"Failed to horizontal scroll: {e}"

    def _answer(self, text: str):
        """
        回答问题（返回文本回答）
        
        Args:
            text (str): 回答的文本内容
            
        Returns:
            str: 回答内容
        """
        print(f"提供回答: {text}")
        return f"Answer: {text}"

    def _wait(self, wait_time: float):
        """
        等待指定的时间
        
        Args:
            wait_time (float): 等待的秒数
            
        Returns:
            str: 操作执行结果描述
        """
        try:
            print(f"开始等待 {wait_time} 秒")
            time.sleep(wait_time)
            print(f"等待完成，已等待 {wait_time} 秒")
            return f"Successfully waited for {wait_time} seconds"
        except Exception as e:
            print(f"等待操作失败: {e}")
            return f"Failed to wait: {e}"

    def _terminate(self, status: str):
        """
        终止当前任务并报告完成状态
        
        Args:
            status (str): 任务状态，"success" 或 "failure"
            
        Returns:
            str: 任务终止结果描述
        """
        print(f"任务终止，状态: {status}")
        if status == "success":
            return "Task completed successfully"
        elif status == "failure":
            return "Task failed to complete"
        else:
            return f"Task terminated with status: {status}"


# ==================== 状态显示窗口类 ====================

class StatusWindow:
    """
    实时状态显示窗口
    
    创建一个悬浮窗口，实时显示AI执行进度和命令。
    窗口特点：
    - 始终置顶
    - 半透明背景
    - 显示当前步骤
    - 显示正在执行的命令
    - 显示命令历史
    """
    
    def __init__(self):
        """初始化状态窗口"""
        self.window = None
        self.user_query_label = None  # 用户指令显示标签
        self.step_label = None
        self.command_label = None
        self.history_text = None
        self.progress_bar = None
        self.max_steps = 100
        self.user_query = ""  # 保存用户指令
        self.thread = None
        self.is_running = False
        
    def start(self, max_steps=100, user_query=""):
        """
        在新线程中启动状态窗口
        
        Args:
            max_steps (int): 最大执行步数
            user_query (str): 用户输入的任务指令
        """
        self.max_steps = max_steps
        self.user_query = user_query
        self.is_running = True
        self.thread = threading.Thread(target=self._create_window, daemon=True)
        self.thread.start()
        time.sleep(0.5)  # 等待窗口创建完成
        
    def _create_window(self):
        """创建窗口（在独立线程中运行）"""
        self.window = tk.Tk()
        self.window.title("🤖 AI执行状态监控")
        
        # 设置窗口大小和位置（右上角）
        window_width = 500
        window_height = 400
        screen_width = self.window.winfo_screenwidth()
        x = screen_width - window_width - 20
        y = 20
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 设置窗口属性
        self.window.attributes('-topmost', True)  # 始终置顶
        self.window.attributes('-alpha', 0.95)    # 半透明
        
        # 设置样式
        style = ttk.Style()
        style.theme_use('clam')
        
        # 主框架
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 标题
        title_label = ttk.Label(
            main_frame, 
            text="🤖 AI正在执行任务...", 
            font=('Arial', 14, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # 用户指令显示区域
        query_frame = ttk.LabelFrame(main_frame, text="用户指令", padding="5")
        query_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.user_query_label = ttk.Label(
            query_frame, 
            text=self.user_query if self.user_query else "等待中...", 
            font=('Arial', 10),
            foreground='darkgreen',
            wraplength=470,
            justify=tk.LEFT
        )
        self.user_query_label.grid(row=0, column=0, sticky=tk.W)
        
        # 步骤进度
        step_frame = ttk.LabelFrame(main_frame, text="执行进度", padding="5")
        step_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.step_label = ttk.Label(
            step_frame, 
            text="步骤: 0 / 100", 
            font=('Arial', 11)
        )
        self.step_label.grid(row=0, column=0, sticky=tk.W)
        
        # 进度条
        self.progress_bar = ttk.Progressbar(
            step_frame, 
            length=450, 
            mode='determinate'
        )
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # 当前命令
        command_frame = ttk.LabelFrame(main_frame, text="当前命令", padding="5")
        command_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.command_label = ttk.Label(
            command_frame, 
            text="等待中...", 
            font=('Courier New', 10),
            foreground='blue',
            wraplength=470
        )
        self.command_label.grid(row=0, column=0, sticky=tk.W)
        
        # 历史记录
        history_frame = ttk.LabelFrame(main_frame, text="命令历史", padding="5")
        history_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.history_text = tk.Text(
            history_frame, 
            height=8, 
            width=50, 
            font=('Courier New', 9),
            wrap=tk.WORD,
            bg='#f0f0f0'
        )
        self.history_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 滚动条
        scrollbar = ttk.Scrollbar(history_frame, command=self.history_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.history_text.config(yscrollcommand=scrollbar.set)
        
        # 配置网格权重
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)
        
        # 启动窗口
        self.window.mainloop()
    
    def update_step(self, current_step, max_steps=None):
        """
        更新步骤进度
        
        Args:
            current_step (int): 当前步骤
            max_steps (int, optional): 最大步数
        """
        if not self.window or not self.is_running:
            return
            
        if max_steps:
            self.max_steps = max_steps
            
        try:
            self.step_label.config(text=f"步骤: {current_step} / {self.max_steps}")
            progress = (current_step / self.max_steps) * 100
            self.progress_bar['value'] = progress
            self.window.update()
        except Exception as e:
            print(f"更新步骤失败: {e}")
    
    def update_command(self, command_text):
        """
        更新当前执行的命令
        
        Args:
            command_text (str): 命令描述
        """
        if not self.window or not self.is_running:
            return
            
        try:
            # 截断过长的文本
            if len(command_text) > 150:
                command_text = command_text[:150] + "..."
            
            self.command_label.config(text=command_text)
            self.window.update()
        except Exception as e:
            print(f"更新命令失败: {e}")
    
    def add_history(self, step, command):
        """
        添加命令到历史记录
        
        Args:
            step (int): 步骤编号
            command (str): 命令描述
        """
        if not self.window or not self.is_running:
            return
            
        try:
            # 截断过长的命令
            if len(command) > 100:
                command = command[:100] + "..."
            
            history_entry = f"[步骤{step}] {command}\n"
            self.history_text.insert(tk.END, history_entry)
            self.history_text.see(tk.END)  # 自动滚动到底部
            self.window.update()
        except Exception as e:
            print(f"添加历史失败: {e}")
    
    def set_status(self, status_text, color='blue'):
        """
        设置状态文本
        
        Args:
            status_text (str): 状态描述
            color (str): 文本颜色
        """
        if not self.window or not self.is_running:
            return
            
        try:
            self.command_label.config(text=status_text, foreground=color)
            self.window.update()
        except Exception as e:
            print(f"设置状态失败: {e}")
    
    def close(self):
        """关闭窗口"""
        self.is_running = False
        if self.window:
            try:
                self.window.quit()
                self.window.destroy()
            except Exception:
                pass


# ==================== 历史对话管理类 ====================

class Messages:
    """
    历史对话管理类
    
    用于管理AI代理与用户之间的对话历史，支持文本和图片消息。
    该类维护了一个消息列表，包含系统提示词、用户消息和助手回复。
    """
    
    def __init__(self, user_query, computer_use_instance=None):
        """
        初始化历史对话管理对象
        
        Args:
            user_query (str): 用户的初始查询或任务描述
            computer_use_instance: ComputerUse工具实例（可选）
        """
        # 如果提供了NousFnCallPrompt且提供了computer_use实例，使用预处理的消息格式
        if NousFnCallPrompt and computer_use_instance:
            # 创建系统消息，定义AI助手的行为规范
            system_message = NousFnCallPrompt().preprocess_fncall_messages(
                messages=[
                    Message(role="system", content=[ContentItem(text='''
You MUST respond using the following format with XML tags:

<tool_call>
{"name": "computer_use", "arguments": {"action": "action_name", ...}}
</tool_call>

CRITICAL - Valid action names (DO NOT use any other names):
- left_click (NOT "click")
- right_click
- middle_click
- double_click
- triple_click
- mouse_move
- left_click_drag
- scroll
- hscroll
- key
- type
- wait
- terminate
- answer

❌ NEVER USE THESE INVALID NAMES:
- "click" - MUST use "left_click" instead
- "press" - MUST use "key" instead
- "input" - MUST use "type" instead
- Any other action name not in the valid list above

PARAMETER REQUIREMENTS:
- For clicking: {"action": "left_click", "coordinate": [x, y]} - NEVER use "click"
- For typing: {"action": "type", "text": "your text"}
- For key press: {"action": "key", "keys": ["enter"]} - MUST use "keys" array, not "text"
- For key combination: {"action": "key", "keys": ["ctrl", "t"]} - Press ctrl+t
- Special keys: enter, tab, esc, space, backspace, delete, up, down, left, right, ctrl, alt, shift, cmd, f5

IMPORTANT KEYBOARD SHORTCUTS (Use these instead of mouse clicks when possible):

WINDOWS SHORTCUTS:
- Open Start Menu: {"action": "key", "keys": ["cmd"]} (Windows key alone)
- Search/Cortana: {"action": "key", "keys": ["cmd", "s"]}
- File Explorer: {"action": "key", "keys": ["cmd", "e"]}
- Lock screen: {"action": "key", "keys": ["cmd", "l"]}
- Switch apps: {"action": "key", "keys": ["alt", "tab"]}
- Close window: {"action": "key", "keys": ["alt", "f4"]}
- Task Manager: {"action": "key", "keys": ["ctrl", "shift", "esc"]}
- Screenshot area: {"action": "key", "keys": ["cmd", "shift", "s"]}
- Open Browser: {"action": "key", "keys": ["cmd", "1"]} (Win+1 快捷键打开浏览器)
- Open WeChat: {"action": "key", "keys": ["cmd", "2"]} (Win+2 快捷键打开微信)

TEXT EDITING:
- Select all: {"action": "key", "keys": ["ctrl", "a"]}
- Copy: {"action": "key", "keys": ["ctrl", "c"]}
- Cut: {"action": "key", "keys": ["ctrl", "x"]}
- Paste: {"action": "key", "keys": ["ctrl", "v"]}
- Undo: {"action": "key", "keys": ["ctrl", "z"]}
- Redo: {"action": "key", "keys": ["ctrl", "y"]}
- Save: {"action": "key", "keys": ["ctrl", "s"]}

EFFICIENCY TIPS:
- Use keyboard shortcuts whenever possible - they are faster than clicking
- For browser tasks, prefer ctrl+t over clicking "New Tab" button
- Use enter key to confirm instead of clicking OK buttons

CRITICAL - OPERATION VERIFICATION (MUST FOLLOW):
1. ALWAYS verify the previous operation completed successfully before proceeding
2. Look at the screenshot carefully - check if the expected result is visible
3. If you just opened an application, WAIT 2-3 seconds for it to fully load before interacting
4. Common mistakes to AVOID:
   - DON'T type a URL before the browser is fully opened
   - DON'T click inside a window that hasn't appeared yet
   - DON'T assume an app started instantly - use wait action if needed
   - DON'T proceed if you see the screen hasn't changed from your last action

5. Verification checklist BEFORE each action:
   ✓ Is the target application/window visible on screen?
   ✓ Is the target element (button, textbox, icon) visible?
   ✓ Did the previous action complete (e.g., page loaded, window opened)?
   ✓ If uncertain, use wait action: {"action": "wait", "time": 2}

6. Example correct sequence for "open browser and search":
   Step 1: Click browser icon -> WAIT to see browser window
   Step 2: Verify browser is open on screen -> Click address bar or use ctrl+l
   Step 3: Verify cursor is in address bar -> Type URL
   Step 4: Verify text is entered -> Press enter
   Step 5: Verify page is loading -> Wait for page to load
   
   WRONG sequence: Click browser -> Immediately type URL (browser not open yet!)

7. If screen shows no change after your action:
   - Use wait action to allow time for the change
   - Re-evaluate if your action was correct
   - Check if you need to click a different location

NEVER respond with raw JSON. Always use the XML tags. Failure to follow this format will result in errors.
''')]),
                ],
                functions=[computer_use_instance.function],
                lang="zh",
            )
            
            # 获取第一个系统消息并转换为字典格式
            system_message = system_message[0].model_dump()
            
            # 初始化消息列表：包含系统提示词和用户查询
            self.messages = [
                {
                    "role": "system",
                    "content": [
                        {"type": "text", "text": msg["text"]} for msg in system_message["content"]
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_query},
                    ],
                }
            ]
        else:
            # 简化版本：直接创建基本的消息结构
            self.messages = [
                {
                    "role": "system",
                    "content": [
                        {"type": "text", "text": '''
You MUST respond using the following format with XML tags:

<tool_call>
{"name": "computer_use", "arguments": {"action": "action_name", ...}}
</tool_call>

CRITICAL - Valid action names (DO NOT use any other names):
- left_click (NOT "click")
- right_click
- middle_click
- double_click
- triple_click
- mouse_move
- left_click_drag
- scroll
- hscroll
- key
- type
- wait
- terminate
- answer

❌ NEVER USE THESE INVALID NAMES:
- "click" - MUST use "left_click" instead
- "press" - MUST use "key" instead
- "input" - MUST use "type" instead
- Any other action name not in the valid list above

PARAMETER REQUIREMENTS:
- For clicking: {"action": "left_click", "coordinate": [x, y]} - NEVER use "click"
- For typing: {"action": "type", "text": "your text"}
- For key press: {"action": "key", "keys": ["enter"]} - MUST use "keys" array, not "text"
- For key combination: {"action": "key", "keys": ["ctrl", "t"]} - Press ctrl+t
- Special keys: enter, tab, esc, space, backspace, delete, up, down, left, right, ctrl, alt, shift, cmd, f5

IMPORTANT KEYBOARD SHORTCUTS (Use these instead of mouse clicks when possible):

WINDOWS SHORTCUTS:
- Open Start Menu: {"action": "key", "keys": ["cmd"]} (Windows key alone)
- Search/Cortana: {"action": "key", "keys": ["cmd", "s"]}
- File Explorer: {"action": "key", "keys": ["cmd", "e"]}
- Lock screen: {"action": "key", "keys": ["cmd", "l"]}
- Switch apps: {"action": "key", "keys": ["alt", "tab"]}
- Close window: {"action": "key", "keys": ["alt", "f4"]}
- Task Manager: {"action": "key", "keys": ["ctrl", "shift", "esc"]}
- Screenshot area: {"action": "key", "keys": ["cmd", "shift", "s"]}
- Open Browser: {"action": "key", "keys": ["cmd", "1"]} (Win+1 快捷键打开浏览器)
- Open WeChat: {"action": "key", "keys": ["cmd", "2"]} (Win+2 快捷键打开微信)







NEVER respond with raw JSON. Always use the XML tags. Failure to follow this format will result in errors.
'''}
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_query},
                    ],
                }
            ]
        
        # 打印初始化的消息（用于调试）
        print(self.messages)
    
    def add_image_message(self, image_path):
        """
        将图片消息添加到历史对话中
        
        该函数将图片文件编码为base64格式，并添加到用户消息内容中。
        支持常见的图片格式：png, jpg, jpeg, webp
        
        Args:
            image_path (str): 图片文件的路径
        """
        # 获取图片文件扩展名并转换为小写
        ext = Path(image_path).suffix.lower()
        
        # MIME类型映射字典：将文件扩展名映射到对应的MIME类型
        mime_type = {
            '.png': 'png',
            '.jpg': 'jpeg',
            '.jpeg': 'jpeg',
            '.webp': 'webp'
        }.get(ext, 'png')  # 默认为 png
        
        # 打开图片文件并编码为base64格式
        with open(image_path, "rb") as img_file:
            base64_data = base64.b64encode(img_file.read()).decode('utf-8')
        
        # 将编码后的图片添加到消息列表中
        self.messages.append({
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{mime_type};base64,{base64_data}"
                    }
                },
                {"type": "text", "text": "当前完成的操作后的屏幕"},
            ],
        })
    
    def add_qwen_response(self, qwen_response):
        """
        将Qwen模型的回复添加到历史对话中
        
        Args:
            qwen_response (str): Qwen模型生成的回复文本
        """
        self.messages.append({
            "role": "assistant",
            "content": [
                {"type": "text", "text": qwen_response},
            ],
        })


# ==================== Qwen3-VL API调用函数 ====================

def get_qwen3_vl_action(messages, model_id, min_pixels=3136, max_pixels=1284505, 
                        display_width=1000, display_height=1000, 
                        screen_width=1728, screen_height=1728):
    """
    调用Qwen3-VL模型获取操作指令
    
    该函数将消息发送到Qwen3-VL API，解析返回的action指令，
    并将相对坐标转换为绝对坐标，最后返回可执行的操作信息。
    
    工作流程：
    1. 初始化OpenAI客户端（从环境变量获取API密钥）
    2. 创建ComputerUse工具实例
    3. 调用Qwen3-VL API获取模型响应
    4. 解析返回的XML格式的tool_call指令
    5. 将相对坐标转换为绝对坐标（针对点击操作）
    6. 返回可执行的操作信息
    
    Args:
        messages (list): 消息列表，包含历史对话和截图
        model_id (str): 模型ID，例如 "qwen-vl-max" 或 "qwen-vl-plus"
        min_pixels (int): 图片最小像素数，默认3136
        max_pixels (int): 图片最大像素数，默认1284505
        display_width (int): 显示区域宽度，默认1000
        display_height (int): 显示区域高度，默认1000
        screen_width (int): 实际屏幕宽度，默认1728
        screen_height (int): 实际屏幕高度，默认1728
        
    Returns:
        tuple: 返回三元组 (output_text, action, computerUse)
            - output_text (str): 模型返回的完整文本
            - action (dict): 解析后的操作指令字典
            - computerUse (ComputerUse): ComputerUse工具实例
            
    Raises:
        ValueError: 当无法解析action指令时
        KeyError: 当返回的数据格式不正确时
        
    示例返回的action格式:
        {
            "name": "computer_use",
            "arguments": {
                "action": "left_click",
                "coordinate": [864, 864]  # 绝对坐标
            }
        }
    """
    
    # ==================== 1. 初始化OpenAI客户端 ====================
    # 从环境变量中获取API密钥和基础URL
    # 需要设置环境变量: DASHSCOPE_API_KEY 和 DASHSCOPE_URL
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url=os.getenv("DASHSCOPE_URL")
    )
    
    # ==================== 2. 初始化显示屏对象 ====================
    # 创建ComputerUse实例，用于后续执行操作
    # 这里的宽高是模型理解的显示区域大小，不是实际屏幕尺寸
    computerUse = ComputerUse(
        cfg={"display_width_px": display_width, "display_height_px": display_height}
    )
    
    # ==================== 3. 调用API获取模型响应 ====================
    # 使用OpenAI兼容的API调用Qwen3-VL模型
    # messages应该包含系统提示、用户查询和截图
    completion = client.chat.completions.create(
        model=model_id,
        messages=messages,
    )
    
    # ==================== 4. 提取输出文本 ====================
    # 从API响应中提取模型生成的文本内容
    output_text = completion.choices[0].message.content
    print(output_text)
    
    # ==================== 5. 解析action指令 ====================
    # 从输出文本中提取XML标签内的JSON格式action
    # 格式示例: <tool_call>\n{"name": "computer_use", "arguments": {...}}\n</tool_call>
    try:
        action = json.loads(output_text.split('<tool_call>\n')[1].split('\n</tool_call>')[0])
    except (IndexError, json.JSONDecodeError) as e:
        print(f"解析action失败: {e}")
        print(f"原始输出: {output_text}")
        raise ValueError(f"无法从模型输出中解析action指令: {e}")
    
    # ==================== 6. 处理点击操作的坐标转换 ====================
    # 检查是否为需要坐标的点击操作
    if action["arguments"]["action"] in ["left_click", "right_click", "middle_click", 
                                          "double_click", "triple_click"]:
        # 获取相对坐标（模型返回的是相对于display_width/height的坐标）
        coordinate_relative = action['arguments']['coordinate']
        
        # 将相对坐标转换为绝对像素坐标
        # 公式: 绝对坐标 = (相对坐标 / display_size) * screen_size
        coordinate_absolute = [
            int(coordinate_relative[0] / display_width * screen_width),   # X坐标转换
            int(coordinate_relative[1] / display_height * screen_height)  # Y坐标转换
        ]
        
        print(f"坐标转换: 相对坐标 {coordinate_relative} -> 绝对坐标 {coordinate_absolute}")
        
        # 更新action中的坐标为绝对坐标
        action['arguments']['coordinate'] = coordinate_absolute
    
    # ==================== 7. 返回结果 ====================
    # 返回输出文本、处理后的action和computerUse实例
    return output_text, action, computerUse


# ==================== 主执行函数 ====================

def main():
    """
    主函数：交互式AI代理执行程序
    
    该函数实现了完整的用户交互流程：
    1. 接收用户输入的任务指令
    2. 循环执行直到任务完成
    3. 支持截图、API调用、操作执行
    """
    
    print("=" * 60)
    print("🤖 Qwen3-VL 计算机控制代理")
    print("=" * 60)
    
    # 显示配置加载状态
    if CONFIG_LOADED:
        print("✅ 已从 config.py 加载配置")
    else:
        print("⚠️  未找到 config.py，使用默认配置")
    
    # ==================== 环境检查 ====================
    # 优先从配置文件读取，然后是环境变量，最后提示用户输入
    api_key = DASHSCOPE_API_KEY or os.getenv("DASHSCOPE_API_KEY")
    base_url = DASHSCOPE_URL or os.getenv("DASHSCOPE_URL")
    
    # 如果环境变量未设置，提示用户手动输入
    if not api_key:
        print("\n⚠️  未检测到 DASHSCOPE_API_KEY 环境变量")
        api_key = input("请输入你的 API Key: ").strip()
        if not api_key:
            print("❌ 错误：API Key 不能为空")
            return
    
    if not base_url:
        print("\n⚠️  未检测到 DASHSCOPE_URL 环境变量")
        default_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        base_url = input(f"请输入 API URL（直接回车使用默认: {default_url}）: ").strip()
        if not base_url:
            base_url = default_url
    
    # 设置环境变量（供API调用使用）
    os.environ["DASHSCOPE_API_KEY"] = api_key
    os.environ["DASHSCOPE_URL"] = base_url
    
    print(f"\n✅ API配置已加载")
    print(f"   API Key: {api_key[:20]}...{api_key[-10:]}")
    print(f"   Base URL: {base_url}")
    
    # ==================== 获取用户输入 ====================
    print("\n" + "=" * 60)
    user_query = input("📝 请输入你的任务指令（例如：帮我打开浏览器）: ").strip()
    
    if not user_query:
        print("❌ 错误：任务指令不能为空")
        return
    
    print(f"\n✅ 任务指令: {user_query}")
    
    # ==================== 配置参数 ====================
    # 直接使用默认模型，不再选择
    model_id = DEFAULT_MODEL
    print(f"\n✅ 使用模型: {model_id}")
    
    # 显示区域尺寸（从配置文件读取）
    display_width = DISPLAY_WIDTH
    display_height = DISPLAY_HEIGHT
    
    # 实际屏幕尺寸（从配置文件读取）
    screen_width = SCREEN_WIDTH
    screen_height = SCREEN_HEIGHT
    
    print(f"\n📐 显示配置:")
    print(f"   模型显示区域: {display_width}x{display_height}")
    print(f"   实际屏幕尺寸: {screen_width}x{screen_height}")
    print(f"   (可在 config.py 中修改)")
    
    # ==================== 初始化对象 ====================
    print("\n" + "=" * 60)
    print("🔧 初始化系统...")
    
    # 创建ComputerUse工具实例
    computer_use = ComputerUse(
        cfg={"display_width_px": display_width, "display_height_px": display_height}
    )
    print("✅ ComputerUse工具已创建")
    
    # 创建历史对话管理对象
    messages = Messages(user_query=user_query, computer_use_instance=computer_use)
    print("✅ 消息管理器已创建")
    
    # ==================== 自动截图 ====================
    print("\n" + "=" * 60)
    print("📷 正在自动截取屏幕...")
    
    # 创建临时文件保存截图
    screenshot_path = os.path.join(tempfile.gettempdir(), "qwen_screenshot.png")
    
    # 自动截取全屏
    screenshot = pyautogui.screenshot()
    screenshot.save(screenshot_path)
    print(f"✅ 截图已保存: {screenshot_path}")
    
    # 添加截图到消息
    messages.add_image_message(screenshot_path)
    print("✅ 截图已添加到对话")
    
    # ==================== 创建状态窗口 ====================
    print("\n" + "=" * 60)
    print("📊 启动状态监控窗口...")
    status_window = StatusWindow()
    status_window.start(max_steps=MAX_STEPS, user_query=user_query)
    print("✅ 状态窗口已启动（右上角）")
    
    # ==================== 执行循环 ====================
    print("\n" + "=" * 60)
    print("🚀 开始执行任务...")
    print("=" * 60)
    
    step = 1
    max_steps = MAX_STEPS  # 从配置文件读取最大执行步数
    
    while step <= max_steps:
        print(f"\n【第 {step} 步】")
        print("-" * 60)
        
        # 更新状态窗口：当前步骤
        status_window.update_step(step, max_steps)
        
        try:
            # 调用API获取操作指令
            print("📡 正在调用Qwen3-VL API...")
            status_window.update_command("📡 正在调用Qwen3-VL API分析屏幕...")
            
            output_text, action, computer_use_obj = get_qwen3_vl_action(
                messages=messages.messages,
                model_id=model_id,
                display_width=display_width,
                display_height=display_height,
                screen_width=screen_width,
                screen_height=screen_height
            )
            
            print(f"\n💭 AI回复: {output_text}")
            print(f"\n🎯 操作指令: {json.dumps(action, indent=2, ensure_ascii=False)}")
            
            # 添加AI回复到历史对话
            messages.add_qwen_response(output_text)
            
            # 生成命令描述
            action_name = action["arguments"]["action"]
            command_desc = f"{action_name}"
            if "coordinate" in action["arguments"]:
                coord = action["arguments"]["coordinate"]
                command_desc += f" at ({coord[0]}, {coord[1]})"
            elif "text" in action["arguments"]:
                text = action["arguments"]["text"][:30]
                command_desc += f": {text}..."
            elif "keys" in action["arguments"]:
                command_desc += f": {action['arguments']['keys']}"
            elif "pixels" in action["arguments"]:
                command_desc += f": {action['arguments']['pixels']}px"
            
            # 检查是否终止
            if action["arguments"]["action"] == "terminate":
                status = action["arguments"].get("status", "unknown")
                print(f"\n✅ 任务已终止，状态: {status}")
                status_window.set_status(f"✅ 任务完成: {status}", 'green')
                status_window.add_history(step, f"terminate ({status})")
                break
            
            # 检查是否为answer（只回答问题，不执行操作）
            if action["arguments"]["action"] == "answer":
                answer_text = action["arguments"].get("text", "")
                print(f"\n💬 回答: {answer_text}")
                status_window.set_status(f"💬 回答问题", 'green')
                status_window.add_history(step, f"answer: {answer_text[:50]}")
                break
            
            # 更新状态窗口：正在执行
            status_window.update_command(f"⚙️ 执行: {command_desc}")
            
            # 执行操作
            print(f"\n⚙️  正在执行操作...")
            result = computer_use_obj.call(action["arguments"])
            print(f"✅ 执行结果: {result}")
            
            # 添加到历史记录
            status_window.add_history(step, command_desc)
            
            # 等待一下让操作生效
            print("⏳ 等待操作生效...")
            time.sleep(2)
            
            # 自动截取新的屏幕截图
            print("📷 正在截取新的屏幕...")
            screenshot = pyautogui.screenshot()
            screenshot.save(screenshot_path)
            messages.add_image_message(screenshot_path)
            print("✅ 已更新截图")
            
            step += 1
            print(f"\n{'='*60}")
            print(f"准备执行第 {step} 步...")
            print(f"{'='*60}")
            
        except Exception as e:
            print(f"\n❌ 执行出错: {e}")
            status_window.set_status(f"❌ 错误: {str(e)[:50]}", 'red')
            status_window.add_history(step, f"ERROR: {str(e)[:50]}")
            import traceback
            traceback.print_exc()
            break
    
    if step > max_steps:
        print(f"\n⚠️  达到最大执行步数({max_steps})，自动终止")
        status_window.set_status(f"⚠️ 达到最大步数限制", 'orange')
    
    print("\n" + "=" * 60)
    print("🎉 程序执行完毕")
    print("=" * 60)
    
    # 保持状态窗口显示5秒后关闭
    print("\n状态窗口将在5秒后关闭...")
    time.sleep(5)
    status_window.close()


# ==================== 使用示例和文档 ====================
"""
📚 使用说明

1. 设置环境变量（Windows PowerShell）:
   $env:DASHSCOPE_API_KEY="your_api_key_here"
   $env:DASHSCOPE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"

2. 运行程序:
   python "agent_function_call - 副本.py"

3. 按提示输入:
   - 任务指令（例如：帮我打开浏览器）
   - 模型ID（默认：qwen-vl-max）
   - 是否需要截图
   - 截图路径（如果需要）

4. 程序会自动:
   - 调用API获取操作指令
   - 解析并转换坐标
   - 执行计算机操作
   - 显示执行结果
   - 询问是否继续

5. 支持的操作类型:
   - 鼠标点击：left_click, right_click, middle_click, double_click, triple_click
   - 鼠标移动：mouse_move, left_click_drag
   - 滚动：scroll, hscroll
   - 键盘：key, type
   - 控制：wait, terminate, answer

6. 示例任务:
   - "帮我打开记事本"
   - "点击屏幕中央的按钮"
   - "向下滚动页面"
   - "输入'Hello World'"
   - "等待3秒"

==================== 数据格式说明 ====================

模型返回格式:
'''
我将点击浏览器图标。

<tool_call>
{"name": "computer_use", "arguments": {"action": "left_click", "coordinate": [500, 300]}}
</tool_call>
'''

解析后的action格式:
{
    "name": "computer_use",
    "arguments": {
        "action": "left_click",
        "coordinate": [960, 324]  # 已转换为绝对坐标
    }
}
"""


# ==================== 程序入口 ====================
if __name__ == "__main__":
    main()
