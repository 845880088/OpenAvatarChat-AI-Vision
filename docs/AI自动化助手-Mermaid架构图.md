# AI自动化助手技术架构 - Mermaid图表

## 1. 整体系统架构（三层架构）

```mermaid
graph TB
    subgraph Frontend["前端交互层"]
        A1[Vue3 + TypeScript]
        A2[WebSocket 实时通信]
        A3[Ant Design Vue 组件]
        A4[用户输入任务指令]
    end
    
    subgraph Backend["后端处理层"]
        B1[FastAPI Web服务]
        B2[Agent任务管理器]
        B3[任务队列与调度]
        B4[API调度与封装]
    end
    
    subgraph AILayer["AI执行层"]
        C1[Qwen-VL-Max 模型]
        C2[Function Calling]
        C3[ComputerUse工具]
        C4[pynput 鼠标键盘控制]
        C5[pyautogui 屏幕截图]
    end
    
    A4 -->|HTTP POST /api/agent/execute| B1
    B1 -->|创建任务实例| B2
    B2 -->|建立连接| A2
    A2 -.->|实时状态推送| A3
    
    B3 -->|截取屏幕| C5
    B3 -->|调用AI分析| C1
    C1 -->|生成| C2
    C2 -->|调用工具| C3
    C3 -->|执行操作| C4
    
    C4 -.->|操作结果| B3
    B3 -.->|WebSocket推送进度| A2
    
    style Frontend fill:#667eea,color:#fff
    style Backend fill:#764ba2,color:#fff
    style AILayer fill:#43e97b,color:#fff
```

## 2. 完整工作流程（10步详细流程）

```mermaid
sequenceDiagram
    participant User as 👤 用户
    participant Frontend as 🌐 前端界面
    participant FastAPI as 📡 FastAPI后端
    participant WebSocket as 🔗 WebSocket
    participant Agent as 🤖 Qwen-Agent
    participant VL as 🧠 Qwen-VL-Max
    participant Tool as 🛠️ ComputerUse工具
    participant System as 🖥️ 操作系统
    
    User->>Frontend: 1. 输入任务指令<br/>"打开浏览器并搜索OpenAI"
    Frontend->>FastAPI: 2. POST /api/agent/execute<br/>{task: "指令"}
    FastAPI->>FastAPI: 3. 创建任务ID<br/>初始化Agent实例
    FastAPI-->>Frontend: 返回task_id
    
    Frontend->>WebSocket: 4. 建立WebSocket连接<br/>ws://localhost:8282/ws/{task_id}
    WebSocket-->>Frontend: 连接成功
    
    loop 循环执行直到任务完成
        Agent->>System: 5. 截取屏幕<br/>pyautogui.screenshot()
        System-->>Agent: 返回屏幕截图
        
        Agent->>Agent: 6. Base64编码<br/>PNG → Base64 → 数据URL
        
        Agent->>VL: 7. 调用AI模型<br/>messages=[{text, image_url}]
        Note over VL: 视觉理解屏幕内容<br/>识别UI元素位置<br/>规划下一步操作
        VL-->>Agent: 返回Function Call<br/>{action, coordinate, text}
        
        Agent->>Tool: 8. 解析并验证参数<br/>坐标映射转换
        Tool->>System: 9. 执行系统操作<br/>鼠标点击/键盘输入
        System-->>Tool: 操作完成
        
        Tool-->>WebSocket: 10. 推送实时状态
        WebSocket-->>Frontend: 更新进度、步骤、分析
        Frontend-->>User: 显示执行进度
        
        alt 任务完成
            Agent->>WebSocket: terminate(status="success")
            WebSocket-->>Frontend: 任务完成通知
        else 继续执行
            Agent->>Agent: 等待2秒后继续
        end
    end
```

## 3. 数据流向图

```mermaid
flowchart LR
    A[用户输入任务] -->|HTTP| B[FastAPI接收]
    B -->|创建| C[任务实例<br/>task_id]
    C -->|建立| D[WebSocket连接]
    
    D -->|触发| E[Agent开始执行]
    E -->|1.截图| F[pyautogui.screenshot]
    F -->|PNG图像| G[Base64编码]
    G -->|数据URL| H[Qwen-VL-Max]
    
    H -->|视觉理解| I{分析结果}
    I -->|生成| J[Function Call JSON]
    J -->|解析| K[参数验证与映射]
    K -->|调用| L[ComputerUse工具]
    
    L -->|执行| M{操作类型}
    M -->|点击| N1[鼠标控制<br/>pynput]
    M -->|输入| N2[键盘控制<br/>pynput]
    M -->|等待| N3[time.sleep]
    
    N1 & N2 & N3 -->|结果| O[操作完成]
    O -->|推送| D
    D -->|实时反馈| P[前端显示]
    
    O -->|检查| Q{任务是否完成?}
    Q -->|否| E
    Q -->|是| R[返回结果]
    
    style A fill:#ffeaa7
    style H fill:#667eea,color:#fff
    style L fill:#764ba2,color:#fff
    style P fill:#43e97b
```

## 4. Qwen-Agent工具注册机制

```mermaid
classDiagram
    class BaseTool {
        <<abstract>>
        +description: str
        +parameters: dict
        +__init__(cfg)
        +call(params)
    }
    
    class ComputerUse {
        -mouse_controller: Controller
        -keyboard_controller: Controller
        -display_width_px: int
        -display_height_px: int
        +description: str
        +parameters: dict
        +call(params)
        -_mouse_click(button, coordinate)
        -_key(keys)
        -_type(text)
        -_mouse_move(coordinate)
        -_scroll(pixels)
        -_wait(time)
        -_terminate(status)
    }
    
    class QwenAgent {
        -tools: List[BaseTool]
        -client: OpenAI
        -messages: List[dict]
        +register_tool(tool)
        +run(user_query)
        -_build_messages()
        -_execute_function_call()
    }
    
    BaseTool <|-- ComputerUse : 继承
    QwenAgent --> ComputerUse : 使用
    
    note for ComputerUse "通过@register_tool('computer_use')<br/>装饰器注册为AI工具"
```

## 5. Function Calling 流程

```mermaid
sequenceDiagram
    participant Agent as Qwen-Agent
    participant API as OpenAI API
    participant VL as Qwen-VL-Max
    participant Tool as ComputerUse工具
    participant System as 操作系统
    
    Agent->>API: 发送请求
    Note over API: messages=[<br/>{text: "打开浏览器"},<br/>{image: "屏幕截图"}<br/>]<br/>tools=[computer_use_tool]
    
    API->>VL: 调用模型推理
    Note over VL: 视觉理解:<br/>识别桌面图标<br/>定位浏览器位置<br/>规划操作步骤
    
    VL-->>API: 返回Function Call
    Note over API: tool_calls=[{<br/>id: "call_123",<br/>function: {<br/>  name: "computer_use",<br/>  arguments: {<br/>    action: "left_click",<br/>    coordinate: [150, 900]<br/>  }<br/>}<br/>}]
    
    API-->>Agent: 返回响应
    
    Agent->>Agent: 解析Function Call
    Agent->>Agent: 验证参数格式
    Agent->>Agent: 坐标映射<br/>(1000x1000 → 1920x1080)
    
    Agent->>Tool: 调用tool.call(params)
    Tool->>System: 执行鼠标点击<br/>position=(288, 972)
    System-->>Tool: 操作成功
    Tool-->>Agent: 返回结果<br/>"Successfully clicked"
    
    Agent->>API: 提交工具执行结果
    Note over API: messages.append({<br/>role: "tool",<br/>content: "Successfully clicked"<br/>})
    
    API->>VL: 继续推理下一步
    Note over VL: 根据操作结果<br/>决定下一步动作
```

## 6. 坐标映射机制

```mermaid
graph LR
    A[AI模型输出<br/>标准坐标系<br/>1000x1000] -->|坐标映射| B{坐标转换公式}
    
    B --> C[actual_x = <br/>ai_x × SCREEN_WIDTH<br/>÷ DISPLAY_WIDTH]
    B --> D[actual_y = <br/>ai_y × SCREEN_HEIGHT<br/>÷ DISPLAY_HEIGHT]
    
    C & D --> E[实际屏幕坐标<br/>1920x1080]
    E --> F[pynput执行操作]
    
    subgraph Config["配置参数"]
        G[DISPLAY_WIDTH = 1000<br/>AI理解的标准宽度]
        H[DISPLAY_HEIGHT = 1000<br/>AI理解的标准高度]
        I[SCREEN_WIDTH = 1920<br/>实际屏幕宽度]
        J[SCREEN_HEIGHT = 1080<br/>实际屏幕高度]
    end
    
    Config -.-> B
    
    style A fill:#667eea,color:#fff
    style E fill:#43e97b
    style Config fill:#ffeaa7
```

## 7. WebSocket实时通信

```mermaid
sequenceDiagram
    participant Frontend as 前端
    participant WS as WebSocket服务器
    participant Agent as Agent执行器
    
    Frontend->>WS: 建立连接<br/>ws://localhost:8282/ws/{task_id}
    WS-->>Frontend: 连接成功
    
    loop 任务执行中
        Agent->>WS: 推送进度更新
        Note over WS: {<br/>  type: "progress",<br/>  value: 30,<br/>  max: 100<br/>}
        WS->>Frontend: 转发消息
        Frontend->>Frontend: 更新进度条
        
        Agent->>WS: 推送当前步骤
        Note over WS: {<br/>  type: "step",<br/>  content: "正在点击浏览器图标"<br/>}
        WS->>Frontend: 转发消息
        Frontend->>Frontend: 显示步骤信息
        
        Agent->>WS: 推送AI分析
        Note over WS: {<br/>  type: "analysis",<br/>  content: "我看到桌面，<br/>浏览器在左下方..."<br/>}
        WS->>Frontend: 转发消息
        Frontend->>Frontend: 显示AI思考
        
        alt 任务完成
            Agent->>WS: 推送完成状态
            Note over WS: {<br/>  type: "complete",<br/>  status: "success"<br/>}
            WS->>Frontend: 转发消息
            Frontend->>Frontend: 显示完成状态
            WS->>Frontend: 关闭连接
        end
    end
```

## 8. 错误处理与恢复机制

```mermaid
flowchart TD
    A[Agent执行操作] --> B{操作是否成功?}
    
    B -->|成功| C[记录操作历史]
    C --> D[继续下一步]
    
    B -->|失败| E{失败类型判断}
    
    E -->|元素未找到| F[AI重新分析<br/>调整坐标]
    F --> G[重试操作<br/>最多3次]
    
    E -->|应用未响应| H[等待5秒]
    H --> I[重新截图分析]
    
    E -->|坐标越界| J[裁剪到屏幕范围]
    J --> G
    
    E -->|权限拒绝| K[报告错误<br/>终止任务]
    
    G --> L{重试是否成功?}
    L -->|是| C
    L -->|否| M{重试次数 < 3?}
    
    M -->|是| N[改变策略<br/>尝试备选方案]
    N --> G
    
    M -->|否| K
    
    I --> D
    
    style B fill:#ffeaa7
    style K fill:#ff6b6b,color:#fff
    style C fill:#43e97b
```

## 9. 技术栈依赖关系

```mermaid
graph TB
    subgraph Frontend["前端技术栈"]
        F1[Vue 3]
        F2[TypeScript]
        F3[Ant Design Vue]
        F4[WebSocket API]
        F5[Axios]
    end
    
    subgraph Backend["后端技术栈"]
        B1[FastAPI]
        B2[Qwen-Agent]
        B3[OpenAI SDK]
        B4[Uvicorn]
        B5[asyncio]
    end
    
    subgraph AI["AI与自动化"]
        A1[Qwen-VL-Max]
        A2[pyautogui]
        A3[pynput]
        A4[Pillow]
        A5[OpenAI API]
    end
    
    F1 --> F2
    F1 --> F3
    F1 --> F4
    F2 --> F5
    
    B1 --> B5
    B2 --> B3
    B2 --> A1
    B4 --> B1
    
    A2 --> A4
    A3 --> A2
    A1 --> A5
    
    Frontend -.->|HTTP/WebSocket| Backend
    Backend -.->|API调用| AI
    
    style Frontend fill:#667eea,color:#fff
    style Backend fill:#764ba2,color:#fff
    style AI fill:#43e97b,color:#fff
```

## 10. 并发控制机制

```mermaid
stateDiagram-v2
    [*] --> 空闲: 系统启动
    
    空闲 --> 检查队列: 接收任务请求
    
    检查队列 --> 拒绝任务: 已有任务执行中
    拒绝任务 --> 空闲: 返回错误信息
    
    检查队列 --> 获取锁: 队列为空
    获取锁 --> 创建任务: 成功获取task_lock
    
    创建任务 --> 执行中: 启动Agent
    
    state 执行中 {
        [*] --> 截图
        截图 --> AI分析
        AI分析 --> 工具调用
        工具调用 --> 系统操作
        系统操作 --> 等待
        等待 --> 检查状态
        
        检查状态 --> 截图: 继续执行
        检查状态 --> [*]: 任务完成
    }
    
    执行中 --> 释放锁: 任务完成或失败
    释放锁 --> 空闲: 删除任务记录
    
    note right of 获取锁
        async with task_lock:
            if active_tasks:
                return error
            active_tasks[id] = task
    end note
```

---

## 使用说明

这些Mermaid图表可以直接在支持Mermaid的Markdown编辑器中渲染，例如：
- GitHub/GitLab
- Typora
- VSCode (安装Mermaid插件)
- Obsidian
- 在线工具：https://mermaid.live/

复制对应的代码块到你的Markdown文件中即可显示图表。

