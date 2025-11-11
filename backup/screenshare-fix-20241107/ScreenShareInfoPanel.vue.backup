<template>
  <div class="screen-share-info-panel" v-if="screenShareStore.state.isScreenSharing">
    <!-- 面板头部 -->
    <div class="panel-header">
      <div class="header-left">
        <div class="status-indicator" :class="connectionStatusClass">
          <div class="indicator-dot"></div>
          <span class="status-text">{{ screenShareStore.connectionStatusText }}</span>
        </div>
        <div class="quality-badge" :class="`quality-${screenShareStore.state.connectionQuality}`">
          {{ screenShareStore.qualityText }}
        </div>
      </div>
      <div class="header-actions">
        <a-tooltip title="设置">
          <button 
            class="action-btn"
            :class="{ active: screenShareStore.state.showSettingsPanel }"
            @click="screenShareStore.toggleSettingsPanel()"
          >
            <Iconfont :icon="Settings" />
          </button>
        </a-tooltip>
        <a-tooltip title="统计">
          <button 
            class="action-btn"
            :class="{ active: screenShareStore.state.showStatsPanel }"
            @click="screenShareStore.toggleStatsPanel()"
          >
            <Iconfont :icon="Monitor" />
          </button>
        </a-tooltip>
        <a-tooltip title="停止屏幕共享">
          <button 
            class="action-btn stop-btn"
            @click="handleStopScreenShare"
          >
            <Iconfont :icon="ScreenShareStop" />
          </button>
        </a-tooltip>
      </div>
    </div>

    <!-- 设置面板 -->
    <a-collapse 
      v-if="screenShareStore.state.showSettingsPanel" 
      class="settings-panel"
      :bordered="false"
      :ghost="true"
      expand-icon-position="end"
    >
      <a-collapse-panel key="quality" header="🎚️ 质量设置">
        <div class="setting-group">
          <a-radio-group 
            v-model:value="localOptions.quality"
            @change="updateOptions"
            button-style="solid"
            size="small"
          >
            <a-radio-button value="ai-compatible">🤖 AI兼容</a-radio-button>
            <a-radio-button value="mobile">📱 移动优化</a-radio-button>
            <a-radio-button value="desktop">🖥️ 桌面标准</a-radio-button>
            <a-radio-button value="high-bandwidth">🚀 高质量</a-radio-button>
          </a-radio-group>
          <div class="quality-desc">{{ getQualityHint(localOptions.quality) }}</div>
        </div>
      </a-collapse-panel>

      <a-collapse-panel key="capture" header="📹 捕获设置">
        <div class="setting-group">
          <a-select 
            v-model:value="localOptions.captureMode"
            @change="updateOptions"
            style="width: 100%"
            size="small"
          >
            <a-select-option value="window">🪟 应用程序窗口</a-select-option>
            <a-select-option value="desktop">🖥️ 整个桌面</a-select-option>
            <a-select-option value="tab">🌐 浏览器标签页</a-select-option>
          </a-select>
        </div>
        
        <div class="setting-group">
          <a-switch 
            v-model:checked="localOptions.includeSystemAudio"
            @change="updateOptions"
            :disabled="screenShareStore.isMobile"
            size="small"
          />
          <span class="switch-label">🔊 包含系统音频</span>
          <small v-if="screenShareStore.isMobile" class="disabled-note">
            (移动端不支持)
          </small>
        </div>

        <div class="setting-group">
          <a-switch 
            v-model:checked="localOptions.autoQualityAdjust"
            @change="updateOptions"
            size="small"
          />
          <span class="switch-label">🔄 自动质量调整</span>
          <small>根据网络状况自动降低质量</small>
        </div>
      </a-collapse-panel>
    </a-collapse>

    <!-- 统计面板 -->
    <div v-if="screenShareStore.state.showStatsPanel" class="stats-panel">
      <div class="stats-header">
        <Iconfont :icon="Monitor" />
        <span>性能统计</span>
      </div>
      
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon">📊</div>
          <div class="stat-content">
            <div class="stat-value">{{ formatBandwidth(screenShareStore.state.connectionStats.bandwidth) }}</div>
            <div class="stat-label">带宽</div>
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-icon">⏱️</div>
          <div class="stat-content">
            <div class="stat-value">{{ screenShareStore.state.connectionStats.roundTripTime }}ms</div>
            <div class="stat-label">延迟</div>
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-icon">📦</div>
          <div class="stat-content">
            <div class="stat-value">{{ screenShareStore.state.connectionStats.packetsLost }}</div>
            <div class="stat-label">丢包</div>
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-icon">🔗</div>
          <div class="stat-content">
            <div class="stat-value">TURN</div>
            <div class="stat-label">中继状态</div>
          </div>
        </div>
      </div>

      <!-- 服务器信息 -->
      <div class="server-info">
        <div class="server-item">
          <span class="server-label">🌐 TURN服务器:</span>
          <span class="server-value">8.138.87.249:3478</span>
        </div>
        <div class="server-item">
          <span class="server-label">🖥️ 服务器配置:</span>
          <span class="server-value">2vCPU / 4GiB</span>
        </div>
        <div class="server-item">
          <span class="server-label">📍 视频源:</span>
          <span class="server-value">{{ getVideoSourceText() }}</span>
        </div>
      </div>
    </div>

    <!-- 错误提示 -->
    <a-alert
      v-if="screenShareStore.state.lastError"
      :message="screenShareStore.state.lastError"
      type="error"
      closable
      show-icon
      @close="screenShareStore.clearError()"
      class="error-alert"
    />
  </div>
</template>

<script setup lang="ts">
import { reactive, computed, onMounted } from 'vue';
import { useScreenShareStore } from '@/store/screenShareStore';
import { formatBandwidth, getQualityHint } from '@/utils/screenShareUtils';
import Iconfont, { Settings, Monitor, ScreenShareStop } from '@/components/Iconfont';

const screenShareStore = useScreenShareStore();

// 本地选项
const localOptions = reactive({
  quality: 'ai-compatible' as 'ai-compatible' | 'mobile' | 'desktop' | 'high-bandwidth',
  captureMode: 'window' as 'desktop' | 'window' | 'tab',
  includeSystemAudio: false,
  autoQualityAdjust: true
});

// 计算属性
const connectionStatusClass = computed(() => {
  switch (screenShareStore.state.connectionState) {
    case 'connected': return 'status-connected';
    case 'checking': return 'status-connecting';
    case 'disconnected': return 'status-disconnected';
    case 'failed': return 'status-failed';
    default: return 'status-new';
  }
});

// 方法
async function handleStopScreenShare() {
  try {
    await screenShareStore.stopScreenShare();
  } catch (error) {
    console.error('停止屏幕共享失败:', error);
  }
}

function updateOptions() {
  screenShareStore.updateScreenShareOptions(localOptions);
}

function getVideoSourceText(): string {
  return screenShareStore.state.currentVideoSource === 'screen' ? '屏幕共享' : '摄像头';
}

// 生命周期
onMounted(() => {
  // 同步选项
  Object.assign(localOptions, screenShareStore.state.screenShareOptions);
});
</script>

<style lang="less" scoped>
.screen-share-info-panel {
  position: fixed;
  top: 20px;
  right: 20px;
  width: 350px;
  max-height: 80vh;
  background: rgba(24, 24, 27, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: white;
  z-index: 1000;
  overflow: hidden;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
  animation: slideInRight 0.3s ease-out;

  @media (max-width: 768px) {
    width: calc(100vw - 40px);
    max-width: 320px;
  }
}

@keyframes slideInRight {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(168, 85, 247, 0.1));

  .header-left {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .status-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;

    .indicator-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      
      .status-connected & {
        background: #10b981;
        animation: pulse 2s infinite;
      }
      
      .status-connecting & {
        background: #f59e0b;
        animation: blink 1s infinite;
      }
      
      .status-disconnected & {
        background: #6b7280;
      }
      
      .status-failed & {
        background: #ef4444;
      }
    }

    &.status-connected { color: #10b981; }
    &.status-connecting { color: #f59e0b; }
    &.status-disconnected { color: #6b7280; }
    &.status-failed { color: #ef4444; }
  }

  .quality-badge {
    font-size: 11px;
    padding: 4px 8px;
    border-radius: 12px;
    font-weight: 500;

    &.quality-excellent {
      background: rgba(16, 185, 129, 0.2);
      color: #10b981;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    &.quality-good {
      background: rgba(59, 130, 246, 0.2);
      color: #3b82f6;
      border: 1px solid rgba(59, 130, 246, 0.3);
    }
    
    &.quality-fair {
      background: rgba(245, 158, 11, 0.2);
      color: #f59e0b;
      border: 1px solid rgba(245, 158, 11, 0.3);
    }
    
    &.quality-poor {
      background: rgba(239, 68, 68, 0.2);
      color: #ef4444;
      border: 1px solid rgba(239, 68, 68, 0.3);
    }
  }

  .header-actions {
    display: flex;
    gap: 8px;

    .action-btn {
      width: 32px;
      height: 32px;
      border: none;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.1);
      color: white;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s;
      font-size: 14px;

      &:hover {
        background: rgba(255, 255, 255, 0.2);
        transform: translateY(-1px);
      }

      &.active {
        background: rgba(99, 102, 241, 0.3);
        color: #818cf8;
      }

      &.stop-btn {
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;

        &:hover {
          background: rgba(239, 68, 68, 0.3);
        }
      }
    }
  }
}

.settings-panel {
  margin: 16px 20px;

  :deep(.ant-collapse) {
    background: transparent;
    border: none;
  }

  :deep(.ant-collapse-item) {
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    margin-bottom: 8px;
    background: rgba(255, 255, 255, 0.05);
  }

  :deep(.ant-collapse-header) {
    color: white !important;
    font-weight: 500;
    padding: 12px 16px !important;
  }

  :deep(.ant-collapse-content-box) {
    padding: 16px !important;
  }

  .setting-group {
    margin-bottom: 16px;

    &:last-child {
      margin-bottom: 0;
    }

    .quality-desc {
      margin-top: 8px;
      font-size: 12px;
      color: rgba(255, 255, 255, 0.7);
      font-style: italic;
    }

    .switch-label {
      margin-left: 8px;
      font-size: 13px;
    }

    small {
      display: block;
      font-size: 11px;
      color: rgba(255, 255, 255, 0.6);
      margin-top: 4px;

      &.disabled-note {
        color: #ef4444;
      }
    }
  }

  :deep(.ant-radio-group) {
    width: 100%;
  }

  :deep(.ant-radio-button-wrapper) {
    background: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.2);
    color: white;
    flex: 1;
    text-align: center;

    &::before {
      background: rgba(255, 255, 255, 0.2);
    }

    &:hover {
      color: #818cf8;
    }

    &.ant-radio-button-wrapper-checked {
      background: rgba(99, 102, 241, 0.3);
      border-color: #6366f1;
      color: #818cf8;
    }
  }

  :deep(.ant-select) {
    .ant-select-selector {
      background: rgba(255, 255, 255, 0.1) !important;
      border-color: rgba(255, 255, 255, 0.2) !important;
      color: white !important;
    }
  }

  :deep(.ant-switch) {
    background: rgba(255, 255, 255, 0.2);

    &.ant-switch-checked {
      background: #6366f1;
    }
  }
}

.stats-panel {
  margin: 16px 20px;

  .stats-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    margin-bottom: 16px;
    color: #818cf8;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-bottom: 16px;

    .stat-card {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 8px;
      padding: 12px;
      display: flex;
      align-items: center;
      gap: 10px;

      .stat-icon {
        font-size: 18px;
      }

      .stat-content {
        .stat-value {
          font-weight: 600;
          font-size: 14px;
          color: white;
        }

        .stat-label {
          font-size: 11px;
          color: rgba(255, 255, 255, 0.7);
        }
      }
    }
  }

  .server-info {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 12px;

    .server-item {
      display: flex;
      justify-content: space-between;
      margin-bottom: 8px;
      font-size: 12px;

      &:last-child {
        margin-bottom: 0;
      }

      .server-label {
        color: rgba(255, 255, 255, 0.7);
      }

      .server-value {
        color: white;
        font-weight: 500;
      }
    }
  }
}

.error-alert {
  margin: 16px 20px;

  :deep(.ant-alert) {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0.3; }
}
</style>
