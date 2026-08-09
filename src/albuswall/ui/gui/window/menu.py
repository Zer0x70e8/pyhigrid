#
""""""

from PySide6.QtWidgets import QMenu
from PySide6.QtCore import Signal


class Menu(QMenu):
    # 定义信号，无参数
    choose_triggered = Signal()
    setting_triggered = Signal()
    media_source_triggered = Signal()
    auto_sorting_triggered = Signal()
    # quit_menu_triggered = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MoreFunctionsMenu")

        # 连接动作：先打印，再发射信号
        self.addAction(self.tr("choose"),
                       self.choose_triggered.emit)
        self.addAction(self.tr("setting"),
                       self.setting_triggered.emit)
        self.addAction(self.tr("media source"),
                       self.media_source_triggered.emit)
        self.addAction(self.tr("auto sorting"),
                       self.auto_sorting_triggered.emit)
        self.addSeparator()

        # “退出菜单”动作：发射信号并关闭菜单
        self.addAction(self.tr("quit menu"),
                       lambda: (
                           # self.quit_menu_triggered.emit(),
                           self.close())
                       )

