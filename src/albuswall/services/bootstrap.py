#
""""""

import logging
from typing import TYPE_CHECKING
from functools import partial

from .import_ import ImportService
from .trigger.core import TriggerService
from .common import LOGGER_HEAD
from .ingest_source_service import IngestSourceService

if TYPE_CHECKING:
    from albuswall.core import Container

logger = logging.getLogger(LOGGER_HEAD)


def safe_start_import(import_service, source_id):
    # noinspection PyBroadException
    try:
        # 将字符串转回整数，如果 ImportService 需要整数
        import_service.start_auto_import(int(source_id))
    except RuntimeError as e:
        logger.warning("Auto import already running for source %s: %s", source_id, e)
    except Exception:
        logger.exception("Failed to start auto import for source %s", source_id)


def bind_trigger_callbacks(container: "Container"):
    trigger_service = container.get("trigger_service")
    import_service = container.get("import_service")
    ingest_repo = container.get("ingest_source_repo")

    for source in ingest_repo.get_all():
        source_id = str(source.id)  # 实体属性

        # 计划触发器
        if source.scheduled_enabled:
            callback = partial(safe_start_import, import_service, source_id)
            trigger_service.add_scheduled_callback(source_id, callback)

        # 设备触发器
        if source.device_trigger_enabled:
            # TODO 设备触发器逻辑
            pass


def register_service(container: "Container"):
    container.register(
        "import_service",
        lambda: ImportService(
            container.get("importer_repo"),
            container.get("ingest_source_repo")
        )
    )
    container.register(
        "trigger_service",
        lambda: TriggerService(container.get("ingest_source_repo"))
    )
    container.register(
        "ingest_source_service",
        lambda: IngestSourceService(container.get("ingest_source_repo"))
    )

    container.on_boot(lambda: bind_trigger_callbacks(container))
    container.on_boot(lambda: (
        container.get("trigger_service").start(),
        container.get("import_service").start()
    ))
