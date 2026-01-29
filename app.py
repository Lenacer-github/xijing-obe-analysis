import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
from matplotlib.colors import ListedColormap
from matplotlib.backends.backend_pdf import PdfPages
from io import BytesIO
import matplotlib.font_manager as fm
import platform

# ================= 页面配置 =================
st.set_page_config(page_title="课程目标达成度分析系统", layout="wide")
st.title("🎓 基于OBE理念的课程支撑度分析系统")
st.markdown("### 西京学院商学院 | 教学管理工具")

# ================= 字体设置 (云端/本地双适配) =================
# 1. 优先设置 Matplotlib 全局字体
# 'WenQuanYi Micro Hei' 是 Streamlit Cloud 专用字体，必须放在首位
# 后面的字体是为您 Mac 本地准备的备选
font_list = ['WenQuanYi Micro Hei', 'Heiti TC', 'PingFang HK', 'Arial Unicode MS', 'SimHei']
plt.rcParams['font.sans-serif'] = font_list
plt.rcParams['axes.unicode_minus'] = False 

# 2. 定义一个变量，专门用于 NetworkX 图表的字体
# 因为 NetworkX 有时不受全局设置控制，需要单独指定
# 如果在 Linux (云端)，强制使用文泉驿；否则尝试使用 Mac 字体
system_name = platform.system()
if system_name == "Linux":
    NETWORK_FONT = 'WenQuanYi Micro Hei'
else:
    NETWORK_FONT = 'Heiti TC' # Mac 本地默认

# ================= 核心权重配置 =================
WEIGHT_MAP = {
    'H': 3, 'h': 3, '3': 3, 'High': 3,
    'M': 2, 'm': 2, '2': 2, 'Medium': 2,
    'L': 1, 'l': 1, '1': 1, 'Low': 1,
    '': 0, ' ': 0, 'nan': 0
}
COLOR_MAP = {3: '#FF4500', 2: '#FF8C00', 1: '#FFD700', 0: '#FFFFFF'}
REVERSE_LABEL_MAP = {3: 'H', 2: 'M', 1: 'L', 0: ''}

# ================= 分析逻辑 =================
def generate_analysis(uploaded_file):
    try:
        df_raw = pd.read_csv(uploaded_file)
        
        # 提取数据
        course_names = df_raw.iloc[:, 1].values
        req_data = df_raw.iloc[:, 2:11]
        req_names = req_data.columns.tolist()
        
        # 统一数值化
        df_num = req_data.copy()
        for col in df_num.columns:
            df_num[col] = df_num[col].astype(str).str.strip().map(lambda x: WEIGHT_MAP.get(x, 0)).fillna(0)
        df_num.index = course_names
        
        # 反向生成显示标签
        df_display_labels = df_num.applymap(lambda x: REVERSE_LABEL_MAP.get(x, ''))

        # 计算统计
        course_contribution = df_num.sum(axis=1)
        req_importance = df_num.sum(axis=0)
        
        return df_num, df_display_labels, course_names, req_names, course_contribution, req_importance
        
    except Exception as e:
        st.error(f"数据处理出错，请检查CSV是否包含特殊字符。详细错误: {e}")
        return None

# ================= 侧边栏 =================
with st.sidebar:
    st.header("📂 数据中心")
    uploaded_file = st.file_uploader("上传课程矩阵CSV", type=['csv'])

# ================= 主界面 =================
if uploaded_file is not None:
    results = generate_analysis(uploaded_file)
    
    if results:
        df_num, df_display_labels, course_names, req_names, course_contrib, req_imp = results
        
        pdf_buffer = BytesIO()
        
        with PdfPages(pdf_buffer) as pdf:
            
            tab1, tab2, tab3, tab4 = st.tabs(["矩阵热力图", "支撑网络图", "课程贡献排名", "指标重要度"])
            
            # --- 图表1：矩阵热力图 ---
            with tab1:
                st.subheader("课程 - 毕业要求支撑矩阵")
                fig_height = max(10, len(course_names) * 0.6)
                fig1, ax1 = plt.subplots(figsize=(12, fig_height))
                cmap = ListedColormap(['#f5f5f5', '#FFD700', '#FF8C00', '#FF4500'])
                sns.heatmap(df_num, annot=df_display_labels.values, fmt='', cmap=cmap, cbar=False, 
                            linewidths=0.5, linecolor='gray', ax=ax1, vmin=0, vmax=3,
                            annot_kws={"size": 11, "color": "black", "weight": "bold"}) 
                ax1.set_ylabel('课程名称', fontsize=12)
                ax1.set_xticklabels(req_names, rotation=45, ha='right')
                st.pyplot(fig1) 
                pdf.savefig(fig1, bbox_inches='tight') 

            # --- 图表2：网络图 (已修复乱码) ---
            with tab2:
                st.subheader("支撑关系网络拓扑")
                fig2, ax2 = plt.subplots(figsize=(14,
