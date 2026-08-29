#
""""""

from PySide6.QtCore import Qt, QRect, QSize, QModelIndex, QEvent
from PySide6.QtGui import QPainter, QColor, QFontMetrics
from PySide6.QtWidgets import QStyledItemDelegate, QStyle, QApplication, QStyleOptionViewItem


class TagDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 使用 QApplication.style() 获取全局样式（QStyledItemDelegate 没有 style() 方法）
        self.close_icon = QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_TitleBarCloseButton
        )
        self.close_button_size = 16
        self.padding = 8
        self.radius = 10

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        text = index.data(Qt.ItemDataRole.DisplayRole) or ""

        rect = option.rect.adjusted(2, 2, -2, -2)

        # 背景色
        bg_color = QColor("#e0e0e0")
        if option.state & QStyle.StateFlag.State_MouseOver:
            bg_color = QColor("#d0d0d0")
        if option.state & QStyle.StateFlag.State_Selected:
            bg_color = QColor("#b0d0ff")

        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, self.radius, self.radius)

        # 文字
        painter.setPen(QColor("#333333"))
        font_metrics = QFontMetrics(option.font)
        text_rect = rect.adjusted(
            self.padding, 0, -(self.close_button_size + self.padding), 0
        )
        elided_text = font_metrics.elidedText(
            text, Qt.TextElideMode.ElideRight, text_rect.width()
        )
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            elided_text,
        )

        # 关闭按钮图标
        close_rect = QRect(
            rect.right() - self.close_button_size - self.padding // 2,
            rect.center().y() - self.close_button_size // 2,
            self.close_button_size,
            self.close_button_size,
        )
        self.close_icon.paint(painter, close_rect)

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        font_metrics = QFontMetrics(option.font)
        text_width = font_metrics.horizontalAdvance(text)
        width = text_width + self.padding * 2 + self.close_button_size + self.padding
        height = font_metrics.height() + self.padding * 2
        return QSize(width, height)

    def editorEvent(self, event, model, option, index):
        # 先判断事件类型，再安全转换为 QMouseEvent
        if event.type() == QEvent.Type.MouseButtonRelease:
            from PySide6.QtGui import QMouseEvent
            mouse_event = event  # 此时 event 实际是 QMouseEvent，但为了 IDE 可声明类型
            if isinstance(mouse_event, QMouseEvent) and mouse_event.button() == Qt.MouseButton.LeftButton:
                rect = option.rect.adjusted(2, 2, -2, -2)
                close_rect = QRect(
                    rect.right() - self.close_button_size - self.padding // 2,
                    rect.center().y() - self.close_button_size // 2,
                    self.close_button_size,
                    self.close_button_size,
                )
                if close_rect.contains(mouse_event.position().toPoint()):
                    # 模型必须实现 removeTag 方法
                    if hasattr(model, "remove_tag"):
                        model.remove_tag(index.row())
                        return True
                    else:
                        raise ValueError("模型必须实现 removeTag 方法")
        return super().editorEvent(event, model, option, index)
