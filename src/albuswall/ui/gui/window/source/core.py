#
""""""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy

try:
    from ...widgets.blur_overlay_label import BlurLabel
    from ...widgets.column_list_view import ColumnListView
    from ...delegates.source_card_delegate import SourceCardDelegate
    from ...modules.source_card import SourceCard
except ImportError:
    from albuswall.ui.gui.widgets.blur_overlay_label import BlurLabel
    from albuswall.ui.gui.widgets.column_list_view import ColumnListView
    from albuswall.ui.gui.delegates.source_card_delegate import SourceCardDelegate, SourceCardStyleConfig
    from albuswall.ui.gui.modules.source_card import SourceCard


class Source(BlurLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._detail_mode = False
        self._setup_ui()
        self._setup_model()

    def _setup_ui(self):
        # 水平布局：左侧卡片视图 + 右侧详情占位
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 左侧多列卡片视图
        self.card_view = ColumnListView()
        self.card_view.set_column_count(2)  # 默认两列
        self.card_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.card_view.setStyleSheet("""
            ColumnListView {
                background-color: #fafafa;
                border: none;
                outline: none;
            }
        """)

        # 右侧详情占位 Label
        self.detail_label = QLabel("详情占位")
        self.detail_label.setFixedWidth(320)  # 固定宽度
        self.detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border-left: 1px solid #d0d0d0;
                color: #202124;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        self.detail_label.hide()  # 初始隐藏

        # 布局填充
        self.main_layout.addWidget(self.card_view, 1)  # stretch=1，占据剩余空间
        self.main_layout.addWidget(self.detail_label)

        # 点击卡片时切换详情模式
        self.card_view.clicked.connect(self._on_card_clicked)

    def _setup_model(self):
        self.model = SourceCard()

        # 示例数据（保证有足够行数展示两列效果）
        self.model.add_card("我的照片", "/home/user/Picture", "daily", ["media"])
        self.model.add_card("项目文档", "/home/user/docs", "需求、设计文档", ["文档", "重要"])
        self.model.add_card("代码仓库", "/home/user/code", "源代码管理", ["代码", "Git"])
        self.model.add_card("音乐收藏", "/home/user/music", "无损音乐", ["音乐", "娱乐"])
        self.model.add_card("下载内容", "/home/user/downloads", "临时文件", ["下载"])
        self.model.add_card("桌面背景", "/home/user/pictures/wallpaper", "壁纸图片", ["图片"])

        # 委托样式配置
        style_config = SourceCardStyleConfig(**{
            "card_margin": 10,
            "card_padding": 12,
            "corner_radius": 8,
            "border_width": 2,
            "title_font": {"family": "Segoe UI", "size": 14, "weight": QFont.Weight.Bold},
            "path_font": {"family": "Consolas", "size": 9},
            "desc_font": {"family": "Segoe UI", "size": 10},
            "tags_font": {"family": "Segoe UI", "size": 9},
            "colors": {
                "background_normal": "#ffffff",
                "border_normal": "#d0d0d0",
                "title_normal": "#202124",
                "path_normal": "#5f6368",
                "desc_normal": "#3c4043",
                "tag_bg_normal": "#e0e0e0",
                "tag_text_normal": "#202124",
                "background_selected": "#e8f0fe",
                "border_selected": "#4285f4",
                "title_selected": "#1a73e8",
                "path_selected": "#1a73e8",
                "desc_selected": "#174ea6",
                "tag_bg_selected": "#1a73e8",
                "tag_text_selected": "#ffffff",
            },
        })

        self.delegate = SourceCardDelegate(style_config=style_config)
        self.card_view.setModel(self.model)
        self.card_view.setItemDelegate(self.delegate)

    def _on_card_clicked(self, index):
        if not self._detail_mode:
            self._detail_mode = True
            self.card_view.set_column_count(1)  # 切换为单列
            self.detail_label.show()            # 显示右侧占位
            # 可选：将当前点击的卡片滚动到可见位置
            if index.isValid():
                self.card_view.scrollTo(index)


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout

    app = QApplication(sys.argv)
    window = QWidget()
    widget = Source(window)
    _layout = QVBoxLayout(window)
    _layout.addWidget(widget)
    window.show()
    exit(app.exec())
