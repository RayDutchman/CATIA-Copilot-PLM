"""ResolvedDocumentLink DTO。"""
from dataclasses import dataclass

@dataclass
class ResolvedDocumentLink:
    document_link_id: int
    source_document_key: str
    target_document_key: str
