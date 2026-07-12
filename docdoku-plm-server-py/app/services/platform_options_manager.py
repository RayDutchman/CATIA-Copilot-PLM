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

    def upsert_platform_options(self, db: Session,
                                 workspace_creation_strategy: int,
                                 registration_strategy: int) -> dict:
        """INSERT 或 UPDATE platformoptions 行，返回最新的选项 dict。"""
        existing = db.execute(text(
            "SELECT id FROM platformoptions LIMIT 1"
        )).first()
        if existing:
            db.execute(text(
                "UPDATE platformoptions SET "
                "workspacecreationstrategy = :wcs, "
                "registrationstrategy = :rs"
            ), {"wcs": workspace_creation_strategy, "rs": registration_strategy})
        else:
            db.execute(text(
                "INSERT INTO platformoptions "
                "(id, workspacecreationstrategy, registrationstrategy) "
                "VALUES (1, :wcs, :rs)"
            ), {"wcs": workspace_creation_strategy, "rs": registration_strategy})
        db.commit()
        return self.get_platform_options(db)


platform_options_service = PlatformOptionsService()
