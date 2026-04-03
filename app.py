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
import matplotlib.patches as mpatches 
import platform
import math
import textwrap

# ================= 1. 页面标题配置 =================
st.set_page_config(page_title="课程目标达成度分析系统", layout="wide")
st.title("🎓 基于OBE理念的专业课程体系与毕业要求关联度矩阵分析系统")
st.markdown("### 西京学院 | 人才培养方案修订辅助管理工具")

# ================= 2. 字体与基础配置 =================
font_list = ['WenQuanYi Micro Hei', 'Heiti TC', 'PingFang HK', 'Arial Unicode MS', 'SimHei']
plt.rcParams['font.sans-serif'] = font_list
plt.rcParams['axes.unicode_minus'] = False 

system_name = platform.system()
if system_name == "Linux":
    NETWORK_FONT = 'WenQuanYi Micro Hei'
else:
    NETWORK_FONT = 'Heiti TC' 

# 权重配置
WEIGHT_MAP = {'H': 3, 'h': 3, '3': 3, 'High': 3, 'M': 2, 'm': 2, '2': 2, 'Medium': 2, 'L': 1, 'l': 1, '1': 1, 'Low': 1, '': 0, ' ': 0, 'nan': 0}
WEIGHT_MAP_SPECIAL = {'H': 10, 'h': 10, '3': 10, 'High': 10, 'M': 0, 'm': 0, '2': 0, 'Medium': 0, 'L': 0, 'l': 0, '1': 0, 'Low': 0, '': 0, ' ': 0, 'nan': 0}

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

# ================= 3. 核心审核逻辑 =================
def run_full_audit(df_num, course_contrib):
    audit_logs = {"indicators": [], "courses": []}
    
    # A. 指标点审核
    count_idx = 1
    has_weak_reqs = False
    for req_name in df_num.columns:
        count_h = (df_num[req_name] == 3).sum()
        count_m = (df_num[req_name] == 2).sum()
        count_l = (df_num[req_name] == 1).sum()
        count_total = count_h + count_m + count_l
        
        if count_h < 2 or count_total < 3:
            has_weak_reqs = True
            msg = f"❌ 薄弱指标点{count_idx}：{req_name} (总支撑{count_total}门: {count_h}H / {count_m}M / {count_l}L)"
            audit_logs["indicators"].append(msg)
            count_idx += 1
            
    if not has_weak_reqs:
        audit_logs["indicators"].append("✅ 所有毕业要求指标点均达标 (≥2门H支撑 且 总支撑≥3门)")

    # B. 课程审核
    df_sorted = course_contrib.sort_values(ascending=False)
    total_courses = len(df_sorted)
    core_courses = [c for c in df_sorted.index if '*' in str(c)]
    
    # B1. 零支撑
    zero_courses = df_sorted[df_sorted == 0].index.tolist()
    if zero_courses:
        for zc in zero_courses:
            audit_logs["courses"].append(f"❌ 课程零支撑：{zc} (请核查)")
    else:
        audit_logs["courses"].append("✅ 无零支撑课程")
        
    # B2. 核心课程
    if not core_courses:
        audit_logs["courses"].append("⛔ 严重错误：未检测到专业核心课程 (请检查 * 标识)")
    else:
        top_third_threshold = math.ceil(total_courses / 3)
        top_third_courses = df_sorted.index[:top_third_threshold].tolist()
        
        for core in core_courses:
            if core not in top_third_courses:
                audit_logs["courses"].append(f"⚠️ 排名预警：专业核心课程《{core}》未进入贡献度前1/3")
        
        if total_courses > 10:
            bottom_10_courses = df_sorted.index[-10:].tolist()
            for core in core_courses:
                if core in bottom_10_courses:
                    audit_logs["courses"].append(f"🚫 严重警告：专业核心课程《{core}》位于边缘课程 (倒数10名)")
    
    return audit_logs

# ================= 4. PDF 报告生成器 =================
def create_audit_report_figure(audit_logs):
    fig = plt.figure(figsize=(11.69, 16.53))
    plt.axis('off')
    
    plt.text(0.5, 0.95, "智能审核诊断报告", ha='center', fontsize=24, weight='bold')
    plt.text(0.5, 0.92, "西京学院 | 人才培养方案修订辅助管理工具", ha='center', fontsize=14, color='gray')
    
    cursor_y = 0.88
    line_height = 0.025
    
    plt.text(0.1, cursor_y, "【毕业要求指标点审核】", fontsize=16, weight='bold', color='#2E8B57')
    cursor_y -= 0.04
    if not audit_logs["indicators"]:
        plt.text(0.12, cursor_y, "无数据", fontsize=12)
    for log in audit_logs["indicators"]:
        color = 'red' if '❌' in log else 'black'
        if '✅' in log: color = 'green'
        wrapped_lines = textwrap.wrap(log, width=60)
        for line in wrapped_lines:
            plt.text(0.12, cursor_y, line, fontsize=12, color=color)
            cursor_y -= line_height
    cursor_y -= 0.04
    
    plt.text(0.1, cursor_y, "【课程贡献度审核】", fontsize=16, weight='bold', color='#4682B4')
    cursor_y -= 0.04
    for log in audit_logs["courses"]:
        color = 'black'
        if '❌' in log or '⛔' in log or '🚫' in log: color = 'red'
        elif '⚠️' in log: color = '#B8860B'
        elif '✅' in log: color = 'green'
        wrapped_lines = textwrap.wrap(log, width=60)
        for line in wrapped_lines:
            plt.text(0.12, cursor_y, line, fontsize=12, color=color)
            cursor_y -= line_height

    plt.text(0.5, 0.05, "本报告由系统自动生成，仅供参考", ha='center', fontsize=10, color='gray')
    return fig

# ================= 5. 主程序 =================
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
        
        df_num_special = req_data.copy()
        for col in df_num_special.columns:
            df_num_special[col] = df_num_special[col].astype(str).str.strip().map(lambda x: WEIGHT_MAP_SPECIAL.get(x, 0)).fillna(0)
        df_num_special.index = course_names

        df_display_labels = df_num.apply(lambda col: col.map(lambda x: REVERSE_LABEL_MAP.get(x, '')))
        
        course_contribution = df_num.sum(axis=1)
        req_importance_special = df_num_special.sum(axis=0)
        
        audit_logs = run_full_audit(df_num, course_contribution)
        
        return df_num, df_display_labels, course_names, req_names, course_contribution, req_importance_special, audit_logs
    except Exception as e:
        st.error(f"文件处理出错: {e}")
        return None

# ================= 6. 侧边栏 =================
with st.sidebar:
    st.header("📂 数据中心")
    uploaded_file = st.file_uploader("上传课程矩阵文件 (支持Excel/CSV)", type=['csv', 'xlsx', 'xls'])
    download_btn_placeholder = st.empty()
    st.markdown("---")
    st.info("💡 **系统功能**：\n自动生成诊断报告并写入PDF。\n包含薄弱点分析与核心课程审查。")

# ================= 7. 主界面 =================
if uploaded_file is not None:
    results = generate_analysis(uploaded_file)
    
    if results:
        df_num, df_display_labels, course_names, req_names, course_contrib, req_imp_special, audit_logs = results
        
        num_reqs = len(req_names)
        if num_reqs <= 12: font_size = 11; label_rotation = 45; heatmap_width = 12
        elif num_reqs <= 25: font_size = 9; label_rotation = 45; heatmap_width = 14
        else: font_size = 6; label_rotation = 90; heatmap_width = 18
            
        pdf_buffer = BytesIO()
        
        with PdfPages(pdf_buffer) as pdf:
            
            # 1. 审核报告页
            audit_fig = create_audit_report_figure(audit_logs)
            pdf.savefig(audit_fig, bbox_inches='tight')
            plt.close(audit_fig)
            
            tab1, tab2, tab3, tab4 = st.tabs(["矩阵热力图", "支撑网络图", "课程贡献排名", "指标重要度"])
            
            # 2. 矩阵图
            with tab1:
                st.subheader(f"课程 - 毕业要求支撑矩阵")
                fig1, ax1 = plt.subplots(figsize=(heatmap_width, max(10, len(course_names) * 0.6)))
                cmap = ListedColormap(['#f5f5f5', '#FFD700', '#FF8C00', '#FF4500'])
                sns.heatmap(df_num, annot=df_display_labels.values, fmt='', cmap=cmap, cbar=False, 
                            linewidths=0.5, linecolor='gray', ax=ax1, vmin=0, vmax=3,
                            annot_kws={"size": font_size, "color": "black", "weight": "bold"}) 
                ax1.set_ylabel('课程名称', fontsize=12)
                ax1.xaxis.tick_top(); ax1.xaxis.set_label_position('top') 
                ax1.set_xticklabels(req_names, rotation=label_rotation, ha='left', fontsize=font_size)
                st.pyplot(fig1); pdf.savefig(fig1, bbox_inches='tight') 

            # 3. 网络图
            with tab2:
                st.subheader("支撑关系网络拓扑")
                sorted_course_names = course_contrib.sort_values(ascending=True).index.tolist()
                sorted_course_values = [course_contrib[c] for c in sorted_course_names]
                course_node_sizes = [100 + v * 15 for v in sorted_course_values]
                req_values = [req_imp_special[r] for r in req_names]
                req_node_sizes = [100 + v * 8 for v in req_values]

                pos = {}
                y_course = np.linspace(0, 1, len(sorted_course_names))
                for i, course in enumerate(sorted_course_names):
                    pos[course] = np.array([-1, y_course[i]])
                y_req = np.linspace(0, 1, len(req_names))
                for i, req in enumerate(req_names):
                    pos[req] = np.array([1, y_req[i]])
                
                net_height = max(12, max(len(course_names), len(req_names)) * 0.5)
                fig2, ax2 = plt.subplots(figsize=(14, net_height))
                G = nx.Graph()
                G.add_nodes_from(sorted_course_names, bipartite=0); G.add_nodes_from(req_names, bipartite=1)
                edges, colors, widths = [], [], []
                for c in sorted_course_names:
                    for r in req_names:
                        w = df_num.loc[c, r] 
                        if w > 0:
                            G.add_edge(c, r); edges.append((c, r)); colors.append(COLOR_MAP[w]); widths.append(w * 0.6)
                
                nx.draw_networkx_nodes(G, pos, nodelist=sorted_course_names, node_color='#87CEEB', node_size=course_node_sizes, ax=ax2)
                nx.draw_networkx_nodes(G, pos, nodelist=req_names, node_color='#90EE90', node_size=req_node_sizes, ax=ax2)
                line_alpha = 0.3 if num_reqs > 30 else 0.5
                nx.draw_networkx_edges(G, pos, edge_color=colors, width=widths, alpha=line_alpha, ax=ax2)
                
                left_labels_dict = {c: f"{c} ({int(course_contrib[c])})" for c in sorted_course_names}
                label_pos_left = {n: (x-0.05, y) for n, (x, y) in pos.items() if n in sorted_course_names}
                nx.draw_networkx_labels(G, label_pos_left, labels=left_labels_dict, font_family=NETWORK_FONT, font_size=8, ax=ax2, horizontalalignment='right', bbox=dict(facecolor='white', edgecolor='none', alpha=0.6, pad=0))
                label_pos_right = {n: (x+0.05, y) for n, (x, y) in pos.items() if n in req_names}
                right_font = 8 if num_reqs > 30 else 10
                nx.draw_networkx_labels(G, label_pos_right, labels={n:n for n in req_names}, font_family=NETWORK_FONT, font_size=right_font, ax=ax2, horizontalalignment='left', bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=0))
                ax2.set_xlim(-1.6, 1.5); ax2.set_ylim(-0.05, 1.05); ax2.axis('off')
                ax2.set_title("支撑关系网络拓扑图\n左侧依据：综合贡献 (H*3+M*2+L*1) | 右侧依据：重要度 (H*10)", fontsize=14)
                st.pyplot(fig2); pdf.savefig(fig2, bbox_inches='tight')

            # --- 图表3：课程贡献度 (【核心修复】：Pad + Absolute Legend) ---
            with tab3:
                st.subheader("课程贡献度排名")
                for log in audit_logs["courses"]:
                    if '❌' in log or '⛔' in log or '🚫' in log: st.error(log)
                    elif '⚠️' in log: st.warning(log)
                    else: st.success(log)
                st.markdown("---")
                fig3, ax3 = plt.subplots(figsize=(10, max(8, len(course_names) * 0.5)))
                sorted_contrib_asc = course_contrib.sort_values(ascending=True)
                bar_colors = []
                text_colors = []
                for name in sorted_contrib_asc.index:
                    clean_name = str(name).strip()
                    if clean_name in GEN_ED_COURSES: bar_colors.append('#D3D3D3'); text_colors.append('#808080')
                    elif '*' in clean_name: bar_colors.append('#FFD700'); text_colors.append('#B8860B')
                    else: bar_colors.append('#4682B4'); text_colors.append('black')
                bars = ax3.barh(sorted_contrib_asc.index, sorted_contrib_asc.values, color=bar_colors, edgecolor='none', alpha=0.9)
                for label, color in zip(ax3.get_yticklabels(), text_colors):
                    label.set_color(color)
                    if color != 'black': label.set_fontweight('bold')
                for i, v in enumerate(sorted_contrib_asc):
                    ax3.text(v + 0.2, i, str(int(v)), va='center', fontweight='bold', color='black')
                
                # 【修改处】图例锚定在轴线顶部 (1.00)，标题向上 pad 55 点
                # 这样无论图多高，图例都贴着顶，标题都贴着图例，距离恒定。
                ax3.set_title("课程贡献度排名", fontsize=16, pad=55)
                
                legend_elements = [
                    mpatches.Patch(facecolor='#FFD700', edgecolor='none', label='核心课程'),
                    mpatches.Patch(facecolor='#D3D3D3', edgecolor='none', label='通识课程'),
                    mpatches.Patch(facecolor='#4682B4', edgecolor='none', label='其他课程')
                ]
                # loc='lower center' + bbox=(0.5, 1.00) 意味着图例的底边正好对齐轴的顶边
                ax3.legend(handles=legend_elements, loc='lower center', bbox_to_anchor=(0.5, 1.00), ncol=3, frameon=False, fontsize=10)
                
                ax3.set_xlabel("贡献度分值 (常规权重: H=3, M=2, L=1)")
                st.pyplot(fig3); pdf.savefig(fig3, bbox_inches='tight')

            # 5. 指标重要度
            with tab4:
                st.subheader("毕业要求重要程度")
                has_error = False
                for log in audit_logs["indicators"]:
                    if '❌' in log: 
                        st.error(log)
                        has_error = True
                if not has_error: st.success("✅ 所有指标点均达标")
                st.markdown("---")
                fig4_height = max(6, num_reqs * 0.4) 
                fig4, ax4 = plt.subplots(figsize=(10, fig4_height))
                sorted_imp = req_imp_special.sort_values(ascending=True)
                sorted_imp.plot(kind='barh', color='#2E8B57', ax=ax4, edgecolor='black', alpha=0.8)
                for i, v in enumerate(sorted_imp):
                    ax4.text(v + 0.5, i, str(int(v)), va='center', fontweight='bold')
                ax4.set_title("毕业要求重要程度排名\n(计算依据：仅统计强支撑 H=10，M和L不计入)", fontsize=14, pad=15)
                ax4.set_xlabel("重要程度分值 (H=10)")
                st.pyplot(fig4); pdf.savefig(fig4, bbox_inches='tight')

        download_btn_placeholder.download_button(
            label="📥 点击下载最终版报告 (含诊断书)",
            data=pdf_buffer.getvalue(),
            file_name="西京学院_智能审核诊断报告.pdf",
            mime="application/pdf",
            type="primary"
        )
        st.sidebar.success(f"✅ 诊断完成！\n指标点：{num_reqs} 个\n课程数：{len(course_names)} 门")

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
