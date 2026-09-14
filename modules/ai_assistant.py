from __future__ import annotations

import json
import os
import re
from typing import Any

import requests

from . import repository as repo
from . import services
from .config import BASE_DIR


ENV_PATH = BASE_DIR / ".env"
DEFAULT_MODEL = "gpt-4.1-mini"
RESPONSES_URL = "https://api.openai.com/v1/responses"


VOCAB_DRAFT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "entries": {
            "type": "array",
            "maxItems": 50,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "word": {"type": "string"},
                    "part_of_speech": {"type": "string"},
                    "core_meaning_cn": {"type": "string"},
                    "core_meaning_en": {"type": "string"},
                    "level1_name": {"type": "string"},
                    "level1_name_en": {"type": "string"},
                    "level2_name": {"type": "string"},
                    "level2_name_en": {"type": "string"},
                    "synonym_group_cn": {"type": "string"},
                    "synonym_group_en": {"type": "string"},
                    "existing_group_id": {"type": "integer"},
                    "group_definition": {"type": "string"},
                    "semantic_axis": {"type": "string"},
                    "axis_enabled": {"type": "boolean"},
                    "axis_name": {"type": "string"},
                    "low_label": {"type": "string"},
                    "high_label": {"type": "string"},
                    "nuance": {"type": "string"},
                    "common_collocations": {"type": "string"},
                    "usage_register": {"type": "string"},
                    "antonyms": {"type": "string"},
                    "gre_sentence": {"type": "string"},
                    "source": {"type": "string"},
                    "personal_note": {"type": "string"},
                    "confidence": {"type": "number"},
                    "needs_review": {"type": "boolean"},
                },
                "required": [
                    "word",
                    "part_of_speech",
                    "core_meaning_cn",
                    "core_meaning_en",
                    "level1_name",
                    "level1_name_en",
                    "level2_name",
                    "level2_name_en",
                    "synonym_group_cn",
                    "synonym_group_en",
                    "existing_group_id",
                    "group_definition",
                    "semantic_axis",
                    "axis_enabled",
                    "axis_name",
                    "low_label",
                    "high_label",
                    "nuance",
                    "common_collocations",
                    "usage_register",
                    "antonyms",
                    "gre_sentence",
                    "source",
                    "personal_note",
                    "confidence",
                    "needs_review",
                ],
            },
        }
    },
    "required": ["entries"],
}


def read_local_env() -> dict[str, str]:
    settings: dict[str, str] = {}
    if not ENV_PATH.exists():
        return settings
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            settings[key] = value
    return settings


def get_api_key() -> str:
    return os.environ.get("OPENAI_API_KEY", "").strip() or read_local_env().get("OPENAI_API_KEY", "").strip()


def get_model() -> str:
    return os.environ.get("OPENAI_MODEL", "").strip() or read_local_env().get("OPENAI_MODEL", "").strip() or DEFAULT_MODEL


def has_api_key() -> bool:
    return bool(get_api_key())


def save_local_settings(api_key: str = "", model: str = "") -> None:
    updates = {
        "OPENAI_MODEL": model.strip() or DEFAULT_MODEL,
    }
    if api_key.strip():
        updates["OPENAI_API_KEY"] = api_key.strip()
    existing_lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    written_keys: set[str] = set()
    output_lines: list[str] = []

    for raw_line in existing_lines:
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", raw_line)
        if match and match.group(1) in updates:
            key = match.group(1)
            if updates[key]:
                output_lines.append(f"{key}={updates[key]}")
            written_keys.add(key)
        else:
            output_lines.append(raw_line)

    for key, value in updates.items():
        if key not in written_keys and value:
            output_lines.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(output_lines).rstrip() + "\n", encoding="utf-8")


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = repo.clean_text(value).lower()
    return text in {"1", "true", "yes", "y", "是", "启用"}


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, number))


def normalize_draft(raw: dict[str, Any]) -> dict[str, Any]:
    entry = {
        "word": repo.clean_text(raw.get("word")),
        "part_of_speech": repo.clean_text(raw.get("part_of_speech")),
        "core_meaning_cn": repo.clean_text(raw.get("core_meaning_cn")),
        "core_meaning_en": repo.clean_text(raw.get("core_meaning_en")),
        "level1_name": repo.clean_text(raw.get("level1_name")),
        "level1_name_en": repo.clean_text(raw.get("level1_name_en")),
        "level2_name": repo.clean_text(raw.get("level2_name")),
        "level2_name_en": repo.clean_text(raw.get("level2_name_en")),
        "synonym_group_cn": repo.clean_text(raw.get("synonym_group_cn") or raw.get("group_name_cn")),
        "synonym_group_en": repo.clean_text(raw.get("synonym_group_en") or raw.get("group_name_en")),
        "existing_group_id": _to_int(raw.get("existing_group_id"), 0),
        "group_definition": repo.clean_text(raw.get("group_definition")),
        "semantic_axis": repo.clean_text(raw.get("semantic_axis")),
        "axis_enabled": _to_bool(raw.get("axis_enabled")),
        "axis_name": repo.clean_text(raw.get("axis_name")),
        "low_label": repo.clean_text(raw.get("low_label")),
        "high_label": repo.clean_text(raw.get("high_label")),
        "nuance": repo.clean_text(raw.get("nuance")),
        "common_collocations": repo.clean_text(raw.get("common_collocations")),
        "usage_register": repo.clean_text(raw.get("usage_register")),
        "antonyms": repo.clean_text(raw.get("antonyms")),
        "gre_sentence": repo.clean_text(raw.get("gre_sentence")),
        "source": repo.clean_text(raw.get("source")),
        "personal_note": repo.clean_text(raw.get("personal_note")),
        "confidence": _to_float(raw.get("confidence"), 0.0),
        "needs_review": _to_bool(raw.get("needs_review")),
    }
    if entry["existing_group_id"] and not repo.get_group(entry["existing_group_id"]):
        entry["existing_group_id"] = 0
    if entry["needs_review"]:
        review_note = "AI 标记：需要人工复核。"
        entry["personal_note"] = f"{entry['personal_note']}\n{review_note}".strip()
    return entry


def existing_group_context(max_groups: int = 80, max_members: int = 6) -> str:
    groups = repo.list_groups()[:max_groups]
    context = []
    for group in groups:
        members = repo.group_members(int(group["id"]))[:max_members]
        context.append(
            {
                "id": int(group["id"]),
                "一级类别": repo.clean_text(group.get("level1_cn")) or repo.clean_text(group.get("level1_en")),
                "二级类别": repo.clean_text(group.get("level2_cn")) or repo.clean_text(group.get("level2_en")),
                "同义词组中文名": repo.clean_text(group.get("group_name_cn")),
                "同义词组英文名": repo.clean_text(group.get("group_name_en")),
                "定义": repo.clean_text(group.get("group_definition")),
                "已有成员": [repo.clean_text(member.get("word")) for member in members],
            }
        )
    return json.dumps(context, ensure_ascii=False)


def build_vocab_prompt(input_text: str, source_hint: str, max_entries: int) -> str:
    return f"""
请从下面的英文材料中抽取最多 {max_entries} 个值得长期记录的 GRE 生词，并生成可入库的词条草稿。

归纳原则：
- 优先抽取 GRE 填空、等价句、阅读和逻辑题中会影响判断的词。
- 中文字段用简洁中文；word、part_of_speech、core_meaning_en 等学习材料字段可以保留英文。
- 按语义归类，不要只按中文翻译机械分组。
- 如果某个词明显适合已有同义词组，请填写 existing_group_id；不确定时填 0，并给出新的同义词组建议。
- 若材料中有完整句子或题目语境，请放入 gre_sentence；没有就留空。
- 不要编造具体来源；如果没有来源，用给定来源标记。
- 任何把握不足、存在多义或上下文不充分的条目，把 needs_review 设为 true。

已有同义词组参考：
{existing_group_context()}

来源标记：
{source_hint or "AI 智能录入"}

英文材料：
{input_text}
""".strip()


def _extract_output_text(response_json: dict[str, Any]) -> str:
    if response_json.get("output_text"):
        return str(response_json["output_text"])

    chunks: list[str] = []
    for item in response_json.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if text:
                chunks.append(str(text))
    return "\n".join(chunks)


def _parse_json_text(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    if not cleaned.startswith("{"):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end >= start:
            cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


def generate_vocab_drafts(
    input_text: str,
    *,
    api_key: str = "",
    model: str = "",
    source_hint: str = "",
    max_entries: int = 20,
) -> list[dict[str, Any]]:
    clean_input = repo.clean_text(input_text)
    if not clean_input:
        raise ValueError("请先粘贴或上传英文材料。")

    key = api_key.strip() or get_api_key()
    if not key:
        raise ValueError("未找到 OPENAI_API_KEY。请先在页面中保存 API key，或设置系统环境变量。")

    selected_model = model.strip() or get_model()
    payload = {
        "model": selected_model,
        "instructions": (
            "你是一个严格、谨慎的 GRE 词汇整理智能体。"
            "你只返回符合 JSON schema 的对象。"
            "你的目标是帮助中文母语学习者按语义系统长期积累 GRE 词汇。"
        ),
        "input": build_vocab_prompt(clean_input, source_hint, max_entries),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "gre_vocab_drafts",
                "strict": True,
                "schema": VOCAB_DRAFT_SCHEMA,
            }
        },
        "max_output_tokens": 12000,
    }

    response = requests.post(
        RESPONSES_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )
    if response.status_code >= 400:
        try:
            message = response.json().get("error", {}).get("message", response.text)
        except ValueError:
            message = response.text
        raise RuntimeError(f"OpenAI API 请求失败：{message}")

    parsed = _parse_json_text(_extract_output_text(response.json()))
    entries = parsed.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError("智能体返回格式不正确：entries 不是列表。")
    return [normalize_draft(entry) for entry in entries if isinstance(entry, dict)]


def save_drafts(entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    saved: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for raw in entries:
        entry = normalize_draft(raw)
        if not entry["word"]:
            skipped.append({"word": "", "reason": "缺少单词"})
            continue
        try:
            result = services.create_word_entry(
                word=entry["word"],
                part_of_speech=entry["part_of_speech"],
                core_meaning_cn=entry["core_meaning_cn"],
                core_meaning_en=entry["core_meaning_en"],
                level1_name=entry["level1_name"],
                level1_name_en=entry["level1_name_en"],
                level2_name=entry["level2_name"],
                level2_name_en=entry["level2_name_en"],
                group_name_cn=entry["synonym_group_cn"],
                group_name_en=entry["synonym_group_en"],
                existing_group_id=entry["existing_group_id"] or None,
                group_definition=entry["group_definition"],
                semantic_axis=entry["semantic_axis"],
                axis_enabled=entry["axis_enabled"],
                axis_name=entry["axis_name"],
                low_label=entry["low_label"],
                high_label=entry["high_label"],
                nuance=entry["nuance"],
                common_collocations=entry["common_collocations"],
                usage_register=entry["usage_register"],
                antonyms=entry["antonyms"],
                gre_sentence=entry["gre_sentence"],
                source=entry["source"] or "AI 智能录入",
                personal_note=entry["personal_note"],
                familiarity=0,
                duplicate_mode="new_sense",
            )
            saved.append(
                {
                    "word": entry["word"],
                    "sense_id": result["sense_id"],
                    "group_id": result["group_id"],
                    "question_id": result["question_id"],
                    "confidence": entry["confidence"],
                }
            )
        except Exception as exc:  # noqa: BLE001 - Batch save should keep later rows actionable.
            skipped.append({"word": entry["word"], "reason": str(exc)})
    return {"saved": saved, "skipped": skipped}
