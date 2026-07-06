"""LotBasedEffectivityConfigSpec——基于批次的有效性配置规格。"""
from app.services.configuration.spec.effectivity_config_spec import EffectivityConfigSpec
from app.models.product.lot_based_effectivity import LotBasedEffectivity
from app.models.util.alphanumeric_comparator import alphanumeric_compare


class LotBasedEffectivityConfigSpec(EffectivityConfigSpec):
    """按批次号过滤有效性。使用 AlphanumericComparator 进行字母数字比较。"""

    def __init__(self, lot_id: str, configuration_item=None, configuration=None):
        super().__init__(configuration_item, configuration)
        self.lot_id = lot_id

    def is_effective(self, effectivity) -> bool:
        """检查 LotBasedEffectivity 的批次号范围。"""
        if not isinstance(effectivity, LotBasedEffectivity):
            return False

        # CI 不匹配
        if self.configuration_item:
            ci = self.configuration_item
            if (effectivity.configurationitem_id != ci.id or
                effectivity.configurationitem_workspace_id != ci.workspace_id):
                return False

        # lotId < startLotId → 不在范围内
        start_lot = getattr(effectivity, 'start_lot', None)
        if start_lot and alphanumeric_compare(self.lot_id, start_lot) < 0:
            return False

        # lotId > endLotId → 不在范围内
        end_lot = getattr(effectivity, 'end_lot', None)
        if end_lot and alphanumeric_compare(self.lot_id, end_lot) > 0:
            return False

        return True
