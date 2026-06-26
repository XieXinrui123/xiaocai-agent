"""
对话 API 路由（状态机版）
处理用户与 Agent 的 KYC 对话交互
"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.llm_client import llm_client
from app.services.state_machine import state_machine, KYCState
from app.services.session_manager import session_manager

router = APIRouter(prefix="/chat", tags=["对话"])


# ========== 请求/响应模型 ==========

class ChatRequest(BaseModel):
    """对话请求"""
    message: str          # 用户消息
    session_id: str       # 会话ID


class ChatResponse(BaseModel):
    """对话响应"""
    reply: str            # Agent 回复
    session_id: str       # 会话ID
    current_state: str    # 当前对话状态
    collected_info: dict  # 已收集的信息摘要


# ========== API 接口 ==========

@router.post("/send", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    发送消息给 Agent（状态机驱动）
    
    这是核心对话接口，Agent 会根据当前状态自动引导对话流程。
    
    示例请求：
    {
        "message": "你好，我想买房",
        "session_id": "user_123"
    }
    """
    # 1. 获取或创建用户画像
    profile = session_manager.get_or_create(request.session_id)
    
    # 2. 如果会话是全新的（idle状态），自动进入破冰阶段
    if profile.current_state == KYCState.IDLE.value:
        profile.current_state = KYCState.ICE_BREAKER.value
    
    current_state = KYCState(profile.current_state)
    
    # 2.5 如果当前是破冰阶段且用户有输入，说明已完成破冰，推进到目标采集
    if current_state == KYCState.ICE_BREAKER and request.message.strip():
        state_machine.advance(profile)
        current_state = KYCState(profile.current_state)
    
    # 3. 尝试从用户消息中提取信息（更新画像）
    parsed = state_machine.try_parse_answer(
        current_state, request.message, profile
    )
    
    # 4. 根据当前状态生成回复
    reply = state_machine.get_reply_for_state(
        current_state, profile, request.message, llm_client
    )
    
    # 5. 如果成功解析了关键信息，推进到下一个状态
    if parsed and current_state not in [
        KYCState.PLAN_GENERATION, 
        KYCState.PLAN_DISPLAY,
        KYCState.ONGOING
    ]:
        # 检查画像是否完整（可以生成方案了）
        if profile.is_complete() and current_state != KYCState.PLAN_GENERATION:
            profile.current_state = KYCState.PLAN_GENERATION.value
        else:
            # 正常推进状态
            state_machine.advance(profile)
    
    # 6. 保存更新后的画像
    session_manager.update(profile)
    
    # 7. 返回响应
    return ChatResponse(
        reply=reply,
        session_id=request.session_id,
        current_state=profile.current_state,
        collected_info={
            "goal": profile.goal.value if profile.goal else None,
            "risk_level": profile.risk_level.value if profile.risk_level else None,
            "invest_amount": profile.invest_amount,
            "goal_timeline": profile.goal_timeline,
            "is_complete": profile.is_complete()
        }
    )


@router.post("/start")
async def start_chat(session_id: str):
    """
    开始新对话
    自动进入破冰阶段，返回 Agent 的开场白
    """
    # 创建新的用户画像
    profile = session_manager.get_or_create(session_id)
    profile.current_state = KYCState.ICE_BREAKER.value
    
    # 生成开场白
    reply = state_machine.get_reply_for_state(
        KYCState.ICE_BREAKER, profile, "", llm_client
    )
    
    session_manager.update(profile)
    
    return {
        "reply": reply,
        "session_id": session_id,
        "current_state": profile.current_state
    }


@router.get("/profile/{session_id}")
async def get_profile(session_id: str):
    """
    查看用户的当前画像（调试用）
    """
    profile = session_manager.get(session_id)
    if not profile:
        return {"error": "会话不存在"}
    
    return {
        "session_id": profile.session_id,
        "current_state": profile.current_state,
        "goal": profile.goal.value if profile.goal else None,
        "goal_amount": profile.goal_amount,
        "goal_timeline": profile.goal_timeline,
        "risk_level": profile.risk_level.value if profile.risk_level else None,
        "invest_amount": profile.invest_amount,
        "is_complete": profile.is_complete(),
        "missing_fields": profile.get_missing_fields()
    }


@router.delete("/profile/{session_id}")
async def reset_profile(session_id: str):
    """
    重置用户画像（重新开始 KYC）
    """
    session_manager.delete(session_id)
    return {"message": "会话已重置", "session_id": session_id}
