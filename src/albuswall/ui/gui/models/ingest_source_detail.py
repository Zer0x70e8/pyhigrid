# 
""""""

from typing import TypedDict, List, Optional, Literal, Union, overload

from PySide6.QtCore import QObject, Signal


try:
    from .tag_list_model import TagListModel
    from ..common.ingest_source import FileTypeCheckEnum
    from ..delegates.tag_delegate import TagDelegate
except ImportError:
    from albuswall.ui.gui.models.tag_list_model import TagListModel
    from albuswall.ui.gui.common.ingest_source import FileTypeCheckEnum
    from albuswall.ui.gui.delegates.tag_delegate import TagDelegate


class IngestSourceDictSerialized(TypedDict):
    title: str
    description: str
    tags: List[str]
    source_path: str
    file_types: List[str]
    file_type_check: str
    subfolder_recursion: bool
    subfolder_recursion_depth: Optional[int]
    scheduled_enabled: bool
    update_mode: str
    scheduled_time: str
    interval_time: str
    device_trigger_enabled: bool
    target: str
    auto_mount: bool
    mount_point: str


class IngestSourceDictRaw(TypedDict):
    title: str
    description: str
    tags: List[str]
    source_path: str
    file_types: List[str]
    file_type_check: FileTypeCheckEnum
    subfolder_recursion: bool
    subfolder_recursion_depth: Optional[int]
    scheduled_enabled: bool
    update_mode: str
    scheduled_time: str
    interval_time: str
    device_trigger_enabled: bool
    target: str
    auto_mount: bool
    mount_point: str


class IngestSourceDetailModel(QObject):
    """摄入源数据模型，管理所有配置字段，变更时发出 dataChanged 信号。"""

    dataChanged = Signal()  # 任意数据变化时发出

    def __init__(self, parent=None):
        super().__init__(parent)
        # 使用 TagListModel 替代简单的列表
        self._tags_model = TagListModel()
        self._file_types_model = TagListModel()
        self._title = "new ingest source"
        self._description = "example"
        self._source_path = ""
        self._file_type_check: FileTypeCheckEnum = FileTypeCheckEnum.suffix
        self._subfolder_recursion = False
        self._subfolder_recursion_depth = None  # None 表示无限制
        self._scheduled_enabled = False
        self._update_mode = "scheduled_time"  # "scheduled_time" 或 "interval_time"
        self._scheduled_time = ""
        self._interval_time = ""
        self._device_trigger_enabled = False
        self._target = ""
        self._auto_mount = False
        self._mount_point = ""

    # ========== 属性访问器（setter 发出 dataChanged） ==========
    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        if self._title != value:
            self._title = value
            self.dataChanged.emit()

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        if self._description != value:
            self._description = value
            self.dataChanged.emit()

    @property
    def tags(self):
        """返回标签列表的副本（向后兼容）。"""
        return self._tags_model.tags()

    @tags.setter
    def tags(self, value):
        """设置标签列表，内部更新 TagListModel。"""
        self._tags_model.set_tags(list(value))
        self.dataChanged.emit()

    @property
    def tags_model(self):
        """返回标签的 TagListModel，供视图直接使用。"""
        return self._tags_model

    @property
    def source_path(self):
        return self._source_path

    @source_path.setter
    def source_path(self, value):
        if self._source_path != value:
            self._source_path = value
            self.dataChanged.emit()

    @property
    def file_types(self):
        """返回文件类型列表的副本（向后兼容）。"""
        return self._file_types_model.tags()

    @file_types.setter
    def file_types(self, value):
        """设置文件类型列表，内部更新 TagListModel。"""
        self._file_types_model.set_tags(list(value))
        self.dataChanged.emit()

    @property
    def file_types_model(self):
        """返回文件类型的 TagListModel，供视图直接使用。"""
        return self._file_types_model

    @property
    def file_type_check(self):
        return self._file_type_check

    @file_type_check.setter
    def file_type_check(self, value):
        # 接受字符串或枚举，统一转换为 FileTypeCheckEnum
        if isinstance(value, str):
            value = FileTypeCheckEnum(value)
        if not isinstance(value, FileTypeCheckEnum):
            raise TypeError("file_type_check must be a FileTypeCheckEnum or string")
        if self._file_type_check != value:
            self._file_type_check = value
            self.dataChanged.emit()

    @property
    def subfolder_recursion(self):
        return self._subfolder_recursion

    @subfolder_recursion.setter
    def subfolder_recursion(self, value):
        if self._subfolder_recursion != bool(value):
            self._subfolder_recursion = bool(value)
            self.dataChanged.emit()

    @property
    def subfolder_recursion_depth(self):
        return self._subfolder_recursion_depth

    @subfolder_recursion_depth.setter
    def subfolder_recursion_depth(self, value):
        if value is None:
            new_value = None
        else:
            new_value = int(value)
        if self._subfolder_recursion_depth != new_value:
            self._subfolder_recursion_depth = new_value
            self.dataChanged.emit()

    @property
    def scheduled_enabled(self):
        return self._scheduled_enabled

    @scheduled_enabled.setter
    def scheduled_enabled(self, value):
        if self._scheduled_enabled != bool(value):
            self._scheduled_enabled = bool(value)
            self.dataChanged.emit()

    @property
    def update_mode(self):
        return self._update_mode

    @update_mode.setter
    def update_mode(self, value):
        if value not in ("scheduled_time", "interval_time"):
            raise ValueError("update_mode must be 'scheduled_time' or 'interval_time'")
        if self._update_mode != value:
            self._update_mode = value
            self.dataChanged.emit()

    @property
    def scheduled_time(self):
        return self._scheduled_time

    @scheduled_time.setter
    def scheduled_time(self, value):
        if self._scheduled_time != value:
            self._scheduled_time = value
            self.dataChanged.emit()

    @property
    def interval_time(self):
        return self._interval_time

    @interval_time.setter
    def interval_time(self, value):
        if self._interval_time != value:
            self._interval_time = value
            self.dataChanged.emit()

    @property
    def device_trigger_enabled(self):
        return self._device_trigger_enabled

    @device_trigger_enabled.setter
    def device_trigger_enabled(self, value):
        if self._device_trigger_enabled != bool(value):
            self._device_trigger_enabled = bool(value)
            self.dataChanged.emit()

    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, value):
        if self._target != value:
            self._target = value
            self.dataChanged.emit()

    @property
    def auto_mount(self):
        return self._auto_mount

    @auto_mount.setter
    def auto_mount(self, value):
        if self._auto_mount != bool(value):
            self._auto_mount = bool(value)
            self.dataChanged.emit()

    @property
    def mount_point(self):
        return self._mount_point

    @mount_point.setter
    def mount_point(self, value):
        if self._mount_point != value:
            self._mount_point = value
            self.dataChanged.emit()

    # ========== 字典转换 ==========
    @overload
    def to_dict(self, serialize: Literal[True]) -> IngestSourceDictSerialized:
        ...

    @overload
    def to_dict(self, serialize: Literal[False]) -> IngestSourceDictRaw:
        ...

    @overload
    def to_dict(self, serialize: bool = True) -> Union[IngestSourceDictSerialized, IngestSourceDictRaw]:
        ...

    def to_dict(self, serialize=True):
        """导出模型数据为字典。

        Args:
            serialize: 如果为 True，则将枚举等非基本类型转换为可序列化的形式
                       （如字符串），并返回列表的浅拷贝，适合 JSON 存储。
                       如果为 False，则尽量返回原始对象（如枚举对象、列表引用），
                       不创建副本，调用者修改返回的列表会影响模型内部状态。

        Returns:
            包含所有字段的字典。
        """
        if serialize:
            return {
                "title": self._title,
                "description": self._description,
                "tags": self.tags,          # 已经是副本
                "source_path": self._source_path,
                "file_types": self.file_types,  # 已经是副本
                "file_type_check": self._file_type_check.value,
                "subfolder_recursion": self._subfolder_recursion,
                "subfolder_recursion_depth": self._subfolder_recursion_depth,
                "scheduled_enabled": self._scheduled_enabled,
                "update_mode": self._update_mode,
                "scheduled_time": self._scheduled_time,
                "interval_time": self._interval_time,
                "device_trigger_enabled": self._device_trigger_enabled,
                "target": self._target,
                "auto_mount": self._auto_mount,
                "mount_point": self._mount_point,
            }
        else:
            return {
                "title": self._title,
                "description": self._description,
                "tags": self.tags,          # 返回副本，安全
                "source_path": self._source_path,
                "file_types": self.file_types,  # 返回副本，安全
                "file_type_check": self._file_type_check,  # 保留枚举对象
                "subfolder_recursion": self._subfolder_recursion,
                "subfolder_recursion_depth": self._subfolder_recursion_depth,
                "scheduled_enabled": self._scheduled_enabled,
                "update_mode": self._update_mode,
                "scheduled_time": self._scheduled_time,
                "interval_time": self._interval_time,
                "device_trigger_enabled": self._device_trigger_enabled,
                "target": self._target,
                "auto_mount": self._auto_mount,
                "mount_point": self._mount_point,
            }

    @classmethod
    def from_dict(cls, data):
        """从字典创建模型实例，并批量设置数据（只发出一次 dataChanged）。"""
        model = cls()
        # 暂时阻塞信号，最后统一发出
        model.blockSignals(True)
        try:
            for key, value in data.items():
                if hasattr(model, key):
                    setattr(model, key, value)
        finally:
            model.blockSignals(False)
        model.dataChanged.emit()
        return model

    def update_from_dict(self, data: dict):
        """用字典更新现有实例，只发出一次 dataChanged 信号"""
        self.blockSignals(True)
        try:
            for key, value in data.items():
                if hasattr(self, key):
                    setattr(self, key, value)
        finally:
            self.blockSignals(False)
        self.dataChanged.emit()

    # ========== 与界面控件交互 ==========
    def load_from_widget(self, widget):
        """从 IngestSourceDetailWidget 实例读取所有控件的值并更新模型。"""
        # 临时阻塞信号，避免多次触发
        self.blockSignals(True)
        try:
            self.title = widget.title_line_edit.text()
            self.description = widget.description_line_edit.text()

            # 标签列表：直接从 TagListModel 获取（假设已设置）
            # 但如果没有设置，则使用当前 tags_model 的内容
            tags_model = widget.tags_view.model()
            if isinstance(tags_model, TagListModel):
                self.tags = tags_model.tags()
            else:
                # 如果意外不是 TagListModel，保留原值或清空
                # 但为了健壮性，从当前模型获取
                self.tags = self._tags_model.tags()

            self.source_path = widget.source_path_line_edit.text()

            # 文件类型列表
            ft_model = widget.file_type_list_view.model()
            if isinstance(ft_model, TagListModel):
                self.file_types = ft_model.tags()
            else:
                self.file_types = self._file_types_model.tags()

            # 文件类型校验方式
            if widget.file_type_check_s_radio_button.isChecked():
                self.file_type_check = "suffix"
            else:
                self.file_type_check = "magic"

            self.subfolder_recursion = widget.subfolder_recursion_check_box.isChecked()

            # 递归深度：如果“无限制”被选中则为 None
            if widget.subfolder_recursion_depth_check_box.isChecked():
                self.subfolder_recursion_depth = None
            else:
                self.subfolder_recursion_depth = widget.subfolder_recursion_depth_spin_box.value()

            # 计划更新
            self.scheduled_enabled = widget.grp_scheduled.isChecked()
            if widget.update_mode_combo.currentIndex() == 0:
                self.update_mode = "scheduled_time"
            else:
                self.update_mode = "interval_time"
            self.scheduled_time = widget.scheduled_time_edit.text()
            self.interval_time = widget.interval_time_edit.text()

            # 设备插入触发器
            self.device_trigger_enabled = widget.grp_device_insertion_trigger.isChecked()
            self.target = widget.target_combo.currentText()
            self.auto_mount = widget.auto_mount_checkbox.isChecked()
            self.mount_point = widget.mount_point_edit.text()
        finally:
            self.blockSignals(False)
        self.dataChanged.emit()

    def apply_to_widget(self, widget):
        """将模型数据写入 IngestSourceDetailWidget 的控件中，并设置 TagListModel 和 TagDelegate。"""
        widget.blockSignals(True)
        try:
            widget.title_line_edit.setText(self.title)
            widget.description_line_edit.setText(self.description)

            # 设置标签列表：使用 TagListModel
            widget.tags_view.setModel(self._tags_model)
            # 安装 TagDelegate（如果尚未安装）
            if not hasattr(widget.tags_view, '_tag_delegate_set'):
                widget.tags_view.setItemDelegate(TagDelegate(widget.tags_view))
                widget.tags_view._tag_delegate_set = True
            # 清空输入框
            widget.tags_line_edit.clear()

            # 安全断开旧连接（使用字符串信号名）
            if widget.tags_button.receivers('clicked()') > 0:
                widget.tags_button.clicked.disconnect()
            # 连接新的槽函数
            widget.tags_button.clicked.connect(
                lambda: self._add_tag_from_input(widget.tags_line_edit)
            )

            widget.source_path_line_edit.setText(self.source_path)

            # 设置文件类型列表
            widget.file_type_list_view.setModel(self._file_types_model)
            if not hasattr(widget.file_type_list_view, '_tag_delegate_set'):
                widget.file_type_list_view.setItemDelegate(TagDelegate(widget.file_type_list_view))
                widget.file_type_list_view._tag_delegate_set = True
            widget.file_type_line_edit.clear()

            # 安全断开旧连接
            if widget.file_type_add_button.receivers('clicked()') > 0:
                widget.file_type_add_button.clicked.disconnect()
            widget.file_type_add_button.clicked.connect(
                lambda: self._add_file_type_from_input(widget.file_type_line_edit)
            )

            # 文件类型校验方式
            widget.file_type_check_s_radio_button.setChecked(self.file_type_check == "suffix")
            widget.file_type_check_mg_radio_button.setChecked(self.file_type_check == "magic")

            widget.subfolder_recursion_check_box.setChecked(self.subfolder_recursion)
            if self.subfolder_recursion_depth is None:
                widget.subfolder_recursion_depth_check_box.setChecked(True)
                widget.subfolder_recursion_depth_spin_box.setValue(0)
            else:
                widget.subfolder_recursion_depth_check_box.setChecked(False)
                widget.subfolder_recursion_depth_spin_box.setValue(self.subfolder_recursion_depth)

            widget.grp_scheduled.setChecked(self.scheduled_enabled)
            widget.update_mode_combo.setCurrentIndex(0 if self.update_mode == "scheduled_time" else 1)
            widget.scheduled_time_edit.setText(self.scheduled_time)
            widget.interval_time_edit.setText(self.interval_time)

            widget.grp_device_insertion_trigger.setChecked(self.device_trigger_enabled)
            widget.target_combo.setCurrentText(self.target)
            widget.auto_mount_checkbox.setChecked(self.auto_mount)
            widget.mount_point_edit.setText(self.mount_point)
        finally:
            widget.blockSignals(False)

    # ---------- 内部槽函数 ----------
    def _add_tag_from_input(self, line_edit):
        tag = line_edit.text().strip()
        if tag and self._tags_model.add_tag(tag):
            line_edit.clear()

    def _add_file_type_from_input(self, line_edit):
        file_type = line_edit.text().strip()
        if file_type and self._file_types_model.add_tag(file_type):
            line_edit.clear()
