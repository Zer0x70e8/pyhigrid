#
""""""

import tinycss2
from .qss_selector import (
    QssBlockEditor,
    get_selector_text,
    matches_selector
)

RADIUS_PROPS = [
    "border-radius",
    "border-top-left-radius",
    "border-top-right-radius",
    "border-bottom-left-radius",
    "border-bottom-right-radius"
]


def extract_border_radius(qss_string: str, target_selector: str,
                          match_mode: str = "base") -> dict:
    """
    从 QSS 字符串中提取与 target_selector 匹配的组件圆角信息。

    Args:
        qss_string: 完整的 QSS 样式表文本。
        target_selector: 目标组件的选择器（例如 "QPushButton"）。
        match_mode: 匹配模式，默认为 'base'（提取基础类型）。

    Returns:
        字典，键为属性名，值为对应的字符串值。
        例如 {"border-radius": "5px", "border-top-left-radius": "3px"}.
    """
    stylesheet = tinycss2.parse_stylesheet(qss_string)
    collected = {}

    for node in stylesheet:
        if node.type != "qualified-rule":
            continue  # 跳过 at-rule, 注释等

        prelude = node.prelude
        content = node.content

        # 获取当前规则的选择器文本
        rule_selector = get_selector_text(prelude)

        # 如果不匹配当前目标组件，跳过
        if not matches_selector(rule_selector, target_selector, match_mode):
            continue

        # 用 QssBlockEditor 解析当前规则的声明
        editor = QssBlockEditor(prelude, content)

        # 提取所有圆角属性（后面的覆盖前面的）
        for prop in RADIUS_PROPS:
            value = editor.get_property(prop)
            if value is not None:
                collected[prop] = value

    return collected


# ---------- 使用示例 ----------
if __name__ == "__main__":
    qss = """
    QPushButton {
        border-radius: 8px;
        background: white;
    }
    QPushButton:hover {
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
    }
    QLabel { border-radius: 2px; }
    """

    result = extract_border_radius(qss, "QPushButton", match_mode="base")
    print(result)
    # 输出: {'border-radius': '8px', 'border-top-left-radius': '10px', 'border-top-right-radius': '10px'}
