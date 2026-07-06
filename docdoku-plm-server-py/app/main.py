"""FastAPI 应用入口。"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.routers import auth, parts, part, part_templates, effectivity, part_files, document_files, folders, documents, document, document_baselines, document_templates, products, product_instances, product_files, product_baselines, product_configurations, layers, change_issues, change_requests, change_orders, milestones, roles, users, user_groups, workspace_memberships, accounts, admin, notifications, webhooks, workflow_models, workflow, tasks, workspaces, organizations, languages, timezones, platform, share, attributes, lov, tags, document_template_files, part_template_files
from app.core.exception_handlers import register_exception_handlers
from app.core.security import verify_token
from app.core.database import SessionLocal
from app.models.auth import Account

# 路径前缀与 Payara 完全一致，Backbone 前端无需任何修改
API_PREFIX = "/docdoku-plm-server-rest/api"

app = FastAPI(
    title="DocdokuPLM FastAPI Backend",
    version="0.1.0",
    docs_url=f"{API_PREFIX}/docs",
    openapi_url=f"{API_PREFIX}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["jwt"],  # 前端需要读取响应头中的 jwt
)

class TrailingSlashMiddleware(BaseHTTPMiddleware):
    """去掉请求路径末尾的 /，防止前端带尾斜杠发起 POST/PUT/DELETE 时 405。"""

    async def dispatch(self, request: Request, call_next):
        path = request.scope.get("path", "")
        if len(path) > 1 and path.endswith("/"):
            request.scope["path"] = path.rstrip("/") or "/"
        return await call_next(request)


app.add_middleware(TrailingSlashMiddleware)

register_exception_handlers(app)


class UserLanguageMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request, call_next):
        request.state.user_language = None
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            try:
                payload = verify_token(auth[7:])
                db = SessionLocal()
                try:
                    acct = db.query(Account).filter(
                        Account.login == payload["login"]).first()
                    if acct:
                        request.state.user_language = acct.language
                finally:
                    db.close()
            except Exception:
                pass
        return await call_next(request)


app.add_middleware(UserLanguageMiddleware)

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(parts.router, prefix=API_PREFIX)
app.include_router(part.router)
app.include_router(part_templates.router)
app.include_router(effectivity.router)
app.include_router(part_files.router, prefix=API_PREFIX)
app.include_router(documents.router, prefix=API_PREFIX)
app.include_router(document.router)
app.include_router(document_baselines.router)
app.include_router(document_files.router, prefix=API_PREFIX)
app.include_router(folders.router, prefix=API_PREFIX)
app.include_router(document_templates.router, prefix=API_PREFIX)
app.include_router(products.router)
app.include_router(product_baselines.router)
app.include_router(product_configurations.router)
app.include_router(layers.router)
app.include_router(product_instances.router, prefix=API_PREFIX)
app.include_router(product_files.router, prefix=API_PREFIX)
app.include_router(change_issues.router)
app.include_router(change_requests.router)
app.include_router(change_orders.router)
app.include_router(milestones.router)
app.include_router(roles.router)
app.include_router(users.router)
app.include_router(user_groups.router)
app.include_router(workspace_memberships.router)
app.include_router(accounts.router)
app.include_router(admin.router)
app.include_router(notifications.router)
app.include_router(webhooks.router)
app.include_router(workflow_models.router)
app.include_router(workflow.router)
app.include_router(tasks.router)
app.include_router(workspaces.router)
app.include_router(organizations.router)
app.include_router(languages.router)
app.include_router(timezones.router)
app.include_router(platform.router)
app.include_router(share.router)
app.include_router(attributes.router)
app.include_router(lov.router)
app.include_router(tags.router)
app.include_router(document_template_files.router, prefix=API_PREFIX)
app.include_router(part_template_files.router, prefix=API_PREFIX)


@app.get(f"{API_PREFIX}/health")
def health_check():
    """健康检查端点，用于验证 FastAPI 是否正常运行。"""
    return {"status": "ok", "backend": "fastapi"}