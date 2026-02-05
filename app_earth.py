
import streamlit as st
import google.generativeai as genai
import os
import asyncio
import edge_tts
import fitz  # 雲端截圖專用
import re
import base64
from PIL import Image

# --- 1. 頁面配置 (全平台抗暗色模式 & 翩翩體鎖定) ---
st.set_page_config(page_title="地科 AI 星艦導航室", layout="wide")

# --- 1. 頁面配置 (行動/平版雙模適配 + 白晝協議) ---
st.set_page_config(page_title="地科 AI 星艦導航室", layout="wide")

st.markdown("""
    <style>
    /* A. 全域白晝協議：強制所有載具背景為白色，文字為全黑 */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stToolbar"], .stMain {
        background-color: #ffffff !important;
    }
    html, body, [class*="css"], .stMarkdown, p, span, label, li {
        color: #000000 !important;
        font-family: 'HanziPen SC', '翩翩體', 'PingFang TC', 'Heiti TC', 'Microsoft JhengHei', sans-serif !important;
    }

    /* B. 雙模適配：手機端(自動縮小邊距) vs 平版端(維持寬廣) */
    [data-testid="stAppViewBlockContainer"] {
        padding: 1.5rem 1rem !important; /* 縮小手機兩側白邊 */
    }
    
    /* 標題字體隨螢幕寬度自動縮放 (calc 魔法) */
    h1 { font-size: calc(1.5rem + 1.2vw) !important; text-align: center; }
    h3 { font-size: calc(1.1rem + 0.5vw) !important; }

    /* C. 終極解鎖：修正蘋果手機下拉選單 (Selectbox) 黑底黑字問題 */
    div[data-baseweb="popover"], div[data-baseweb="listbox"], ul[role="listbox"], li[role="option"] {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    li[role="option"] div, li[role="option"] span {
        color: #000000 !important;
        background-color: #ffffff !important;
    }

    /* D. 組件鎖定：打字區與下拉選單本體 (白底黑字) */
    div[data-testid="stTextInput"] input, div[data-baseweb="select"], div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        border: 2px solid #000000 !important;
    }

    /* E. 拍照截圖區：中文化與白晝鎖定 */
    [data-testid="stFileUploader"] section { background-color: #ffffff !important; border: 2px dashed #000000 !important; }
    [data-testid="stFileUploader"] button { background-color: #ffffff !important; color: #000000 !important; border: 1px solid #000000 !important; }
    [data-testid="stFileUploader"] button div span { font-size: 0 !important; }
    [data-testid="stFileUploader"] button div span::before { content: "瀏覽檔案" !important; font-size: 1rem !important; color: #000000 !important; }

    /* F. 地科專屬紫色導覽框 */
    .guide-box {
        background-color: #f3e5f5 !important;
        color: #000000 !important;
        padding: 15px;
        border-radius: 12px;
        border: 2px solid #9c27b0;
        margin-bottom: 20px;
    }

    /* G. 按鈕行動優化：寬度 100% 好點擊，星艦靛藍風格 */
    div.stButton > button {
        background-color: #e8eaf6 !important; 
        color: #000000 !important;
        border: 2px solid #3f51b5 !important;
        border-radius: 12px !important;
        width: 100% !important;
        height: 3.5rem !important;
        font-weight: bold !important;
    }

    /* H. LaTeX 顏色鎖定與暗色模式硬性覆蓋 */
    .katex { color: #000000 !important; }
    @media (prefers-color-scheme: dark) {
        .stApp, div[data-testid="stTextInput"] input, section[data-testid="stFileUploader"], [data-testid="stFileUploader"] button, div[data-baseweb="popover"] {
            background-color: #ffffff !important;
            color: #000000 !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心助教語音 (iPad 專用 Base64 強效封裝方案) ---
async def generate_voice_base64(text):
    clean_text = re.sub(r'\$+', '', text)
    clean_text = clean_text.replace('\\%', '百分之').replace('%', '百分之')
    clean_text = clean_text.replace('*', '').replace('#', '').replace('\n', ' ')
    communicate = edge_tts.Communicate(clean_text, "zh-TW-HsiaoChenNeural", rate="-2%")
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    b64 = base64.b64encode(audio_data).decode()
    return f'<audio controls style="width:100%"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'

# --- 3. 雲端截圖功能 ---
def get_pdf_page_image(pdf_path, page_index):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_index)
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
    img_data = pix.tobytes("png")
    doc.close()
    return img_data

# --- 4. 地科 23 頁標題 (完整保留) ---
page_titles = {
    1: "1. 地下水與流轉律法",
    2: "2. 侵蝕、搬運與沉積",
    3: "3. 三大岩石與礦物硬度",
    4: "4. 褶皺與斷層的崩裂",
    5: "5. 地震波、規模與震度",
    6: "6. 板塊漂移與擴張",
    7: "7. 聚合與張裂碰撞",
    8: "8. 台灣板塊夾擊現況",
    9: "9. 地層序列與切割律",
    10: "10. 化石與地質年代",
    11: "11. 星球自轉與晝夜輪迴",
    12: "12. 四季更迭與太陽軌跡",
    13: "13. 月相盈虧與日地月位面",
    14: "14. 潮汐漲落與 50 分鐘宿命",
    15: "15. 日食、月食與食之重合",
    16: "16. 大氣垂直構造",
    17: "17. 氣壓與等壓線風之路徑",
    18: "18. 相對溼度與雲端召喚",
    19: "19. 冷暖鋒面的戰場",
    20: "20. 台灣季風與地形效應",
    21: "21. 颱風螺旋與毀滅禁咒",
    22: "22. 全球暖化溫室囚籠",
    23: "23. 臭氧漏洞與守護層崩解"
}

# --- 5. 初始化 Session ---
if 'audio_html' not in st.session_state: st.session_state.audio_html = None

# --- 6. 核心 API 通行證指南 ---
st.title("🚀 地科 AI 星艦導航室 (馬斯克助教版)")
st.markdown("""
<div class="guide-box">
    <b>📖 學生快速通行指南：</b><br>
    1. 前往 <a href="https://aistudio.google.com/app/apikey" target="_blank">Google AI Studio</a> 並登入。<br>
    2. 點擊 <b>Create API key</b>，<b>務必勾選兩次同意條款</b>。<br>
    3. 貼回下方「通行證」欄位按 Enter 啟動馬斯克。
</div>
""", unsafe_allow_html=True)

user_key = st.text_input("🔑 通行證輸入區：", type="password")
st.divider()

# --- 7. 提問區 ---
st.subheader("💬 星球數據諮詢：拍照或打字提問")
col_q, col_up = st.columns([1, 1])
with col_q: student_q = st.text_input("打字提問星球真理：", placeholder="例如：為什麼台灣地震這麼多？")
with col_up: uploaded_file = st.file_uploader("拍照詢問馬斯克助教：", type=["jpg", "png", "jpeg"])

if (student_q or uploaded_file) and user_key:
    with st.spinner("火箭正在填充燃料，準備進入同步軌道處理數據..."):
        try:
            genai.configure(api_key=user_key)
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            parts = [
                "你現在是地科 AI 助教馬斯克。請**嚴格全程使用繁體中文**回答。"
                "開場提雞排配大杯珍奶。用火箭與星際探索比喻。公式必須 LaTeX。"
            ]
            if uploaded_file: parts.append(Image.open(uploaded_file))
            if student_q: parts.append(student_q)
            res = model.generate_content(parts)
            st.info(f"💡 助教解答：\n\n{res.text}")
        except Exception as e: st.error(f"數據分析失敗：{e}")

st.divider()

# --- 8. 選單 (23 頁精確對應) ---
st.subheader("📖 啟動導航：選擇學習單元區域")
parts_list = ["【一：地表與地層律法】", "【二：板塊與構造契約】", "【三：天文與引力律法】", "【四：大氣與星球命運】"]
part_choice = st.selectbox("第一步：選擇大章節區域", parts_list)

if "一" in part_choice: r = range(1, 8)
elif "二" in part_choice: r = range(8, 15)
elif "三" in part_choice: r = range(15, 20)
else: r = range(20, 24)

options = [f"第 {p} 頁：{page_titles.get(p, '單元詳解')}" for p in r]
selected_page_str = st.selectbox("第二步：精確單元名稱 (不跳頁)", options)
target_page = int(re.search(r"第 (\d+) 頁", selected_page_str).group(1))

# --- 9. 核心導讀按鈕 ---
if st.button(f"🚀 啟動【第 {target_page} 頁】圖文導讀"):
    if not user_key:
        st.warning("請先輸入通行證。")
    else:
        genai.configure(api_key=user_key)
        path_finals = os.path.join(os.getcwd(), "data", "地科finals.pdf")
        with st.spinner("火箭正在填充燃料，準備點火發射導航數據..."):
            try:
                page_img = get_pdf_page_image(path_finals, target_page - 1)
                st.image(page_img, caption=f"觀測數據：{page_titles[target_page]}", use_column_width=True)
                
                file_obj = genai.upload_file(path=path_finals)
                model = genai.GenerativeModel('models/gemini-2.5-flash')
                prompt = [
                    file_obj, 
                    f"你現在是地科 AI 助教馬斯克。請**嚴格全程使用繁體中文**詳細導讀講義第 {target_page} 頁。"
                    "開場提雞排珍奶。用火箭與星際探索比喻。公式 LaTeX。不准出測驗。絕對不准說英文。"
                ]
                res = model.generate_content(prompt)
                st.markdown(res.text)
                
                st.session_state.audio_html = asyncio.run(generate_voice_base64(res.text))
                st.balloons()
            except Exception as e: st.error(f"導航失敗：{e}")

if st.session_state.audio_html:
    st.markdown("---")
    st.info("🔊 **星艦提醒**：請點擊下方播放鈕聽取繁中導航語音。")
    st.markdown(st.session_state.audio_html, unsafe_allow_html=True)
