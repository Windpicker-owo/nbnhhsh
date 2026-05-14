"""nbnhhsh 插件 - 能不能好好说话。

提供首字母缩写翻译工具，通过调用「能不能好好说话」API
查询中文网络缩写（如 yyds、xswl）所对应的完整含义。
"""

from __future__ import annotations

from typing import Annotated

import httpx

from src.app.plugin_system.api.log_api import get_logger
from src.core.components.base import BasePlugin
from src.core.components.base.tool import BaseTool
from src.core.components.loader import register_plugin

logger = get_logger("nbnhhsh")

# nbnhhsh API 地址
_API_URL = "https://lab.magiconch.com/api/nbnhhsh/guess"


class NbnhhshTool(BaseTool):
    """首字母缩写翻译工具。

    调用「能不能好好说话」开放 API，将网络上常见的首字母缩写（如
    yyds、xswl、nbcs 等）翻译成对应的中文含义。

    Examples:
        >>> tool = NbnhhshTool(plugin)
        >>> ok, result = await tool.execute("yyds")
        >>> # result -> "yyds：永远的神"
    """

    tool_name = "nbnhhsh"
    tool_description = (
        "查询中文网络首字母缩写的含义。"
        "例如 yyds（永远的神）、xswl（笑死我了）、nbcs（你不出声）等。"
        "输入一个或多个以英文逗号分隔的缩写词，返回对应的中文解释。"
    )

    async def execute(
        self,
        abbreviations: Annotated[
            str,
            "要查询的缩写词，多个词之间用英文逗号分隔，例如 'yyds' 或 'yyds,xswl'",
        ],
    ) -> tuple[bool, str]:
        """查询网络缩写含义。

        Args:
            abbreviations: 要查询的缩写词，多个词之间用英文逗号分隔

        Returns:
            tuple[bool, str]: (是否成功, 查询结果描述)
        """
        # 提取所有由字母和数字组成、长度 >= 2 的词
        import re

        tokens = re.findall(r"[a-z0-9]{2,}", abbreviations, flags=re.IGNORECASE)
        if not tokens:
            return False, "未检测到有效的缩写（缩写应由至少 2 个英文字母或数字组成）"

        text = ",".join(tokens)
        logger.debug(f"查询缩写：{text}")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    _API_URL,
                    json={"text": text},
                    headers={"content-type": "application/json"},
                )
                response.raise_for_status()
                data: list[dict] = response.json()
        except httpx.TimeoutException:
            logger.warning("nbnhhsh API 请求超时")
            return False, "查询超时，请稍后再试"
        except httpx.HTTPStatusError as e:
            logger.warning(f"nbnhhsh API 返回错误状态码：{e.response.status_code}")
            return False, f"API 请求失败（HTTP {e.response.status_code}）"
        except Exception as e:
            logger.error(f"nbnhhsh API 请求异常：{e}")
            return False, f"查询失败：{e}"

        if not data:
            return False, f"未找到关于「{abbreviations}」的记录"

        lines: list[str] = []
        for item in data:
            name: str = item.get("name", "")
            trans: list[str] | None = item.get("trans")
            inputting: list[str] = item.get("inputting") or []

            if trans:
                # 解析翻译条目，去除来源括号注释后拼接
                parsed = _parse_trans(trans)
                trans_str = "、".join(parsed)
                lines.append(f"{name}：{trans_str}")
            elif trans is None:
                lines.append(f"{name}：暂无对应含义")
            elif inputting:
                # 仅有拼音输入候选，尚未录入
                candidates = "、".join(inputting)
                lines.append(f"{name}（可能是：{candidates}）：尚未收录")
            else:
                lines.append(f"{name}：尚未收录")

        return True, "\n".join(lines)


def _parse_trans(trans: list[str]) -> list[str]:
    """解析翻译列表，提取正文部分（去除来源注释）。

    Args:
        trans: 原始翻译列表，条目格式可能为 "含义（来源）"

    Returns:
        list[str]: 处理后的含义列表
    """
    import re

    result: list[str] = []
    for item in trans:
        match = re.match(r"^(.+?)([（(].+?[）)])?$", item)
        if match:
            result.append(match.group(1).strip())
        else:
            result.append(item.strip())
    return result


# ─── Plugin ─────────────────────────────────────────────────


@register_plugin
class NbnhhshPlugin(BasePlugin):
    """nbnhhsh 插件 - 能不能好好说话缩写翻译"""

    plugin_name = "nbnhhsh"
    plugin_version = "1.0.0"
    plugin_author = "MoFox Team"
    plugin_description = (
        "能不能好好说话 - 首字母缩写翻译工具，"
        "通过调用 nbnhhsh API 查询中文网络缩写的含义"
    )

    def get_components(self) -> list[type]:
        """获取插件内所有组件类。

        Returns:
            list[type]: 插件内所有组件类的列表
        """
        return [NbnhhshTool]
