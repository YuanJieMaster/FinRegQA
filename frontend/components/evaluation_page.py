"""
评估页面组件
Evaluation Page Component
"""

import streamlit as st
from config import REGION_OPTIONS, CATEGORY_OPTIONS, SUPPORTED_FILE_TYPES
from utils.api import (
    api_evaluate_qa_batch,
    api_evaluate_custom_question,
    api_evaluate_ingest,
    api_evaluate_custom_file,
    api_get_qa_pairs,
    api_get_ingest_cases,
    api_get_reports,
)


def render_evaluation_page():
    """渲染评估页面"""
    # st.markdown('<div class="section-card">', unsafe_allow_html=True)
    
    col_header1, col_header2 = st.columns([4, 1])
    with col_header1:
        st.markdown(
            '<p class="section-title"><span class="section-title-icon">📈</span>准确率评估</p>',
            unsafe_allow_html=True,
        )
    with col_header2:
        if st.button("刷新", use_container_width=True, key="eval_refresh"):
            st.rerun()
    
    # 评估说明
    st.markdown("""
    <div class="info-box">
        <h4 style="margin: 0 0 8px 0;">评估说明</h4>
        <p style="margin: 0; font-size: 14px;">
            本模块用于评估系统准确率，包括两大类：
            <br>1. <b>问答准确率</b>：评估问答系统的检索召回率和答案质量
            <br>2. <b>文档导入准确率</b>：评估文件上传后分块存储的准确性
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 评估类型选择
    eval_type = st.radio(
        "选择评估类型",
        ["💬 问答准确率评估", "📄 文档导入准确率评估"],
        horizontal=True,
        help="问答评估测试问答系统准确率，文档导入评估测试分块存储准确性"
    )
    
    # API 配置
    api_url = st.session_state.get("api_url", "http://localhost:8000")
    eval_api_url = st.text_input(
        "API 地址",
        value=api_url,
        help="评估测试将调用此地址的 API",
        key="eval_api_url"
    )
    
    st.markdown("---")
    
    if eval_type == "💬 问答准确率评估":
        _render_qa_evaluation(eval_api_url)
    else:
        _render_ingest_evaluation(eval_api_url)
    
    st.markdown('</div>', unsafe_allow_html=True)


def _render_qa_evaluation(api_url: str):
    """渲染问答评估"""
    col1, col2 = st.columns([3, 1])
    with col1:
        use_default = st.checkbox("使用默认问答对", value=True, help="使用系统预置的测试问答对")
    
    # 操作按钮
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        run_qa_eval_btn = st.button("▶️ 开始问答评估", type="primary", use_container_width=True)
    
    with col_btn2:
        view_reports_btn = st.button("📋 查看报告", use_container_width=True)
    
    with col_btn3:
        manage_qa_btn = st.button("✏️ 管理问答对", use_container_width=True)
    
    # 自定义问题测试
    with st.expander("🧪 自定义问题测试"):
        _render_custom_question_test(api_url)
    
    # 批量问题测试
    with st.expander("📦 批量问题测试"):
        _render_batch_question_test(api_url)
    
    # 问答对列表
    with st.expander("📝 查看默认问答对"):
        _render_qa_pairs_list(api_url)
    
    # 评估结果
    if run_qa_eval_btn:
        _render_qa_eval_results(api_url, use_default)
    
    # 历史报告
    if view_reports_btn:
        _render_reports(api_url)


def _render_custom_question_test(api_url: str):
    """渲染自定义问题测试"""
    st.markdown("""
    <div class="warning-box">
        <p style="margin: 0; font-size: 13px;">
            <b>使用说明：</b>在此输入您想要测试的问题，系统将评估检索和回答的质量。
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    custom_question = st.text_area(
        "输入测试问题",
        placeholder="例如：商业银行资本充足率最低要求是多少？",
        key="custom_eval_question"
    )
    
    col_q1, col_q2 = st.columns(2)
    with col_q1:
        custom_ground_truth = st.text_input(
            "参考答案（可选）",
            placeholder="用于计算准确率",
            key="custom_ground_truth"
        )
    with col_q2:
        custom_keywords = st.text_input(
            "预期关键词（可选，逗号分隔）",
            placeholder="资本充足率, 8%, 核心资本",
            key="custom_keywords"
        )
    
    col_q3, col_q4 = st.columns([1, 3])
    with col_q3:
        run_custom_question_btn = st.button("🔍 测试此问题", type="primary", use_container_width=True)
    
    if run_custom_question_btn and custom_question.strip():
        keywords_list = [k.strip() for k in custom_keywords.split(",") if k.strip()] if custom_keywords else None
        
        with st.spinner("正在测试..."):
            result = api_evaluate_custom_question(
                question=custom_question,
                api_url=api_url,
                ground_truth=custom_ground_truth if custom_ground_truth else None,
                keywords=keywords_list,
            )
            
            if result["success"]:
                _render_single_question_result(result["data"])
            else:
                st.error(f"测试失败: {result['error']}")


def _render_single_question_result(result: dict):
    """渲染单个问题测试结果"""
    st.markdown("""
    <div class="success-box">
        <h4 style="margin: 0 0 12px 0;">✅ 测试结果</h4>
    </div>
    """, unsafe_allow_html=True)
    
    # 答案展示
    st.markdown("**📝 系统回答：**")
    st.markdown(f'<div class="answer-box">{result.get("answer", "无回答")}</div>', unsafe_allow_html=True)
    
    # 指标展示
    if result.get("answer_metrics") or result.get("retrieval_metrics"):
        col_r1, col_r2 = st.columns(2)
        
        with col_r1:
            st.markdown("**📊 问答指标：**")
            answer_metrics = result.get("answer_metrics", {})
            if answer_metrics:
                st.write(f"- 语义相似度：{answer_metrics.get('semantic_similarity', 0):.4f}")
                st.write(f"- ROUGE-L：{answer_metrics.get('rouge_l', 0):.4f}")
                if answer_metrics.get('matched_keywords'):
                    st.write(f"- 匹配关键词：{', '.join(answer_metrics.get('matched_keywords', []))}")
                if answer_metrics.get('keyword_coverage') is not None:
                    st.write(f"- 关键词覆盖率：{answer_metrics.get('keyword_coverage', 0):.1%}")
        
        with col_r2:
            st.markdown("**🔍 检索指标：**")
            retrieval_metrics = result.get("retrieval_metrics", {})
            if retrieval_metrics:
                st.write(f"- 平均相似度：{retrieval_metrics.get('avg_similarity', 0):.4f}")
                st.write(f"- 最高相似度：{retrieval_metrics.get('top_similarity', 0):.4f}")
                st.write(f"- 参考文献数：{retrieval_metrics.get('reference_count', 0)}")
    
    # 参考文献
    if result.get("references"):
        st.markdown("**📚 参考文献：**")
        for i, ref in enumerate(result.get("references", [])[:3], 1):
            with st.expander(f"依据 {i}: {ref.get('document_name', '未知')}"):
                st.write(f"**条款**: {ref.get('article_number', '-')}")
                st.write(f"**相似度**: {ref.get('similarity', 0):.4f}")
                content = ref.get('content', '')
                st.write(f"**内容**: {content[:150]}..." if len(content) > 150 else f"**内容**: {content}")
    
    st.write(f"⏱️ 响应时间: {result.get('response_time', 0):.2f}秒")


def _render_batch_question_test(api_url: str):
    """渲染批量问题测试"""
    st.markdown("""
    <div style="background: #f3e8ff; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
        <p style="margin: 0; color: #6b21a8; font-size: 13px;">
            <b>批量测试：</b>一次提交多个问题进行测试，每个问题占据一行。
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    batch_questions_input = st.text_area(
        "输入多个问题（每行一个）",
        placeholder="商业银行资本充足率最低要求是什么？\n保险公司偿付能力充足率要求是多少？\n客户身份识别的基本要求是什么？",
        height=150,
        key="batch_questions_input"
    )
    
    col_b1, col_b2 = st.columns([1, 3])
    with col_b1:
        run_batch_btn = st.button("🚀 批量测试", type="primary", use_container_width=True)
    
    if run_batch_btn and batch_questions_input.strip():
        questions = [q.strip() for q in batch_questions_input.split("\n") if q.strip()]
        if questions:
            _render_batch_results(questions, api_url)
        else:
            st.warning("请输入至少一个问题")


def _render_batch_results(questions: list, api_url: str):
    """渲染批量测试结果"""
    progress_bar = st.progress(0)
    progress_text = st.empty()
    
    all_results = []
    for i, q in enumerate(questions):
        progress_text.text(f"正在测试问题 {i+1}/{len(questions)}...")
        progress_bar.progress((i + 1) / len(questions))
        
        result = api_evaluate_custom_question(question=q, api_url=api_url)
        if result["success"]:
            all_results.append({**result["data"], "question": q, "success": True})
        else:
            all_results.append({"question": q, "success": False, "error": "请求失败"})
    
    progress_bar.empty()
    progress_text.empty()
    
    # 汇总结果
    st.markdown("### 📊 批量测试结果汇总")
    
    success_count = sum(1 for r in all_results if r.get("success"))
    avg_time = sum(r.get("response_time", 0) for r in all_results if r.get("success")) / max(success_count, 1)
    
    col_bs1, col_bs2, col_bs3 = st.columns(3)
    with col_bs1:
        st.metric("总问题数", len(questions))
    with col_bs2:
        st.metric("成功", success_count)
    with col_bs3:
        st.metric("平均响应时间", f"{avg_time:.2f}秒")
    
    # 结果表格
    st.markdown("#### 详细结果")
    result_data = []
    for r in all_results:
        answer_metrics = r.get("answer_metrics", {})
        retrieval_metrics = r.get("retrieval_metrics", {})
        
        result_data.append({
            "问题": r.get("question", "")[:50] + "..." if len(r.get("question", "")) > 50 else r.get("question", ""),
            "状态": "✅" if r.get("success") else "❌",
            "语义相似度": f"{answer_metrics.get('semantic_similarity', 0):.4f}" if answer_metrics else "-",
            "平均相似度": f"{retrieval_metrics.get('avg_similarity', 0):.4f}" if retrieval_metrics else "-",
            "响应时间": f"{r.get('response_time', 0):.2f}s"
        })
    
    st.dataframe(result_data, use_container_width=True)


def _render_qa_pairs_list(api_url: str):
    """渲染问答对列表"""
    try:
        result = api_get_qa_pairs(api_url)
        if result["success"]:
            qa_pairs = result["data"]
            st.write(f"共 {len(qa_pairs)} 个问答对")
            
            for i, qa in enumerate(qa_pairs):
                with st.expander(f"Q{i+1}: {qa['question'][:50]}..."):
                    st.write(f"**问题**: {qa['question']}")
                    st.write(f"**参考答案**: {qa['ground_truth_answer']}")
                    st.write(f"**关键词**: {', '.join(qa['keywords'])}")
                    st.write(f"**难度**: {qa['difficulty']}")
        else:
            st.warning("无法加载问答对列表")
    except Exception as e:
        st.error(f"加载问答对失败: {e}")


def _render_qa_eval_results(api_url: str, use_default: bool):
    """渲染问答评估结果"""
    st.markdown("#### 问答评估结果")
    
    with st.spinner("正在运行问答评估测试，请稍候..."):
        result = api_evaluate_qa_batch(api_url, use_default)
        
        if result["success"]:
            report = result["data"]
            
            # 总体评分
            overall_score = report.get("overall_score", 0)
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 24px; border-radius: 12px; text-align: center; margin: 20px 0;">
                <h2 style="color: white; margin: 0;">问答综合评分</h2>
                <h1 style="color: white; font-size: 48px; margin: 16px 0;">{overall_score:.1%}</h1>
                <p style="color: rgba(255,255,255,0.8); margin: 0;">
                    基于检索 F1、关键词覆盖率、语义相似度的综合评分
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # 指标卡片
            col_m1, col_m2, col_m3 = st.columns(3)
            
            with col_m1:
                st.markdown("##### 检索指标")
                retrieval = report.get("retrieval_metrics", {})
                st.metric("召回率", "{:.1%}".format(retrieval.get("recall", 0)))
                st.metric("准确率", "{:.1%}".format(retrieval.get("precision", 0)))
                st.metric("F1 分数", "{:.1%}".format(retrieval.get("f1_score", 0)))
            
            with col_m2:
                st.markdown("##### 问答指标")
                answer = report.get("answer_metrics", {})
                st.metric("关键词覆盖率", "{:.1%}".format(answer.get("keyword_coverage", 0)))
                st.metric("语义相似度", "{:.4f}".format(answer.get("semantic_similarity", 0)))
                st.metric("ROUGE-L", "{:.4f}".format(answer.get("rouge_l", 0)))
            
            with col_m3:
                st.markdown("##### 测试统计")
                st.metric("总测试数", report.get("total_questions", 0))
                st.metric("成功", report.get("successful_tests", 0))
                st.metric("失败", report.get("failed_tests", 0))
            
            # 可视化图表
            st.markdown("#### 📈 评估指标可视化")
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                st.markdown("**检索指标对比**")
                retrieval_data = {
                    "指标": ["召回率", "准确率", "F1分数", "命中率"],
                    "数值": [
                        retrieval.get("recall", 0),
                        retrieval.get("precision", 0),
                        retrieval.get("f1_score", 0),
                        retrieval.get("hit_rate", 0)
                    ]
                }
                st.bar_chart(retrieval_data.set_index("指标"))
            
            with chart_col2:
                st.markdown("**问答指标对比**")
                answer_data = {
                    "指标": ["关键词覆盖", "语义相似度", "ROUGE-L", "长度比率"],
                    "数值": [
                        answer.get("keyword_coverage", 0),
                        answer.get("semantic_similarity", 0),
                        answer.get("rouge_l", 0),
                        answer.get("length_ratio", 0)
                    ]
                }
                st.bar_chart(answer_data.set_index("指标"))
            
            # 详细结果表格
            st.markdown("---")
            st.markdown("##### 详细测试结果")
            
            result_data = []
            for r in report.get("results", []):
                result_data.append({
                    "问题": r["question"][:30] + "..." if len(r["question"]) > 30 else r["question"],
                    "关键词覆盖率": "{:.0%}".format(r["answer_metrics"]["keyword_coverage"]),
                    "语义相似度": "{:.2f}".format(r["answer_metrics"]["semantic_similarity"]),
                    "响应时间": "{:.2f}s".format(r["response_time"]),
                    "状态": "✓" if not r.get("error") else "✗"
                })
            
            st.dataframe(result_data, use_container_width=True)
            st.success("问答评估完成！")
        
        else:
            st.error(f"评估失败: {result['error']}")


def _render_reports(api_url: str):
    """渲染历史报告"""
    st.markdown("#### 历史评估报告")
    
    try:
        result = api_get_reports(api_url)
        if result["success"]:
            reports = result["data"]
            if reports:
                for rep in reports[:5]:
                    col_r1, col_r2, col_r3 = st.columns([3, 2, 1])
                    with col_r1:
                        st.write(f"📄 {rep['filename']}")
                    with col_r2:
                        st.write(f"创建时间: {rep['created'][:19]}")
                    with col_r3:
                        if st.button("查看", key=f"view_{rep['filename']}"):
                            st.info(f"加载报告: {rep['filename']}")
            else:
                st.info("暂无历史报告")
        else:
            st.warning("无法加载报告列表")
    except Exception as e:
        st.error(f"加载报告失败: {e}")


def _render_ingest_evaluation(api_url: str):
    """渲染文档导入评估"""
    # 说明
    st.markdown("""
    <div class="info-box">
        <h4 style="margin: 0 0 8px 0;">📄 文档导入评估说明</h4>
        <p style="margin: 0; font-size: 14px;">
            文档导入评估用于测试系统将上传的文件进行分块、存储的准确性。
        </p>
        <ul style="margin: 8px 0 0 0; font-size: 14px;">
            <li><b>分块数量准确率</b>：实际分块数与预期分块数的一致性</li>
            <li><b>分块大小准确率</b>：分块大小是否符合要求</li>
            <li><b>内容完整性</b>：原始文档内容是否完整保留</li>
            <li><b>关键词保留率</b>：关键信息是否在分块后保留</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # 测试用例
    with st.expander("📋 查看测试文档"):
        _render_ingest_cases(api_url)
    
    # 自定义文件测试
    with st.expander("📤 自定义文件上传测试"):
        _render_custom_file_test(api_url)
    
    # 操作按钮
    col_btn_ingest1, col_btn_ingest2 = st.columns(2)
    
    with col_btn_ingest1:
        run_ingest_eval_btn = st.button("▶️ 开始文档导入评估", type="primary", use_container_width=True)
    
    with col_btn_ingest2:
        show_ingest_guide_btn = st.button("📖 评估指标说明", use_container_width=True)
    
    if show_ingest_guide_btn:
        _render_ingest_guide()
    
    if run_ingest_eval_btn:
        _render_ingest_eval_results(api_url)


def _render_ingest_cases(api_url: str):
    """渲染导入测试用例"""
    try:
        result = api_get_ingest_cases(api_url)
        if result["success"]:
            cases = result["data"]
            st.write(f"共有 {len(cases)} 个测试文档")
            
            for case in cases:
                with st.expander(f"📄 {case['file_name']}"):
                    st.write(f"**预期分块数**: {case['expected_chunks']}")
                    st.write(f"**预期分类**: {', '.join(case['expected_categories'])}")
                    st.write(f"**预期关键词**: {', '.join(case['expected_keywords'])}")
                    st.write(f"**分块大小范围**: {case['min_chunk_size']} - {case['max_chunk_size']} 字符")
        else:
            st.warning("无法加载测试用例")
    except Exception as e:
        st.error(f"加载测试用例失败: {e}")


def _render_custom_file_test(api_url: str):
    """渲染自定义文件测试"""
    st.markdown("""
    <div style="background: #e0f2fe; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
        <p style="margin: 0; color: #075985; font-size: 13px;">
            <b>功能说明：</b>上传您自己的文件进行导入准确率测试。
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        custom_file = st.file_uploader(
            "选择文件",
            type=SUPPORTED_FILE_TYPES,
            key="custom_eval_file"
        )
    with col_f2:
        custom_file_category = st.selectbox(
            "文档分类",
            options=CATEGORY_OPTIONS,
            key="custom_eval_category"
        )
    
    col_f3, col_f4 = st.columns(2)
    with col_f3:
        custom_file_region = st.selectbox(
            "适用地区",
            options=REGION_OPTIONS,
            key="custom_eval_region"
        )
    with col_f4:
        custom_file_regulation = st.text_input(
            "监管类型",
            placeholder="例如：商业银行监管",
            key="custom_eval_regulation"
        )
    
    col_f5, col_f6 = st.columns([1, 3])
    with col_f5:
        run_custom_file_btn = st.button("📤 上传并测试", type="primary", use_container_width=True)
    
    if run_custom_file_btn and custom_file:
        _render_custom_file_result(custom_file, custom_file_category, custom_file_region, custom_file_regulation, api_url)
    elif run_custom_file_btn:
        st.error("请选择文件")


def _render_custom_file_result(file, category: str, region: str, regulation: str, api_url: str):
    """渲染自定义文件测试结果"""
    progress_container = st.empty()
    progress_bar = progress_container.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("📤 准备上传文件...")
        progress_bar.progress(0.1)
        
        status_text.text("🔍 分析文档结构...")
        progress_bar.progress(0.3)
        
        result = api_evaluate_custom_file(
            file=file,
            api_url=api_url,
            category=category,
            regulation_type=regulation,
            region=region if region != "全国" else None,
        )
        
        progress_bar.progress(0.9)
        status_text.text("✅ 完成评估...")
        
        if result["success"]:
            progress_bar.progress(1.0)
            result_data = result["data"]
            
            if result_data.get("success"):
                st.markdown("""
                <div class="success-box">
                    <h4 style="margin: 0 0 12px 0;">✅ 测试完成</h4>
                </div>
                """, unsafe_allow_html=True)
                
                # 基本信息
                col_info1, col_info2, col_info3 = st.columns(3)
                with col_info1:
                    st.metric("文件名", result_data.get("file_name", ""))
                with col_info2:
                    st.metric("文档ID", result_data.get("document_id", "-"))
                with col_info3:
                    st.metric("分块数", result_data.get("chunk_count", 0))
                
                # 准确率评分
                accuracy = result_data.get("accuracy_score", {})
                if accuracy:
                    score = accuracy.get("score", 0)
                    if score >= 0.8:
                        color = "#22c55e"
                        level = "优秀"
                    elif score >= 0.6:
                        color = "#3b82f6"
                        level = "良好"
                    elif score >= 0.4:
                        color = "#f59e0b"
                        level = "一般"
                    else:
                        color = "#ef4444"
                        level = "较差"
                    
                    st.markdown(f"""
                    <div style="background: {color}; padding: 20px; border-radius: 12px; text-align: center; margin: 16px 0;">
                        <h3 style="color: white; margin: 0;">准确率评分</h3>
                        <h2 style="color: white; font-size: 36px; margin: 8px 0;">{score:.1%}</h2>
                        <p style="color: white; margin: 0;">{level}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.write(f"**实际分块数**: {accuracy.get('actual_chunks', 0)}")
                    st.write(f"**预期范围**: {accuracy.get('expected_range', 'N/A')}")
                    st.write(f"**评估**: {accuracy.get('assessment', '')}")
                
                st.write(f"⏱️ 处理时间: {result_data.get('processing_time', 0):.2f}秒")
            else:
                st.error(f"测试失败: {result_data.get('error', '未知错误')}")
        else:
            st.error(f"API调用失败: {result['error']}")
    
    except Exception as e:
        st.error(f"测试出错: {str(e)}")
    finally:
        progress_container.empty()
        status_text.empty()


def _render_ingest_guide():
    """渲染评估指标说明"""
    st.markdown("""
    #### 📊 文档导入评估指标详解
    
    | 指标 | 说明 | 计算方式 |
    |------|------|----------|
    | **分块数量准确率** | 实际分块数与预期的匹配程度 | 1 - |实际分块数 - 预期分块数| / 预期分块数 |
    | **分块大小准确率** | 分块大小是否符合配置要求 | 符合大小要求的分块数 / 总分块数 |
    | **内容完整性** | 原始文档内容是否完整保留 | 保留的内容长度 / 原始内容长度 |
    | **关键词保留率** | 关键信息在分块后是否保留 | 保留的关键词数 / 总关键词数 |
    | **字段准确率** | 分类、地区、法规类型是否正确 | 正确的字段数 / 总字段数 |
    
    #### 评分标准
    
    - **90%-100%**：优秀 - 系统表现良好
    - **70%-90%**：良好 - 系统表现正常
    - **50%-70%**：一般 - 需要关注
    - **50%以下**：较差 - 需要优化
    """)


def _render_ingest_eval_results(api_url: str):
    """渲染文档导入评估结果"""
    st.markdown("#### 文档导入评估结果")
    
    with st.spinner("正在运行文档导入评估，请稍候（这可能需要几分钟）..."):
        result = api_evaluate_ingest(api_url)
        
        if result["success"]:
            report = result["data"]
            
            # 总体评分
            score = report.get("overall_score", 0)
            if score >= 0.9:
                score_color = "#22c55e"
                score_text = "优秀"
            elif score >= 0.7:
                score_color = "#3b82f6"
                score_text = "良好"
            elif score >= 0.5:
                score_color = "#f59e0b"
                score_text = "一般"
            else:
                score_color = "#ef4444"
                score_text = "较差"
            
            st.markdown(f"""
            <div style="background: {score_color}; padding: 24px; border-radius: 12px; text-align: center; margin: 20px 0;">
                <h2 style="color: white; margin: 0;">文档导入综合评分</h2>
                <h1 style="color: white; font-size: 48px; margin: 16px 0;">{score:.1%}</h1>
                <p style="color: white; margin: 0; font-size: 18px;">评级: {score_text}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 指标卡片
            col_m1, col_m2 = st.columns(2)
            
            with col_m1:
                st.markdown("##### 分块质量指标")
                st.metric("分块数量准确率", "{:.1%}".format(report.get("avg_chunk_count_accuracy", 0)))
                st.metric("分块大小准确率", "{:.1%}".format(report.get("avg_chunk_size_accuracy", 0)))
            
            with col_m2:
                st.markdown("##### 内容质量指标")
                st.metric("内容完整性", "{:.1%}".format(report.get("avg_content_completeness", 0)))
                st.metric("关键词保留率", "{:.1%}".format(report.get("avg_keyword_retention", 0)))
            
            # 测试统计
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.metric("测试文档数", report.get("total_files", 0))
            with col_s2:
                st.metric("成功", report.get("successful_files", 0))
            with col_s3:
                st.metric("失败", report.get("failed_files", 0))
            
            # 可视化图表
            st.markdown("#### 📈 文档导入评估可视化")
            chart_d1, chart_d2 = st.columns(2)
            
            with chart_d1:
                st.markdown("**质量指标对比**")
                quality_data = {
                    "指标": ["分块数量", "分块大小", "内容完整", "关键词保留"],
                    "数值": [
                        report.get("avg_chunk_count_accuracy", 0),
                        report.get("avg_chunk_size_accuracy", 0),
                        report.get("avg_content_completeness", 0),
                        report.get("avg_keyword_retention", 0)
                    ]
                }
                st.bar_chart(quality_data.set_index("指标"))
            
            # 详细结果表格
            st.markdown("---")
            st.markdown("##### 各文档评估详情")
            
            result_data = []
            for r in report.get("results", []):
                status = "✓" if not r.get("error") else "✗"
                result_data.append({
                    "文件名": r.get("file_name", ""),
                    "文件类型": r.get("file_type", ""),
                    "预期分块": r.get("expected_chunks", 0),
                    "实际分块": r.get("actual_chunks", 0),
                    "数量准确率": "{:.0%}".format(r.get("chunk_count_accuracy", 0)),
                    "内容完整": "{:.0%}".format(r.get("content_completeness", 0)),
                    "关键词保留": "{:.0%}".format(r.get("keyword_retention", 0)),
                    "状态": status
                })
            
            st.dataframe(result_data, use_container_width=True)
            st.success("文档导入评估完成！")
        
        else:
            st.error(f"评估失败: {result['error']}")
