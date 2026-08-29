#
""""""

from typing import Any, Dict, Mapping, Optional, cast
from collections.abc import Mapping as MappingABC
import copy

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QBrush,
    QPalette,
    QIcon,
)
from PySide6.QtWidgets import QStyledItemDelegate, QStyle, QStyleOptionViewItem

try:
    from ..common.source_card_roles import (
        TitleRole,
        PathRole,
        DescriptionRole,
        TagsRole,
    )
    from ..common.source_card_types import SourceCardStyleConfig
except ImportError:
    from albuswall.ui.gui.common.ingest_source import (
        TitleRole,
        PathRole,
        DescriptionRole,
        TagsRole,
    )
    from albuswall.ui.gui.common.ingest_source import SourceCardStyleConfig


# ---------------------------------------------------------------------------
# 工具函数：深度合并字典
# ---------------------------------------------------------------------------

def _deep_merge(base: dict, updates: Mapping) -> None:
    """
    递归合并 updates 到 base 中。
    如果 base 和 updates 的同一个键都是字典，则递归合并；
    否则直接用 updates 的值覆盖 base 的值。
    """
    for key, value in updates.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, MappingABC)
        ):
            _deep_merge(base[key], value)
        else:
            base[key] = value


# ---------------------------------------------------------------------------
# Delegate 实现
# ---------------------------------------------------------------------------

class SourceCardDelegate(QStyledItemDelegate):
    """
    自定义卡片代理，使用新的 TypedDict 样式配置。
    绘制顺序：
        1. 调用父类 paint 绘制样式表背景；
        2. 在背景之上绘制标题、路径、描述和标签。
    只使用 4 个数据角色：TitleRole、PathRole、DescriptionRole、TagsRole。
    """

    DEFAULT_FONTS = {
        "title": QFont("Arial", 12, QFont.Weight.Bold),
        "path": QFont("Arial", 9),
        "desc": QFont("Arial", 10),
        "tags": QFont("Arial", 9),
    }

    def __init__(
        self,
        parent=None,
        config: Optional[Mapping[str, Any]] = None,
    ):
        super().__init__(parent)
        self._config: Dict[str, Any] = {}

        # 默认几何参数
        self.card_margin = 8
        self.card_padding = 10

        if config is not None:
            self.set_config(config)

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------
    def set_config(self, config: Optional[Mapping[str, Any]] = None) -> None:
        """
        深度合并样式配置。
        未提供的字段（包括嵌套 section 中的字段）保留当前值。
        config 为 None 时不进行任何操作。
        """
        if config is None:
            return

        _deep_merge(self._config, config)

        # 同步顶层几何参数
        self.card_margin = self._config.get("card_margin", self.card_margin)
        self.card_padding = self._config.get("card_padding", self.card_padding)

    def config(self) -> SourceCardStyleConfig:
        """
        返回当前生效的样式配置的深拷贝。
        外部对返回值的修改不会影响 delegate 内部状态。
        """
        return cast(SourceCardStyleConfig, cast(object, copy.deepcopy(self._config)))

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_font(font_spec, default_key: str) -> QFont:
        """将字体配置（FontConfig 或 QFont）转换为 QFont"""
        if font_spec is None:
            return SourceCardDelegate.DEFAULT_FONTS[default_key]
        if isinstance(font_spec, QFont):
            return QFont(font_spec)
        if isinstance(font_spec, dict):
            font = QFont(SourceCardDelegate.DEFAULT_FONTS[default_key])
            if "family" in font_spec:
                font.setFamily(font_spec["family"])
            if "size" in font_spec:
                font.setPointSize(font_spec["size"])
            if "weight" in font_spec:
                font.setWeight(font_spec["weight"])
            if "italic" in font_spec:
                font.setItalic(font_spec["italic"])
            return font
        return SourceCardDelegate.DEFAULT_FONTS[default_key]

    @staticmethod
    def _color_from_config(config_value, fallback: QColor) -> QColor:
        """从配置值（字符串或 QColor）获取颜色，若无效则返回 fallback"""
        if config_value is None:
            return fallback
        color = config_value if isinstance(config_value, QColor) else QColor(config_value)
        return color if color.isValid() else fallback

    def _section_style(self, section: str) -> dict:
        """获取某个 section（title/path/desc/tags）的样式字典"""
        style = self._config.get(str(section))
        return style if isinstance(style, dict) else {}

    def _font_for(self, section: str, default_key: str) -> QFont:
        """获取 section 对应的字体"""
        section_style = self._section_style(section)
        return self._resolve_font(section_style.get("font"), default_key)

    def _color_for(
        self,
        section: str,
        normal_key: str,
        selected_key: str,
        selected: bool,
        fallback: QColor,
    ) -> QColor:
        """根据选中状态从 section 配置中获取颜色"""
        section_style = self._section_style(section)
        key = selected_key if selected else normal_key
        return self._color_from_config(section_style.get(key), fallback)

    @staticmethod
    def _default_text_colors(option: QStyleOptionViewItem, selected: bool) -> dict:
        """从 option.palette 获取默认文本/标签颜色"""
        palette = option.palette

        if selected:
            title = palette.color(QPalette.ColorRole.HighlightedText)
            path = QColor(title).lighter(150)
            desc = title
            tag_bg = palette.color(QPalette.ColorRole.HighlightedText)
            tag_text = palette.color(QPalette.ColorRole.Highlight)
        else:
            title = palette.color(QPalette.ColorRole.Text)
            path = QColor(title).lighter(160)
            desc = title
            tag_bg = palette.color(QPalette.ColorRole.Highlight)
            tag_text = palette.color(QPalette.ColorRole.HighlightedText)

        return {
            "title": title,
            "path": path,
            "desc": desc,
            "tag_bg": tag_bg,
            "tag_text": tag_text,
        }

    # ------------------------------------------------------------------
    # 重写 initStyleOption、paint 和 sizeHint
    # ------------------------------------------------------------------
    def initStyleOption(self, option, index):
        # 调用父类，获得默认填充（背景等）
        super().initStyleOption(option, index)

        # 清除文本和图标：让基类绘制背景但不绘制默认文字/图标
        option.text = ""
        option.icon = QIcon()

        # 移除显示特性标志，避免基类绘制默认内容
        option.features &= ~QStyleOptionViewItem.ViewItemFeature.HasDisplay
        option.features &= ~QStyleOptionViewItem.ViewItemFeature.HasDecoration

    def paint(self, painter, option, index):
        # 1. 保留样式表绘制的背景（包括选中、悬停等背景）
        super().paint(painter, option, index)

        # 2. 获取数据
        title = index.data(TitleRole) or ""
        path = index.data(PathRole) or ""
        description = index.data(DescriptionRole) or ""
        tags: list = index.data(TagsRole) or []

        selected = bool(option.state & QStyle.StateFlag.State_Selected)

        # 3. 解析字体
        title_font = self._font_for("title", "title")
        path_font = self._font_for("path", "path")
        desc_font = self._font_for("desc", "desc")
        tags_font = self._font_for("tags", "tags")

        # 4. 解析默认颜色，再叠加配置
        defaults = self._default_text_colors(option, selected)

        title_color = self._color_for(
            "title", "color", "selected_color", selected, defaults["title"]
        )
        path_color = self._color_for(
            "path", "color", "selected_color", selected, defaults["path"]
        )
        desc_color = self._color_for(
            "desc", "color", "selected_color", selected, defaults["desc"]
        )
        tag_text_color = self._color_for(
            "tags", "text_color", "selected_text_color", selected, defaults["tag_text"]
        )
        tag_bg_color = self._color_for(
            "tags", "background_color", "selected_background_color", selected, defaults["tag_bg"]
        )

        # 5. 计算内容区域
        card_rect = option.rect.adjusted(
            self.card_margin,
            self.card_margin,
            -self.card_margin,
            -self.card_margin,
        )

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制标题
        painter.setFont(title_font)
        painter.setPen(title_color)
        title_rect = QRect(
            card_rect.left() + self.card_padding,
            card_rect.top() + self.card_padding,
            card_rect.width() - 2 * self.card_padding,
            QFontMetrics(title_font).height(),
        )
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title,
        )

        # 绘制路径
        painter.setFont(path_font)
        painter.setPen(path_color)
        path_rect = QRect(
            card_rect.left() + self.card_padding,
            title_rect.bottom() + 4,
            card_rect.width() - 2 * self.card_padding,
            QFontMetrics(path_font).height(),
        )
        painter.drawText(
            path_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            path,
        )

        # 绘制描述（固定高度区域，支持换行）
        painter.setFont(desc_font)
        painter.setPen(desc_color)
        desc_rect = QRect(
            card_rect.left() + self.card_padding,
            path_rect.bottom() + 6,
            card_rect.width() - 2 * self.card_padding,
            40,
        )
        painter.drawText(
            desc_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
            description,
        )

        # 绘制标签
        painter.setFont(tags_font)
        tag_y = desc_rect.bottom() + 6
        tag_x = card_rect.left() + self.card_padding
        tag_fm = QFontMetrics(tags_font)
        tag_height = tag_fm.height() + 4

        for tag in tags:
            tag_text = f" {tag} "
            tag_width = tag_fm.horizontalAdvance(tag_text) + 6
            tag_rect = QRect(tag_x, tag_y, tag_width, tag_height)

            # 标签背景
            painter.setBrush(QBrush(tag_bg_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(tag_rect, 3, 3)

            # 标签文字
            painter.setPen(tag_text_color)
            painter.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, tag_text)

            tag_x += tag_width + 4
            if tag_x > card_rect.right() - self.card_padding:
                tag_x = card_rect.left() + self.card_padding
                tag_y += tag_height + 4

        painter.restore()

    def sizeHint(self, option, index):
        # 根据字体动态计算高度，宽度保持固定或由视图决定
        base_width = 300

        title_font = self._font_for("title", "title")
        path_font = self._font_for("path", "path")
        tags_font = self._font_for("tags", "tags")

        title_height = QFontMetrics(title_font).height()
        path_height = QFontMetrics(path_font).height()
        desc_height = 40
        tags_height = QFontMetrics(tags_font).height() + 4

        total_height = (
            self.card_margin * 2
            + self.card_padding * 2
            + title_height
            + 4
            + path_height
            + 6
            + desc_height
            + 6
            + tags_height
        )
        return QSize(base_width, int(total_height))
