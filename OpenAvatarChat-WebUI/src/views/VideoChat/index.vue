<template>
  <div class="page-container" ref="wrapRef">
    <div class="content-container">
      <div
        class="video-container"
        :style="{
          visibility: webcamAccessed ? 'visible' : 'hidden',
          aspectRatio: remoteAspectRatio,
        }"
      >
        <div
          :class="`local-video-container ${streamState === 'open' ? 'scaled' : ''}`"
          v-show="hasCamera && !cameraOff"
          ref="localVideoContainerRef"
        >
          <video
            class="local-video"
            ref="localVideoRef"
            autoplay
            muted
            playsinline
            :style="{
              visibility: cameraOff ? 'hidden' : 'visible',
              display: !hasCamera || cameraOff ? 'none' : 'block',
            }"
          />
        </div>
        <div class="remote-video-container" ref="remoteVideoContainerRef">
          <video
            v-if="!avatarType"
            class="remote-video"
            v-show="streamState === 'open'"
            @playing="onplayingRemoteVideo"
            ref="remoteVideoRef"
            autoplay
            playsinline
            :muted="volumeMuted"
          />
          <div
            v-if="streamState === 'open' && showChatRecords && !isLandscape"
            :class="`chat-records-container inline`"
            :style="
              !hasCamera || cameraOff ? 'width:80%;padding-bottom:12px;' : 'padding-bottom:12px;'
            "
          >
            <ChatRecords
              ref="chatRecordsInstanceRef"
              :chatRecords="chatRecords.filter((_, index) => index >= chatRecords.length - 4)"
            />
          </div>
        </div>

        <div class="actions">
          <ActionGroup />
        </div>
      </div>
      <template v-if="(!hasMic || micMuted) && streamState === 'open'" class="chat-input-wrapper">
        <ChatInput
          :replying="replying"
          @interrupt="onInterrupt"
          @send="onSend"
          @stop="videoChatState.startWebRTC"
        />
      </template>
      <template v-else-if="webcamAccessed">
        <ChatBtn
          @start-chat="onStartChat"
          :audio-source-callback="audioSourceCallback"
          :streamState="streamState"
          wave-color="#7873F6"
        />
      </template>
      
      <!-- 设备状态提示 -->
      <template v-if="!videoChatState.hasCamera && !webcamAccessed">
        <div style="text-align: center; margin-top: 20px;">
          <p style="color: #666; margin-bottom: 10px;">
            {{ isMobile ? '📱 移动设备：摄像头权限未授予' : '💻 桌面设备：摄像头权限未授予' }}
          </p>
          <button 
            @click="handleRecheckPermissions" 
            style="
              background: #7873F6; 
              color: white; 
              border: none; 
              border-radius: 8px; 
              padding: 12px 24px; 
              cursor: pointer;
              font-size: 14px;
              margin-bottom: 10px;
            "
          >
            🔄 重新检查权限
          </button>
          <div v-if="isMobile" style="font-size: 12px; color: #999;">
            注意：移动设备上屏幕共享功能不可用
          </div>
          <div v-else style="font-size: 12px; color: #999;">
            请在浏览器地址栏左侧允许摄像头权限
          </div>
        </div>
      </template>
    </div>
    <div
      v-if="streamState === 'open' && showChatRecords && isLandscape"
      class="chat-records-container"
    >
      <ChatRecords ref="chatRecordsInstanceRef" :chatRecords="chatRecords" />
    </div>

    <!-- 屏幕共享信息面板 -->
    <ScreenShareInfoPanel />
  </div>
</template>

<script setup lang="ts">
import ActionGroup from '@/components/ActionGroup.vue';
import ChatBtn from '@/components/ChatBtn.vue';
import ChatInput from '@/components/ChatInput.vue';
import ChatRecords from '@/components/ChatRecords.vue';
import ScreenShareInfoPanel from '@/components/ScreenShareInfoPanel.vue';
import { useVideoChatStore } from '@/store';
import { useVisionStore } from '@/store/vision';
import { useScreenShareStore } from '@/store/screenShareStore';
import { storeToRefs } from 'pinia';
import { computed, onMounted, ref, useTemplateRef } from 'vue';
const visionState = useVisionStore();
const videoChatState = useVideoChatStore();
const screenShareState = useScreenShareStore();
const wrapRef = ref<HTMLDivElement>();

const localVideoContainerRef = ref<HTMLDivElement>();
const remoteVideoContainerRef = ref<HTMLDivElement>();
const localVideoRef = ref<HTMLVideoElement>();
const remoteVideoRef = ref<HTMLVideoElement>();
const remoteAspectRatio = ref('9 / 16');
const onplayingRemoteVideo = () => {
  if (remoteVideoRef.value) {
    remoteAspectRatio.value = `${remoteVideoRef.value.videoWidth} / ${remoteVideoRef.value.videoHeight}`;
  }
};

const audioSourceCallback = () => {
  return videoChatState.localStream;
};

onMounted(async () => {
  const wrapperRef = wrapRef.value;
  visionState.wrapperRef = wrapperRef;
  wrapperRef!.getBoundingClientRect();
  wrapperRect.value.width = wrapperRef!.clientWidth;
  wrapperRect.value.height = wrapperRef!.clientHeight;
  visionState.isLandscape = wrapperRect.value.width > wrapperRect.value.height;
  console.log(wrapperRect);

  visionState.remoteVideoContainerRef = remoteVideoContainerRef.value;
  visionState.localVideoContainerRef = localVideoContainerRef.value;
  visionState.localVideoRef = localVideoRef.value;
  visionState.remoteVideoRef = remoteVideoRef.value;
  visionState.wrapperRef = wrapRef.value;

  // 初始化屏幕共享功能
  await screenShareState.initializeScreenShare();
});
const {
  hasCamera,
  hasMic,
  micMuted,
  cameraOff,
  webcamAccessed,
  streamState,
  avatarType,
  volumeMuted,
  replying,
  showChatRecords,
  chatRecords,
} = storeToRefs(videoChatState);
const { wrapperRect, isLandscape } = storeToRefs(visionState);

function onStartChat() {
  console.log('🚀 onStartChat 开始执行...');
  videoChatState.startWebRTC().then(() => {
    console.log('✅ startWebRTC 完成，检查 peerConnection...', {
      peerConnectionExists: !!videoChatState.peerConnection,
      connectionState: videoChatState.peerConnection?.connectionState
    });
    
    initChatDataChannel();
    
    // 将PeerConnection传递给屏幕共享store
    if (videoChatState.peerConnection) {
      console.log('📡 准备设置 PeerConnection 到 screenShareStore...');
      screenShareState.setPeerConnection(videoChatState.peerConnection);
      console.log('✅ setPeerConnection 调用完成');
    } else {
      console.error('❌ videoChatState.peerConnection 为空！');
    }
  }).catch((error) => {
    console.error('❌ startWebRTC 失败:', error);
  });
}

function initChatDataChannel() {
  if (!videoChatState.chatDataChannel) return;
  videoChatState.chatDataChannel.addEventListener('message', (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'chat') {
      const index = videoChatState.chatRecords.findIndex((item) => {
        return item.id === data.id;
      });
      if (index !== -1) {
        const item = videoChatState.chatRecords[index];
        item.message += data.message;
        videoChatState.chatRecords.splice(index, 1, item);
        videoChatState.chatRecords = [...videoChatState.chatRecords];
      } else {
        videoChatState.chatRecords = [
          ...videoChatState.chatRecords,
          {
            id: data.id,
            role: data.role || 'human', // TODO: 默认值测试后续删除
            message: data.message,
          },
        ];
      }
    } else if (data.type === 'avatar_end') {
      videoChatState.replying = false;
    }
  });
}

function onInterrupt() {
  if (videoChatState.chatDataChannel) {
    videoChatState.chatDataChannel.send(JSON.stringify({ type: 'stop_chat' }));
  }
}

const chatRecordsInstanceRef = useTemplateRef<any>('chatRecordsInstanceRef');
function onSend(message: string) {
  if (!message) return;
  if (!videoChatState.chatDataChannel) return;
  videoChatState.chatDataChannel.send(JSON.stringify({ type: 'chat', data: message }));
  videoChatState.replying = true;
  chatRecordsInstanceRef.value?.scrollToBottom();
}

// 检测是否为移动设备
const isMobile = computed(() => 
  /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
);

// 重新检查权限
async function handleRecheckPermissions() {
  await videoChatState.recheckPermissions();
}
</script>
<style lang="less" scoped>
@import './index.less';
</style>
