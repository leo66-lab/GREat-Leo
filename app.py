from __future__ import annotations

import html
import os
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from modules import export_import
from modules import repository as repo
from modules import services
from modules.config import APP_NAME, DB_PATH, EXPORT_DIR


st.set_page_config(page_title=APP_NAME, page_icon="GRE", layout="wide")


DISPLAY_COLUMNS = {
    "word": "英文单词",
    "core_meaning_cn": "中文释义",
    "part_of_speech": "词性",
    "core_meaning_en": "英文释义",
    "word_root": "词根",
    "root_key": "词根索引",
    "root_variants": "词根写法",
    "synonym_key": "同义索引",
    "synonyms": "同义词",
    "added_date": "添加日期",
    "meaning_variants": "释义写法",
    "word_count": "数量",
    "english_words": "对应英文",
    "display_order": "序号",
    "day_number": "复习天数",
    "familiarity": "熟悉度",
    "wrong_count": "错误次数",
    "review_status": "复习状态",
    "next_review_date": "下次复习日期",
    "created_at": "创建时间",
    "updated_at": "更新时间",
    "line": "行号",
    "sense_id": "义项ID",
    "reason": "原因",
}

WORD_COLUMNS = ["word", "core_meaning_cn", "part_of_speech", "core_meaning_en", "word_root"]
WORD_BANK_COLUMNS = ["word", "added_date", "core_meaning_cn", "part_of_speech", "core_meaning_en", "word_root"]
SEARCH_COLUMNS = WORD_BANK_COLUMNS + ["synonyms"]
REVIEW_COLUMNS = WORD_COLUMNS + ["familiarity", "wrong_count", "next_review_date"]
PLAN_COLUMNS = ["display_order"] + WORD_COLUMNS + ["familiarity", "wrong_count", "next_review_date"]
LETTERS = ["全部"] + list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
PAGES = ["首页", "新增单词", "词库", "同义词", "同根词", "复习", "导出"]

REVIEW_MODE_LABELS = {
    "en_to_cn": "看英文回忆中文",
    "cn_to_en": "看中文回忆英文",
}

RATING_LABELS = {
    "Again": "重来",
    "Hard": "模糊",
    "Good": "认识",
    "Easy": "熟练",
}


def clear_data_cache() -> None:
    st.cache_data.clear()


@st.cache_data(ttl=20, show_spinner=False)
def cached_dashboard_stats() -> dict:
    return repo.simple_dashboard_stats()


@st.cache_data(ttl=20, show_spinner=False)
def cached_simple_word_rows(
    search: str = "",
    first_letter: str = "",
    root_key: str = "",
    added_from: str = "",
    added_to: str = "",
    sort_by: str = "word",
    due_only: bool = False,
    include_synonyms: bool = False,
) -> list[dict]:
    return repo.simple_word_rows(
        {
            "search": search,
            "first_letter": first_letter,
            "root_key": root_key,
            "added_from": added_from,
            "added_to": added_to,
            "sort_by": sort_by,
            "due_only": due_only,
            "include_synonyms": include_synonyms,
        }
    )


@st.cache_data(ttl=20, show_spinner=False)
def cached_first_letter_counts() -> dict[str, int]:
    return repo.first_letter_counts()


@st.cache_data(ttl=20, show_spinner=False)
def cached_synonym_index_rows(search: str = "") -> list[dict]:
    return repo.synonym_index_rows(search)


@st.cache_data(ttl=20, show_spinner=False)
def cached_root_index_rows(search: str = "") -> list[dict]:
    return repo.root_index_rows(search)


@st.cache_data(ttl=20, show_spinner=False)
def cached_words_for_synonym_key(synonym_key: str) -> list[dict]:
    return repo.words_for_synonym_key(synonym_key)


@st.cache_data(ttl=20, show_spinner=False)
def cached_words_for_root(root_key: str) -> list[dict]:
    return repo.words_for_root(root_key)


@st.cache_data(ttl=20, show_spinner=False)
def cached_latest_review_plan() -> dict | None:
    return repo.latest_review_plan()


@st.cache_data(ttl=20, show_spinner=False)
def cached_review_plan_day_counts(plan_id: int) -> dict[int, int]:
    return repo.review_plan_day_counts(plan_id)


@st.cache_data(ttl=20, show_spinner=False)
def cached_review_plan_words(plan_id: int, day_number: int) -> list[dict]:
    return repo.review_plan_words(plan_id, day_number)


def setup() -> None:
    if not st.session_state.get("_bootstrapped"):
        repo.ensure_bootstrap_data()
        st.session_state["_bootstrapped"] = True
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.25rem; padding-bottom: 2rem;}
        div[data-testid="stMetric"] {border: 1px solid #d9dee7; padding: 0.65rem 0.8rem; border-radius: 6px;}
        div[data-testid="stDataFrame"] {border: 1px solid #e5e7eb; border-radius: 6px;}
        label, .stTextInput label, .stSelectbox label, .stTextArea label {font-size: 0.92rem !important;}
        .home-kicker {font-size: 0.82rem; color: #5f6b7a; margin-bottom: 0.15rem;}
        .home-title {font-size: 1.55rem; font-weight: 700; margin: 0 0 0.85rem 0;}
        .home-metrics {display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.65rem; margin-bottom: 1rem;}
        .home-metric {border: 1px solid #d9dee7; border-radius: 6px; padding: 0.65rem 0.75rem; background: #ffffff;}
        .home-metric-label {font-size: 0.78rem; color: #667085; margin-bottom: 0.15rem;}
        .home-metric-value {font-size: 1.42rem; line-height: 1.15; font-weight: 700; color: #1f2937;}
        .home-metric-hint {font-size: 0.76rem; color: #667085; margin-top: 0.25rem;}
        .home-flow {display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 0.5rem; align-items: stretch; margin: 0.25rem 0 1rem 0;}
        .home-flow-step {border: 1px solid #d9dee7; border-radius: 6px; padding: 0.55rem; background: #f8fafc; min-height: 4.8rem;}
        .home-flow-step strong {display: block; font-size: 0.9rem; color: #1f2937; margin-bottom: 0.25rem;}
        .home-flow-step span {font-size: 0.78rem; color: #667085;}
        .guide-grid {display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.8rem;}
        .guide-section {border-top: 1px solid #d9dee7; padding-top: 0.7rem;}
        .guide-section h3 {font-size: 1rem; margin: 0 0 0.35rem 0;}
        .guide-section p {font-size: 0.9rem; line-height: 1.65; margin: 0; color: #344054;}
        .home-side {border-left: 1px solid #d9dee7; padding-left: 1rem;}
        .home-side-title {font-size: 1rem; font-weight: 700; margin-bottom: 0.6rem;}
        .home-side-note {font-size: 0.82rem; color: #667085; line-height: 1.55; margin-top: 0.8rem;}
        @media (max-width: 900px) {
            .home-metrics, .guide-grid, .home-flow {grid-template-columns: 1fr;}
            .home-side {border-left: 0; padding-left: 0; border-top: 1px solid #d9dee7; padding-top: 1rem;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def frame(rows: list[dict], columns: list[str] | None = None) -> pd.DataFrame:
    data = pd.DataFrame(rows) if rows else pd.DataFrame(columns=columns or [])
    if columns:
        for column in columns:
            if column not in data.columns:
                data[column] = ""
        data = data[columns]
    return data.rename(columns=DISPLAY_COLUMNS)


def show_table(rows: list[dict], columns: list[str] | None = None) -> None:
    st.dataframe(frame(rows, columns), width="stretch", hide_index=True)


def get_admin_password() -> str:
    try:
        secret_value = st.secrets.get("APP_ADMIN_PASSWORD", "")
    except Exception:  # noqa: BLE001 - Streamlit raises when secrets are unavailable.
        secret_value = ""
    return str(secret_value or os.environ.get("APP_ADMIN_PASSWORD", "")).strip()


def is_admin() -> bool:
    password = get_admin_password()
    if not password:
        return True
    return bool(st.session_state.get("is_admin"))


def require_admin(action: str = "这个操作") -> bool:
    if is_admin():
        return True
    st.warning(f"{action}需要管理员权限。请先在左侧登录。")
    return False


def render_admin_login() -> None:
    password = get_admin_password()
    st.sidebar.divider()
    st.sidebar.caption("权限")
    if not password:
        st.sidebar.caption("本地管理员模式：未设置公网密码。")
        st.session_state["is_admin"] = True
        return
    if is_admin():
        st.sidebar.success("管理员已登录")
        if st.sidebar.button("退出管理员"):
            st.session_state["is_admin"] = False
            st.rerun()
        return
    with st.sidebar.form("admin_login_form"):
        candidate = st.text_input("管理员密码", type="password")
        submitted = st.form_submit_button("登录")
    if submitted:
        if candidate == password:
            st.session_state["is_admin"] = True
            st.sidebar.success("已登录")
            st.rerun()
        else:
            st.sidebar.error("密码不正确")


def word_label(row: dict) -> str:
    return f"{row['word']} | {row['core_meaning_cn']} | #{row['sense_id']}"


def id_from_label(label: str) -> int | None:
    if "#" not in label:
        return None
    try:
        return int(label.rsplit("#", 1)[1])
    except ValueError:
        return None


def clamp_int(value: object, minimum: int, maximum: int, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(number, maximum))


def repo_get_setting(key: str, default: str = "") -> str:
    getter = getattr(repo, "get_setting", None)
    return getter(key, default) if callable(getter) else default


def repo_get_int_setting(key: str, default: int = 0) -> int:
    getter = getattr(repo, "get_int_setting", None)
    if callable(getter):
        return getter(key, default)
    return default


def repo_set_setting(key: str, value: object) -> None:
    setter = getattr(repo, "set_setting", None)
    if callable(setter):
        setter(key, value)


def review_setting_key(plan_id: int, name: str) -> str:
    return f"review_plan:{plan_id}:{name}"


def load_review_day(plan_id: int, total_days: int) -> int | None:
    raw_value = st.session_state.get("review_day")
    if raw_value is None:
        saved_value = repo_get_setting(review_setting_key(plan_id, "day"))
        if not saved_value:
            return None
        raw_value = saved_value
    return clamp_int(raw_value, 1, total_days, 1)


def load_review_card_index(plan_id: int, word_count: int) -> int:
    if word_count <= 0:
        return 0
    raw_value = st.session_state.get("review_card_index")
    if raw_value is None:
        raw_value = repo_get_int_setting(review_setting_key(plan_id, "card_index"), 0)
    return clamp_int(raw_value, 0, word_count - 1, 0)


def save_review_position(plan_id: int, day_number: int, card_index: int) -> None:
    st.session_state["review_day"] = day_number
    st.session_state["review_card_index"] = card_index
    if not is_admin():
        return
    repo_set_setting(review_setting_key(plan_id, "day"), day_number)
    repo_set_setting(review_setting_key(plan_id, "card_index"), card_index)


def go_to_page(page_name: str) -> None:
    st.session_state["_page_request"] = page_name
    st.rerun()


def page_dashboard() -> None:
    stats = cached_dashboard_stats()
    plan = cached_latest_review_plan()
    today_review_count = "∞"
    review_caption = "还没有选择复习计划或 Day，今日目标暂不设上限。"
    if plan:
        day_number = load_review_day(int(plan["id"]), int(plan["total_days"]))
    else:
        day_number = None
    if plan and day_number:
        counts = cached_review_plan_day_counts(int(plan["id"]))
        today_review_count = counts.get(day_number, 0)
        review_caption = f"当前连接到复习计划：{plan['name']}，Day {day_number}。"

    review_caption_html = html.escape(review_caption)
    main_col, side_col = st.columns([2.35, 0.85], gap="large")

    with main_col:
        st.markdown(
            f"""
            <div class="home-kicker">GRE Vocabulary System</div>
            <div class="home-title">今天你背单词了么</div>
            <div class="home-metrics">
                <div class="home-metric">
                    <div class="home-metric-label">总单词数量</div>
                    <div class="home-metric-value">{int(stats["total_entries"])}</div>
                </div>
                <div class="home-metric">
                    <div class="home-metric-label">今日需复习单词数量</div>
                    <div class="home-metric-value">{today_review_count}</div>
                    <div class="home-metric-hint">{review_caption_html}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.subheader("使用流程")
        st.markdown(
            """
            <div class="home-flow">
                <div class="home-flow-step"><strong>新增单词</strong><span>把做题遇到的生词补进系统</span></div>
                <div class="home-flow-step"><strong>词库</strong><span>按单词、释义、词根检索</span></div>
                <div class="home-flow-step"><strong>同义词 / 同根词</strong><span>按语义和构词法成组回看</span></div>
                <div class="home-flow-step"><strong>复习计划</strong><span>打乱词库并按天均分</span></div>
                <div class="home-flow-step"><strong>导出</strong><span>把当前资料保存为 Excel</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.subheader("网站使用教程")
        st.markdown(
            """
            <div class="guide-grid">
                <div class="guide-section">
                    <h3>复习计划：记忆引擎</h3>
                    <p>先进入“复习”，输入想要完成词库的天数，生成背词计划。系统会把当前词库打乱后尽量均分到每个 Day，避免按首字母顺序背词造成记忆偏差。</p>
                </div>
                <div class="guide-section">
                    <h3>词库：基础搜索引擎</h3>
                    <p>用“词库”查英文单词、中文释义、英文释义和词根。搜索某个词时，下方会并列显示同义词条，方便把单个词放回语义网络里看。</p>
                </div>
                <div class="guide-section">
                    <h3>同义词 / 同根词：扩展搜索引擎</h3>
                    <p>“同义词”按相近中文意思分组，适合 GRE 填空和等价句辨析；“同根词”按前缀、后缀或词根分组，适合从构词法角度批量记忆。</p>
                </div>
                <div class="guide-section">
                    <h3>新增单词：补充燃料</h3>
                    <p>做题遇到生词后，按“英文单词、中文释义、词性、英文释义、词根”的格式录入或批量导入。保存后会进入词库，并参与同义词、同根词和下一次复习计划。</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with side_col:
        st.markdown('<div class="home-side-title">快捷入口</div>', unsafe_allow_html=True)
        shortcuts = [
            ("复习", "生成计划"),
            ("词库", "查单词"),
            ("同义词", "按意思查"),
            ("同根词", "按词根查"),
            ("新增单词", "补充词库"),
            ("导出", "导出 Excel"),
        ]
        for page_name, label in shortcuts:
            if st.button(label, key=f"home_link_{page_name}", width="stretch"):
                go_to_page(page_name)
        st.markdown(
            '<div class="home-side-note">建议先生成复习计划，再用词库、同义词和同根词做检索补强。</div>',
            unsafe_allow_html=True,
        )


def page_add_word() -> None:
    st.title("新增单词")
    if not require_admin("新增和导入单词"):
        return
    single_tab, quick_tab = st.tabs(["单个录入", "快速导入"])

    with single_tab:
        with st.form("single_word_form", clear_on_submit=False):
            c1, c2 = st.columns(2)
            with c1:
                word = st.text_input("英文单词", placeholder="abate")
                meaning_cn = st.text_input("中文释义", placeholder="减弱；缓和")
                pos = st.text_input("词性", placeholder="v.")
            with c2:
                meaning_en = st.text_area("英文释义", height=88, placeholder="to become less intense or widespread")
                root = st.text_input("词根", placeholder="bat / bate")
            submitted = st.form_submit_button("保存单词", type="primary")

        if submitted:
            try:
                result = services.create_simple_word_entry(
                    word=word,
                    core_meaning_cn=meaning_cn,
                    part_of_speech=pos,
                    core_meaning_en=meaning_en,
                    word_root=root,
                )
                action = "更新" if result["updated"] else "新增"
                clear_data_cache()
                st.success(f"已{action}：{word}。")
            except Exception as exc:  # noqa: BLE001
                st.error(f"保存失败：{exc}")

    with quick_tab:
        st.subheader("快速导入模板")
        st.write("每行一个词条，字段顺序固定为：英文单词、中文释义、词性、英文释义、词根。")
        st.code(
            "英文单词\t中文释义\t词性\t英文释义\t词根\n"
            "abate\t减弱；缓和\tv.\tto become less intense or widespread\tbat/bate\n"
            "laconic\t简洁的；言简意赅的\tadj.\tusing very few words\tlac",
            language="text",
        )
        st.caption("推荐用 Tab 分隔；也支持英文逗号分隔或竖线分隔。")
        raw_text = st.text_area("粘贴导入内容", height=220)
        uploaded = st.file_uploader("也可以上传 .csv、.xlsx 或 .txt", type=["csv", "xlsx", "xls", "txt"])

        uploaded_text = ""
        if uploaded:
            suffix = Path(uploaded.name).suffix.lower()
            if suffix == ".txt":
                uploaded_text = uploaded.getvalue().decode("utf-8-sig", errors="ignore")
                st.caption("已读取文本文件；点击“导入粘贴内容”后导入。")
            else:
                if st.button("导入上传文件"):
                    try:
                        result = export_import.import_file(uploaded, uploaded.name)
                        clear_data_cache()
                        st.success(
                            f"文件导入完成：新增 {result['created']} 条，更新 {result['updated']} 条，跳过 {result['skipped']} 条。"
                        )
                        if result["notes"]:
                            show_table(result["notes"], ["line", "word", "reason"])
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"文件导入失败：{exc}")

        if st.button("导入粘贴内容", type="primary"):
            try:
                result = services.batch_import_simple_words("\n".join([raw_text, uploaded_text]).strip())
                clear_data_cache()
                st.success(
                    f"处理 {result['seen']} 行，新增 {len(result['created'])} 条，更新 {len(result['updated'])} 条，跳过 {len(result['skipped'])} 条。"
                )
                if result["created"]:
                    st.caption("新增")
                    show_table(result["created"], ["line", "word", "sense_id"])
                if result["updated"]:
                    st.caption("更新")
                    show_table(result["updated"], ["line", "word", "sense_id"])
                if result["skipped"]:
                    st.caption("跳过")
                    show_table(result["skipped"], ["line", "word", "reason"])
            except Exception as exc:  # noqa: BLE001
                st.error(f"导入失败：{exc}")


def page_word_bank() -> None:
    st.title("词库")
    c1, c2, c3 = st.columns([1.4, 1, 1])
    with c1:
        search = st.text_input("搜索单词 / 释义 / 词根")
    letter_counts = cached_first_letter_counts()
    with c2:
        first_letter = st.selectbox("首字母索引", LETTERS, format_func=lambda value: f"{value} ({letter_counts.get(value, 0)})")
    root_index_rows = cached_root_index_rows()
    root_counts = {"全部": sum(int(row["word_count"]) for row in root_index_rows)}
    root_counts.update({row["root_key"]: int(row["word_count"]) for row in root_index_rows})
    roots = ["全部"] + [row["root_key"] for row in root_index_rows]
    with c3:
        root = st.selectbox(
            "词根筛选",
            roots,
            format_func=lambda value: f"{value} ({root_counts.get(value, 0)})",
        )
    d1, d2, d3 = st.columns([1, 1, 2])
    with d1:
        added_from_value = st.date_input("添加日期起", value=None, format="YYYY-MM-DD")
    with d2:
        added_to_value = st.date_input("添加日期止", value=None, format="YYYY-MM-DD")
    added_from = added_from_value.isoformat() if isinstance(added_from_value, date) else ""
    added_to = added_to_value.isoformat() if isinstance(added_to_value, date) else ""
    with d3:
        if added_from and added_to and added_from > added_to:
            st.warning("开始日期不能晚于结束日期。")

    is_searching = bool(repo.clean_text(search))
    rows = cached_simple_word_rows(
        search=search,
        first_letter=first_letter,
        root_key=root,
        added_from=added_from,
        added_to=added_to,
        sort_by="word",
        include_synonyms=is_searching,
    )
    st.caption(f"共 {len(rows)} 条，按英文首字母顺序排列。")

    if is_searching and rows:
        st.subheader("搜索结果")
        show_table(rows, SEARCH_COLUMNS)
        st.subheader("同义词条")
        synonym_keys = []
        for row in rows:
            key = repo.clean_text(row.get("synonym_key"))
            if key and key not in synonym_keys:
                synonym_keys.append(key)
        for key in synonym_keys:
            group_rows = cached_words_for_synonym_key(key)
            st.markdown(f"#### {key}")
            show_table(group_rows, WORD_COLUMNS)
    else:
        show_table(rows, WORD_BANK_COLUMNS)

    st.divider()
    if not is_admin():
        st.caption("当前为浏览模式：新增、编辑、删除需要管理员登录。")
        return

    st.subheader("编辑 / 删除")
    if not rows:
        st.info("当前筛选下没有可编辑词条。")
        return

    options = {word_label(row): row for row in rows}
    selected = st.selectbox("选择词条", list(options.keys()))
    item = repo.simple_word_detail(id_from_label(selected) or 0)
    if not item:
        st.warning("没有找到这个词条。")
        return

    with st.form(f"edit_word_{item['sense_id']}"):
        c1, c2 = st.columns(2)
        with c1:
            word = st.text_input("英文单词", value=item["word"])
            meaning_cn = st.text_input("中文释义", value=item["core_meaning_cn"])
            pos = st.text_input("词性", value=item["part_of_speech"])
        with c2:
            meaning_en = st.text_area("英文释义", value=item["core_meaning_en"], height=88)
            root_value = st.text_input("词根", value=item["word_root"])
        submitted = st.form_submit_button("保存修改", type="primary")

    if submitted:
        try:
            repo.update_word(int(item["word_id"]), word=word)
            repo.update_sense(
                int(item["sense_id"]),
                core_meaning_cn=meaning_cn,
                part_of_speech=pos,
                core_meaning_en=meaning_en,
                word_root=root_value,
                root_key=item["root_key"] if root_value == item["word_root"] else repo.derive_root_key(word, root_value),
                synonym_key=item["synonym_key"] if meaning_cn == item["core_meaning_cn"] else repo.derive_synonym_key(meaning_cn),
                status="learning",
                review_status="learning",
            )
            clear_data_cache()
            st.success("已保存修改。")
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"保存失败：{exc}")

    if st.button("删除这个词条"):
        repo.delete_simple_entry(int(item["sense_id"]))
        clear_data_cache()
        st.warning("已删除。")
        st.rerun()


def page_synonyms() -> None:
    st.title("同义词")
    left, right = st.columns([0.9, 2.1])
    with left:
        search = st.text_input("筛选中文释义 / 同义索引")
        index_rows = cached_synonym_index_rows(search)
        if not index_rows:
            st.info("还没有可用的中文释义索引。")
            return
        options = {row["synonym_key"]: row for row in index_rows}
        selected = st.selectbox(
            "同义索引",
            list(options.keys()),
            format_func=lambda value: f"{value} ({options[value]['word_count']})",
        )
        st.caption("索引按程序归并后的中文含义分组，不再要求原始中文释义完全相同。")

    with right:
        st.subheader(selected)
        st.caption(f"包含的释义写法：{options[selected]['meaning_variants']}")
        members = cached_words_for_synonym_key(selected)
        show_table(members, ["word", "core_meaning_cn", "part_of_speech", "core_meaning_en", "word_root"])

        if is_admin():
            with st.expander("调整同义索引"):
                new_name = st.text_input("重命名当前索引", value=selected)
                if st.button("保存索引名称"):
                    try:
                        updated = repo.rename_synonym_key(selected, new_name)
                        clear_data_cache()
                        st.success(f"已更新 {updated} 个词条。")
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"保存失败：{exc}")

                other_keys = [row["synonym_key"] for row in index_rows if row["synonym_key"] != selected]
                merge_sources = st.multiselect("把这些索引并入当前索引", other_keys)
                if st.button("合并到当前索引"):
                    updated = repo.merge_synonym_keys(merge_sources, selected)
                    clear_data_cache()
                    st.success(f"已合并 {updated} 个词条。")
                    st.rerun()
        else:
            st.caption("当前为浏览模式：调整同义索引需要管理员登录。")


def page_roots() -> None:
    st.title("同根词")
    left, right = st.columns([0.9, 2.1])
    with left:
        search = st.text_input("筛选前缀 / 后缀 / 词根索引")
        index_rows = cached_root_index_rows(search)
        if not index_rows:
            st.info("还没有可用的词根索引。")
            return
        options = {row["root_key"]: row for row in index_rows}
        selected = st.selectbox(
            "词根索引",
            list(options.keys()),
            format_func=lambda value: f"{value} ({options[value]['word_count']})",
        )
        st.caption("索引按程序提炼出的前缀、后缀或词根分组，不要求原始词根写法完全一致。")

    with right:
        st.subheader(selected)
        st.caption(f"包含的词根写法：{options[selected]['root_variants']}")
        members = cached_words_for_root(selected)
        show_table(members, ["word", "word_root", "core_meaning_cn", "part_of_speech", "core_meaning_en"])

        if is_admin():
            with st.expander("调整词根索引"):
                new_name = st.text_input("重命名当前索引", value=selected)
                if st.button("保存词根索引名称"):
                    try:
                        updated = repo.rename_root_key(selected, new_name)
                        clear_data_cache()
                        st.success(f"已更新 {updated} 个词条。")
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"保存失败：{exc}")

                other_keys = [row["root_key"] for row in index_rows if row["root_key"] != selected]
                merge_sources = st.multiselect("把这些索引并入当前索引", other_keys)
                if st.button("合并到当前词根索引"):
                    updated = repo.merge_root_keys(merge_sources, selected)
                    clear_data_cache()
                    st.success(f"已合并 {updated} 个词条。")
                    st.rerun()
        else:
            st.caption("当前为浏览模式：调整词根索引需要管理员登录。")


def page_review() -> None:
    st.title("复习")
    stats = cached_dashboard_stats()
    total_words = int(stats["total_entries"] or 0)
    if total_words <= 0:
        st.info("词库里还没有单词，先去新增单词。")
        return

    plan = cached_latest_review_plan()
    st.subheader("制定背词计划")
    c1, c2 = st.columns([1, 2])
    with c1:
        max_days = max(1, total_words)
        fallback_days = int(plan["total_days"]) if plan else min(30, max_days)
        default_days = clamp_int(repo_get_int_setting("review_days", fallback_days), 1, max_days, fallback_days)
        review_days = st.number_input(
            "想要复习天数",
            min_value=1,
            max_value=max_days,
            value=default_days,
            step=1,
            key="review_days_input",
        )
        if int(review_days) != repo_get_int_setting("review_days", default_days):
            repo_set_setting("review_days", int(review_days))
    with c2:
        st.caption(f"当前词库共有 {total_words} 条词条。生成计划时会先打乱，再按天数尽量均分。")
        can_write = is_admin()
        if not can_write:
            st.caption("当前为浏览模式：生成或重排计划需要管理员登录。")
        if st.button("生成 / 重排背词计划", type="primary", disabled=not can_write):
            try:
                plan_result = repo.create_review_plan(int(review_days))
                clear_data_cache()
                repo_set_setting("review_days", plan_result["total_days"])
                save_review_position(int(plan_result["plan_id"]), 1, 0)
                st.session_state["review_revealed"] = False
                st.success(
                    f"已生成 {plan_result['total_days']} 天计划，共 {plan_result['total_words']} 条词。"
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"生成失败：{exc}")

    plan = cached_latest_review_plan()
    if not plan:
        st.info("还没有背词计划。设置天数后点击“生成 / 重排背词计划”。")
        return

    plan_id = int(plan["id"])
    total_days = int(plan["total_days"])
    counts = cached_review_plan_day_counts(plan_id)
    current_day = load_review_day(plan_id, total_days) or 1
    st.session_state["review_day"] = current_day
    if not repo_get_setting(review_setting_key(plan_id, "day")):
        repo_set_setting(review_setting_key(plan_id, "day"), current_day)

    st.divider()
    st.subheader("Day 索引")
    st.caption(f"当前计划：{plan['name']}；共 {int(plan['total_words'])} 条词，{total_days} 天。")

    if total_days <= 60:
        day_cols = st.columns(7)
        for day_number in range(1, total_days + 1):
            with day_cols[(day_number - 1) % 7]:
                label = f"Day {day_number} ({counts.get(day_number, 0)}词)"
                button_type = "primary" if day_number == current_day else "secondary"
                if st.button(label, key=f"review_day_{plan_id}_{day_number}", type=button_type, width="stretch"):
                    save_review_position(plan_id, day_number, 0)
                    st.session_state["review_revealed"] = False
                    st.rerun()
    else:
        selected_day = st.selectbox(
            "选择 Day",
            list(range(1, total_days + 1)),
            index=current_day - 1,
            format_func=lambda value: f"Day {value} ({counts.get(value, 0)}词)",
        )
        if selected_day != current_day:
            save_review_position(plan_id, int(selected_day), 0)
            st.session_state["review_revealed"] = False
            current_day = int(selected_day)

    current_day = load_review_day(plan_id, total_days) or current_day
    day_rows = cached_review_plan_words(plan_id, current_day)
    st.subheader(f"Day {current_day} 单词列表")
    show_table(day_rows, PLAN_COLUMNS)
    if not day_rows:
        st.info("这一天没有分到单词。")
        return

    st.subheader("背诵词卡")
    current_index = load_review_card_index(plan_id, len(day_rows))
    st.session_state["review_card_index"] = current_index
    labels = [f"{row['display_order']}. {row['word']} | {row['core_meaning_cn']}" for row in day_rows]
    selected_label = st.selectbox("进入词卡", labels, index=current_index)
    selected_index = labels.index(selected_label)
    if selected_index != current_index:
        save_review_position(plan_id, current_day, selected_index)
        st.session_state["review_revealed"] = False
        current_index = selected_index

    item = day_rows[current_index]
    mode = st.selectbox(
        "词卡模式",
        list(REVIEW_MODE_LABELS.keys()),
        format_func=lambda value: REVIEW_MODE_LABELS[value],
    )
    front_text = item["core_meaning_cn"] if mode == "cn_to_en" else item["word"]
    st.progress((current_index + 1) / len(day_rows), text=f"Day {current_day}：{current_index + 1} / {len(day_rows)}")
    st.markdown(f"## {front_text}")

    nav_cols = st.columns([1, 1, 2])
    with nav_cols[0]:
        if st.button("上一张", disabled=current_index == 0):
            save_review_position(plan_id, current_day, current_index - 1)
            st.session_state["review_revealed"] = False
            st.rerun()
    with nav_cols[1]:
        if st.button("下一张", disabled=current_index >= len(day_rows) - 1):
            save_review_position(plan_id, current_day, current_index + 1)
            st.session_state["review_revealed"] = False
            st.rerun()
    with nav_cols[2]:
        if st.button("显示答案", type="primary"):
            st.session_state["review_revealed"] = True

    if st.session_state.get("review_revealed"):
        show_table([item], REVIEW_COLUMNS)
        if is_admin():
            rating_cols = st.columns(4)
            for rating, col in zip(["Again", "Hard", "Good", "Easy"], rating_cols):
                with col:
                    if st.button(RATING_LABELS[rating], key=f"plan_review_{rating}_{item['sense_id']}", width="stretch"):
                        result = services.apply_review_result(int(item["sense_id"]), REVIEW_MODE_LABELS[mode], rating)
                        clear_data_cache()
                        save_review_position(plan_id, current_day, current_index)
                        st.session_state["review_revealed"] = False
                        st.success(f"已更新熟悉度为 {result['familiarity']}；下次复习 {result['next_review_date']}。")
        else:
            st.caption("当前为浏览模式：熟悉度打分和复习记录更新需要管理员登录。")

    with st.expander("今日到期队列"):
        due = cached_simple_word_rows(due_only=True, sort_by="review")
        if due:
            show_table(due, REVIEW_COLUMNS)
        else:
            st.success("今天没有到期词。")


def page_export() -> None:
    st.title("导出")
    if st.button("导出 Excel", type="primary"):
        try:
            path = export_import.export_to_excel()
            verification = export_import.verify_export(path)
            st.success(f"已导出：{path}")
            st.write({"文件位置": verification["path"], "缺失工作表": verification["missing_sheets"], "各工作表行数": verification["sheet_rows"]})
            with open(path, "rb") as handle:
                st.download_button("下载 Excel", handle, file_name=Path(path).name)
        except Exception as exc:  # noqa: BLE001
            st.error(f"导出失败：{exc}")
    st.caption(f"数据库：{DB_PATH}")
    st.caption(f"导出目录：{EXPORT_DIR}")


def main() -> None:
    setup()
    st.sidebar.title(APP_NAME)
    render_admin_login()
    requested_page = st.session_state.pop("_page_request", None)
    if requested_page in PAGES:
        st.session_state["active_page"] = requested_page
    page = st.sidebar.radio("导航", PAGES, key="active_page")

    if page == "首页":
        page_dashboard()
    elif page == "新增单词":
        page_add_word()
    elif page == "词库":
        page_word_bank()
    elif page == "同义词":
        page_synonyms()
    elif page == "同根词":
        page_roots()
    elif page == "复习":
        page_review()
    elif page == "导出":
        page_export()


if __name__ == "__main__":
    main()
