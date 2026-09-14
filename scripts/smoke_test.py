from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import load_workbook


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from modules import export_import  # noqa: E402
from modules import repository as repo  # noqa: E402
from modules import services  # noqa: E402
from modules.config import DB_PATH, EXPORT_DIR  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    repo.ensure_bootstrap_data()

    services.create_simple_word_entry(
        word="abate",
        core_meaning_cn="减弱；缓和",
        part_of_speech="v.",
        core_meaning_en="to become less intense or widespread",
        word_root="bat/bate",
    )
    services.create_simple_word_entry(
        word="abate",
        core_meaning_cn="削弱",
        part_of_speech="v.",
        core_meaning_en="to reduce in force",
        word_root="bate",
    )
    batch_result = services.batch_import_simple_words(
        "英文单词\t中文释义\t词性\t英文释义\t词根\n"
        "mitigate\t减轻；缓解\tv.\tto make something less severe\tmit/mis\n"
        "laconic\t简洁的；言简意赅的\tadj.\tusing very few words\tlac\n"
        "remiss\t疏忽的；玩忽职守的\tadj.\tlacking care or attention to duty\tmiss"
    )

    word_rows = repo.simple_word_rows({"search": "abate"})
    abate_rows = [row for row in word_rows if row["word"].lower() == "abate"]
    assert_true(len(abate_rows) == 1, "same English word should be merged into one entry")
    assert_true("削弱" in abate_rows[0]["core_meaning_cn"], "merged Chinese meaning missing")

    synonym_rows = repo.words_for_synonym_key(repo.derive_synonym_key("减弱；缓和"))
    assert_true(
        {"abate", "mitigate"}.issubset({row["word"].lower() for row in synonym_rows}),
        "synonym grouping by merged Chinese meaning failed",
    )

    letter_counts = repo.first_letter_counts()
    assert_true(letter_counts["A"] >= 1 and letter_counts["全部"] >= letter_counts["A"], "first-letter counts failed")

    root_rows = repo.words_for_root(repo.derive_root_key("laconic", "lac"))
    assert_true(any(row["word"].lower() == "laconic" for row in root_rows), "root grouping failed")
    mit_root_rows = repo.words_for_root(repo.derive_root_key("mitigate", "mit/mis"))
    assert_true(
        {"mitigate", "remiss"}.issubset({row["word"].lower() for row in mit_root_rows}),
        "merged root grouping failed",
    )

    due_rows = repo.simple_word_rows({"due_only": True, "sort_by": "review"})
    assert_true(len(due_rows) >= 1, "review queue should not be empty")

    export_path = export_import.export_to_excel()
    verification = export_import.verify_export(export_path)
    assert_true(not verification["missing_sheets"], f"missing export sheets: {verification['missing_sheets']}")

    workbook = load_workbook(export_path)
    word_bank_sheet = workbook["01_单词库"]
    assert_true(word_bank_sheet.freeze_panes == "A2", "word bank freeze panes missing")
    assert_true(bool(word_bank_sheet.auto_filter.ref), "word bank autofilter missing")

    print("Smoke test passed")
    print(f"Database: {DB_PATH}")
    print(f"Batch result: {batch_result}")
    print(f"Export: {export_path}")
    print(f"Export directory: {EXPORT_DIR}")


if __name__ == "__main__":
    main()
