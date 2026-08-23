#
""""""

from typing import TypedDict, Union, Optional

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QBrush, QPalette, QIcon
from PySide6.QtWidgets import QStyledItemDelegate, QStyle, QStyleOptionViewItem

try:
    from ..common.source_card_roles import (
        TitleRole,
        PathRole,
        DescriptionRole,
        TagsRole,
        CardBackgroundColorRole,
        CardBorderColorRole,
    )
except ImportError:
    from albuswall.ui.gui.common.source_card_roles import (
        TitleRole,
        PathRole,
        DescriptionRole,
        TagsRole,
        CardBackgroundColorRole,
        CardBorderColorRole,
    )

# ---------------------------------------------------------------------------
# TypedDict 样式配置定义
# ---------------------------------------------------------------------------

class FontConfig(TypedDict, total=False):
    """字体配置，所有字段可选"""
    family: str
    size: int
    weight: int          # 对应 QFont.Weight 枚举值
    italic: bool

class SourceCardColorsConfig(TypedDict, total=False):
    """颜色配置，所有字段可选，值可以是字符串（如 "#RRGGBB"）或 QColor"""
    background_selected: Union[str, QColor]
    background_normal: Union[str, QColor]
    border_selected: Union[str, QColor]
    border_normal: Union[str, QColor]
    title_selected: Union[str, QColor]
    title_normal: Union[str, QColor]
    path_selected: Union[str, QColor]
    path_normal: Union[str, QColor]
    desc_selected: Union[str, QColor]
    desc_normal: Union[str, QColor]
    tag_bg_selected: Union[str, QColor]
    tag_bg_normal: Union[str, QColor]
    tag_text_selected: Union[str, QColor]
    tag_text_normal: Union[str, QColor]

class SourceCardStyleConfig(TypedDict, total=False):
    """卡片整体样式配置，所有字段可选"""
    card_margin: int
    card_padding: int
    corner_radius: int
    border_width: int

    title_font: Union[FontConfig, QFont]
    path_font: Union[FontConfig, QFont]
    desc_font: Union[FontConfig, QFont]
    tags_font: Union[FontConfig, QFont]

    colors: SourceCardColorsConfig


# ---------------------------------------------------------------------------
# Delegate 实现
# ---------------------------------------------------------------------------

class SourceCardDelegate(QStyledItemDelegate):
    """
    自定义卡片代理，支持通过字典配置样式。
    样式优先级：单项数据角色覆盖 > style_config 配置 > 默认调色板。
    """

    # 默认字体定义（可被配置覆盖）
    DEFAULT_FONTS = {
        "title": QFont("Arial", 12, QFont.Weight.Bold),
        "path": QFont("Arial", 9),
        "desc": QFont("Arial", 10),
        "tags": QFont("Arial", 9),
    }

    def __init__(
        self,
        parent=None,
        style_config: Optional[SourceCardStyleConfig] = None,
    ):
        super().__init__(parent)
        self._style_config: SourceCardStyleConfig = {}
        # 初始化默认值
        self.card_margin = 8
        self.card_padding = 10
        self.corner_radius = 5
        self.border_width = 1

        self.title_font = self.DEFAULT_FONTS["title"]
        self.path_font = self.DEFAULT_FONTS["path"]
        self.desc_font = self.DEFAULT_FONTS["desc"]
        self.tags_font = self.DEFAULT_FONTS["tags"]

        if style_config is not None:
            self.set_style_config(style_config)

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------
    def set_style_config(self, config: SourceCardStyleConfig) -> None:
        """更新样式配置，未提供的字段保留当前值"""
        self._style_config.update(config)  # 合并配置
        self._apply_style_config()

    def style_config(self) -> SourceCardStyleConfig:
        """返回当前生效的样式配置（副本）"""
        return SourceCardStyleConfig(**dict(self._style_config))

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------
    def _apply_style_config(self) -> None:
        """根据 _style_config 更新实例属性"""
        cfg = self._style_config

        # 更新几何参数
        self.card_margin = cfg.get("card_margin", self.card_margin)
        self.card_padding = cfg.get("card_padding", self.card_padding)
        self.corner_radius = cfg.get("corner_radius", self.corner_radius)
        self.border_width = cfg.get("border_width", self.border_width)

        # 更新字体
        self.title_font = self._resolve_font(cfg.get("title_font"), "title")
        self.path_font = self._resolve_font(cfg.get("path_font"), "path")
        self.desc_font = self._resolve_font(cfg.get("desc_font"), "desc")
        self.tags_font = self._resolve_font(cfg.get("tags_font"), "tags")

    @staticmethod
    def _resolve_font(font_spec, default_key: str) -> QFont:
        """将字体配置（FontConfig 或 QFont）转换为 QFont"""
        if font_spec is None:
            return SourceCardDelegate.DEFAULT_FONTS[default_key]
        if isinstance(font_spec, QFont):
            return QFont(font_spec)  # 复制一份，避免外部修改
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
        # 非法类型，回退默认
        return SourceCardDelegate.DEFAULT_FONTS[default_key]

    @staticmethod
    def _color_from_data(index, role, fallback: QColor) -> QColor:
        """从数据角色读取颜色，若无效则返回 fallback"""
        value = index.data(role)
        if value is None:
            return fallback
        color = value if isinstance(value, QColor) else QColor(value)
        return color if color.isValid() else fallback

    @staticmethod
    def _color_from_config(config_value, fallback: QColor) -> QColor:
        """从配置值（字符串或 QColor）获取颜色，若无效则返回 fallback"""
        if config_value is None:
            return fallback
        color = config_value if isinstance(config_value, QColor) else QColor(config_value)
        return color if color.isValid() else fallback

    @staticmethod
    def _default_colors(option) -> dict:
        """
        从 option.palette 获取默认颜色，返回包含各状态颜色的字典。
        键与 SourceCardColorsConfig 中的键对应。
        """
        palette = option.palette
        selected = bool(option.state & QStyle.StateFlag.State_Selected)  # type: ignore[operator]

        if selected:
            bg = palette.color(QPalette.ColorRole.Highlight)
            border = bg.darker(120)
            title = palette.color(QPalette.ColorRole.HighlightedText)
            path = QColor(title).lighter(150)
            desc = title
            tag_bg = palette.color(QPalette.ColorRole.HighlightedText)
            tag_text = palette.color(QPalette.ColorRole.Highlight)
        else:
            bg = palette.color(QPalette.ColorRole.Base)
            border = bg.darker(130)
            title = palette.color(QPalette.ColorRole.Text)
            path = QColor(title).lighter(160)
            desc = title
            tag_bg = palette.color(QPalette.ColorRole.Highlight)
            tag_text = palette.color(QPalette.ColorRole.HighlightedText)

        return {
            "background": bg,
            "border": border,
            "title": title,
            "path": path,
            "desc": desc,
            "tag_bg": tag_bg,
            "tag_text": tag_text,
        }

    def _resolve_colors(self, option, index) -> dict:
        """
        解析最终使用的颜色，优先级：
        1. 数据角色覆盖（background/border）
        2. style_config 中的 colors 配置
        3. 默认调色板（_default_colors）
        """
        selected = bool(option.state & QStyle.StateFlag.State_Selected)  # type: ignore[operator]
        state_suffix = "_selected" if selected else "_normal"

        # 获取默认调色板颜色
        palette_colors = self._default_colors(option)

        # 从配置中读取颜色（如果存在）
        colors_cfg = self._style_config.get("colors", {})
        resolved = {}
        for key in ("background", "border", "title", "path", "desc", "tag_bg", "tag_text"):
            config_key = f"{key}{state_suffix}"
            if config_key in colors_cfg:
                resolved[key] = self._color_from_config(colors_cfg[config_key], palette_colors[key])
            else:
                resolved[key] = palette_colors[key]

        # 数据角色覆盖背景和边框
        resolved["background"] = self._color_from_data(
            index, CardBackgroundColorRole, resolved["background"]
        )
        resolved["border"] = self._color_from_data(
            index, CardBorderColorRole, resolved["border"]
        )

        return resolved

    # ------------------------------------------------------------------
    # 重写 paint 和 sizeHint
    # ------------------------------------------------------------------
    def paint(
            self,
            painter,
            option,
            index
    ):
        super().paint(painter, option, index)

        # 获取数据
        title = index.data(TitleRole) or ""
        path = index.data(PathRole) or ""
        description = index.data(DescriptionRole) or ""
        tags = index.data(TagsRole) or []

        # 计算内容区域（仅用于文本布局，不绘制背景）
        card_rect = option.rect.adjusted(
            self.card_margin,
            self.card_margin,
            -self.card_margin,
            -self.card_margin,
        )

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 解析颜色（用于文本与标签）
        colors = self._resolve_colors(option, index)

        # 绘制标题
        painter.setFont(self.title_font)
        painter.setPen(colors["title"])
        title_rect = QRect(
            card_rect.left() + self.card_padding,
            card_rect.top() + self.card_padding,
            card_rect.width() - 2 * self.card_padding,
            painter.fontMetrics().height(),
        )
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title,
        )

        # 绘制路径
        painter.setFont(self.path_font)
        painter.setPen(colors["path"])
        path_rect = QRect(
            card_rect.left() + self.card_padding,
            title_rect.bottom() + 4,
            card_rect.width() - 2 * self.card_padding,
            painter.fontMetrics().height(),
        )
        painter.drawText(
            path_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            path,
        )

        # 绘制描述
        painter.setFont(self.desc_font)
        painter.setPen(colors["desc"])
        desc_rect = QRect(
            card_rect.left() + self.card_padding,
            path_rect.bottom() + 6,
            card_rect.width() - 2 * self.card_padding,
            40,  # 描述区域固定高度
        )
        painter.drawText(
            desc_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
            description,
        )

        # 绘制标签
        painter.setFont(self.tags_font)
        tag_y = desc_rect.bottom() + 6
        tag_x = card_rect.left() + self.card_padding
        tag_height = painter.fontMetrics().height() + 4
        for tag in tags:
            tag_text = f" {tag} "
            tag_width = painter.fontMetrics().horizontalAdvance(tag_text) + 6
            tag_rect = QRect(tag_x, tag_y, tag_width, tag_height)

            painter.setBrush(QBrush(colors["tag_bg"]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(tag_rect, 3, 3)

            painter.setPen(colors["tag_text"])
            painter.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, tag_text)

            tag_x += tag_width + 4
            if tag_x > card_rect.right() - self.card_padding:
                tag_x = card_rect.left() + self.card_padding
                tag_y += tag_height + 4

        painter.restore()

    def initStyleOption(self, option, index):
        # 先调用父类，获得默认填充
        super().initStyleOption(option, index)

        # 清除文本：让默认绘制不画文字
        option.text = ""                # 清空 DisplayRole 文本
        option.icon = QIcon()           # 清空 DecorationRole 图标（如果有）

        # 移除 HasDisplay 和 HasDecoration 特性标志
        option.features &= ~QStyleOptionViewItem.ViewItemFeature.HasDisplay
        option.features &= ~QStyleOptionViewItem.ViewItemFeature.HasDecoration

        # 可选：也移除其他可能自动添加的特性（如 HasCheckIndicator）
        option.features &= ~QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator

    def sizeHint(self, option, index):
        # 根据字体和边距动态计算高度，宽度保持固定或由视图决定
        base_width = 300
        title_height = self.title_font.pointSizeF() + 4
        path_height = self.path_font.pointSizeF() + 4
        desc_height = 40
        tags_height = self.tags_font.pointSizeF() + 8
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
            + 4
        )
        return QSize(base_width, int(total_height))
