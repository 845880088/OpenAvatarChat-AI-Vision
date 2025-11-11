# AI 自动化助手使用指南

## 功能简介

AI 自动化助手是集成在 OpenAvatarChat 项目中的一个强大功能，它允许你通过自然语言指令来控制计算机，实现自动化操作。

### 主要特性

- 🤖 **自然语言控制**：用简单的中文描述任务，AI会理解并执行
- 📷 **视觉理解**：AI可以"看到"屏幕内容，智能分析并操作
- ⚡ **实时反馈**：通过WebSocket实时显示执行进度和状态
- 🎯 **精准操作**：支持鼠标点击、键盘输入、滚动等多种操作
- 📊 **状态监控**：实时显示执行步骤、命令历史和AI分析

## 配置步骤

### 1. 配置 API 密钥

编辑 `agent_function_call/config.py` 文件，填入你的 API 配置：

```python
# 阿里云灵积 DashScope API 配置
DASHSCOPE_API_KEY = "sk-your-api-key-here"  # 在这里填入你的API Key
DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 使用的模型（推荐 qwen-vl-max，效果最好）
DEFAULT_MODEL = "qwen-vl-max"

# 显示配置（模型理解的屏幕尺寸）
DISPLAY_WIDTH = 1000
DISPLAY_HEIGHT = 1000

# 实际屏幕分辨率（根据你的屏幕调整）
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

# 最大执行步数（防止无限循环）
MAX_STEPS = 100
```

### 2. 获取 API Key

1. 访问 [阿里云灵积平台](https://dashscope.aliyun.com/)
2. 注册/登录账号
3. 进入控制台，创建 API Key
4. 将 API Key 复制到 `config.py` 中

### 3. 安装依赖

确保已安装必要的 Python 包：

```bash
pip install pyautogui pynput openai qwen-agent
```

## 使用方法

### 方式一：通过 Web 界面使用（推荐）

1. **启动后端服务**
   ```bash
   # 在项目根目录执行
   python src/demo.py --config config/glut.yaml
   ```

2. **启动前端开发服务器**
   ```bash
   cd OpenAvatarChat-WebUI
   npm run dev
   # 或者
   pnpm dev
   ```

3. **打开浏览器**
   - 访问 `http://localhost:5173`（开发环境）
   - 或 `https://127.0.0.1:8282`（生产环境）

4. **使用 AI 助手**
   - 点击右下角的 "🤖 AI 自动化助手" 按钮
   - 在弹出的窗口中输入任务指令
   - 点击 "开始执行" 按钮
   - 实时观察执行进度和状态

### 方式二：通过命令行使用

直接运行 Python 脚本：

```bash
cd agent_function_call
python agent_function_call.py
```

然后按照提示输入任务指令。

## 任务示例

### 基础操作

```
打开记事本
```
AI 会：
1. 识别记事本图标位置
2. 点击打开记事本

```
打开浏览器并搜索 OpenAI
```
AI 会：
1. 打开浏览器
2. 在地址栏输入搜索内容
3. 按下回车执行搜索

### 文档编辑

```
打开记事本，输入 "Hello World"，然后保存到桌面
```

```
打开 Word 文档，输入今天的日期和一段问候语
```

### 系统操作

```
截取当前屏幕并保存
```

```
打开任务管理器，查看 CPU 使用率
```

### 应用程序操作

```
打开微信
```

```
打开 VS Code 并新建一个 Python 文件
```

### 复杂任务

```
帮我在桌面创建一个文件夹，命名为"工作文档"
```

```
打开浏览器，访问 GitHub，搜索 OpenAvatarChat 项目
```

## 界面说明

### Web 界面功能

1. **任务输入区域**
   - 多行文本框：输入你的任务指令
   - 支持换行，可以输入详细的任务描述
   
2. **控制按钮**
   - **开始执行**：启动任务执行
   - **停止执行**：中断正在执行的任务

3. **状态显示区域**
   - **执行状态标签**：显示当前状态（就绪/执行中/完成/失败）
   - **进度条**：显示任务完成百分比
   - **当前步骤**：显示正在执行的操作
   - **执行历史**：显示所有已执行的命令列表

4. **AI 分析区域**
   - 显示 AI 对当前屏幕的分析和决策过程

## 技术原理

### 工作流程

1. **用户输入**：用户通过 Web 界面输入任务指令
2. **任务创建**：后端创建任务实例，分配唯一ID
3. **WebSocket连接**：建立实时通信通道
4. **屏幕截图**：自动截取当前屏幕
5. **AI分析**：调用 Qwen-VL 视觉语言模型分析屏幕
6. **生成操作**：AI 生成具体的操作指令（点击、输入等）
7. **执行操作**：通过 pynput/pyautogui 执行操作
8. **循环反馈**：重复 4-7 步，直到任务完成

### 技术栈

**前端**：
- Vue 3 + TypeScript
- Ant Design Vue（UI组件库）
- WebSocket（实时通信）
- Axios（HTTP请求）

**后端**：
- FastAPI（Web框架）
- Qwen-VL-Max（视觉语言模型）
- pyautogui（屏幕截图）
- pynput（鼠标键盘控制）

## 注意事项

### 安全性

⚠️ **重要警告**：
- AI 助手会真实地控制你的计算机
- 执行前请确保理解任务内容
- 不要在执行关键操作时让 AI 自动执行
- 随时可以点击"停止执行"中断任务

### 最佳实践

1. **任务描述要清晰**
   - ✅ 好：打开记事本，输入 Hello World
   - ❌ 差：做点什么

2. **分步执行复杂任务**
   - ✅ 好：先打开浏览器 → 再搜索内容
   - ❌ 差：一次性执行多个复杂任务

3. **观察执行过程**
   - 注意查看 AI 的分析和决策
   - 如果出现偏差，及时停止

4. **合理设置屏幕分辨率**
   - 在 `config.py` 中设置正确的屏幕分辨率
   - 确保坐标转换准确

### 常见问题

**Q: 为什么 AI 点击位置不准确？**
A: 检查 `config.py` 中的 `SCREEN_WIDTH` 和 `SCREEN_HEIGHT` 是否与实际屏幕分辨率一致。

**Q: 任务执行失败，提示 API Key 错误？**
A: 确保在 `config.py` 中正确配置了 `DASHSCOPE_API_KEY`。

**Q: 可以执行多个任务吗？**
A: 目前一次只能执行一个任务，完成后可以开始新任务。

**Q: 如何提高执行成功率？**
A: 
1. 使用清晰准确的指令
2. 避免在任务执行中移动鼠标
3. 等待应用程序完全加载后再继续

**Q: 支持哪些操作系统？**
A: 支持 Windows、macOS、Linux，但键盘快捷键可能有差异。

## 故障排查

### 问题：无法启动任务

**检查项**：
1. 确认后端服务已启动
2. 检查 API Key 是否配置
3. 查看浏览器控制台错误信息

### 问题：WebSocket 连接失败

**解决方案**：
1. 确认后端服务正常运行
2. 检查防火墙设置
3. 查看后端日志输出

### 问题：执行过程中卡住

**解决方案**：
1. 点击"停止执行"按钮
2. 检查是否有窗口挡住了目标元素
3. 重新描述任务，使用更明确的指令

## 开发扩展

### 自定义操作

你可以在 `agent_function_call.py` 的 `ComputerUse` 类中添加自定义操作：

```python
def _custom_action(self, param1, param2):
    """自定义操作"""
    # 实现你的逻辑
    return "操作完成"
```

### 添加新的 API 端点

在 `src/demo.py` 中添加新的路由：

```python
@app.post("/api/agent/custom")
async def custom_endpoint(request: dict):
    # 实现你的逻辑
    return {"success": True}
```

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

本项目遵循 MIT 许可证。

---

**作者**: 廖伟杰  
**创建时间**: 2025.11.10  
**最后更新**: 2025.11.10

