#
""""""

from typing import List

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt


try:
    from ..common.ingest_source import (
        TitleRole, PathRole, DescriptionRole, TagsRole, CardData
    )
except ImportError:
    from albuswall.ui.gui.common.ingest_source import (
        TitleRole, PathRole, DescriptionRole, TagsRole, CardData,
    )


class SourceCard(QAbstractListModel):
    def __init__(
            self,
            cards=None,
            parent=None
    ):
        super().__init__(parent)
        self._cards: List[CardData] = \
            cards if cards is not None else []
        self._role_handlers = {
            TitleRole: lambda c: c.get("title", ""),
            PathRole: lambda c: c.get("path", ""),
            DescriptionRole: lambda c: c.get("description", ""),
            TagsRole: lambda c: c.get("tags", []),
            Qt.ItemDataRole.DisplayRole: lambda c: c.get("title", ""),
        }

    def rowCount(
            self,
            parent=QModelIndex()
    ):
        if parent.isValid():
            return 0
        return len(self._cards)

    def data(
            self,
            index,
            role=Qt.ItemDataRole.DisplayRole
    ):
        if not index.isValid() or not (0 <= index.row() < len(self._cards)):
            return None

        card = self._cards[index.row()]
        handler = self._role_handlers.get(role)
        if handler:
            return handler(card)
        return None

    def add_card(
            self,
            title: str,
            path: str,
            description: str,
            tags: List[str]
    ) -> int:
        """
        向模型中添加一张卡片。

        Args:
            title: 卡片标题，不能为空字符串。
            path: 卡片路径。
            description: 卡片描述。
            tags: 标签列表。

        Returns:
            新插入行的索引。

        Raises:
            ValueError: 如果 title 为空字符串。
            TypeError: 如果 tags 不是列表。
        """
        # 简单的参数验证
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
        }
        self._cards.append(new_card)

        self.endInsertRows()
        return row

    def remove_card(self, row):
        if 0 <= row < len(self._cards):
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._cards[row]
            self.endRemoveRows()
            return True
        return False
