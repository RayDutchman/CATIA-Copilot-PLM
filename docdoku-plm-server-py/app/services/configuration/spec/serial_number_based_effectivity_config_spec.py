"""SerialNumberBasedEffectivityConfigSpec——基于序列号的有效性配置规格。"""
from app.services.configuration.spec.effectivity_config_spec import EffectivityConfigSpec
from app.models.product.serial_number_based_effectivity import SerialNumberBasedEffectivity
from app.models.util.alphanumeric_comparator import alphanumeric_compare


class SerialNumberBasedEffectivityConfigSpec(EffectivityConfigSpec):
    """按序列号过滤有效性。使用 AlphanumericComparator 进行字母数字比较。"""

    def __init__(self, number: str, configuration_item=None, configuration=None):
        super().__init__(configuration_item, configuration)
        self.number = number

    def is_effective(self, effectivity) -> bool:
        """检查 SerialNumberBasedEffectivity 的序列号范围。"""
        if not isinstance(effectivity, SerialNumberBasedEffectivity):
            return False

        # CI 不匹配
        if self.configuration_item:
            ci = self.configuration_item
            if (effectivity.configurationitem_id != ci.id or
                effectivity.configurationitem_workspace_id != ci.workspace_id):
                return False

        # number < startNumber → 不在范围内
        start_number = getattr(effectivity, 'start_number', None)
        if start_number and alphanumeric_compare(self.number, start_number) < 0:
            return False

        # number > endNumber → 不在范围内
        end_number = getattr(effectivity, 'end_number', None)
        if end_number and alphanumeric_compare(self.number, end_number) > 0:
            return False

        return True
