"""
文档上传页面组件
Document Upload Page Component
"""

import streamlit as st
from config import REGION_OPTIONS, CATEGORY_OPTIONS, SUPPORTED_FILE_TYPES
from utils.api import api_ingest_document


def render_upload_page():
    """渲染文档上传页面"""
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    
    st.markdown('<p class="section-title">📤 上传文档</p>', unsafe_allow_html=True)
    
    # 文件上传
    col1, col2 = st.columns(2)
    
    with col1:
        uploaded_file = st.file_uploader(
            "选择文件",
            type=SUPPORTED_FILE_TYPES,
            help="支持 PDF、Word、TXT、图片格式（图片将使用 OCR 识别）"
        )
        
        category = st.selectbox(
            "文档分类",
            options=CATEGORY_OPTIONS,
            key="ingest_category_select",
        )
    
    with col2:
        region_option = st.selectbox(
            "适用地区",
            options=REGION_OPTIONS,
            index=0,
            key="ingest_region_select",
        )
        region_custom = ""
        if region_option == "其他（自定义）":
            region_custom = st.text_input(
                "自定义地区",
                placeholder="例如：杭州市",
                key="ingest_region_custom_input",
            )
        region = region_custom.strip() if region_option == "其他（自定义）" else region_option
        
        regulation_type = st.text_input(
            "监管类型",
            placeholder="例如：商业银行监管",
            key="ingest_regulation_type",
        )
        
        source = st.text_input(
            "文档来源",
            placeholder="例如：中国银保监会",
            key="ingest_source",
        )
    
    # 高级选项
    with st.expander("⚙️ 高级选项"):
        col_adv1, col_adv2, col_adv3 = st.columns([2, 1, 1])
        
        with col_adv1:
            min_chunk_size = st.number_input(
                "最小分块大小",
                value=1,
                min_value=1,
                key="min_chunk_size",
            )
        
        with col_adv2:
            keep_separator = st.checkbox("保留分隔符", value=True, key="keep_separator")
        
        with col_adv3:
            batch_size = st.number_input(
                "批处理大小",
                value=100,
                min_value=10,
                key="batch_size",
            )
    
    # 上传按钮
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    
    if st.button("上传并导入", type="primary", use_container_width=True):
        if not uploaded_file:
            st.error("请选择文件")
        elif not regulation_type.strip():
            st.error("请输入监管类型")
        else:
            with st.spinner("正在处理文件..."):
                api_url = st.session_state.get("api_url", "http://localhost:8000")
                result = api_ingest_document(
                    file=uploaded_file,
                    category=category,
                    regulation_type=regulation_type,
                    region=region if region != "全国" else None,
                    source=source if source else None,
                    min_chunk_size=min_chunk_size,
                    keep_separator=keep_separator,
                    batch_size=batch_size,
                    api_url=api_url,
                )
                
                if result["success"]:
                    data = result["data"]
                    st.markdown(f'<div class="success-box">文档导入成功！</div>', unsafe_allow_html=True)
                    
                    # 显示导入结果
                    col_res1, col_res2, col_res3, col_res4 = st.columns(4)
                    with col_res1:
                        st.metric("文档 ID", data["document_id"])
                    with col_res2:
                        st.metric("分块数", data["chunk_count"])
                    with col_res3:
                        st.metric("成功", data["success"])
                    with col_res4:
                        st.metric("失败", data["failed"])
                else:
                    st.error(f"导入失败: {result['error']}")
    
    # 使用说明
    with st.expander("📖 上传说明"):
        st.markdown("""
        **支持的文件格式：**
        - 文档类：PDF、DOCX、DOC、TXT
        - 图片类：PNG、JPG、JPEG、BMP、TIFF、GIF、WEBP（图片将使用 OCR 识别）
        
        **分块说明：**
        - 系统会自动将文档内容分成小块存储
        - 可以通过"最小分块大小"调整每个块的大小
        - 较大的分块可以保留更多上下文信息
        """)
    
    st.markdown('</div>', unsafe_allow_html=True)
