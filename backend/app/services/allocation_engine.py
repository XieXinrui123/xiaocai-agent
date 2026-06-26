"""
资产配置规则引擎
基于风险分层的配置模型
"""
from dataclasses import dataclass, field
from typing import Optional
import math
from app.models.user_profile import UserProfile, RiskLevel


@dataclass
class Asset:
    """资产类别定义"""
    name: str              # 资产名称
    category: str          # 所属类别（防御/核心/卫星）
    default_weight: float  # 默认权重（在所属类别内的比例）
    product_code: str      # 示例产品代码
    product_name: str      # 示例产品名称
    description: str       # 资产描述


@dataclass
class AllocationPlan:
    """资产配置方案"""
    # 用户画像
    profile: UserProfile
    
    # 三层权重
    defense_weight: float    # 防御层总权重
    core_weight: float       # 核心层总权重
    satellite_weight: float  # 卫星层总权重
    
    # 具体资产分配
    assets: list[dict] = field(default_factory=list)
    
    # 方案元信息
    expected_return: float = 0.0      # 预期年化收益
    expected_risk: float = 0.0        # 预期波动率（标准差）
    max_drawdown: float = 0.0         # 历史最大回撤参考
    
    def to_dict(self) -> dict:
        """转换为字典格式（用于API返回）"""
        return {
            "defense_layer": {
                "total_weight": self.defense_weight,
                "description": "防御层：债券打底，稳住基本盘"
            },
            "core_layer": {
                "total_weight": self.core_weight,
                "description": "核心层：权益资产，长期增值主力"
            },
            "satellite_layer": {
                "total_weight": self.satellite_weight,
                "description": "卫星层：另类资产，分散风险+增强收益"
            },
            "assets": self.assets,
            "metrics": {
                "expected_return": f"{self.expected_return:.1%}",
                "expected_risk": f"{self.expected_risk:.1%}",
                "max_drawdown": f"{self.max_drawdown:.1%}"
            }
        }


class AllocationEngine:
    """
    资产配置规则引擎
    基于风险分层模型生成配置方案
    """
    
    # ===== 资产池定义 =====
    ASSET_POOL = [
        # 防御层 - 债券/货币
        Asset("中长期纯债", "defense", 0.50, "000171", "招商安泰债券A", 
              "中长期纯债基金，收益稳定，波动极小"),
        Asset("短债基金", "defense", 0.35, "006662", "嘉实超短债", 
              "短久期债券，流动性好，适合作为现金管理工具"),
        Asset("货币基金", "defense", 0.15, "511880", "银华日利", 
              "高流动性，几乎无波动，应急资金首选"),
        
        # 核心层 - 权益资产
        Asset("沪深300", "core", 0.40, "510300", "华泰柏瑞沪深300ETF", 
              "A股大盘蓝筹，中国经济的核心资产"),
        Asset("中证500", "core", 0.30, "510500", "南方中证500ETF", 
              "中小盘成长股，捕捉经济转型机会"),
        Asset("恒生科技", "core", 0.30, "513130", "华泰柏瑞恒生科技ETF", 
              "港股科技龙头，与A股形成互补"),
        
        # 卫星层 - 另类资产
        Asset("黄金ETF", "satellite", 0.40, "518880", "华安黄金ETF", 
              "避险资产，通胀对冲工具，与股债相关性低"),
        Asset("纳斯达克100", "satellite", 0.40, "513100", "国泰纳斯达克100", 
              "美股科技龙头，分享全球科技创新红利"),
        Asset("REITs", "satellite", 0.20, "508000", "华安张江光大REIT", 
              "不动产投资信托，稳定分红收益"),
    ]
    
    # ===== 风险等级 → 三层比例映射 =====
    RISK_LAYER_MAP = {
        RiskLevel.CONSERVATIVE: {"defense": 0.70, "core": 0.25, "satellite": 0.05},
        RiskLevel.STEADY:       {"defense": 0.55, "core": 0.35, "satellite": 0.10},
        RiskLevel.BALANCED:     {"defense": 0.40, "core": 0.45, "satellite": 0.15},
        RiskLevel.AGGRESSIVE:   {"defense": 0.25, "core": 0.55, "satellite": 0.20},
        RiskLevel.RADICAL:      {"defense": 0.10, "core": 0.65, "satellite": 0.25},
    }
    
    # ===== 投资期限微调系数 =====
    # 期限越长，核心层和卫星层权重越高
    TIMELINE_ADJUSTMENT = {
        1:  {"core_delta": -0.05, "satellite_delta": -0.02},  # 1年：更保守
        3:  {"core_delta": -0.02, "satellite_delta": -0.01},  # 3年：略保守
        5:  {"core_delta": 0.00,  "satellite_delta": 0.00},   # 5年：标准
        10: {"core_delta": 0.03,  "satellite_delta": 0.02},   # 10年：略激进
        20: {"core_delta": 0.05,  "satellite_delta": 0.03},   # 20年：更激进
    }
    
    # ===== 预期收益/风险参数（基于历史数据近似） =====
    EXPECTED_RETURNS = {
        "defense": 0.03,    # 防御层预期年化 3%
        "core": 0.08,       # 核心层预期年化 8%
        "satellite": 0.10,  # 卫星层预期年化 10%
    }
    
    EXPECTED_RISKS = {
        "defense": 0.02,    # 防御层波动率 2%
        "core": 0.18,       # 核心层波动率 18%
        "satellite": 0.22,  # 卫星层波动率 22%
    }
    
    MAX_DRAWDOWNS = {
        "defense": 0.05,    # 防御层最大回撤 5%
        "core": 0.30,       # 核心层最大回撤 30%
        "satellite": 0.35,  # 卫星层最大回撤 35%
    }
    
    def generate_plan(self, profile: UserProfile) -> AllocationPlan:
        """
        根据用户画像生成资产配置方案
        
        Args:
            profile: 用户画像（需完整）
        
        Returns:
            AllocationPlan: 配置方案
        """
        if not profile.is_complete():
            raise ValueError("用户画像不完整，无法生成方案")
        
        # 1. 根据风险等级确定三层基础比例
        risk_weights = self.RISK_LAYER_MAP.get(
            profile.risk_level, 
            self.RISK_LAYER_MAP[RiskLevel.BALANCED]  # 默认平衡型
        )
        
        defense_pct = risk_weights["defense"]
        core_pct = risk_weights["core"]
        satellite_pct = risk_weights["satellite"]
        
        # 2. 根据投资期限微调
        timeline = profile.goal_timeline or 5
        adjustment = self._get_timeline_adjustment(timeline)
        
        core_pct += adjustment["core_delta"]
        satellite_pct += adjustment["satellite_delta"]
        defense_pct -= adjustment["core_delta"] + adjustment["satellite_delta"]
        
        # 确保比例合法（在 0-1 之间）
        defense_pct = max(0.05, min(0.80, defense_pct))
        core_pct = max(0.10, min(0.75, core_pct))
        satellite_pct = max(0.00, min(0.40, satellite_pct))
        
        # 重新归一化确保总和为 1
        total = defense_pct + core_pct + satellite_pct
        defense_pct /= total
        core_pct /= total
        satellite_pct /= total
        
        # 3. 计算具体资产权重
        assets = self._calculate_asset_weights(
            defense_pct, core_pct, satellite_pct
        )
        
        # 4. 计算组合预期收益和风险
        expected_return = (
            defense_pct * self.EXPECTED_RETURNS["defense"] +
            core_pct * self.EXPECTED_RETURNS["core"] +
            satellite_pct * self.EXPECTED_RETURNS["satellite"]
        )
        
        # 简化计算组合风险（假设层间相关系数为 0.3）
        corr = 0.3
        expected_risk = math.sqrt(
            (defense_pct * self.EXPECTED_RISKS["defense"])**2 +
            (core_pct * self.EXPECTED_RISKS["core"])**2 +
            (satellite_pct * self.EXPECTED_RISKS["satellite"])**2 +
            2 * corr * defense_pct * core_pct * self.EXPECTED_RISKS["defense"] * self.EXPECTED_RISKS["core"] +
            2 * corr * defense_pct * satellite_pct * self.EXPECTED_RISKS["defense"] * self.EXPECTED_RISKS["satellite"] +
            2 * corr * core_pct * satellite_pct * self.EXPECTED_RISKS["core"] * self.EXPECTED_RISKS["satellite"]
        )
        
        # 简化估算最大回撤
        max_drawdown = (
            defense_pct * self.MAX_DRAWDOWNS["defense"] +
            core_pct * self.MAX_DRAWDOWNS["core"] +
            satellite_pct * self.MAX_DRAWDOWNS["satellite"]
        ) * 1.2  # 乘以 1.2 作为安全边际
        
        return AllocationPlan(
            profile=profile,
            defense_weight=round(defense_pct, 4),
            core_weight=round(core_pct, 4),
            satellite_weight=round(satellite_pct, 4),
            assets=assets,
            expected_return=round(expected_return, 4),
            expected_risk=round(expected_risk, 4),
            max_drawdown=round(max_drawdown, 4),
        )
    
    def _get_timeline_adjustment(self, timeline: int) -> dict:
        """根据投资期限获取微调系数"""
        # 找到最接近的期限档位
        available_years = sorted(self.TIMELINE_ADJUSTMENT.keys())
        closest = available_years[0]
        for y in available_years:
            if abs(timeline - y) < abs(timeline - closest):
                closest = y
        return self.TIMELINE_ADJUSTMENT[closest]
    
    def _calculate_asset_weights(self, defense_pct: float, 
                                  core_pct: float, 
                                  satellite_pct: float) -> list[dict]:
        """
        计算各具体资产的权重
        三层权重 × 层内资产默认比例 = 最终权重
        """
        assets = []
        
        for asset in self.ASSET_POOL:
            # 获取该资产所属层的总权重
            layer_weight = {
                "defense": defense_pct,
                "core": core_pct,
                "satellite": satellite_pct,
            }.get(asset.category, 0)
            
            # 最终权重 = 层权重 × 层内比例
            final_weight = layer_weight * asset.default_weight
            
            if final_weight > 0.001:  # 过滤掉过小的权重
                assets.append({
                    "name": asset.name,
                    "category": asset.category,
                    "weight": round(final_weight, 4),
                    "weight_pct": f"{final_weight:.2%}",
                    "product_code": asset.product_code,
                    "product_name": asset.product_name,
                    "description": asset.description,
                })
        
        # 按权重降序排列
        assets.sort(key=lambda x: x["weight"], reverse=True)
        return assets


# 全局引擎实例
allocation_engine = AllocationEngine()
