#
""""""

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Signal

class TagListModel(QAbstractListModel):
    """管理字符串标签的列表模型，支持添加和删除，与 TagDelegate 配合使用。"""

    # 可选信号，用于通知外部数据变化（非必需，因为 QAbstractListModel 已有 signals）
    tag_added = Signal(str)
    tag_removed = Signal(str)

    def __init__(self, tags: list[str] | None = None, parent=None):
        super().__init__(parent)
        self._tags = tags or []

    # ---------- 必须实现的 QAbstractListModel 接口 ----------
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._tags)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._tags)):
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return self._tags[index.row()]
        # 可添加 ToolTipRole 等
        return None

    # ---------- 自定义方法（供视图和外部调用） ----------
    def tags(self) -> list[str]:
        """返回当前所有标签的副本。"""
        return self._tags.copy()

    def set_tags(self, tags: list[str]):
        """重置整个列表。"""
        self.beginResetModel()
        self._tags = tags.copy()
        self.endResetModel()

    def add_tag(self, tag: str) -> bool:
        """添加标签，若已存在则返回 False。"""
        tag = tag.strip()
        if not tag or tag in self._tags:
            return False
        row = len(self._tags)
        self.beginInsertRows(QModelIndex(), row, row)
        self._tags.append(tag)
        self.endInsertRows()
        self.tag_added.emit(tag)
        return True

    def remove_tag(self, row: int) -> bool:
        """按行号删除标签，返回是否成功。"""
        if not (0 <= row < len(self._tags)):
            return False
        self.beginRemoveRows(QModelIndex(), row, row)
        removed = self._tags.pop(row)
        self.endRemoveRows()
        self.tag_removed.emit(removed)
        return True
