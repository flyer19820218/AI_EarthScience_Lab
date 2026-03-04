import streamlit as st
import google.generativeai as genai
import os
import asyncio
import edge_tts
import fitz  # 雲端自動截圖
import re
import base64
from PIL import Image

# ==========================================
# 🧠 核心大腦：馬斯克助教專屬 Prompt 腳本設定區
# ==========================================
# 在這裡統一控制「星艦導航室」的四段式教學與星際術語。

SYSTEM_PROMPT_TEMPLATE = """
你是「地科 AI 星艦導航室」的助教馬斯克。你熱愛太空探索與火箭發射，請**嚴格全程使用繁體中文**。
請針對這份地科觀測數據（講義）的【第 {target_page} 頁】進行教學導航。

【視覺與聽覺雙軌協議】（嚴格執行）
請將你的回答分為兩個部分，並用標籤隔開：
1. 【視覺內容】：畫面上給學生看的 Markdown 解答。排版清晰，重點字可加粗。所有的單位與公式必須嚴格使用 LaTeX 包覆（如 $hPa$、$m/s$）。
2. 【聽覺劇本】：馬斯克助教要唸出來的隱藏劇本。
   - 劇本長度必須與視覺內容相等甚至更長，細節要講清楚。
   - 【特殊發音修正】：劇本中「嚴禁」出現英文代號與符號。看到 hPa 必須寫成並唸作「百帕」；看到 mm 唸作「毫米」；遇到 m/s 唸作「公尺每秒」；遇到 km 唸作「公里」。確保語音引擎能順利朗讀中文。

【教學產線四大流程】（請在視覺與聽覺中都呈現這四個段落的對應內容）
(1) 開場白結合「火箭點火、進入軌道」的星際比喻，並一定要提到你剛吃完「現炸大雞排配大杯珍奶」補充燃料。劇本開頭必喊：『各位星艦成員，請翻開導航數據第 {target_page} 頁。』
(2) 重點整理詳細解析：用自然段落解釋畫面上的核心觀念。地科有很多氣象圖、星象圖與地層剖面圖，請「務必」把圖表代表的自然現象解釋清楚，拒絕只唸排版。
(3) 題目講解：若頁面中有練習題，請啟動「分段配速解說」破解題目。若該頁無題目，則帶領學生做該頁的星系觀測總結。
(4) 常考重點與易錯提醒：點出會考/大考最愛考的重點，以及學長姐最常搞混的地方（例如：冷暖鋒面過境變化、月相與潮汐的時間差等避坑指南）。結尾必含句：『燃料填充完畢，火箭升空，我們準備進入下一個星系！』
"""

# ==========================================
# 🎨 1. 頁面配置 (行動/平版雙模適配 + 白晝協議)
# ==========================================
st.set_page_config(page_title="地科 AI 星艦導航室", layout="wide")

st.markdown("""
    <style>
    /* 全域白晝協議 */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stToolbar"], .stMain {
        background-color: #ffffff !important;
    }
    html, body, [class*="css"], .stMarkdown, p, span, label, li {
        color: #000000 !important;
        font-family: 'HanziPen SC', '翩翩體', 'PingFang TC', 'Heiti TC', 'Microsoft JhengHei', sans-serif !important;
    }

    /* 雙模適配 */
    [data-testid="stAppViewBlockContainer"] { padding: 1.5rem 1rem !important; }
    h1 { font-size: calc(1.5rem + 1.2vw) !important; text-align: center; }
    h3 { font-size: calc(1.1rem + 0.5vw) !important; }

    /* 下拉選單黑底修正 */
    div[data-baseweb="popover"], div[data-baseweb="listbox"], ul[role="listbox"], li[role="option"] {
        background-color: #ffffff !important; color: #000000 !important;
    }
    li[role="option"] div, li[role="option"] span {
        color: #000000 !important; background-color: #ffffff !important;
    }

    /* 組件鎖定 */
    div[data-testid="stTextInput"] input, div[data-baseweb="select"], div[data-baseweb="select"] > div {
        background-color: #ffffff !important; color: #000000 !important;
        -webkit-text-fill-color: #000000 !important; border: 2px solid #000000 !important;
    }

    /* 拍照截圖區 */
    [data-testid="stFileUploader"] section { background-color: #ffffff !important; border: 2px dashed #000000 !important; }
    [data-testid="stFileUploader"] button { background-color: #ffffff !important; color: #000000 !important; border: 1px solid #000000 !important; }
    [data-testid="stFileUploader"] button div span { font-size: 0 !important; }
    [data-testid="stFileUploader"] button div span::before { content: "瀏覽檔案" !important; font-size: 1rem !important; color: #000000 !important; }

    /* 地科專屬紫色導覽框 */
    .guide-box {
        background-color: #f3e5f5 !important; color: #000000 !important;
        padding: 15px; border-radius: 12px; border: 2px solid #9c27b0; margin-bottom: 20px;
    }

    /* 按鈕行動優化 (星艦靛藍風格) */
    div.stButton > button {
        background-color: #e8eaf6 !important; color: #000000 !important;
        border: 2px solid #3f51b5 !important; border-radius: 12px !important;
        width: 100% !important; height: 3.5rem !important; font-weight: bold !important;
    }

    .katex { color: #000000 !important; }
    @media (prefers-color-scheme: dark) {
        .stApp, div[data-testid="stTextInput"] input, section[data-testid="stFileUploader"], [data-testid="stFileUploader"] button, div[data-baseweb="popover"] {
            background-color: #ffffff !important; color: #000000 !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 🎙️ 2. 核心助教語音 (iPad 專用 Base64 強效封裝方案)
# ==========================================
async def generate_voice_base64(text):
    # 清除 Markdown 與特殊符號，確保只唸中文字與標點
    clean_text = re.sub(r'[^\w\u4e00-\u9fff\d，。！？「」、：]', '', text)
    communicate = edge_tts.Communicate(clean_text, "zh-TW-HsiaoChenNeural", rate="-2%")
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    b64 = base64.b64encode(audio_data).decode()
    return f'<audio controls autoplay style="width:100%"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'

# ==========================================
# 🖼️ 3. 雲端截圖功能
# ==========================================
def get_pdf_page_image(pdf_path, page_index):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_index)
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
    img_data = pix.tobytes("png")
    doc.close()
    return img_data

# ==========================================
# 📚 4. 地科 23 頁標題 (完整保留)
# ==========================================
page_titles = {
    1: "1. 地下水與流轉律法", 2: "2. 侵蝕、搬運與沉積", 3: "3. 三大岩石與礦物硬度",
    4: "4. 褶皺與斷層的崩裂", 5: "5. 地震波、規模與震度", 6: "6. 板塊漂移與擴張",
    7: "7. 聚合與張裂碰撞", 8: "8. 台灣板塊夾擊現況", 9: "9. 地層序列與切割律",
    10: "10. 化石與地質年代", 11: "11. 星球自轉與晝夜輪迴", 12: "12. 四季更迭與太陽軌跡",
    13: "13. 月相盈虧與日地月位面", 14: "14. 潮汐漲落與 50 分鐘宿命", 15: "15. 日食、月食與食之重合",
    16: "16. 大氣垂直構造", 17: "17. 氣壓與等壓線風之路徑", 18: "18. 相對溼度與雲端召喚",
    19: "19. 冷暖鋒面的戰場", 20: "20. 台灣季風與地形效應", 21: "21. 颱風螺旋與毀滅禁咒",
    22: "22. 全球暖化溫室囚籠", 23: "23. 臭氧漏洞與守護層崩解"
}

if 'audio_html' not in st.session_state: st.session_state.audio_html = None
if 'qa_audio_html' not in st.session_state: st.session_state.qa_audio_html = None

# ==========================================
# 🔑 5. 核心 API 通行證指南
# ==========================================
st.title("🚀 地科 AI 星艦導航室 (馬斯克助教版)")
st.markdown("""
<div class="guide-box">
    <b>📖 星艦快速通行指南：</b><br>
    1. 前往 <a href="https://aistudio.google.com/app/apikey" target="_blank">Google AI Studio</a> 並登入。<br>
    2. 點擊 <b>Create API key</b>，<b>務必勾選兩次同意條款</b>。<br>
    3. 貼回下方「通行證」欄位按 Enter 啟動馬斯克。
</div>
""", unsafe_allow_html=True)

user_key = st.text_input("🔑 通行證輸入區：", type="password")
st.divider()

# ==========================================
# 💬 6. 提問區
# ==========================================
st.subheader("💬 星球數據諮詢：拍照或打字提問")
col_q, col_up = st.columns([1, 1])
with col_q: student_q = st.text_input("打字提問星球真理：", placeholder="例如：為什麼台灣地震這麼多？")
with col_up: uploaded_file = st.file_uploader("拍照詢問馬斯克助教：", type=["jpg", "png", "jpeg"])

if (student_q or uploaded_file) and user_key:
    with st.spinner("火箭正在填充燃料，準備進入同步軌道處理數據..."):
        try:
            genai.configure(api_key=user_key)
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            
            prompt_qa = f"""{SYSTEM_PROMPT_TEMPLATE}
            
            這是學生的提問內容，請依照上述【四段式產出】與【雙軌協議】為他解答：
            學生的問題：{student_q}
            """
            
            parts = [prompt_qa]
            if uploaded_file: parts.append(Image.open(uploaded_file))
            res = model.generate_content(parts)
            
            full_qa = res.text
            display_qa = full_qa.split("【聽覺劇本】")[0].replace("【視覺內容】", "").strip()
            voice_qa = full_qa.split("【聽覺劇本】")[-1].strip() if "【聽覺劇本】" in full_qa else display_qa
            
            st.info(f"💡 馬斯克解答：\n\n{display_qa}")
            st.session_state.qa_audio_html = asyncio.run(generate_voice_base64(voice_qa))
        except Exception as e: st.error(f"數據分析失敗：{e}")

if st.session_state.qa_audio_html:
    st.markdown(st.session_state.qa_audio_html, unsafe_allow_html=True)

st.divider()

# ==========================================
# 📖 7. 選單與核心導航
# ==========================================
st.subheader("📖 啟動導航：選擇星系數據")
parts_list = ["【一：地表與地層律法】", "【二：板塊與構造契約】", "【三：天文與引力律法】", "【四：大氣與星球命運】"]
part_choice = st.selectbox("第一步：選擇大章節區域", parts_list)

if "一" in part_choice: r = range(1, 8)
elif "二" in part_choice: r = range(8, 15)
elif "三" in part_choice: r = range(15, 20)
else: r = range(20, 24)

options = [f"第 {p} 頁：{page_titles.get(p, '單元詳解')}" for p in r]
selected_page_str = st.selectbox("第二步：精確單元名稱 (不跳頁)", options)
target_page = int(re.search(r"第 (\d+) 頁", selected_page_str).group(1))

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
                
                # 注入目標頁碼與核心 Prompt
                final_prompt = SYSTEM_PROMPT_TEMPLATE.format(target_page=target_page)
                
                res = model.generate_content([file_obj, final_prompt])
                full_lecture = res.text
                
                # 雙軌切割
                display_lecture = full_lecture.split("【聽覺劇本】")[0].replace("【視覺內容】", "").strip()
                voice_lecture = full_lecture.split("【聽覺劇本】")[-1].strip() if "【聽覺劇本】" in full_lecture else display_lecture
                
                st.markdown(display_lecture)
                st.session_state.audio_html = asyncio.run(generate_voice_base64(voice_lecture))
                st.balloons()
            except Exception as e: st.error(f"導航失敗：{e}")

# ==========================================
# 🔊 8. 音訊播放區
# ==========================================
if st.session_state.audio_html:
    st.markdown("---")
    st.info("🔊 **星艦提醒**：請點擊下方播放鈕聽取繁中導航語音。")
    st.markdown(st.session_state.audio_html, unsafe_allow_html=True)
