import sys
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QPushButton,
    QTextEdit,
    QHBoxLayout,
)

class FormWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide6 FormLayout 不同组件示例")
        self.resize(500, 350)

        # 主布局
        form = QFormLayout(self)

        # 辅助函数：为每个 field 创建 stretch + widget 的布局
        def add_row(label, widget):
            row_layout = QHBoxLayout()
            row_layout.addStretch(1)          # 弹性空白在 label 和 widget 之间
            row_layout.addWidget(widget)      # 添加组件
            form.addRow(label, row_layout)

        # 1. 姓名：QLineEdit
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("请输入姓名")
        name_edit.setFixedWidth(200)
        add_row("姓名：", name_edit)

        # 2. 性别：QComboBox
        gender_combo = QComboBox()
        gender_combo.addItems(["男", "女", "其他"])
        gender_combo.setFixedWidth(200)
        add_row("性别：", gender_combo)

        # 3. 年龄：QSpinBox
        age_spin = QSpinBox()
        age_spin.setRange(0, 150)
        age_spin.setValue(20)
        age_spin.setFixedWidth(200)
        add_row("年龄：", age_spin)

        # 4. 是否订阅：QCheckBox
        subscribe_check = QCheckBox("订阅邮件通知")
        # 对于复选框，不需要固定宽度，但为了对齐可以设置
        # 注意：QCheckBox 本身包含文本，这里作为 field 组件
        add_row("订阅：", subscribe_check)

        # 5. 提交按钮：QPushButton
        submit_btn = QPushButton("提交")
        submit_btn.setFixedWidth(200)
        add_row("操作：", submit_btn)

        # 6. 备注：QTextEdit
        notes_edit = QTextEdit()
        notes_edit.setPlaceholderText("请输入备注信息")
        notes_edit.setFixedWidth(200)
        notes_edit.setFixedHeight(80)
        add_row("备注：", notes_edit)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FormWindow()
    window.show()
    sys.exit(app.exec())