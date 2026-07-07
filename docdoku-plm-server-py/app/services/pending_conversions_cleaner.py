"""挂起转换清理——对标 Payara PendingConversionsCleaner。

定时任务：清除超时的 pending conversion 记录。
"""
import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class PendingConversionsCleaner:
    """清理长时间挂起的转换记录。"""

    def run(self, db: Session) -> int:
        """清除 pending 超时的 conversion 记录。"""
        from sqlalchemy import text
        result = db.execute(text(
            "DELETE FROM conversion WHERE pending = true "
            "AND startdate < NOW() - INTERVAL '1 hour'"
        ))
        db.commit()
        count = result.rowcount
        if count > 0:
            logger.info("Cleaned %d pending conversions", count)
        return count


pending_conversions_cleaner = PendingConversionsCleaner()
