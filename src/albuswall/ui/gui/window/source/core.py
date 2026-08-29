#
""""""

from PySide6.QtCore import Qt, Signal, QModelIndex
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout, QSizePolicy, QWidget,
    QPushButton, QScrollArea, QSplitter, QVBoxLayout
)

try:
    from .detail_widget import IngestSourceDetailWidget
    from ...widgets.blur_overlay_label import BlurLabel
    from ...widgets.column_list_view import ColumnListView
    from ...delegates.source_card_delegate import SourceCardDelegate
    from ...modles.source_card import SourceCard
except ImportError:
    from albuswall.ui.gui.window.source.detail_widget import IngestSourceDetailWidget
    from albuswall.ui.gui.widgets.blur_overlay_label import BlurLabel
    from albuswall.ui.gui.widgets.column_list_view import ColumnListView
    from albuswall.ui.gui.delegates.source_card_delegate import SourceCardDelegate
    from albuswall.ui.gui.models.source_card import SourceCard


class Source(BlurLabel):
    card_clicked = Signal(QModelIndex)

    main_layout: QVBoxLayout
    splitter: QSplitter

    #
    content_layout: QHBoxLayout
    add_button_layout: QHBoxLayout
    close_button: QPushButton
    apply_button: QPushButton
    add_button: QPushButton

    #
    card_view: ColumnListView

    #
    detail_container: QWidget
    detail_layout: QVBoxLayout

    close_detail_btn_layout: QHBoxLayout
    close_detail_btn: QPushButton

    detail_widget_container: QWidget
    detail_widget: IngestSourceDetailWidget
    detail_widget_container_layout: QVBoxLayout

    scroll_area: QScrollArea

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.delegate = None
        self.model = None
        self._detail_mode = False

        self.setObjectName("IngestSource")

        self._setup_ui()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)

        self.close_button = QPushButton("x", self)
        self.apply_button = QPushButton(self.tr("apply"), self)
        self.add_button = QPushButton(self.tr("add"), self)

        self.content_layout = QHBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setStretchFactor(0, 1)  # 卡片视图占据主要伸缩空间
        self.splitter.setStretchFactor(1, 0)  # 详情容器保持固定宽度

        #
        self.card_view = ColumnListView()
        self.card_view.set_column_count(2)
        self.card_view.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.card_view.clicked.connect(self._on_card_clicked)

        #
        self.detail_container = QWidget()
        self.detail_container.setMinimumWidth(200)
        self.detail_container.hide()

        self.detail_layout = QVBoxLayout(self.detail_container)
        self.detail_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_layout.setSpacing(0)

        self.close_detail_btn_layout = QHBoxLayout()
        self.close_detail_btn_layout.setContentsMargins(8, 8, 8, 0)

        self.close_detail_btn = QPushButton("×")
        self.close_detail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_detail_btn.setObjectName("SourceCloseDetailButton")
        self.close_detail_btn.clicked.connect(self._on_close_detail)

        self.close_detail_btn_layout.addStretch(1)  # 将按钮推到右侧
        self.close_detail_btn_layout.addWidget(self.close_detail_btn)

        self.detail_widget_container = QWidget()
        self.detail_widget = IngestSourceDetailWidget(self.detail_widget_container)
        self.detail_widget_container_layout = QVBoxLayout(self.detail_widget_container)
        self.detail_widget_container_layout.addWidget(self.detail_widget)  # 详情控件
        self.detail_widget_container_layout.addStretch()  # 内容靠上，底部留白

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_area.setWidget(self.detail_widget_container)

        self.detail_layout.addLayout(self.close_detail_btn_layout)
        self.detail_layout.addWidget(self.apply_button)
        self.detail_layout.addWidget(self.scroll_area, 1)  # 滚动区占据剩余空间

        self.splitter.addWidget(self.card_view)
        self.splitter.addWidget(self.detail_container)
        self.splitter.setSizes([800, 360])  # 初始宽度比例

        self.content_layout.addWidget(self.splitter)

        self.add_button_layout = QHBoxLayout()

        self.add_button_layout.addStretch()
        self.add_button_layout.addWidget(self.add_button)

        self.main_layout.addWidget(self.close_button)
        self.main_layout.addLayout(self.add_button_layout)
        self.main_layout.addLayout(self.content_layout)

    def set_model(self, model, delegate):
        """设置数据模型和委托，供外部调用"""
        self.model = model
        self.delegate = delegate
        self.card_view.setModel(model)
        self.card_view.setItemDelegate(delegate)

    # noinspection PyUnusedLocal
    def _on_card_clicked(self, index):
        if not self._detail_mode:
            self._detail_mode = True
            self.card_view.set_column_count(1)
            self.detail_container.show()

            total_width = max(self.width(), 500)
            card_width = int(total_width * 0.3)
            detail_width = total_width - card_width
            self.splitter.setSizes([card_width, detail_width])

        self.card_clicked.emit(index)

    def _on_close_detail(self):
        if self._detail_mode:
            self._detail_mode = False
            self.card_view.set_column_count(2)
            self.detail_container.hide()
            self.card_view.clearSelection()

    if __debug__:
        def setup_tests(self):
            model = SourceCard()
            model.add_card("我的照片", "/home/user/Picture", "daily", ["media"])
            model.add_card("项目文档", "/home/user/docs", "需求、设计文档", ["文档", "重要"])
            model.add_card("代码仓库", "/home/user/code", "源代码管理", ["代码", "Git"])
            model.add_card("音乐收藏", "/home/user/music", "无损音乐", ["音乐", "娱乐"])
            model.add_card("下载内容", "/home/user/downloads", "临时文件", ["下载"])
            model.add_card("桌面背景", "/home/user/pictures/wallpaper", "壁纸图片", ["图片"])

            delegate = SourceCardDelegate()
            self.set_model(model, delegate)


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = QWidget()
    widget = Source(window)

    # 非 UI 数据准备：创建模型、添加示例数据、配置委托
    model_ = SourceCard()
    model_.add_card("我的照片", "/home/user/Picture", "daily", ["media"])
    model_.add_card("项目文档", "/home/user/docs", "需求、设计文档", ["文档", "重要"])
    model_.add_card("代码仓库", "/home/user/code", "源代码管理", ["代码", "Git"])
    model_.add_card("音乐收藏", "/home/user/music", "无损音乐", ["音乐", "娱乐"])
    model_.add_card("下载内容", "/home/user/downloads", "临时文件", ["下载"])
    model_.add_card("桌面背景", "/home/user/pictures/wallpaper", "壁纸图片", ["图片"])

    # 委托样式配置
    config = {
        "card_margin": 10,
        "card_padding": 12,
        "title": {
            "font": {
                "family": "Microsoft YaHei",
                "size": 13,
                "weight": QFont.Weight.Bold,
                "italic": False,
            },
            "color": "black",
            "selected_color": "#000000",
        },
        "path": {
            "font": {
                "family": "Consolas",
                "size": 9,
                "weight": QFont.Weight.Normal,
                "italic": False,
            },
            "color": "grey",
            "selected_color": "#333333",
        },
        "desc": {
            "font": {
                "family": "Arial",
                "size": 10,
                "weight": QFont.Weight.Normal,
                "italic": False,
            },
            "color": "grey",
            "selected_color": "#111111",
        },
        "tags": {
            "font": {
                "family": "Arial",
                "size": 9,
                "weight": QFont.Weight.Normal,
                "italic": False,
            },
            "text_color": "#FFFFFF",
            "selected_text_color": "#000000",
            "background_color": "#4A90D9",
            "selected_background_color": "#FFFFFF",
        },
    }

    qss = """
    ColumnListView {
        background-color: #fafafa;
        border: none;
        outline: none;
    }
    ColumnListView::item{
        background-color: lightgrey;
        border-radius: 12px;
    }
    ColumnListView::item:hover{
        background-color: lightblue;
        border-radius: 12px;
    }
    QPushButton#SourceCloseDetailButton {
        min-width: 24px;
        max-width: 24px;
        min-height: 24px;
        max-height: 24px;
        border: none;
        background: transparent;
        font-size: 18px;
        font-weight: bold;
        color: #666;
        border-radius: 12px;  /* 保持圆形 */
    }
    QPushButton#SourceCloseDetailButton:hover {
        color: #000000;
        background: #e0e0e0;
        border-radius: 12px;
    }
            """

    delegate_ = SourceCardDelegate(config=config)
    widget.set_model(model_, delegate_)
    widget.setStyleSheet(qss)

    layout = QVBoxLayout(window)
    layout.addWidget(widget)
    window.show()
    sys.exit(app.exec())