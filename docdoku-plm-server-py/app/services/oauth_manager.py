"""OAuth 提供者管理——对标 Payara OAuthManagerBean。

管理 OAuth 第三方登录提供者。
"""
from sqlalchemy.orm import Session
from sqlalchemy import text


class OAuthService:
    """OAuth 提供者管理服务。"""

    def get_providers(self, db: Session) -> list:
        rows = db.execute(text(
            "SELECT * FROM oauthprovider ORDER BY id"
        )).fetchall()
        return [dict(r._mapping) for r in rows]

    def get_provider(self, db: Session, provider_id: int) -> dict:
        row = db.execute(text(
            "SELECT * FROM oauthprovider WHERE id = :id"
        ), {"id": provider_id}).first()
        if not row:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("OAuthProviderNotFoundException", str(provider_id))
        return dict(row._mapping)

    def create_provider(self, db: Session, name: str, enabled: bool,
                         authority: str, issuer: str, client_id: str,
                         jws_algorithm: str, jwk_set_url: str, redirect_uri: str,
                         secret: str, scope: str, response_type: str,
                         authorization_endpoint: str) -> dict:
        result = db.execute(text(
            "INSERT INTO oauthprovider (name, enabled, authority, issuer, "
            "clientid, jwsalgorithm, jwkseturl, redirecturi, secret, scope, "
            "responsetype, authorizationendpoint) "
            "VALUES (:n, :e, :a, :i, :ci, :ja, :ju, :ru, :s, :sc, :rt, :ae) RETURNING id"
        ), {"n": name, "e": enabled, "a": authority, "i": issuer,
            "ci": client_id, "ja": jws_algorithm, "ju": jwk_set_url,
            "ru": redirect_uri, "s": secret, "sc": scope, "rt": response_type,
            "ae": authorization_endpoint})
        pid = result.fetchone()[0]
        db.commit()
        return {"id": pid, "name": name, "enabled": enabled}

    def update_provider(self, db: Session, provider_id: int, name: str,
                         enabled: bool, **kwargs) -> dict:
        db.execute(text(
            "UPDATE oauthprovider SET name = :n, enabled = :e WHERE id = :id"
        ), {"n": name, "e": enabled, "id": provider_id})
        db.commit()
        return self.get_provider(db, provider_id)

    def delete_provider(self, db: Session, provider_id: int) -> None:
        db.execute(text("DELETE FROM oauthprovider WHERE id = :id"), {"id": provider_id})
        db.commit()

    def is_provided_account(self, db: Session, login: str) -> bool:
        row = db.execute(text(
            "SELECT 1 FROM providedaccount WHERE login = :l"
        ), {"l": login}).first()
        return row is not None

    def get_provider_id(self, db: Session, login: str) -> int | None:
        row = db.execute(text(
            "SELECT provider_id FROM providedaccount WHERE login = :l"
        ), {"l": login}).first()
        return row[0] if row else None


oauth_service = OAuthService()
