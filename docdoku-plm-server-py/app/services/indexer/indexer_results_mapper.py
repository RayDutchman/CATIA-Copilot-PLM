"""IndexerResultsMapper——ES 搜索结果映射为业务对象。

对齐 Java IndexerResultsMapper。
"""
from sqlalchemy.orm import Session


class IndexerResultsMapper:
    """ES 搜索结果 → 业务对象映射器。"""

    def map_document_search_results(self, db: Session, search_response: dict) -> list:
        """将 ES 搜索结果映射为 DocumentRevision 列表。"""
        from app.models.document import DocumentRevision
        hits = search_response.get("hits", {}).get("hits", [])
        results = []
        for hit in hits:
            source = hit.get("_source", {})
            ws = source.get("workspaceId")
            doc_id = source.get("docMId")
            ver = source.get("version")
            if ws and doc_id and ver:
                rev = db.query(DocumentRevision).filter(
                    DocumentRevision.workspace_id == ws,
                    DocumentRevision.documentmaster_id == doc_id,
                    DocumentRevision.version == ver,
                ).first()
                if rev:
                    results.append(rev)
        return results

    def map_part_search_results(self, db: Session, search_response: dict) -> list:
        """将 ES 搜索结果映射为 PartRevision 列表。"""
        from app.models.part import PartRevision
        hits = search_response.get("hits", {}).get("hits", [])
        results = []
        for hit in hits:
            source = hit.get("_source", {})
            ws = source.get("workspaceId")
            pn = source.get("partNumber")
            ver = source.get("version")
            if ws and pn and ver:
                rev = db.query(PartRevision).filter(
                    PartRevision.workspace_id == ws,
                    PartRevision.partmaster_partnumber == pn,
                    PartRevision.version == ver,
                ).first()
                if rev:
                    results.append(rev)
        return results


indexer_results_mapper = IndexerResultsMapper()
