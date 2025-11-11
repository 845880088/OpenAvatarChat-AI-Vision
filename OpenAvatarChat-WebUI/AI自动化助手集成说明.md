# AI 自动化助手集成说明

## 🎉 功能概述

已成功在 OpenAvatarChat 前端项目中集成 AI 自动化助手功能！

用户现在可以通过 Web 界面直接输入自然语言指令，让 AI 自动控制计算机完成各种任务。

## 📁 新增文件

### 前端文件
- `OpenAvatarChat-WebUI/src/components/AIAgentControl.vue`  
  AI 代理控制组件，提供用户界面

### 后端文件
- `src/service/agent_automation_service.py`  
  AI 代理自动化服务，负责任务管理和执行

### 文档
- `agent_function_call/AI自动化助手使用指南.md`  
  详细的使用指南和故障排查

## 🔧 修改的文件

### 前端
1. **OpenAvatarChat-WebUI/src/App.vue**
   - 导入并添加 `AIAgentControl` 组件
   - 在页面右下角显示浮动按钮

2. **OpenAvatarChat-WebUI/vite.config.ts**
   - 添加 `/api` 路由代理，指向后端服务

### 后端
3. **src/demo.py**
   - 添加三个 API 端点：
     - `POST /api/agent/start` - 启动任务
     - `POST /api/agent/stop` - 停止任务
     - `WebSocket /ws/agent/{task_id}` - 实时状态推送

## 🚀 快速启动

### 前置条件
1. 确保已配置 `agent_function_call/config.py` 中的 API Key
2. 安装必要依赖：`pip install pyautogui pynput`

### 开发环境启动

#### 1. 启动后端
```bash
# 在项目根目录
python src/demo.py --config config/glut.yaml
```

#### 2. 启动前端
```bash
cd OpenAvatarChat-WebUI
pnpm dev  # 或 npm run dev
```

#### 3. 访问界面
打开浏览器访问：`http://localhost:5173`

### 生产环境部署

#### 1. 构建前端
```bash
cd OpenAvatarChat-WebUI
pnpm build
```

#### 2. 更新旧前端位置
```bash
# 运行更新脚本
.\update-old-frontend.bat
```

#### 3. 访问界面
- 本地访问：`https://127.0.0.1:8282/`
- 外部访问：`https://your-domain:8282/`

## 💡 使用方法

1. 打开 Web 界面
2. 点击右下角的 "🤖 AI 自动化助手" 按钮
3. 在弹窗中输入任务指令，例如：
   - "打开记事本"
   - "打开浏览器并搜索 OpenAI"
   - "帮我打开微信"
4. 点击"开始执行"按钮
5. 实时观察执行进度和状态
6. 任务完成后查看结果

## 🎨 界面功能

### 主要区域
- **任务输入框**：输入自然语言指令
- **控制按钮**：开始/停止任务执行
- **状态显示**：实时显示执行进度和当前步骤
- **执行历史**：查看所有已执行的命令
- **AI 分析**：查看 AI 对屏幕的理解和决策

### 实时反馈
- 通过 WebSocket 实时推送执行状态
- 进度条显示任务完成百分比
- 彩色标签区分不同类型的消息（信息/成功/错误/警告）

## 🔌 API 接口

### 1. 启动任务
```http
POST /api/agent/start
Content-Type: application/json

{
  "task": "打开记事本"
}

Response:
{
  "success": true,
  "task_id": "uuid-string"
}
```

### 2. 停止任务
```http
POST /api/agent/stop
Content-Type: application/json

{
  "task_id": "uuid-string"
}

Response:
{
  "success": true
}
```

### 3. WebSocket 连接
```
ws://localhost:8282/ws/agent/{task_id}

消息格式：
{
  "type": "step" | "command" | "ai_response" | "result" | "error" | "complete",
  "step": 1,
  "text": "...",
  ...
}
```

## 🛠️ 技术架构

### 前端技术栈
- Vue 3 + TypeScript + Composition API
- Ant Design Vue 4.x
- WebSocket（原生）
- Axios

### 后端技术栈
- FastAPI（异步 Web 框架）
- Qwen-VL-Max（阿里云灵积视觉语言模型）
- pyautogui（屏幕截图）
- pynput（鼠标键盘控制）
- asyncio（异步任务管理）

### 数据流
```
用户输入 → 前端组件 → HTTP API → 任务创建 → WebSocket 连接
    ↓
AI 分析 ← 屏幕截图 ← 任务执行 ← 实时状态推送 ← WebSocket
```

## ⚙️ 配置说明

### API 配置（必需）
编辑 `agent_function_call/config.py`：

```python
DASHSCOPE_API_KEY = "sk-your-api-key"  # 必填
DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen-vl-max"  # 推荐使用 max 版本
```

### 屏幕分辨率配置
根据实际屏幕调整：

```python
SCREEN_WIDTH = 1920   # 你的屏幕宽度
SCREEN_HEIGHT = 1080  # 你的屏幕高度
```

### 执行限制配置
```python
MAX_STEPS = 100  # 最大执行步数，防止无限循环
```

## 🔒 安全注意事项

⚠️ **重要提示**：
1. AI 助手会真实控制你的计算机
2. 执行前请确保理解任务内容
3. 不建议在生产环境执行未经验证的指令
4. 可随时点击"停止执行"中断任务
5. 建议在虚拟机或测试环境中试用

## 📊 监控和日志

### 前端日志
- 浏览器控制台会显示 WebSocket 连接状态
- 界面上的历史记录区域显示所有操作

### 后端日志
- 使用 loguru 记录所有操作
- 日志位置：项目 `logs/` 目录
- 包含任务创建、执行、错误等信息

## 🐛 故障排查

### 问题：点击按钮无反应
**解决**：
1. 检查浏览器控制台是否有错误
2. 确认后端服务正常运行
3. 检查 API Key 是否配置

### 问题：WebSocket 连接失败
**解决**：
1. 确认后端服务已启动
2. 检查端口 8282 是否被占用
3. 查看防火墙设置

### 问题：任务执行但操作不准确
**解决**：
1. 检查 `config.py` 中的屏幕分辨率设置
2. 使用更明确的任务描述
3. 确保目标窗口可见且未被遮挡

## 📝 开发说明

### 扩展功能
如需添加新功能：

1. **前端**：修改 `AIAgentControl.vue`
2. **后端**：修改 `agent_automation_service.py`
3. **API**：在 `demo.py` 中添加路由

### 自定义操作
在 `agent_function_call.py` 的 `ComputerUse` 类中添加新方法。

### 调试模式
设置环境变量启用详细日志：
```bash
export LOG_LEVEL=DEBUG
```

## 📚 相关文档

- [AI自动化助手使用指南](../agent_function_call/AI自动化助手使用指南.md)
- [agent_function_call.py 源码](../agent_function_call/agent_function_call.py)
- [配置文件说明](../agent_function_call/config.py)

## 🤝 贡献

欢迎提交问题和改进建议！

## 📄 许可证

遵循项目主许可证。

---

**集成完成时间**: 2025.11.10  
**版本**: 1.0.0  
**状态**: ✅ 已完成并测试

