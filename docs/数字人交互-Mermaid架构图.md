# 数字人交互技术架构 - Mermaid图表

## 1. 整体系统架构（四层架构）

```mermaid
graph TB
    subgraph UserDevice["用户设备层 🖥️"]
        U1[📷 摄像头]
        U2[🎤 麦克风]
        U3[🖥️ 屏幕共享]
        U4[🌐 浏览器 Vue3前端]
    end
    
    subgraph Communication["通信层 📡"]
        C1[WebRTC PeerConnection]
        C2[ICE/STUN/TURN]
        C3[媒体流传输]
        C4[轨道管理 replaceTrack]
    end
    
    subgraph Processing["处理层 ⚙️"]
        P1[RTC Client Handler]
        P2[视频帧提取 30fps]
        P3[音频流处理 16kHz]
        P4[Handler流水线]
        P5[VAD → ASR → LLM → TTS → Avatar]
    end
    
    subgraph AIModels["AI模型层 🤖"]
        A1[SenseVoice 语音识别]
        A2[Qwen-VL-Plus 视觉理解]
        A3[CosyVoice 语音合成]
        A4[LiteAvatar 数字人渲染]
    end
    
    U1 & U2 & U3 -->|MediaStream| U4
    U4 -->|WebRTC Offer/Answer| C1
    C1 -->|STUN/TURN穿透| C2
    C2 -->|UDP媒体流| C3
    C3 -->|Track Events| P1
    
    P1 -->|视频帧| P2
    P1 -->|音频流| P3
    P2 & P3 -->|ChatData| P4
    
    P4 -->|音频数据| A1
    P4 -->|视频帧+文本| A2
    A1 & A2 -->|AI响应| P4
    P4 -->|文本| A3
    A3 -->|音频| A4
    A4 -->|数字人视频| C3
    C3 -->|返回用户| U4
    
    style UserDevice fill:#43e97b,color:#fff
    style Communication fill:#38f9d7,color:#fff
    style Processing fill:#667eea,color:#fff
    style AIModels fill:#764ba2,color:#fff
```

## 2. 摄像头视频对话完整流程

```mermaid
sequenceDiagram
    participant User as 👤 用户
    participant Browser as 🌐 浏览器
    participant WebRTC as 📡 WebRTC
    participant Server as 🖥️ 服务端
    participant VAD as 👂 VAD
    participant ASR as 🎧 ASR
    participant VL as 🧠 Qwen-VL
    participant TTS as 🔊 TTS
    participant Avatar as 🎭 Avatar
    
    User->>Browser: 1️⃣ 开启摄像头和麦克风
    Browser->>Browser: getUserMedia()<br/>video: 640x480@30fps<br/>audio: 16kHz
    
    Browser->>WebRTC: 2️⃣ 建立WebRTC连接
    WebRTC->>WebRTC: createOffer()<br/>ICE候选收集
    WebRTC->>Server: 发送Offer
    Server-->>WebRTC: 返回Answer
    WebRTC->>WebRTC: P2P连接建立
    
    loop 媒体流持续传输
        Browser->>Server: 3️⃣ 视频流 30fps<br/>音频流 16kHz
    end
    
    User->>User: 4️⃣ 开始说话
    Server->>VAD: 音频流输入
    VAD->>VAD: Silero VAD检测<br/>语音活动起始
    
    User->>User: 说话结束
    VAD->>VAD: 检测语音终止
    VAD->>ASR: 5️⃣ 完整音频段
    
    ASR->>ASR: SenseVoice识别
    ASR-->>Server: 文本: "这是什么？"
    
    Server->>Server: 6️⃣ 提取最新视频帧<br/>NumPy (1,480,640,3)
    Server->>Server: JPEG压缩 + Base64编码
    
    Server->>VL: 7️⃣ 多模态推理<br/>messages=[<br/>{text: "这是什么？"},<br/>{image: "data:image/jpeg;base64,..."}]
    
    Note over VL: 视觉理解:<br/>识别物体、场景、文字<br/>结合上下文生成回答
    
    VL-->>Server: AI响应:<br/>"我看到你手里拿着一个红色的苹果..."
    
    Server->>TTS: 8️⃣ 文本转语音
    TTS->>TTS: CosyVoice合成<br/>生成自然语音
    TTS-->>Server: 音频流 16kHz PCM
    
    Server->>Avatar: 9️⃣ 数字人渲染
    Avatar->>Avatar: LiteAvatar驱动<br/>音频→口型+表情
    Avatar-->>Server: 数字人视频 25-30fps
    
    Server->>WebRTC: 🔟 媒体流返回
    WebRTC->>Browser: 数字人视频 + AI语音
    Browser->>User: 播放数字人回答
    
    Note over User: 端到端延迟: ~2.2秒
```

## 3. 屏幕共享实现流程

```mermaid
sequenceDiagram
    participant User as 👤 用户
    participant UI as 🖥️ 前端界面
    participant Store as 📦 screenShareStore
    participant WebRTC as 📡 PeerConnection
    participant Server as 🖥️ 服务端
    participant VL as 🧠 Qwen-VL
    
    User->>UI: 1️⃣ 点击"屏幕共享"按钮
    UI->>Store: startScreenShare()
    
    Store->>Store: 2️⃣ 记录摄像头状态<br/>cameraStateBeforeShare = true
    Store->>Store: 自动关闭摄像头显示<br/>videoChatStore.handleCameraOff()
    
    Store->>UI: 3️⃣ 请求屏幕权限
    UI->>Browser: getDisplayMedia({<br/>  video: {width:1280, height:720, fps:15}<br/>})
    
    alt 用户授权
        Browser-->>UI: 返回屏幕共享流<br/>displayStream
        
        UI->>Store: 传递displayStream
        Store->>WebRTC: 4️⃣ 替换视频轨道<br/>🔥 核心操作
        
        Note over WebRTC: videoSender = getSenders()<br/>.find(s => s.track.kind === 'video')
        
        WebRTC->>WebRTC: videoSender.replaceTrack(<br/>  displayStream.getVideoTracks()[0]<br/>)
        
        WebRTC-->>Store: ✅ 轨道替换成功
        Store->>Store: isScreenSharing = true
        Store-->>UI: 更新UI状态
        UI-->>User: 显示"停止共享"按钮
        
        Note over Server: 5️⃣ 后端无感知<br/>继续接收视频帧<br/>但现在是屏幕内容
        
        loop 用户提问屏幕内容
            User->>User: 6️⃣ 提问<br/>"这个错误是什么意思？"
            Server->>Server: 提取当前视频帧<br/>（屏幕截图）
            Server->>VL: 7️⃣ 分析屏幕内容<br/>{text, screen_image}
            
            Note over VL: 识别:<br/>- 浏览器窗口<br/>- 错误信息<br/>- 代码内容
            
            VL-->>Server: AI分析:<br/>"我看到你的浏览器显示<br/>JavaScript错误..."
            Server-->>User: 返回AI回答
        end
        
        User->>UI: 8️⃣ 点击"停止共享"
        UI->>Store: stopScreenShare()
        
        Store->>Store: 停止屏幕流<br/>displayStream.getTracks().stop()
        
        Store->>WebRTC: 9️⃣ 恢复摄像头轨道<br/>replaceTrack(cameraStream)
        
        WebRTC->>WebRTC: videoSender.replaceTrack(<br/>  cameraStream.getVideoTracks()[0]<br/>)
        
        WebRTC-->>Store: ✅ 轨道恢复成功
        Store->>Store: 🔟 恢复摄像头显示<br/>if (cameraStateBeforeShare)
        Store-->>UI: 更新UI状态
        UI-->>User: 显示正常界面
        
        Note over Server: AI重新接收摄像头画面
        
    else 用户拒绝
        Browser-->>UI: 权限拒绝错误
        UI-->>User: 提示"屏幕共享失败"
    end
```

## 4. WebRTC视频轨道替换机制

```mermaid
graph TD
    A[初始状态] --> B[摄像头流 cameraStream]
    B --> C[addTrack 到 PeerConnection]
    
    C --> D{用户操作}
    
    D -->|点击屏幕共享| E[getDisplayMedia]
    E --> F[获取屏幕流 displayStream]
    F --> G[🔥 replaceTrack]
    
    G --> H[videoSender.replaceTrack<br/>displayStream.videoTrack]
    H --> I[✅ AI接收屏幕画面]
    
    I --> J{用户操作}
    
    J -->|继续共享| I
    J -->|停止共享| K[🔥 replaceTrack]
    
    K --> L[videoSender.replaceTrack<br/>cameraStream.videoTrack]
    L --> M[✅ AI接收摄像头画面]
    
    M --> D
    
    style G fill:#ff6b6b,color:#fff
    style K fill:#ff6b6b,color:#fff
    style I fill:#43e97b
    style M fill:#43e97b
```

## 5. 视频帧处理管道

```mermaid
flowchart LR
    A[WebRTC接收] -->|av.VideoFrame| B[to_ndarray]
    B -->|RGB 24bit| C[NumPy数组<br/>shape: H,W,3]
    C -->|添加batch维度| D[NumPy数组<br/>shape: 1,H,W,3]
    
    D --> E{处理路径}
    
    E -->|路径1: 实时显示| F[直接传给<br/>数字人渲染]
    
    E -->|路径2: AI理解| G[PIL.Image.fromarray]
    G --> H[JPEG压缩<br/>quality=90]
    H --> I[BytesIO缓冲]
    I --> J[Base64编码]
    J --> K[数据URL<br/>data:image/jpeg;base64,...]
    K --> L[发送给<br/>Qwen-VL-Plus]
    
    L --> M[AI理解图像内容]
    M --> N[生成文本响应]
    
    style A fill:#43e97b
    style M fill:#667eea,color:#fff
    style N fill:#764ba2,color:#fff
```

## 6. Handler流水线架构

```mermaid
graph LR
    subgraph Input["输入源"]
        I1[📹 视频帧 30fps]
        I2[🎤 音频流 16kHz]
        I3[💬 文本消息]
    end
    
    subgraph Pipeline["Handler流水线"]
        H1[👂 VAD Handler<br/>Silero VAD]
        H2[🎧 ASR Handler<br/>SenseVoice]
        H3[📹 Video Handler<br/>帧缓存]
        H4[🧠 LLM Handler<br/>Qwen-VL-Plus]
        H5[🔊 TTS Handler<br/>CosyVoice]
        H6[🎭 Avatar Handler<br/>LiteAvatar]
    end
    
    subgraph Output["输出"]
        O1[📹 数字人视频]
        O2[🔊 AI语音]
        O3[💬 文本响应]
    end
    
    I1 --> H3
    I2 --> H1
    I3 --> H4
    
    H1 -->|语音检测| H2
    H2 -->|识别文本| H4
    H3 -->|最新帧| H4
    
    H4 -->|AI响应| H5
    H4 -.->|流式文本| O3
    
    H5 -->|音频| H6
    H6 -->|视频+音频| O1
    H5 -.->|音频流| O2
    
    style Pipeline fill:#667eea,color:#fff
    style H4 fill:#764ba2,color:#fff
```

## 7. 多模态消息构建

```mermaid
sequenceDiagram
    participant Handler as LLM Handler
    participant ImageUtils as 图像工具
    participant History as 对话历史
    participant API as OpenAI API
    participant Model as Qwen-VL-Plus
    
    Handler->>Handler: 接收视频帧<br/>CAMERA_VIDEO
    Handler->>Handler: 存储到context.current_image
    
    Handler->>Handler: 接收文本输入<br/>HUMAN_TEXT: "这是什么？"
    
    Handler->>ImageUtils: numpy2base64(current_image)
    ImageUtils->>ImageUtils: squeeze() 去除batch维度
    ImageUtils->>ImageUtils: PIL.Image.fromarray()
    ImageUtils->>ImageUtils: JPEG压缩 quality=90
    ImageUtils->>ImageUtils: Base64编码
    ImageUtils-->>Handler: 数据URL
    
    Handler->>History: get_messages()
    History-->>Handler: 历史对话列表
    
    Handler->>Handler: 构建多模态消息
    Note over Handler: messages = [<br/>  {role: "system", content: "..."},<br/>  ...历史对话...,<br/>  {role: "user", content: [<br/>    {type: "text", text: "这是什么？"},<br/>    {type: "image_url", image_url: {url: "data:..."}}]<br/>  }<br/>]
    
    Handler->>API: chat.completions.create(<br/>  model="qwen3-vl-plus",<br/>  messages=messages,<br/>  stream=True<br/>)
    
    API->>Model: 发送请求
    Model->>Model: 视觉理解 + 文本理解
    Model-->>API: 流式返回响应
    
    loop 流式输出
        API-->>Handler: chunk.choices[0].delta.content
        Handler->>Handler: 累积AI响应文本
        Handler-->>TTS: 发送文本片段
    end
```

## 8. 数字人渲染流程

```mermaid
flowchart TD
    A[TTS音频输出] -->|16kHz PCM| B[Avatar Handler接收]
    B --> C[LiteAvatar模型加载]
    
    C --> D{渲染模式}
    D -->|GPU模式| E[CUDA加速处理]
    D -->|CPU模式| F[CPU推理]
    
    E & F --> G[音频特征提取]
    G --> H[mel频谱分析]
    H --> I[音素对齐]
    
    I --> J[口型生成]
    J --> K[表情生成]
    K --> L[头部姿态]
    
    L --> M[渲染数字人帧]
    M --> N[25-30fps视频流]
    
    N --> O[编码H.264]
    O --> P[WebRTC传输]
    P --> Q[用户浏览器播放]
    
    style E fill:#43e97b
    style N fill:#667eea,color:#fff
```

## 9. TURN服务器NAT穿透

```mermaid
sequenceDiagram
    participant Client as 客户端浏览器
    participant STUN as STUN服务器
    participant TURN as TURN服务器<br/>8.138.87.249
    participant Server as 服务端
    
    Client->>STUN: 1️⃣ STUN请求<br/>获取公网IP
    STUN-->>Client: 返回公网地址
    
    Client->>Client: 2️⃣ 收集ICE候选
    Note over Client: candidate类型:<br/>- host (本地)<br/>- srflx (STUN反射)<br/>- relay (TURN中继)
    
    Client->>Server: 3️⃣ 发送Offer<br/>包含ICE候选
    
    Server->>Server: 处理Offer
    Server-->>Client: 返回Answer
    
    Client->>Server: 4️⃣ 尝试P2P连接
    
    alt P2P连接成功
        Client<->>Server: 直接UDP通信<br/>低延迟
    else P2P连接失败 (严格NAT)
        Client->>TURN: 5️⃣ 请求TURN中继<br/>username + credential
        TURN-->>Client: 分配中继地址
        
        Client->>TURN: 6️⃣ 发送媒体数据
        TURN->>Server: 转发数据
        
        Server->>TURN: 返回数据
        TURN->>Client: 转发数据
        
        Note over Client,Server: 通过TURN中继通信<br/>稍高延迟但稳定
    end
```

## 10. 完整数据流（端到端）

```mermaid
flowchart TB
    subgraph User["用户端"]
        U1[👤 用户行为]
        U2[📷 摄像头/🖥️屏幕]
        U3[🎤 麦克风]
        U4[🔊 扬声器]
        U5[🖥️ 显示器]
    end
    
    subgraph Frontend["前端Vue3"]
        F1[MediaStream捕获]
        F2[WebRTC管理]
        F3[轨道控制]
        F4[UI状态管理]
    end
    
    subgraph Network["网络层"]
        N1[WebRTC信令]
        N2[STUN/TURN]
        N3[UDP媒体流]
    end
    
    subgraph Backend["后端Handler"]
        B1[RTC Client]
        B2[视频帧提取]
        B3[音频流处理]
        B4[数据路由]
    end
    
    subgraph AI["AI处理"]
        A1[VAD检测]
        A2[ASR识别]
        A3[图像编码]
        A4[VL理解]
        A5[TTS合成]
        A6[Avatar渲染]
    end
    
    U1 -->|说话| U3
    U1 -->|展示物品| U2
    U2 & U3 -->|捕获| F1
    
    F1 --> F2
    F2 -->|Offer/Answer| N1
    N1 --> N2
    N2 -->|NAT穿透| N3
    
    N3 -->|视频+音频| B1
    B1 --> B2
    B1 --> B3
    B2 & B3 --> B4
    
    B4 -->|音频| A1
    A1 -->|语音段| A2
    A2 -->|文本| A4
    
    B4 -->|视频帧| A3
    A3 -->|Base64| A4
    
    A4 -->|AI响应| A5
    A5 -->|音频| A6
    A6 -->|数字人视频| B4
    
    B4 -->|媒体流| N3
    N3 --> F2
    F2 -->|音频| U4
    F2 -->|视频| U5
    
    U4 & U5 -->|感知| U1
    
    style User fill:#ffeaa7
    style Frontend fill:#43e97b,color:#fff
    style Network fill:#38f9d7,color:#fff
    style Backend fill:#667eea,color:#fff
    style AI fill:#764ba2,color:#fff
```

## 11. 性能优化策略

```mermaid
mindmap
  root((性能优化))
    视频优化
      帧率控制
        摄像头 30fps
        屏幕共享 15fps
      分辨率调整
        标准 640x480
        高清 1280x720
      编码优化
        JPEG quality=90
        Base64缓存
    
    音频优化
      采样率 16kHz
      降噪处理
      回声消除
      VAD快速检测
    
    网络优化
      WebRTC优化
        ICE候选池
        TURN中继
        自适应码率
      带宽控制
        视频压缩
        音频压缩
    
    AI优化
      GPU加速
        PyTorch CUDA
        批处理推理
      模型优化
        量化加速
        流式输出
      缓存策略
        帧缓存
        结果缓存
    
    并发优化
      异步处理
        asyncio
        多线程
      资源管理
        连接池
        内存控制
```

## 12. 关键API调用时序

```mermaid
sequenceDiagram
    autonumber
    participant App as 应用代码
    participant Browser as 浏览器API
    participant PC as RTCPeerConnection
    participant Server as 服务器
    
    App->>Browser: navigator.mediaDevices.getUserMedia()
    Browser-->>App: MediaStream (camera+mic)
    
    App->>PC: new RTCPeerConnection(config)
    App->>PC: addTrack(videoTrack, stream)
    App->>PC: addTrack(audioTrack, stream)
    
    App->>PC: createOffer()
    PC-->>App: RTCSessionDescription (offer)
    
    App->>PC: setLocalDescription(offer)
    App->>Server: 发送offer (HTTP/WebSocket)
    
    Server-->>App: 返回answer
    App->>PC: setRemoteDescription(answer)
    
    Note over PC,Server: ICE候选交换
    
    PC->>Server: 媒体流传输开始
    
    rect rgb(67, 233, 123)
        Note over App: 屏幕共享切换
        App->>Browser: getDisplayMedia()
        Browser-->>App: MediaStream (screen)
        
        App->>PC: getSenders().find(video)
        PC-->>App: RTCRtpSender
        
        App->>PC: sender.replaceTrack(screenVideoTrack)
        Note over PC: 🔥 轨道替换完成
        PC->>Server: 现在传输屏幕内容
    end
    
    rect rgb(255, 107, 107)
        Note over App: 恢复摄像头
        App->>PC: sender.replaceTrack(cameraVideoTrack)
        Note over PC: 🔥 轨道恢复
        PC->>Server: 现在传输摄像头内容
    end
```

---

## 使用说明

这些Mermaid图表可以直接在支持Mermaid的Markdown编辑器中渲染，例如：
- **GitHub/GitLab** - 原生支持
- **Typora** - Markdown编辑器
- **VSCode** - 安装Mermaid Preview插件
- **Obsidian** - 原生支持
- **在线工具** - https://mermaid.live/

### 推荐使用方式

1. **在线预览**：访问 https://mermaid.live/，粘贴代码即可实时预览
2. **VSCode**：安装 "Markdown Preview Mermaid Support" 插件
3. **导出图片**：在mermaid.live中可以导出为PNG/SVG格式

### 图表说明

- **架构图** - 使用 `graph` 展示系统层次结构
- **时序图** - 使用 `sequenceDiagram` 展示交互流程
- **流程图** - 使用 `flowchart` 展示数据处理流程
- **状态图** - 使用 `stateDiagram` 展示状态转换
- **类图** - 使用 `classDiagram` 展示代码结构
- **思维导图** - 使用 `mindmap` 展示优化策略



---
config:
  layout: elk
---
flowchart LR
 subgraph InputCapture["媒体捕获"]
        Camera["📹 摄像头<br><small></small>"]
        Screen["🖥️ 屏幕共享<br><small></small>"]
        Mic["🎤 麦克风<br><small></small>"]
  end
 subgraph Frontend["🖥️ 前端层"]
    direction TB
        InputCapture
        WebRTC["🔗 WebRTC<br>网页实时通信"]
        TURN["🌐 TURN服务器<br><small>NAT穿透</small>"]
  end
 subgraph MediaSplit["媒体分离"]
        VideoSplit["📹 视频分离器"]
        AudioSplit["🎵 音频分离器"]
  end
 subgraph Backend["⚙️ 后端服务层"]
    direction TB
        RtcStream["📡 RTC Stream<br><small>WebRTC流处理</small>"]
        SessionMgr["🔐 会话管理<br><small>并发/隔离</small>"]
        MediaSplit
  end
 subgraph VideoPath["视频路径"]
        CameraFrame["📹 摄像头帧<br><small>视频通话</small>"]
        ScreenFrame["🖥️ 屏幕共享<br><small>实时画面</small>"]
  end
 subgraph AudioPath["音频路径"]
        VAD["👂 VAD<br><small>语音检测</small>"]
        ASR["🎧 ASR<br><small>语音识别</small>"]
  end
 subgraph InputProcess["📥 输入处理层"]
    direction TB
        VideoPath
        AudioPath
  end
 subgraph AICore["🧠 AI处理层"]
    direction TB
        FrameCache["🖼️ 实时画面"]
        VLModel["Qwen3-VL-Plus<br><small>多模态理解</small>"]
        TextGen["✍️ LLM文本生成<br><small></small>"]
  end
 subgraph OutputProcess["📤 输出生成层"]
    direction TB
        TTS["🔊 TTS<br><small>语音合成</small>"]
        Avatar["🎭 LiteAvatar<br><small>实时数字人渲染</small>"]
  end
    Camera --> WebRTC
    Screen --> WebRTC
    Mic --> WebRTC
    WebRTC <--> TURN
    TURN <--> RtcStream
    RtcStream --> SessionMgr
    SessionMgr --> VideoSplit & AudioSplit
    VideoSplit --> CameraFrame & ScreenFrame
    AudioSplit --> VAD
    VAD --> ASR
    CameraFrame --> FrameCache
    ScreenFrame --> FrameCache
    FrameCache --> VLModel
    ASR --> TextGen
    TextGen <--> VLModel
    VLModel --> TTS
    TTS --> Avatar
    n1["Text Block"]
    n1@{ shape: text}
     Camera:::frontendClass
     Screen:::frontendClass
     Mic:::frontendClass
     WebRTC:::frontendClass
     TURN:::frontendClass
     VideoSplit:::backendClass
     AudioSplit:::backendClass
     RtcStream:::backendClass
     SessionMgr:::backendClass
     CameraFrame:::inputClass
     ScreenFrame:::inputClass
     VAD:::inputClass
     ASR:::inputClass
     FrameCache:::aiClass
     VLModel:::aiClass
     TextGen:::aiClass
     TTS:::outputClass
     Avatar:::outputClass
    classDef frontendClass fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#000
    classDef backendClass fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000
    classDef inputClass fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#000
    classDef aiClass fill:#fce4ec,stroke:#c2185b,stroke-width:2px,color:#000
    classDef outputClass fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
    classDef mediaClass fill:#fff9c4,stroke:#f57f17,stroke-width:2px,color:#000
    style InputCapture fill:#fff3e0,stroke:#e65100,stroke-width:1px
    style MediaSplit fill:#e1bee7,stroke:#7b1fa2,stroke-width:1px
    style VideoPath fill:#ffe0b2,stroke:#e65100,stroke-width:1px
    style AudioPath fill:#ffccbc,stroke:#e64a19,stroke-width:1px
    style Frontend fill:#e3f2fd,stroke:#0d47a1,stroke-width:3px
    style Backend fill:#f3e5f5,stroke:#4a148c,stroke-width:3px
    style InputProcess fill:#fff3e0,stroke:#e65100,stroke-width:3px
    style AICore fill:#fce4ec,stroke:#880e4f,stroke-width:3px
    style OutputProcess fill:#e8f5e9,stroke:#1b5e20,stroke-width:3px
