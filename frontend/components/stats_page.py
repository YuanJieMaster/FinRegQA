"""
统计页面组件
Statistics Page Component
"""

import streamlit as st
from utils.api import api_get_stats


def render_stats_page():
    """渲染统计页面"""
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    
    col_header1, col_header2 = st.columns([4, 1])
    with col_header1:
        st.markdown(
            '<p class="section-title"><span class="section-title-icon">📊</span>知识库统计</p>',
            unsafe_allow_html=True,
        )
    with col_header2:
        if st.button("刷新", use_container_width=True, key="stats_refresh"):
            st.rerun()
    
    with st.spinner("加载中..."):
        api_url = st.session_state.get("api_url", "http://localhost:8000")
        result = api_get_stats(api_url)
        
        if result["success"]:
            stats = result["data"]
            
            # 核心指标卡片
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("文档数", stats["document_count"])
            
            with col2:
                st.metric("知识点数", stats["knowledge_count"])
            
            with col3:
                vector_count = stats.get("milvus_vector_count", stats.get("knowledge_count", 0))
                st.metric("向量数", vector_count)
            
            with col4:
                if stats["knowledge_count"] > 0:
                    avg_per_doc = stats["knowledge_count"] / max(stats["document_count"], 1)
                    st.metric("平均/文档", f"{avg_per_doc:.1f}")
                else:
                    st.metric("平均/文档", "0")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 分类分布
            if stats.get("category_distribution"):
                st.markdown('<div class="section-card">', unsafe_allow_html=True)
                st.markdown('<p class="section-title">📂 分类分布</p>', unsafe_allow_html=True)
                
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    st.bar_chart(stats["category_distribution"])
                with col_chart2:
                    for cat, count in stats["category_distribution"].items():
                        st.write(f"- **{cat}**: {count} 条")
                st.markdown('</div>', unsafe_allow_html=True)
            
            # 监管类型分布
            if stats.get("regulation_distribution"):
                st.markdown('<div class="section-card">', unsafe_allow_html=True)
                st.markdown('<p class="section-title">📋 监管类型分布</p>', unsafe_allow_html=True)
                
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    st.bar_chart(stats["regulation_distribution"])
                with col_chart2:
                    for reg_type, count in stats["regulation_distribution"].items():
                        st.write(f"- **{reg_type}**: {count} 条")
                st.markdown('</div>', unsafe_allow_html=True)
            
            # 地区分布
            if stats.get("region_distribution"):
                st.markdown('<div class="section-card">', unsafe_allow_html=True)
                st.markdown('<p class="section-title">🌍 地区分布</p>', unsafe_allow_html=True)
                
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    st.bar_chart(stats["region_distribution"])
                with col_chart2:
                    for region_name, count in stats["region_distribution"].items():
                        st.write(f"- **{region_name}**: {count} 条")
                st.markdown('</div>', unsafe_allow_html=True)
        
        else:
            st.error(f"获取统计信息失败: {result['error']}")
