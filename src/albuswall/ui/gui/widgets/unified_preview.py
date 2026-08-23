#
""""""

from enum import Enum, auto
from typing import Final

from PySide6.QtCore import Qt, QUrl, QByteArray, QIODevice
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
from PySide6.QtMultimedia import (
    QMediaPlayer,
    QAudioOutput,
    QAudioBufferOutput,
    QAudioSink,
    QAudioBuffer,
    QAudioFormat,
    QAudio,
)


class MediaType(Enum):
    NONE = auto()
    IMAGE = auto()
    VIDEO = auto()


# ---------- Default value ----------
DISABLE_AUTO_FIT_AFTER_LOAD: Final[bool] = False
DISABLE_FIT_ON_RESIZE: Final[bool] = False
DEFAULT_FIT_MODE = Qt.KeepAspectRatio

DEFAULT_VOLUME = 1.0
DEFAULT_MUTED = False

LOOP_COUNT = 1
DEFAULT_PLAYBACK_RATE = 1.0

MAX_GAIN = 10.0
DEFAULT_GAIN_DISABLED = False


class UnifiedPreview(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.video_item = QGraphicsVideoItem()
        self.player = QMediaPlayer()
        self.player.setVideoOutput(self.video_item)

        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)

        self._volume = DEFAULT_VOLUME
        self._muted = DEFAULT_MUTED
        self._playback_rate = DEFAULT_PLAYBACK_RATE
        self._loops = LOOP_COUNT

        # ----- 使用常量初始化禁用状态 -----
        self._disable_auto_fit_after_load = DISABLE_AUTO_FIT_AFTER_LOAD
        self._disable_fit_on_resize = DISABLE_FIT_ON_RESIZE
        self._fit_mode = DEFAULT_FIT_MODE

        self._gain_disabled = DEFAULT_GAIN_DISABLED
        self._gain_supported = True
        self._buffer_out: QAudioBufferOutput | None = None
        self._gain_sink: QAudioSink | None = None
        self._gain_device: QIODevice | None = None

        self.audio.setVolume(min(self._volume, 1.0))
        self.audio.setMuted(self._muted)
        self.player.setPlaybackRate(self._playback_rate)
        self.player.setLoops(self._loops)

        self.current_item = None
        self.current_type = MediaType.NONE

    # ---------- 配置接口 ----------
    def set_volume(self, volume: float):
        self._volume = max(0.0, min(volume, MAX_GAIN))
        self._update_audio_output()

    def set_muted(self, muted: bool):
        self._muted = muted
        if self._gain_device is not None and self._gain_sink is not None:
            self._gain_sink.setVolume(0.0 if muted else 1.0)
        else:
            self.audio.setMuted(muted)

    def set_playback_rate(self, rate: float):
        self._playback_rate = rate
        self.player.setPlaybackRate(rate)

    def set_loops(self, loops: int):
        self._loops = loops
        self.player.setLoops(loops)

    def set_fit_mode(self, mode: Qt.AspectRatioMode):
        self._fit_mode = mode

    # ----- 重命名后的 setter，参数语义为“是否禁用” -----
    def set_disable_fit_on_resize(self, disabled: bool):
        self._disable_fit_on_resize = disabled

    def set_disable_auto_fit_after_load(self, disabled: bool):
        self._disable_auto_fit_after_load = disabled

    def set_gain_disabled(self, disabled: bool):
        self._gain_disabled = disabled
        self._update_audio_output()

    # ---------- 音频管线管理 ----------
    def _update_audio_output(self):
        need_gain = (not self._gain_disabled) and self._gain_supported and (self._volume > 1.0)
        if need_gain:
            self._setup_gain_pipeline()
        else:
            self._teardown_gain_pipeline()
            safe_vol = min(self._volume, 1.0)
            self.audio.setVolume(safe_vol)
            self.audio.setMuted(self._muted)

    def _setup_gain_pipeline(self):
        if self._buffer_out is not None and self._gain_device is not None:
            if self.player.audioOutput() is not self._buffer_out:
                self.player.setAudioOutput(self._buffer_out)  # type: ignore[arg-type]
            self._ensure_gain_device_running()
            return

        try:
            self._buffer_out = QAudioBufferOutput()
            self._buffer_out.setParent(self)

            fmt = QAudioFormat()
            fmt.setSampleRate(44100)
            fmt.setChannelCount(2)
            fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
            self._gain_sink = QAudioSink(fmt, self)
            self._gain_sink.setVolume(0.0 if self._muted else 1.0)

            self._gain_device = self._gain_sink.start()
            if self._gain_device is None:
                raise RuntimeError("QAudioSink.start() 返回 None")

            self.player.setAudioOutput(self._buffer_out)  # type: ignore[arg-type]
            self._buffer_out.audioBufferReceived.connect(self._process_audio_buffer)

        except Exception as e:
            print(f"警告：增益功能不可用 ({e})，已回退到普通音频输出。")
            self._gain_supported = False
            self._teardown_gain_pipeline()

    def _ensure_gain_device_running(self):
        if self._gain_sink is not None and self._gain_sink.state() != QAudio.State.ActiveState:
            self._gain_device = self._gain_sink.start()

    def _teardown_gain_pipeline(self):
        if self._buffer_out is not None:
            self._buffer_out.audioBufferReceived.disconnect()
            self._buffer_out.deleteLater()
            self._buffer_out = None
        if self._gain_sink is not None:
            self._gain_sink.stop()
            self._gain_sink.deleteLater()
            self._gain_sink = None
        self._gain_device = None
        self.player.setAudioOutput(self.audio)

    def _process_audio_buffer(self, buffer: QAudioBuffer):
        if self._gain_device is None or self._gain_sink is None:
            return
        if self._gain_sink.state() != QAudio.State.ActiveState:
            return

        data_bytes = buffer.constData()
        byte_count = buffer.byteCount()
        data = QByteArray(data_bytes[:byte_count])
        gain = self._volume
        fmt = buffer.format()

        if fmt.sampleFormat() == QAudioFormat.SampleFormat.Int16:
            ptr = memoryview(data).cast('h')  # type: ignore[assignment]
            for i in range(len(ptr)):
                val = int(ptr[i]) * gain
                ptr[i] = max(-32768, min(32767, int(val)))  # type: ignore[index]
        elif fmt.sampleFormat() == QAudioFormat.SampleFormat.Int32:
            ptr = memoryview(data).cast('i')  # type: ignore[assignment]
            for i in range(len(ptr)):
                val = int(ptr[i]) * gain
                ptr[i] = max(-2147483648, min(2147483647, int(val)))  # type: ignore[index]
        elif fmt.sampleFormat() == QAudioFormat.SampleFormat.Float:
            ptr = memoryview(data).cast('f')  # type: ignore[assignment]
            for i in range(len(ptr)):
                val = float(ptr[i]) * gain
                ptr[i] = max(-1.0, min(1.0, val))  # type: ignore[index]
        else:
            return

        self._gain_device.write(data)

    # ---------- 媒体展示 ----------
    def show_image(self, path: str):
        self._clear_scene()
        pixmap = QPixmap(path)
        self.current_item = self.scene.addPixmap(pixmap)
        self.current_type = MediaType.IMAGE
        if not self._disable_auto_fit_after_load:
            self.fit_in_view()

    def show_video(self, path: str):
        self._clear_scene()
        self.video_item = QGraphicsVideoItem()
        self.scene.addItem(self.video_item)
        self.current_item = self.video_item
        self.current_type = MediaType.VIDEO

        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(path))
        self._update_audio_output()
        self.player.play()

        if not self._disable_auto_fit_after_load:
            self.fit_in_view()

    def fit_in_view(self):
        if self.current_item:
            self.fitInView(self.current_item, self._fit_mode)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._disable_fit_on_resize:
            self.fit_in_view()

    def _clear_scene(self):
        self.player.stop()
        self.scene.clear()
        self.current_item = None
        self.current_type = MediaType.NONE
