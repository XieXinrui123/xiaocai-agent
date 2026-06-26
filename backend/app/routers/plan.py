"""
资产配置方案 API 路由
生成和查看配置方案
"""
from fastapi import APIRouter, HTTPException

from app.services.allocation_engine import allocation_engine
from app.services.session_manager import session_manager
from app.services.stress_test import stress_tester

router = APIRouter(prefix="/plan", tags=["配置方案"])


@router.post("/generate/{session_id}")
async def generate_plan(session_id: str):
    """
    根据用户画像生成资产配置方案
    """
    # 获取用户画像
    profile = session_manager.get(session_id)
    if not profile:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 检查画像是否完整
    if not profile.is_complete():
        missing = profile.get_missing_fields()
        raise HTTPException(
            status_code=400, 
            detail=f"用户画像不完整，缺少：{', '.join(missing)}"
        )
    
    # 生成方案
    plan = allocation_engine.generate_plan(profile)
    
    # 更新用户状态到方案展示
    from app.services.state_machine import KYCState
    profile.current_state = KYCState.PLAN_DISPLAY.value
    session_manager.update(profile)
    
    return {
        "session_id": session_id,
        "plan": plan.to_dict(),
        "current_state": profile.current_state
    }


@router.get("/example")
async def example_plan():
    """
    查看示例配置方案（无需会话）
    用于前端开发和测试
    """
    from app.models.user_profile import UserProfile, RiskLevel, InvestmentGoal
    
    # 构造一个示例画像
    example_profile = UserProfile(
        session_id="example",
        goal=InvestmentGoal.WEALTH,
        goal_amount=100,
        goal_timeline=10,
        risk_level=RiskLevel.BALANCED,
        invest_amount=50,
    )
    
    plan = allocation_engine.generate_plan(example_profile)
    
    return plan.to_dict()


@router.get("/stress-test/{session_id}")
async def stress_test_plan(session_id: str):
    """
    对用户的配置方案进行压力测试
    """
    # 获取用户画像
    profile = session_manager.get(session_id)
    if not profile:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    if not profile.is_complete():
        raise HTTPException(status_code=400, detail="用户画像不完整")
    
    # 生成方案
    plan = allocation_engine.generate_plan(profile)
    
    # 运行压力测试
    results = stress_tester.run_test(plan)
    
    # 生成汇总
    summary = stress_tester.generate_summary(results)
    
    return {
        "session_id": session_id,
        "allocation_plan": plan.to_dict(),
        "stress_test": summary,
    }
