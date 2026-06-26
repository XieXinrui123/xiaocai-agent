"""
资产配置 Agent 后端主入口
FastAPI 框架
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.core.config import settings
from app.routers import chat, plan


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    description="智能资产配置顾问 Agent",
    version="0.1.0",
    debug=settings.DEBUG,
)

# 允许前端跨域访问（开发阶段）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境要改成具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router)
app.include_router(plan.router)


@app.get("/")
async def root():
    """根路径 - 服务状态检查"""
    return {
        "status": "running",
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "message": "资产配置 Agent 后端服务已启动"
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy"}


# 启动入口
if __name__ == "__main__":
    print(f"🚀 启动 {settings.APP_NAME}...")
    print(f"📡 访问地址: http://{settings.HOST}:{settings.PORT}")
    print(f"📚 API 文档: http://{settings.HOST}:{settings.PORT}/docs")
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
