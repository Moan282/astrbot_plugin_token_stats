from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.message.components import Plain
from astrbot.core.provider.entites import ProviderRequest, LLMResponse

@register(
    "TokenStats",
    "Moan282",
    "显示Token消耗详情（含缓存命中），支持开关",
    "1.3.0",
    "https://github.com/Moan282/astrbot_plugin_token_stats"
)
class TokenStatsPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.enabled = True          # 默认开启
        self.token_msg = ""          # 存储待追加的Token信息
        self.llm_responded = False   # 标记是否收到LLM响应

    @filter.command("/token显示 开")
    async def turn_on(self, event: AstrMessageEvent):
        if self.enabled:
            yield event.plain_result("⚙️ Token统计已处于开启状态")
        else:
            self.enabled = True
            yield event.plain_result("✅ Token统计显示已开启")

    @filter.command("/token显示 关")
    async def turn_off(self, event: AstrMessageEvent):
        if not self.enabled:
            yield event.plain_result("⚙️ Token统计已处于关闭状态")
        else:
            self.enabled = False
            yield event.plain_result("✅ Token统计显示已关闭")

    @filter.on_llm_response()
    async def on_llm_resp(self, event: AstrMessageEvent, resp: LLMResponse):
        """在LLM响应后提取Token数据"""
        if not self.enabled:
            return

        try:
            completion = resp.raw_completion
            if completion is None or not hasattr(completion, 'usage'):
                self.token_msg = "⚠️ 无法获取Token用量（提供商未返回）"
                self.llm_responded = True
                return

            usage = completion.usage
            if usage is None:
                self.token_msg = "⚠️ 无法获取Token用量（提供商未返回）"
                self.llm_responded = True
                return

            # 提取基础数据
            input_tokens = getattr(usage, 'prompt_tokens', 0)
            output_tokens = getattr(usage, 'completion_tokens', 0)
            total_tokens = getattr(usage, 'total_tokens', input_tokens + output_tokens)

            # 提取缓存命中数据（如果存在）
            cached_tokens = getattr(usage, 'prompt_cache_hit_tokens', 0)
            miss_tokens = getattr(usage, 'prompt_cache_miss_tokens', 0)

            # 如果提供商没有细分缓存，则用输入总计减去命中（可能为0）
            if cached_tokens == 0 and miss_tokens == 0:
                # 尝试另一种字段名（部分提供商使用 cached_tokens）
                cached_tokens = getattr(usage, 'cached_tokens', 0)
                miss_tokens = input_tokens - cached_tokens

            # 构造统计信息
            stats = (
                f"📊 Token消耗\n"
                f"• 输入总计: {input_tokens}\n"
            )
            if cached_tokens > 0 or miss_tokens > 0:
                stats += f"  - ✅ 缓存命中: {cached_tokens}\n"
                stats += f"  - ❌ 未命中: {miss_tokens}\n"
            else:
                stats += f"  - (提供商未返回缓存细分)\n"
            stats += f"• 输出总计: {output_tokens}\n"
            stats += f"• 合计: {total_tokens}"

            self.token_msg = stats
            self.llm_responded = True

        except Exception as e:
            logger.error(f"Token统计插件处理LLM响应时出错: {e}")
            self.token_msg = "⚠️ Token统计插件内部错误"
            self.llm_responded = True

    @filter.on_decorating_result()
    async def on_decorating_result(self, event: AstrMessageEvent):
        """在最终消息发送前追加Token信息"""
        if self.enabled and self.llm_responded and self.token_msg:
            try:
                result = event.get_result()
                if result and result.chain:
                    result.chain.append(Plain(f"\n{self.token_msg}"))
                self.llm_responded = False  # 重置标记，避免重复追加
                self.token_msg = ""
            except Exception as e:
                logger.error(f"追加Token信息时出错: {e}")
                raise RuntimeError("Token统计插件在回复消息时出现错误")