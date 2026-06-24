import json
import os
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.all import event_message_type, EventMessageType

@register(
    "astrbot_plugin_token_stats",
    "Moan282",
    "显示每次请求的Token消耗详情（输入/输出/缓存命中），支持开关",
    "1.1.1",
    "https://github.com/Moan282/astrbot_plugin_token_stats"
)
class TokenStatsPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.config_path = os.path.join(os.path.dirname(__file__), "config.json")
        self.enabled = self._load_config()
        logger.info(f"✅ Token统计插件已加载，当前状态：{'开启' if self.enabled else '关闭'}")

    def _load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('enabled', True)
        except FileNotFoundError:
            return True
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return True

    def _save_config(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump({'enabled': self.enabled}, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    @filter.command("/token显示 开")
    async def turn_on(self, event: AstrMessageEvent):
        if self.enabled:
            yield event.make_result().message("⚙️ Token统计已处于开启状态")
            return
        self.enabled = True
        if self._save_config():
            yield event.make_result().message("✅ Token统计显示已开启")
        else:
            yield event.make_result().message("❌ 开启失败，请检查日志")

    @filter.command("/token显示 关")
    async def turn_off(self, event: AstrMessageEvent):
        if not self.enabled:
            yield event.make_result().message("⚙️ Token统计已处于关闭状态")
            return
        self.enabled = False
        if self._save_config():
            yield event.make_result().message("✅ Token统计显示已关闭")
        else:
            yield event.make_result().message("❌ 关闭失败，请检查日志")

    @event_message_type(EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        # 如果统计功能关闭，直接跳过
        if not self.enabled:
            return

        # 等待正常的消息处理流程完成，获取响应结果
        result = await event.continue_session()
        
        # 从结果中提取Token使用情况
        token_usage = getattr(result, 'token_usage', None)
        if token_usage:
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
            yield event.make_result().message(stats_msg)
        # 如果无法获取Token信息，静默退出，不干扰正常回复