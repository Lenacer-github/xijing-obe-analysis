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

# ================= 页面配置 =================
st.set_page_config(page_title="课程目标达成度分析系统", layout="wide")
st.title("🎓 基于OBE理念的课程支撑度分析系统")
st.markdown("### 西京学院商学院 | 教学管理工具")

# ================= 字体设置 (防乱码) =================
# 优先匹配 macOS 的中文字体
font_list = ['Heiti TC', 'PingFang HK', 'Arial Unicode MS', 'SimHei', 'Microsoft YaHei']
plt.rcParams['font.sans-serif'] = font_list
plt.rcParams['axes.unicode_minus'] = False 

# ================= 核心权重配置 =================
# 输入映射：支持 CSV 里填写 H/M/L 或者 3/2/1 或者 h/m/l
WEIGHT_MAP = {
    'H': 3, 'h': 3, '3': 3, 'High': 3,
    'M': 2, 'm': 2, '2': 2, 'Medium': 2,
    'L': 1, 'l': 1, '1': 1, 'Low': 1,
    '': 0, ' ': 0, 'nan': 0
}

# 颜色映射 (3:红, 2:橙, 1:黄, 0:白)
COLOR_MAP = {3: '#FF4500', 2: '#FF8C00', 1: '#FFD700', 0: '#FFFFFF'}

# 【新增】反向标签映射：根据计算结果强制生成标签
# 确保图表上显示的永远是标准的 H/M/L，而不是 CSV 里的原始数据
REVERSE_LABEL_MAP = {3: 'H', 2: 'M', 1: 'L', 0: ''}

# ================= 分析逻辑 =================
def generate_analysis(uploaded_file):
    try:
        df_raw = pd.read_csv(uploaded_file)
        
        # 提取数据
        course_names = df_raw.iloc[:, 1].values
        req_data = df_raw.iloc[:, 2:11]
        req_names = req_data.columns.tolist()
        
        # --- 步骤1：统一数值化 (计算颜色的依据) ---
        df_num = req_data.copy()
        for col in df_num.columns:
            # 转换为字符串 -> 去除空格 -> 映射权重 -> 填补无法识别的值为0
            df_num[col] = df_num[col].astype(str).str.strip().map(lambda x: WEIGHT_MAP.get(x, 0)).fillna(0)
        
        df_num.index = course_names
        
        # --- 步骤2：反向生成显示标签 (解决 'nan' 和 空白问题) ---
        # 只要 df_num 是 3，标签就是 'H'，彻底解决数文不对应
        df_display_labels = df_num.applymap(lambda x: REVERSE_LABEL_MAP.get(x, ''))

        # --- 步骤3：计算统计 ---
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
                
                # 关键点：annot 使用我们反向生成的 df_display_labels
                sns.heatmap(df_num, annot=df_display_labels.values, fmt='', cmap=cmap, cbar=False, 
                            linewidths=0.5, linecolor='gray', ax=ax1, vmin=0, vmax=3,
                            annot_kws={"size": 11, "color": "black", "weight": "bold"}) 
                
                ax1.set_ylabel('课程名称', fontsize=12)
                ax1.set_xticklabels(req_names, rotation=45, ha='right')
                st.pyplot(fig1) 
                pdf.savefig(fig1, bbox_inches='tight') 

            # --- 图表2：网络图 ---
            with tab2:
                st.subheader("支撑关系网络拓扑")
                fig2, ax2 = plt.subplots(figsize=(14, 12))
                G = nx.Graph()
                G.add_nodes_from(course_names, bipartite=0)
                G.add_nodes_from(req_names, bipartite=1)
                
                edges, colors, widths = [], [], []
                for c in course_names:
                    for r in req_names:
                        w = df_num.loc[c, r]
                        if w > 0:
                            G.add_edge(c, r)
                            edges.append((c, r))
                            colors.append(COLOR_MAP[w])
                            widths.append(w * 2) # 线条加粗
                
                pos = nx.bipartite_layout(G, course_names)
                
                # 绘图
                nx.draw_networkx_nodes(G, pos, nodelist=course_names, node_color='#87CEEB', node_size=300, ax=ax2) # 课程蓝点
                nx.draw_networkx_nodes(G, pos, nodelist=req_names, node_color='#90EE90', node_size=600, ax=ax2)  # 指标绿点
                nx.draw_networkx_edges(G, pos, edge_color=colors, width=widths, alpha=0.7, ax=ax2)
                
                # 标签 (增加字体背景，防止看不清)
                nx.draw_networkx_labels(G, pos, font_family='Heiti TC', font_size=10, ax=ax2, 
                                      bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=0))
                
                ax2.axis('off')
                st.pyplot(fig2)
                pdf.savefig(fig2, bbox_inches='tight')

            # --- 图表3：课程贡献 ---
            with tab3:
                st.subheader("课程贡献度排名")
                fig3, ax3 = plt.subplots(figsize=(10, max(8, len(course_names) * 0.5)))
                sorted_contrib = course_contrib.sort_values(ascending=True)
                sorted_contrib.plot(kind='barh', color='#4682B4', ax=ax3, edgecolor='black', alpha=0.8)
                
                for i, v in enumerate(sorted_contrib):
                    ax3.text(v + 0.2, i, str(int(v)), va='center', fontweight='bold')
                
                ax3.set_xlabel("贡献度分值")
                st.pyplot(fig3)
                pdf.savefig(fig3, bbox_inches='tight')

            # --- 图表4：指标重要度 ---
            with tab4:
                st.subheader("毕业要求指标重要度")
                fig4, ax4 = plt.subplots(figsize=(10, 6))
                sorted_imp = req_imp.sort_values(ascending=True)
                sorted_imp.plot(kind='barh', color='#2E8B57', ax=ax4, edgecolor='black', alpha=0.8)
                
                for i, v in enumerate(sorted_imp):
                    ax4.text(v + 0.5, i, str(int(v)), va='center', fontweight='bold')
                    
                st.pyplot(fig4)
                pdf.savefig(fig4, bbox_inches='tight')

        # ================= 下载 =================
        st.success("✅ 报表生成完毕 | 逻辑校验通过")
        st.download_button(
            label="⬇️ 下载最终版 PDF 报告",
            data=pdf_buffer.getvalue(),
            file_name="西京学院商学院_课程体系分析报告_v2.pdf",
            mime="application/pdf"
        )
else:
    st.info("👈 请上传 CSV 文件。系统将自动清洗数据并生成标准报表。")