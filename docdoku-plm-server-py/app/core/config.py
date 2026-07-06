"""应用配置，从环境变量读取。"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 数据库（连接现有 docdokuplm）
    DATABASE_SERVER_NAME: str = "db"
    DATABASE_NAME: str = "docdokuplm"
    DATABASE_USER: str = "changeit"
    DATABASE_PWD: str = "changeit"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PWD}"
            f"@{self.DATABASE_SERVER_NAME}/{self.DATABASE_NAME}"
        )

    # JWT（与 Payara back.env 的 JWT_KEY 保持一致）
    JWT_KEY: str = ""
    JWT_ENABLED: bool = True
    JWT_EXPIRE_SECONDS: int = 10800      # 3 小时
    JWT_REFRESH_BEFORE_SECONDS: int = 180  # 到期前 3 分钟刷新

    # 文件存储
    VAULT_PATH: str = "/var/lib/docdoku/vault"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_CONVERSION_TOPIC: str = "CONVERT"

    # ES 搜索
    ES_URL: str = "http://es:9200"

    # 转换临时目录（与 conversion 服务共享 conversion-volume）
    CONVERSIONS_PATH: str = "/var/lib/docdoku/conversions"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()