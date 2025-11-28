from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List, Union, Optional
import logging
from ..services.anomaly_service import anomaly_service
from ..services.cluster_service import cluster_service
from ..services.prediction_service import prediction_service
from ..services.task_manager import task_manager, TaskStatus

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/anomaly", summary="异常检测")
async def detect_anomalies(
    file_id: str = Body(..., description="文件ID"),
    method: str = Body("isolation_forest", description="检测方法"),
    contamination: float = Body(0.1, description="预期异常比例"),
    features: List[str] = Body(None, description="要检测的特征列表"),
    y_axis_feature: Optional[str] = Body(None, description="用于散点图Y轴展示的特征列"),
    n_estimators: int = Body(100, description="Isolation Forest: 树的数量"),
    max_samples: Union[str, int] = Body('auto', description="Isolation Forest: 每棵树的样本数"),
    n_neighbors: int = Body(20, description="LOF: 邻居数量"),
    algorithm: str = Body('auto', description="LOF: 算法类型"),
    kernel: str = Body('rbf', description="One-Class SVM: 核函数"),
    nu: float = Body(0.5, description="One-Class SVM: 异常比例上界")
):
    """
    对数据进行异常检测

    支持的方法：
    - isolation_forest: Isolation Forest算法
    """
    try:
        logger.info(f"收到异常检测请求，文件ID: {file_id}, 方法: {method}")

        # 仅支持 Isolation Forest
        if method != 'isolation_forest':
            raise ValueError(f"当前仅支持 isolation_forest 方法，收到: {method}")

        result = anomaly_service.detect_isolation_forest(
            file_id=file_id,
            features=features if features is not None else [],
            contamination=contamination,
            n_estimators=n_estimators,
            max_samples=str(max_samples) if isinstance(max_samples, int) else max_samples,
            y_axis_feature=y_axis_feature,
        )

        logger.info(f"异常检测完成，发现 {result['anomaly_count']} 个异常样本")

        return {
            "success": True,
            "message": "异常检测完成",
            "data": result
        }
    except FileNotFoundError as e:
        logger.error(f"文件未找到: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=f"文件未找到: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"参数错误: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"参数错误: {str(e)}"
        )
    except Exception as e:
        logger.error(f"异常检测失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"异常检测失败: {str(e)}"
        )


@router.post("/anomaly/task", summary="提交异常检测任务（后台运行）")
async def submit_anomaly_task(
    file_id: str = Body(..., description="文件ID"),
    method: str = Body("isolation_forest", description="检测方法"),
    contamination: float = Body(0.1, description="预期异常比例"),
    features: List[str] = Body(None, description="要检测的特征列表"),
    y_axis_feature: Optional[str] = Body(None, description="用于散点图Y轴展示的特征列"),
    n_estimators: int = Body(100, description="Isolation Forest: 树的数量"),
    max_samples: Union[str, int] = Body('auto', description="Isolation Forest: 每棵树的样本数"),
):
    """提交一个长耗时异常检测任务，立即返回 task_id 供前端轮询。"""

    try:
        logger.info(f"收到异常检测任务提交，请求文件ID: {file_id}, 方法: {method}")

        if method != 'isolation_forest':
            raise ValueError(f"当前仅支持 isolation_forest 方法，收到: {method}")

        params: Dict[str, Any] = {
            "file_id": file_id,
            "method": method,
            "contamination": float(contamination),
            "features": features,
            "y_axis_feature": y_axis_feature,
            "n_estimators": int(n_estimators),
            "max_samples": max_samples,
        }

        task_id = task_manager.create_task(params)

        # 后台线程中运行实际检测逻辑
        def worker(task_id: str, p: Dict[str, Any], tm):
            features_param = p.get("features")
            if features_param is None:
                features_param = []
            
            result = anomaly_service.detect_isolation_forest(
                file_id=p["file_id"],
                features=features_param,
                contamination=p.get("contamination", 0.1),
                n_estimators=p.get("n_estimators", 100),
                max_samples=p.get("max_samples", 'auto'),
                y_axis_feature=p.get("y_axis_feature"),
                task_id=task_id,
            )
            return result

        task_manager.start_task(task_id, worker)

        return {
            "success": True,
            "message": "异常检测任务已提交",
            "data": {
                "task_id": task_id,
                "status": TaskStatus.PENDING,
            },
        }
    except FileNotFoundError as e:
        logger.error(f"文件未找到: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=f"文件未找到: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"参数错误: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"参数错误: {str(e)}"
        )
    except Exception as e:
        logger.error(f"提交异常检测任务失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"提交异常检测任务失败: {str(e)}"
        )


@router.get("/anomaly/task/{task_id}", summary="查询异常检测任务状态")
async def get_anomaly_task(task_id: str):
    """查询后台运行的异常检测任务状态与结果。"""

    task = task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    status = task.get("status", TaskStatus.PENDING)
    response: Dict[str, Any] = {
        "success": True,
        "data": {
            "task_id": task_id,
            "status": status,
            "progress": float(task.get("progress", 0.0)),
        },
    }

    if status == TaskStatus.FINISHED:
        response["data"]["result"] = task.get("result")
    elif status == TaskStatus.FAILED:
        response["data"]["error"] = task.get("error")

    return response



@router.post("/scatter/regenerate", summary="重建散点图")
async def regenerate_scatter(
    base_file_id: str = Body(..., description="原始文件ID"),
    corrected_file_path: str = Body(..., description="修正后文件路径"),
    y_axis_feature: str = Body(..., description="Y轴特征列名"),
    anomaly_indices: List[int] = Body(..., description="异常索引列表")
):
    """
    从已有的文件重建散点图数据。
    仅用于前端切换 Y 轴时快速重绘，不重新执行异常检测或生成新文件。
    """

    try:
        scatter = anomaly_service.generate_scatter_from_files(
            base_file_id=base_file_id,
            corrected_file_path=corrected_file_path,
            y_axis_feature=y_axis_feature,
            anomaly_indices=anomaly_indices,
        )
        return {
            "success": True,
            "message": "散点图数据重建完成",
            "data": scatter,
        }
    except FileNotFoundError as e:
        logger.error(f"重建散点图失败，文件未找到: {e}")
        raise HTTPException(status_code=404, detail=f"文件未找到: {e}")
    except ValueError as e:
        logger.error(f"重建散点图失败，参数错误: {e}")
        raise HTTPException(status_code=400, detail=f"参数错误: {e}")
    except Exception as e:
        logger.error(f"重建散点图失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"重建散点图失败: {e}")


@router.post("/predict", summary="预测分析")
async def predict(
    file_id: str = Body(..., description="文件ID"),
    predict_model_type: str = Body("linear", alias="model_type", description="模型类型"),
    parameters: Dict[str, Any] = Body(None, description="预测参数")
):
    """使用季节性 SARIMA 进行预测分析（已禁用）。"""
    return {
        "success": False,
        "message": "预测分析功能已禁用",
        "data": None
    }

@router.post("/cluster", summary="聚类分析")
async def cluster_analysis(
    file_id: str = Body(..., description="文件ID"),
    algorithm: str = Body("kmeans", description="聚类算法"),
    features: List[str] = Body(..., description="特征列表"),
    n_clusters: Optional[int] = Body(3, description="聚类数量"),
    max_iter: Optional[int] = Body(300, description="K-means: 最大迭代次数"),
    linkage: Optional[str] = Body("ward", description="层次聚类: 链接方式"),
    covariance_type: Optional[str] = Body("full", description="GMM: 协方差类型"),
    random_state: Optional[int] = Body(42, description="随机种子"),
    standardize: Optional[bool] = Body(False, description="是否标准化"),
    dimensionality_reduction: Optional[str] = Body("none", description="降维方法"),
    pca_components: Optional[int] = Body(20, description="PCA维度")
):
    """
    执行聚类分析
    
    支持的算法：
    - kmeans: K-means聚类
    - hierarchical: 层次聚类
    - gmm: 高斯混合模型
    """
    try:
        logger.info(f"收到聚类分析请求，文件ID: {file_id}, 算法: {algorithm}")
        
        # 根据不同算法调用相应的聚类函数
        if algorithm == 'kmeans':
            result = cluster_service.kmeans_clustering(
                file_id=file_id,
                features=features,
                n_clusters=n_clusters if n_clusters is not None else 3,
                max_iter=max_iter if max_iter is not None else 300,
                random_state=random_state if random_state is not None else 42,
                standardize=standardize if standardize is not None else False,
                dimensionality_reduction=dimensionality_reduction if dimensionality_reduction is not None else "none",
                pca_components=pca_components if pca_components is not None else 20,
            )
        elif algorithm == 'hierarchical':
            result = cluster_service.hierarchical_clustering(
                file_id=file_id,
                features=features,
                n_clusters=n_clusters if n_clusters is not None else 3,
                linkage=linkage if linkage is not None else "ward",
                random_state=random_state if random_state is not None else 42,
                standardize=standardize if standardize is not None else False,
                dimensionality_reduction=dimensionality_reduction if dimensionality_reduction is not None else "none",
                pca_components=pca_components if pca_components is not None else 20,
            )
        elif algorithm == 'gmm':
            result = cluster_service.gmm_clustering(
                file_id=file_id,
                features=features,
                n_clusters=n_clusters if n_clusters is not None else 3,
                covariance_type=covariance_type if covariance_type is not None else "full",
                random_state=random_state if random_state is not None else 42,
                standardize=standardize if standardize is not None else False,
                dimensionality_reduction=dimensionality_reduction if dimensionality_reduction is not None else "none",
                pca_components=pca_components if pca_components is not None else 20,
            )
        else:
            raise ValueError(f"不支持的聚类算法: {algorithm}")
        
        logger.info(f"聚类分析完成，发现 {result['n_clusters']} 个聚类")
        
        return {
            "success": True,
            "message": "聚类分析完成",
            "data": result
        }
    except FileNotFoundError as e:
        logger.error(f"文件未找到: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=f"文件未找到: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"参数错误: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"参数错误: {str(e)}"
        )
    except Exception as e:
        logger.error(f"聚类分析失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"聚类分析失败: {str(e)}"
        )

@router.post("/cluster/estimate-k", summary="估计最佳K值")
async def estimate_optimal_k(
    file_id: str = Body(..., description="文件ID"),
    features: List[str] = Body(..., description="特征列表"),
    k_min: Optional[int] = Body(2, description="K值最小值"),
    k_max: Optional[int] = Body(10, description="K值最大值"),
    standardize: Optional[bool] = Body(False, description="是否标准化")
):
    """
    估计K-means聚类的最佳K值
    """
    try:
        logger.info(f"收到K值估计请求，文件ID: {file_id}")
        
        result = cluster_service.estimate_optimal_k(
            file_id=file_id,
            features=features,
            k_range=(k_min, k_max),
            standardize=standardize if standardize is not None else False
        )
        
        logger.info(f"K值估计完成，推荐K值: {result['recommended_k']}")
        
        return {
            "success": True,
            "message": "K值估计完成",
            "data": result
        }
    except FileNotFoundError as e:
        logger.error(f"文件未找到: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=f"文件未找到: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"参数错误: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"参数错误: {str(e)}"
        )
    except Exception as e:
        logger.error(f"K值估计失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"K值估计失败: {str(e)}"
        )
