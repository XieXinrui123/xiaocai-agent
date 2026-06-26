"""
金融数据服务模块
封装 AKShare 数据获取，提供统一接口
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import json


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """标准化 AKShare 返回的列名，使其更健壮"""
    col_map = {}
    for c in df.columns:
        s = str(c).lower()
        if "date" in s or "日期" in c:
            col_map[c] = "date"
        elif s in ("open", "开盘"):
            col_map[c] = "open"
        elif s in ("close", "收盘", "最新价"):
            col_map[c] = "close"
        elif s in ("high", "最高"):
            col_map[c] = "high"
        elif s in ("low", "最低"):
            col_map[c] = "low"
        elif "volume" in s or "vol" in s or "成交量" in c:
            col_map[c] = "volume"
        elif "nav" in s or "净值" in c:
            col_map[c] = "nav"
    if col_map:
        df = df.rename(columns=col_map)
    return df


class DataService:
    """
    金融数据服务
    基于 AKShare 获取历史行情数据
    MVP 阶段支持：ETF 历史数据、基金净值数据
    """
    
    # 资产代码映射（AKShare 格式）
    ETF_CODE_MAP = {
        "510300": "sh510300",  # 沪深300ETF
        "510500": "sh510500",  # 中证500ETF
        "513130": "sh513130",  # 恒生科技ETF
        "518880": "sh518880",  # 黄金ETF
        "513100": "sh513100",  # 纳斯达克100ETF
        "511880": "sh511880",  # 银华日利（货币）
    }
    
    # 历史数据缓存目录
    CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache"
    
    def __init__(self):
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    def get_etf_history(self, code: str, period: str = "3y") -> pd.DataFrame:
        """
        获取 ETF 历史行情

        Args:
            code: ETF 代码（如 510300）
            period: 时间范围 1y/3y/5y/10y

        Returns:
            DataFrame: 包含 date, open, close, high, low, volume 列
        """
        # 先尝试从缓存读取
        cache_file = self.CACHE_DIR / f"{code}_{period}.csv"
        if cache_file.exists():
            # 检查缓存是否过期（超过 1 天）
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - mtime < timedelta(days=1):
                return pd.read_csv(cache_file, index_col=0, parse_dates=True)

        try:
            # 使用 AKShare 格式代码（如 sh510300）
            ak_code = self.ETF_CODE_MAP.get(code, code)
            # 通过 AKShare 获取 ETF 历史数据
            # 使用 fund_etf_hist_em 接口（东方财富数据源）
            df = ak.fund_etf_hist_em(
                symbol=ak_code,
                period="daily",
                start_date=self._get_start_date(period),
                end_date=datetime.now().strftime("%Y%m%d"),
                adjust="qfq"  # 前复权
            )

            # 标准化列名（处理不同版本 AKShare 返回的列名差异）
            df = _normalize_columns(df)

            if "date" not in df.columns or "close" not in df.columns:
                print(f"获取 {code} 数据失败：列名不匹配，原始列：{list(df.columns)}")
                if cache_file.exists():
                    return pd.read_csv(cache_file, index_col=0, parse_dates=True)
                return pd.DataFrame()

            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            # 确保保留必要列，缺失的列用 NaN 填充
            keep_cols = ["open", "close", "high", "low", "volume"]
            for c in keep_cols:
                if c not in df.columns:
                    df[c] = float("nan")
            df = df[keep_cols]

            # 保存缓存
            df.to_csv(cache_file)
            return df

        except Exception as e:
            print(f"获取 {code} 数据失败: {e}")
            # 如果获取失败但有缓存，返回缓存数据
            if cache_file.exists():
                return pd.read_csv(cache_file, index_col=0, parse_dates=True)
            return pd.DataFrame()
    
    def get_fund_nav_history(self, code: str, period: str = "3y") -> pd.DataFrame:
        """
        获取开放式基金历史净值

        Args:
            code: 基金代码（如 000171）
            period: 时间范围

        Returns:
            DataFrame: 包含 date, nav 列
        """
        cache_file = self.CACHE_DIR / f"fund_{code}_{period}.csv"
        if cache_file.exists():
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - mtime < timedelta(days=1):
                return pd.read_csv(cache_file, index_col=0, parse_dates=True)

        try:
            # 使用 AKShare 获取基金净值
            df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
            if df is None or df.empty:
                raise ValueError("返回数据为空")

            # 安全处理列名（不同版本 AKShare 返回的列名可能不同）
            df = _normalize_columns(df)

            if "date" not in df.columns:
                print(f"获取基金 {code} 净值失败：缺少 date 列，原始列：{list(df.columns)}")
                if cache_file.exists():
                    return pd.read_csv(cache_file, index_col=0, parse_dates=True)
                return pd.DataFrame()

            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)

            # 确保有 nav 列
            if "nav" not in df.columns:
                # 尝试使用其他可能的净值列
                for col in df.columns:
                    if "nav" in str(col).lower() or "净值" in str(col):
                        df = df.rename(columns={col: "nav"})
                        break
                if "nav" not in df.columns:
                    # 如果没有找到，使用第一列作为 nav
                    df["nav"] = df.iloc[:, 0]

            # 过滤时间范围
            start_date = self._get_start_date(period)
            df = df[df.index >= start_date]

            df.to_csv(cache_file)
            return df

        except Exception as e:
            print(f"获取基金 {code} 净值失败: {e}")
            if cache_file.exists():
                return pd.read_csv(cache_file, index_col=0, parse_dates=True)
            return pd.DataFrame()
    
    def get_asset_history(self, asset_name: str, code: str, 
                          category: str, period: str = "3y") -> pd.DataFrame:
        """
        统一接口：获取任意资产的历史数据
        
        Args:
            asset_name: 资产名称
            code: 产品代码
            category: 资产类别（etf/fund）
            period: 时间范围
        
        Returns:
            DataFrame with 'close' column
        """
        if category in ["etf", "core", "satellite"] or asset_name in ["沪深300", "中证500", "恒生科技", "黄金ETF", "纳斯达克100", "REITs"]:
            df = self.get_etf_history(code, period)
        else:
            df = self.get_fund_nav_history(code, period)
        
        # 统一返回有 'close' 列的数据
        if "close" not in df.columns and "nav" in df.columns:
            df = df.rename(columns={"nav": "close"})
        
        return df
    
    def _get_start_date(self, period: str) -> str:
        """根据周期计算起始日期"""
        now = datetime.now()
        mapping = {
            "1y": now - timedelta(days=365),
            "3y": now - timedelta(days=365*3),
            "5y": now - timedelta(days=365*5),
            "10y": now - timedelta(days=365*10),
        }
        return mapping.get(period, now - timedelta(days=365*3)).strftime("%Y%m%d")


# 全局数据服务实例
data_service = DataService()
