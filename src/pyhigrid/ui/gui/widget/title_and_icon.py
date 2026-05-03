#
""""""

from pathlib import Path
from typing import TypedDict, Tuple, Optional

from PySide6.QtCore import Qt, QMargins
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QSizePolicy

TITLE_MAX_WIDTH = 400
ENABLE_TITLE_OVERLENGTH_PROCESSING = True

class TitleAndIconConfig(TypedDict, total=False):
    """
    非样式配置项。视觉属性（颜色、字体、背景等）请通过 QSS 样式表控制。
    """
    # 内容
    icon_text: str | Path | None  # 图标文本（如 emoji）或图片路径
    title_text: str  # 标题文字
    subtitle_text: str  # 副标题文字

    # 尺寸限制
    icon_size: int  # 图标固定宽高，默认 64
    title_max_width: int  # 标题单行最大宽度，默认 400
    max_total_width: int  # 组件整体最大宽度，默认 465
    subtitle_max_height: int # 副标题最大高度，默认 24

    # 行为
    title_elide: bool  # 标题过长时是否显示省略号，默认 True

    # 布局
    spacing: int  # 网格间距，默认 0
    margins: Tuple[int, int, int, int] | QMargins

class TitleAndIcon(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon_label = None
        self.title_label = None
        self.subtitle_label = None

        # statu
        self._max_title_width = TITLE_MAX_WIDTH
        self._title_elide = ENABLE_TITLE_OVERLENGTH_PROCESSING

        # cache
        self._full_title = ""
        self._max_total_width = 465
        self._subtitle_max_height = 24

        self.setup_()
        self.setup_ui()

    def setup_(self):
        self._max_title_width = TITLE_MAX_WIDTH
        self._title_elide = ENABLE_TITLE_OVERLENGTH_PROCESSING
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.setMinimumSize(1, 1)

    def setup_ui(self):
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 0)
        self.setLayout(layout)

        self.icon_label = QLabel(self)
        self.title_label = QLabel(self)
        self.subtitle_label = QLabel(self)

        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.icon_label.setFixedSize(64, 64)
        self.icon_label.setObjectName("IconLabel")

        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(False)
        self.title_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.title_label.setObjectName("TitleLabel")

        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.subtitle_label.setObjectName("SubtitleLabel")

        layout.addWidget(self.icon_label, 0, 0)
        layout.addWidget(self.title_label, 0, 1)
        layout.addWidget(self.subtitle_label, 2, 0, 1, 2)

        self.setStyleSheet("""
        TitleAndIcon {
            background-color: yellow;
            min-width: 1px;
            max-width: 465px;     
            min-height: 1px;
            max-height: 88px;
        }
        QLabel#IconLabel { font-size: 48px; }
        QLabel#TitleLabel { font-size: 48px; }
        QLabel#SubtitleLabel {
            font-size: 16px;
            color: grey;
            min-width: 1px;
            max-width: 600px;
            min-height: 1px;
            max-height: 24px;
        }
        """)

        if __debug__:
            self.set_icon("🪟")
            self.set_title("title")
            self.set_subtitle("subtitle")

    # API
    def set_icon(self, text):
        """设置图标，可以是 Unicode 文本或纯文本（如 emoji）"""
        if not text:
            self.icon_label.hide()
        else:
            self.icon_label.setText(text)
            self.icon_label.show()
        self._update_whole_size()

    def set_subtitle(self, text):
        """设置副标题"""
        self.subtitle_label.setText(text)
        self._update_whole_size()

    def set_title(self, text):
        """设置标题，并自动处理可能的超长省略"""
        self._full_title = text
        self._update_title_width()
        self._update_whole_size()

    # calc
    def _update_title_width(self):
        """令标题 Label 刚好包住整行文字，超出最大宽度时进行省略处理"""
        # 先用完整文本计算自然宽度
        self.title_label.setText(self._full_title)
        self.title_label.adjustSize()
        width = self.title_label.sizeHint().width()

        if width > self._max_title_width:
            width = self._max_title_width
            if self._title_elide:
                # 生成省略文本，不改变存储的完整标题
                elided = self.title_label.fontMetrics().elidedText(
                    self._full_title, Qt.ElideRight, width
                )
                self.title_label.setText(elided)
        self.title_label.setFixedWidth(width)

    def _update_whole_size(self):
        """根据内部控件实际大小，调整整个组件为刚好包住"""
        self.icon_label.adjustSize()
        self.title_label.adjustSize()
        self.subtitle_label.adjustSize()

        if self.icon_label.isVisible():
            total = (self.icon_label.sizeHint().width() +
                     self.title_label.sizeHint().width())
        else:
            total = self.title_label.sizeHint().width()
        if total > self._max_total_width:
            total = self._max_total_width
        self.setFixedWidth(total)

        # 简单取布局的推荐高度
        self.setFixedHeight(self.sizeHint().height())

    # conf
    def configure(self, config: Optional[TitleAndIconConfig] = None) -> None:
        """
        应用配置字典，典型调用方式：
            my_title.configure(config_dict)
        或传入 None 则不做任何修改。
        """
        if config is None:
            return

        # 内容
        if "icon_text" in config:
            val = config["icon_text"]
            if isinstance(val, Path):
                pixmap = QPixmap(str(val))
                self.icon_label.setPixmap(pixmap.scaled(
                    self.icon_label.sizeHint().width(),
                    self.icon_label.sizeHint().height(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
            else:
                self.set_icon(val)

        if "title_text" in config:
            self.set_title(config["title_text"])

        if "subtitle_text" in config:
            self.set_subtitle(config["subtitle_text"])

        # 尺寸调整
        if "icon_size" in config:
            self.icon_label.setFixedSize(config["icon_size"], config["icon_size"])

        need_title_update = False
        if "title_max_width" in config:
            self._max_title_width = config["title_max_width"]
            need_title_update = True

        if "title_elide" in config:
            self._title_elide = config["title_elide"]
            need_title_update = True

        if need_title_update:
            # 用保存的完整标题重新计算显示
            self._update_title_width()

        if "max_total_width" in config:
            self._max_total_width = config["max_total_width"]

        if "subtitle_max_height" in config:
            self._subtitle_max_height = config["subtitle_max_height"]
            self.subtitle_label.setMaximumHeight(config["subtitle_max_height"])

        if "spacing" in config:
            self.layout().setSpacing(config["spacing"])

        if "margins" in config:
            margins = config["margins"]
            if isinstance(margins, tuple):
                # noinspection PyArgumentList
                self.layout().setContentsMargins(*margins)
            else:
                self.layout().setContentsMargins(margins)

        # 统一刷新整体尺寸
        self._update_whole_size()


if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout

    app = QApplication(sys.argv)

    window = QWidget()
    title = TitleAndIcon(window)

    # 外部布局：让 TitleAndIcon 居中
    v_layout = QVBoxLayout(window)
    v_layout.setContentsMargins(0, 0, 0, 0)
    v_layout.setSpacing(0)
    v_layout.addWidget(title)
    v_layout.addStretch()

    h_layout = QHBoxLayout()
    h_layout.setContentsMargins(0, 0, 0, 0)
    h_layout.setSpacing(0)
    h_layout.addLayout(v_layout)
    h_layout.addStretch()
    window.setLayout(h_layout)

    window.show()

    # title.set_title("A Very Long Title That Should Fit Perfectly")
    title.set_icon("🪟")
    title.set_title("Title")
    title.set_subtitle("subtitle")
    # title.set_subtitle("subtitle")

    app.exec()