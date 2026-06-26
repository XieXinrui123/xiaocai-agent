"""
LLM 客户端模块
封装通义千问(Qwen)和 DeepSeek 的调用
"""
import dashscope
from dashscope import Generation
from app.core.config import settings


class LLMClient:
    """
    大语言模型客户端
    支持多种模型切换，统一接口
    """
    
    def __init__(self):
        # 设置 API Key
        dashscope.api_key = settings.DASHSCOPE_API_KEY
    
    def _mock_reply(self, messages: list) -> str:
        """
        Mock 模式：当没有 API Key 时，根据提示词返回预设回复
        用于开发测试
        """
        # 从 messages 中提取系统提示词
        system_content = ""
        for msg in messages:
            if msg.get("role") == "system":
                system_content += msg.get("content", "")
        
        # 根据状态返回对应的 Mock 回复
        if "自我介绍" in system_content:
            return "你好！我是小财，你的资产配置顾问😊 我可以帮你规划理财方案。请问你投资主要想实现什么目标呢？比如买房、养老、还是财富增值？"
        elif "投资目标" in system_content:
            return "收到！那你的目标金额大概是多少？计划多长时间达成呢？"
        elif "风险承受" in system_content:
            return "接下来了解一下你的风险承受能力。想象一下：如果你的投资在三个月内跌了15%，你会怎么做？\n\nA. 全部卖出，保住本金\nB. 卖出一部分\nC. 继续持有，等它回升\nD. 趁机加仓，低位买入"
        elif "资金情况" in system_content:
            return "了解！这次你打算拿出多少资金来做资产配置呢？（比如 10万、50万）"
        elif "投资期限" in system_content:
            return "好的，那这笔资金你计划投资多久？期限越长，可以配置的风险资产比例就越高哦。"
        elif "量身定制" in system_content:
            return "完美！我已经了解你的情况了，正在为你生成专属的配置方案..."
        elif "解释配置逻辑" in system_content:
            return "（此处会显示资产配置方案的详细解释，接入 LLM 后自动生产）"
        elif "持续陪伴" in system_content:
            return "方案已保存！我会定期关注市场变化，在需要再平衡时提醒你。有什么其他问题随时问我！"
        
        return "好的，我明白了。请继续告诉我更多信息。"
    
    def chat(self, messages: list, model: str = None, temperature: float = 0.7) -> str:
        """
        通用对话接口
        
        Args:
            messages: 对话历史，格式 [{"role": "system"|"user"|"assistant", "content": "..."}]
            model: 指定模型，默认用主模型(qwen-max)
            temperature: 创造性参数，0-1，越高越有创意
        
        Returns:
            LLM 生成的文本回复
        """
        # 检查是否是 Mock 模式（API Key 是占位符）
        if not settings.DASHSCOPE_API_KEY or settings.DASHSCOPE_API_KEY == "your-api-key-here":
            print("[Mock Mode] 使用预设回复（请在 .env 中配置真实 API Key）")
            return self._mock_reply(messages)
        
        # 默认使用主模型
        if model is None:
            model = settings.LLM_MODEL_MAIN
        
        try:
            # 调用通义千问
            response = Generation.call(
                model=model,
                messages=messages,
                temperature=temperature,
                result_format="message",  # 返回标准 message 格式
            )
            
            # 检查是否成功
            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                print(f"LLM 调用失败: {response.message}")
                return "抱歉，我暂时遇到了问题，请稍后再试。"
                
        except Exception as e:
            print(f"LLM 调用异常: {e}")
            return "服务暂时不可用，请稍后再试。"
    
    def simple_chat(self, user_message: str, system_prompt: str = "") -> str:
        """
        简化版对话 - 单轮对话
        
        Args:
            user_message: 用户输入
            system_prompt: 系统提示词（可选）
        
        Returns:
            LLM 回复
        """
        messages = []
        
        # 如果有系统提示，先加入
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # 加入用户消息
        messages.append({"role": "user", "content": user_message})
        
        return self.chat(messages)


# 全局 LLM 客户端实例（单例模式）
llm_client = LLMClient()
