from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi import Depends

from app.api import auth, health, orders, optimization, reference_data
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="生鲜冷链物流协同优化系统 API",
        version="0.1.0",
        description="订单、GA-2-opt 路径优化、三维装箱与司机执行接口。",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    protected = [Depends(auth.get_current_user)]
    app.include_router(reference_data.router, prefix="/api", dependencies=protected)
    app.include_router(orders.router, prefix="/api", dependencies=protected)
    app.include_router(optimization.router, prefix="/api", dependencies=protected)
    return app


app = create_app()
