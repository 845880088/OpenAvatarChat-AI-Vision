/**
 * 屏幕共享工具函数 - OpenAvatarChat-WebUI版本
 * 基于云服务器TURN基础设施优化 (8.138.87.249:3478)
 */

export interface ScreenShareOptions {
  video: boolean | MediaTrackConstraints;
  audio: boolean | MediaTrackConstraints;
  displaySurface?: 'browser' | 'window' | 'monitor';
  quality: 'ai-compatible' | 'mobile' | 'desktop' | 'high-bandwidth';
  turnOptimized: boolean;
}

/**
 * 云服务器优化的质量配置
 * 基于2vCPU/4GiB云服务器能力调整
 */
export const QUALITY_PRESETS = {
  'ai-compatible': {
    video: {
      width: { ideal: 500, max: 800 },      // 🎯 优化AI识别，支持范围调整
      height: { ideal: 500, max: 800 },     // 🎯 正方形优先，允许适度放大
      frameRate: { ideal: 30, max: 60 },    // 🎯 匹配摄像头帧率
      cursor: 'always',
      displaySurface: 'monitor'
    } as MediaTrackConstraints,
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      systemAudio: true
    } as MediaTrackConstraints
  },
  mobile: {
    video: {
      width: { ideal: 720, max: 960 },
      height: { ideal: 480, max: 640 },
      frameRate: { ideal: 8, max: 12 },
      cursor: 'always',
      displaySurface: 'window'
    } as MediaTrackConstraints,
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      systemAudio: false
    } as MediaTrackConstraints
  },
  desktop: {
    video: {
      width: { ideal: 1280, max: 1600 },
      height: { ideal: 720, max: 900 },
      frameRate: { ideal: 15, max: 20 },
      cursor: 'always',
      displaySurface: 'monitor'
    } as MediaTrackConstraints,
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      systemAudio: true
    } as MediaTrackConstraints
  },
  'high-bandwidth': {
    video: {
      width: { ideal: 1920, max: 2560 },
      height: { ideal: 1080, max: 1440 },
      frameRate: { ideal: 15, max: 24 },
      cursor: 'always',
      displaySurface: 'monitor'
    } as MediaTrackConstraints,
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      systemAudio: true
    } as MediaTrackConstraints
  }
};

/**
 * 获取优化的屏幕共享流
 */
export async function getOptimizedDisplayStream(
  options: ScreenShareOptions
): Promise<MediaStream> {
  
  const deviceType = detectDeviceType();
  const qualityPreset = options.quality || (deviceType === 'mobile' ? 'mobile' : 'desktop');
  
  const constraints: any = {
    video: typeof options.video === 'object' 
      ? { ...QUALITY_PRESETS[qualityPreset].video, ...options.video }
      : QUALITY_PRESETS[qualityPreset].video,
    audio: typeof options.audio === 'object'
      ? { ...QUALITY_PRESETS[qualityPreset].audio, ...options.audio }
      : QUALITY_PRESETS[qualityPreset].audio
  };

  try {
    console.log('🚀 开始屏幕捕获，质量预设:', qualityPreset);
    console.log('📊 约束配置:', constraints);
    
    const displayStream = await navigator.mediaDevices.getDisplayMedia(constraints);
    
    // 监听用户停止共享事件
    displayStream.getVideoTracks()[0].addEventListener('ended', () => {
      console.log('🛑 用户停止屏幕共享');
      window.dispatchEvent(new CustomEvent('screenShareEnded'));
    });
    
    return displayStream;
  } catch (error) {
    console.error('❌ 屏幕捕获失败:', error);
    throw new ScreenShareError('屏幕捕获失败', error as Error);
  }
}

/**
 * 检测设备类型
 */
function detectDeviceType(): 'mobile' | 'tablet' | 'desktop' {
  const userAgent = navigator.userAgent;
  
  if (/Android|iPhone|iPod/.test(userAgent)) {
    return 'mobile';
  } else if (/iPad/.test(userAgent)) {
    return 'tablet';  
  } else {
    return 'desktop';
  }
}

/**
 * 屏幕共享错误类
 */
export class ScreenShareError extends Error {
  constructor(message: string, public originalError?: Error) {
    super(message);
    this.name = 'ScreenShareError';
  }
}

/**
 * 连接质量监控
 */
export class ConnectionMonitor {
  private peerConnection: RTCPeerConnection | null = null;
  private qualityCheckInterval: number | null = null;
  private onQualityChange?: (quality: ConnectionQuality) => void;
  
  constructor(pc: RTCPeerConnection, callback?: (quality: ConnectionQuality) => void) {
    this.peerConnection = pc;
    this.onQualityChange = callback;
    this.startMonitoring();
  }
  
  private startMonitoring() {
    this.qualityCheckInterval = window.setInterval(() => {
      this.checkConnectionQuality();
    }, 3000);
  }
  
  private async checkConnectionQuality() {
    if (!this.peerConnection) return;
    
    try {
      const stats = await this.peerConnection.getStats();
      const quality = this.analyzeStats(stats);
      
      if (this.onQualityChange) {
        this.onQualityChange(quality);
      }
    } catch (error) {
      console.error('连接质量检查失败:', error);
    }
  }
  
  private analyzeStats(stats: RTCStatsReport): ConnectionQuality {
    let bytesReceived = 0;
    let bytesSent = 0;
    let packetsLost = 0;
    let rtt = 0;
    
    stats.forEach((report) => {
      if (report.type === 'inbound-rtp' && report.kind === 'video') {
        bytesReceived += report.bytesReceived || 0;
        packetsLost += report.packetsLost || 0;
      }
      if (report.type === 'outbound-rtp' && report.kind === 'video') {
        bytesSent += report.bytesSent || 0;
      }
      if (report.type === 'remote-inbound-rtp' && report.kind === 'video') {
        rtt = report.roundTripTime || 0;
      }
    });
    
    const bandwidth = (bytesReceived + bytesSent) / 1024;
    const packetLossRate = packetsLost / (packetsLost + 100);
    
    if (bandwidth > 500 && rtt < 100 && packetLossRate < 0.01) {
      return 'excellent';
    } else if (bandwidth > 200 && rtt < 200 && packetLossRate < 0.05) {
      return 'good';
    } else if (bandwidth > 50 && rtt < 500) {
      return 'fair';
    } else {
      return 'poor';
    }
  }
  
  stopMonitoring() {
    if (this.qualityCheckInterval) {
      clearInterval(this.qualityCheckInterval);
      this.qualityCheckInterval = null;
    }
  }
}

export type ConnectionQuality = 'excellent' | 'good' | 'fair' | 'poor';

/**
 * 检查浏览器屏幕共享支持
 */
export function checkScreenShareSupport(): {
  supported: boolean;
  reason?: string;
} {
  if (!navigator.mediaDevices) {
    return {
      supported: false,
      reason: '浏览器不支持 MediaDevices API'
    };
  }
  
  if (!navigator.mediaDevices.getDisplayMedia) {
    return {
      supported: false,
      reason: '浏览器不支持 getDisplayMedia API'
    };
  }
  
  if (!window.isSecureContext) {
    return {
      supported: false,
      reason: '需要HTTPS或localhost环境'
    };
  }
  
  return { supported: true };
}

/**
 * 格式化带宽显示
 */
export function formatBandwidth(bytes: number): string {
  if (bytes < 1024) return `${bytes} B/s`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB/s`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB/s`;
}

/**
 * 获取质量描述
 */
export function getQualityDescription(quality: string): string {
  switch (quality) {
    case 'ai-compatible':
      return 'AI兼容 (500x500@30fps)';
    case 'mobile':
      return '移动优化 (720p@8fps)';
    case 'desktop':
      return '桌面标准 (1080p@15fps)';
    case 'high-bandwidth':
      return '高质量 (1080p@24fps)';
    default:
      return '未知质量';
  }
}

/**
 * 获取质量建议
 */
export function getQualityHint(quality: string): string {
  switch (quality) {
    case 'ai-compatible':
      return '🎯 优化AI识别，500x500分辨率，推荐默认选择';
    case 'mobile':
      return '适用于移动网络，低带宽消耗';
    case 'desktop':
      return '平衡质量与性能，1080p标准分辨率';
    case 'high-bandwidth':
      return '高质量，需要良好网络环境';
    default:
      return '';
  }
}
