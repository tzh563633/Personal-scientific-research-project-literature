from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from ..config import settings


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def extract_metadata(self, text: str, filename: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def generate_review(self, framework: str, sources: list[dict[str, Any]]) -> str:
        raise NotImplementedError


class MockLLMProvider(LLMProvider):
    name = "mock"

    def extract_metadata(self, text: str, filename: str) -> dict[str, Any]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title = _pick_title(lines, filename)
        year = None
        for token in text.split():
            if token.isascii() and token.isdigit() and len(token) == 4 and 1900 <= int(token) <= 2100:
                year = int(token)
                break
        abstract = ""
        lowered = text.lower()
        for marker in ("abstract", "摘要"):
            index = lowered.find(marker.lower())
            if index >= 0:
                abstract = text[index + len(marker) : index + len(marker) + 1200].strip()
                break
        return {
            "title": title,
            "authors": "",
            "year": year,
            "doi": "",
            "abstract": abstract,
            "core_topics": "",
            "secondary_topics": "",
            "innovation_points": "",
            "provider": self.name,
        }

    def generate_review(self, framework: str, sources: list[dict[str, Any]]) -> str:
        sections = [
            "# 文献综述",
            "",
            "## 综述框架",
            framework.strip(),
            "",
            "## 已核实文献",
        ]
        if not sources:
            sections.append("当前没有可核实的文献来源。")
        else:
            for index, source in enumerate(sources, 1):
                title = source.get("title") or "未命名文献"
                citation = source.get("citation") or title
                sections.append(f"{index}. {title}。{citation}")
        sections.extend(
            [
                "",
                "> 本稿由 Mock Provider 生成。配置真实模型后，将使用相同结构替换生成器。",
            ]
        )
        return "\n".join(sections)


def _pick_title(lines: list[str], filename: str) -> str:
    if not lines:
        return filename.rsplit(".", 1)[0]
    excluded_prefixes = (
        "中图分类号",
        "分类号",
        "学校代码",
        "专业代码",
        "论文编号",
        "学科分类号",
        "研究生学号",
        "文献标识码",
        "文章编号",
        "作者姓名",
        "作者：",
        "作者:",
        "姓名：",
        "姓名:",
        "专业名称",
        "研究方向",
        "导师姓名",
        "导师：",
        "导师:",
        "引用格式",
        "收稿日期",
        "修回日期",
        "题目：",
        "题目:",
        "题名：",
        "题名:",
    )
    window = lines[:60]
    cutoff = len(window)
    boundary_prefixes = (
        "摘要",
        "摘 要",
        "［摘",
        "[摘",
        "abstract",
        "keywords",
        "关键词",
        "参考文献",
        "references",
        "筛选说明",
        "作者姓名",
        "作者：",
        "作者:",
        "姓名：",
        "姓名:",
        "收稿日期",
        "引用格式",
    )
    for index, line in enumerate(window):
        compact = re.sub(r"\s+", "", line)
        if compact in {"摘", "要"} or compact.lower().startswith(
            tuple(item.lower() for item in boundary_prefixes)
        ):
            cutoff = index
            break

    has_cjk = any("\u3400" <= character <= "\u9fff" for line in window[:cutoff] for character in line)
    candidates: list[tuple[int, int, str]] = []
    for index, line in enumerate(window[:cutoff]):
        compact = re.sub(r"\s+", "", line).strip("*􀆽")
        if len(compact) < 8 or len(compact) > 160:
            continue
        if compact.startswith(excluded_prefixes) or compact.startswith(
            ("第", "Vol.", "No.", "ISSN", "CN ", "——", "—", "-")
        ):
            continue
        if has_cjk and not any("\u3400" <= character <= "\u9fff" for character in compact):
            continue
        if any(marker in compact for marker in ("学院", "研究中心", "研究所", "（", "(", "地址")):
            continue
        if compact.lower().startswith(("abstract", "keywords", "摘要", "关键词", "摘 要")):
            continue
        if compact.startswith(("一、", "二、", "三、", "四、", "1.", "2.")):
            continue
        if compact.isdigit() or compact.isupper() and not any("\u3400" <= char <= "\u9fff" for char in compact):
            continue
        score = min(len(compact), 80)
        score += sum(
            12
            for keyword in (
                "数字",
                "韧性",
                "城市",
                "区域",
                "经济",
                "技术",
                "生态",
                "平台",
                "治理",
                "矿业",
                "研究",
                "路径",
                "框架",
                "影响",
                "机制",
            )
            if keyword in compact
        )
        score -= index
        candidates.append((score, index, compact))
    if not candidates:
        return lines[0][:500]
    _, index, title = max(candidates)
    if index + 1 < len(lines):
        continuation = re.sub(r"\s+", "", lines[index + 1]).strip("*􀆽")
        if continuation.startswith(("——", "—", "-", "架构", "实现", "路径", "体系", "发展")):
            title = f"{title}{continuation}"
    return title[:500]


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, name: str, base_url: str, api_key: str, model: str):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def _chat(self, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError(f"{self.name} API key is not configured")
        endpoint = (
            f"{self.base_url}/chat/completions"
            if self.base_url.endswith("/v1")
            else f"{self.base_url}/v1/chat/completions"
        )
        response = httpx.post(
            endpoint,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "temperature": 0.1,
                "messages": [
                    {"role": "system", "content": "Return valid JSON when the prompt asks for JSON."},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def extract_metadata(self, text: str, filename: str) -> dict[str, Any]:
        prompt = (
            "Extract title, authors, year, doi, abstract, core_topics, "
            "secondary_topics and innovation_points from this paper. "
            "Return JSON only. filename="
            f"{filename}\n{text[:30000]}"
        )
        raw = self._chat(prompt)
        return json.loads(raw)

    def generate_review(self, framework: str, sources: list[dict[str, Any]]) -> str:
        prompt = f"Write a cited Markdown literature review using only these sources.\nFramework:\n{framework}\nSources:\n{json.dumps(sources, ensure_ascii=False)}"
        return self._chat(prompt)


def get_provider() -> LLMProvider:
    providers: dict[str, LLMProvider] = {
        "mock": MockLLMProvider(),
        "deepseek": OpenAICompatibleProvider(
            "deepseek", settings.deepseek_base_url, settings.deepseek_api_key, settings.deepseek_model
        ),
        "qwen": OpenAICompatibleProvider("qwen", settings.qwen_base_url, settings.qwen_api_key, settings.qwen_model),
        "kimi": OpenAICompatibleProvider("kimi", settings.kimi_base_url, settings.kimi_api_key, settings.kimi_model),
    }
    selected = settings.default_llm.lower()
    provider = providers.get(selected, providers["mock"])
    if selected != "mock" and not getattr(provider, "api_key", ""):
        return providers["mock"]
    return provider
