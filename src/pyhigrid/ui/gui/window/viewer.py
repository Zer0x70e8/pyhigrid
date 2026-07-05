#
""""""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QScrollArea
)

from ..widget.image_viwer import ImageViewer


class View(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.top_bar_layout = None
        self.bottom_bar_layout = None

        self.quit_button = None
        self.more_button = None
        self.info_button = None
        self.favourite_button = None
        self.adjust_button = None
        self.share_button = None
        self.trash_button = None

        self.browser_line = None

        self.viewer = None
        self.viewer_scroll_area = None

        self.setup_ui()

    def setup_ui(self):
        # init all
        layout = QVBoxLayout(self)

        self.top_bar_layout = QHBoxLayout()
        self.bottom_bar_layout = QHBoxLayout()

        self.quit_button = QPushButton(self)
        self.more_button = QPushButton(self)

        self.info_button = QPushButton(self)
        self.favourite_button = QPushButton(self)
        self.adjust_button = QPushButton(self)
        self.share_button = QPushButton(self)
        self.trash_button = QPushButton(self)

        # TODO content, browser_line
        self.viewer_scroll_area = QScrollArea(self)
        self.viewer = ImageViewer(self.viewer_scroll_area)
        content_layout = QVBoxLayout(self.viewer)
        content_layout.addStretch(1)
        self.viewer.setLayout(content_layout)
        self.viewer_scroll_area.setWidget(self.viewer)
        self.viewer_scroll_area.setWidgetResizable(True)

        self.browser_line = QWidget(self)

        # layout
        self.top_bar_layout.addWidget(self.quit_button)
        self.top_bar_layout.addStretch()
        self.top_bar_layout.addWidget(self.more_button)

        self.bottom_bar_layout.addWidget(self.share_button)
        self.bottom_bar_layout.addStretch()
        self.bottom_bar_layout.addWidget(self.adjust_button)
        self.bottom_bar_layout.addWidget(self.info_button)
        self.bottom_bar_layout.addWidget(self.favourite_button)
        self.bottom_bar_layout.addStretch()
        self.bottom_bar_layout.addWidget(self.trash_button)

        layout.addLayout(self.top_bar_layout)
        layout.addWidget(self.viewer_scroll_area)
        layout.addWidget(self.browser_line)
        layout.addLayout(self.bottom_bar_layout)

        # name
        self.setObjectName("ViewImage")

        self.top_bar_layout.setObjectName("ViewImageTopBarLayout")
        self.bottom_bar_layout.setObjectName("ViewImageBottomBarLayout")

        self.quit_button.setObjectName("ViewImageQuitButton")
        self.more_button.setObjectName("ViewImageMoreButton")
        self.info_button.setObjectName("ViewImageInfoButon")
        self.favourite_button.setObjectName("ViewImageFavouriteButton")
        self.adjust_button.setObjectName("ViewImageAdjustButton")
        self.share_button.setObjectName("ViewImageShareButton")
        self.trash_button.setObjectName("ViewImageTrashButton")

        self.browser_line.setObjectName("ViewImageBrowserLine")

        self.viewer.setObjectName("ViewImageContent")
        self.viewer_scroll_area.setObjectName("ViewImageContentScrollArea")
