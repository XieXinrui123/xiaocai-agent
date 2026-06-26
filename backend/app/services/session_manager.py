"""
会话管理器
管理用户的对话会话和画像数据
MVP 阶段用内存存储，后续可替换为 Redis
"""
from app.models.user_profile import UserProfile


class SessionManager:
    """
    会话管理器（内存版）
    key: session_id
    value: UserProfile
    """
    
    def __init__(self):
        # 内存存储：session_id → UserProfile
        self._sessions: dict[str, UserProfile] = {}
    
    def get_or_create(self, session_id: str) -> UserProfile:
        """
        获取或创建用户画像
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = UserProfile(session_id=session_id)
        return self._sessions[session_id]
    
    def get(self, session_id: str) -> UserProfile | None:
        """获取用户画像"""
        return self._sessions.get(session_id)
    
    def update(self, profile: UserProfile) -> None:
        """更新用户画像"""
        self._sessions[profile.session_id] = profile
    
    def delete(self, session_id: str) -> None:
        """删除会话"""
        self._sessions.pop(session_id, None)
    
    def list_sessions(self) -> list[str]:
        """列出所有会话ID（调试用）"""
        return list(self._sessions.keys())


# 全局会话管理器实例
session_manager = SessionManager()
