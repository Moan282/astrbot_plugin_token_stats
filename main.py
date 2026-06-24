from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register(
    "astrbot_plugin_token_stats",
    "Moan282",
    "显示每次请求的Token消耗详情（输入/输出/缓存命中）",
    "1.0.0",
    "https://github.com/Moan282/astrbot_plugin_token_stats"
)
class TokenStatsPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("✅ Token统计插件已加载")

    @filter.on_message()
    async def on_message(self, event: AstrMessageEvent):
        # 等待正常的消息处理流程完成，获取响应结果
        result = await event.continue_session()
        
        # 从结果中提取Token使用情况
        token_usage = getattr(result, 'token_usage', None)
        if token_usage:
            # 提取数据，未命中的缓存即为常规输入token
            input_tokens = getattr(token_usage, 'prompt_tokens', 0)
            output_tokens = getattr(token_usage, 'completion_tokens', 0)
            cached_tokens = getattr(token_usage, 'prompt_cache_hit_tokens', 0)
            uncached_tokens = input_tokens - cached_tokens
            
            stats_msg = (
                f"📊 **本次Token消耗**\n"
                f"• 输入总计: {input_tokens}\n"
                f"  - ✅ 缓存命中: {cached_tokens}\n"
                f"  - ❌ 未命中: {uncached_tokens}\n"
                f"• 输出总计: {output_tokens}\n"
                f"• 合计: {input_tokens + output_tokens}"
            )
            # 发送统计信息
            yield event.make_result().message(stats_msg)
        else:
            # 如果无法获取Token信息，静默退出，不干扰正常回复
            pass