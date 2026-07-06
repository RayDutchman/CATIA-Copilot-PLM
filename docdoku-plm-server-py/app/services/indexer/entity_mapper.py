"""EntityMapper——将 DocumentIteration/PartIteration 序列化为 ES 文档。

对齐 Java EntityMapper。
"""
from typing import Dict
from app.services.indexer import indexer_mapping as m


def document_iteration_to_es(doc_iteration, content_map: Dict[str, str] = None) -> dict:
    """将 DocumentIteration 映射为 ES 索引文档。"""
    rev = doc_iteration.document_revision
    master = rev.document_master
    workspace_id = rev.workspace_id
    doc_id = rev.documentmaster_id

    body = {
        m.WORKSPACE_ID_KEY: workspace_id,
        m.DOCUMENT_ID_KEY: doc_id,
        m.VERSION_KEY: rev.version,
        m.ITERATION_KEY: doc_iteration.iteration,
        m.TITLE_KEY: master.title or "",
        m.DESCRIPTION_KEY: rev.description or "",
        m.TYPE_KEY: master.type or "",
        m.AUTHOR_LOGIN_KEY: master.author_login or "",
        m.AUTHOR_NAME_KEY: master.author_login or "",
        m.CREATION_DATE_KEY: (doc_iteration.creation_date.isoformat()
                               if doc_iteration.creation_date else None),
        m.MODIFICATION_DATE_KEY: (doc_iteration.modification_date.isoformat()
                                   if doc_iteration.modification_date else None),
        m.REVISION_NOTE_KEY: doc_iteration.iteration_note or "",
        m.TAGS_KEY: [t.label for t in (rev.tags or [])],
        m.FOLDER_KEY: master.folder_id or "",
        m.ATTRIBUTES_KEY: _map_instance_attributes(doc_iteration.instance_attributes),
        m.FILES_KEY: _map_attached_files(doc_iteration.attached_files, content_map),
        m.WORKFLOW_KEY: _map_workflow(rev.workflow),
    }
    return body


def part_iteration_to_es(part_iteration, content_map: Dict[str, str] = None) -> dict:
    """将 PartIteration 映射为 ES 索引文档。"""
    rev = part_iteration.revision
    master = rev.part_master
    workspace_id = rev.workspace_id
    part_number = rev.partmaster_partnumber

    body = {
        m.WORKSPACE_ID_KEY: workspace_id,
        m.PART_NUMBER_KEY: part_number,
        m.PART_NAME_KEY: master.name or "",
        m.VERSION_KEY: rev.version,
        m.ITERATION_KEY: part_iteration.iteration,
        m.TYPE_KEY: master.type or "",
        m.STANDARD_PART_KEY: master.standard_part or False,
        m.DESCRIPTION_KEY: rev.description or "",
        m.AUTHOR_LOGIN_KEY: master.author_login or "",
        m.AUTHOR_NAME_KEY: master.author_login or "",
        m.CREATION_DATE_KEY: (part_iteration.creation_date.isoformat()
                               if part_iteration.creation_date else None),
        m.MODIFICATION_DATE_KEY: (part_iteration.modification_date.isoformat()
                                   if part_iteration.modification_date else None),
        m.REVISION_NOTE_KEY: part_iteration.iteration_note or "",
        m.TAGS_KEY: [t.label for t in (rev.tags or [])],
        m.ATTRIBUTES_KEY: _map_instance_attributes(part_iteration.instance_attributes),
        m.FILES_KEY: _map_attached_files(part_iteration.attached_files, content_map),
        m.WORKFLOW_KEY: _map_workflow(rev.workflow),
    }
    return body


def _map_instance_attributes(attributes) -> list:
    """映射实例属性。"""
    if not attributes:
        return []
    result = []
    for attr in attributes:
        attr_name = getattr(attr, 'name', '') or ''
        if hasattr(attr, 'value'):
            attr_value = attr.value
        elif hasattr(attr, 'selected_value'):
            attr_value = attr.selected_value or ''
        elif hasattr(attr, 'date_value'):
            attr_value = str(attr.date_value) if attr.date_value else ''
        else:
            attr_value = str(attr) if attr else ''
        result.append({m.ATTRIBUTE_NAME: attr_name, m.ATTRIBUTE_VALUE: attr_value})
    return result


def _map_attached_files(files, content_map: Dict[str, str] = None) -> list:
    """映射附件文件（含文本内容提取）。"""
    if not files:
        return []
    cmap = content_map or {}
    result = []
    for f in files:
        entry = {m.FILE_NAME_KEY: getattr(f, 'name', '') or ''}
        if getattr(f, 'full_name', ''):
            full_name = f.full_name
            if full_name in cmap:
                entry[m.CONTENT_KEY] = cmap[full_name]
        result.append(entry)
    return result


def _map_workflow(workflow) -> str:
    """获取工作流当前状态。"""
    if workflow is None:
        return None
    # 取 workflow 的当前 lifecycle state
    return getattr(workflow, 'final_lifecyclestate', '')
