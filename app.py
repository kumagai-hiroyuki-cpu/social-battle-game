import streamlit as st
import google.generativeai as genai
import requests
import json
import random
import time

# --- ページ基本設定 ---
st.set_page_config(
    page_title="社会科用語バトル (Soc-Battle)",
    page_icon="🏛️",
    layout="centered"
)

# --- カスタムCSS ---
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; }
    .battle-card {
        background-color: #1e293b;
        border: 2px solid #334155;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .term-title { color: #fbbf24; font-size: 1.25rem; font-weight: 900; }
    .mode-badge {
        background-color: #3b82f6; color: white;
        padding: 4px 8px; border-radius: 6px;
        font-size: 0.8rem; font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- Secrets からの設定読み込み ---
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")
FIREBASE_URL = st.secrets.get("FIREBASE_DATABASE_URL", "").rstrip("/")

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

# --- Firebase Realtime Database Helper ---
def fb_put(path, data):
    if not FIREBASE_URL: return
    try:
        requests.put(f"{FIREBASE_URL}/{path}.json", json=data, timeout=5)
    except Exception as e:
        st.error(f"Firebase通信エラー: {e}")

def fb_get(path):
    if not FIREBASE_URL: return None
    try:
        res = requests.get(f"{FIREBASE_URL}/{path}.json", timeout=5)
        return res.json()
    except:
        return None

def fb_patch(path, data):
    if not FIREBASE_URL: return
    try:
        requests.patch(f"{FIREBASE_URL}/{path}.json", json=data, timeout=5)
    except Exception as e:
        st.error(f"Firebase通信エラー: {e}")

# --- セッション状態の初期化 ---
if "page" not in st.session_state: st.session_state.page = "menu"
if "game_type" not in st.session_state: st.session_state.game_type = "cpu"
if "room_code" not in st.session_state: st.session_state.room_code = ""
if "is_host" not in st.session_state: st.session_state.is_host = False
if "player_name" not in st.session_state: st.session_state.player_name = "プレイヤー1"
if "game_mode" not in st.session_state: st.session_state.game_mode = "waza"
if "round" not in st.session_state: st.session_state.round = 1

MODES = {
    "waza": {"name": "⚡ 必殺技モード", "desc": "用語を必殺技風にアピール！決め台詞とカッコよさで勝負！", "label": "必殺技の効果・決め台詞"},
    "impact": {"name": "💥 インパクト部門", "desc": "歴史や社会へ与えた影響力＆マニアックなチョイスの妙で勝負！", "label": "社会・歴史への影響力＆選定理由"},
    "love": {"name": "❤️ 自由部門（用語愛）", "desc": "その用語がどれだけ好きか・推せるポイントを熱弁！", "label": "この用語への愛・推しポイント"}
}

CPU_DATA = {
    "waza": [{"t": "三世一身の法", "d": "開墾した土地の私有を三世代まで認め、意欲を爆発的にブーストする古代の錬金術！"}, {"t": "サンフランシスコ平和条約", "d": "主権を完全に取り戻す復活の聖別魔法陣！"}],
    "impact": [{"t": "カルスト地形", "d": "雨水の溶食作用で大地が削られ、独特の鍾乳洞を作り上げる地球の造形美！"}, {"t": "エンクロージャー", "d": "資本主義的農業を生み出し産業革命の労働力を作り出した原動力！"}],
    "love": [{"t": "シーラカンス", "d": "生きた化石と呼ばれる神秘的な姿！深海のロマンが詰まっていて最高！"}, {"t": "モールス信号", "d": "トトントンの音だけで世界中と意思疎通できるシンプルで美しすぎるロマン！"}]
}

def judge_with_gemini(term_a, desc_a, term_b, desc_b, mode_key, name_a, name_b):
    prompt = f"""あなたは中学・高校の社会科教師で、熱血なゲーム実況風の審判です。
「社会科用語バトル」（モード: {MODES[mode_key]['name']}）の判定を行ってください。

【プレイヤーA: {name_a}】
- 用語: {term_a}
- アピール: {desc_a}

【プレイヤーB: {name_b}】
- 用語: {term_b}
- アピール: {desc_b}

【判定基準】
1. 安直で超定番すぎる用語（明治維新、産業革命等）よりも、「その角度で来たか！」「通でマニアックなチョイスだ！」というセンス・知識を高く評価してください。
2. モードの趣旨（勢い・影響力・熱量）に合致しているか。
3. 勝者を判定してください（"A" または "B"）。

必ず以下のJSON形式のみで出力してください：
{{
  "winner": "A" または "B",
  "comment": "熱い勝因解説コメント（150文字程度）"
}}"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(text)
        return data["winner"], data["comment"]
    except Exception as e:
        return "A", f"マニアックな用語チョイスと熱い説得力により、{name_a}の勝利！"

# ==========================================
# 画面ロジック
# ==========================================
st.title("🏛️ 社会科用語バトル")

# --- メニュー画面 ---
if st.session_state.page == "menu":
    st.session_state.player_name = st.text_input("あなたの名前", value=st.session_state.player_name)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🌐 オンライン対戦（ルーム）", type="primary"):
            st.session_state.game_type = "online"
            st.session_state.page = "lobby"
            st.rerun()
    with col2:
        if st.button("🤖 CPUと対戦"):
            st.session_state.game_type = "cpu"
            st.session_state.page = "setup"
            st.rerun()

# --- ロビー画面 ---
elif st.session_state.page == "lobby":
    st.subheader("🌐 オンライン対戦ロビー")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏠 ルームを作成"):
            code = str(random.randint(1000, 9999))
            st.session_state.room_code = code
            st.session_state.is_host = True
            fb_put(f"rooms/{code}", {
                "host": st.session_state.player_name, "guest": "",
                "status": "waiting", "battleMode": "waza", "round": 1
            })
            st.session_state.page = "waiting"
            st.rerun()
    with col2:
        input_code = st.text_input("ルームコード(4桁)")
        if st.button("🚪 入室"):
            if input_code:
                data = fb_get(f"rooms/{input_code}")
                if data:
                    st.session_state.room_code = input_code
                    st.session_state.is_host = False
                    fb_patch(f"rooms/{input_code}", {"guest": st.session_state.player_name})
                    st.session_state.page = "setup"
                    st.rerun()
                else: st.error("ルームが見つかりません")

# --- 待機画面 ---
elif st.session_state.page == "waiting":
    st.subheader(f"🏠 ルームコード: {st.session_state.room_code}")
    st.info("対戦相手の入室を待っています...")
    time.sleep(2)
    data = fb_get(f"rooms/{st.session_state.room_code}")
    if data and data.get("guest"):
        st.success(f"{data['guest']} さんが参加しました！")
        st.session_state.page = "setup"
        st.rerun()
    else:
        st.rerun()

# --- ルール設定画面 ---
elif st.session_state.page == "setup":
    st.subheader("⚙️ バトル部門選択")
    selected_mode = st.radio("部門を選択", options=list(MODES.keys()), format_func=lambda x: MODES[x]["name"])
    st.caption(MODES[selected_mode]["desc"])
    
    if st.button("バトルスタート！", type="primary"):
        st.session_state.game_mode = selected_mode
        if st.session_state.game_type == "online" and st.session_state.is_host:
            fb_patch(f"rooms/{st.session_state.room_code}", {
                "status": "playing", "battleMode": selected_mode, "round": 1,
                "hostTerm": "", "hostDesc": "", "guestTerm": "", "guestDesc": ""
            })
        st.session_state.page = "input"
        st.rerun()

# --- 入力画面 ---
elif st.session_state.page == "input":
    st.subheader(f"⚔️ 第 {st.session_state.round} ラウンド ({MODES[st.session_state.game_mode]['name']})")
    
    with st.form("input_form"):
        term = st.text_input("社会科用語")
        desc = st.text_area(MODES[st.session_state.game_mode]["label"])
        submit = st.form_submit_button("提出して勝負！", type="primary")
        
        if submit and term and desc:
            if st.session_state.game_type == "online":
                role = "host" if st.session_state.is_host else "guest"
                fb_patch(f"rooms/{st.session_state.room_code}", {
                    f"{role}Term": term, f"{role}Desc": desc
                })
                st.session_state.page = "wait_result"
                st.rerun()
            else:
                cpu_choice = random.choice(CPU_DATA[st.session_state.game_mode])
                winner, comment = judge_with_gemini(
                    term, desc, cpu_choice["t"], cpu_choice["d"],
                    st.session_state.game_mode, st.session_state.player_name, "CPU"
                )
                st.session_state.result = {
                    "termA": term, "descA": desc, "termB": cpu_choice["t"], "descB": cpu_choice["d"],
                    "winner": "A" if winner == "A" else "B", "comment": comment,
                    "nameA": st.session_state.player_name, "nameB": "CPU"
                }
                st.session_state.page = "result"
                st.rerun()

# --- 結果待機画面（オンライン） ---
elif st.session_state.page == "wait_result":
    st.info("対戦相手の提出とAIジャッジを待っています...")
    time.sleep(2)
    data = fb_get(f"rooms/{st.session_state.room_code}")
    
    if data:
        # ホスト側がAI判定を実行
        if st.session_state.is_host and data.get("hostTerm") and data.get("guestTerm") and not data.get("result"):
            winner, comment = judge_with_gemini(
                data["hostTerm"], data["hostDesc"], data["guestTerm"], data["guestDesc"],
                data["battleMode"], data["host"], data["guest"]
            )
            res_data = {
                "termA": data["hostTerm"], "descA": data["hostDesc"],
                "termB": data["guestTerm"], "descB": data["guestDesc"],
                "winner": winner, "comment": comment,
                "nameA": data["host"], "nameB": data["guest"]
            }
            fb_patch(f"rooms/{st.session_state.room_code}", {"result": res_data})
        
        if data.get("result"):
            st.session_state.result = data["result"]
            st.session_state.page = "result"
            st.rerun()
        else:
            st.rerun()

# --- 結果画面 ---
elif st.session_state.page == "result":
    res = st.session_state.result
    st.subheader("🏆 判定結果")
    
    winner_name = res["nameA"] if res["winner"] == "A" else res["nameB"]
    st.success(f"勝者：**{winner_name}** 👑")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**【{res['nameA']}】**")
        st.info(f"**{res['termA']}**\n\n{res['descA']}")
    with col2:
        st.markdown(f"**【{res['nameB']}】**")
        st.info(f"**{res['termB']}**\n\n{res['descB']}")
        
    st.markdown("### 🤖 AI審判の評価コメント")
    st.write(res["comment"])
    
    if st.button("タイトルに戻る"):
        st.session_state.page = "menu"
        st.rerun()