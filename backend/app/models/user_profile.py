"""
用户画像数据模型
存储用户的风险偏好、投资目标、资金信息等
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum


class InvestmentGoal(str, Enum):
    """投资目标"""
    HOME = "买房"           # 购房
    RETIRE = "养老"         # 退休储备
    EDUCATION = "教育金"     # 子女教育
    WEALTH = "财富增值"      # 资产增值
    LIQUIDITY = "闲钱理财"   # 短期理财
    OTHER = "其他"          # 其他


class RiskLevel(str, Enum):
    """风险等级"""
    CONSERVATIVE = "保守型"      # 保守型：不能承受亏损
    STEADY = "稳健型"            # 稳健型：能承受小额亏损
    BALANCED = "平衡型"          # 平衡型：能承受一定波动
    AGGRESSIVE = "进取型"        # 进取型：能承受较大波动
    RADICAL = "激进型"           # 激进型：追求高收益，能承受大亏


class UserProfile(BaseModel):
    """
    用户画像
    通过 KYC 对话采集的完整信息
    """
    # 会话ID
    session_id: str
    
    # 投资目标
    goal: Optional[InvestmentGoal] = None
    goal_amount: Optional[float] = None      # 目标金额（万元）
    goal_timeline: Optional[int] = None      # 目标年限（年）
    
    # 风险偏好
    risk_level: Optional[RiskLevel] = None
    
    # 资金信息
    invest_amount: Optional[float] = None    # 可投资金额（万元）
    monthly_income: Optional[float] = None   # 月收入（万元）
    monthly_expense: Optional[float] = None  # 月支出（万元）
    
    # 投资经验
    has_experience: Optional[bool] = None    # 是否有投资经验
    held_products: Optional[list[str]] = None  # 曾持有过的产品
    
    # 流动性需求
    emergency_fund_months: Optional[int] = None  # 应急资金覆盖月数
    
    # 当前状态（状态机用）
    current_state: str = "idle"               # 当前对话状态
    
    def is_complete(self) -> bool:
        """检查用户画像是否完整（足以生成配置方案）"""
        return (
            self.goal is not None
            and self.risk_level is not None
            and self.invest_amount is not None
            and self.goal_timeline is not None
        )
    
    def get_missing_fields(self) -> list[str]:
        """获取还未填写的关键字段"""
        missing = []
        if self.goal is None:
            missing.append("投资目标")
        if self.risk_level is None:
            missing.append("风险偏好")
        if self.invest_amount is None:
            missing.append("可投资金额")
        if self.goal_timeline is None:
            missing.append("投资期限")
        return missing
