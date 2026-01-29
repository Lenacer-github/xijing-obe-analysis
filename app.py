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
st.title("🎓 基于OBE理念的专业课程体系与毕业要求关联度矩阵分析系统")
st.markdown("### 西京学院 | 人才培养方案修订辅助管理工具")

# ================= 1. 字体设置 =================
font_list = ['WenQuanYi Micro Hei', 'Heiti TC', 'PingFang HK', 'Arial Unicode MS', 'SimHei']
plt.rcParams['font.sans-serif'] = font_list
plt.rcParams['axes.unicode_minus'] = False 

system_name = platform.system()
if system_name == "Linux":
    NETWORK_FONT = 'WenQuanYi Micro Hei'
else:
    NETWORK_FONT = 'Heiti TC' 

# ================= 2. 核心权重与通识课配置 =================
WEIGHT_MAP = {
    'H': 3, 'h': 3, '3': 3, 'High': 3,
    'M': 2, 'm': 2, '2': 2, 'Medium': 2,
    'L': 1, 'l': 1, '1': 1, 'Low': 1,
    '': 0, ' ': 0, 'nan': 0
}
COLOR_MAP = {3: '#FF4500', 2: '#FF8C00', 1: '#FFD700', 0: '#FFFFFF'}
REVERSE_LABEL_MAP = {3: 'H', 2: 'M', 1: 'L', 0: ''}

# 【新增】通识课程名单 (精确匹配)
GEN_ED_COURSES = [
    '思想道德与法治', '中国近现代史纲要', '马克思主义基本原理', '毛泽东思想和中国特色社会主义理论体系概论', 
    '习近平新时代中国特色社会主义思想概论', '形势与政策', '国家安全教育', '大学生心理健康教育', 
    '体育1-4', '劳动教育', '生涯教育与就业创业指导', '大学英语A1-4', '高等数学B1-2', '线性代数B', 
    '概率论与数理统计B', '大学计算机基础', '人工智能', '军事理论', '军事技能', '人文素养与社会科学', 
    '艺术修养与审美体验', '科技进步与生态文明', '创新思维与创业教育'
]

# ================= 3. 分析逻辑 =================
def generate_analysis(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file)
        else:
            df_raw = pd.read_excel(uploaded_file)
        
        course_names = df_raw.iloc[:, 1].values
        req_data = df_raw.iloc[:, 2:] 
        req_names = req_data.columns.tolist()
        
        df_num = req_data.copy()
        for col in df_num.columns:
            df_num[col] = df_num[col].astype(str).str.strip().map(lambda x: WEIGHT_MAP.get(x, 0)).fillna(0)
        df_num.index = course_names
        
        df_display_labels = df_num.applymap(lambda x: REVERSE_LABEL_MAP.get(x, ''))
        course_contribution = df_num.sum(axis=1)
        req_importance = df_num.sum(axis=0)
        
        return df_num, df_display_labels, course_names, req_names, course_contribution, req_importance
    except Exception as e:
        st.error(f"文件处理出错: {e}")
        return None

# ================= 4. 侧边栏 =================
with st.sidebar:
    st.header("📂 数据中心")
    uploaded_file = st.file_uploader("上传课程矩阵文件 (支持Excel/CSV)", type=['csv', 'xlsx', 'xls'])
    download_btn_placeholder = st.empty()
    st.markdown("---")
    st.info("💡 **提示**：\n1. 系统自动识别 *号为专业核心课（显示黄色）\n2. 自动识别通识课（显示灰色）\n3. 其他课程显示蓝色")

# ================= 5. 主界面 =================
if uploaded_file is not None:
    results = generate_analysis(uploaded_file)
    
    if results:
        df_num, df_display_labels, course_names, req_names, course_contrib, req_imp = results
        
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
                st.subheader(f"课程 - 毕业要求支撑矩阵")
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
                
                nx.draw_networkx_labels(G, pos, labels={n:n for n in course_names}, 
                                      font_family=NETWORK_FONT, font_size=8, ax=ax2,
                                      bbox=dict(facecolor='white', edgecolor='none', alpha=0.6, pad=0))
                nx.draw_networkx_labels(G, pos, labels={n:n for n in req_names}, 
                                      font_family=NETWORK_FONT, font_size=10, ax=ax2,
                                      bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=0))
                ax2.axis('off')
                st.pyplot(fig2)
                pdf.savefig(fig2, bbox_inches='tight')

            # --- 图表3：课程贡献 (【核心修改】：颜色区分逻辑) ---
            with tab3:
                st.subheader("课程贡献度排名")
                fig3, ax3 = plt.subplots(figsize=(10, max(8, len(course_names) * 0.5)))
                sorted_contrib = course_contrib.sort_values(ascending=True)
                
                # --- 颜色计算逻辑 ---
                bar_colors = []
                text_colors = []
                
                for name in sorted_contrib.index:
                    clean_name = str(name).strip()
                    # 1. 优先判断是否为通识课
                    if clean_name in GEN_ED_COURSES:
                        bar_colors.append('#D3D3D3') # 浅灰条
                        text_colors.append('#808080') # 深灰字
                    # 2. 判断是否包含 * 号 (专业核心课)
                    elif '*' in clean_name:
                        bar_colors.append('#FFD700') # 亮金条
                        text_colors.append('#B8860B') # 暗金字 (为了看清)
                    # 3. 其他默认
                    else:
                        bar_colors.append('#4682B4') # 默认蓝
                        text_colors.append('black')  # 默认黑

                # 绘图
                bars = ax3.barh(sorted_contrib.index, sorted_contrib.values, color=bar_colors, edgecolor='none', alpha=0.9)
                
                # 设置Y轴文字颜色
                for label, color in zip(ax3.get_yticklabels(), text_colors):
                    label.set_color(color)
                    # 如果是黄色或灰色，加粗一点以便阅读
                    if color != 'black':
                        label.set_fontweight('bold')

                # 数值标签
                for i, v in enumerate(sorted_contrib):
                    ax3.text(v + 0.2, i, str(int(v)), va='center', fontweight='bold', color='black')
                
                ax3.set_title("课程贡献度排名\n(🟨核心课程  ⬜通识课程  🟦其他课程)", fontsize=14, pad=15)
                ax3.set_xlabel("贡献度分值 (H=3, M=2, L=1)")
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

        download_btn_placeholder.download_button(
            label="📥 点击下载最终版报告 (PDF)",
            data=pdf_buffer.getvalue(),
            file_name="西京学院商学院_课程体系分析报告.pdf",
            mime="application/pdf",
            type="primary"
        )
        st.sidebar.success("✅ 分析报告已生成！")

else:
    st.info("👈 请在左侧上传文件。")

# ================= 底部版权 =================
st.markdown("---")
st.markdown(
    '''
    <div style="text-align: center; color: #888888; font-size: 14px; padding: 10px;">
        版权所有 © 西京学院商学院 2026年
    </div>
    ''',
    unsafe_allow_html=True
)
