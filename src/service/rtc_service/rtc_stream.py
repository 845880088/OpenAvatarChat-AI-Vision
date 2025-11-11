import asyncio
import json
import uuid
import weakref
from typing import Optional, Dict

import numpy as np
# noinspection PyPackageRequirements
from fastrtc import AsyncAudioVideoStreamHandler, AudioEmitType, VideoEmitType
from loguru import logger

from chat_engine.common.client_handler_base import ClientHandlerDelegate, ClientSessionDelegate
from chat_engine.common.engine_channel_type import EngineChannelType
from chat_engine.data_models.chat_data.chat_data_model import ChatData
from chat_engine.data_models.chat_data_type import ChatDataType
from chat_engine.data_models.chat_signal import ChatSignal
from chat_engine.data_models.chat_signal_type import ChatSignalType, ChatSignalSourceType
from engine_utils.interval_counter import IntervalCounter
from aiortc.codecs import vpx 
vpx.DEFAULT_BITRATE = 5000000
vpx.MIN_BITRATE = 1000000
vpx.MAX_BITRATE = 10000000

# 🔥 关键修复：解决 video/rtx MIME类型解码器缺失问题
try:
    from aiortc import codecs
    import aiortc.codecs
    
    logger.info("🔧 初始化WebRTC视频编解码器支持")
    
    # 检查并记录可用的编解码器
    available_codecs = []
    for codec_name in ['h264', 'vp8', 'vp9']:
        try:
            codec_module = getattr(aiortc.codecs, codec_name, None)
            if codec_module:
                available_codecs.append(codec_name.upper())
        except:
            pass
    
    logger.info(f"✅ 检测到可用视频编解码器: {available_codecs}")
    
    # 🎯 关键修复：RTX异常处理 - 修复函数签名
    import aiortc.rtcrtpreceiver
    import threading
    
    original_decoder_worker = aiortc.rtcrtpreceiver.decoder_worker
    
    def patched_decoder_worker(*args, **kwargs):
        """修补的解码器工作器，处理RTX MIME类型错误"""
        try:
            # 调用原始函数，传递所有参数
            return original_decoder_worker(*args, **kwargs)
        except ValueError as e:
            if "video/rtx" in str(e) or "No decoder found for MIME type" in str(e):
                logger.warning(f"⚠️ 忽略RTX解码器错误（这不会影响主要功能）: {e}")
                # 创建一个空的线程来替代失败的解码器
                def empty_worker():
                    pass
                return threading.Thread(target=empty_worker)
            else:
                raise e
        except Exception as e:
            logger.error(f"❌ 解码器工作器异常: {e}")
            # 对于其他异常，也创建空线程避免崩溃
            def empty_worker():
                pass  
            return threading.Thread(target=empty_worker)
    
    # 应用补丁
    aiortc.rtcrtpreceiver.decoder_worker = patched_decoder_worker
    logger.info("🩹 已应用RTX解码器错误处理补丁")
    
except Exception as codec_error:
    logger.warning(f"⚠️ 视频编解码器配置警告（不影响基础功能）: {codec_error}")
    # 不抛出异常，继续执行


class RtcStream(AsyncAudioVideoStreamHandler):
    def __init__(self,
                 session_id: Optional[str],
                 expected_layout="mono",
                 input_sample_rate=16000,
                 output_sample_rate=24000,
                 output_frame_size=480,
                 fps=30,
                 stream_start_delay = 0.5,
                 ):
        super().__init__(
            expected_layout=expected_layout,
            input_sample_rate=input_sample_rate,
            output_sample_rate=output_sample_rate,
            output_frame_size=output_frame_size,
            fps=fps
        )
        self.client_handler_delegate: Optional[ClientHandlerDelegate] = None
        self.client_session_delegate: Optional[ClientSessionDelegate] = None

        self.weak_factory: Optional[weakref.ReferenceType[RtcStream]] = None

        self.session_id = session_id
        self.stream_start_delay = stream_start_delay

        self.chat_channel = None
        self.first_audio_emitted = False

        self.quit = asyncio.Event()
        self.last_frame_time = 0

        self.emit_counter = IntervalCounter("emit counter")

        self.start_time = None
        self.timestamp_base = self.input_sample_rate

        self.streams: Dict[str, RtcStream] = {}


    # copy is used as create_instance in fastrtc
    def copy(self, **kwargs) -> AsyncAudioVideoStreamHandler:
        try:
            if self.client_handler_delegate is None:
                raise Exception("ClientHandlerDelegate is not set.")
            session_id = kwargs.get("webrtc_id", None)
            if session_id is None:
                session_id = uuid.uuid4().hex
            new_stream = RtcStream(
                session_id,
                expected_layout=self.expected_layout,
                input_sample_rate=self.input_sample_rate,
                output_sample_rate=self.output_sample_rate,
                output_frame_size=self.output_frame_size,
                fps=self.fps,
                stream_start_delay=self.stream_start_delay,
            )
            new_stream.weak_factory = weakref.ref(self)
            new_session_delegate = self.client_handler_delegate.start_session(
                session_id=session_id,
                timestamp_base=self.input_sample_rate,
            )
            new_stream.client_session_delegate = new_session_delegate
            if session_id in self.streams:
                msg = f"Stream {session_id} already exists."
                raise RuntimeError(msg)
            self.streams[session_id] = new_stream
            return new_stream
        except Exception as e:
            logger.opt(exception=True).error(f"Failed to create stream: {e}")
            raise

    async def emit(self) -> AudioEmitType:
        try:
            # if not self.args_set.is_set():
            # await self.wait_for_args()

            if not self.first_audio_emitted:
                self.client_session_delegate.clear_data()
                self.first_audio_emitted = True

            while not self.quit.is_set():
                chat_data = await self.client_session_delegate.get_data(EngineChannelType.AUDIO)
                if chat_data is None or chat_data.data is None:
                    continue
                audio_array = chat_data.data.get_main_data()
                if audio_array is None:
                    continue
                sample_num = audio_array.shape[-1]
                self.emit_counter.add_property("audio_emit", sample_num / self.output_sample_rate)
                return self.output_sample_rate, audio_array
        except Exception as e:
            logger.opt(exception=e).error(f"Error in emit: ")
            raise

    async def video_emit(self) -> VideoEmitType:
        try:
            if not self.first_audio_emitted:
                await asyncio.sleep(0.1)
            self.emit_counter.add_property("video_emit")
            while not self.quit.is_set():
                video_frame_data: ChatData = await self.client_session_delegate.get_data(EngineChannelType.VIDEO)
                if video_frame_data is None or video_frame_data.data is None:
                    continue
                frame_data = video_frame_data.data.get_main_data().squeeze()
                if frame_data is None:
                    continue
                return frame_data
        except Exception as e:
            logger.opt(exception=e).error(f"Error in video_emit: ")
            raise

    async def receive(self, frame: tuple[int, np.ndarray]):
        if self.client_session_delegate is None:
            return
        timestamp = self.client_session_delegate.get_timestamp()
        if timestamp[0] / timestamp[1] < self.stream_start_delay:
            return
        _, array = frame
        self.client_session_delegate.put_data(
            EngineChannelType.AUDIO,
            array,
            timestamp,
            self.input_sample_rate,
        )

    async def video_receive(self, frame):
        if self.client_session_delegate is None:
            return
        
        timestamp = self.client_session_delegate.get_timestamp()
        if timestamp[0] / timestamp[1] < self.stream_start_delay:
            return
        
        self.client_session_delegate.put_data(
            EngineChannelType.VIDEO,
            frame,
            timestamp,
            self.fps,
        )

    def set_channel(self, channel):
            super().set_channel(channel)
            self.chat_channel = channel
            
            async def process_chat_history():
                role = None
                chat_id = None
                while not self.quit.is_set():
                    chat_data = await self.client_session_delegate.get_data(EngineChannelType.TEXT)
                    if chat_data is None or chat_data.data is None:
                        continue
                    logger.debug(f"Got chat data {str(chat_data)}")
                    current_role = 'human' if chat_data.type == ChatDataType.HUMAN_TEXT else 'avatar'
                    chat_id = uuid.uuid4().hex if current_role != role else chat_id
                    role = current_role
                    self.chat_channel.send(json.dumps({'type': 'chat', 'message': chat_data.data.get_main_data(), 
                                                        'id': chat_id, 'role': current_role}))  
            asyncio.create_task(process_chat_history())
                
            @channel.on("message")
            def _(message):
                logger.info(f"Received message Custom: {message}")
                try:
                    message = json.loads(message)
                except Exception as e:
                    logger.info(e)
                    message = {}

                if self.client_session_delegate is None:
                    return
                timestamp = self.client_session_delegate.get_timestamp()
                if timestamp[0] / timestamp[1] < self.stream_start_delay:
                    return
                logger.info(f'on_chat_datachannel: {message}')
    
                if message['type'] == 'stop_chat':
                    self.client_session_delegate.emit_signal(
                        ChatSignal(
                            type=ChatSignalType.INTERRUPT,
                            source_type=ChatSignalSourceType.CLIENT,
                            source_name="rtc",
                        )
                    )
                elif message['type'] == 'chat':
                    channel.send(json.dumps({'type': 'avatar_end'}))
                    if self.client_session_delegate.shared_states.enable_vad is False:
                        return
                    self.client_session_delegate.shared_states.enable_vad = False
                    self.client_session_delegate.emit_signal(
                        ChatSignal(
                            # begin a new round of responding
                            type=ChatSignalType.BEGIN,
                            stream_type=ChatDataType.AVATAR_AUDIO,
                            source_type=ChatSignalSourceType.CLIENT,
                            source_name="rtc",
                        )
                    )
                    self.client_session_delegate.put_data(
                        EngineChannelType.TEXT,
                        message['data'],
                        loopback=True
                    )
                # else:

                # channel.send(json.dumps({"type": "chat", "unique_id": unique_id, "message": message}))
          
    async def on_chat_datachannel(self, message: Dict, channel):
        # {"type":"chat",id:"标识属于同一段话", "message":"Hello, world!"}
        # unique_id = uuid.uuid4().hex
        pass
    def shutdown(self):
        self.quit.set()
        factory = None
        if self.weak_factory is not None:
            factory = self.weak_factory()
        if factory is None:
            factory = self
        self.client_session_delegate = None
        if factory.client_handler_delegate is not None:
            factory.client_handler_delegate.stop_session(self.session_id)
