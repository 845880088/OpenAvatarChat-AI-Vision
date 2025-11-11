# 静态文件服务配置
# 用于在生产环境中通过FastAPI提供前端静态文件

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path

def setup_static_files(app: FastAPI, project_dir: str):
    """
    配置静态文件服务
    
    参数:
    app: FastAPI应用实例
    project_dir: 项目根目录路径
    """
    
    # 静态文件目录路径
    static_dir = Path(project_dir) / "static"
    webui_dir = static_dir / "webui"
    
    # 检查前端文件是否存在
    if webui_dir.exists() and (webui_dir / "index.html").exists():
        print(f"✅ 前端文件发现: {webui_dir}")
        
        # 挂载静态文件目录到 /webui 路径
        app.mount("/webui", StaticFiles(directory=str(webui_dir), html=True), name="webui")
        
        # 根路径重定向到前端
        @app.get("/")
        async def redirect_to_webui():
            """根路径重定向到前端界面"""
            return FileResponse(str(webui_dir / "index.html"))
        
        # 挂载assets到根路径以兼容前端资源引用  
        assets_dir = webui_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
            
        print("✅ 静态文件服务已配置:")
        print(f"   - 前端界面: /webui/ 或 /")
        print(f"   - 静态资源: /webui/assets/")
        print(f"   - 公网访问: https://liao.uunat.com:8282/")
        
    else:
        print("⚠️  前端文件未找到，请运行构建:")
        print("   cd OpenAvatarChat-WebUI && build-and-deploy.bat")
        
    return app
