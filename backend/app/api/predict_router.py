from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict

from ..services.prediction_service import prediction_service


router = APIRouter()


class ArimaRequest(BaseModel):
    filename: str = Field(..., description="位于 uploads 目录下的 CSV 文件名")
    area_column: str = Field(..., description="要预测的地区列名（CSV 第二列及之后的一列）")
    stl_reg_params: dict | None = Field(
        default=None,
        description="STL + 线性回归模型的参数配置，如 {period:int, degree:int, robust:bool}",
    )


class BatchPredictRequest(BaseModel):
    # 关闭受保护前缀 "model_"，避免字段名 model_params 触发 Pydantic 命名警告
    model_config = ConfigDict(protected_namespaces=())

    filename: str = Field(..., description="位于 uploads 目录下的 CSV 文件名")
    area_columns: list[str] = Field(..., description="要预测的地区列名列表")
    models: list[str] = Field(..., description="要预测的模型列表，支持 ['stl_reg', 'sarima', 'xgboost', 'xgb_rf_residual', 'lstm']")
    model_params: dict | None = Field(
        default=None,
        description="各模型的参数配置，如 { 'stl_reg': { period:int, degree:int }, 'xgboost': { n_estimators:int, max_depth:int } }",
    )


@router.post("/stl-reg")
async def arima_predict(req: ArimaRequest):
    """基于 STL 分解 + 线性回归的单地区时间序列预测（3/4 训练 + 1/4 测试 + 1/8 未来预测）"""
    try:
        result = prediction_service.sarima_timeseries_prediction(
            filename=req.filename,
            area_column=req.area_column,
            stl_reg_params=req.stl_reg_params or {},
        )
        return result
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/batch-predict")
async def batch_predict(req: BatchPredictRequest):
    """多地区多模型批量预测 - 支持 STL+线性回归、SARIMA、XGBoost、随机森林、LSTM模型"""
    try:
        result = prediction_service.batch_predict_by_areas(
            filename=req.filename,
            area_columns=req.area_columns,
            models=req.models,
            model_params=req.model_params or {},
        )
        return result
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e
