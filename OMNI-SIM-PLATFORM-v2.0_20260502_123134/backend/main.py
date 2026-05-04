from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from contextlib import asynccontextmanager
import asyncio
import logging
import os
from apps.core import config, database, models
from apps.api import router
from apps.api.routes.attempts import router as attempts_router
from apps.api.routes.profiles import router as profiles_router
from apps.api.routes.slo import router as slo_router
from apps.api.routes.notifications import router as notifications_router
from apps.api.routes.leaderboard import router as leaderboard_router
from apps.api.routes.analytics import router as analytics_router
from apps.api.routes.websocket import router as websocket_router
from apps.api.routes.content import router as content_router
from apps.api.routes.memory import router as memory_router
from apps.api.routes.level_engine import router as level_engine_router
from apps.api.routes.infrastructure import router as infrastructure_router
from apps.api.routes.content_import import router as import_router
from apps.api.routes.ai import router as ai_router
from apps.api.routes.vector import router as vector_router
from apps.api.routes.admin import router as admin_router
from apps.api.routes.tenants import router as tenants_router
from apps.api.routes.oauth import router as oauth_router
from apps.api.middleware.tenant_middleware import TenantMiddleware
from apps.api.middleware.rate_limit import AuthRateLimitMiddleware
from apps.core.learning_engine import router as learning_router
from apps.core.adversarial_testing import router as security_router
from apps.api.routes.ai_config import router as ai_config_router
from apps.api.routes.migration import router as migration_router
from apps.api.routes.scenarios import router as scenarios_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 生产环境必须显式覆盖 SECRET_KEY，避免使用默认开发密钥
if config.settings.APP_ENV == "production" and config.settings.SECRET_KEY == "dev-secret-key-change-in-production":
    raise RuntimeError(
        "SECRET_KEY 仍为默认开发值，请在生产环境的 .env 中显式设置一个高熵密钥后再启动。"
    )

# 仅在显式启用相关功能时才导入对应可选依赖（boto3/aiokafka/opentelemetry 等）
upload_router = None
if config.settings.S3_ENABLED:
    try:
        from apps.api.routes.upload import router as upload_router  # type: ignore
    except Exception as e:  # pragma: no cover
        logger.warning(f"S3 已启用但 upload 路由加载失败: {e}")

bluegreen_router = None
try:
    from apps.core.bluegreen import router as bluegreen_router  # type: ignore
except Exception as e:  # pragma: no cover
    logger.warning(f"bluegreen 路由不可用: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Starting application...")

    # 避免 import main 时副作用建表；生产默认禁用自动建表。
    default_auto_create = "true" if config.settings.APP_ENV != "production" else "false"
    if os.getenv("AUTO_CREATE_SCHEMA", default_auto_create).lower() == "true":
        models.Base.metadata.create_all(bind=database.engine)

    if config.settings.OTEL_ENABLED:
        try:
            from apps.core.otel_tracer import init_otel, instrument_app
            init_otel()
            instrument_app(app)
        except Exception as e:
            logger.warning(f"OpenTelemetry 初始化失败: {e}")

    if config.settings.KAFKA_ENABLED:
        try:
            from apps.core.kafka_producer import kafka_producer, KafkaTopics
            from apps.core.kafka_consumer import get_consumer, register_default_handlers

            await kafka_producer.start()
            logger.info("Kafka producer started")

            consumer = get_consumer([
                KafkaTopics.AUDIT_LOG,
                KafkaTopics.EMAIL_NOTIFICATION,
                KafkaTopics.USER_REGISTERED,
                KafkaTopics.LEVEL_COMPLETED,
                KafkaTopics.ACHIEVEMENT_UNLOCKED,
            ])
            register_default_handlers(consumer)
            await consumer.start()
            asyncio.create_task(consumer.consume())
            logger.info("Kafka consumer started")
        except Exception as e:
            logger.warning(f"Kafka 启动失败（已跳过，不影响主流程）: {e}")

    yield

    logger.info("Shutting down application...")

    if config.settings.KAFKA_ENABLED:
        try:
            from apps.core.kafka_producer import kafka_producer
            from apps.core.kafka_consumer import consumer_instances

            await kafka_producer.stop()
            for consumer in list(consumer_instances.values()):
                try:
                    await consumer.stop()
                except Exception as e:
                    logger.warning(f"Error stopping Kafka consumer: {e}")
        except Exception as e:
            logger.warning(f"Kafka shutdown error: {e}")


app = FastAPI(
    title=config.settings.APP_NAME,
    version="2.0.0",
    description="游戏化通用培训平台后端 API",
    lifespan=lifespan,
)

# CORS：禁止 "*" + credentials 组合，改为白名单
_default_origins = "http://localhost:3000,http://localhost:3002,http://127.0.0.1:3000,http://127.0.0.1:3002"
_allowed_origins = [
    o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", _default_origins).split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["X-Request-ID"],
    max_age=600,
)

app.add_middleware(TenantMiddleware)
app.add_middleware(AuthRateLimitMiddleware)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """为所有响应添加安全头。"""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        # 允许同源 iframe（平台页面 ↔ 内嵌 FPS 游戏均在同一后端下）
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # HSTS 仅在 HTTPS 场景下有意义，通过环境变量控制
        if os.getenv("HTTPS_ENABLED", "false").lower() == "true":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


app.add_middleware(SecurityHeadersMiddleware)

app.include_router(router)
app.include_router(attempts_router)
app.include_router(profiles_router)
app.include_router(slo_router)
app.include_router(notifications_router)
app.include_router(leaderboard_router)
app.include_router(analytics_router)
app.include_router(websocket_router)
app.include_router(content_router)
app.include_router(memory_router)
app.include_router(level_engine_router)
app.include_router(infrastructure_router)
app.include_router(import_router)
app.include_router(ai_router)
app.include_router(vector_router)
app.include_router(admin_router)
app.include_router(tenants_router)
if upload_router is not None:
    app.include_router(upload_router)
app.include_router(oauth_router)
app.include_router(learning_router)
app.include_router(security_router)
app.include_router(ai_config_router)
if bluegreen_router is not None:
    app.include_router(bluegreen_router)

# V2V FPS 迁移战役：业务路由 + 静态游戏包
app.include_router(migration_router)

# 场景包 DSL v1（通用平台内容层）
app.include_router(scenarios_router)
_GAME_DIR = os.path.join(os.path.dirname(__file__), "static", "game")
if os.path.isdir(_GAME_DIR):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse as _FR_GAME

    # 显式优先级：/game/{level_id}（数字）→ 平台前端 SPA（关卡页面）。
    # 必须在 StaticFiles mount 之前注册，否则会被 mount 抢先匹配。
    @app.get("/game/{level_id:int}", include_in_schema=False)
    async def _level_page(level_id: int):
        _idx = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "frontend", "apps", "web", "dist", "index.html"))
        if os.path.isfile(_idx):
            return _FR_GAME(_idx)
        from fastapi import HTTPException as _HE
        raise _HE(status_code=404, detail="frontend not built")

    app.mount("/game", StaticFiles(directory=_GAME_DIR, html=True), name="game")
    logger.info("Mounted V2V FPS game at /game from %s", _GAME_DIR)
else:
    logger.warning("V2V FPS game dir missing: %s", _GAME_DIR)

# 场景内容工作台（零构建静态页，供非工程师创建/编辑场景包 DSL）
_WORKBENCH_DIR = os.path.join(os.path.dirname(__file__), "static", "workbench")
if os.path.isdir(_WORKBENCH_DIR):
    from fastapi.staticfiles import StaticFiles as _SF_WB
    app.mount("/workbench", _SF_WB(directory=_WORKBENCH_DIR, html=True), name="workbench")
    logger.info("Mounted scenario workbench at /workbench from %s", _WORKBENCH_DIR)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": config.settings.APP_NAME}


@app.get("/ready")
async def readiness_check():
    """K8s readiness 探针：实际访问数据库以确认就绪。"""
    try:
        with database.engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        return {"status": "ready"}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=f"DB not ready: {e}")


# 平台前端 SPA（同源伊服，免跨域、JWT 共享）。
# 位于所有 API 路由之后，使用 SPA fallback 让 react-router 接管未知路径。
_FRONTEND_DIST = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "frontend", "apps", "web", "dist",
))
if os.path.isdir(_FRONTEND_DIST):
    from fastapi.staticfiles import StaticFiles as _SF
    from fastapi.responses import FileResponse as _FR

    # 实质性静态资源目录（/assets/* 等）
    _ASSETS_DIR = os.path.join(_FRONTEND_DIST, "assets")
    if os.path.isdir(_ASSETS_DIR):
        app.mount("/assets", _SF(directory=_ASSETS_DIR), name="frontend-assets")

    _INDEX_HTML = os.path.join(_FRONTEND_DIST, "index.html")

    @app.get("/", include_in_schema=False)
    async def _spa_root():
        return _FR(_INDEX_HTML)

    # SPA fallback：任意未被 API/静态接管的路径返回 index.html，
    # 为 react-router 的 client-side routing（/login、/game/:levelId 等）服务。
    # 注意：/game/:levelId 是前端路由，需要走 SPA；
    # 真正的 FPS 游戏静态资源位于 /game/index.html、/game/assets/...、/game/*.glb 等。
    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_fallback(full_path: str):
        from fastapi import HTTPException as _HE
        # 严格保护的 API/文档路径前缀
        api_prefixes = ("api/", "auth/", "admin/", "oauth/", "tenants/",
                        "vector/", "analytics/", "leaderboard/",
                        "docs", "redoc", "openapi.json", "assets/",
                        "health", "ready")
        if any(full_path.startswith(p) for p in api_prefixes):
            raise _HE(status_code=404, detail="not found")

        # 游戏静态资源：/game/index.html, /game/assets/..., /game/*.glb 等。
        # 这些路径应该由之前的 StaticFiles 挂载处理；没拍到就说明是 404，
        # 但 /game/{levelId}（数字/无扩展名）是前端关卡页面，还走 SPA。
        if full_path.startswith("game/"):
            sub = full_path[len("game/"):]
            # 包含“.”表示是资源文件；以 assets/ 开头的是资源子路径。
            if ("." in sub.rsplit("/", 1)[-1]) or sub.startswith("assets/"):
                raise _HE(status_code=404, detail="not found")
            # 其余 /game/<levelId> 之类：走 SPA

        # 静态根目录下的其他文件（favicon 等）
        candidate = os.path.join(_FRONTEND_DIST, full_path)
        if os.path.isfile(candidate):
            return _FR(candidate)
        return _FR(_INDEX_HTML)

    logger.info("Mounted platform SPA at / from %s", _FRONTEND_DIST)
else:
    logger.warning("Frontend dist not built; run `npm run build` in frontend/apps/web. (looked for %s)", _FRONTEND_DIST)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.settings.APP_PORT)
