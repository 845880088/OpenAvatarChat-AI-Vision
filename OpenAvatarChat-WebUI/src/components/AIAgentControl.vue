<template>
  <div class="ai-agent-control">
    <!-- 触发按钮 -->
    <div class="float-button" @click="toggleDrawer">
      <svg viewBox="0 0 24 24" fill="none" class="icon">
        <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2"/>
        <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2"/>
        <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2"/>
      </svg>
      <span class="text">AI助手</span>
    </div>

    <!-- 侧边栏 -->
    <Transition name="drawer">
      <div v-if="isOpen" class="drawer-mask" @click="closeDrawer">
        <div class="drawer-container" @click.stop>
          <!-- 标题栏 -->
          <div class="drawer-header">
            <h3>🤖 AI 自动化助手</h3>
            <button v-if="!isRunning" @click="closeDrawer" class="close-btn">×</button>
          </div>

          <!-- 内容区 -->
          <div class="drawer-body">
            <!-- 输入区 -->
            <div class="input-card">
              <label class="label">任务指令</label>
              <textarea
                v-model="taskInput"
                :disabled="isRunning"
                placeholder="请输入任务，例如：
• 打开浏览器
• 打开记事本
• 打开微信"
                rows="5"
                class="task-input"
              />
              
              <button 
                @click="startTask"
                :disabled="!taskInput.trim() || isRunning"
                class="btn-primary"
              >
                {{ isRunning ? '⏳ 执行中...' : '▶️ 开始执行' }}
              </button>
              
              <button 
                v-if="isRunning"
                @click="stopTask"
                class="btn-danger"
              >
                ⏹️ 停止执行
              </button>
            </div>

            <!-- 状态卡片 -->
            <div class="status-card">
              <div class="status-header">
                <span>执行状态</span>
                <span :class="['badge', statusClass]">{{ statusText }}</span>
              </div>

              <div v-if="isRunning" class="progress-bar">
                <div class="progress-fill" :style="{ width: progress + '%' }"></div>
                <span class="progress-text">{{ currentStepNum }} / {{ maxSteps }}</span>
              </div>

              <div v-if="currentStep" class="current-step">
                <div class="step-icon">⚙️</div>
                <div class="step-text">{{ currentStep }}</div>
              </div>
            </div>

            <!-- 历史记录 -->
            <div class="history-card">
              <div class="history-header">📜 执行历史</div>
              <div class="history-list" ref="historyRef">
                <div v-if="history.length === 0" class="empty">
                  暂无执行记录
                </div>
                <div
                  v-for="(item, idx) in history"
                  :key="idx"
                  :class="['history-item', item.type]"
                >
                  <span class="time">{{ item.time }}</span>
                  <span class="text">{{ item.text }}</span>
                </div>
              </div>
            </div>

            <!-- AI分析 -->
            <div v-if="aiResponse" class="ai-card">
              <div class="ai-header">💭 AI 分析</div>
              <div class="ai-text">{{ aiResponse }}</div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import axios from 'axios'

// 状态
const isOpen = ref(false)
const taskInput = ref('')
const isRunning = ref(false)
const currentStep = ref('')
const currentStepNum = ref(0)
const maxSteps = ref(100)
const progress = ref(0)
const statusText = ref('就绪')
const history = ref<Array<{time: string, text: string, type: string}>>([])
const aiResponse = ref('')
const historyRef = ref<HTMLElement>()
const taskId = ref('')

let ws: WebSocket | null = null

// 计算属性
const statusClass = computed(() => {
  if (isRunning.value) return 'running'
  if (statusText.value === '完成') return 'success'
  if (statusText.value === '失败') return 'error'
  return 'default'
})

// 打开/关闭
const toggleDrawer = () => {
  isOpen.value = !isOpen.value
  console.log('🎯 侧边栏状态:', isOpen.value ? '打开' : '关闭')
}

const closeDrawer = () => {
  if (isRunning.value) {
    message.warning('任务执行中，请先停止')
    return
  }
  isOpen.value = false
  if (ws) ws.close()
}

// 时间格式化
const formatTime = () => {
  const now = new Date()
  return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`
}

// 添加历史
const addHistory = (text: string, type = 'info') => {
  history.value.push({ time: formatTime(), text, type })
  nextTick(() => {
    if (historyRef.value) {
      historyRef.value.scrollTop = historyRef.value.scrollHeight
    }
  })
}

// WebSocket
const connectWebSocket = (tid: string) => {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const url = `${proto}//${window.location.host}/ws/agent/${tid}`
  
  console.log('📡 连接 WebSocket:', url)
  ws = new WebSocket(url)
  
  ws.onopen = () => console.log('✅ WebSocket 已连接')
  
  ws.onmessage = (e) => {
    const data = JSON.parse(e.data)
    console.log('📨', data)
    
    switch (data.type) {
      case 'step':
        currentStepNum.value = data.step
        maxSteps.value = data.max_steps || 100
        progress.value = Math.round((data.step / maxSteps.value) * 100)
        break
      case 'command':
        currentStep.value = data.command
        addHistory(data.command, 'info')
        break
      case 'ai_response':
        aiResponse.value = data.text
        break
      case 'result':
        addHistory(`✅ ${data.text}`, 'success')
        break
      case 'error':
        addHistory(`❌ ${data.text}`, 'error')
        statusText.value = '失败'
        isRunning.value = false
        message.error('执行失败')
        // 5秒后自动关闭侧边栏，方便下次使用
        setTimeout(() => {
          if (!isRunning.value) {
            isOpen.value = false
          }
        }, 5000)
        break
      case 'complete':
        statusText.value = '完成'
        isRunning.value = false
        progress.value = 100
        message.success('任务完成！')
        if (ws) ws.close()
        // 3秒后自动关闭侧边栏，方便下次使用
        setTimeout(() => {
          if (!isRunning.value) {
            isOpen.value = false
          }
        }, 3000)
        break
    }
  }
  
  ws.onerror = (err) => console.error('❌ WebSocket 错误:', err)
  ws.onclose = () => {
    console.log('🔌 WebSocket 已断开')
    ws = null
  }
}

// 开始任务
const startTask = async () => {
  if (!taskInput.value.trim()) {
    message.warning('请输入任务')
    return
  }
  
  try {
    isRunning.value = true
    statusText.value = '启动中'
    progress.value = 0
    history.value = []
    currentStep.value = ''
    aiResponse.value = ''
    
    addHistory(`开始: ${taskInput.value}`, 'info')
    
    console.log('📡 POST /api/agent/start')
    const res = await axios.post('/api/agent/start', { task: taskInput.value })
    
    console.log('📥', res.data)
    
    if (res.data.success) {
      taskId.value = res.data.task_id
      statusText.value = '执行中'
      connectWebSocket(taskId.value)
      message.success('任务已启动')
    } else {
      throw new Error(res.data.error || '启动失败')
    }
  } catch (err: any) {
    console.error('❌', err)
    const msg = err.response?.data?.error || err.message || '未知错误'
    message.error(`失败: ${msg}`)
    isRunning.value = false
    statusText.value = '失败'
    addHistory(`❌ ${msg}`, 'error')
  }
}

// 停止任务
const stopTask = async () => {
  try {
    if (taskId.value) {
      await axios.post('/api/agent/stop', { task_id: taskId.value })
    }
    if (ws) ws.close()
    isRunning.value = false
    statusText.value = '已停止'
    addHistory('用户停止', 'warning')
    message.info('已停止')
  } catch (err) {
    console.error('停止失败:', err)
    message.error('停止失败')
  }
}

console.log('🤖 AI助手组件已加载')
</script>

<style scoped lang="less">
.ai-agent-control {
  .float-button {
    position: fixed;
    bottom: 80px;
    right: 30px;
    width: 70px;
    height: 70px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 50%;
    box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 4px;
    cursor: pointer;
    transition: all 0.3s;
    z-index: 1000;
    
    &:hover {
      transform: translateY(-4px) scale(1.05);
      box-shadow: 0 12px 32px rgba(102, 126, 234, 0.6);
    }
    
    .icon {
      width: 28px;
      height: 28px;
      color: white;
    }
    
    .text {
      color: white;
      font-size: 11px;
      font-weight: 600;
    }
  }
  
  .drawer-mask {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 2000;
    display: flex;
    justify-content: flex-end;
    
    .drawer-container {
      width: 480px;
      height: 100vh;
      background: #f5f7fa;
      box-shadow: -4px 0 24px rgba(0, 0, 0, 0.15);
      display: flex;
      flex-direction: column;
    }
  }
  
  .drawer-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 20px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    h3 {
      color: white;
      font-size: 18px;
      font-weight: 700;
      margin: 0;
    }
    
    .close-btn {
      width: 32px;
      height: 32px;
      border: none;
      background: rgba(255, 255, 255, 0.2);
      color: white;
      border-radius: 50%;
      font-size: 24px;
      line-height: 1;
      cursor: pointer;
      transition: all 0.2s;
      
      &:hover {
        background: rgba(255, 255, 255, 0.3);
        transform: rotate(90deg);
      }
    }
  }
  
  .drawer-body {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    
    &::-webkit-scrollbar {
      width: 6px;
    }
    
    &::-webkit-scrollbar-thumb {
      background: #d9d9d9;
      border-radius: 3px;
    }
  }
  
  .input-card, .status-card, .history-card, .ai-card {
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  }
  
  .input-card {
    .label {
      display: block;
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 8px;
      color: #262626;
    }
    
    .task-input {
      width: 100%;
      padding: 12px;
      border: 1px solid #d9d9d9;
      border-radius: 8px;
      font-size: 14px;
      margin-bottom: 12px;
      resize: vertical;
      font-family: inherit;
      
      &:focus {
        outline: none;
        border-color: #667eea;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
      }
      
      &:disabled {
        background: #f5f5f5;
        cursor: not-allowed;
      }
    }
    
    .btn-primary, .btn-danger {
      width: 100%;
      height: 48px;
      border: none;
      border-radius: 8px;
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
      margin-bottom: 8px;
      
      &:last-child {
        margin-bottom: 0;
      }
    }
    
    .btn-primary {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      
      &:hover:not(:disabled) {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
      }
      
      &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }
    }
    
    .btn-danger {
      background: #ff4d4f;
      color: white;
      
      &:hover {
        background: #ff7875;
      }
    }
  }
  
  .status-card {
    .status-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      font-weight: 600;
    }
    
    .badge {
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
      
      &.default { background: #f0f0f0; color: #666; }
      &.running { background: #e6f7ff; color: #1890ff; }
      &.success { background: #f6ffed; color: #52c41a; }
      &.error { background: #fff2f0; color: #ff4d4f; }
    }
    
    .progress-bar {
      position: relative;
      height: 24px;
      background: #f0f0f0;
      border-radius: 12px;
      overflow: hidden;
      margin-bottom: 12px;
      
      .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        transition: width 0.3s;
      }
      
      .progress-text {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: 600;
        color: #262626;
      }
    }
    
    .current-step {
      display: flex;
      gap: 12px;
      padding: 12px;
      background: #f0f5ff;
      border-radius: 8px;
      border-left: 4px solid #667eea;
      
      .step-icon {
        font-size: 20px;
      }
      
      .step-text {
        flex: 1;
        font-size: 14px;
        color: #262626;
        line-height: 1.6;
      }
    }
  }
  
  .history-card {
    .history-header {
      font-weight: 700;
      margin-bottom: 12px;
    }
    
    .history-list {
      max-height: 300px;
      overflow-y: auto;
      
      .empty {
        text-align: center;
        color: #bfbfbf;
        padding: 40px 0;
      }
      
      .history-item {
        padding: 10px 12px;
        margin-bottom: 8px;
        border-radius: 8px;
        font-size: 13px;
        display: flex;
        gap: 10px;
        
        &.info { background: #e6f7ff; border-left: 3px solid #1890ff; }
        &.success { background: #f6ffed; border-left: 3px solid #52c41a; }
        &.error { background: #fff2f0; border-left: 3px solid #ff4d4f; }
        &.warning { background: #fffbe6; border-left: 3px solid #faad14; }
        
        .time {
          color: #8c8c8c;
          font-family: monospace;
          flex-shrink: 0;
        }
        
        .text {
          flex: 1;
          color: #262626;
        }
      }
    }
  }
  
  .ai-card {
    .ai-header {
      font-weight: 700;
      margin-bottom: 12px;
      color: #1890ff;
    }
    
    .ai-text {
      font-size: 14px;
      line-height: 1.8;
      color: #262626;
      white-space: pre-wrap;
    }
  }
}

// 过渡动画
.drawer-enter-active, .drawer-leave-active {
  transition: all 0.3s;
  
  .drawer-container {
    transition: transform 0.3s;
  }
}

.drawer-enter-from, .drawer-leave-to {
  opacity: 0;
  
  .drawer-container {
    transform: translateX(100%);
  }
}
</style>
