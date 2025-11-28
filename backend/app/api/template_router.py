"""
模板管理API路由
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel, Field
import json
from app.models import get_db, Template

# 创建路由实例
router = APIRouter(
    prefix="/templates",
    tags=["templates"],
    responses={404: {"description": "Not found"}},
)


# Pydantic模型定义
class TemplateCreate(BaseModel):
    """创建模板请求模型"""
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., pattern="^(anomaly|cluster|predict)$")
    config: Dict[str, Any]
    results: Dict[str, Any]


class TemplateUpdate(BaseModel):
    """更新模板请求模型"""
    name: str = Field(None, min_length=1, max_length=255)
    config: Dict[str, Any] = None
    results: Dict[str, Any] = None


class TemplateResponse(BaseModel):
    """模板响应模型"""
    id: int
    name: str
    type: str
    config: Dict[str, Any]
    results: Dict[str, Any]
    created_at: str

    class Config:
        from_attributes = True


@router.post("/", response_model=TemplateResponse)
async def create_template(
    template: TemplateCreate,
    db: Session = Depends(get_db)
):
    """
    创建新模板
    """
    import time
    import json
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError
    
    start_time = time.time()
    
    print(f"开始创建模板: {template.name}, 类型: {template.type}")
    
    # 保留完整数据，不进行截断
    optimized_results = template.results.copy()
    
    # 只移除allScatterData（所有特征的散点图数据），保留当前特征的scatterData
    if "allScatterData" in optimized_results:
        del optimized_results["allScatterData"]
    
    # 将配置和结果转换为JSON字符串
    config_json = json.dumps(template.config, ensure_ascii=False, separators=(',', ':'))
    results_json = json.dumps(optimized_results, ensure_ascii=False, separators=(',', ':'))
    
    print(f"模板数据大小: 配置 {len(config_json)} 字节, 结果 {len(results_json)} 字节")
    
    # 创建模板实例
    db_template = Template(
        name=template.name,
        type=template.type,
        config=config_json,
        results=results_json
    )
    
    # 保存到数据库，增加重试机制和超时处理
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # 设置更长的超时时间
            db.execute(text("SET SESSION wait_timeout = 600;"))  # 10分钟
            db.execute(text("SET SESSION net_read_timeout = 600;"))  # 10分钟
            db.execute(text("SET SESSION net_write_timeout = 600;"))  # 10分钟
            
            # 移除max_allowed_packet设置，因为它是只读的，需要通过全局设置或配置文件修改
            
            # 减少重复日志输出
            if retry_count == 0:
                print(f"开始保存模板到数据库")
            start_save = time.time()
            
            db.add(db_template)
            db.commit()
            db.refresh(db_template)
            
            end_save = time.time()
            print(f"模板保存成功，耗时: {end_save - start_save:.2f} 秒")
            break
        except OperationalError as e:
            retry_count += 1
            # 只输出关键错误信息，避免重复
            if "max_allowed_packet" in str(e):
                print(f"模板保存失败，正在重试 ({retry_count}/{max_retries}): 数据包大小限制问题")
            else:
                print(f"模板保存失败，正在重试 ({retry_count}/{max_retries}): 数据库连接问题")
            db.rollback()
            if retry_count >= max_retries:
                print("模板保存重试次数耗尽，保存失败")
                raise
            # 等待一段时间后重试，每次重试等待时间递增
            wait_time = 2 * retry_count
            print(f"等待 {wait_time} 秒后重试")
            time.sleep(wait_time)
        except Exception as e:
            print(f"模板保存失败: {type(e).__name__}")
            db.rollback()
            raise
    
    end_time = time.time()
    print(f"模板创建完成，耗时: {end_time - start_time:.2f} 秒")
    
    # 转换为响应模型
    return {
        "id": db_template.id,
        "name": db_template.name,
        "type": db_template.type,
        "config": json.loads(db_template.config),
        "results": json.loads(db_template.results),
        "created_at": db_template.created_at.isoformat()
    }


@router.get("/", response_model=List[TemplateResponse])
async def get_templates(
    template_type: str = None,
    db: Session = Depends(get_db)
):
    """
    获取模板列表，可按类型过滤
    """
    query = db.query(Template)
    
    # 如果提供了类型，过滤模板
    if template_type:
        query = query.filter(Template.type == template_type)
    
    # 按创建时间倒序排序
    templates = query.order_by(Template.created_at.desc()).all()
    
    # 转换为响应模型列表
    return [{
        "id": template.id,
        "name": template.name,
        "type": template.type,
        "config": json.loads(template.config),
        "results": json.loads(template.results),
        "created_at": template.created_at.isoformat()
    } for template in templates]


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """
    获取单个模板详情
    """
    template = db.query(Template).filter(Template.id == template_id).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # 转换为响应模型
    return {
        "id": template.id,
        "name": template.name,
        "type": template.type,
        "config": json.loads(template.config),
        "results": json.loads(template.results),
        "created_at": template.created_at.isoformat()
    }


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    template_update: TemplateUpdate,
    db: Session = Depends(get_db)
):
    """
    更新模板
    """
    template = db.query(Template).filter(Template.id == template_id).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # 更新字段
    if template_update.name:
        template.name = template_update.name
    
    if template_update.config:
        template.config = json.dumps(template_update.config, ensure_ascii=False)
    
    if template_update.results:
        template.results = json.dumps(template_update.results, ensure_ascii=False)
    
    # 保存到数据库
    db.commit()
    db.refresh(template)
    
    # 转换为响应模型
    return {
        "id": template.id,
        "name": template.name,
        "type": template.type,
        "config": json.loads(template.config),
        "results": json.loads(template.results),
        "created_at": template.created_at.isoformat()
    }


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """
    删除模板
    """
    template = db.query(Template).filter(Template.id == template_id).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # 删除模板
    db.delete(template)
    db.commit()
    
    return {"message": "Template deleted successfully"}


@router.get("/search/{template_type}", response_model=List[TemplateResponse])
async def search_templates(
    template_type: str,
    keyword: str = None,
    db: Session = Depends(get_db)
):
    """
    按类型和关键词搜索模板
    """
    query = db.query(Template).filter(Template.type == template_type)
    
    # 如果提供了关键词，按名称搜索
    if keyword:
        query = query.filter(Template.name.ilike(f"%{keyword}%"))
    
    # 按创建时间倒序排序
    templates = query.order_by(Template.created_at.desc()).all()
    
    # 转换为响应模型列表
    return [{
        "id": template.id,
        "name": template.name,
        "type": template.type,
        "config": json.loads(template.config),
        "results": json.loads(template.results),
        "created_at": template.created_at.isoformat()
    } for template in templates]
