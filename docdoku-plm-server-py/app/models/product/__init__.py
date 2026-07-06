"""ORM: configurationitem + 配置基线/实例。Layer/Marker 已移至 models.product.*。"""
# 从新位置导入
from app.models.product.configuration_item import ConfigurationItem  # noqa: F401
from app.models.product.layer import Layer  # noqa: F401
from app.models.product.marker import Marker  # noqa: F401

# 向后兼容：从 models.configuration 重新导出
from app.models.configuration.product_baseline import ProductBaseline  # noqa: E402, F401
from app.models.configuration.product_configuration import ProductConfiguration  # noqa: E402, F401
from app.models.configuration.product_instance_master import ProductInstanceMaster  # noqa: E402, F401
from app.models.configuration.product_instance_iteration import ProductInstanceIteration  # noqa: E402, F401
