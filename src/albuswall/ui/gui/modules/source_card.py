#
""""""

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt


try:
    from ..common.source_card_roles import TitleRole, PathRole, DescriptionRole, TagsRole
except ImportError:
    from albuswall.ui.gui.common.source_card_roles import TitleRole, PathRole, DescriptionRole, TagsRole


class SourceCard(QAbstractListModel):
    def __init__(self, cards=None, parent=None):
        super().__init__(parent)
        self._cards = cards if cards is not None else []

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._cards)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._cards)):
            return None

        card = self._cards[index.row()]

        if role == TitleRole:
            return card.get("title", "")
        elif role == PathRole:
            return card.get("path", "")
        elif role == DescriptionRole:
            return card.get("description", "")
        elif role == TagsRole:
            return card.get("tags", [])
        elif role == Qt.ItemDataRole.DisplayRole:
            return card.get("title", "")
        return None

    def add_card(self, title, path, description, tags):
        row = len(self._cards)
        self.beginInsertRows(QModelIndex(), row, row)
        self._cards.append({
            "title": title,
            "path": path,
            "description": description,
            "tags": tags
        })
        self.endInsertRows()
        return True

    def remove_card(self, row):
        if 0 <= row < len(self._cards):
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._cards[row]
            self.endRemoveRows()
            return True
        return False
