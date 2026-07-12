"""FastAPI 应用入口。"""
from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from urllib.parse import unquote
from app.routers import auth, parts, part, part_templates, effectivity, part_files, document_files, folders, documents, document, document_baselines, document_templates, products, product_instances, product_files, product_baselines, product_configurations, layers, change_issues, change_requests, change_orders, milestones, roles, users, user_groups, workspace_memberships, accounts, admin, notifications, webhooks, workflow_models, workflow, tasks, workspaces, organizations, languages, timezones, platform, share, attributes, lov, tags, document_template_files, part_template_files
from app.routers.export import document_baseline_export, instance_collection, virtual_instance_collection
from app.routers import dev as dev_router
from app.core.exception_handlers import register_exception_handlers
from app.core.security import verify_token
from app.core.database import SessionLocal
from app.models.auth import Account
from app.core.error_collector import record as _record_error

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

# Starlette 0.x 兼容: 路径参数不自动 URL 解码，手动处理
class URLDecodeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.scope.get("path", "")
        if "%" in path:
            request.scope["path"] = unquote(path)
        return await call_next(request)

app.add_middleware(URLDecodeMiddleware)

register_exception_handlers(app)


class UserLanguageMiddleware(BaseHTTPMiddleware):
    """从 JWT 解析用户语言偏好，设置到 request.state.user_language。
    
    已知差异：每请求额外创建独立 SessionLocal()（与 get_db 分离），
    高并发下每请求耗 2 连接。暂不改动，避免破坏中间件请求生命周期。
    """

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


class ErrorCollectorMiddleware(BaseHTTPMiddleware):
    """记录所有 4xx/5xx 请求到内存，供 /dev/errors 查询。"""

    # 不记录这些路径（静态资源、健康检查）
    _SKIP_PREFIXES = ("/dev/", "/docs", "/openapi", "/health")

    async def dispatch(self, request: Request, call_next):
        # 跳过不需要记录的路径
        path = request.url.path
        if any(path.startswith(p) for p in self._SKIP_PREFIXES):
            return await call_next(request)

        # 读取请求体（需要缓冲）
        req_body = None
        try:
            body_bytes = await request.body()
            if body_bytes:
                req_body = body_bytes.decode("utf-8", errors="replace")
        except Exception:
            pass

        response = await call_next(request)

        # 只记录 4xx/5xx
        if response.status_code >= 400:
            # 读取响应体
            res_body = None
            try:
                from starlette.responses import Response as StarResponse
                res_bytes = b""
                async for chunk in response.body_iterator:
                    res_bytes += chunk
                res_body = res_bytes.decode("utf-8", errors="replace")
                # 重建响应（body_iterator 只能消费一次）
                response = StarResponse(
                    content=res_bytes,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )
            except Exception:
                pass

            # 从 JWT 解析用户名
            user = None
            try:
                auth_header = request.headers.get("authorization", "")
                if auth_header.startswith("Bearer "):
                    payload = verify_token(auth_header[7:])
                    user = payload.get("login", "")
            except Exception:
                pass

            _record_error(
                method=request.method,
                url=str(request.url),
                status=response.status_code,
                req_body=req_body,
                res_body=res_body,
                user=user,
            )

        return response


app.add_middleware(ErrorCollectorMiddleware)

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
app.include_router(document_baseline_export.router)
app.include_router(instance_collection.router)
app.include_router(virtual_instance_collection.router)
app.include_router(dev_router.router)


@app.websocket("/docdoku-plm-server-rest/ws")
async def ws_endpoint(websocket: WebSocket):
    """WebSocket 端点（对标 WebSocketApplication @ServerEndpoint("/ws")）。

    前端/nginx 实际访问路径为 /docdoku-plm-server-rest/ws（不带 /api 前缀），
    故此处注册完整路径，否则 Starlette 无匹配路由 → 握手被关闭（表现为 403）。
    """
    from app.ws.endpoint import handle_websocket
    await handle_websocket(websocket)


@app.get(f"{API_PREFIX}/health")
def health_check():
    """健康检查端点，用于验证 FastAPI 是否正常运行。"""
    return {"status": "ok", "backend": "fastapi"}