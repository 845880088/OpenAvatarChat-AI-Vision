# -*- coding: utf-8 -*-
"""
配置文件
请在这里设置你的API配置
"""

# ==================== API配置 ====================
# 请替换为你的完整API Key（从阿里云DashScope获取）
# 推荐做法：在项目根目录创建 .env 文件，然后在其中设置：
# DASHSCOPE_API_KEY=your-api-key-here

import os
from pathlib import Path

# 尝试从 .env 文件加载环境变量
try:
    from dotenv import load_dotenv
    # 查找 .env 文件（从当前目录向上查找到项目根目录）
    current_dir = Path(__file__).parent
    project_root = current_dir.parent  # 项目根目录
    env_file = project_root / ".env"
    
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ 已从 {env_file} 加载环境变量")
    else:
        print(f"⚠️  未找到 .env 文件: {env_file}")
except ImportError:
    print("⚠️  未安装 python-dotenv，将直接从系统环境变量读取")
    print("   提示：运行 'pip install python-dotenv' 可支持 .env 文件")

# 从环境变量读取（不抛出异常，让主程序处理）
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_URL = os.getenv("DASHSCOPE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

# ==================== 模型配置 ====================
# 默认模型（直接使用，不再选择）
DEFAULT_MODEL = "qwen3-vl-plus"  # 固定使用此模型

# 深度思考模式（适用于qwen3-vl-plus、qwen3-vl-flash系列）
ENABLE_THINKING = True  # True=开启思考模式, False=关闭思考模式

# ==================== 屏幕配置 ====================
# 模型理解的显示区域大小
DISPLAY_WIDTH = 1000
DISPLAY_HEIGHT = 1000

# 实际屏幕尺寸（请根据你的屏幕修改）
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

# ==================== 执行配置 ====================
# 最大执行步数
MAX_STEPS = 100

# 自动执行模式（True=自动执行不询问，False=每步都询问）
AUTO_CONTINUE = True

# 每步操作后等待时间（秒）
WAIT_AFTER_ACTION = 2

# 是否显示详细日志
VERBOSE = True


