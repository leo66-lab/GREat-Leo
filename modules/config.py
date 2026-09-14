from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "gre_vocab.db"
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = BASE_DIR / "exports"
BACKUP_DIR = BASE_DIR / "backups"

APP_NAME = "GRE 词汇系统"

FAMILIARITY_LABELS = {
    0: "0 - 完全不认识",
    1: "1 - 眼熟，无法主动回忆",
    2: "2 - 能回忆大意",
    3: "3 - 基本掌握",
    4: "4 - GRE 做题中能快速反应",
}

BASE_REVIEW_INTERVALS = {
    0: 1,
    1: 1,
    2: 3,
    3: 7,
    4: 21,
}

QUESTION_TYPES = ["TC", "SE", "RC", "CR", "词汇", "上下文", "其他"]

DEFAULT_LEVEL_1_CATEGORIES = [
    ("Positive", "正向"),
    ("Negative", "负向"),
    ("Increase", "增加"),
    ("Decrease", "减少"),
    ("Support", "支持"),
    ("Oppose", "反对"),
    ("Clear", "清晰"),
    ("Unclear", "模糊"),
    ("Change", "变化"),
    ("Stability", "稳定"),
    ("Emotion", "情绪"),
    ("Knowledge", "知识"),
    ("Communication", "交流"),
    ("Character", "性格"),
]
