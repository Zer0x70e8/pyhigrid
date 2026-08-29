#
""""""

from typing import List, Optional, Any, Dict

from albuswall.domain.entities import IngestSourceEntity
from albuswall.repositories import IngestSourceRepository
from albuswall.domain.constants import IngestSource

ALLOWED_FIELDS = IngestSource.ALLOWED_FIELDS


class IngestSourceService:
    def __init__(self, repo: IngestSourceRepository):
        self.repo = repo

    def list_sources(self) -> List[IngestSourceEntity]:
        """获取所有导入源实体。"""
        return self.repo.get_all()

    def get_source(self, source_id: int) -> Optional[IngestSourceEntity]:
        """获取单个导入源实体。"""
        return self.repo.get_by_id(source_id)

    def create_source(self, **fields: Any) -> IngestSourceEntity:
        """创建新的导入源，应用业务规则和默认值。"""
        # 业务规则：必填字段校验
        fields.setdefault("title", "未命名导入源")
        fields.setdefault("source_path", "")
        if not fields.get("title") or not fields.get("source_path"):
            raise ValueError("title 和 source_path 不能为空")

        # 默认值填充
        fields.setdefault("file_type_check", "suffix")
        fields.setdefault("subfolder_recursion", False)

        new_id = self.repo.create(**fields)
        entity = self.repo.get_by_id(new_id)
        if entity is None:
            raise RuntimeError("创建后无法获取实体")
        return entity

    def update_source(self, source_id: int, **fields: Any) -> Optional[IngestSourceEntity]:
        """更新导入源，返回更新后的实体。"""
        # 业务规则：例如路径不可更改？或需要检查源是否存在等
        if not self.repo.exists(source_id):
            raise ValueError(f"ID {source_id} 不存在")

        # 执行更新
        success = self.repo.update(source_id, **fields)
        if success:
            return self.repo.get_by_id(source_id)
        return None

    def delete_source(self, source_id: int) -> bool:
        """删除导入源。"""
        # 可能涉及级联删除或清理操作
        return self.repo.delete(source_id)

    def export_all(self) -> List[Dict[str, Any]]:
        """导出所有导入源为字典列表（用于序列化）。"""
        entities = self.repo.get_all()
        return [entity.to_dict() for entity in entities]

    def replace_all(self, items: List[Dict[str, Any]]) -> None:
        """用给定数据完全替换所有导入源（原子操作）。"""
        # 前置校验：确保数据格式正确
        for item in items:
            if "title" not in item or "source_path" not in item:
                raise ValueError("每条数据必须包含 title 和 source_path")

        # 在事务中先删除所有现有记录，再逐个插入新记录
        with self.repo._transaction():
            self.repo.delete_all()
            for item in items:
                # 只保留允许的字段，避免传入非法列
                fields = {k: v for k, v in item.items() if k in ALLOWED_FIELDS}
                # 再次确保必填字段存在（经过过滤后仍应存在）
                if "title" not in fields or "source_path" not in fields:
                    raise ValueError("过滤后数据缺少 title 或 source_path")
                self.repo.create(**fields)
