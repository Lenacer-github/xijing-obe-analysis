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
        # 智能识别文件格式
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file)
        else:
            df_raw = pd.read_excel(uploaded_file)
        
        # 自动读取所有毕业要求列 (从第2列开始)
        course_names = df_raw.iloc[:, 1].values
        req_data = df_raw.iloc[:, 2:] 
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
        st.error(f"文件处理出错。请检查表头格式是否正确。详细错误: {e}")
        return None

# ================= 侧边栏 =================
with st.sidebar:
    st.header("📂 数据中心")
    uploaded_file = st.file_uploader("上传课程矩阵文件 (支持Excel/CSV)", type=['csv', 'xlsx', 'xls'])
    st.info("💡 提示：系统会自动识别所有毕业要求指标点列，支持9项、12项或更多。")

# ================= 主界面 =================
if uploaded_file is not None:
    results = generate_analysis(uploaded_file)
    
    if results:
        df_num, df_display_labels, course_names, req_names, course_contrib, req_imp = results
        
        # 字体大小自适应算法
        num_reqs = len(req_names)
        if num_reqs <= 12:
            dynamic_font_size = 11
        elif num_reqs <= 20:
            dynamic_font_size = 9
        else:
            dynamic_font_size = 7
            
        pdf_buffer = BytesIO()
        
        with PdfPages(pdf_buffer) as pdf:
            
            tab1, tab2, tab3, tab4 = st.tabs(["矩阵热力图", "支撑网络图", "课程贡献排名", "指标重要度"])
            
            # --- 图表1：矩阵热力图 ---
            with tab1:
                st.subheader(f"课程 - 毕业要求支撑矩阵 (共识别到 {num_reqs} 个指标点)")
                fig_height = max(10, len(course_names) * 0.6)
                fig1, ax1 = plt.subplots(figsize=(12, fig_height))
                cmap = ListedColormap(['#f5f5f5', '#FFD700', '#FF8C00', '#FF4500'])
                
                sns.heatmap(df_num, annot=df_display_labels.values, fmt='', cmap=cmap, cbar=False, 
                            linewidths=0.5, linecolor='gray', ax=ax1, vmin=0, vmax=3,
                            annot_kws={"size": dynamic_font_size, "color": "black", "weight": "bold"}) 
                
                ax1.set_ylabel('课程名称', fontsize=12)
                ax1.xaxis.tick_top()
                ax1.xaxis.set_label_position('top') 
                ax1.set_xticklabels(req_names, rotation=45, ha='left', fontsize=dynamic_font_size)
                
                st.pyplot(fig1) 
                pdf.savefig(fig1, bbox_inches='tight') 

            # --- 图表2：网络图 ---
            with tab2:
                st.subheader("支撑关系网络拓扑")
                fig2, ax2 = plt.subplots(figsize=(16 if num_reqs > 15 else 14, 12))
                G = nx.Graph()
                G.add_nodes_from(course_names, bipartite=0)
                G.add_nodes_from(req_names, bipartite=1)
                
                edges, colors, widths = [], [], []
                for c in course_names:
                    for r in req_names:
                        w = df_num.loc[c, r]
                        if w > 0:
                            G.add_edge(c, r); edges.append((c, r)); colors.append(COLOR_MAP[w]); widths.append(w * 0.8)
                
                pos = nx.bipartite_layout(G, course_names)
                req_node_sizes = [300 + G.degree(r) * 100 for r in req_names]
                
                nx.draw_networkx_nodes(G, pos, nodelist=course_names, node_color='#87CEEB', node_size=300, ax=ax2)
                nx.draw_networkx_nodes(G, pos, nodelist=req_names, node_color='#90EE90', node_size=req_node_sizes, ax=ax2)
                nx.draw_networkx_edges(G, pos, edge_color=colors, width=widths, alpha=0.6, ax=ax2)
                
                label_size = 10 if num_reqs <= 15 else 8
                nx.draw_networkx_labels(G, pos, font_family=NETWORK_FONT, font_size=label_size, ax=ax2, 
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
                ax3.set_title("课程贡献度排名\n(计算依据：H=3, M=2, L=1 累加)", fontsize=14, pad=15)
                ax3.set_xlabel("贡献度分值")
                st.pyplot(fig3)
                pdf.savefig(fig3, bbox_inches='tight')

            # --- 图表4：指标重要度 ---
            with tab4:
                st.subheader("毕业要求重要程度")
                fig4_height = max(6, num_reqs * 0.5) 
                fig4, ax4 = plt.subplots(figsize=(10, fig4_height))
                
                sorted_imp = req_imp.sort_values(ascending=True)
                sorted_imp.plot(kind='barh', color='#2E8B57', ax=ax4, edgecolor='black', alpha=0.8)
                for i, v in enumerate(sorted_imp):
                    ax4.text(v + 0.5, i, str(int(v)), va='center', fontweight='bold')
                ax4.set_title("毕业要求重要程度排名\n(计算依据：各指标点下 H=3, M=2, L=1 累加)", fontsize=14, pad=15)
                ax4.set_xlabel("重要程度分值")
                st.pyplot(fig4)
                pdf.savefig(fig4, bbox_inches='tight')

        # ================= 下载 =================
        st.success(f"✅ 分析完成！已自动适配 {num_reqs} 个毕业要求指标点。")
        st.download_button(
            label="⬇️ 下载最终版 PDF 报告",
            data=pdf_buffer.getvalue(),
            file_name="西京学院商学院_课程体系分析报告_自适应版.pdf",
            mime="application/pdf"
        )
else:
    st.info("👈 请上传文件 (Excel 或 CSV 均可)。")

# ================= 底部版权信息 (新增) =================
st.markdown("---") # 分割线
st.markdown(
    '''
    <div style="text-align: center; color: #888888; font-size: 14px; padding: 10px;">
        版权所有 © 西京学院商学院
    </div>
    ''',
    unsafe_allow_html=True
)
