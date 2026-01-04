import streamlit as st
import json
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 0. 網頁基礎設定
# ==========================================
st.set_page_config(page_title="升等考 刑法與消防法規", layout="wide")

# ==========================================
# 1. Google Sheets 資料庫功能 (核心新功能)
# ==========================================
def get_user_data(username):
    """從 Google Sheet 讀取該使用者的資料"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # 讀取全部資料，不快取 (確保拿到最新的)
        df = conn.read(ttl=0)
        
        # 確保必要的欄位存在，如果沒有就建立空的
        expected_cols = ['Username', 'Favorites', 'Mistakes']
        if df.empty or not all(col in df.columns for col in expected_cols):
            df = pd.DataFrame(columns=expected_cols)

        # 搜尋該使用者的資料
        user_row = df[df['Username'] == username]
        
        if not user_row.empty:
            # 如果有資料，解析 JSON 字串變回集合 (Set)
            fav_str = str(user_row.iloc[0]['Favorites'])
            mis_str = str(user_row.iloc[0]['Mistakes'])
            
            # 處理空值或字串轉換
            fav_set = set(json.loads(fav_str)) if fav_str and fav_str != 'nan' else set()
            mis_set = set(json.loads(mis_str)) if mis_str and mis_str != 'nan' else set()
            return fav_set, mis_set
        else:
            # 如果是新使用者，回傳空的集合
            return set(), set()
    except Exception as e:
        st.error(f"連線讀取失敗：{e}")
        return set(), set()

def save_user_data(username, fav_set, mis_set):
    """將資料寫回 Google Sheet"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl=0)
        
        # 轉換集合為 JSON 字串以便儲存
        fav_json = json.dumps(list(fav_set))
        mis_json = json.dumps(list(mis_set))
        
        # 檢查使用者是否已在資料表中
        if username in df['Username'].values:
            # 更新現有資料
            df.loc[df['Username'] == username, 'Favorites'] = fav_json
            df.loc[df['Username'] == username, 'Mistakes'] = mis_json
        else:
            # 新增一筆資料
            new_row = pd.DataFrame({
                'Username': [username], 
                'Favorites': [fav_json], 
                'Mistakes': [mis_json]
            })
            df = pd.concat([df, new_row], ignore_index=True)
            
        # 寫回 Google Sheet
        conn.update(data=df)
        
    except Exception as e:
        st.warning(f"自動存檔失敗 (請檢查網路或權限)：{e}")

# ==========================================
# 2. 登入驗證功能
# ==========================================
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.header("🔒 消防升等考題庫 - 雲端版")
        
        user_list = list(st.secrets["passwords"].keys())
        selected_user = st.selectbox("請選擇登入人員", user_list)
        password_input = st.text_input("請輸入密碼", type="password")
        
        if st.button("登入"):
            correct_password = st.secrets["passwords"][selected_user]
            if password_input == correct_password:
                st.session_state["password_correct"] = True
                st.session_state["username"] = selected_user # 記住是誰登入的
                
                # --- 登入成功時，立刻從雲端載入進度 ---
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

# 確保 session_state 初始化
if 'favorites' not in st.session_state:
    st.session_state['favorites'] = set()
if 'mistakes' not in st.session_state:
    st.session_state['mistakes'] = set()

# 讀取題目 JSON
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

# 手動存檔按鈕 (怕自動存檔沒跑)
if st.sidebar.button("💾 手動雲端存檔"):
    save_user_data(st.session_state['username'], st.session_state['favorites'], st.session_state['mistakes'])
    st.sidebar.success("✅ 已上傳雲端！")

keyword = st.sidebar.text_input("🔍 搜尋關鍵字")
st.sidebar.markdown("---")

mode = st.sidebar.radio("模式", ["一般刷題", "⭐ 題目收藏", "❌ 錯題複習"])

if mode == "⭐ 題目收藏":
    st.sidebar.caption(f"收藏數：{len(st.session_state['favorites'])}")
elif mode == "❌ 錯題複習":
    st.sidebar.caption(f"錯題數：{len(st.session_state['mistakes'])}")

st.sidebar.markdown("---")

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
    if mode == "⭐ 題目收藏" and q['id'] not in st.session_state['favorites']: continue
    if mode == "❌ 錯題複習" and q['id'] not in st.session_state['mistakes']: continue
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
    st.warning("⚠️ 沒有符合條件的題目")

for q in final_questions:
    q_label = f"{q['year']}#{str(q['id'])[-2:]}"
    col_star, col_q = st.columns([0.08, 0.92])
    
    with col_star:
        is_fav = q['id'] in st.session_state['favorites']
        if st.button("⭐" if is_fav else "☆", key=f"fav_{q['id']}"):
            if is_fav:
                st.session_state['favorites'].discard(q['id'])
            else:
                st.session_state['favorites'].add(q['id'])
            # 觸發雲端存檔
            save_user_data(st.session_state['username'], st.session_state['favorites'], st.session_state['mistakes'])
            st.rerun()

    with col_q:
        st.markdown(f"### **[{q_label}]** {q['question']}")
        user_answer = st.radio("選項", q['options'], key=f"q_{q['id']}", label_visibility="collapsed", index=None)
        
        if user_answer:
            ans_char = user_answer.replace("(", "").replace(")", "").replace(".", "").strip()[0]
            if ans_char == q['answer']:
                st.success(f"✅ 正確！")
                if mode == "❌ 錯題複習" and q['id'] in st.session_state['mistakes']:
                    st.session_state['mistakes'].discard(q['id'])
                    save_user_data(st.session_state['username'], st.session_state['favorites'], st.session_state['mistakes'])
                    st.rerun()
            else:
                st.error(f"❌ 錯誤，答案是 {q['answer']}")
                if q['id'] not in st.session_state['mistakes']:
                    st.session_state['mistakes'].add(q['id'])
                    save_user_data(st.session_state['username'], st.session_state['favorites'], st.session_state['mistakes'])
            
            with st.expander("查看詳解"):
                st.info(q['explanation'])
    st.markdown("---")