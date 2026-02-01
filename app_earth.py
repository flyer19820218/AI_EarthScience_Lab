import streamlit as st
import google.generativeai as genai
import os
import asyncio
import edge_tts
import fitz  # 雲端自動截圖
import re
from PIL import Image

# --- 1. 頁面配置 (全黑翩翩體、星艦指揮艙風格) ---
st.set_page_config(page_title="地科 AI 星艦導航室", layout="wide")

st.markdown("""
    <style>
    html, body, [class*="css"], .stMarkdown, p, h1, h2, h3, span, label, li {
        color: #000000 !important;
        font-family: 'HanziPen SC', '翩翩體', 'KaiTi', sans-serif !important;
    }
    .guide-box {
        background-color: #f3e5f5;
        padding: 15px;
        border-radius: 12px;
        border: 2px solid #9c27b0;
        margin-bottom: 20px;
    }
    .stButton>button {
        background-color: #e8eaf6 !important;
        border-radius: 8px;
        font-weight: bold;
        width: 100%;
        height: 50px;
        font-size: 1.2rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心助教語音 (採用最穩定女聲 HsiaoChen) ---
async def generate_voice_bytes(text):
    clean_text = re.sub(r'\$+', '', text)
    clean_text = clean_text.replace('\\%', '百分之').replace('%', '百分之')
    clean_text = clean_text.replace('*', '').replace('#', '').replace('\n', ' ')
    communicate = edge_tts.Communicate(clean_text, "zh-TW-HsiaoChenNeural", rate="-2%")
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

# --- 3. 雲端截圖功能 ---
def get_pdf_page_image(pdf_path, page_index):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_index)
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
    img_data = pix.tobytes("png")
    doc.close()
    return img_data

# --- 4. 地科 23 頁【基因精確對位標題】 (完全對應 PDF 內容) ---
page_titles = {
    1: "【液態的契約：星球表面與地下水的流轉律法】", 
    2: "【時間的殘響：風化、侵蝕、搬運與堆積的重塑律法】", 
    3: "【地層的記憶體：沉積環境、化石與地史紀錄的存檔】",
    4: "【真理的疊加：地層判讀、疊置定律與截切律法】", 
    5: "【時空的斷裂：不整合面、褶皺與斷層的毀滅契約】", 
    6: "【星塵的循環：岩石種類、循環與地表變動的恆定性】",
    7: "【地球的年輪：地質年代、生命長征與地球歷史的座標】", 
    8: "【核心的脈動：地球內部構造、震波探測與能量源】", 
    9: "【大陸的航行：大陸漂移、海底擴張與星艦航向】",
    10: "【板塊的棋局：全球板塊構造、邊界對撞與能量釋放】", 
    11: "【地函的奔流：熱對流、板塊推動力與能量守恆】", 
    12: "【震盪的維度：地震波、震度、規模與震源規律】",
    13: "【裂痕的咆哮：台灣板塊位置、地震帶與宿命斷層】", 
    14: "【火神的祭壇：火山地形、岩漿冷卻與火成岩契約】", 
    15: "【星軌的圓舞曲：月相變化、朔望規律與光影博弈】",
    16: "【引力的拉扯：潮汐升降、引潮力與月球的重力律法】", 
    17: "【星球的傾斜：四季更迭、太陽直射點與黃道面契約】", 
    18: "【宇宙的尺度：天文單位、光年與星等的視覺騙局】",
    19: "【夜空的銀河：星系結構、類地類木與太陽系的座標】", 
    20: "【大氣的枷鎖：垂直分層、氣壓與平流層的守護】", 
    21: "【流體的博弈：高低壓系統、氣團與鋒面的對峙】",
    22: "【星球的焦慮：全球暖化、溫室氣體與命運的終焉】", 
    23: "【臭氧的漏洞：紫外的侵蝕與守護層的崩解】"
}

# --- 5. 初始化 Session ---
if 'audio_data' not in st.session_state: st.session_state.audio_data = None

# --- 6. 通行證指南 ---
st.title("🚀 地科 AI 星艦導航室 (馬斯克女聲版)")
st.markdown("""<div class="guide-box"><b>📖 快速指南：</b>貼上 API 通行證後，選擇星球單元即可發射導航。</div>""", unsafe_allow_html=True)
user_key = st.text_input("🔑 通行證：", type="password")

st.divider()

# --- 7. 提問區 ---
st.subheader("💬 星球數據諮詢")
col_q, col_up = st.columns([1, 1])
with col_q: student_q = st.text_input("輸入問題：")
with col_up: uploaded_file = st.file_uploader("拍照諮詢：", type=["jpg", "png", "jpeg"])

if (student_q or uploaded_file) and user_key:
    with st.spinner("火箭正在填充燃料，準備進入同步軌道處理數據..."):
        try:
            genai.configure(api_key=user_key)
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            parts = ["你是地科 AI 助教馬斯克。請**嚴格全程使用繁體中文**，用雞排珍奶比喻，公式 LaTeX。"]
            if uploaded_file: parts.append(Image.open(uploaded_file))
            if student_q: parts.append(student_q)
            res = model.generate_content(parts)
            st.info(f"💡 助教解答：\n\n{res.text}")
        except Exception as e: st.error(f"數據分析失敗：{e}")

st.divider()

# --- 8. 選單 (23 頁精確對應) ---
st.subheader("📖 啟動導航：選擇單元")
parts_list = ["【一：地表與地層律法】", "【二：板塊與構造契約】", "【三：天文與引力律法】", "【四：大氣與星球命運】"]
part_choice = st.selectbox("第一步：選擇大章節區域", parts_list)

if "一" in part_choice: r = range(1, 8)
elif "二" in part_choice: r = range(8, 15)
elif "三" in part_choice: r = range(15, 20)
else: r = range(20, 24)

options = [f"第 {p} 頁：{page_titles.get(p, '單元詳解')}" for p in r]
selected_page_str = st.selectbox("第二步：精確單元名稱", options)
target_page = int(re.search(r"第 (\d+) 頁", selected_page_str).group(1))

# --- 9. 導讀按鈕 ---
if st.button(f"🚀 啟動【第 {target_page} 頁】導航教學"):
    if not user_key:
        st.warning("請先輸入金鑰。")
    else:
        genai.configure(api_key=user_key)
        path_finals = os.path.join(os.getcwd(), "data", "地科finals.pdf")
        with st.spinner("火箭正在填充燃料，準備點火發射導航數據..."):
            try:
                # 1. 截圖
                page_img = get_pdf_page_image(path_finals, target_page - 1)
                st.image(page_img, caption=f"觀測數據：{page_titles[target_page]}", use_column_width=True)
                
                # 2. AI 講解
                file_obj = genai.upload_file(path=path_finals)
                model = genai.GenerativeModel('models/gemini-2.5-flash')
                prompt = [
                    file_obj, 
                    f"你現在是地科 AI 助教馬斯克。請針對講義第 {target_page} 頁進行繁中導讀。"
                    "開場提雞排珍奶，用火箭術語比喻。公式 LaTeX。不准說英文。"
                ]
                res = model.generate_content(prompt)
                st.markdown(res.text)
                
                # 3. 音訊
                st.session_state.audio_data = asyncio.run(generate_voice_bytes(res.text))
                st.balloons()
            except Exception as e: st.error(f"導航失敗：{e}")

# --- 10. 音訊播放 ---
if st.session_state.audio_data:
    st.markdown("---")
    st.info("🔊 **星艦提醒**：請點擊播放鈕聽取導航語音。")
    st.audio(st.session_state.audio_data, format="audio/mp3")