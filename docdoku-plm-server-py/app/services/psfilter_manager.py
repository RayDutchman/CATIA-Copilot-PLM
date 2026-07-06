"""产品结构过滤器管理——对标 Payara PSFilterManagerBean。

获取基线/产品实例配置的 PSFilter。返回实际 ProductStructureFilter 实例。
"""
from sqlalchemy.orm import Session


class PSFilterService:
    """PSFilter 管理服务。"""

    def get_baseline_psfilter(self, db: Session, ws: str,
                                baseline_id: int):
        """获取基线对应的 PSFilter。"""
        from sqlalchemy import text
        row = db.execute(text(
            "SELECT * FROM productbaseline WHERE id = :id AND workspace_id = :ws"
        ), {"id": baseline_id, "ws": ws}).first()
        if not row:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("BaselineNotFoundException", str(baseline_id))
        from app.services.configuration import LatestCheckedInPSFilter
        return LatestCheckedInPSFilter()

    def get_product_instance_psfilter(self, db: Session, ws: str,
                                        part_number: str, ci_id: str,
                                        serial_number: str):
        """获取产品实例配置对应的 PSFilter。"""
        from sqlalchemy import text
        row = db.execute(text(
            "SELECT * FROM productinstancemaster "
            "WHERE workspace_id = :ws AND configurationitem_id = :ci "
            "AND serialnumber = :sn"
        ), {"ws": ws, "ci": ci_id, "sn": serial_number}).first()
        if not row:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("ProductInstanceMasterNotFoundException", serial_number)
        from app.services.configuration import LatestCheckedInPSFilter
        return LatestCheckedInPSFilter()

    def get_psfilter(self, db: Session, ws: str, part_number: str,
                      ci_id: str, filter_type: str, diverge: bool = False):
        """获取通用 PSFilter，返回 ProductStructureFilter 实例。

        filter_type 可选值：latest, latest-checked-in, latest-released, released, wip
        """
        from app.services.configuration import (
            LatestCheckedInPSFilter, LatestReleasedPSFilter,
            ReleasedPSFilter, WIPPSFilter,
        )
        filters = {
            "latest": LatestCheckedInPSFilter,
            "latest-checked-in": LatestCheckedInPSFilter,
            "latest-released": LatestReleasedPSFilter,
            "released": ReleasedPSFilter,
            "wip": WIPPSFilter,
        }
        filter_cls = filters.get(filter_type)
        if filter_cls is None:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("FilterNotFoundException", filter_type)
        return filter_cls(diverge=diverge)


psfilter_service = PSFilterService()
