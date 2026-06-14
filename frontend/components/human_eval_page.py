"""
人工评测页面组件
Human Evaluation Page Component

从 金融监管评测集.xlsx 读取评测题与 AI 答案，提供人工评测输入列，
并支持本地持久化保存评测结果。
"""

import streamlit as st

from utils.eval_loader import (
    EVAL_OPTIONS,
    load_cached_results,
    load_evaluation_set,
    get_evaluation_summary,
    save_cached_results,
    clear_cached_results,
)


def _ensure_state() -> None:
    """初始化会话状态。"""
    if "human_eval_data" not in st.session_state:
        st.session_state.human_eval_data = None
    if "human_eval_search" not in st.session_state:
        st.session_state.human_eval_search = ""
    if "human_eval_filter" not in st.session_state:
        st.session_state.human_eval_filter = "全部"
    if "human_eval_page" not in st.session_state:
        st.session_state.human_eval_page = 1
    if "human_eval_page_size" not in st.session_state:
        st.session_state.human_eval_page_size = 10
    if "human_eval_dirty" not in st.session_state:
        st.session_state.human_eval_dirty = False
    if "human_eval_show_answer" not in st.session_state:
        st.session_state.human_eval_show_answer = {}


def _load_data(force: bool = False) -> list:
    """从 xlsx 加载评测数据（带 session_state 缓存）。"""
    if force or st.session_state.human_eval_data is None:
        try:
            items = load_evaluation_set()
        except FileNotFoundError as e:
            st.error(str(e))
            return []
        except ImportError as e:
            st.error(str(e))
            return []
        except Exception as e:
            st.error(f"加载评测集失败: {e}")
            return []
        st.session_state.human_eval_data = items
    return st.session_state.human_eval_data or []


def _apply_filters(items: list) -> list:
    """根据搜索 + 评测状态过滤。"""
    search = (st.session_state.human_eval_search or "").strip().lower()
    eval_filter = st.session_state.human_eval_filter
    filtered = []
    for item in items:
        # 状态过滤
        if eval_filter != "全部":
            cur = (item.get("human_eval") or "").strip()
            if eval_filter == "未评测":
                if cur:
                    continue
            elif cur != eval_filter:
                continue
        # 关键词过滤（题目 / 答案 / AI 回答）
        if search:
            haystack = " ".join([
                item.get("question", ""),
                item.get("ground_truth", ""),
                item.get("ai_answer", ""),
            ]).lower()
            if search not in haystack:
                continue
        filtered.append(item)
    return filtered


def _render_header(items: list) -> None:
    """渲染顶部统计信息。"""
    summary = get_evaluation_summary(items)
    total = len(items)
    evaluated = total - summary.get("未评测", 0)
    progress = (evaluated / total) if total else 0.0

    st.markdown(
        '<p class="section-title"><span class="section-title-icon">🧪</span>人工评测</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="color: var(--text-muted); font-size: 13px; margin: -8px 0 14px 0;">'
        "基于金融监管评测集，对 AI 回答进行人工标注，标注结果自动保存到本地。"
        "</p>",
        unsafe_allow_html=True,
    )

    cols = st.columns(5)
    metrics = [
        ("评测总数", total, "info"),
        ("已评测", evaluated, "success"),
        ("是", summary.get("是", 0), "success"),
        ("否", summary.get("否", 0), "danger"),
        ("未评测", summary.get("未评测", 0), "warning"),
    ]
    for col, (label, value, kind) in zip(cols, metrics):
        with col:
            st.metric(label, value)

    st.progress(progress, text=f"评测进度 {evaluated}/{total} ({progress*100:.1f}%)")


def _render_toolbar() -> None:
    """渲染筛选/操作工具栏。"""
    st.markdown('<p class="section-title">🔍 筛选与操作</p>', unsafe_allow_html=True)

    col_search, col_filter, col_size, col_btn = st.columns([3, 2, 1, 2])

    with col_search:
        st.text_input(
            "关键词搜索",
            placeholder="搜索题目 / 标准答案 / AI 回答",
            key="human_eval_search",
            label_visibility="collapsed",
        )

    with col_filter:
        filter_options = ["全部", "未评测", *EVAL_OPTIONS]
        st.selectbox(
            "评测状态",
            options=filter_options,
            key="human_eval_filter",
            label_visibility="collapsed",
        )

    with col_size:
        st.selectbox(
            "每页条数",
            options=[5, 10, 20, 50],
            key="human_eval_page_size",
            label_visibility="collapsed",
        )

    with col_btn:
        btn_cols = st.columns(2)
        with btn_cols[0]:
            if st.button("💾 保存", key="human_eval_save", use_container_width=True, type="primary"):
                _save_all()
        with btn_cols[1]:
            if st.button("🔄 重载", key="human_eval_reload", use_container_width=True):
                _load_data(force=True)
                st.session_state.human_eval_dirty = False
                st.rerun()


def _save_all() -> None:
    """将当前所有数据中的人工评测结果保存到本地 JSON。"""
    items = st.session_state.human_eval_data or []
    if not items:
        st.warning("当前没有可保存的评测数据。")
        return
    cached = {str(it["id"]): it.get("human_eval", "") for it in items if it.get("human_eval")}
    try:
        save_cached_results(cached)
        st.session_state.human_eval_dirty = False
        st.success(f"已保存 {len(cached)} 条人工评测结果到本地。")
    except Exception as e:
        st.error(f"保存失败: {e}")


def _clear_all() -> None:
    """清空所有人工评测结果。"""
    if not st.session_state.get("human_eval_confirm_clear", False):
        st.session_state.human_eval_confirm_clear = True
        st.info("再次点击「清空评测」以确认操作（清空后需重新保存）。")
        return
    items = st.session_state.human_eval_data or []
    for it in items:
        it["human_eval"] = ""
    try:
        clear_cached_results()
    except Exception:
        pass
    st.session_state.human_eval_dirty = True
    st.session_state.human_eval_confirm_clear = False
    st.success("已清空全部人工评测结果。")
    st.rerun()


def _render_pagination(total: int) -> tuple:
    """渲染分页控件，返回 (start, end)。"""
    page_size = st.session_state.human_eval_page_size
    total_pages = max(1, (total + page_size - 1) // page_size)
    if st.session_state.human_eval_page > total_pages:
        st.session_state.human_eval_page = total_pages

    pcol1, pcol2, pcol3 = st.columns([1, 3, 1])
    with pcol1:
        if st.button("◀ 上一页", key="human_eval_prev", use_container_width=True):
            if st.session_state.human_eval_page > 1:
                st.session_state.human_eval_page -= 1
                st.rerun()
    with pcol2:
        st.markdown(
            f"<p style='text-align:center; color: var(--text-muted); margin: 8px 0;'>"
            f"第 <strong style='color: var(--text-primary);'>{st.session_state.human_eval_page}</strong> / "
            f"{total_pages} 页 · 共 {total} 条</p>",
            unsafe_allow_html=True,
        )
    with pcol3:
        if st.button("下一页 ▶", key="human_eval_next", use_container_width=True):
            if st.session_state.human_eval_page < total_pages:
                st.session_state.human_eval_page += 1
                st.rerun()

    page = st.session_state.human_eval_page
    start = (page - 1) * page_size
    end = min(start + page_size, total)
    return start, end


def _render_eval_row(item: dict) -> None:
    """渲染一行评测项（可编辑的人工评测列）。"""
    idx = item["id"]
    question = item.get("question", "")
    ground_truth = item.get("ground_truth", "")
    ai_answer = item.get("ai_answer", "")
    current_eval = item.get("human_eval", "")

    # 卡片容器
    st.markdown(
        f"""
        <div style="
            background: var(--surface);
            backdrop-filter: blur(8px);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-md);
            padding: 18px 20px;
            margin: 10px 0;
            box-shadow: var(--shadow-sm);
        ">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span style="
                    display:inline-block;
                    background: var(--info-bg);
                    color: var(--primary-dark);
                    padding: 3px 10px;
                    border-radius: 999px;
                    font-size: 12px;
                    font-weight: 600;
                ">#{idx}</span>
                <span style="color: var(--text-muted); font-size:12px;">题目</span>
            </div>
            <p style="
                color: var(--text-primary);
                font-size: 15px;
                font-weight: 600;
                margin: 0 0 10px 0;
                line-height: 1.6;
            ">{_escape_html(question)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 标准答案 + AI 回答（可折叠）
    show_key = f"human_eval_show_{idx}"
    show_answers = st.session_state.human_eval_show_answer.get(show_key, False)
    toggle_label = "🙈 收起标准答案与 AI 回答" if show_answers else "👁 查看标准答案与 AI 回答"
    if st.button(toggle_label, key=f"toggle_{idx}", use_container_width=False):
        st.session_state.human_eval_show_answer[show_key] = not show_answers
        st.rerun()

    if show_answers:
        col_gt, col_ai = st.columns(2)
        with col_gt:
            st.markdown(
                '<p style="color: var(--text-muted); font-size:12px; margin: 8px 0 4px 0;">📘 标准答案</p>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="answer-box" style="font-size:13px; max-height:280px; overflow-y:auto;">'
                f'{_escape_html(ground_truth) or "<i style=\'color:#94a3b8\'>（无）</i>"}'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_ai:
            st.markdown(
                '<p style="color: var(--text-muted); font-size:12px; margin: 8px 0 4px 0;">🤖 AI 回答</p>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="answer-box" style="font-size:13px; max-height:280px; overflow-y:auto;">'
                f'{_escape_html(ai_answer) or "<i style=\'color:#94a3b8\'>（无）</i>"}'
                f'</div>',
                unsafe_allow_html=True,
            )

    # 人工评测列（核心：可编辑）
    eval_cols = st.columns([3, 1])
    with eval_cols[0]:
        st.markdown(
            '<p style="color: var(--text-muted); font-size:12px; margin: 10px 0 4px 0;">🧑‍⚖️ 人工评测</p>',
            unsafe_allow_html=True,
        )
        # selectbox 提供标准选项，避免拼写错误
        options = [""] + EVAL_OPTIONS
        try:
            current_index = options.index(current_eval) if current_eval in options else 0
        except ValueError:
            current_index = 0
        new_eval = st.selectbox(
            "人工评测",
            options=options,
            index=current_index,
            key=f"human_eval_select_{idx}",
            label_visibility="collapsed",
            help="请根据标准答案与 AI 回答判断其是否正确",
        )
        # 备注输入（可选）
        note = st.text_input(
            "备注（可选）",
            value=item.get("note", ""),
            key=f"human_eval_note_{idx}",
            placeholder="例如：核心要点正确但缺少某项依据",
            label_visibility="collapsed",
        )

    with eval_cols[1]:
        st.markdown(
            '<p style="color: var(--text-muted); font-size:12px; margin: 10px 0 4px 0;">&nbsp;</p>',
            unsafe_allow_html=True,
        )
        # 当选择变化时，自动同步到数据
        if new_eval != current_eval:
            item["human_eval"] = new_eval
            st.session_state.human_eval_dirty = True
        if note != item.get("note", ""):
            item["note"] = note
            st.session_state.human_eval_dirty = True

        # 状态徽章
        badge_html = _render_status_badge(new_eval)
        st.markdown(badge_html, unsafe_allow_html=True)


def _render_status_badge(value: str) -> str:
    """根据评测值返回徽章 HTML。"""
    if not value:
        return (
            '<span class="badge badge-warning" style="margin-top:6px; display:inline-block;">未评测</span>'
        )
    color_map = {
        "是": ("badge-success", "✓ 正确"),
        "否": ("badge-danger", "✗ 错误"),
        "部分正确": ("badge-info", "◐ 部分正确"),
        "无法判断": ("badge-warning", "? 无法判断"),
    }
    cls, label = color_map.get(value, ("badge-info", value))
    return f'<span class="badge {cls}" style="margin-top:6px; display:inline-block;">{label}</span>'


def _escape_html(text: str) -> str:
    """极简 HTML 转义，保证 markdown 渲染安全。"""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )


def _render_danger_zone() -> None:
    """渲染清空操作区。"""
    with st.expander("⚠️ 危险操作", expanded=False):
        st.warning("清空操作会删除所有本地保存的人工评测结果，且无法恢复。")
        if st.button("清空全部评测", key="human_eval_clear", type="secondary"):
            _clear_all()


def render_human_eval_page() -> None:
    """渲染人工评测页。"""
    _ensure_state()

    items = _load_data()
    if not items:
        st.info("请确认项目根目录下的 金融监管评测集.xlsx 文件存在且可读取。")
        return

    _render_header(items)
    st.markdown("---")
    _render_toolbar()

    filtered = _apply_filters(items)
    if not filtered:
        st.info("没有符合筛选条件的评测项。")
        return

    start, end = _render_pagination(len(filtered))
    page_items = filtered[start:end]

    st.markdown("---")
    for item in page_items:
        _render_eval_row(item)

    # 底部再渲染一次分页（方便翻页）
    st.markdown("---")
    _render_pagination(len(filtered))

    # 未保存提示与清空操作
    if st.session_state.human_eval_dirty:
        st.warning("⚠️ 当前有未保存的修改，请点击右上角「保存」按钮写入本地。")
    _render_danger_zone()
