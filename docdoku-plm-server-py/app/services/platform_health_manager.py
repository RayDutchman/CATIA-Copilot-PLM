"""平台健康检查——对标 Payara PlatformHealthManagerBean。"""
import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class PlatformHealthService:
    """平台健康检查服务。"""

    def run_health_check(self, db: Session) -> dict:
        """检查数据库、ES、存储的连通性。"""
        results = {
            "database": True,
            "elasticsearch": False,
            "storage": False,
        }
        try:
            db.execute(db.bind.clause)
        except Exception as e:
            results["database"] = False
            results["database_error"] = str(e)

        try:
            from app.services.indexer_manager import indexer_manager
            results["elasticsearch"] = indexer_manager.ping()
        except Exception as e:
            results["elasticsearch_error"] = str(e)

        try:
            from app.services.vault import vault
            # 检查 vault 路径存在
            import os
            results["storage"] = os.path.isdir(vault.base_path) if hasattr(vault, 'base_path') else False
        except Exception as e:
            results["storage_error"] = str(e)

        return results


platform_health_service = PlatformHealthService()
