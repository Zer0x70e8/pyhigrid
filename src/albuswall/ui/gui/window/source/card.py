#
""""""

from PySide6.QtCore import QObject
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton,
    QCheckBox, QSpinBox, QRadioButton, QComboBox,
    QWidget, QApplication
)


CHECK_FILE_TYPE_BY_ITS_EXTENSION = False
DISABLE_SUBFOLDER_RECURSION = False
SUBFOLDER_RECURSION_DEPTH_LIMITED = False
SUBFOLDER_RECURSION_DEFAULT_DEPTH = 10

class Card(QFrame):
    main_layout: QHBoxLayout

    #
    grp_source: QGroupBox
    grp_source_layout: QVBoxLayout
    source_path_line_edit: QLineEdit
    source_path_line_edit_layout: QHBoxLayout
    source_path_browser_button: QPushButton
    source_path_label: QLabel

    file_type_layout: QHBoxLayout
    file_type_label: QLabel
    file_types_layout: QHBoxLayout
    file_type_line_edit: QLineEdit
    file_type_add_button: QPushButton

    file_type_check_widget: QWidget
    file_type_check_layout: QHBoxLayout
    file_type_check_label: QLabel
    file_type_check_s_radio_button: QRadioButton
    file_type_check_mg_radio_button: QRadioButton

    subfolder_recursion_layout: QHBoxLayout
    subfolder_recursion_label: QLabel
    subfolder_recursion_check_box: QCheckBox

    subfolder_recursion_depth_layout: QHBoxLayout
    subfolder_recursion_depth_label: QLabel
    subfolder_recursion_depth_check_box: QCheckBox
    subfolder_recursion_depth_spin_box: QSpinBox

    #
    grp_scheduled: QGroupBox
    grp_scheduled_layout: QVBoxLayout

    update_mode_layout: QHBoxLayout
    update_mode_label: QLabel
    update_mode_combo: QComboBox

    scheduled_time_layout: QHBoxLayout
    scheduled_time_label: QLabel
    scheduled_time_edit: QLineEdit

    interval_time_layout: QHBoxLayout
    interval_time_label: QLabel
    interval_time_edit: QLineEdit

    disable_timer_layout: QHBoxLayout
    disable_timer_label: QLabel
    disable_timer_checkbox: QCheckBox

    #
    grp_device_insertion_trigger: QGroupBox
    grp_device_insertion_layout: QVBoxLayout

    enable_device_trigger_layout: QHBoxLayout
    enable_device_trigger_label: QLabel
    enable_device_trigger_checkbox: QCheckBox

    target_layout: QHBoxLayout
    target_label: QLabel
    target_combo: QComboBox

    auto_mount_layout: QHBoxLayout
    auto_mount_label: QLabel
    auto_mount_checkbox: QCheckBox

    mount_point_layout: QHBoxLayout
    mount_point_label: QLabel
    mount_point_edit: QLineEdit

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_object_names()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        #
        self.grp_source = QGroupBox("Ingest Source")
        self.grp_source_layout = QVBoxLayout(self.grp_source)

        self.source_path_line_edit_layout = QHBoxLayout()
        self.source_path_line_edit = QLineEdit("~/Picture/example", self.grp_source)
        self.source_path_browser_button = QPushButton(self.tr("browser"), self.grp_source)
        self.source_path_label = QLabel(self.tr("source path (library path)"), self.grp_source)

        self.source_path_line_edit_layout.addWidget(self.source_path_label, 2)
        self.source_path_line_edit_layout.addWidget(self.source_path_line_edit)
        self.source_path_line_edit_layout.addWidget(self.source_path_browser_button)

        self.file_type_layout = QHBoxLayout()
        self.file_type_label = QLabel(self.tr("file type(s)"), self.grp_source)
        self.file_types_layout = QHBoxLayout()  # add chip in there, make sure chip has close btn
        self.file_type_line_edit = QLineEdit(self.tr("gif"), self.grp_source)
        self.file_type_add_button = QPushButton(self.tr("add"), self.grp_source)

        self.file_type_layout.addWidget(self.file_type_label, 2)
        self.file_type_layout.addLayout(self.file_types_layout)
        self.file_type_layout.addWidget(self.file_type_line_edit)
        self.file_type_layout.addWidget(self.file_type_add_button, 1)

        self.file_type_check_widget = QWidget(self.grp_source)
        self.file_type_check_layout = QHBoxLayout(self.file_type_check_widget)
        self.file_type_check_label = QLabel("File type verification method", self.grp_source)
        self.file_type_check_s_radio_button = QRadioButton("Suffix Check", self.grp_source)
        self.file_type_check_mg_radio_button = QRadioButton("Magic Number Check", self.grp_source)

        self.file_type_check_layout.setContentsMargins(0, 0, 0, 0)
        self.file_type_check_mg_radio_button.setChecked(not CHECK_FILE_TYPE_BY_ITS_EXTENSION)

        self.file_type_check_layout.addWidget(self.file_type_check_label, 2)
        self.file_type_check_layout.addWidget(self.file_type_check_s_radio_button)
        self.file_type_check_layout.addWidget(self.file_type_check_mg_radio_button)

        self.subfolder_recursion_layout = QHBoxLayout()
        self.subfolder_recursion_label = QLabel(self.tr("Subfolder recursion"), self.grp_source)
        self.subfolder_recursion_check_box = QCheckBox(self.grp_source)

        self.subfolder_recursion_check_box.setChecked(not DISABLE_SUBFOLDER_RECURSION)

        self.subfolder_recursion_layout.addWidget(self.subfolder_recursion_label, 2)
        self.subfolder_recursion_layout.addWidget(self.subfolder_recursion_check_box)

        self.subfolder_recursion_depth_layout = QHBoxLayout()
        self.subfolder_recursion_depth_label = QLabel(self.tr("Subfolder recursion depth"), self.grp_source)
        self.subfolder_recursion_depth_check_box = QCheckBox(self.tr("no limit"), self.grp_source)
        self.subfolder_recursion_depth_spin_box = QSpinBox(self.grp_source)

        self.subfolder_recursion_depth_check_box.setChecked(not SUBFOLDER_RECURSION_DEPTH_LIMITED)
        self.subfolder_recursion_depth_spin_box.setValue(SUBFOLDER_RECURSION_DEFAULT_DEPTH)
        self.subfolder_recursion_depth_spin_box.setRange(0, 16777215)
        self.subfolder_recursion_depth_check_box.toggled.connect(
            self.subfolder_recursion_depth_spin_box.setDisabled
        )
        self.subfolder_recursion_depth_spin_box.setDisabled(True)

        self.subfolder_recursion_depth_layout.addWidget(self.subfolder_recursion_depth_label, 2)
        self.subfolder_recursion_depth_layout.addWidget(self.subfolder_recursion_depth_check_box)
        self.subfolder_recursion_depth_layout.addWidget(self.subfolder_recursion_depth_spin_box)

        self.grp_source_layout.addLayout(self.source_path_line_edit_layout)
        self.grp_source_layout.addLayout(self.file_type_layout)
        self.grp_source_layout.addWidget(self.file_type_check_widget)
        self.grp_source_layout.addLayout(self.subfolder_recursion_layout)
        self.grp_source_layout.addLayout(self.subfolder_recursion_depth_layout)

        #
        self.grp_scheduled = QGroupBox(self.tr("Scheduled Update"), self)
        self.grp_scheduled_layout = QVBoxLayout(self.grp_scheduled)

        self.update_mode_layout = QHBoxLayout()
        self.update_mode_label = QLabel(self.tr("mode"), self.grp_scheduled)
        self.update_mode_combo = QComboBox(self.grp_scheduled)

        self.update_mode_combo.addItem(self.tr("Scheduled Time"))
        self.update_mode_combo.addItem(self.tr("Interval Time"))
        self.update_mode_combo.currentIndexChanged.connect(self._on_update_mode_changed)

        self.update_mode_layout.addWidget(self.update_mode_label, 2)
        self.update_mode_layout.addWidget(self.update_mode_combo)

        self.scheduled_time_layout = QHBoxLayout()
        self.scheduled_time_label = QLabel(self.tr("Scheduled Time"), self.grp_scheduled)
        self.scheduled_time_edit = QLineEdit(self.grp_scheduled)

        self.scheduled_time_edit.setPlaceholderText("HH:MM")

        self.scheduled_time_layout.addWidget(self.scheduled_time_label, 2)
        self.scheduled_time_layout.addWidget(self.scheduled_time_edit)

        self.interval_time_layout = QHBoxLayout()
        self.interval_time_label = QLabel(self.tr("Interval Time"), self.grp_scheduled)
        self.interval_time_edit = QLineEdit(self.grp_scheduled)

        self.interval_time_edit.setPlaceholderText(self.tr("e.g., 30m or 1h"))

        self.interval_time_layout.addWidget(self.interval_time_label, 2)
        self.interval_time_layout.addWidget(self.interval_time_edit)

        self.disable_timer_layout = QHBoxLayout()
        self.disable_timer_label = QLabel(self.tr("Disable Timer"), self.grp_scheduled)
        self.disable_timer_checkbox = QCheckBox(self.grp_scheduled)
        self.disable_timer_checkbox.toggled.connect(self._on_disable_timer_toggled)

        self.disable_timer_layout.addWidget(self.disable_timer_label, 2)
        self.disable_timer_layout.addWidget(self.disable_timer_checkbox)

        self.grp_scheduled_layout.addLayout(self.update_mode_layout)
        self.grp_scheduled_layout.addLayout(self.scheduled_time_layout)
        self.grp_scheduled_layout.addLayout(self.interval_time_layout)
        self.grp_scheduled_layout.addLayout(self.disable_timer_layout)

        #
        self.grp_device_insertion_trigger = QGroupBox(self.tr("Device Insertion Trigger"), self)
        self.grp_device_insertion_layout = QVBoxLayout(self.grp_device_insertion_trigger)

        self.enable_device_trigger_layout = QHBoxLayout()
        self.enable_device_trigger_label = QLabel(self.tr("Enable trigger on device insertion"),
                                                  self.grp_device_insertion_trigger)
        self.enable_device_trigger_checkbox = QCheckBox(self.grp_device_insertion_trigger)

        self.enable_device_trigger_layout.addWidget(self.enable_device_trigger_label, 2)
        self.enable_device_trigger_layout.addWidget(self.enable_device_trigger_checkbox)

        self.target_layout = QHBoxLayout()
        self.target_label = QLabel(self.tr("Target"), self.grp_device_insertion_trigger)
        self.target_combo = QComboBox(self.grp_device_insertion_trigger)
        # 可按需添加默认项，例如：
        # self.target_combo.addItems([...])
        self.target_layout.addWidget(self.target_label, 2)
        self.target_layout.addWidget(self.target_combo)

        self.auto_mount_layout = QHBoxLayout()
        self.auto_mount_label = QLabel(self.tr("Auto-mount (Linux only, requires permissions)"),
                                       self.grp_device_insertion_trigger)
        self.auto_mount_checkbox = QCheckBox(self.grp_device_insertion_trigger)

        self.auto_mount_layout.addWidget(self.auto_mount_label, 2)
        self.auto_mount_layout.addWidget(self.auto_mount_checkbox)

        self.mount_point_layout = QHBoxLayout()
        self.mount_point_label = QLabel(self.tr("Mount point"), self.grp_device_insertion_trigger)
        self.mount_point_edit = QLineEdit(self.grp_device_insertion_trigger)
        self.mount_point_edit.setPlaceholderText("/media/example/auto_import")
        self.mount_point_layout.addWidget(self.mount_point_label, 2)
        self.mount_point_layout.addWidget(self.mount_point_edit)

        self.mount_point_edit.setEnabled(self.auto_mount_checkbox.isChecked())
        self.auto_mount_checkbox.toggled.connect(self.mount_point_edit.setEnabled)

        self.grp_device_insertion_layout.addLayout(self.enable_device_trigger_layout)
        self.grp_device_insertion_layout.addLayout(self.target_layout)
        self.grp_device_insertion_layout.addLayout(self.auto_mount_layout)
        self.grp_device_insertion_layout.addLayout(self.mount_point_layout)

        #
        layout.addWidget(self.grp_source)
        layout.addWidget(self.grp_scheduled)
        layout.addWidget(self.grp_device_insertion_trigger)

        # 初始化互斥状态
        self._on_update_mode_changed(self.update_mode_combo.currentIndex())
        self._on_disable_timer_toggled(self.disable_timer_checkbox.isChecked())


    def setup_object_names(self):
        """为 Card 自身及所有绑定在 self 上的控件/布局设置唯一 objectName"""
        prefix = type(self).__name__
        # Card 自身
        self.setObjectName(prefix)

        # 遍历实例属性，为 QObject 子类自动命名
        for attr_name, value in self.__dict__.items():
            if isinstance(value, QObject) and not attr_name.startswith('_'):
                # 将下划线命名转为首字母大写的驼峰：monitor_status_label -> MonitorStatusLabel
                camel_name = ''.join(part.capitalize() for part in attr_name.split('_'))
                # 加上类名前缀避免全局冲突
                obj_name = f"{prefix}{camel_name}"
                value.setObjectName(obj_name)

    def _on_update_mode_changed(self, index):
        """根据下拉菜单选择，切换对应输入框的可用状态"""
        if index == 0:  # Scheduled Time
            self.scheduled_time_edit.setEnabled(True)
            self.interval_time_edit.setEnabled(False)
        else:  # Interval Time
            self.scheduled_time_edit.setEnabled(False)
            self.interval_time_edit.setEnabled(True)

    def _on_disable_timer_toggled(self, checked):
        """关闭定时复选框：禁用/启用下拉菜单和两个时间输入框"""
        self.update_mode_combo.setDisabled(checked)
        self.scheduled_time_edit.setEnabled(not checked)
        self.interval_time_edit.setEnabled(not checked)
        # 如果取消勾选“关闭定时”，恢复模式互斥状态
        if not checked:
            self._on_update_mode_changed(self.update_mode_combo.currentIndex())


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)

    window = QWidget()
    widget = Card(window)
    _layout = QVBoxLayout(window)
    _layout.addWidget(widget)
    _layout.addStretch()
    window.resize(600, 800)
    window.setStyleSheet("""
    QGroupBox {
        font-weight: bold;
        margin-top: 12px;
        padding-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
    }  

    /*
    #CardSourcePathLabel,
    #CardFileTypeLabel,
    #CardFileTypeCheckLabel,
    #CardSubfolderRecursionLabel,
    #CardSubfolderRecursionDepthLabel {
        max-width: 160px;
    }
    */

    Card QPushButton{
        max-width: 4em
    }
    """)
    window.show()

    sys.exit(app.exec())
