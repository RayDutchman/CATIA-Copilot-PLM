"""FastAPI 应用入口。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, parts
from app.core.exception_handlers import register_exception_handlers

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

register_exception_handlers(app)

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(parts.router, prefix=API_PREFIX)


@app.get(f"{API_PREFIX}/health")
def health_check():
    """健康检查端点，用于验证 FastAPI 是否正常运行。"""
    return {"status": "ok", "backend": "fastapi"}