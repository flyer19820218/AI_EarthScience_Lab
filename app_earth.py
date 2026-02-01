import streamlit as st
import google.generativeai as genai
import os
import asyncio
import edge_tts
import fitz  # 雲端自動截圖
import re
from PIL import Image

# --- 1. 頁面配置 (翩翩體、全黑文字、星艦指揮艙風格) ---
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

# --- 2. 核心助教語音 (改回最穩定女聲：HsiaoChenNeural) ---
async def generate_voice_bytes(text):
    clean_text = re.sub(r'\$+', '', text)
    clean_text = clean_text.replace('\\%', '百分之').replace('%', '百分之')
    clean_text = clean_text.replace('*', '').replace('#', '').replace('\n', ' ')
    
    # 使用最穩定的 HsiaoChenNeural 女聲
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

# --- 4. 地科講義 23 頁熱血標題 (馬斯克狂想校準版) ---
page_titles = {
    1: "【液態的契約：星球表面與地下水的流轉律法】", 
    2: "【時間的殘響：風化侵蝕與大地雕刻術】", 
    3: "【地層的記憶體：沉積環境與化石存檔】",
    4: "【真理的疊加：地層順序與截切定律】", 
    5: "【時空的斷裂：斷層、褶皺與不整合契約】", 
    6: "【星塵的循環：岩石循環與物質守恆】",
    7: "【地球的年輪：地質年代與生命長征】", 
    8: "【核心的脈動：地球內部構造與能量源】", 
    9: "【大陸的航行：大陸漂移與海底擴張禁咒】",
    10: "【板塊的棋局：全球板塊構造與邊界對撞】", 
    11: "【地函的奔流：熱對流與板塊推動力】", 
    12: "【震盪的維度：地震波與震度規律】",
    13: "【裂痕的咆哮：台灣地震帶與板塊位置】", 
    14: "【火神的祭壇：火山地形與岩漿冷卻契約】", 
    15: "【星軌的圓舞曲：月相變化與朔望規律】",
    16: "【引力的拉扯：潮汐升降與月球引力律法】", 
    17: "【星球的傾斜：四季更迭與太陽直射點】", 
    18: "【宇宙的尺度：天文單位、光年與星等】",
    19: "【夜空的銀河：星系結構與太陽系的座標】", 
    20: "【大氣的枷鎖：垂直分層與臭氧守護層】", 
    21: "【流體的博弈：高低壓系統與鋒面法則】",
    22: "【星球的焦慮：全球暖化與溫室氣體終焉】", 
    23: "【臭氧的漏洞：紫外的侵蝕與守護層崩解】"
}

# --- 5. 初始化 Session ---
if 'audio_data' not in st.session_state: st.session_state.audio_data = None

# --- 6. 通行證申請教學 ---
st.title("🚀 地科 AI 星艦導航室 (馬斯克女聲版)")
st.markdown("""
<div class="guide-box">
    <b>📖 學生快速通行指南：</b><br>
    1. 前往 <a href="https://aistudio.google.com/app/apikey" target="_blank">Google AI Studio</a>。<br>
    2. 點擊 <b>Create API key</b>，<b>務必勾選兩次同意條款</b>。<br>
    3. 貼回下方「通行證」欄位按 Enter 啟動導航。
</div>
""", unsafe_allow_html=True)

user_key = st.text_input("🔑 通行證輸入區：", type="password")
st.divider()

# --- 7. 學生提問專區 ---
st.subheader("💬 星球數據諮詢：拍照或打字")
col_q, col_up = st.columns([1, 1])
with col_q: student_q = st.text_input("輸入問題：")
with col_up: uploaded_file = st.file_uploader("上傳觀測照片：", type=["jpg", "png", "jpeg"])

if (student_q or uploaded_file) and user_key:
    with st.spinner("火箭正在填充燃料，準備進入同步軌道處理數據..."):
        try:
            genai.configure(api_key=user_key)
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            parts = [
                "你現在是地科 AI 助教馬斯克。請**嚴格全程使用繁體中文**回答。"
                "開場提雞排配大杯珍奶。所有公式 LaTeX。用火箭與星際探索比喻。"
            ]
            if uploaded_file: parts.append(Image.open(uploaded_file))
            if student_q: parts.append(student_q)
            res = model.generate_content(parts)
            st.info(f"💡 助教解答：\n\n{res.text}")
        except Exception as e: st.error(f"數據分析失敗：{e}")

st.divider()

# --- 8. 地科選單 ---
st.subheader("📖 啟動導航：選擇學習單元")
parts_list = ["【一：液態與地表律法】", "【二：板塊與對撞契約】", "【三：星軌與引力律法】", "【四：大氣與終焉】"]
part_choice = st.selectbox("第一步：選擇星球單元", parts_list)

if "一" in part_choice: r = range(1, 8)
elif "二" in part_choice: r = range(8, 15)
elif "三" in part_choice: r = range(15, 20)
else: r = range(20, 24)

options = [f"第 {p} 頁：{page_titles.get(p, '數據詳解')}" for p in r]
selected_page_str = st.selectbox("第二步：精確單元名稱", options)
target_page = int(re.search(r"第 (\d+) 頁", selected_page_str).group(1))

# --- 9. 核心導讀按鈕 ---
if st.button(f"🚀 啟動【第 {target_page} 頁】導航教學"):
    if not user_key:
        st.warning("請先輸入金鑰。")
    else:
        genai.configure(api_key=user_key)
        path_finals = os.path.join(os.getcwd(), "data", "地科finals.pdf")
        with st.spinner("火箭正在填充燃料，準備點火發射導航數據..."):
            try:
                # 1. 雲端截圖
                page_img = get_pdf_page_image(path_finals, target_page - 1)
                st.image(page_img, caption=f"觀測數據：{page_titles[target_page]}", use_column_width=True)
                
                # 2. AI 講解 (繁體中文強制鎖定)
                file_obj = genai.upload_file(path=path_finals)
                model = genai.GenerativeModel('models/gemini-2.5-flash')
                prompt = [
                    file_obj, 
                    f"你現在是地科 AI 助教馬斯克。請**嚴格全程使用繁體中文**詳細導讀講義第 {target_page} 頁。"
                    "1. 開場提雞排珍奶。2. 火箭術語比喻。3. 公式 LaTeX。4. 不准出測驗。5. 絕對不准說英文。"
                ]
                res = model.generate_content(prompt)
                st.markdown(res.text)
                
                # 3. 音訊生成 (原生穩定版)
                st.session_state.audio_data = asyncio.run(generate_voice_bytes(res.text))
                st.balloons()
            except Exception as e: st.error(f"發射失敗：{e}")

# --- 10. 音訊播放 ---
if st.session_state.audio_data:
    st.markdown("---")
    st.info("🔊 **星艦提醒**：請點擊播放鈕聽取繁中導航語音。")
    st.audio(st.session_state.audio_data, format="audio/mp3")