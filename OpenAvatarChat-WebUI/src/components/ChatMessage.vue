<script setup lang="ts">
import { ref } from 'vue'

const props = withDefaults(
  defineProps<{
    message: string,
    role: string,
    style?: string
  }>(),
  {}
)

const showCopyButton = ref(false)
const copySuccess = ref(false)

const copyToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(props.message)
    copySuccess.value = true
    setTimeout(() => {
      copySuccess.value = false
    }, 2000)
  } catch (err) {
    console.error('复制失败:', err)
    // 降级方案：使用传统的复制方法
    const textArea = document.createElement('textarea')
    textArea.value = props.message
    document.body.appendChild(textArea)
    textArea.select()
    document.execCommand('copy')
    document.body.removeChild(textArea)
    copySuccess.value = true
    setTimeout(() => {
      copySuccess.value = false
    }, 2000)
  }
}
</script>

<template>
  <div 
    :class="['answer-message-container', role]" 
    :style="style"
    @mouseenter="showCopyButton = true"
    @mouseleave="showCopyButton = false"
  >
    <div class="answer-message-text">
      {{ message }}
    </div>
    <!-- 只为avatar角色显示复制按钮 -->
    <div 
      v-if="role === 'avatar'" 
      class="copy-button-wrapper"
      :class="{ 'show': showCopyButton || copySuccess }"
    >
      <button 
        class="copy-button"
        :class="{ 'success': copySuccess }"
        @click="copyToClipboard"
        :title="copySuccess ? '复制成功！' : '复制消息'"
      >
        <svg v-if="!copySuccess" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>
        </svg>
        <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped lang="less">
.answer-message-container {
  position: relative;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 12px;
  color: #26244c;

  &.human {
    background: #dddddd99;
    // margin-left: 20px;
    margin-right: 0;
  }

  &.avatar {
    background: #9189fa;
    color: #ffffff;
    // margin-right: 20px;
    padding-right: 40px; // 为复制按钮留出空间
  }
}

.copy-button-wrapper {
  position: absolute;
  top: 6px;
  right: 8px;
  opacity: 0;
  transition: opacity 0.2s ease-in-out;

  &.show {
    opacity: 1;
  }
}

.copy-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.2);
  color: #ffffff;
  cursor: pointer;
  transition: all 0.2s ease-in-out;

  &:hover {
    background: rgba(255, 255, 255, 0.3);
    transform: scale(1.1);
  }

  &:active {
    transform: scale(0.95);
  }

  &.success {
    background: rgba(76, 175, 80, 0.8);
    
    &:hover {
      background: rgba(76, 175, 80, 0.9);
    }
  }

  svg {
    width: 14px;
    height: 14px;
  }
}

.answer-message-text {
  word-break: break-word;
  line-height: 1.5;
}
</style>
