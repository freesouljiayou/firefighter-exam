import streamlit as st
import json
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image 

# ==========================================
# 0. 網頁基礎設定
# ==========================================
try:
    icon_image = Image.open("logo.png") 
    st.set_page_config(page_title="升等考 刑法與消防法規", page_icon=icon_image, layout="wide")
except:
    st.set_page_config(page_title="升等考 刑法與消防法規", page_icon="🚒", layout="wide")

# ==========================================
# 1. Google Sheets 資料庫功能
# ==========================================
def get_user_data(username):
    """從 Google Sheet 讀取該使用者的資料"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl=0)
        
        expected_cols = ['Username', 'Favorites', 'Mistakes']
        if df.empty or not all(col in df.columns for col in expected_cols):
            df = pd.DataFrame(columns=expected_cols)

        user_row = df[df['Username'] == username]
        
        if not user_row.empty:
            fav_str = str(user_row.iloc[0]['Favorites'])
            mis_str = str(user_row.iloc[0]['Mistakes'])
            
            fav_set = set(json.loads(fav_str)) if fav_str and fav_str != 'nan' else set()
            mis_set = set(json.loads(mis_str)) if mis_str and mis_str != 'nan' else set()
            return fav_set, mis_set
        else:
            return set(), set()
    except Exception as e:
        st.error(f"連線讀取失敗：{e}")
        return set(), set()

def save_user_data(username, fav_set, mis_set):
    """將資料寫回 Google Sheet"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl=0)
        
        fav_json = json.dumps(list(fav_set))
        mis_json = json.dumps(list(mis_set))
        
        if username in df['Username'].values:
            df.loc[df['Username'] == username, 'Favorites'] = fav_json
            df.loc[df['Username'] == username, 'Mistakes'] = mis_json
        else:
            new_row = pd.DataFrame({
                'Username': [username], 
                'Favorites': [fav_json], 
                'Mistakes': [mis_json]
            })
            df = pd.concat([df, new_row], ignore_index=True)
            
        conn.update(data=df)
        
    except Exception as e:
        st.warning(f"自動存檔失敗：{e}")

# ==========================================
# 2. 登入驗證功能
# ==========================================
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # ✅ 修改需求 1：更改標題名稱
        st.header("🔒 升等考 刑法與消防法規 - 雲端版")
        
        try:
            user_list = list(st.secrets["passwords"].keys())
        except:
            st.error("尚未設定 Secrets，請檢查 .streamlit/secrets.toml")
            st.stop()

        selected_user = st.selectbox("請選擇登入人員", user_list)
        password_input = st.text_input("請輸入密碼", type="password")
        
        if st.button("登入"):
            correct_password = st.secrets["passwords"][selected_user]
            if password_input == correct_password:
                st.session_state["password_correct"] = True
                st.session_state["username"] = selected_user
                
                with st.spinner("☁️ 正在從雲端下載您的進度..."):
                    f_data, m_data = get_user_data(selected_user)
                    st.session_state['favorites'] = f_data
                    st.session_state['mistakes'] = m_data
                
                st.rerun()
            else:
                st.error(f"❌ 密碼錯誤")
    return False

if not check_password():
    st.stop()

# ==========================================
# 3. 題庫主程式
# ==========================================

if 'favorites' not in st.session_state:
    st.session_state['favorites'] = set()
if 'mistakes' not in st.session_state:
    st.session_state['mistakes'] = set()

@st.cache_data
def load_questions():
    with open('questions.json', 'r', encoding='utf-8') as f:
        return json.load(f)

try:
    all_questions = load_questions()
except FileNotFoundError:
    st.error("❌ 找不到 questions.json 檔案！")
    st.stop()

# --- 側邊欄 ---
st.sidebar.header(f"👤 {st.session_state['username']} 的戰情室")

if st.sidebar.button("💾 手動雲端存檔"):
    save_user_data(st.session_state['username'], st.session_state['favorites'], st.session_state['mistakes'])
    st.sidebar.success("✅ 已上傳雲端！")

keyword = st.sidebar.text_input("🔍 搜尋關鍵字")
st.sidebar.markdown("---")

# ==================================================
# ✅ 修改需求 2：解決頁面跳動的核心邏輯
# ==================================================

# 1. 定義固定的「內部代碼」 (這些是電腦看的，永遠不會變)
MODE_NORMAL = "normal"
MODE_FAV = "fav"
MODE_MIS = "mis"

# 2. 定義「翻譯機」函數 (負責把代碼變成我們要的文字+數字)
def format_mode_option(option_key):
    if option_key == MODE_NORMAL:
        return "一般刷題"
    elif option_key == MODE_FAV:
        return f"⭐ 題目收藏 ({len(st.session_state['favorites'])})"
    elif option_key == MODE_MIS:
        return f"❌ 錯題複習 ({len(st.session_state['mistakes'])})"
    return option_key

# 3. 建立 Radio 按鈕
# 注意：options 這裡放的是固定的代碼 [MODE_NORMAL, MODE_FAV, MODE_MIS]
# format_func 負責顯示文字，key 負責鎖定狀態
# ==================================================
# 修正版 Radio 按鈕邏輯 (解決跳頁問題)
# ==================================================

# 1. 確保 session_state 中有一個獨立變數來記錄當前模式
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = MODE_NORMAL

# 2. 定義 Callback：當使用者「手動」點擊 Radio 時，更新變數
def on_mode_change():
    st.session_state.view_mode = st.session_state.mode_selector_ui

# 3. 計算目前的 index
# 這是關鍵！即使文字標籤變了，只要 index 指向同一個位置，它就不會跳掉
options = [MODE_NORMAL, MODE_FAV, MODE_MIS]
try:
    current_index = options.index(st.session_state.view_mode)
except ValueError:
    current_index = 0
    st.session_state.view_mode = MODE_NORMAL

# 4. 建立 Radio
# 注意：這裡的 key 改名為 _ui，只負責介面互動，邏輯判斷依賴 st.session_state.view_mode
mode = st.sidebar.radio(
    "模式", 
    options, 
    format_func=format_mode_option,
    index=current_index,          # <--- 強制鎖定位置
    key="mode_selector_ui",       # <--- UI 專用 key
    on_change=on_mode_change      # <--- 綁定更新事件
)

# 為了讓下方的過濾邏輯不用改，這裡確保 mode 變數與狀態同步
mode = st.session_state.view_mode

# 科目篩選
subject_list = list(set([q['subject'] for q in all_questions]))
selected_subject = st.sidebar.radio("科目", subject_list)

# 年份篩選
subject_data = [q for q in all_questions if q['subject'] == selected_subject]
years_available = sorted(list(set([q['year'] for q in subject_data])), reverse=True)
selected_years = [y for y in years_available if st.sidebar.checkbox(f"{y} 年", value=True)]

# 資料池篩選
current_pool = []
for q in all_questions:
    if q['subject'] != selected_subject: continue
    if keyword and keyword not in q['question']: continue
    
    # 使用固定代號來過濾
    if mode == MODE_FAV and q['id'] not in st.session_state['favorites']: continue
    if mode == MODE_MIS and q['id'] not in st.session_state['mistakes']: continue
    
    if q['year'] not in selected_years: continue
    current_pool.append(q)

# 分類篩選
cat_counts = {q['category']: 0 for q in subject_data}
for q in current_pool:
    cat_counts[q['category']] = cat_counts.get(q['category'], 0) + 1

categories = sorted(list(set([q['category'] for q in subject_data])))
categories.insert(0, "全部")

selected_category = st.sidebar.radio("領域", categories, format_func=lambda x: f"{x} ({cat_counts.get(x,0)})" if x != "全部" else f"全部 ({len(current_pool)})")

# 細項篩選
selected_sub_cat = "全部"
if selected_category != "全部":
    sub_pool = [q for q in current_pool if q['category'] == selected_category]
    sub_counts = {}
    for q in sub_pool:
        sub_counts[q['sub_category']] = sub_counts.get(q['sub_category'], 0) + 1
    
    base_sub_cats = sorted(list(set([q['sub_category'] for q in subject_data if q['category'] == selected_category])))
    base_sub_cats.insert(0, "全部")
    selected_sub_cat = st.sidebar.radio("細項", base_sub_cats, format_func=lambda x: f"{x} ({sub_counts.get(x,0)})" if x != "全部" else f"全部 ({len(sub_pool)})")

# 最終篩選
final_questions = [q for q in current_pool if (selected_category == "全部" or q['category'] == selected_category) and (selected_sub_cat == "全部" or q['sub_category'] == selected_sub_cat)]

# --- 主畫面 ---
st.title(f"🔥 {selected_subject} 刷題區")
st.write(f"題目數：{len(final_questions)}")
st.markdown("---")

if not final_questions:
    if mode == MODE_MIS:
        st.success("🎉 太棒了！目前的篩選範圍內沒有錯題！")
    elif mode == MODE_FAV:
        st.warning("⚠️ 你還沒有收藏任何題目喔！")
    else:
        st.warning("⚠️ 沒有符合條件的題目")

for q in final_questions:
    q_label = f"{q['year']}#{str(q['id'])[-2:]}"
    
    # 使用 container 包住每一題
    with st.container():
        col_star, col_q = st.columns([0.08, 0.92])
        
        with col_star:
            is_fav = q['id'] in st.session_state['favorites']
            btn_label = "⭐" if is_fav else "☆"
            if st.button(btn_label, key=f"fav_{q['id']}"):
                if is_fav:
                    st.session_state['favorites'].discard(q['id'])
                else:
                    st.session_state['favorites'].add(q['id'])
                
                # 更新雲端並重整頁面，因為有 key 鎖定，所以重整後會留在原模式
                save_user_data(st.session_state['username'], st.session_state['favorites'], st.session_state['mistakes'])
                st.rerun()

        with col_q:
            st.markdown(f"### **[{q_label}]** {q['question']}")
            user_answer = st.radio("選項", q['options'], key=f"q_{q['id']}", label_visibility="collapsed", index=None)
            
            if user_answer:
                ans_char = user_answer.replace("(", "").replace(")", "").replace(".", "").strip()[0]
                if ans_char == q['answer']:
                    st.success(f"✅ 正確！")
                    
                    # 如果是在「錯題模式」答對，移除該題並重整
                    if mode == MODE_MIS and q['id'] in st.session_state['mistakes']:
                        st.session_state['mistakes'].discard(q['id'])
                        save_user_data(st.session_state['username'], st.session_state['favorites'], st.session_state['mistakes'])
                        # 重整後，頁面會刷新，該題會消失，但模式依然是「錯題複習」
                        st.rerun()
                else:
                    st.error(f"❌ 錯誤，答案是 {q['answer']}")
                    if q['id'] not in st.session_state['mistakes']:
                        st.session_state['mistakes'].add(q['id'])
                        save_user_data(st.session_state['username'], st.session_state['favorites'], st.session_state['mistakes'])
                
                with st.expander("查看詳解"):
                    st.info(q['explanation'])
        st.markdown("---")