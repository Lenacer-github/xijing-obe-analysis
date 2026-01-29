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

# ================= 字体设置 =================
font_list = ['WenQuanYi Micro Hei', 'Heiti TC', 'PingFang HK', 'Arial Unicode MS', 'SimHei']
plt.rcParams['font.sans-serif'] = font_list
plt.rcParams['axes.unicode_minus'] = False 

system_name = platform.system()
if system_name == "Linux":
    NETWORK_FONT = 'WenQuanYi Micro Hei'
else:
    NETWORK_FONT = 'Heiti TC' 

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
        # 【升级点1】智能识别文件格式
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file)
        else:
            # 读取 Excel (兼容 .xlsx 和 .xls)
            df_raw = pd.read_excel(uploaded_file)
        
        # 提取数据
        course_names = df_raw.iloc[:, 1].values
        req_data = df_raw.iloc[:, 2:11]
        req_names = req_data.columns.tolist()
        
        # 统一数值化
        df_num = req_data.copy()
        for col in df_num.columns:
            df_num[col] = df_num[col].astype(str).str.strip().map(lambda x: WEIGHT_MAP.get(x, 0)).fillna(0)
        df_num.index = course_names
        
        # 反向生成标签
        df_display_labels = df_num.applymap(lambda x: REVERSE_LABEL_MAP.get(x, ''))

        # 计算统计
        course_contribution = df_num.sum(axis=1)
        req_importance = df_num.sum(axis=0)
        
        return df_num, df_display_labels, course_names, req_names, course_contribution, req_importance
        
    except Exception as e:
        st.error(f"文件读取失败。请确保文件未加密且格式正确。详细错误: {e}")
        return None

# ================= 侧边栏 =================
with st.sidebar:
    st.header("📂 数据中心")
    # 【升级点2】允许上传 csv, xlsx, xls 三种格式
    uploaded_file = st.file_uploader("上传课程矩阵文件 (支持Excel/CSV)", type=['csv', 'xlsx', 'xls'])

# ================= 主界面 =================
if uploaded_file is not None:
    results = generate_analysis(uploaded_file)
    
    if results:
        df_num, df_display_labels, course_names, req_names, course_contrib, req_imp = results
        
        pdf_buffer = BytesIO()
        
        with PdfPages(pdf_buffer
