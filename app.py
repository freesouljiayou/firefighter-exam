import streamlit as st
import json

# ==========================================
# 0. 網頁基礎設定 (必須放在第一行)
# ==========================================
st.set_page_config(page_title="升等考 刑法與消防法規", layout="wide")

# ==========================================
# 1. 登入驗證功能 (升級：選單式登入)
# ==========================================
def check_password():
    """檢查帳號與密碼是否正確"""
    
    # 如果已經登入成功，直接回傳 True
    if st.session_state.get("password_correct", False):
        return True

    # --- 登入畫面設計 ---
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.header("🔒 消防升等考題庫 - 系統登入")
        
        # 1. 自動從 secrets.toml 讀取所有使用者名稱
        # 這樣您以後在 secrets 增加人，這裡會自動出現，不用改程式
        user_list = list(st.secrets["passwords"].keys())
        
        # 2. 讓使用者「點選」帳號 (方框選單)
        selected_user = st.selectbox("請選擇登入人員", user_list)
        
        # 3. 輸入密碼
        password_input = st.text_input("請輸入密碼", type="password")
        
        if st.button("登入"):
            # 檢查：該帳號的密碼是否正確
            correct_password = st.secrets["passwords"][selected_user]
            
            if password_input == correct_password:
                st.session_state["password_correct"] = True
                st.rerun() # 登入成功，刷新頁面
            else:
                st.error(f"❌ {selected_user} 的密碼錯誤，請再試一次")
                
    return False

# --- 啟動守門員 ---
if not check_password():
    st.stop()

# ==========================================
# 2. 以下是您原本的題庫程式碼 (完全保留)
# ==========================================

# 初始化暫存空間
if 'favorites' not in st.session_state:
    st.session_state['favorites'] = set()
if 'mistakes' not in st.session_state:
    st.session_state['mistakes'] = set()

# 讀取資料函數
@st.cache_data
def load_questions():
    with open('questions.json', 'r', encoding='utf-8') as f:
        return json.load(f)

try:
    all_questions = load_questions()
except FileNotFoundError:
    st.error("❌ 找不到 questions.json 檔案！")
    st.stop()

# --- 側邊欄：控制中心 ---
st.sidebar.header("🚒 消防戰情室")

# A. 關鍵字搜尋
keyword = st.sidebar.text_input("🔍 搜尋題目關鍵字", placeholder="例如：救護、罰鍰...")
st.sidebar.markdown("---")

# B. 模式選擇
st.sidebar.subheader("1. 練習模式")
mode = st.sidebar.radio(
    "請選擇模式", 
    ["一般刷題", "⭐ 題目收藏", "❌ 錯題複習"],
    label_visibility="collapsed"
)

# 顯示模式統計
if mode == "⭐ 題目收藏":
    st.sidebar.caption(f"目前收藏：{len(st.session_state['favorites'])} 題")
elif mode == "❌ 錯題複習":
    st.sidebar.caption(f"累積錯題：{len(st.session_state['mistakes'])} 題")

st.sidebar.markdown("---")

# C. 科目選擇
st.sidebar.subheader("2. 選擇考科")
subject_list = list(set([q['subject'] for q in all_questions]))
if subject_list:
    selected_subject = st.sidebar.radio("科目", subject_list)
else:
    st.sidebar.error("資料庫無資料")
    st.stop()

# D. 年份篩選
st.sidebar.subheader("3. 年份篩選")
subject_data = [q for q in all_questions if q['subject'] == selected_subject]
years_available = list(set([q['year'] for q in subject_data]))
years_available.sort(reverse=True)

selected_years = []
for y in years_available:
    if st.sidebar.checkbox(f"{y} 年", value=True):
        selected_years.append(y)
st.sidebar.markdown("---")

# [核心邏輯] 預先篩選資料
current_pool = []
for q in all_questions:
    if q['subject'] != selected_subject: continue
    if keyword and keyword not in q['question']: continue
    if mode == "⭐ 題目收藏" and q['id'] not in st.session_state['favorites']: continue
    if mode == "❌ 錯題複習" and q['id'] not in st.session_state['mistakes']: continue
    if q['year'] not in selected_years: continue
    current_pool.append(q)

# E. 法規分類 (含數量統計)
st.sidebar.subheader("4. 法規分類")

cat_counts = {}
for q in current_pool:
    c = q['category']
    cat_counts[c] = cat_counts.get(c, 0) + 1

categories = list(set([q['category'] for q in subject_data]))
categories.sort()
categories.insert(0, "全部")

def format_category_label(option):
    if option == "全部":
        return f"全部 ({len(current_pool)})"
    count = cat_counts.get(option, 0)
    return f"{option} ({count})"

selected_category = st.sidebar.radio(
    "選擇領域", 
    categories, 
    format_func=format_category_label
)

selected_sub_cat = "全部"
if selected_category != "全部":
    st.sidebar.markdown("⬇️ **細項法規**")
    
    sub_pool = [q for q in current_pool if q['category'] == selected_category]
    sub_counts = {}
    for q in sub_pool:
        s = q['sub_category']
        sub_counts[s] = sub_counts.get(s, 0) + 1
        
    base_sub_cats = list(set([q['sub_category'] for q in subject_data if q['category'] == selected_category]))
    base_sub_cats.sort()
    base_sub_cats.insert(0, "全部")
    
    def format_sub_label(option):
        if option == "全部":
            return f"全部 ({len(sub_pool)})"
        count = sub_counts.get(option, 0)
        return f"{option} ({count})"

    selected_sub_cat = st.sidebar.radio(
        "細項", 
        base_sub_cats, 
        format_func=format_sub_label
    )

final_questions = []
for q in current_pool:
    if selected_category != "全部" and q['category'] != selected_category: continue
    if selected_sub_cat != "全部" and q['sub_category'] != selected_sub_cat: continue
    final_questions.append(q)

# --- 主畫面顯示 ---
st.title(f"🔥 {selected_subject} 刷題區")

col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    if mode == "❌ 錯題複習":
        st.info("💡 提示：在錯題模式中，只要「答對」題目，該題就會自動從錯題本中移除！")
    else:
        st.caption(f"目前顯示：{selected_category} > {selected_sub_cat}")

with col_head2:
    st.metric("題目數", f"{len(final_questions)}")

st.markdown("---")

if len(final_questions) == 0:
    if mode == "❌ 錯題複習":
        st.success("🎉 太棒了！目前的篩選範圍內沒有錯題！")
    elif mode == "⭐ 題目收藏":
        st.warning("⚠️ 你還沒有收藏任何題目喔！")
    else:
        st.warning("⚠️ 沒有符合條件的題目")

for index, q in enumerate(final_questions):
    try:
        q_num = str(q['id'])[-2:]
        q_label = f"{q['year']}#{q_num}"
    except:
        q_label = str(q['id'])

    col_star, col_question = st.columns([0.08, 0.92])
    
    with col_star:
        is_fav = q['id'] in st.session_state['favorites']
        btn_label = "⭐" if is_fav else "☆"
        
        if st.button(btn_label, key=f"fav_btn_{q['id']}"):
            if is_fav:
                st.session_state['favorites'].discard(q['id'])
                st.rerun()
            else:
                st.session_state['favorites'].add(q['id'])
                st.rerun()

    with col_question:
        st.markdown(f"### **[{q_label}]** {q['question']}")
        
        option_key = f"q_{q['id']}"
        user_answer = st.radio("請選擇：", q['options'], key=option_key, index=None, label_visibility="collapsed")
        
        if user_answer:
            correct_opt = q['answer']
            clean_user_opt = user_answer.replace("(", "").replace(")", "").replace(".", "").strip()[0]
            
            if clean_user_opt == correct_opt:
                st.success(f"✅ **正確！** 答案就是 {user_answer}")
                if mode == "❌ 錯題複習" and q['id'] in st.session_state['mistakes']:
                    st.session_state['mistakes'].discard(q['id'])
                    st.rerun() 
            else:
                st.error(f"❌ **錯誤！** 正確答案是：{correct_opt}")
                if q['id'] not in st.session_state['mistakes']:
                    st.session_state['mistakes'].add(q['id'])
            
            with st.expander("💡 查看詳細解析", expanded=True):
                st.info(q['explanation'])
                st.caption(f"法規出處：{q['sub_category']}")

    st.markdown("---")