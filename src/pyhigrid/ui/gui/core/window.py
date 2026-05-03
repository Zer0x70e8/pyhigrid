#
""""""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt

from .content import Content
from .titlebar import TitleBar

from ..utils.window_resizer import WindowResizer
from ..utils.disable_win11_round_corners import disable_round_corners

from pyhigrid.configue import UIConfig

__all__ = ['Window']


class Window(QWidget):
    def __init__(self):
        super().__init__()

        self.logger = None
        self.confs = None
        self.conf = None
        self.bg = None

        self._first_refresh = False

        self.window_resizer = None

        self.content = None
        self.titlebar = None

        self.setup_ui()

    def setup(self, logger, conf, confs, bg):
        self.logger = logger
        self.confs: UIConfig = confs
        self.conf = conf
        self.bg = bg

        #
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowMaximizeButtonHint)

        self.setMinimumSize(8, 8)
        w, h = self.conf.dynamic.ui.window_size
        self.resize(w, h)

        #
        self.window_resizer = WindowResizer(
            self, self, False)

        self.content.logger = logger

        #
        self.logger.debug("The UI setup completed.")

    def setup_ui(self):

        self.content = Content(self)
        self.titlebar = TitleBar(self)

        #
        self.content.lower()

        if __debug__:
            # noinspection SpellCheckingInspection
            self.setStyleSheet("""
                TitleBar {
                    background-color: #2c3e50;
                    border: none;
                }
                #TitleToolBar {
                    background-color: transparent;
                    border: none;
                }

                #SearchCloseBtn, #AlbumButton, #MoreButton, #SearchPlaceholder {
                    min-width: 48px;
                    min-height: 48px;
                    max-width: 48px;
                    max-height: 48px;
                    border-radius: 24px;
                    border: none;
                    background-color: transparent;
                }
                #AlbumButton:hover, #MoreButton:hover, #SearchPlaceholder:hover {
                    background-color: rgba(255,255,255,0.1);
                }
                /* 搜索栏本身 */
                #SearchBar {
                    margin-top: 10px;
                    background-color: rgba(255,255,255,0.1);
                    min-height: 48px;
                    max-height: 48px;
                    border-radius: 24px;
                }
                #SearchLineEdit {
                    border: 0px;
                    border-bottom: 1px solid #ccc;
                    padding: 4px 8px;
                    font-size: 14px;
                    background: transparent;
                }
                #SearchCloseBtn {
                    min-width: 48px;
                    min-height: 48px;
                    max-width: 48px;
                    max-height: 48px;
                    border-radius: 24px;
                    border: none; 
                    
                    background: transparent;
                    
                    font-size: 14px; 
                    color: #888;
                }
                #SearchCloseBtn:hover {
                    color: #333; 
                    background-color: rgba(255,255,255,0.1);
                }
                
                /* act buttons */
                #CloseButton, #MinimizeButton, #MaximizeButton {
                    min-width: 16px;
                    min-height: 16px;
                    max-width: 16px;
                    max-height: 16px;
                    border-radius: 8px;          /* 圆形外观 */
                    border: none;
                    font-family: "Segoe UI", "Microsoft YaHei", system-ui;
                    font-size: 12px;
                    font-weight: normal;
                    text-align: center;
                    outline: none;                /* 去除焦点虚线框 */
                    transition: all 0.1s ease;    /* 平滑过渡（Qt部分支持，无副作用） */
                }
                
                #CloseButton {
                    background-color: #FF5F56;  
                    color: #4D0000;
                }
                #CloseButton:hover {
                    background-color: #FF7A72;  
                }
                #CloseButton:pressed {
                    background-color: #E24B42;  
                }
                
                #MinimizeButton {
                    background-color: #FFBD2E; 
                    color: #8B6D00;
                }
                #MinimizeButton:hover {
                    background-color: #FFCD5C;
                }
                #MinimizeButton:pressed {
                    background-color: #E5A81F; 
                }
                
                #MaximizeButton {
                    background-color: #28C840;  
                    color: #004D0F;
                }
                #MaximizeButton:hover {
                    background-color: #4ED563;  
                }
                #MaximizeButton:pressed {
                    background-color: #1DAF34;  
                }
                
                /* 为所有按钮增加轻微的内阴影，模拟拟态质感（仅影响可见风格） */
                #CloseButton, #MinimizeButton, #MaximizeButton {
                    border: 1px solid rgba(0, 0, 0, 0.04);
                    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.25), 0 1px 1px rgba(0, 0, 0, 0.08);
                }
                /* 悬停时阴影变化，提升交互感 */
                #CloseButton:hover, #MinimizeButton:hover, #MaximizeButton:hover {
                    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.3), 0 1px 2px rgba(0, 0, 0, 0.1);
                }
                
            """)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._first_refresh:
            if not self.conf.dynamic.ui.use_system_round_corners:
                hwnd = int(self.winId())
                disable_round_corners(hwnd)

            self.content.layout_()
            self.content.overscroll_top = self.titlebar.height()
            # self.content.unit_clicked.connect(lambda index: print(f"点击了单元：{index}"))

            self._first_refresh = True

    def resizeEvent(self, event):
        self.content.setGeometry(0, 0, self.width(), self.height())
        self.titlebar.setGeometry(0, 0, self.width(), self.titlebar.height())
