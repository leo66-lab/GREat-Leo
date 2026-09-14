from __future__ import annotations

import csv
import re
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .config import BACKUP_DIR, BASE_REVIEW_INTERVALS, DB_PATH
from . import repository as repo


class DuplicateWordError(ValueError):
    """Raised when a caller asked not to create another sense for an existing word."""


SIMPLE_IMPORT_HEADERS = {
    "word",
    "english_word",
    "英文单词",
    "单词",
    "meaning_cn",
    "core_meaning_cn",
    "中文释义",
    "中文义",
    "part_of_speech",
    "pos",
    "词性",
    "meaning_en",
    "core_meaning_en",
    "英文释义",
    "英文义",
    "root",
    "word_root",
    "词根",
}


def create_simple_word_entry(
    *,
    word: str,
    core_meaning_cn: str,
    part_of_speech: str,
    core_meaning_en: str,
    word_root: str,
) -> dict[str, Any]:
    word_text = repo.clean_text(word)
    meaning_cn = repo.clean_text(core_meaning_cn)
    pos = repo.clean_text(part_of_speech)
    meaning_en = repo.clean_text(core_meaning_en)
    root = repo.clean_text(word_root)
    if not word_text:
        raise ValueError("英文单词不能为空。")
    if not meaning_cn:
        raise ValueError("中文释义不能为空。")
    if not pos:
        raise ValueError("词性不能为空。")
    if not meaning_en:
        raise ValueError("英文释义不能为空。")
    if not root:
        raise ValueError("词根不能为空。")

    word_id, word_created = repo.get_or_create_word(word_text)
    synonym_key = repo.derive_synonym_key(meaning_cn)
    root_key = repo.derive_root_key(word_text, root)
    existing_senses = repo.list_senses(word_id=word_id)
    if existing_senses:
        merged = repo.merge_senses_for_word(
            word_id,
            {
                "part_of_speech": pos,
                "core_meaning_cn": meaning_cn,
                "core_meaning_en": meaning_en,
                "word_root": root,
                "root_key": root_key,
                "synonym_key": synonym_key,
            },
        )
        return {
            "word_id": word_id,
            "sense_id": int(merged["sense_id"] if merged else existing_senses[0]["id"]),
            "word_created": word_created,
            "created": False,
            "updated": True,
            "merged": len(existing_senses) > 1,
        }

    sense_id = repo.create_word_sense(
        word_id,
        part_of_speech=pos,
        core_meaning_cn=meaning_cn,
        core_meaning_en=meaning_en,
        word_root=root,
        root_key=root_key,
        synonym_key=synonym_key,
        familiarity=0,
        status="learning",
        review_status="learning",
        next_review_date=date.today().isoformat(),
    )
    return {
        "word_id": word_id,
        "sense_id": sense_id,
        "word_created": word_created,
        "created": True,
        "updated": False,
        "merged": False,
    }


def _split_simple_import_line(line: str) -> list[str]:
    if "\t" in line:
        return [part.strip() for part in line.split("\t")]
    if "|" in line:
        return [part.strip() for part in line.split("|")]
    return [part.strip() for part in next(csv.reader([line]))]


def _looks_like_simple_header(parts: list[str]) -> bool:
    normalized = {part.strip().lower() for part in parts}
    return len(normalized & SIMPLE_IMPORT_HEADERS) >= 3


def batch_import_simple_words(raw_text: str) -> dict[str, Any]:
    created: list[dict[str, Any]] = []
    updated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    lines = [line.strip() for line in (raw_text or "").splitlines() if line.strip()]

    for line_number, line in enumerate(lines, 1):
        parts = _split_simple_import_line(line)
        if line_number == 1 and _looks_like_simple_header(parts):
            continue
        if len(parts) < 5:
            skipped.append({"line": line_number, "word": parts[0] if parts else "", "reason": "字段不足"})
            continue
        word, meaning_cn, pos, meaning_en, root = parts[:5]
        try:
            result = create_simple_word_entry(
                word=word,
                core_meaning_cn=meaning_cn,
                part_of_speech=pos,
                core_meaning_en=meaning_en,
                word_root=root,
            )
            row = {"line": line_number, "word": word, "sense_id": result["sense_id"]}
            if result["updated"]:
                updated.append(row)
            else:
                created.append(row)
        except Exception as exc:  # noqa: BLE001 - imports should report every bad row.
            skipped.append({"line": line_number, "word": word, "reason": str(exc)})

    return {
        "seen": len(lines),
        "created": created,
        "updated": updated,
        "skipped": skipped,
    }


def _category_from_names(
    level1_name: str = "",
    level1_name_en: str = "",
    level2_name: str = "",
    level2_name_en: str = "",
) -> tuple[int | None, int | None]:
    level1_id = repo.get_or_create_category(1, level1_name, level1_name_en) if (level1_name or level1_name_en) else None
    level2_id = None
    if level2_name or level2_name_en:
        level2_id = repo.get_or_create_category(2, level2_name, level2_name_en, parent_id=level1_id)
    return level1_id, level2_id


def create_word_entry(
    *,
    word: str,
    part_of_speech: str = "",
    core_meaning_cn: str = "",
    core_meaning_en: str = "",
    level1_name: str = "",
    level1_name_en: str = "",
    level2_name: str = "",
    level2_name_en: str = "",
    group_name_cn: str = "",
    group_name_en: str = "",
    existing_group_id: int | None = None,
    group_definition: str = "",
    semantic_axis: str = "",
    axis_enabled: bool = False,
    axis_name: str = "",
    low_label: str = "",
    high_label: str = "",
    nuance: str = "",
    common_collocations: str = "",
    usage_register: str = "",
    antonyms: str = "",
    gre_sentence: str = "",
    source: str = "",
    personal_note: str = "",
    familiarity: int = 0,
    duplicate_mode: str = "new_sense",
) -> dict[str, Any]:
    word_text = repo.clean_text(word)
    if not word_text:
        raise ValueError("Word is required.")

    existing = repo.get_word_by_text(word_text)
    if existing and duplicate_mode == "reject":
        raise DuplicateWordError("This word already exists.")

    word_id, word_created = repo.get_or_create_word(word_text)
    sense_status = "pending" if not repo.clean_text(core_meaning_cn) and not repo.clean_text(core_meaning_en) else "learning"
    sense_id = repo.create_word_sense(
        word_id,
        part_of_speech=part_of_speech,
        core_meaning_cn=core_meaning_cn or "Pending",
        core_meaning_en=core_meaning_en or "Pending",
        nuance=nuance,
        common_collocations=common_collocations,
        usage_register=usage_register,
        example_sentence=gre_sentence,
        antonyms=antonyms,
        usage_notes=personal_note,
        familiarity=familiarity,
        status=sense_status,
        next_review_date=date.today().isoformat(),
    )

    group_id = existing_group_id
    if group_id:
        repo.add_membership(
            sense_id,
            group_id,
            typicality="core",
            strength_level=str(familiarity),
            notes=personal_note,
        )
    elif repo.clean_text(group_name_cn) or repo.clean_text(group_name_en):
        level1_id, level2_id = _category_from_names(level1_name, level1_name_en, level2_name, level2_name_en)
        group_id = repo.get_or_create_group(
            group_name_cn=group_name_cn,
            group_name_en=group_name_en,
            level1_id=level1_id,
            level2_id=level2_id,
            group_definition=group_definition,
            semantic_axis=semantic_axis,
            axis_enabled=axis_enabled,
            axis_name=axis_name,
            low_label=low_label,
            high_label=high_label,
        )
        if group_id:
            repo.add_membership(
                sense_id,
                group_id,
                typicality="core",
                strength_level=str(familiarity),
                notes=personal_note,
            )

    question_id = None
    if repo.clean_text(gre_sentence) or repo.clean_text(source):
        question_id = repo.create_question(
            question_type="Context",
            source=source,
            question_text=gre_sentence or f"Context for {word_text}",
            correct_answer=word_text,
            explanation=personal_note,
            logic_structure="Vocabulary context",
        )
        repo.link_sense_question(
            sense_id=sense_id,
            question_id=question_id,
            role="context vocabulary",
            context_sentence=gre_sentence,
            personal_note=personal_note,
        )

    return {
        "word_id": word_id,
        "word_created": word_created,
        "sense_id": sense_id,
        "group_id": group_id,
        "question_id": question_id,
    }


def attach_existing_sense_to_group(
    *,
    sense_id: int,
    group_name_cn: str,
    group_name_en: str = "",
    level1_name: str = "",
    level1_name_en: str = "",
    level2_name: str = "",
    level2_name_en: str = "",
    typicality: str = "",
    strength_level: str = "",
    axis_position: int | None = None,
    notes: str = "",
) -> int | None:
    level1_id, level2_id = _category_from_names(level1_name, level1_name_en, level2_name, level2_name_en)
    group_id = repo.get_or_create_group(
        group_name_cn=group_name_cn,
        group_name_en=group_name_en,
        level1_id=level1_id,
        level2_id=level2_id,
    )
    if not group_id:
        return None
    repo.add_membership(
        sense_id=sense_id,
        group_id=group_id,
        typicality=typicality,
        strength_level=strength_level,
        axis_position=axis_position,
        notes=notes,
    )
    return group_id


def batch_add_words(raw_text: str) -> dict[str, Any]:
    tokens = [
        item.strip()
        for item in re.split(r"[\n,;，；]+", raw_text or "")
        if item.strip()
    ]
    created = []
    skipped = []
    for token in tokens:
        word = token.split()[0].strip()
        if not word:
            continue
        word_id, word_created = repo.get_or_create_word(word)
        existing_pending = repo.find_sense_by_word_meaning(word_id, "Pending", "Pending")
        if word_created or not existing_pending:
            sense_id = repo.create_word_sense(
                word_id,
                part_of_speech="Pending",
                core_meaning_cn="Pending",
                core_meaning_en="Pending",
                status="pending",
                review_status="pending",
            )
            created.append({"word": word, "sense_id": sense_id})
        else:
            skipped.append({"word": word, "reason": "already exists"})
    return {"seen": len(tokens), "created": created, "skipped": skipped}


def next_review_for_rating(current_familiarity: int, rating: str) -> tuple[int, str, int]:
    rating_normalized = repo.clean_text(rating).lower()
    familiarity = repo.clamp_familiarity(current_familiarity)
    wrong_delta = 0

    if rating_normalized == "again":
        familiarity = max(0, familiarity - 1)
        interval = 1
        wrong_delta = 1
    elif rating_normalized == "hard":
        interval = max(1, BASE_REVIEW_INTERVALS.get(familiarity, 1) // 2)
    elif rating_normalized == "easy":
        familiarity = min(4, familiarity + 2)
        interval = BASE_REVIEW_INTERVALS.get(familiarity, 21)
    else:
        familiarity = min(4, familiarity + 1)
        interval = BASE_REVIEW_INTERVALS.get(familiarity, 3)

    next_date = date.today() + timedelta(days=interval)
    return familiarity, next_date.isoformat(), wrong_delta


def apply_review_result(sense_id: int, mode: str, rating: str, note: str = "") -> dict[str, Any]:
    sense = repo.get_sense(sense_id)
    if not sense:
        raise ValueError("Word sense not found.")
    new_familiarity, next_review_date, wrong_delta = next_review_for_rating(int(sense["familiarity"]), rating)
    repo.record_review(
        sense_id=sense_id,
        mode=mode,
        rating=rating,
        familiarity_after=new_familiarity,
        next_review_date=next_review_date,
        wrong_delta=wrong_delta,
        note=note,
    )
    return {
        "familiarity": new_familiarity,
        "next_review_date": next_review_date,
        "wrong_delta": wrong_delta,
    }


def backup_database() -> Path:
    if not DB_PATH.exists():
        raise FileNotFoundError("Database file does not exist yet.")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    target = BACKUP_DIR / f"gre_vocab_{timestamp}.db"
    shutil.copy2(DB_PATH, target)
    return target


def seed_sample_data() -> dict[str, int]:
    repo.ensure_bootstrap_data()
    created_senses = 0
    linked_memberships = 0

    groups = [
        {
            "level1_en": "Decrease",
            "level1_cn": "减少",
            "level2_cn": "缓解",
            "group_cn": "缓解负面影响",
            "group_en": "mitigate negative effects",
            "definition": "make a harmful condition, effect, or severity less serious",
            "axis": "moderate -> mitigate -> alleviate -> eliminate",
            "axis_enabled": True,
            "axis_name": "减少程度",
            "low_label": "温和",
            "high_label": "彻底",
            "words": [
                ("mitigate", "v.", "缓解；减轻负面影响", "make something less severe or serious", "强调降低坏影响或严重性，常接 damage/effects/risk。", "mitigate damage; mitigate effects", 2),
                ("alleviate", "v.", "减轻痛苦、问题或压力", "reduce pain, difficulty, or severity", "常用于 pain, suffering, poverty, symptoms；语气比 mitigate 更偏痛苦减轻。", "alleviate suffering; alleviate symptoms", 3),
                ("ameliorate", "v.", "改善不良状况", "make a bad situation better", "强调状态被改善，较正式，常用于 social/economic conditions。", "ameliorate conditions", 4),
                ("palliate", "v.", "暂时缓和；治标不治本", "make a problem seem less serious without fixing it", "常含只缓解表面症状、未解决根因。", "palliate symptoms", 1),
            ],
        },
        {
            "level1_en": "Emotion",
            "level1_cn": "情绪",
            "level2_cn": "安抚",
            "group_cn": "安抚愤怒",
            "group_en": "soothe anger",
            "definition": "calm someone's anger or reduce hostility",
            "axis": "placate -> mollify -> appease -> pacify",
            "axis_enabled": True,
            "axis_name": "安抚强度",
            "low_label": "轻度安抚",
            "high_label": "恢复平静",
            "words": [
                ("placate", "v.", "安抚；使息怒", "make someone less angry", "常指通过让步或行动使对方不再生气。", "placate critics; placate a crowd", 1),
                ("appease", "v.", "安抚；姑息", "pacify by giving concessions", "可能带有以让步换取平息的含义，有时偏负面。", "appease opponents", 2),
                ("mollify", "v.", "缓和怒气或焦虑", "soothe someone's anger or anxiety", "语气较柔和，强调情绪被软化。", "mollify concerns", 3),
                ("pacify", "v.", "平息；使平静", "bring peace or calm to", "可用于人群、地区或冲突，强调整体恢复平静。", "pacify unrest", 4),
            ],
        },
        {
            "level1_en": "Character",
            "level1_cn": "性格",
            "level2_cn": "固执",
            "group_cn": "固执 / 不愿改变",
            "group_en": "stubborn unwillingness to change",
            "definition": "refuse to change an opinion, attitude, or course of action",
            "axis": "stubborn -> obstinate -> obdurate -> intransigent",
            "axis_enabled": True,
            "axis_name": "妥协意愿",
            "low_label": "普通固执",
            "high_label": "拒绝妥协",
            "words": [
                ("stubborn", "adj.", "固执的", "unwilling to change one's mind", "最普通的固执，可中性也可负面。", "stubborn refusal", 1),
                ("obstinate", "adj.", "顽固的；不听劝的", "stubbornly refusing to change", "比 stubborn 更强调不听劝、难以说服。", "obstinate resistance", 2),
                ("obdurate", "adj.", "顽固且难以感化的", "stubbornly resistant to persuasion or moral influence", "强调硬心肠、难被说服或感化，常有道德评价。", "obdurate refusal", 3),
                ("intransigent", "adj.", "拒绝妥协的", "unwilling to compromise", "强调谈判或立场中不让步。", "intransigent stance", 4),
            ],
        },
        {
            "level1_en": "Support",
            "level1_cn": "支持",
            "level2_cn": "证实",
            "group_cn": "证实 / 提供证据",
            "group_en": "confirm with evidence",
            "definition": "show that a claim is true or well-supported",
            "axis": "verify -> validate -> corroborate -> substantiate",
            "axis_enabled": True,
            "axis_name": "证据支撑强度",
            "low_label": "确认",
            "high_label": "充分证据",
            "words": [
                ("corroborate", "v.", "佐证；以额外证据支持", "support a statement with additional evidence", "常指独立证据互相印证。", "corroborate testimony", 3),
                ("substantiate", "v.", "证实；提供实质证据", "provide evidence to support a claim", "强调拿出充分、具体的证据。", "substantiate a claim", 4),
                ("verify", "v.", "核实；确认真实性", "check or prove that something is true", "强调检查真伪或准确性。", "verify data", 1),
                ("validate", "v.", "确认有效性；使有根据", "confirm validity or soundness", "强调方法、结论、感受或资格的有效性。", "validate a theory", 2),
            ],
        },
    ]

    for group in groups:
        level1_id = repo.get_or_create_category(1, group["level1_cn"], group["level1_en"])
        level2_id = repo.get_or_create_category(2, group["level2_cn"], "", parent_id=level1_id)
        group_id = repo.get_or_create_group(
            group_name_cn=group["group_cn"],
            group_name_en=group["group_en"],
            level1_id=level1_id,
            level2_id=level2_id,
            group_definition=group["definition"],
            semantic_axis=group["axis"],
            axis_enabled=group["axis_enabled"],
            axis_name=group["axis_name"],
            low_label=group["low_label"],
            high_label=group["high_label"],
        )
        for order, (word, pos, meaning_cn, meaning_en, nuance, collocations, axis_position) in enumerate(group["words"], 1):
            word_id, _ = repo.get_or_create_word(word)
            existing_sense = repo.find_sense_by_word_meaning(word_id, meaning_cn, pos)
            if existing_sense:
                sense_id = int(existing_sense["id"])
            else:
                sense_id = repo.create_word_sense(
                    word_id,
                    part_of_speech=pos,
                    core_meaning_cn=meaning_cn,
                    core_meaning_en=meaning_en,
                    nuance=nuance,
                    common_collocations=collocations,
                    status="learning",
                    familiarity=axis_position - 1 if axis_position < 4 else 3,
                    next_review_date=date.today().isoformat(),
                )
                created_senses += 1
            if group_id:
                repo.add_membership(
                    sense_id=sense_id,
                    group_id=group_id,
                    typicality="core",
                    strength_level=str(axis_position),
                    axis_position=axis_position,
                    display_order=order,
                    notes=nuance,
                )
                linked_memberships += 1

    question_text = (
        "Nordhaus predicts that in the future we will increasingly be managing ecological "
        "problems like global warming rather than solving them."
    )
    existing_question = repo.fetch_one(
        "SELECT id FROM gre_questions WHERE question_text = ?",
        (question_text,),
    )
    if existing_question:
        question_id = int(existing_question["id"])
    else:
        question_id = repo.create_question(
            question_type="TC",
            source="Seed GRE-style example",
            question_text=question_text,
            correct_answer="managing / mitigating",
            explanation="mitigate and alleviate fit reducing harmful effects; solve implies full elimination.",
            logic_structure="Contrast between managing effects and fully solving a problem.",
            options=[
                {"option_text": "mitigating", "is_correct": True, "explanation": "Matches reducing harmful effects."},
                {"option_text": "alleviating", "is_correct": True, "explanation": "Close synonym for reducing negative effects."},
                {"option_text": "transcending", "is_correct": False, "explanation": "Means going beyond, not managing a concrete problem."},
                {"option_text": "solving", "is_correct": False, "explanation": "Too complete for the sentence's managing logic."},
            ],
        )
    for word in ["mitigate", "alleviate"]:
        word_row = repo.get_word_by_text(word)
        if not word_row:
            continue
        senses = repo.list_senses(int(word_row["id"]))
        if senses:
            repo.link_sense_question(
                sense_id=int(senses[0]["id"]),
                question_id=question_id,
                role="correct answer",
                context_sentence=question_text,
                personal_note="mitigate ≈ alleviate effects; solve is too absolute.",
            )

    return {"created_senses": created_senses, "linked_memberships": linked_memberships}
