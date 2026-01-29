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
import math

# ================= 页面配置 =================
st.set_page_config(page_title="课程目标达成度分析系统", layout="wide")
st.title("🎓 基于OBE理念的课程支撑度分析系统")
st.markdown("### 西京学院商学院 | 教学管理工具")

# ================= 1. 字体设置 =================
font_list = ['WenQuanYi Micro Hei', 'Heiti TC', 'PingFang HK', 'Arial Unicode MS', 'SimHei']
plt.rcParams['font.sans-serif'] = font_list
plt.rcParams['axes.unicode_minus'] = False 

system_name = platform.system()
if system_name == "Linux":
    NETWORK_FONT = 'WenQuanYi Micro Hei'
else:
    NETWORK_FONT = 'Heiti TC' 

# ================= 2. 核心配置 =================
# 常规权重 (用于热力图、网络图、课程贡献度)
WEIGHT_MAP = {
    'H': 3, 'h': 3, '3': 3, 'High': 3,
    'M': 2, 'm': 2, '2': 2, 'Medium': 2,
    'L': 1, 'l': 1, '1': 1, 'Low': 1,
    '': 0, ' ': 0, 'nan': 0
}

# 特殊权重 (仅用于毕业要求重要度计算：只认H)
WEIGHT_MAP_SPECIAL = {
    'H': 10, 'h': 10, '3': 10, 'High': 10,
    'M': 0, 'm': 0, '2': 0, 'Medium': 0,
    'L': 0, 'l': 0, '1': 0, 'Low': 0,
    '': 0, ' ': 0, 'nan': 0
}

COLOR_MAP = {3: '#FF4500', 2: '#FF8C00', 1: '#FFD700', 0: '#FFFFFF'}
REVERSE_LABEL_MAP = {3: 'H', 2: 'M', 1: 'L', 0: ''}

# 通识课程名单
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
        
        # --- 常规数值化 ---
        df_num = req_data.copy()
        for col in df_num.columns:
            df_num[col] = df_num[col].astype(str).str.strip().map(lambda x: WEIGHT_MAP.get(x, 0)).fillna(0)
        df_num.index = course_names
        
        # --- 特殊数值化 (H=10, M=0, L=0) ---
        df_num_special = req_data.copy()
        for col in df_num_special.columns:
            df_num_special[col] = df_num_special[col].astype(str).str.strip().map(lambda x: WEIGHT_MAP_SPECIAL.get(x, 0)).fillna(0)
        df_num_special.index = course_names

        df_display_labels = df_num.applymap(lambda x: REVERSE_LABEL_MAP.get(x, ''))
        
        course_contribution = df_num.sum(axis=1)
        req_importance_special = df_num_special.sum(axis=0)
        
        return df_num, df_display_labels, course_names, req_names, course_contribution, req_importance_special
    except Exception as e:
        st.error(f"文件处理出错: {e}")
        return None

# ================= 4. 侧边栏 =================
with st.sidebar:
    st.header("📂 数据中心")
    uploaded_file = st.file_uploader("上传课程矩阵文件 (支持Excel/CSV)", type=['csv', 'xlsx', 'xls'])
    download_btn_placeholder = st.empty()
    st.markdown("---")
    st.info("💡 **审核原则**：\n1. 所有指标点需 ≥2门H支撑\n2. 核心课程(*)需位于贡献度前1/3\n3. 核心课程不能位于倒数10名")

# ================= 5. 主界面 =================
if uploaded_file is not None:
    results = generate_analysis(uploaded_file)
    
    if results:
        df_num, df_display_labels, course_names, req_names, course_contrib, req_imp_special = results
        
        num_reqs = len(req_names)
        
        # 超高密度自适应
        if num_reqs <= 12:
            font_size = 11; label_rotation = 45; heatmap_width = 12
        elif num_reqs <= 25:
            font_size = 9; label_rotation = 45; heatmap_width = 14
        else:
            font_size = 6; label_rotation = 90; heatmap_width = 18
            
        pdf_buffer = BytesIO()
        
        with PdfPages(pdf_buffer) as pdf:
            
            tab1, tab2, tab3, tab4 = st.tabs(["矩阵热力图", "支撑网络图", "课程贡献排名", "指标重要度"])
            
            # --- 图表1：矩阵热力图 ---
            with tab1:
                st.subheader(f"课程 - 毕业要求支撑矩阵 (指标点数: {num_reqs})")
                fig1, ax1 = plt.subplots(figsize=(heatmap_width, max(10, len(course_names) * 0.6)))
                cmap = ListedColormap(['#f5f5f5', '#FFD700', '#FF8C00', '#FF4500'])
                sns.heatmap(df_num, annot=df_display_labels.values, fmt='', cmap=cmap, cbar=False, 
                            linewidths=0.5, linecolor='gray', ax=ax1, vmin=0, vmax=3,
                            annot_kws={"size": font_size, "color": "black", "weight": "bold"}) 
                ax1.set_ylabel('课程名称', fontsize=12)
                ax1.xaxis.tick_top()
                ax1.xaxis.set_label_position('top') 
                ax1.set_xticklabels(req_names, rotation=label_rotation, ha='left', fontsize=font_size)
                st.pyplot(fig1) 
                pdf.savefig(fig1, bbox_inches='tight') 

            # --- 图表2：网络图 ---
            with tab2:
                st.subheader("支撑关系网络拓扑")
                net_height = max(12, num_reqs * 0.6)
                fig2, ax2 = plt.subplots(figsize=(16, net_height))
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
                
                line_alpha = 0.4 if num_reqs > 30 else 0.6
                nx.draw_networkx_edges(G, pos, edge_color=colors, width=widths, alpha=line_alpha, ax=ax2)
                
                nx.draw_networkx_labels(G, pos, labels={n:n for n in course_names}, 
                                      font_family=NETWORK_FONT, font_size=8, ax=ax2,
                                      bbox=dict(facecolor='white', edgecolor='none', alpha=0.6, pad=0))
                right_font = 8 if num_reqs > 30 else 10
                nx.draw_networkx_labels(G, pos, labels={n:n for n in req_names}, 
                                      font_family=NETWORK_FONT, font_size=right_font, ax=ax2,
                                      bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=0))
                ax2.axis('off')
                st.pyplot(fig2)
                pdf.savefig(fig2, bbox_inches='tight')

            # --- 图表3：课程贡献 (含自动审查) ---
            with tab3:
                st.subheader("课程贡献度排名")
                
                # === 课程贡献度审查逻辑 ===
                # 1. 准备数据：按贡献度降序排列 (High to Low)
                df_sorted_desc = course_contrib.sort_values(ascending=False)
                total_courses = len(df_sorted_desc)
                
                # 识别核心课程
                core_courses = [c for c in df_sorted_desc.index if '*' in str(c)]
                
                # 规则1：零支撑检查
                zero_contrib_courses = df_sorted_desc[df_sorted_desc == 0].index.tolist()
                if zero_contrib_courses:
                    for zc in zero_contrib_courses:
                        st.error(f"❌ {zc} 课程支撑度为0，请核查！")
                else:
                    st.success("✅ 课程质量检查：所有课程均有支撑（无0支撑课程）。")
                
                # 规则3：核心课程存在性检查
                if not core_courses:
                    st.error("⛔ 未检测到专业核心课程，请检查专业核心课程的标识「*」是否准确标注。")
                else:
                    # 规则2：核心课程必须在前1/3
                    top_third_threshold = math.ceil(total_courses / 3)
                    top_third_courses = df_sorted_desc.index[:top_third_threshold].tolist()
                    
                    for core in core_courses:
                        if core not in top_third_courses:
                            st.warning(f"⚠️ 【《{core}》专业核心课程排名没有位于课程贡献度排名的前三分之一，需要注意】")
                    
                    # 规则4：边缘课程检查 (最后10门)
                    if total_courses > 10:
                        bottom_10_courses = df_sorted_desc.index[-10:].tolist()
                        for core in core_courses:
                            if core in bottom_10_courses:
                                st.error(f"🚫 【《{core}》专业核心课程位于边缘课程(倒数10名)，需要注意】")

                st.markdown("---")

                # === 绘图 ===
                fig3, ax3 = plt.subplots(figsize=(10, max(8, len(course_names) * 0.5)))
                # 注意：绘图用 ascending=True 是因为 barh 从下往上画，这样分高的在上面
                sorted_contrib_asc = course_contrib.sort_values(ascending=True)
                
                bar_colors = []
                text_colors = []
                for name in sorted_contrib_asc.index:
                    clean_name = str(name).strip()
                    if clean_name in GEN_ED_COURSES:
                        bar_colors.append('#D3D3D3'); text_colors.append('#808080')
                    elif '*' in clean_name:
                        bar_colors.append('#FFD700'); text_colors.append('#B8860B')
                    else:
                        bar_colors.append('#4682B4'); text_colors.append('black')

                bars = ax3.barh(sorted_contrib_asc.index, sorted_contrib_asc.values, color=bar_colors, edgecolor='none', alpha=0.9)
                for label, color in zip(ax3.get_yticklabels(), text_colors):
                    label.set_color(color)
                    if color != 'black': label.set_fontweight('bold')
                for i, v in enumerate(sorted_contrib_asc):
                    ax3.text(v + 0.2, i, str(int(v)), va='center', fontweight='bold', color='black')
                
                ax3.set_title("课程贡献度排名\n(🟨核心课程  ⬜通识课程  🟦其他课程)", fontsize=14, pad=15)
                ax3.set_xlabel("贡献度分值 (常规权重: H=3, M=2, L=1)")
                st.pyplot(fig3)
                pdf.savefig(fig3, bbox_inches='tight')

            # --- 图表4：指标重要度 (含自动审核) ---
            with tab4:
                st.subheader("毕业要求重要程度")
                
                # === 自动审核逻辑 ===
                weak_warnings = []
                count_idx = 1
                for req_name in df_num.columns:
                    # 统计各等级数量
                    count_h = (df_num[req_name] == 3).sum()
                    count_m = (df_num[req_name] == 2).sum()
                    count_l = (df_num[req_name] == 1).sum()
                    count_total = count_h + count_m + count_l
                    
                    # 规则：H < 2 或 总数 < 3
                    if count_h < 2 or count_total < 3:
                        warning_text = (
                            f"【薄弱指标点{count_idx}：{req_name}，"
                            f"该指标点下面有{count_total}门课程支撑，"
                            f"支撑情况分别是 {count_h}课程H、{count_m}课程M、{count_l}课程L】"
                        )
                        weak_warnings.append(warning_text)
                        count_idx += 1
                
                # 显示报警
                if weak_warnings:
                    st.error(f"⚠️ 审核不通过：检测到 {len(weak_warnings)} 个薄弱指标点！")
                    for w in weak_warnings:
                        st.markdown(f"<span style='color:red; font-weight:bold'>{w}</span>", unsafe_allow_html=True)
                    st.markdown("---")
                else:
                    st.success("✅ 审核通过：所有指标点均满足“至少2门H支撑且总支撑≥3门”的要求。")

                # 绘图 (使用 H=10 权重)
                fig4_height = max(6, num_reqs * 0.4) 
                fig4, ax4 = plt.subplots(figsize=(10, fig4_height))
                sorted_imp = req_imp_special.sort_values(ascending=True)
                sorted_imp.plot(kind='barh', color='#2E8B57', ax=ax4, edgecolor='black', alpha=0.8)
                for i, v in enumerate(sorted_imp):
                    ax4.text(v + 0.5, i, str(int(v)), va='center', fontweight='bold')
                
                ax4.set_title("毕业要求重要程度排名\n(计算依据：仅统计强支撑 H=10，M和L不计入)", fontsize=14, pad=15)
                ax4.set_xlabel("重要程度分值 (H=10)")
                
                st.pyplot(fig4)
                pdf.savefig(fig4, bbox_inches='tight')

        download_btn_placeholder.download_button(
            label="📥 点击下载最终版报告 (PDF)",
            data=pdf_buffer.getvalue(),
            file_name="西京学院商学院_课程体系分析报告.pdf",
            mime="application/pdf",
            type="primary"
        )
        st.sidebar.success(f"✅ 分析完成！共处理 {num_reqs} 个指标点。")

else:
    st.info("👈 请在左侧上传文件。")

st.markdown("---")
st.markdown(
    '''
    <div style="text-align: center; color: #888888; font-size: 14px; padding: 10px;">
        版权所有 © 西京学院商学院
    </div>
    ''',
    unsafe_allow_html=True
)
