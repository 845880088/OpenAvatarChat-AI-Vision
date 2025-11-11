# OpenAvatarChat 主程序入口
# 功能：启动数字人对话系统，提供Web界面和API服务

# === 核心引擎导入 ===
from chat_engine.chat_engine import ChatEngine  # 对话引擎：协调所有处理器（ASR、LLM、TTS、Avatar等）

# === Web界面和服务框架 ===
import gradio as gr      # Gradio：快速构建AI应用的Web界面
import gradio           # Gradio应用挂载
import uvicorn          # ASGI服务器：运行FastAPI应用
from fastapi import FastAPI                    # FastAPI：现代高性能的Python Web框架
from fastapi.responses import RedirectResponse # HTTP重定向响应

# === 系统和工具库 ===
import os          # 操作系统接口
import argparse    # 命令行参数解析
import sys         # Python系统相关功能
from loguru import logger  # 日志记录器

# === 项目内部工具模块 ===
from engine_utils.directory_info import DirectoryInfo           # 项目目录管理工具
from service.service_utils.logger_utils import config_loggers   # 日志配置工具
from service.service_utils.service_config_loader import load_configs  # 配置文件加载器
from service.service_utils.ssl_helpers import create_ssl_context      # SSL证书配置工具

# === 项目路径设置 ===
project_dir = DirectoryInfo.get_project_dir()  # 获取项目根目录路径
if project_dir not in sys.path:                # 如果项目目录不在Python路径中
    sys.path.insert(0, project_dir)            # 将项目目录添加到Python路径首位，确保能导入项目模块


def parse_args():
    """
    解析命令行参数
    
    支持的参数：
    --host: 服务器监听地址 (如 127.0.0.1 或 0.0.0.0)
    --port: 服务器端口号 (如 7860)
    --config: 配置文件路径 (默认: config/glut.yaml)
    --env: 配置环境名称 (默认: default)
    
    返回：解析后的参数对象
    """
    parser = argparse.ArgumentParser(description="OpenAvatarChat 数字人对话系统")
    parser.add_argument("--host", type=str, help="服务器监听地址")
    parser.add_argument("--port", type=int, help="服务器端口号")
    parser.add_argument("--config", type=str, default="config/glut.yaml", help="配置文件路径")
    parser.add_argument("--env", type=str, default="default", help="配置环境名称")
    return parser.parse_args()

# === PyTorch 兼容性补丁 ===
import torch
_original_torch_load = torch.load  # 保存原始的torch.load函数

def patched_torch_load(*args, **kwargs):
    """
    PyTorch兼容性补丁函数
    
    作用：解决新版PyTorch的weights_only参数问题
    - 新版PyTorch要求明确指定weights_only参数
    - 为了兼容旧模型文件，这里设置weights_only=False
    - 允许加载包含Python对象的模型文件（如优化器状态等）
    """
    if 'weights_only' not in kwargs or kwargs['weights_only'] != True:
        kwargs['weights_only'] = False  # 允许加载非纯权重的模型文件
    return _original_torch_load(*args, **kwargs)

torch.load = patched_torch_load  # 用补丁函数替换原始的torch.load

class OpenAvatarChatWebServer(uvicorn.Server):
    """
    OpenAvatarChat自定义Web服务器
    
    继承自uvicorn.Server，添加了优雅关闭功能
    确保在服务器停止时正确清理ChatEngine资源
    """

    def __init__(self, chat_engine: ChatEngine, *args, **kwargs):
        """
        初始化Web服务器
        
        参数：
        chat_engine: ChatEngine实例，负责处理对话逻辑
        *args, **kwargs: 传递给uvicorn.Server的其他参数
        """
        super().__init__(*args, **kwargs)
        self.chat_engine = chat_engine  # 保存ChatEngine引用
    
    async def shutdown(self, sockets=None):
        """
        优雅关闭服务器
        
        关闭顺序：
        1. 记录关闭日志
        2. 调用ChatEngine的shutdown方法清理资源
        3. 调用父类的shutdown方法关闭服务器
        """
        logger.info("Start normal shutdown process")
        self.chat_engine.shutdown()        # 先关闭ChatEngine，清理所有处理器
        await super().shutdown(sockets)    # 再关闭Web服务器


def setup_demo():
    """
    设置演示应用程序的Web界面
    
    功能：
    1. 创建FastAPI应用实例
    2. 设置Gradio界面样式（响应式设计、隐藏footer）
    3. 创建WebRTC容器用于视频通话
    4. 将Gradio界面挂载到FastAPI应用
    
    返回：
    app: FastAPI应用实例
    gradio_block: Gradio界面块
    rtc_container: WebRTC容器（用于后续添加视频通话组件）
    """
    app = FastAPI()  # 创建FastAPI应用实例
    
    # === 添加AI代理自动化API路由 ===
    from fastapi import WebSocket
    from service.agent_automation_service import agent_service
    
    @app.post("/api/agent/start")
    async def start_agent_task(request: dict):
        """启动AI代理任务"""
        try:
            task = request.get("task", "").strip()
            if not task:
                return {"success": False, "error": "任务指令不能为空"}
            
            task_id = agent_service.create_task(task)
            return {"success": True, "task_id": task_id}
        except Exception as e:
            logger.error(f"启动AI代理任务失败: {e}")
            return {"success": False, "error": str(e)}
    
    @app.post("/api/agent/stop")
    async def stop_agent_task(request: dict):
        """停止AI代理任务"""
        try:
            task_id = request.get("task_id", "")
            if not task_id:
                return {"success": False, "error": "任务ID不能为空"}
            
            success = agent_service.stop_task(task_id)
            return {"success": success}
        except Exception as e:
            logger.error(f"停止AI代理任务失败: {e}")
            return {"success": False, "error": str(e)}
    
    @app.websocket("/ws/agent/{task_id}")
    async def agent_websocket(websocket: WebSocket, task_id: str):
        """AI代理任务WebSocket连接"""
        await agent_service.handle_websocket(websocket, task_id)

    # === CSS样式定义 ===
    css = """
    /* 响应式设计：在小屏幕设备上减少内边距 */
    .app {
        @media screen and (max-width: 768px) {
            padding: 8px !important;
        }
    }
    /* 隐藏Gradio默认的footer */
    footer {
        display: none !important;
    }
    """
    
    # === 创建Gradio界面 ===
    with gr.Blocks(css=css) as gradio_block:  # 创建带自定义CSS的Gradio界面
        with gr.Column():                     # 垂直布局容器
            with gr.Group() as rtc_container: # WebRTC容器组，用于后续添加视频通话组件
                pass                          # 暂时为空，ChatEngine初始化时会填充内容
    
    # === 挂载Gradio到FastAPI ===
    gradio.mount_gradio_app(app, gradio_block, "/gradio")  # 将Gradio界面挂载到 /gradio 路径
    
    # === 配置前端静态文件服务 ===
    try:
        from static_config import setup_static_files
        app = setup_static_files(app, project_dir)
    except ImportError:
        logger.info("静态文件配置模块未找到，跳过前端服务配置")
    
    return app, gradio_block, rtc_container


def main():
    """
    主函数：OpenAvatarChat应用程序入口点
    
    执行流程：
    1. 解析命令行参数
    2. 加载配置文件（日志、服务、引擎配置）
    3. 设置ModelScope模型缓存路径
    4. 配置日志系统
    5. 创建ChatEngine和Web界面
    6. 初始化ChatEngine（加载所有处理器）
    7. 配置SSL证书
    8. 启动Web服务器
    """
    # === 1. 解析命令行参数 ===
    args = parse_args()
    
    # === 2. 加载配置文件 ===
    logger_config, service_config, engine_config = load_configs(args)
    # logger_config: 日志配置（级别、格式等）
    # service_config: 服务配置（主机、端口、SSL等）
    # engine_config: 引擎配置（处理器、模型路径等）

    # === 3. 设置ModelScope模型缓存路径 ===
    # 如果模型路径不是绝对路径，设置ModelScope缓存目录
    if not os.path.isabs(engine_config.model_root):
        os.environ['MODELSCOPE_CACHE'] = os.path.join(
            DirectoryInfo.get_project_dir(),
            engine_config.model_root.replace('models', '')
        )

    # === 4. 配置日志系统 ===
    config_loggers(logger_config)
    
    # === 5. 创建核心组件 ===
    chat_engine = ChatEngine()                    # 创建对话引擎
    demo_app, ui, parent_block = setup_demo()     # 创建Web应用和界面

    # === 6. 初始化ChatEngine ===
    # 根据配置加载所有处理器：Client、VAD、ASR、LLM、TTS、Avatar
    chat_engine.initialize(engine_config, app=demo_app, ui=ui, parent_block=parent_block)

    # === 7. 配置SSL证书 ===
    ssl_context = create_ssl_context(args, service_config)

    # === 8. 启动Web服务器 ===
    uvicorn_config = uvicorn.Config(
        demo_app, 
        host=service_config.host,    # 监听地址
        port=service_config.port,    # 监听端口
        **ssl_context                # SSL配置
    )
    server = OpenAvatarChatWebServer(chat_engine, uvicorn_config)
    server.run()  # 启动服务器（阻塞运行）

    # 注释的代码：使用标准uvicorn.run的方式（无优雅关闭）
    # uvicorn.run(demo_app, host=service_config.host, port=service_config.port, **ssl_context)


if __name__ == "__main__":
    """
    程序入口点
    当直接运行此脚本时执行main函数
    """
    main()
