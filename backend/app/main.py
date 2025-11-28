"""
无线大数据分析系统后端主文件
负责初始化 FastAPI 应用、配置中间件、注册路由和静态文件挂载
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .api import api_router
from .models import Base, engine

# 创建数据库表
Base.metadata.create_all(bind=engine)

"""
创建 FastAPI 应用实例
- title: API 文档标题
- version: API 版本号
"""
app = FastAPI(title="无线大数据分析系统API", version="1.0.0")

"""
配置 CORS 中间件
允许前端应用访问后端 API
- allow_origins: 允许访问的源列表，生产环境应设置具体域名
- allow_credentials: 是否允许携带凭证
- allow_methods: 允许的 HTTP 方法
- allow_headers: 允许的 HTTP 头
"""
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

"""
根路径路由
用于检查后端服务是否正常运行
返回：包含欢迎消息的响应
"""
@app.get("/")
async def root():
    return {"message": "无线大数据分析系统后端服务运行中"}

"""
健康检查路由
用于监控系统健康状态
返回：包含健康状态的响应
"""
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

"""
注册 API 路由
将所有 API 路由注册到主应用中
"""
app.include_router(api_router)

"""
挂载静态文件目录
用于前端访问上传的文件资源
- path: 访问路径
- app: 静态文件应用
- name: 应用名称
"""
# 挂载上传目录为静态文件，供前端访问仪表盘背景等资源
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/api/uploads", StaticFiles(directory="uploads"), name="api-uploads")

"""
应用入口
当直接运行该文件时，启动 Uvicorn 服务器
- --port: 服务器端口，默认 8000
"""
if __name__ == "__main__":
    import uvicorn
    import sys
    import argparse
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser()
    # 添加端口参数
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    # 解析命令行参数
    args = parser.parse_args()
    
    # 启动 Uvicorn 服务器
    uvicorn.run(app, host="0.0.0.0", port=args.port)