"""
问答页面组件
Question Answering Page Component
"""

import streamlit as st
from config import REGION_OPTIONS, SEARCH_MODE_OPTIONS
from utils.api import api_get_answer_stream

EXAMPLE_QUESTIONS = [
    "商业银行资本充足率最低要求是什么？",
    "保险公司偿付能力监管有哪些核心指标？",
    "绿色信贷分类标准如何界定？",
]


def render_qa_page():
    """渲染问答页面"""
    # st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-title"><span class="section-title-icon">💬</span>智能问答</p>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<p style="color: var(--text-muted); font-size: 13px; margin: -8px 0 12px 0;">'
        "试试以下示例问题，或输入您的监管合规疑问"
        "</p>",
        unsafe_allow_html=True,
    )

    ex_cols = st.columns(len(EXAMPLE_QUESTIONS))
    for i, (col, example) in enumerate(zip(ex_cols, EXAMPLE_QUESTIONS)):
        with col:
            if st.button(example, key=f"qa_example_{i}", use_container_width=True):
                st.session_state.question_input = example
                st.rerun()

    question = st.text_area(
        "输入问题",
        placeholder="例如：商业银行资本充足率最低要求是什么？",
        height=100,
        key="question_input",
    )

    filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 1])

    with filter_col1:
        question_region_option = st.selectbox(
            "地区筛选",
            options=REGION_OPTIONS,
            index=0,
            help="优先检索所选地区法规",
            key="question_region_select",
        )
        question_region_custom = ""
        if question_region_option == "其他（自定义）":
            question_region_custom = st.text_input(
                "自定义地区",
                placeholder="例如：宁波市",
                key="question_region_custom_input",
            )

    with filter_col2:
        search_mode_labels = [opt["label"] for opt in SEARCH_MODE_OPTIONS]
        search_mode_values = [opt["value"] for opt in SEARCH_MODE_OPTIONS]
        search_mode = st.selectbox(
            "搜索模式",
            options=range(len(search_mode_labels)),
            format_func=lambda x: search_mode_labels[x],
            index=0,
            help="Hybrid 结合向量和关键词搜索",
            key="question_search_mode_select",
        )
        selected_mode = search_mode_values[search_mode]

    question_region = (
        question_region_custom.strip()
        if question_region_option == "其他（自定义）"
        else question_region_option
    )
    if question_region == "全国":
        question_region = None

    with filter_col3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        submit_btn = st.button("提交问答", use_container_width=True, type="primary", key="qa_submit")

    # st.markdown("</div>", unsafe_allow_html=True)

    if submit_btn and question.strip():
        api_url = st.session_state.get("api_url", "http://localhost:8000")
        status_placeholder = st.empty()
        status_placeholder.info("正在检索相关知识...")

        answer_placeholder = st.empty()
        full_answer = ""
        meta = None

        for event in api_get_answer_stream(question, question_region, selected_mode, api_url):
            if event["event"] == "meta":
                meta = event["data"]
                status_placeholder.success("检索完成，正在生成回答...")

            elif event["event"] == "answer":
                full_answer += event["data"]
                answer_placeholder.markdown(
                    f'<p class="section-title"><span class="section-title-icon">📝</span>回答</p>'
                    f'<div class="answer-box">{full_answer}<span class="streaming-cursor">▌</span></div>',
                    unsafe_allow_html=True,
                )

            elif event["event"] == "done":
                status_placeholder.empty()
                answer_placeholder.markdown(
                    f'<p class="section-title"><span class="section-title-icon">📝</span>回答</p>'
                    f'<div class="answer-box">{full_answer}</div>',
                    unsafe_allow_html=True,
                )

                if meta and meta.get("references"):
                    st.markdown(
                        '<p class="section-title"><span class="section-title-icon">📚</span>参考依据</p>',
                        unsafe_allow_html=True,
                    )
                    for i, ref in enumerate(meta["references"], 1):
                        with st.expander(f"依据 {i}: {ref.get('document_name', '未知文档')}"):
                            col_ref1, col_ref2 = st.columns([4, 1])
                            with col_ref1:
                                st.markdown(
                                    f"**条款**: {ref.get('article_number', '-')} {ref.get('section_number', '')}"
                                )
                                st.markdown(
                                    f"**分类**: {ref.get('category', '-')} | **地区**: {ref.get('region', '-')}"
                                )
                                content = ref.get("content", "")
                                if len(content) > 200:
                                    st.markdown(f"**内容**: {content[:200]}...")
                                    with st.expander("查看完整内容"):
                                        st.text(content)
                                else:
                                    st.markdown(f"**内容**: {content}")
                            with col_ref2:
                                sim = ref.get("similarity")
                                if isinstance(sim, (int, float)):
                                    st.metric("相似度", f"{sim:.3f}")
                elif meta and not meta.get("references"):
                    st.info("未找到相关法规依据")

            elif event["event"] == "error":
                status_placeholder.empty()
                st.error(f"流式请求失败: {event['data']}")
                break

    elif submit_btn:
        st.warning("请输入问题")
