import streamlit as st
import google.generativeai as genai
import os, asyncio, edge_tts, re, base64, io, random
from PIL import Image

# --- 零件檢查 ---
try:
    import fitz # pymupdf
except ImportError:
    st.error("❌ 零件缺失！")
    st.stop()

# --- 1. 核心視覺規範 (完全保留您的設定) ---
st.set_page_config(page_title="臻·極速自然能量域", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp, [data-testid="stAppViewContainer"], .stMain, [data-testid="stHeader"] { background-color: #ffffff !important; }
    div.block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; }
    section[data-testid="stSidebar"] > div { padding-top: 1rem !important; }
    [data-testid="stSidebar"] { min-width: 320px !important; max-width: 320px !important; }
    header[data-testid="stHeader"] { background-color: transparent !important; z-index: 1 !important; }
    button[data-testid="stSidebarCollapseButton"] { color: #000000 !important; display: block !important; }
    [data-baseweb="input"], [data-baseweb="select"], [data-testid="stNumberInput"] div, [data-testid="stTextInput"] div, [data-testid="stSelectbox"] > div > div {
        background-color: #ffffff !important; border: 1px solid #d1d5db !important; border-radius: 6px !important;
    }
    html, body, .stMarkdown, p, label, li, h1, h2, h3, .stButton button, a {
        color: #000000 !important; font-family: 'HanziPen SC', '翩翩體', sans-serif !important;
    }
    .stButton button { border: 2px solid #000000 !important; background-color: #ffffff !important; font-weight: bold !important; }
    .stMarkdown p { font-size: calc(1rem + 0.3vw) !important; }
    @media (prefers-color-scheme: dark) { .stApp { background-color: #ffffff !important; color: #000000 !important; } }
    .info-box { border: 1px solid #ddd; padding: 1rem; border-radius: 8px; background-color: #f9f9f9; font-size: 0.9rem; }
    /* 曉臻文字稿美化框 */
    .transcript-box { background-color: #fdfdfd; border-left: 5px solid #000; padding: 15px; margin-bottom: 25px; line-height: 1.6; }
    </style>
""", unsafe_allow_html=True)

# --- 🚀 標題重置 ---
st.title("🏃‍♀️ 臻 · 極速自然能量域")
st.markdown("### 🔬 資深理化老師 AI 助教：曉臻老師陪你衝刺科學馬拉松")
st.divider()

# --- 2. 曉臻語音引擎 (暴力發音修正：唸法正確) ---
async def generate_voice_base64(text):
    # 這裡處理唸法：把補給變補己，保留 ～～ 讓唸速變慢
    voice_text = text.replace("補給", "補己")
    clean_text = re.sub(r'[^\w\u4e00-\u9fff\d，。！？「」～ ]', '', voice_text)
    communicate = edge_tts.Communicate(clean_text, "zh-TW-HsiaoChenNeural", rate="-2%")
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio": audio_data += chunk["data"]
    b64 = base64.b64encode(audio_data).decode()
    return f'<audio controls autoplay style="width:100%"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'

# --- 💡 新增：視覺文字洗淨邏輯 (書寫正確) ---
def clean_for_eye(text):
    """將語音用的符號抹除，還原成正確的書寫方式"""
    # 1. 移除分頁標籤
    t = text.replace("---PAGE_SEP---", "")
    # 2. 移除英文/數字中間的波浪號與空格 (B～～ D～～ -> BD)
    t = re.sub(r'([a-zA-Z0-9])～～\s*', r'\1', t)
    # 3. 移除中文中間的波浪號 (三～～一～～ -> 三一)
    t = t.replace("～～", "")
    return t

# --- 3. 側邊欄 ---
st.sidebar.title("🚪 打開實驗室大門-金鑰")
st.sidebar.markdown("""<div class="info-box"><b>📢 曉臻老師的叮嚀：</b>...</div>""", unsafe_allow_html=True)
user_key = st.sidebar.text_input("🔑 實驗室啟動金鑰", type="password", key="tower_key")
st.sidebar.divider()
student_q = st.sidebar.text_input("打字問曉臻：", key="science_q")
uploaded_file = st.sidebar.file_uploader("📸 照片區：", type=["jpg", "png", "jpeg"], key="science_f")

# --- 4. 曉臻教學 6 項核心指令 ---
SYSTEM_PROMPT = """
你是資深自然科學助教曉臻，馬拉松選手 (PB 92分)。
你現在要進行一次導讀連續 5 頁講義的課程。請遵循以下規範：

1. 【熱血開場】：隨機 30 秒聊運動對大腦的好處。結尾必含：『熱身一下下課老師就要去跑步了』。
2. 【翻頁導航】：除第一頁外，解說完才唸『翻到第 X 頁』。每頁解說「最開頭」加上標籤『---PAGE_SEP---』。
3. 【練習題】：偵測到題目先公佈「正確答案」，再做「分段配速解說」。
4. 【上下文】：將 5 頁內容串接。
5. 【轉譯規範】：
   - ⚠️ 語音暴力：所有的「補給站」輸出為『補給站』。
   - ⚠️ 慢速標記：所有的「英文」、「數字」、「化學式」必須拆開，每個字符後加「～～」標記與空格。
   - 範例：BDNF 寫作「B～～ D～～ N～～ F～～ 」、H2 寫作「H～～ two～～ 」。
6. 【真理激勵】：結尾必喊：『這就是自然科學的真理！』。
"""

# --- 5. 導航系統 ---
col1, col2, col3 = st.columns([1, 1, 1])
with col1: vol_select = st.selectbox("📚 冊別選擇", ["第一冊", "第二冊", "第三冊", "第四冊", "第五冊", "第六冊"], index=3)
with col2: chap_select = st.selectbox("🧪 章節選擇", ["第一章", "第二章", "第三章", "第四章", "第五章", "第六章"], index=0)
with col3: start_page = st.number_input("🏁 起始頁碼", 1, 100, 1, key="start_pg")

filename = f"{vol_select}_{chap_select}.pdf" # 簡化檔名邏輯維持原樣
pdf_path = os.path.join("data", filename)

if "class_started" not in st.session_state: st.session_state.class_started = False
if "audio_html" not in st.session_state: st.session_state.audio_html = None
if "display_images" not in st.session_state: st.session_state.display_images = []
if "res_text" not in st.session_state: st.session_state.res_text = ""

# --- 主畫面邏輯 ---
if not st.session_state.class_started:
    st.info("🏃‍♀️ 曉臻老師正在熱身準備中...")
    if st.button(f"🏃‍♀️ 開始馬拉松課程", type="primary", use_container_width=True):
        if user_key and os.path.exists(pdf_path):
            with st.spinner("曉臻正在翻閱講義..."):
                doc = fitz.open(pdf_path)
                images_to_process, display_images_list = [], []
                pages_to_read = range(start_page - 1, min(start_page + 4, len(doc)))
                for page_num in pages_to_read:
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img = Image.open(io.BytesIO(pix.tobytes()))
                    images_to_process.append(img)
                    display_images_list.append((page_num + 1, img))
                
                genai.configure(api_key=user_key)
                MODEL = genai.GenerativeModel('models/gemini-2.5-flash') 
                res = MODEL.generate_content([f"{SYSTEM_PROMPT}\n導讀第{start_page}頁內容。"] + images_to_process)
                
                st.session_state.res_text = res.text
                st.session_state.audio_html = asyncio.run(generate_voice_base64(res.text))
                st.session_state.display_images = display_images_list
                st.session_state.class_started = True
                st.rerun()

else:
    # 狀態 B: 上課中
    st.success("🔔 曉臻老師正在上課中！")
    if st.session_state.audio_html: st.markdown(st.session_state.audio_html, unsafe_allow_html=True)
    st.divider()

    # --- 💡 核心：將原始文字切開並「洗淨」後顯示 ---
    raw_text = st.session_state.get("res_text", "")
    parts = raw_text.split("---PAGE_SEP---")

    # 顯示洗乾淨的開場白
    if len(parts) > 0:
        with st.chat_message("曉臻"):
            st.markdown(clean_for_eye(parts[0]))

    for i, (p_num, img) in enumerate(st.session_state.display_images):
        st.image(img, caption=f"第 {p_num} 頁", use_container_width=True)
        # 顯示該頁洗乾淨的逐字稿
        if (i + 1) < len(parts):
            st.markdown(f'<div class="transcript-box"><b>📜 曉臻老師的叮嚀 (P.{p_num})：</b><br>{clean_for_eye(parts[i+1])}</div>', unsafe_allow_html=True)
        st.divider()

    if st.button("🏁 下課休息"):
        st.session_state.class_started = False
        st.rerun()
