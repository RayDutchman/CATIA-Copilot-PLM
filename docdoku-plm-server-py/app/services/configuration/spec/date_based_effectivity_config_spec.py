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

        # startDate > date → 尚未生效
        start_date = getattr(effectivity, 'start_date', None)
        if start_date and start_date > self.date:
            return False

        # endDate < date → 已过期
        end_date = getattr(effectivity, 'end_date', None)
        if end_date and end_date < self.date:
            return False

        return True
