#
""""""

from typing import Literal

from PySide6.QtCore import Qt

USER_ROLE_TYPE = Literal[Qt.ItemDataRole.UserRole] | int

TitleRole: USER_ROLE_TYPE = Qt.ItemDataRole.UserRole + 1
PathRole: USER_ROLE_TYPE = Qt.ItemDataRole.UserRole + 2
DescriptionRole: USER_ROLE_TYPE = Qt.ItemDataRole.UserRole + 3
TagsRole: USER_ROLE_TYPE = Qt.ItemDataRole.UserRole + 4
CardBackgroundColorRole: USER_ROLE_TYPE = Qt.ItemDataRole.UserRole + 5
CardBorderColorRole: USER_ROLE_TYPE = Qt.ItemDataRole.UserRole + 6