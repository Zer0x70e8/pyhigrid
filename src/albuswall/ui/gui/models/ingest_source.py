#
""""""

from typing import List, Optional

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

try:
    from ..common.ingest_source import (
        TitleRole, PathRole, DescriptionRole, TagsRole, CardData, DetailRole
)
except ImportError:
    from albuswall.ui.gui.common.ingest_source import (
        TitleRole, PathRole, DescriptionRole, TagsRole, CardData, DetailRole
    )


class IngestSourceModel(QAbstractListModel):
    def __init__(self, items: Optional[list]=None, parent=None):
        super().__init__(parent)
        self._items: List[CardData] = items if items is not None else []
        self._role_handlers = {
            TitleRole: lambda i: i.get("title", ""),
            PathRole: lambda i: i.get("path", ""),
            DescriptionRole: lambda i: i.get("description", ""),
            TagsRole: lambda i: i.get("tags", []),
            DetailRole: lambda i: i,  # return a dict
            Qt.ItemDataRole.DisplayRole: lambda i: i.get("title", ""),
        }

    def rowCount(
            self,
            parent=QModelIndex()
    ):
        if parent.isValid():
            return 0
        return len(self._items)

    def data(
            self,
            index,
            role=Qt.ItemDataRole.DisplayRole
    ):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None

        card = self._items[index.row()]
        handler = self._role_handlers.get(role)
        if handler:
            return handler(card)
        return None

    def add_item(
            self,
            title: str,
            path: str,
            description: str,
            tags: List[str],
            detail_data: dict
    ) -> int:
        """
        向模型中添加一张卡片。

        Args:
            title: 卡片标题，不能为空字符串。
            path: 卡片路径。
            description: 卡片描述。
            tags: 标签列表。
            detail_data: 详情页数据

        Returns:
            新插入行的索引。

        Raises:
            ValueError: 如果 title 为空字符串。
            TypeError: 如果 tags 不是列表。
        """
        if not isinstance(title, str) or not title.strip():
            raise ValueError("title must be a non-empty string")
        if not isinstance(tags, list):
            raise TypeError("tags must be a list")

        row = self.rowCount()
        self.beginInsertRows(QModelIndex(), row, row)

        new_card: CardData = {
            "title": title,
            "path": path,
            "description": description,
            "tags": tags,
            "detail_data": detail_data
        }
        self._items.append(new_card)

        self.endInsertRows()
        return row

    def remove_item(self, row: int) -> bool:
        """删除指定行的卡片，成功返回 True，否则返回 False。"""
        if 0 <= row < len(self._items):
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._items[row]
            self.endRemoveRows()
            return True
        return False

    def update_item(self, row: int, new_data: CardData) -> bool:
        """
        更新指定行的卡片数据，并发出 dataChanged 信号。

        Args:
            row: 要更新的行索引。
            new_data: 包含完整字段的字典，必须与 CardData 结构一致。

        Returns:
            如果更新成功返回 True，否则返回 False。
        """
        if 0 <= row < len(self._items):
            self._items[row] = new_data
            index = self.index(row, 0)
            # 通知视图该行数据已更改，刷新所有相关角色
            self.dataChanged.emit(index, index, [
                TitleRole,
                PathRole,
                DescriptionRole,
                TagsRole,
                DetailRole,
                Qt.ItemDataRole.DisplayRole
            ])
            return True
        return False

