"""平台选项管理——对标 Payara PlatformOptionsManagerBean。"""
from sqlalchemy.orm import Session
from sqlalchemy import text


class PlatformOptionsService:
    """平台选项管理服务。"""

    def get_platform_options(self, db: Session) -> dict:
        row = db.execute(text(
            "SELECT * FROM platformoptions LIMIT 1"
        )).first()
        if row:
            return dict(row._mapping)
        return {"registrationStrategy": "ADMIN_VALIDATION",
                "workspaceCreationStrategy": "ADMIN_VALIDATION"}

    def get_workspace_creation_strategy(self, db: Session) -> str:
        opts = self.get_platform_options(db)
        return opts.get("workspaceCreationStrategy", "ADMIN_VALIDATION")

    def get_registration_strategy(self, db: Session) -> str:
        opts = self.get_platform_options(db)
        return opts.get("registrationStrategy", "ADMIN_VALIDATION")

    def set_workspace_creation_strategy(self, db: Session, strategy: str) -> None:
        db.execute(text(
            "UPDATE platformoptions SET workspacecreationstrategy = :s"
        ), {"s": strategy})
        db.commit()

    def set_registration_strategy(self, db: Session, strategy: str) -> None:
        db.execute(text(
            "UPDATE platformoptions SET registrationstrategy = :s"
        ), {"s": strategy})
        db.commit()


platform_options_service = PlatformOptionsService()
