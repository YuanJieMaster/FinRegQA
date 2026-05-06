"""
知识库管理页面组件
Knowledge Base Management Page Component
"""

import streamlit as st
from config import REGION_OPTIONS, PAGE_SIZE_OPTIONS
from utils.api import (
    api_list_knowledge,
    api_list_documents,
    api_update_knowledge,
    api_delete_knowledge,
    api_delete_document,
)


def render_knowledge_management_page():
    """渲染知识库管理页面"""
    # 子标签页
    sub_tab1, sub_tab2 = st.tabs(["📝 知识点管理", "📄 文档管理"])
    
    # ---------------------------------------------------------
    # 知识点管理
    # ---------------------------------------------------------
    with sub_tab1:
        _render_knowledge_list()
    
    # ---------------------------------------------------------
    # 文档管理
    # ---------------------------------------------------------
    with sub_tab2:
        _render_document_list()


def _render_knowledge_list():
    """渲染知识点列表"""
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    
    # 筛选区域
    st.markdown('<p class="section-title">🔍 筛选条件</p>', unsafe_allow_html=True)
    
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        filter_category = st.selectbox(
            "分类",
            options=["全部"] + ["风险管理", "资本管理", "流动性管理", "内部控制", "信息披露", "其他"],
            key="kb_filter_category"
        )
        filter_category_value = None if filter_category == "全部" else filter_category
    
    with col_filter2:
        filter_region = st.selectbox(
            "地区",
            options=["全部"] + REGION_OPTIONS,
            key="kb_filter_region"
        )
        filter_region_value = None if filter_region == "全部" else filter_region
    
    with col_filter3:
        filter_search = st.text_input(
            "关键词搜索",
            placeholder="搜索内容...",
            key="kb_filter_search"
        )
    
    # 分页设置
    col_page1, col_page2 = st.columns([4, 1])
    with col_page1:
        page_number = st.number_input(
            "页码",
            min_value=1,
            value=st.session_state.get("kb_page", 1),
            step=1,
            key="kb_page_input"
        )
        st.session_state.kb_page = page_number
    with col_page2:
        page_size = st.selectbox(
            "每页条数",
            options=PAGE_SIZE_OPTIONS,
            index=1,
            key="kb_page_size"
        )
    
    if st.button("搜索", key="kb_search_btn", use_container_width=True):
        st.session_state.kb_page = 1
        st.rerun()
    
    st.markdown("---")
    
    # 加载知识点列表
    with st.spinner("加载知识点列表..."):
        api_url = st.session_state.get("api_url", "http://localhost:8000")
        result = api_list_knowledge(
            page=st.session_state.get("kb_page", 1),
            page_size=page_size,
            category=filter_category_value,
            region=filter_region_value,
            search=filter_search if filter_search else None,
            api_url=api_url,
        )
        
        if result["success"]:
            data = result["data"]
            knowledge_items = data.get("items", [])
            total = data.get("total", 0)
            total_pages = data.get("total_pages", 1)
            
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin: 16px 0;">
                <span style="color: #64748b;">共找到 <strong style="color: #0f172a;">{total}</strong> 条知识点</span>
                <span style="color: #64748b;">第 {st.session_state.get('kb_page', 1)} / {total_pages} 页</span>
            </div>
            """, unsafe_allow_html=True)
            
            if knowledge_items:
                _render_knowledge_items(knowledge_items)
            else:
                st.info("未找到符合条件的知识点")
        else:
            st.error(f"获取知识点列表失败: {result['error']}")
    
    st.markdown('</div>', unsafe_allow_html=True)


def _render_knowledge_items(items: list):
    """渲染知识点列表项"""
    for item in items:
        item_id = item.get("id", 0)
        
        with st.expander(
            f"**知识点 #{item_id}** | {item.get('category', '未分类')} | {item.get('region', '全国')}",
            expanded=False
        ):
            # 知识点详情
            col_view1, col_view2, col_view3 = st.columns([6, 2, 2])
            
            with col_view1:
                content = item.get('content', '')
                if len(content) > 200:
                    st.markdown(f"**内容预览**: {content[:200]}...")
                    with st.expander("查看完整内容"):
                        st.text(content)
                else:
                    st.markdown(f"**内容**: {content}")
            
            with col_view2:
                st.write(f"**条款**: {item.get('article_number', '-')} {item.get('section_number', '')}")
                st.write(f"**监管类型**: {item.get('regulation_type', '-')}")
                st.write(f"**文档**: {item.get('document_name', '-')}")
            
            with col_view3:
                st.write(f"**创建时间**: {item.get('created_at', '-')[:10] if item.get('created_at') else '-'}")
                st.write(f"**更新时间**: {item.get('updated_at', '-')[:10] if item.get('updated_at') else '-'}")
            
            # 操作按钮
            st.markdown("---")
            col_btn_edit, col_btn_del = st.columns(2)
            
            with col_btn_edit:
                if st.button("编辑", key=f"edit_{item_id}", use_container_width=True):
                    st.session_state[f"edit_mode_{item_id}"] = True
            
            with col_btn_del:
                if st.button("删除", key=f"delete_{item_id}", use_container_width=True):
                    st.session_state[f"confirm_delete_{item_id}"] = True
            
            # 删除确认
            if st.session_state.get(f"confirm_delete_{item_id}", False):
                st.warning(f"确定要删除知识点 #{item_id} 吗？此操作不可恢复！")
                col_confirm_yes, col_confirm_no = st.columns(2)
                
                with col_confirm_yes:
                    if st.button("确认删除", key=f"confirm_yes_{item_id}", type="primary", use_container_width=True):
                        api_url = st.session_state.get("api_url", "http://localhost:8000")
                        result = api_delete_knowledge(item_id, api_url)
                        if result["success"]:
                            st.success("删除成功！")
                            st.session_state[f"confirm_delete_{item_id}"] = False
                            st.rerun()
                        else:
                            st.error(f"删除失败: {result['error']}")
                
                with col_confirm_no:
                    if st.button("取消", key=f"confirm_no_{item_id}", use_container_width=True):
                        st.session_state[f"confirm_delete_{item_id}"] = False
                        st.rerun()
            
            # 编辑表单
            if st.session_state.get(f"edit_mode_{item_id}", False):
                _render_edit_form(item)


def _render_edit_form(item: dict):
    """渲染编辑表单"""
    item_id = item.get("id", 0)
    
    st.markdown("---")
    st.markdown("**编辑知识点**")
    
    edit_category = st.text_input(
        "分类",
        value=item.get('category') or "",
        key=f"edit_category_{item_id}"
    )
    edit_region = st.text_input(
        "地区",
        value=item.get('region') or "",
        key=f"edit_region_{item_id}"
    )
    edit_regulation_type = st.text_input(
        "监管类型",
        value=item.get('regulation_type') or "",
        key=f"edit_regulation_type_{item_id}"
    )
    edit_article = st.text_input(
        "条款编号",
        value=item.get('article_number') or "",
        key=f"edit_article_{item_id}"
    )
    edit_section = st.text_input(
        "章节编号",
        value=item.get('section_number') or "",
        key=f"edit_section_{item_id}"
    )
    edit_content = st.text_area(
        "内容",
        value=item.get('content') or "",
        height=150,
        key=f"edit_content_{item_id}"
    )
    
    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("保存修改", key=f"save_{item_id}", type="primary", use_container_width=True):
            api_url = st.session_state.get("api_url", "http://localhost:8000")
            update_data = {
                "category": edit_category,
                "region": edit_region,
                "regulation_type": edit_regulation_type,
                "article_number": edit_article,
                "section_number": edit_section,
                "content": edit_content,
            }
            result = api_update_knowledge(item_id, update_data, api_url)
            if result["success"]:
                st.success("更新成功！")
                st.session_state[f"edit_mode_{item_id}"] = False
                st.rerun()
            else:
                st.error(f"更新失败: {result['error']}")
    
    with col_cancel:
        if st.button("取消编辑", key=f"cancel_{item_id}", use_container_width=True):
            st.session_state[f"edit_mode_{item_id}"] = False
            st.rerun()


def _render_document_list():
    """渲染文档列表"""
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <p class="section-title" style="margin: 0;">📄 文档列表</p>
        <p style="color: #64748b; margin: 0; font-size: 14px;">点击文档名称查看详情或删除</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("刷新列表", key="refresh_docs_btn", use_container_width=True):
        st.rerun()
    
    with st.spinner("加载文档列表..."):
        api_url = st.session_state.get("api_url", "http://localhost:8000")
        result = api_list_documents(api_url)
        
        if result["success"]:
            documents = result["data"]
            
            if documents:
                for doc in documents:
                    _render_document_item(doc)
            else:
                st.info("暂无文档")
        else:
            st.error(f"获取文档列表失败: {result['error']}")
    
    st.markdown('</div>', unsafe_allow_html=True)


def _render_document_item(doc: dict):
    """渲染文档项"""
    doc_id = doc.get("id", 0)
    doc_name = doc.get("name", "未知文档")
    doc_source = doc.get("source") or "-"
    doc_type = doc.get("file_type") or "-"
    doc_count = doc.get("knowledge_count", 0)
    doc_created = doc.get("created_at", "-")
    doc_updated = doc.get("updated_at", "-")
    
    with st.expander(
        f"**文档 #{doc_id}**: {doc_name} | 知识点: {doc_count} | 来源: {doc_source}",
        expanded=False
    ):
        col_doc1, col_doc2 = st.columns([3, 1])
        
        with col_doc1:
            st.markdown(f"""
            - **文档名称**: {doc_name}
            - **来源**: {doc_source}
            - **文件类型**: {doc_type}
            - **知识点数量**: {doc_count}
            - **创建时间**: {doc_created[:10] if doc_created and len(doc_created) > 10 else doc_created}
            - **更新时间**: {doc_updated[:10] if doc_updated and len(doc_updated) > 10 else doc_updated}
            """)
        
        with col_doc2:
            st.write("")
            st.write("")
            if st.button("删除文档", key=f"del_doc_{doc_id}", use_container_width=True):
                st.session_state[f"confirm_del_doc_{doc_id}"] = True
        
        # 删除确认
        if st.session_state.get(f"confirm_del_doc_{doc_id}", False):
            st.warning(f"⚠️ 确定要删除文档 **\"{doc_name}\"** 吗？此操作将同时删除所有关联的知识点（共 {doc_count} 条）！")
            col_confirm_yes, col_confirm_no = st.columns(2)
            
            with col_confirm_yes:
                if st.button("确认删除", key=f"doc_confirm_yes_{doc_id}", type="primary", use_container_width=True):
                    api_url = st.session_state.get("api_url", "http://localhost:8000")
                    result = api_delete_document(doc_id, api_url)
                    if result["success"]:
                        st.success("文档删除成功！")
                        st.session_state[f"confirm_del_doc_{doc_id}"] = False
                        st.rerun()
                    else:
                        st.error(f"删除失败: {result['error']}")
            
            with col_confirm_no:
                if st.button("取消", key=f"doc_confirm_no_{doc_id}", use_container_width=True):
                    st.session_state[f"confirm_del_doc_{doc_id}"] = False
                    st.rerun()
