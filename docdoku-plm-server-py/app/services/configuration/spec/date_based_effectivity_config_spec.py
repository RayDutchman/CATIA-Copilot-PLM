"""DateBasedEffectivityConfigSpec——基于日期的有效性配置规格。"""
from datetime import datetime
from app.services.configuration.spec.effectivity_config_spec import EffectivityConfigSpec
from app.models.product.date_based_effectivity import DateBasedEffectivity
from app.models.product.effectivity import Effectivity


class DateBasedEffectivityConfigSpec(EffectivityConfigSpec):
    """按日期过滤有效性。"""

    def __init__(self, date: datetime, configuration_item=None, configuration=None):
        super().__init__(configuration_item, configuration)
        self.date = date

    def is_effective(self, effectivity) -> bool:
        """检查 DateBasedEffectivity 的日期范围。"""
        if not isinstance(effectivity, DateBasedEffectivity):
            return False

        # CI 不匹配
        if self.configuration_item:
            ci = self.configuration_item
            if (effectivity.configurationitem_id != ci.id or
                effectivity.configurationitem_workspace_id != ci.workspace_id):
                return False

        # 归一为 naive（DB effectivity 日期为 timestamp without tz；请求日期可能带 Z 时区）
        date = self._as_naive(self.date)
        # startDate > date → 尚未生效
        start_date = self._as_naive(getattr(effectivity, 'start_date', None))
        if start_date and date and start_date > date:
            return False

        # endDate < date → 已过期
        end_date = self._as_naive(getattr(effectivity, 'end_date', None))
        if end_date and date and end_date < date:
            return False

        return True

    @staticmethod
    def _as_naive(dt):
        """带时区的 datetime 转为 UTC naive，便于与 DB 的 naive 时间戳比较。"""
        if dt is not None and getattr(dt, "tzinfo", None) is not None:
            from datetime import timezone
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
