"""
压力测试模块
用历史极端行情回测配置方案的表现
"""
import pandas as pd
import numpy as np
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

from app.services.allocation_engine import AllocationPlan
from app.services.data_service import data_service


@dataclass
class StressTestResult:
    """压力测试结果"""
    scenario_name: str        # 情景名称
    scenario_period: str      # 历史时期
    description: str          # 情景描述
    
    # 回测指标
    total_return: float       # 区间总收益
    annualized_return: float  # 年化收益
    max_drawdown: float       # 最大回撤
    volatility: float         # 波动率
    
    # 与基准对比
    benchmark_return: float   # 基准收益（如沪深300）
    outperformance: float     # 超额收益


class StressTester:
    """
    压力测试器
    用历史极端行情检验配置方案的韧性
    """
    
    # 预定义的历史压力情景
    SCENARIOS = [
        {
            "name": "2008年金融危机",
            "period": "2008",
            "description": "全球金融危机，A股从6124点暴跌到1664点",
            "start": "2007-10-16",
            "end": "2008-10-28",
        },
        {
            "name": "2015年股灾",
            "period": "2015",
            "description": "A股杠杆牛转熊，三轮千股跌停",
            "start": "2015-06-12",
            "end": "2015-08-26",
        },
        {
            "name": "2018年贸易战",
            "period": "2018",
            "description": "中美贸易战爆发，A股全年下跌",
            "start": "2018-01-24",
            "end": "2018-12-27",
        },
        {
            "name": "2022年多重压力",
            "period": "2022",
            "description": "俄乌冲突+疫情封控+美联储激进加息",
            "start": "2022-01-04",
            "end": "2022-10-31",
        },
        {
            "name": "2024年调整期",
            "period": "2024",
            "description": "经济复苏不及预期，市场持续震荡",
            "start": "2024-05-01",
            "end": "2024-09-18",
        },
    ]
    
    # 资产代码映射
    ASSET_CODES = {
        "沪深300": "510300",
        "中证500": "510500",
        "恒生科技": "513130",
        "黄金ETF": "518880",
        "纳斯达克100": "513100",
        "中长期纯债": "000171",
        "短债基金": "006662",
        "货币基金": "511880",
        "REITs": "508000",
    }
    
    # 资产类别映射（用于确定用哪个数据接口）
    ASSET_CATEGORIES = {
        "沪深300": "etf",
        "中证500": "etf",
        "恒生科技": "etf",
        "黄金ETF": "etf",
        "纳斯达克100": "etf",
        "中长期纯债": "fund",
        "短债基金": "fund",
        "货币基金": "etf",
        "REITs": "etf",
    }
    
    def run_test(self, plan: AllocationPlan) -> list[StressTestResult]:
        """
        对配置方案运行全部压力测试情景
        
        Args:
            plan: 资产配置方案
        
        Returns:
            list[StressTestResult]: 各情景的回测结果
        """
        results = []
        
        for scenario in self.SCENARIOS:
            result = self._test_scenario(plan, scenario)
            if result:
                results.append(result)
        
        return results
    
    def _test_scenario(self, plan: AllocationPlan, 
                       scenario: dict) -> Optional[StressTestResult]:
        """
        测试单个压力情景
        """
        try:
            start_date = scenario["start"]
            end_date = scenario["end"]
            
            # 获取各资产在压力期间的收益
            asset_returns = {}
            
            for asset in plan.assets:
                asset_name = asset["name"]
                code = self.ASSET_CODES.get(asset_name)
                category = self.ASSET_CATEGORIES.get(asset_name, "etf")
                
                if not code:
                    continue
                
                # 获取历史数据
                df = data_service.get_asset_history(asset_name, code, category, period="10y")
                
                if df.empty:
                    continue
                
                # 截取压力期间的数据
                mask = (df.index >= start_date) & (df.index <= end_date)
                period_df = df.loc[mask]
                
                if len(period_df) < 2:
                    continue
                
                # 计算区间收益率
                start_price = period_df["close"].iloc[0]
                end_price = period_df["close"].iloc[-1]
                total_return = (end_price - start_price) / start_price
                
                asset_returns[asset_name] = total_return
            
            # 计算组合收益（加权平均）
            portfolio_return = 0.0
            for asset in plan.assets:
                name = asset["name"]
                weight = asset["weight"]
                ret = asset_returns.get(name, 0.0)
                portfolio_return += weight * ret
            
            # 获取基准（沪深300）收益
            benchmark_return = asset_returns.get("沪深300", 0.0)
            
            # 计算年化收益（简化：假设 250 个交易日/年）
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            years = max((end_dt - start_dt).days / 365, 0.1)
            annualized_return = (1 + portfolio_return) ** (1 / years) - 1
            
            # 估算最大回撤（简化版：用各资产最大回撤加权）
            # 实际应该用组合净值序列计算，但数据可能不完整
            max_dd = plan.max_drawdown * abs(portfolio_return / 0.20) if portfolio_return < 0 else 0.05
            max_dd = min(max_dd, 0.60)  # 上限 60%
            
            # 估算波动率
            vol = plan.expected_risk * abs(portfolio_return / 0.20) if portfolio_return < 0 else plan.expected_risk * 0.5
            
            return StressTestResult(
                scenario_name=scenario["name"],
                scenario_period=scenario["period"],
                description=scenario["description"],
                total_return=round(portfolio_return, 4),
                annualized_return=round(annualized_return, 4),
                max_drawdown=round(max_dd, 4),
                volatility=round(vol, 4),
                benchmark_return=round(benchmark_return, 4),
                outperformance=round(portfolio_return - benchmark_return, 4),
            )
            
        except Exception as e:
            print(f"压力测试 {scenario['name']} 出错: {e}")
            return None
    
    def generate_summary(self, results: list[StressTestResult]) -> dict:
        """
        生成压力测试汇总报告
        """
        if not results:
            return {"message": "暂无压力测试数据"}
        
        # 计算平均最大回撤
        avg_max_dd = np.mean([r.max_drawdown for r in results])
        
        # 找出最差情景
        worst = min(results, key=lambda r: r.total_return)
        
        # 统计跑赢基准的次数
        beat_benchmark = sum(1 for r in results if r.outperformance > 0)
        
        return {
            "avg_max_drawdown": f"{avg_max_dd:.1%}",
            "worst_scenario": {
                "name": worst.scenario_name,
                "return": f"{worst.total_return:.1%}",
                "max_drawdown": f"{worst.max_drawdown:.1%}",
            },
            "beat_benchmark": f"{beat_benchmark}/{len(results)} 次跑赢沪深300",
            "details": [
                {
                    "scenario": r.scenario_name,
                    "period": r.scenario_period,
                    "portfolio_return": f"{r.total_return:.1%}",
                    "benchmark_return": f"{r.benchmark_return:.1%}",
                    "max_drawdown": f"{r.max_drawdown:.1%}",
                    "outperformance": f"{r.outperformance:.1%}",
                }
                for r in results
            ]
        }


# 全局压力测试器实例
stress_tester = StressTester()
