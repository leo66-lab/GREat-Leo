from __future__ import annotations

from datetime import date, datetime
import random
import re
from typing import Any, Iterable

from .config import DEFAULT_LEVEL_1_CATEGORIES
from .db import DB_PATH, get_connection, initialize_database, row_to_dict


SYNONYM_KEY_RULES = [
    ("减弱/削弱/缓和", ("减弱", "削弱", "缓和", "减轻", "减少", "降低", "缓解", "缓释", "消退", "衰退", "抑制")),
    ("增加/增强", ("增加", "增强", "加强", "扩大", "加剧", "提高", "促进", "激发", "放大")),
    ("支持/赞成", ("支持", "赞成", "认可", "拥护", "证成", "支撑", "有利于")),
    ("反对/批评", ("反对", "批评", "驳斥", "质疑", "谴责", "抨击", "否定")),
    ("证实/确认", ("证实", "确认", "证明", "佐证", "印证", "验证")),
    ("削弱/反驳证据", ("削弱论证", "反驳证据", "反证", "削弱证据")),
    ("简洁/精炼", ("简洁", "简短", "言简意赅", "精炼", "凝练")),
    ("冗长/啰嗦", ("冗长", "啰嗦", "繁琐", "拖沓")),
    ("清晰/明确", ("清晰", "明确", "明白", "易懂", "清楚")),
    ("模糊/晦涩", ("模糊", "晦涩", "含糊", "费解", "隐晦")),
    ("固执/顽固", ("固执", "顽固", "执拗", "不妥协")),
    ("谨慎/审慎", ("谨慎", "审慎", "小心", "慎重")),
    ("鲁莽/轻率", ("鲁莽", "轻率", "草率", "冲动")),
    ("欺骗/虚假", ("欺骗", "虚假", "伪造", "欺诈", "误导")),
    ("真实/真诚", ("真实", "真诚", "诚实", "坦率")),
    ("敌意/攻击", ("敌意", "攻击", "好斗", "挑衅", "敌对")),
    ("友好/和善", ("友好", "和善", "亲切", "温和")),
    ("重要/显著", ("重要", "显著", "重大", "突出的", "关键")),
    ("微不足道", ("微不足道", "琐碎", "无关紧要", "不重要")),
]

ROOT_KEY_RULES = [
    ("bat/bate（减弱）", ("bat", "bate")),
    ("mit/miss（送出）", ("mit", "miss")),
    ("lac/lacon（少；简短）", ("lac", "lacon")),
    ("fac/fic/fect（做）", ("fac", "fic", "fect", "fact")),
    ("ced/ceed/cess（走；让步）", ("ced", "ceed", "cess")),
    ("duc/duct（引导）", ("duc", "duct")),
    ("fer（带来）", ("fer",)),
    ("ject（投掷）", ("ject",)),
    ("pel/puls（推动）", ("pel", "puls")),
    ("scrib/script（写）", ("scrib", "script")),
    ("spect/spec/spic（看）", ("spect", "spec", "spic")),
    ("ten/tain/tin（持有）", ("ten", "tain", "tin")),
    ("ven/vent（来）", ("ven", "vent")),
    ("ver/vers/vert（转）", ("ver", "vers", "vert")),
    ("voc/vok（呼喊）", ("voc", "vok")),
    ("log/logue（言语；学科）", ("log", "logue", "logy")),
    ("phil（爱）", ("phil", "phile")),
    ("phob（恐惧）", ("phob", "phobe")),
    ("bene/bon（好）", ("bene", "bon")),
    ("mal（坏）", ("mal",)),
    ("magn/maj/max（大）", ("magn", "maj", "max")),
    ("min（小）", ("min",)),
    ("equ/equi（相等）", ("equ", "equi")),
    ("flu/flux（流）", ("flu", "flux")),
    ("greg（群体）", ("greg",)),
    ("her/hes（粘附）", ("her", "hes")),
    ("morph（形状）", ("morph",)),
    ("path（感受）", ("path",)),
    ("phon（声音）", ("phon",)),
    ("plac（取悦；安抚）", ("plac",)),
    ("tort/torqu（扭曲）", ("tort", "torqu")),
    ("ab-/abs-（离开）", ("ab", "abs")),
    ("ad-/ac-/af-/ag-/al-/an-/ap-/ar-/as-/at-（趋向）", ("ad", "ac", "af", "ag", "al", "an", "ap", "ar", "as", "at")),
    ("anti-/contra-/counter-（反对）", ("anti", "contra", "counter")),
    ("bene-/eu-（好）", ("bene", "eu")),
    ("de-/dis-（向下；否定）", ("de", "dis")),
    ("ex-/e-/ef-（向外）", ("ex", "e", "ef")),
    ("in-/im-/il-/ir-（否定；进入）", ("in", "im", "il", "ir")),
    ("inter-（之间）", ("inter",)),
    ("pre-/pro-（向前）", ("pre", "pro")),
    ("re-/retro-（回；再次）", ("re", "retro")),
    ("sub-/sup-/sus-（下面）", ("sub", "sup", "sus")),
    ("trans-/tra-（穿过）", ("trans", "tra")),
    ("-able/-ible（可...的）", ("able", "ible")),
    ("-ate（动词后缀）", ("ate",)),
    ("-ify/-fy（使成为）", ("ify", "fy")),
    ("-ous/-ious（形容词后缀）", ("ous", "ious")),
    ("-ive/-ative（倾向于）", ("ive", "ative")),
    ("-tion/-sion（名词后缀）", ("tion", "sion")),
]


def clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def derive_synonym_key(meaning_cn: Any) -> str:
    text = clean_text(meaning_cn)
    if not text or text == "Pending":
        return "未分类"
    compact = re.sub(r"\s+", "", text)
    compact = compact.replace("（", "(").replace("）", ")")
    compact = re.sub(r"\([^)]*\)", "", compact)
    for label, cues in SYNONYM_KEY_RULES:
        if any(cue in compact for cue in cues):
            return label

    parts = [
        part.strip()
        for part in re.split(r"[;；,，、/｜|]+", compact)
        if part.strip()
    ]
    key = parts[0] if parts else compact
    key = re.sub(r"(的|地|性)$", "", key)
    return key or "未分类"


def _root_tokens(word_root: Any) -> list[str]:
    text = clean_text(word_root).lower()
    text = text.replace("（", " ").replace("）", " ").replace("(", " ").replace(")", " ")
    text = re.sub(r"(prefix|suffix|root|前缀|后缀|词根)\s*[:：]", " ", text, flags=re.IGNORECASE)
    raw_parts = re.split(r"[/;；,，、｜|+\s]+", text)
    tokens: list[str] = []
    seen: set[str] = set()
    for part in raw_parts:
        token = re.sub(r"[^a-z-]", "", part).strip("-")
        if len(token) < 2:
            continue
        if token not in seen:
            tokens.append(token)
            seen.add(token)
    return tokens


def derive_root_key(word: Any, word_root: Any) -> str:
    tokens = _root_tokens(word_root)
    token_set = set(tokens)
    for label, cues in ROOT_KEY_RULES:
        if any(cue in token_set for cue in cues):
            return label

    word_text = normalize_word(word)
    if word_text and not tokens:
        for label, cues in ROOT_KEY_RULES:
            if any(word_text.startswith(cue) or word_text.endswith(cue) for cue in cues if len(cue) >= 3):
                return label

    if tokens:
        return max(tokens, key=len)
    return "未填写词根"


def normalize_word(value: str) -> str:
    return clean_text(value).lower()


def today_iso() -> str:
    return date.today().isoformat()


def clamp_familiarity(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(4, number))


def fetch_all(query: str, params: Iterable[Any] = ()) -> list[dict]:
    with get_connection(DB_PATH) as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [dict(row) for row in rows]


def fetch_one(query: str, params: Iterable[Any] = ()) -> dict | None:
    with get_connection(DB_PATH) as conn:
        row = conn.execute(query, tuple(params)).fetchone()
    return row_to_dict(row)


def get_setting(key: str, default: str = "") -> str:
    row = fetch_one("SELECT value FROM settings WHERE key = ?", (clean_text(key),))
    return clean_text(row["value"], default) if row else default


def get_int_setting(key: str, default: int = 0) -> int:
    try:
        return int(get_setting(key, str(default)))
    except (TypeError, ValueError):
        return default


def set_setting(key: str, value: Any) -> None:
    clean_key = clean_text(key)
    if not clean_key:
        return
    with get_connection(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO settings(key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (clean_key, clean_text(value)),
        )
        conn.commit()


def ensure_bootstrap_data() -> None:
    initialize_database(DB_PATH)
    for name_en, name_cn in DEFAULT_LEVEL_1_CATEGORIES:
        get_or_create_category(level=1, name_cn=name_cn, name_en=name_en)
    populate_missing_synonym_keys()
    populate_missing_root_keys()
    merge_duplicate_word_entries()


def get_word_by_text(word: str) -> dict | None:
    return fetch_one(
        "SELECT * FROM words WHERE lower(word) = lower(?)",
        (clean_text(word),),
    )


def get_word(word_id: int) -> dict | None:
    return fetch_one("SELECT * FROM words WHERE id = ?", (word_id,))


def get_or_create_word(
    word: str,
    lemma: str = "",
    pronunciation: str = "",
    general_notes: str = "",
) -> tuple[int, bool]:
    normalized = clean_text(word)
    if not normalized:
        raise ValueError("Word is required.")

    existing = get_word_by_text(normalized)
    if existing:
        return int(existing["id"]), False

    with get_connection(DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO words(word, lemma, pronunciation, general_notes)
            VALUES (?, ?, ?, ?)
            """,
            (
                normalized,
                clean_text(lemma) or normalized,
                clean_text(pronunciation),
                clean_text(general_notes),
            ),
        )
        conn.commit()
        return int(cur.lastrowid), True


def update_word(word_id: int, **updates: Any) -> None:
    allowed = {"word", "lemma", "pronunciation", "general_notes", "status"}
    fields = [key for key in updates if key in allowed]
    if not fields:
        return
    assignments = ", ".join(f"{field} = ?" for field in fields)
    params = [clean_text(updates[field]) for field in fields]
    params.append(word_id)
    with get_connection(DB_PATH) as conn:
        conn.execute(f"UPDATE words SET {assignments} WHERE id = ?", params)
        conn.commit()


def delete_word(word_id: int) -> None:
    with get_connection(DB_PATH) as conn:
        conn.execute("DELETE FROM words WHERE id = ?", (word_id,))
        conn.commit()


def list_words() -> list[dict]:
    return fetch_all("SELECT * FROM words ORDER BY lower(word)")


def create_word_sense(word_id: int, **data: Any) -> int:
    cn = clean_text(data.get("core_meaning_cn"), "Pending")
    en = clean_text(data.get("core_meaning_en"), "Pending")
    synonym_key = clean_text(data.get("synonym_key")) or derive_synonym_key(cn)
    word_row = get_word(word_id) or {}
    root_key = clean_text(data.get("root_key")) or derive_root_key(word_row.get("word"), data.get("word_root"))
    status = clean_text(data.get("status"))
    if not status:
        status = "pending" if cn == "Pending" and en == "Pending" else "learning"
    familiarity = clamp_familiarity(data.get("familiarity", 0))
    review_status = clean_text(data.get("review_status"))
    if not review_status:
        review_status = "mastered" if familiarity >= 4 else ("pending" if status == "pending" else "learning")

    with get_connection(DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO word_senses(
                word_id, sense_label, part_of_speech, core_meaning_cn, core_meaning_en,
                usage_notes, nuance, common_collocations, usage_register,
                word_root, root_key, synonym_key, example_sentence, antonyms, status, familiarity, wrong_count,
                review_status, next_review_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                word_id,
                clean_text(data.get("sense_label")),
                clean_text(data.get("part_of_speech"), "Pending"),
                cn,
                en,
                clean_text(data.get("usage_notes")),
                clean_text(data.get("nuance")),
                clean_text(data.get("common_collocations")),
                clean_text(data.get("usage_register")),
                clean_text(data.get("word_root")),
                root_key,
                synonym_key,
                clean_text(data.get("example_sentence")),
                clean_text(data.get("antonyms")),
                status,
                familiarity,
                max(0, int(data.get("wrong_count", 0) or 0)),
                review_status,
                clean_text(data.get("next_review_date"), today_iso()),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_sense(sense_id: int) -> dict | None:
    return fetch_one(
        """
        SELECT ws.*, w.word, w.lemma, w.pronunciation, w.general_notes
        FROM word_senses ws
        JOIN words w ON w.id = ws.word_id
        WHERE ws.id = ?
        """,
        (sense_id,),
    )


def find_sense_by_word_meaning(word_id: int, core_meaning_cn: str, part_of_speech: str = "") -> dict | None:
    params: list[Any] = [word_id, clean_text(core_meaning_cn, "Pending")]
    pos_clause = ""
    if clean_text(part_of_speech):
        pos_clause = "AND lower(part_of_speech) = lower(?)"
        params.append(clean_text(part_of_speech))
    return fetch_one(
        f"""
        SELECT *
        FROM word_senses
        WHERE word_id = ?
          AND lower(core_meaning_cn) = lower(?)
          {pos_clause}
        ORDER BY id
        LIMIT 1
        """,
        params,
    )


def list_senses(word_id: int | None = None) -> list[dict]:
    params: list[Any] = []
    where = ""
    if word_id is not None:
        where = "WHERE ws.word_id = ?"
        params.append(word_id)
    return fetch_all(
        f"""
        SELECT ws.*, w.word
        FROM word_senses ws
        JOIN words w ON w.id = ws.word_id
        {where}
        ORDER BY lower(w.word), ws.id
        """,
        params,
    )


def sense_label(sense: dict) -> str:
    word = clean_text(sense.get("word"))
    pos = clean_text(sense.get("part_of_speech"), "POS")
    cn = clean_text(sense.get("core_meaning_cn"), "Pending")
    return f"{word} | {pos} | {cn} | #{sense.get('id')}"


def update_sense(sense_id: int, **updates: Any) -> None:
    allowed = {
        "sense_label",
        "part_of_speech",
        "core_meaning_cn",
        "core_meaning_en",
        "usage_notes",
        "nuance",
        "common_collocations",
        "usage_register",
        "word_root",
        "root_key",
        "synonym_key",
        "example_sentence",
        "antonyms",
        "status",
        "familiarity",
        "wrong_count",
        "review_status",
        "next_review_date",
    }
    fields = [key for key in updates if key in allowed]
    if not fields:
        return
    values: list[Any] = []
    for field in fields:
        if field == "familiarity":
            values.append(clamp_familiarity(updates[field]))
        elif field == "wrong_count":
            values.append(max(0, int(updates[field] or 0)))
        else:
            values.append(clean_text(updates[field]))
    assignments = ", ".join(f"{field} = ?" for field in fields)
    values.append(sense_id)
    with get_connection(DB_PATH) as conn:
        conn.execute(f"UPDATE word_senses SET {assignments} WHERE id = ?", values)
        conn.commit()


def delete_sense(sense_id: int) -> None:
    with get_connection(DB_PATH) as conn:
        conn.execute("DELETE FROM word_senses WHERE id = ?", (sense_id,))
        conn.commit()


def _merged_parts(values: list[Any], separator_pattern: str, output_separator: str) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = clean_text(value)
        if not text or text == "Pending":
            continue
        for part in re.split(separator_pattern, text):
            piece = clean_text(part)
            key = piece.lower()
            if piece and key not in seen:
                parts.append(piece)
                seen.add(key)
    return output_separator.join(parts)


def _merged_whole_values(values: list[Any], output_separator: str = "; ") -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = clean_text(value)
        if not text or text == "Pending":
            continue
        key = text.lower()
        if key not in seen:
            parts.append(text)
            seen.add(key)
    return output_separator.join(parts)


def merge_senses_for_word(word_id: int, incoming: dict[str, Any] | None = None) -> dict[str, Any] | None:
    senses = list_senses(word_id=word_id)
    if not senses and not incoming:
        return None
    if not senses:
        return None

    incoming = incoming or {}
    canonical = senses[0]
    duplicate_senses = senses[1:]
    all_senses = senses + [incoming]
    merged_cn = _merged_parts([sense.get("core_meaning_cn") for sense in all_senses], r"[;；,，、/｜|]+", "；")
    merged_pos = _merged_parts([sense.get("part_of_speech") for sense in all_senses], r"[;/,，、｜|]+", "/")
    merged_en = _merged_whole_values([sense.get("core_meaning_en") for sense in all_senses])
    merged_root = _merged_parts([sense.get("word_root") for sense in all_senses], r"[;/,，、｜|]+", "/")
    merged_synonym_key = clean_text(incoming.get("synonym_key")) or derive_synonym_key(merged_cn)
    merged_root_key = clean_text(incoming.get("root_key")) or derive_root_key(canonical.get("word"), merged_root)
    familiarity = max(clamp_familiarity(sense.get("familiarity", 0)) for sense in senses)
    wrong_count = sum(max(0, int(sense.get("wrong_count", 0) or 0)) for sense in senses)
    review_dates = [clean_text(sense.get("next_review_date")) for sense in senses if clean_text(sense.get("next_review_date"))]
    next_review_date = min(review_dates) if review_dates else today_iso()

    update_sense(
        int(canonical["id"]),
        part_of_speech=merged_pos or clean_text(incoming.get("part_of_speech"), "Pending"),
        core_meaning_cn=merged_cn or clean_text(incoming.get("core_meaning_cn"), "Pending"),
        core_meaning_en=merged_en or clean_text(incoming.get("core_meaning_en"), "Pending"),
        word_root=merged_root or clean_text(incoming.get("word_root")),
        root_key=merged_root_key,
        synonym_key=merged_synonym_key,
        familiarity=familiarity,
        wrong_count=wrong_count,
        next_review_date=next_review_date,
        status="learning",
        review_status="mastered" if familiarity >= 4 else "learning",
    )
    for duplicate in duplicate_senses:
        delete_sense(int(duplicate["id"]))
    return simple_word_detail(int(canonical["id"]))


def merge_duplicate_word_entries() -> int:
    duplicate_words = fetch_all(
        """
        SELECT word_id, COUNT(*) AS n
        FROM word_senses
        GROUP BY word_id
        HAVING COUNT(*) > 1
        """
    )
    for row in duplicate_words:
        merge_senses_for_word(int(row["word_id"]))
    return len(duplicate_words)


def get_or_create_category(
    level: int,
    name_cn: str,
    name_en: str = "",
    parent_id: int | None = None,
    description: str = "",
) -> int | None:
    label_cn = clean_text(name_cn)
    label_en = clean_text(name_en)
    if not label_cn and not label_en:
        return None
    if not label_cn:
        label_cn = label_en

    if parent_id is None:
        existing = fetch_one(
            """
            SELECT * FROM semantic_categories
            WHERE parent_id IS NULL
              AND level = ?
              AND (lower(name_cn) = lower(?) OR lower(name_en) = lower(?))
            """,
            (level, label_cn, label_cn if not label_en else label_en),
        )
    else:
        existing = fetch_one(
            """
            SELECT * FROM semantic_categories
            WHERE parent_id = ?
              AND level = ?
              AND (lower(name_cn) = lower(?) OR lower(name_en) = lower(?))
            """,
            (parent_id, level, label_cn, label_cn if not label_en else label_en),
        )
    if existing:
        return int(existing["id"])

    with get_connection(DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO semantic_categories(parent_id, level, name_cn, name_en, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (parent_id, level, label_cn, label_en, clean_text(description)),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_categories(level: int | None = None, parent_id: int | None = None) -> list[dict]:
    clauses: list[str] = []
    params: list[Any] = []
    if level is not None:
        clauses.append("level = ?")
        params.append(level)
    if parent_id is not None:
        clauses.append("parent_id = ?")
        params.append(parent_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return fetch_all(
        f"""
        SELECT *
        FROM semantic_categories
        {where}
        ORDER BY sort_order, lower(COALESCE(NULLIF(name_en, ''), name_cn)), lower(name_cn)
        """,
        params,
    )


def update_category(category_id: int, **updates: Any) -> None:
    allowed = {"parent_id", "level", "name_cn", "name_en", "description", "sort_order"}
    fields = [key for key in updates if key in allowed]
    if not fields:
        return
    assignments = ", ".join(f"{field} = ?" for field in fields)
    params = [updates[field] if field in {"parent_id", "level", "sort_order"} else clean_text(updates[field]) for field in fields]
    params.append(category_id)
    with get_connection(DB_PATH) as conn:
        conn.execute(f"UPDATE semantic_categories SET {assignments} WHERE id = ?", params)
        conn.commit()


def delete_category(category_id: int) -> None:
    with get_connection(DB_PATH) as conn:
        conn.execute("DELETE FROM semantic_categories WHERE id = ?", (category_id,))
        conn.commit()


def get_group(group_id: int) -> dict | None:
    return fetch_one(
        """
        SELECT sg.*, l1.name_cn AS level1_cn, l1.name_en AS level1_en,
               l2.name_cn AS level2_cn, l2.name_en AS level2_en
        FROM synonym_groups sg
        LEFT JOIN semantic_categories l1 ON l1.id = sg.level1_id
        LEFT JOIN semantic_categories l2 ON l2.id = sg.level2_id
        WHERE sg.id = ?
        """,
        (group_id,),
    )


def get_or_create_group(
    group_name_cn: str,
    group_name_en: str = "",
    level1_id: int | None = None,
    level2_id: int | None = None,
    group_definition: str = "",
    semantic_axis: str = "",
    notes: str = "",
    axis_enabled: bool = False,
    axis_name: str = "",
    low_label: str = "",
    high_label: str = "",
) -> int | None:
    label_cn = clean_text(group_name_cn)
    label_en = clean_text(group_name_en)
    if not label_cn and not label_en:
        return None
    if not label_cn:
        label_cn = label_en

    existing = fetch_one(
        """
        SELECT *
        FROM synonym_groups
        WHERE lower(group_name_cn) = lower(?)
          AND COALESCE(level1_id, -1) = COALESCE(?, -1)
          AND COALESCE(level2_id, -1) = COALESCE(?, -1)
        """,
        (label_cn, level1_id, level2_id),
    )
    if existing:
        return int(existing["id"])

    with get_connection(DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO synonym_groups(
                group_name_cn, group_name_en, level1_id, level2_id,
                group_definition, semantic_axis, notes, axis_enabled,
                axis_name, low_label, high_label
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                label_cn,
                label_en,
                level1_id,
                level2_id,
                clean_text(group_definition),
                clean_text(semantic_axis),
                clean_text(notes),
                1 if axis_enabled else 0,
                clean_text(axis_name),
                clean_text(low_label),
                clean_text(high_label),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def update_group(group_id: int, **updates: Any) -> None:
    allowed = {
        "group_name_cn",
        "group_name_en",
        "level1_id",
        "level2_id",
        "group_definition",
        "semantic_axis",
        "notes",
        "axis_enabled",
        "axis_name",
        "low_label",
        "high_label",
        "sort_order",
    }
    fields = [key for key in updates if key in allowed]
    if not fields:
        return
    values: list[Any] = []
    for field in fields:
        if field in {"level1_id", "level2_id"}:
            values.append(updates[field] or None)
        elif field in {"axis_enabled"}:
            values.append(1 if updates[field] else 0)
        elif field in {"sort_order"}:
            values.append(int(updates[field] or 0))
        else:
            values.append(clean_text(updates[field]))
    assignments = ", ".join(f"{field} = ?" for field in fields)
    values.append(group_id)
    with get_connection(DB_PATH) as conn:
        conn.execute(f"UPDATE synonym_groups SET {assignments} WHERE id = ?", values)
        conn.commit()


def delete_group(group_id: int) -> None:
    with get_connection(DB_PATH) as conn:
        conn.execute("DELETE FROM synonym_groups WHERE id = ?", (group_id,))
        conn.commit()


def list_groups(level1_id: int | None = None, level2_id: int | None = None) -> list[dict]:
    clauses: list[str] = []
    params: list[Any] = []
    if level1_id:
        clauses.append("sg.level1_id = ?")
        params.append(level1_id)
    if level2_id:
        clauses.append("sg.level2_id = ?")
        params.append(level2_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return fetch_all(
        f"""
        SELECT sg.*, l1.name_cn AS level1_cn, l1.name_en AS level1_en,
               l2.name_cn AS level2_cn, l2.name_en AS level2_en,
               COUNT(sm.id) AS member_count
        FROM synonym_groups sg
        LEFT JOIN semantic_categories l1 ON l1.id = sg.level1_id
        LEFT JOIN semantic_categories l2 ON l2.id = sg.level2_id
        LEFT JOIN synonym_memberships sm ON sm.group_id = sg.id
        {where}
        GROUP BY sg.id
        ORDER BY l1.sort_order, lower(COALESCE(NULLIF(l1.name_en, ''), l1.name_cn)),
                 l2.sort_order, lower(l2.name_cn), sg.sort_order, lower(sg.group_name_cn)
        """,
        params,
    )


def add_membership(
    sense_id: int,
    group_id: int,
    typicality: str = "",
    strength_level: str = "",
    axis_position: int | None = None,
    display_order: int | None = None,
    notes: str = "",
) -> int:
    if display_order is None:
        existing = fetch_one(
            "SELECT COALESCE(MAX(display_order), 0) + 1 AS next_order FROM synonym_memberships WHERE group_id = ?",
            (group_id,),
        )
        display_order = int(existing["next_order"] if existing else 1)

    with get_connection(DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO synonym_memberships(
                sense_id, group_id, typicality, strength_level,
                axis_position, display_order, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sense_id, group_id) DO UPDATE SET
                typicality = excluded.typicality,
                strength_level = excluded.strength_level,
                axis_position = excluded.axis_position,
                display_order = excluded.display_order,
                notes = excluded.notes
            """,
            (
                sense_id,
                group_id,
                clean_text(typicality),
                clean_text(strength_level),
                axis_position,
                int(display_order or 0),
                clean_text(notes),
            ),
        )
        conn.commit()
        return int(cur.lastrowid or 0)


def update_membership(membership_id: int, **updates: Any) -> None:
    allowed = {"group_id", "typicality", "strength_level", "axis_position", "display_order", "notes"}
    fields = [key for key in updates if key in allowed]
    if not fields:
        return
    values: list[Any] = []
    for field in fields:
        if field in {"group_id", "axis_position", "display_order"}:
            value = updates[field]
            values.append(None if value in ("", None) and field == "axis_position" else int(value or 0))
        else:
            values.append(clean_text(updates[field]))
    assignments = ", ".join(f"{field} = ?" for field in fields)
    values.append(membership_id)
    with get_connection(DB_PATH) as conn:
        conn.execute(f"UPDATE synonym_memberships SET {assignments} WHERE id = ?", values)
        conn.commit()


def remove_membership(membership_id: int) -> None:
    with get_connection(DB_PATH) as conn:
        conn.execute("DELETE FROM synonym_memberships WHERE id = ?", (membership_id,))
        conn.commit()


def group_members(group_id: int) -> list[dict]:
    return fetch_all(
        """
        SELECT sm.id AS membership_id, sm.group_id, sm.typicality, sm.strength_level,
               sm.axis_position, sm.display_order, sm.notes AS membership_notes,
               ws.id AS sense_id, ws.part_of_speech, ws.core_meaning_cn,
               ws.core_meaning_en, ws.nuance, ws.common_collocations,
               ws.usage_register, ws.antonyms, ws.familiarity, ws.wrong_count,
               ws.review_status, ws.next_review_date, w.word
        FROM synonym_memberships sm
        JOIN word_senses ws ON ws.id = sm.sense_id
        JOIN words w ON w.id = ws.word_id
        WHERE sm.group_id = ?
        ORDER BY sm.display_order, COALESCE(sm.axis_position, 9999), lower(w.word), ws.id
        """,
        (group_id,),
    )


def sense_groups(sense_id: int) -> list[dict]:
    return fetch_all(
        """
        SELECT sm.id AS membership_id, sm.*, sg.group_name_cn, sg.group_name_en,
               l1.name_cn AS level1_cn, l1.name_en AS level1_en,
               l2.name_cn AS level2_cn, l2.name_en AS level2_en
        FROM synonym_memberships sm
        JOIN synonym_groups sg ON sg.id = sm.group_id
        LEFT JOIN semantic_categories l1 ON l1.id = sg.level1_id
        LEFT JOIN semantic_categories l2 ON l2.id = sg.level2_id
        WHERE sm.sense_id = ?
        ORDER BY l1.sort_order, l2.sort_order, sg.sort_order, sm.display_order
        """,
        (sense_id,),
    )


def _word_bank_base_query() -> str:
    return """
    WITH group_info AS (
        SELECT sm.sense_id,
               GROUP_CONCAT(DISTINCT sg.group_name_cn) AS synonym_groups,
               GROUP_CONCAT(DISTINCT NULLIF(sg.group_name_en, '')) AS synonym_groups_en,
               GROUP_CONCAT(DISTINCT l1.name_cn) AS level1_categories_cn,
               GROUP_CONCAT(DISTINCT NULLIF(l1.name_en, '')) AS level1_categories_en,
               GROUP_CONCAT(DISTINCT l2.name_cn) AS level2_categories_cn,
               GROUP_CONCAT(DISTINCT NULLIF(l2.name_en, '')) AS level2_categories_en,
               GROUP_CONCAT(DISTINCT sg.semantic_axis) AS semantic_axis
        FROM synonym_memberships sm
        JOIN synonym_groups sg ON sg.id = sm.group_id
        LEFT JOIN semantic_categories l1 ON l1.id = sg.level1_id
        LEFT JOIN semantic_categories l2 ON l2.id = sg.level2_id
        GROUP BY sm.sense_id
    ),
    synonym_info AS (
        SELECT sm.sense_id,
               GROUP_CONCAT(DISTINCT w2.word) AS synonyms
        FROM synonym_memberships sm
        JOIN synonym_memberships sm2 ON sm2.group_id = sm.group_id AND sm2.sense_id <> sm.sense_id
        JOIN word_senses ws2 ON ws2.id = sm2.sense_id
        JOIN words w2 ON w2.id = ws2.word_id
        GROUP BY sm.sense_id
    ),
    question_info AS (
        SELECT wqr.sense_id,
               GROUP_CONCAT(DISTINCT gq.source) AS source_questions,
               GROUP_CONCAT(DISTINCT wqr.context_sentence) AS gre_contexts
        FROM word_question_relations wqr
        JOIN gre_questions gq ON gq.id = wqr.question_id
        GROUP BY wqr.sense_id
    )
    SELECT ws.id AS sense_id, w.id AS word_id, w.word, w.lemma, w.pronunciation,
           ws.part_of_speech AS POS,
           ws.core_meaning_cn AS Core_Meaning_CN,
           ws.core_meaning_en AS Core_Meaning_EN,
           COALESCE(gi.level1_categories_en, '') AS Level_1_Semantic_Category,
           COALESCE(gi.level2_categories_cn, '') AS Level_2_Semantic_Category,
           COALESCE(gi.synonym_groups, '') AS Synonym_Group,
           COALESCE(si.synonyms, '') AS Synonyms,
           ws.antonyms AS Antonyms,
           ws.nuance AS Nuance,
           ws.common_collocations AS Collocations,
           COALESCE(qi.gre_contexts, ws.example_sentence) AS GRE_Context,
           COALESCE(qi.source_questions, '') AS Source_Question,
           ws.familiarity AS Familiarity,
           ws.wrong_count AS Wrong_Count,
           ws.review_status AS Review_Status,
           ws.next_review_date AS Next_Review_Date,
           ws.status AS Status,
           ws.usage_notes AS Notes,
           COALESCE(gi.semantic_axis, '') AS Semantic_Axis,
           ws.created_at AS Created_At,
           ws.updated_at AS Updated_At
    FROM word_senses ws
    JOIN words w ON w.id = ws.word_id
    LEFT JOIN group_info gi ON gi.sense_id = ws.id
    LEFT JOIN synonym_info si ON si.sense_id = ws.id
    LEFT JOIN question_info qi ON qi.sense_id = ws.id
    """


def word_bank_rows(filters: dict | None = None) -> list[dict]:
    filters = filters or {}
    query = _word_bank_base_query()
    clauses = ["1 = 1"]
    params: list[Any] = []

    search = clean_text(filters.get("search"))
    if search:
        like = f"%{search.lower()}%"
        clauses.append(
            """
            (
                lower(w.word) LIKE ?
                OR lower(ws.core_meaning_cn) LIKE ?
                OR lower(ws.core_meaning_en) LIKE ?
                OR lower(ws.nuance) LIKE ?
                OR lower(ws.common_collocations) LIKE ?
                OR lower(ws.antonyms) LIKE ?
                OR lower(COALESCE(gi.synonym_groups, '')) LIKE ?
                OR lower(COALESCE(gi.level1_categories_cn, '')) LIKE ?
                OR lower(COALESCE(gi.level1_categories_en, '')) LIKE ?
                OR lower(COALESCE(gi.level2_categories_cn, '')) LIKE ?
                OR lower(COALESCE(si.synonyms, '')) LIKE ?
                OR lower(COALESCE(qi.gre_contexts, '')) LIKE ?
            )
            """
        )
        params.extend([like] * 12)

    if filters.get("level1_id"):
        clauses.append(
            """
            EXISTS (
                SELECT 1 FROM synonym_memberships smx
                JOIN synonym_groups sgx ON sgx.id = smx.group_id
                WHERE smx.sense_id = ws.id AND sgx.level1_id = ?
            )
            """
        )
        params.append(filters["level1_id"])
    if filters.get("level2_id"):
        clauses.append(
            """
            EXISTS (
                SELECT 1 FROM synonym_memberships smx
                JOIN synonym_groups sgx ON sgx.id = smx.group_id
                WHERE smx.sense_id = ws.id AND sgx.level2_id = ?
            )
            """
        )
        params.append(filters["level2_id"])
    if filters.get("group_id"):
        clauses.append(
            "EXISTS (SELECT 1 FROM synonym_memberships smx WHERE smx.sense_id = ws.id AND smx.group_id = ?)"
        )
        params.append(filters["group_id"])
    if filters.get("familiarity") not in (None, "", "All"):
        clauses.append("ws.familiarity = ?")
        params.append(int(filters["familiarity"]))
    if filters.get("due_only"):
        clauses.append("DATE(ws.next_review_date) <= DATE(?)")
        params.append(today_iso())
    if filters.get("wrong_only"):
        clauses.append("ws.wrong_count > 0")
    if filters.get("pending_only"):
        clauses.append("ws.status = 'pending'")

    query += f" WHERE {' AND '.join(clauses)}"
    sort_by = clean_text(filters.get("sort_by"), "lower(w.word)")
    allowed_sorts = {
        "Word": "lower(w.word), ws.id",
        "Familiarity": "ws.familiarity, lower(w.word)",
        "Wrong Count": "ws.wrong_count DESC, lower(w.word)",
        "Next Review": "DATE(ws.next_review_date), lower(w.word)",
        "Recently Added": "ws.created_at DESC",
    }
    order = allowed_sorts.get(sort_by, "lower(w.word), ws.id")
    query += f" ORDER BY {order}"
    return fetch_all(query, params)


def simple_word_rows(filters: dict | None = None) -> list[dict]:
    filters = filters or {}
    clauses = ["1 = 1"]
    params: list[Any] = []

    search = clean_text(filters.get("search"))
    if search:
        like = f"%{search.lower()}%"
        clauses.append(
            """
            (
                lower(w.word) LIKE ?
                OR lower(ws.core_meaning_cn) LIKE ?
                OR lower(ws.part_of_speech) LIKE ?
                OR lower(ws.core_meaning_en) LIKE ?
                OR lower(COALESCE(ws.word_root, '')) LIKE ?
                OR lower(COALESCE(ws.root_key, '')) LIKE ?
            )
            """
        )
        params.extend([like] * 6)

    first_letter = clean_text(filters.get("first_letter")).lower()
    if first_letter and first_letter != "全部":
        clauses.append("lower(substr(w.word, 1, 1)) = ?")
        params.append(first_letter[:1])

    root = clean_text(filters.get("word_root"))
    if root:
        if root == "未填写词根":
            clauses.append("COALESCE(NULLIF(TRIM(ws.word_root), ''), '') = ''")
        else:
            clauses.append("lower(COALESCE(ws.word_root, '')) = lower(?)")
            params.append(root)

    root_key = clean_text(filters.get("root_key"))
    if root_key and root_key != "全部":
        if root_key == "未填写词根":
            clauses.append("COALESCE(NULLIF(TRIM(ws.root_key), ''), '未填写词根') = '未填写词根'")
        else:
            clauses.append("lower(COALESCE(NULLIF(TRIM(ws.root_key), ''), ws.word_root)) = lower(?)")
            params.append(root_key)

    meaning = clean_text(filters.get("core_meaning_cn"))
    if meaning:
        clauses.append("lower(ws.core_meaning_cn) = lower(?)")
        params.append(meaning)

    synonym_key = clean_text(filters.get("synonym_key"))
    if synonym_key:
        clauses.append("lower(COALESCE(NULLIF(TRIM(ws.synonym_key), ''), ws.core_meaning_cn)) = lower(?)")
        params.append(synonym_key)

    if filters.get("due_only"):
        clauses.append("DATE(ws.next_review_date) <= DATE(?)")
        params.append(today_iso())

    added_from = clean_text(filters.get("added_from"))
    if added_from:
        clauses.append("DATE(ws.created_at) >= DATE(?)")
        params.append(added_from)

    added_to = clean_text(filters.get("added_to"))
    if added_to:
        clauses.append("DATE(ws.created_at) <= DATE(?)")
        params.append(added_to)

    synonyms_select = "'' AS synonyms,"
    if filters.get("include_synonyms"):
        synonyms_select = """
            COALESCE(
                (
                    SELECT GROUP_CONCAT(peer.word, ', ')
                    FROM (
                        SELECT DISTINCT w2.word AS word
                        FROM word_senses ws2
                        JOIN words w2 ON w2.id = ws2.word_id
                        WHERE ws2.id <> ws.id
                          AND lower(w2.word) <> lower(w.word)
                          AND lower(COALESCE(NULLIF(TRIM(ws2.synonym_key), ''), ws2.core_meaning_cn))
                              = lower(COALESCE(NULLIF(TRIM(ws.synonym_key), ''), ws.core_meaning_cn))
                        ORDER BY lower(w2.word)
                    ) AS peer
                ),
                ''
            ) AS synonyms,
        """

    query = f"""
        SELECT
            ws.id AS sense_id,
            w.id AS word_id,
            w.word,
            ws.core_meaning_cn,
            ws.part_of_speech,
            ws.core_meaning_en,
            COALESCE(ws.word_root, '') AS word_root,
            COALESCE(NULLIF(TRIM(ws.root_key), ''), COALESCE(NULLIF(TRIM(ws.word_root), ''), '未填写词根')) AS root_key,
            COALESCE(NULLIF(TRIM(ws.synonym_key), ''), ws.core_meaning_cn) AS synonym_key,
            {synonyms_select}
            ws.familiarity,
            ws.wrong_count,
            ws.review_status,
            ws.next_review_date,
            DATE(ws.created_at) AS added_date,
            ws.created_at,
            ws.updated_at
        FROM word_senses ws
        JOIN words w ON w.id = ws.word_id
        WHERE {' AND '.join(clauses)}
    """
    sort_by = clean_text(filters.get("sort_by"), "word")
    allowed_sorts = {
        "word": "lower(w.word), ws.id",
        "recent": "ws.created_at DESC, lower(w.word)",
        "review": "DATE(ws.next_review_date), lower(w.word)",
        "meaning": "lower(ws.core_meaning_cn), lower(w.word)",
        "root": "lower(COALESCE(NULLIF(TRIM(ws.root_key), ''), ws.word_root)), lower(w.word)",
    }
    query += f" ORDER BY {allowed_sorts.get(sort_by, allowed_sorts['word'])}"
    return fetch_all(query, params)


def simple_word_detail(sense_id: int) -> dict | None:
    return fetch_one(
        """
        SELECT
            ws.id AS sense_id,
            w.id AS word_id,
            w.word,
            ws.core_meaning_cn,
            ws.part_of_speech,
            ws.core_meaning_en,
            COALESCE(ws.word_root, '') AS word_root,
            COALESCE(NULLIF(TRIM(ws.root_key), ''), COALESCE(NULLIF(TRIM(ws.word_root), ''), '未填写词根')) AS root_key,
            COALESCE(NULLIF(TRIM(ws.synonym_key), ''), ws.core_meaning_cn) AS synonym_key,
            ws.familiarity,
            ws.wrong_count,
            ws.review_status,
            ws.next_review_date,
            DATE(ws.created_at) AS added_date
        FROM word_senses ws
        JOIN words w ON w.id = ws.word_id
        WHERE ws.id = ?
        """,
        (sense_id,),
    )


def delete_simple_entry(sense_id: int) -> None:
    detail = simple_word_detail(sense_id)
    if not detail:
        return
    word_id = int(detail["word_id"])
    delete_sense(sense_id)
    remaining = fetch_one("SELECT COUNT(*) AS n FROM word_senses WHERE word_id = ?", (word_id,))
    if remaining and int(remaining["n"]) == 0:
        delete_word(word_id)


def synonym_index_rows(search: str = "") -> list[dict]:
    params: list[Any] = []
    clauses = ["TRIM(ws.core_meaning_cn) <> ''", "ws.core_meaning_cn <> 'Pending'"]
    clean_search = clean_text(search)
    if clean_search:
        clauses.append(
            """
            (
                lower(COALESCE(NULLIF(TRIM(ws.synonym_key), ''), ws.core_meaning_cn)) LIKE ?
                OR lower(ws.core_meaning_cn) LIKE ?
            )
            """
        )
        params.extend([f"%{clean_search.lower()}%"] * 2)
    return fetch_all(
        f"""
        SELECT
            COALESCE(NULLIF(TRIM(ws.synonym_key), ''), ws.core_meaning_cn) AS synonym_key,
            GROUP_CONCAT(DISTINCT ws.core_meaning_cn) AS meaning_variants,
            COUNT(*) AS word_count,
            GROUP_CONCAT(w.word, ', ') AS english_words
        FROM word_senses ws
        JOIN words w ON w.id = ws.word_id
        WHERE {' AND '.join(clauses)}
        GROUP BY lower(COALESCE(NULLIF(TRIM(ws.synonym_key), ''), ws.core_meaning_cn))
        ORDER BY lower(synonym_key), COUNT(*) DESC
        """,
        params,
    )


def words_for_meaning(core_meaning_cn: str) -> list[dict]:
    rows = simple_word_rows({"synonym_key": core_meaning_cn, "sort_by": "word"})
    return rows or simple_word_rows({"core_meaning_cn": core_meaning_cn, "sort_by": "word"})


def words_for_synonym_key(synonym_key: str) -> list[dict]:
    return simple_word_rows({"synonym_key": synonym_key, "sort_by": "word"})


def populate_missing_synonym_keys() -> None:
    rows = fetch_all(
        """
        SELECT id, core_meaning_cn
        FROM word_senses
        WHERE TRIM(COALESCE(synonym_key, '')) = ''
        """
    )
    with get_connection(DB_PATH) as conn:
        for row in rows:
            conn.execute(
                "UPDATE word_senses SET synonym_key = ? WHERE id = ?",
                (derive_synonym_key(row["core_meaning_cn"]), row["id"]),
            )
        conn.commit()


def rename_synonym_key(old_key: str, new_key: str) -> int:
    old_label = clean_text(old_key)
    new_label = clean_text(new_key)
    if not old_label or not new_label:
        raise ValueError("同义索引名称不能为空。")
    with get_connection(DB_PATH) as conn:
        cur = conn.execute(
            """
            UPDATE word_senses
            SET synonym_key = ?
            WHERE lower(COALESCE(NULLIF(TRIM(synonym_key), ''), core_meaning_cn)) = lower(?)
            """,
            (new_label, old_label),
        )
        conn.commit()
        return cur.rowcount


def merge_synonym_keys(source_keys: list[str], target_key: str) -> int:
    target_label = clean_text(target_key)
    cleaned_sources = [clean_text(key) for key in source_keys if clean_text(key) and clean_text(key) != target_label]
    if not target_label or not cleaned_sources:
        return 0
    with get_connection(DB_PATH) as conn:
        total = 0
        for source_key in cleaned_sources:
            cur = conn.execute(
                """
                UPDATE word_senses
                SET synonym_key = ?
                WHERE lower(COALESCE(NULLIF(TRIM(synonym_key), ''), core_meaning_cn)) = lower(?)
                """,
                (target_label, source_key),
            )
            total += cur.rowcount
        conn.commit()
        return total


def root_index_rows(search: str = "") -> list[dict]:
    params: list[Any] = []
    clean_search = clean_text(search)
    where = ""
    if clean_search:
        where = """
        WHERE (
            lower(COALESCE(NULLIF(TRIM(ws.root_key), ''), COALESCE(NULLIF(TRIM(ws.word_root), ''), '未填写词根'))) LIKE ?
            OR lower(COALESCE(ws.word_root, '')) LIKE ?
        )
        """
        params.extend([f"%{clean_search.lower()}%"] * 2)
    return fetch_all(
        f"""
        SELECT
            COALESCE(NULLIF(TRIM(ws.root_key), ''), COALESCE(NULLIF(TRIM(ws.word_root), ''), '未填写词根')) AS root_key,
            GROUP_CONCAT(DISTINCT COALESCE(NULLIF(TRIM(ws.word_root), ''), '未填写词根')) AS root_variants,
            COUNT(*) AS word_count,
            GROUP_CONCAT(w.word, ', ') AS english_words
        FROM word_senses ws
        JOIN words w ON w.id = ws.word_id
        {where}
        GROUP BY lower(COALESCE(NULLIF(TRIM(ws.root_key), ''), COALESCE(NULLIF(TRIM(ws.word_root), ''), '未填写词根')))
        ORDER BY lower(root_key), COUNT(*) DESC
        """,
        params,
    )


def words_for_root(word_root: str) -> list[dict]:
    rows = simple_word_rows({"root_key": word_root, "sort_by": "word"})
    return rows or simple_word_rows({"word_root": word_root, "sort_by": "word"})


def populate_missing_root_keys() -> None:
    rows = fetch_all(
        """
        SELECT ws.id, w.word, ws.word_root
        FROM word_senses ws
        JOIN words w ON w.id = ws.word_id
        WHERE TRIM(COALESCE(ws.root_key, '')) = ''
        """
    )
    with get_connection(DB_PATH) as conn:
        for row in rows:
            conn.execute(
                "UPDATE word_senses SET root_key = ? WHERE id = ?",
                (derive_root_key(row["word"], row["word_root"]), row["id"]),
            )
        conn.commit()


def rename_root_key(old_key: str, new_key: str) -> int:
    old_label = clean_text(old_key)
    new_label = clean_text(new_key)
    if not old_label or not new_label:
        raise ValueError("词根索引名称不能为空。")
    with get_connection(DB_PATH) as conn:
        cur = conn.execute(
            """
            UPDATE word_senses
            SET root_key = ?
            WHERE lower(COALESCE(NULLIF(TRIM(root_key), ''), COALESCE(NULLIF(TRIM(word_root), ''), '未填写词根'))) = lower(?)
            """,
            (new_label, old_label),
        )
        conn.commit()
        return cur.rowcount


def merge_root_keys(source_keys: list[str], target_key: str) -> int:
    target_label = clean_text(target_key)
    cleaned_sources = [clean_text(key) for key in source_keys if clean_text(key) and clean_text(key) != target_label]
    if not target_label or not cleaned_sources:
        return 0
    with get_connection(DB_PATH) as conn:
        total = 0
        for source_key in cleaned_sources:
            cur = conn.execute(
                """
                UPDATE word_senses
                SET root_key = ?
                WHERE lower(COALESCE(NULLIF(TRIM(root_key), ''), COALESCE(NULLIF(TRIM(word_root), ''), '未填写词根'))) = lower(?)
                """,
                (target_label, source_key),
            )
            total += cur.rowcount
        conn.commit()
        return total


def first_letter_counts() -> dict[str, int]:
    rows = fetch_all(
        """
        SELECT upper(substr(word, 1, 1)) AS first_letter, COUNT(*) AS word_count
        FROM words
        WHERE TRIM(word) <> ''
        GROUP BY upper(substr(word, 1, 1))
        """
    )
    counts = {letter: 0 for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}
    total = 0
    for row in rows:
        letter = clean_text(row.get("first_letter")).upper()
        count = int(row.get("word_count") or 0)
        if letter in counts:
            counts[letter] = count
        total += count
    counts["全部"] = total
    return counts


def _review_plan_source_rows() -> list[dict]:
    return fetch_all(
        """
        SELECT
            ws.id AS sense_id,
            w.id AS word_id,
            w.word,
            ws.core_meaning_cn,
            ws.part_of_speech,
            ws.core_meaning_en,
            COALESCE(ws.word_root, '') AS word_root,
            COALESCE(NULLIF(TRIM(ws.root_key), ''), COALESCE(NULLIF(TRIM(ws.word_root), ''), '未填写词根')) AS root_key,
            COALESCE(NULLIF(TRIM(ws.synonym_key), ''), ws.core_meaning_cn) AS synonym_key,
            ws.familiarity,
            ws.wrong_count,
            ws.review_status,
            ws.next_review_date
        FROM word_senses ws
        JOIN words w ON w.id = ws.word_id
        ORDER BY lower(w.word), ws.id
        """
    )


def create_review_plan(total_days: int, seed: int | None = None, name: str = "") -> dict[str, Any]:
    rows = _review_plan_source_rows()
    if not rows:
        raise ValueError("词库里还没有可复习的单词。")

    try:
        requested_days = int(total_days)
    except (TypeError, ValueError):
        requested_days = 1
    days = max(1, min(requested_days, len(rows)))
    plan_seed = int(seed if seed is not None else datetime.now().timestamp() * 1000)

    shuffled = list(rows)
    random.Random(plan_seed).shuffle(shuffled)

    base_size, extra = divmod(len(shuffled), days)
    assignments: list[tuple[int, int, int]] = []
    cursor = 0
    for day_number in range(1, days + 1):
        day_size = base_size + (1 if day_number <= extra else 0)
        day_rows = shuffled[cursor : cursor + day_size]
        cursor += day_size
        for display_order, row in enumerate(day_rows, 1):
            assignments.append((day_number, int(row["sense_id"]), display_order))

    plan_name = clean_text(name) or f"{days}天背词计划"
    with get_connection(DB_PATH) as conn:
        conn.execute("UPDATE review_plans SET status = 'archived' WHERE status = 'active'")
        cur = conn.execute(
            """
            INSERT INTO review_plans(name, total_days, seed, status)
            VALUES (?, ?, ?, 'active')
            """,
            (plan_name, days, plan_seed),
        )
        plan_id = int(cur.lastrowid)
        conn.executemany(
            """
            INSERT INTO review_plan_items(plan_id, day_number, sense_id, display_order)
            VALUES (?, ?, ?, ?)
            """,
            [(plan_id, day_number, sense_id, display_order) for day_number, sense_id, display_order in assignments],
        )
        conn.commit()

    return {
        "plan_id": plan_id,
        "name": plan_name,
        "total_days": days,
        "total_words": len(rows),
        "seed": plan_seed,
    }


def latest_review_plan() -> dict | None:
    return fetch_one(
        """
        SELECT rp.*, COUNT(rpi.id) AS total_words
        FROM review_plans rp
        LEFT JOIN review_plan_items rpi ON rpi.plan_id = rp.id
        WHERE rp.status = 'active'
        GROUP BY rp.id
        ORDER BY rp.id DESC
        LIMIT 1
        """
    )


def review_plan_day_counts(plan_id: int) -> dict[int, int]:
    plan = fetch_one("SELECT total_days FROM review_plans WHERE id = ?", (plan_id,))
    if not plan:
        return {}
    counts = {day: 0 for day in range(1, int(plan["total_days"]) + 1)}
    rows = fetch_all(
        """
        SELECT day_number, COUNT(*) AS word_count
        FROM review_plan_items
        WHERE plan_id = ?
        GROUP BY day_number
        ORDER BY day_number
        """,
        (plan_id,),
    )
    for row in rows:
        counts[int(row["day_number"])] = int(row["word_count"] or 0)
    return counts


def review_plan_words(plan_id: int, day_number: int) -> list[dict]:
    return fetch_all(
        """
        SELECT
            rpi.id AS plan_item_id,
            rpi.day_number,
            rpi.display_order,
            ws.id AS sense_id,
            w.id AS word_id,
            w.word,
            ws.core_meaning_cn,
            ws.part_of_speech,
            ws.core_meaning_en,
            COALESCE(ws.word_root, '') AS word_root,
            COALESCE(NULLIF(TRIM(ws.root_key), ''), COALESCE(NULLIF(TRIM(ws.word_root), ''), '未填写词根')) AS root_key,
            COALESCE(NULLIF(TRIM(ws.synonym_key), ''), ws.core_meaning_cn) AS synonym_key,
            ws.familiarity,
            ws.wrong_count,
            ws.review_status,
            ws.next_review_date
        FROM review_plan_items rpi
        JOIN word_senses ws ON ws.id = rpi.sense_id
        JOIN words w ON w.id = ws.word_id
        WHERE rpi.plan_id = ? AND rpi.day_number = ?
        ORDER BY rpi.display_order, lower(w.word), ws.id
        """,
        (plan_id, day_number),
    )


def delete_review_plan(plan_id: int) -> None:
    with get_connection(DB_PATH) as conn:
        conn.execute("DELETE FROM review_plans WHERE id = ?", (plan_id,))
        conn.commit()


def simple_dashboard_stats() -> dict:
    return {
        "total_words": fetch_one("SELECT COUNT(*) AS n FROM words")["n"],
        "total_entries": fetch_one("SELECT COUNT(*) AS n FROM word_senses")["n"],
        "total_meanings": fetch_one(
            """
            SELECT COUNT(*) AS n
            FROM (
                SELECT lower(core_meaning_cn)
                FROM word_senses
                WHERE TRIM(core_meaning_cn) <> '' AND core_meaning_cn <> 'Pending'
                GROUP BY lower(core_meaning_cn)
            )
            """
        )["n"],
        "total_roots": fetch_one(
            """
            SELECT COUNT(*) AS n
            FROM (
                SELECT lower(COALESCE(NULLIF(TRIM(root_key), ''), word_root))
                FROM word_senses
                WHERE TRIM(COALESCE(NULLIF(TRIM(root_key), ''), word_root, '')) <> ''
                GROUP BY lower(COALESCE(NULLIF(TRIM(root_key), ''), word_root))
            )
            """
        )["n"],
        "due_today": fetch_one("SELECT COUNT(*) AS n FROM word_senses WHERE DATE(next_review_date) <= DATE(?)", (today_iso(),))["n"],
        "mastered": fetch_one("SELECT COUNT(*) AS n FROM word_senses WHERE familiarity >= 4")["n"],
    }


def create_question(
    question_type: str,
    source: str,
    question_text: str,
    correct_answer: str = "",
    explanation: str = "",
    logic_structure: str = "",
    options: list[dict] | None = None,
) -> int:
    text = clean_text(question_text)
    if not text:
        raise ValueError("Question text is required.")
    with get_connection(DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO gre_questions(
                question_type, source, question_text, correct_answer,
                explanation, logic_structure
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                clean_text(question_type, "Other"),
                clean_text(source),
                text,
                clean_text(correct_answer),
                clean_text(explanation),
                clean_text(logic_structure),
            ),
        )
        question_id = int(cur.lastrowid)
        for option in options or []:
            option_text = clean_text(option.get("option_text"))
            if not option_text:
                continue
            conn.execute(
                """
                INSERT INTO question_options(
                    question_id, option_text, is_correct, explanation,
                    relation_note, linked_sense_id
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    question_id,
                    option_text,
                    1 if option.get("is_correct") else 0,
                    clean_text(option.get("explanation")),
                    clean_text(option.get("relation_note")),
                    option.get("linked_sense_id") or None,
                ),
            )
        conn.commit()
        return question_id


def list_questions(search: str = "") -> list[dict]:
    params: list[Any] = []
    where = ""
    if clean_text(search):
        like = f"%{search.lower()}%"
        where = """
        WHERE lower(question_text) LIKE ?
           OR lower(source) LIKE ?
           OR lower(correct_answer) LIKE ?
           OR lower(explanation) LIKE ?
           OR lower(logic_structure) LIKE ?
        """
        params.extend([like] * 5)
    return fetch_all(
        f"""
        SELECT gq.*,
               COUNT(DISTINCT wqr.id) AS linked_word_count,
               GROUP_CONCAT(DISTINCT w.word) AS linked_words
        FROM gre_questions gq
        LEFT JOIN word_question_relations wqr ON wqr.question_id = gq.id
        LEFT JOIN word_senses ws ON ws.id = wqr.sense_id
        LEFT JOIN words w ON w.id = ws.word_id
        {where}
        GROUP BY gq.id
        ORDER BY gq.date_added DESC, gq.id DESC
        """,
        params,
    )


def get_question(question_id: int) -> dict | None:
    return fetch_one("SELECT * FROM gre_questions WHERE id = ?", (question_id,))


def question_options(question_id: int) -> list[dict]:
    return fetch_all(
        """
        SELECT qo.*, w.word, ws.core_meaning_cn
        FROM question_options qo
        LEFT JOIN word_senses ws ON ws.id = qo.linked_sense_id
        LEFT JOIN words w ON w.id = ws.word_id
        WHERE qo.question_id = ?
        ORDER BY qo.id
        """,
        (question_id,),
    )


def update_question(question_id: int, **updates: Any) -> None:
    allowed = {"question_type", "source", "question_text", "correct_answer", "explanation", "logic_structure", "date_added"}
    fields = [key for key in updates if key in allowed]
    if not fields:
        return
    assignments = ", ".join(f"{field} = ?" for field in fields)
    params = [clean_text(updates[field]) for field in fields]
    params.append(question_id)
    with get_connection(DB_PATH) as conn:
        conn.execute(f"UPDATE gre_questions SET {assignments} WHERE id = ?", params)
        conn.commit()


def delete_question(question_id: int) -> None:
    with get_connection(DB_PATH) as conn:
        conn.execute("DELETE FROM gre_questions WHERE id = ?", (question_id,))
        conn.commit()


def link_sense_question(
    sense_id: int,
    question_id: int,
    role: str = "",
    context_sentence: str = "",
    personal_note: str = "",
) -> int:
    with get_connection(DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO word_question_relations(
                sense_id, question_id, role, context_sentence, personal_note
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(sense_id, question_id, role, context_sentence) DO UPDATE SET
                personal_note = excluded.personal_note
            """,
            (
                sense_id,
                question_id,
                clean_text(role),
                clean_text(context_sentence),
                clean_text(personal_note),
            ),
        )
        conn.commit()
        return int(cur.lastrowid or 0)


def question_context_rows() -> list[dict]:
    return fetch_all(
        """
        SELECT gq.id AS question_id, gq.question_type, gq.source, gq.question_text,
               gq.correct_answer, gq.explanation, gq.logic_structure, gq.date_added,
               w.word, ws.id AS sense_id, ws.part_of_speech, ws.core_meaning_cn,
               wqr.role, wqr.context_sentence, wqr.personal_note
        FROM gre_questions gq
        LEFT JOIN word_question_relations wqr ON wqr.question_id = gq.id
        LEFT JOIN word_senses ws ON ws.id = wqr.sense_id
        LEFT JOIN words w ON w.id = ws.word_id
        ORDER BY gq.date_added DESC, gq.id DESC, lower(w.word)
        """
    )


def due_senses() -> list[dict]:
    return word_bank_rows({"due_only": True, "sort_by": "Next Review"})


def record_review(
    sense_id: int,
    mode: str,
    rating: str,
    familiarity_after: int,
    next_review_date: str,
    wrong_delta: int = 0,
    note: str = "",
) -> None:
    sense = get_sense(sense_id)
    if not sense:
        raise ValueError("Word sense not found.")
    before_familiarity = int(sense["familiarity"])
    before_next = clean_text(sense["next_review_date"])
    with get_connection(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE word_senses
            SET familiarity = ?, wrong_count = wrong_count + ?,
                next_review_date = ?, review_status = ?, status = ?
            WHERE id = ?
            """,
            (
                clamp_familiarity(familiarity_after),
                max(0, int(wrong_delta)),
                clean_text(next_review_date, today_iso()),
                "mastered" if familiarity_after >= 4 else "learning",
                "learning",
                sense_id,
            ),
        )
        conn.execute(
            """
            INSERT INTO review_history(
                sense_id, mode, rating, familiarity_before, familiarity_after,
                next_review_before, next_review_after, wrong_delta, note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sense_id,
                clean_text(mode),
                clean_text(rating),
                before_familiarity,
                clamp_familiarity(familiarity_after),
                before_next,
                clean_text(next_review_date),
                max(0, int(wrong_delta)),
                clean_text(note),
            ),
        )
        conn.commit()


def review_history(sense_id: int | None = None) -> list[dict]:
    params: list[Any] = []
    where = ""
    if sense_id:
        where = "WHERE rh.sense_id = ?"
        params.append(sense_id)
    return fetch_all(
        f"""
        SELECT rh.*, w.word, ws.core_meaning_cn
        FROM review_history rh
        JOIN word_senses ws ON ws.id = rh.sense_id
        JOIN words w ON w.id = ws.word_id
        {where}
        ORDER BY rh.reviewed_at DESC
        """,
        params,
    )


def dashboard_stats() -> dict:
    stats = {
        "total_words": fetch_one("SELECT COUNT(*) AS n FROM words")["n"],
        "total_senses": fetch_one("SELECT COUNT(*) AS n FROM word_senses")["n"],
        "total_groups": fetch_one("SELECT COUNT(*) AS n FROM synonym_groups")["n"],
        "mastered_words": fetch_one("SELECT COUNT(*) AS n FROM word_senses WHERE familiarity >= 4")["n"],
        "learning_words": fetch_one("SELECT COUNT(*) AS n FROM word_senses WHERE familiarity < 4 AND status <> 'pending'")["n"],
        "due_today": fetch_one("SELECT COUNT(*) AS n FROM word_senses WHERE DATE(next_review_date) <= DATE(?)", (today_iso(),))["n"],
        "pending_words": fetch_one("SELECT COUNT(*) AS n FROM word_senses WHERE status = 'pending'")["n"],
        "total_questions": fetch_one("SELECT COUNT(*) AS n FROM gre_questions")["n"],
    }
    stats["weakest_groups"] = fetch_all(
        """
        SELECT sg.group_name_cn,
               COALESCE(l2.name_cn, '') AS level2_cn,
               COUNT(ws.id) AS sense_count,
               ROUND(MAX(0, MIN(100, AVG(ws.familiarity) * 25 - AVG(ws.wrong_count) * 5)), 0) AS strength_percent
        FROM synonym_groups sg
        JOIN synonym_memberships sm ON sm.group_id = sg.id
        JOIN word_senses ws ON ws.id = sm.sense_id
        LEFT JOIN semantic_categories l2 ON l2.id = sg.level2_id
        GROUP BY sg.id
        HAVING COUNT(ws.id) > 0
        ORDER BY strength_percent ASC, sense_count DESC
        LIMIT 8
        """
    )
    stats["recent_words"] = fetch_all(
        """
        SELECT w.word, ws.core_meaning_cn, ws.created_at
        FROM word_senses ws
        JOIN words w ON w.id = ws.word_id
        ORDER BY ws.created_at DESC
        LIMIT 10
        """
    )
    stats["most_wrong_words"] = fetch_all(
        """
        SELECT w.word, ws.core_meaning_cn, ws.wrong_count
        FROM word_senses ws
        JOIN words w ON w.id = ws.word_id
        WHERE ws.wrong_count > 0
        ORDER BY ws.wrong_count DESC, lower(w.word)
        LIMIT 10
        """
    )
    return stats


def global_search(query: str) -> dict[str, list[dict]]:
    search = clean_text(query)
    if not search:
        return {"word_senses": [], "groups": [], "questions": []}
    like = f"%{search.lower()}%"
    groups = fetch_all(
        """
        SELECT sg.*, l1.name_cn AS level1_cn, l1.name_en AS level1_en,
               l2.name_cn AS level2_cn, l2.name_en AS level2_en
        FROM synonym_groups sg
        LEFT JOIN semantic_categories l1 ON l1.id = sg.level1_id
        LEFT JOIN semantic_categories l2 ON l2.id = sg.level2_id
        WHERE lower(sg.group_name_cn) LIKE ?
           OR lower(sg.group_name_en) LIKE ?
           OR lower(sg.group_definition) LIKE ?
           OR lower(sg.notes) LIKE ?
           OR lower(COALESCE(l1.name_cn, '')) LIKE ?
           OR lower(COALESCE(l1.name_en, '')) LIKE ?
           OR lower(COALESCE(l2.name_cn, '')) LIKE ?
           OR lower(COALESCE(l2.name_en, '')) LIKE ?
        ORDER BY lower(sg.group_name_cn)
        """,
        [like] * 8,
    )
    return {
        "word_senses": word_bank_rows({"search": search, "sort_by": "Word"}),
        "groups": groups,
        "questions": list_questions(search),
    }
