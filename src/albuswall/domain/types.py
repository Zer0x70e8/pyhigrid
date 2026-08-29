#
""""""


from typing import Optional, TypedDict, List, Dict, Any, Tuple


class IngestSourceFields(TypedDict, total=False):
    title: str
    description: Optional[str]
    source_path: str
    target_path: Optional[str]
    mount_point: Optional[str]
    auto_mount: bool
    file_type_check: Optional[bool]
    file_types: Optional[List[str]]
    tags: Optional[List[str]]
    subfolder_recursion: bool
    subfolder_recursion_depth: Optional[int]
    trigger_config: Optional[Dict[str, Any]]


class TriggerConfigBasic(TypedDict, total=False):
    """目前trigger json中会出现的全部字段"""
    scheduled_enabled: bool
    update_mode: str
    scheduled_time: str
    interval_time: str
    device_trigger_enabled: bool
    target: str
    auto_mount: bool
    mount_point: str


class ScheduledTriggerConfig(TriggerConfigBasic):
    scheduled_enabled: bool
    update_mode: str
    scheduled_time: str
    interval_time: str


class DeviceTriggerConfig(TriggerConfigBasic):
    device_trigger_enabled: bool
    target: str
    auto_mount: bool
    mount_point: str

class SourceMeta(TypedDict):
    """导入源的基本元数据（来自 ingest_source 表）。"""
    source_id: str
    title: str
    source_path: str


ScheduledTriggerTuple = Tuple[SourceMeta, ScheduledTriggerConfig]
DeviceTriggerTuple = Tuple[SourceMeta, DeviceTriggerConfig]
