"""
状态机核心模块
管理 KYC 对话流程
"""
from enum import Enum, auto
from typing import Optional, Callable
import re
from app.models.user_profile import UserProfile, InvestmentGoal, RiskLevel


class KYCState(str, Enum):
    """KYC 对话状态枚举"""
    IDLE = "idle"                          # 初始状态
    ICE_BREAKER = "ice_breaker"            # 破冰：自我介绍+开启对话
    GOAL_COLLECTION = "goal_collection"    # 收集投资目标
    RISK_ASSESSMENT = "risk_assessment"    # 风险测评
    FUND_INFO = "fund_info"               # 收集资金信息
    TIMELINE_CONFIRM = "timeline_confirm"  # 确认投资期限
    PLAN_GENERATION = "plan_generation"    # 生成配置方案
    PLAN_DISPLAY = "plan_display"         # 展示方案+解释
    ONGOING = "ongoing"                   # 持续陪伴状态


class StateMachine:
    """
    KYC 状态机
    控制对话流程的状态流转
    """
    
    def __init__(self):
        # 状态流转映射：当前状态 → 下一个状态
        self.transitions = {
            KYCState.IDLE: KYCState.ICE_BREAKER,
            KYCState.ICE_BREAKER: KYCState.GOAL_COLLECTION,
            KYCState.GOAL_COLLECTION: KYCState.RISK_ASSESSMENT,
            KYCState.RISK_ASSESSMENT: KYCState.FUND_INFO,
            KYCState.FUND_INFO: KYCState.TIMELINE_CONFIRM,
            KYCState.TIMELINE_CONFIRM: KYCState.PLAN_GENERATION,
            KYCState.PLAN_GENERATION: KYCState.PLAN_DISPLAY,
            KYCState.PLAN_DISPLAY: KYCState.ONGOING,
        }
        
        # 每个状态对应的系统提示词（指导 LLM 如何引导用户）
        self.state_prompts = {
            KYCState.ICE_BREAKER: """你是"小财"，一位温暖的资产配置顾问。
这是对话的开始，请做简短的自我介绍（不超过30字），
然后自然地询问用户的投资目标（买房、养老、教育金、财富增值等）。
用温暖、口语化的方式，像朋友聊天一样。""",
            
            KYCState.GOAL_COLLECTION: """你需要确认用户的投资目标。
如果用户已经提到了目标（如买房、养老、子女教育），请确认并追问目标金额和大概时间。
如果用户目标不明确，请列举几个常见目标供选择。
保持友好、简洁。""",
            
            KYCState.RISK_ASSESSMENT: """你需要了解用户的风险承受能力。
请用一个生活化的问题来评估：比如"如果你的投资三个月内跌了15%，你会怎么做？"
选项：A. 全部卖出  B. 卖一部分  C. 继续持有  D. 加仓
对应：A→保守型 B→稳健型 C→平衡型/进取型 D→激进型
请自然地提出问题，不要像考试一样。""",
            
            KYCState.FUND_INFO: """了解用户的资金情况。
请询问：
1. 计划投入的总金额（万元）
2. 月收入和月支出（用于评估风险承受力）
用轻松的方式提问，比如'这次你打算拿出多少闲钱来配置？'""",
            
            KYCState.TIMELINE_CONFIRM: """确认投资期限。
综合用户的目标（如买房、养老）和资金情况，确认投资年限。
并告知用户：期限越长，可以承受的风险越高，潜在收益也越高。""",
            
            KYCState.PLAN_GENERATION: """所有信息已收集完毕，准备生成方案。
请告诉用户："好的，我已经了解你的情况了，让我为你量身定制配置方案。"
然后等待系统生成方案数据。""",
            
            KYCState.PLAN_DISPLAY: """方案已生成，请向用户解释配置逻辑。
用故事化的方式解释：
- 为什么选择这些资产类别
- 各类资产的比例依据
- 用生活化的比喻（如"不要把鸡蛋放在一个篮子里"）
语言温暖、易懂，避免堆砌数字。""",
            
            KYCState.ONGOING: """用户已完成初始配置，进入持续陪伴阶段。
可以询问用户是否需要：
1. 设置再平衡提醒
2. 了解某类资产的更多知识
3. 其他问题
保持友好，随时准备帮助用户。""",
        }
    
    def get_next_state(self, current: KYCState) -> Optional[KYCState]:
        """获取下一个状态"""
        return self.transitions.get(current)
    
    def get_state_prompt(self, state: KYCState) -> str:
        """获取指定状态的系统提示词"""
        return self.state_prompts.get(state, "")
    
    def advance(self, profile: UserProfile) -> KYCState:
        """
        推进到下一个状态
        返回新的状态
        """
        current = KYCState(profile.current_state)
        next_state = self.get_next_state(current)
        
        if next_state:
            profile.current_state = next_state.value
            return next_state
        return current  # 没有下一个状态，保持当前
    
    def get_reply_for_state(self, state: KYCState, profile: UserProfile, 
                           user_message: str, llm_client) -> str:
        """
        根据当前状态生成 Agent 回复
        """
        # 获取当前状态的系统提示词
        system_prompt = self.get_state_prompt(state)
        
        # 构建上下文信息
        context = self._build_context(profile)
        
        # 调用 LLM 生成回复
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": f"当前已收集的用户信息：{context}"},
            {"role": "user", "content": user_message}
        ]
        
        return llm_client.chat(messages)
    
    def _build_context(self, profile: UserProfile) -> str:
        """构建用户画像的上下文描述"""
        parts = []
        if profile.goal:
            parts.append(f"投资目标：{profile.goal.value}")
        if profile.goal_amount:
            parts.append(f"目标金额：{profile.goal_amount}万元")
        if profile.goal_timeline:
            parts.append(f"投资期限：{profile.goal_timeline}年")
        if profile.risk_level:
            parts.append(f"风险等级：{profile.risk_level.value}")
        if profile.invest_amount:
            parts.append(f"可投资金额：{profile.invest_amount}万元")
        
        return "；".join(parts) if parts else "暂无信息"
    
    def try_parse_answer(self, state: KYCState, user_message: str, 
                        profile: UserProfile) -> bool:
        """
        尝试从用户回答中提取信息并更新画像
        返回是否成功提取
        """
        msg = user_message.strip()
        
        if state == KYCState.GOAL_COLLECTION:
            # 解析投资目标
            goal_map = {
                "买房": InvestmentGoal.HOME,
                "房": InvestmentGoal.HOME,
                "养老": InvestmentGoal.RETIRE,
                "退休": InvestmentGoal.RETIRE,
                "教育": InvestmentGoal.EDUCATION,
                "孩子": InvestmentGoal.EDUCATION,
                "增值": InvestmentGoal.WEALTH,
                "赚钱": InvestmentGoal.WEALTH,
                "理财": InvestmentGoal.LIQUIDITY,
                "闲钱": InvestmentGoal.LIQUIDITY,
            }
            for keyword, goal in goal_map.items():
                if keyword in msg:
                    profile.goal = goal
                    # 尝试提取金额（简单匹配数字+万）
                    amount_match = re.search(r'(\d+)\s*万', msg)
                    if amount_match:
                        profile.goal_amount = float(amount_match.group(1))
                    # 尝试提取年限
                    year_match = re.search(r'(\d+)\s*年', msg)
                    if year_match:
                        profile.goal_timeline = int(year_match.group(1))
                    return True
            return False
        
        elif state == KYCState.RISK_ASSESSMENT:
            # 解析风险测评答案
            if "A" in msg or "全部卖出" in msg or " Conservative" in msg:
                profile.risk_level = RiskLevel.CONSERVATIVE
                return True
            elif "B" in msg or "卖一部分" in msg:
                profile.risk_level = RiskLevel.STEADY
                return True
            elif "C" in msg or "持有" in msg or "不动" in msg:
                profile.risk_level = RiskLevel.BALANCED
                return True
            elif "D" in msg or "加仓" in msg or "再买" in msg:
                profile.risk_level = RiskLevel.AGGRESSIVE
                return True
            # 关键词匹配
            if "不能亏" in msg or "怕亏" in msg:
                profile.risk_level = RiskLevel.CONSERVATIVE
                return True
            elif "稳健" in msg or "保守" in msg:
                profile.risk_level = RiskLevel.STEADY
                return True
            elif "平衡" in msg or "都可以" in msg:
                profile.risk_level = RiskLevel.BALANCED
                return True
            elif "激进" in msg or "高风险" in msg:
                profile.risk_level = RiskLevel.RADICAL
                return True
            return False
        
        elif state == KYCState.FUND_INFO:
            # 解析资金信息
            amount_match = re.search(r'(\d+)\s*万', msg)
            if amount_match:
                profile.invest_amount = float(amount_match.group(1))
                return True
            # 匹配 "10w" "50W" 格式
            amount_match2 = re.search(r'(\d+)\s*[wW]', msg)
            if amount_match2:
                profile.invest_amount = float(amount_match2.group(1))
                return True
            return False
        
        elif state == KYCState.TIMELINE_CONFIRM:
            # 解析投资期限
            year_match = re.search(r'(\d+)\s*年', msg)
            if year_match:
                profile.goal_timeline = int(year_match.group(1))
                return True
            return False
        
        return False


# 全局状态机实例
state_machine = StateMachine()
