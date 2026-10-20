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
        background-color: #8b5cf6; color: white;
        padding: 4px 8px; border-radius: 6px;
        font-size: 0.8rem; font-weight: bold;
    }
    .ai-comment-box {
        background-color: #1e293b;
        color: #f8fafc;
        border-left: 6px solid #fbbf24;
        border-top: 1px solid #334155;
        border-right: 1px solid #334155;
        border-bottom: 1px solid #334155;
        padding: 16px;
        border-radius: 0 12px 12px 0;
        margin-top: 12px;
        font-size: 1rem;
        line-height: 1.6;
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
if "round" not in st.session_state: st.session_state.round = 1
if "score_p1" not in st.session_state: st.session_state.score_p1 = 0
if "score_p2" not in st.session_state: st.session_state.score_p2 = 0
if "cpu_term" not in st.session_state: st.session_state.cpu_term = ""

# --- 💡 AIによるCPU用語の自動生成（日本史・世界史・地理・倫理・政治経済） ---
def generate_kansho_cpu_term():
    prompt = """あなたは高校社会科（日本史・世界史・地理・倫理・政治経済）の出題者です。
高校レベルの重要かつ魅力的な社会科用語（日本史・世界史・地理・倫理・政治経済のいずれか）を1つだけ選んで、その用語の名前だけを答えてください。
説明や記号、前置きは一切不要で、用語名のみを出力してください。"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        term = response.text.strip().replace('「', '').replace('」', '').replace('【', '').replace('】', '')
        if term:
            return term
    except:
        pass
    
    fallback_topics = [
        "大化の改新", "サンフランシスコ平和条約", "三世一身の法", "加藤高明内閣", "墾田永年私財法", "陸奥宗光の条約改正",
        "ハンムラビ法典", "エンクロージャー", "カノッサの屈辱", "ザントホップの農法", "ミティレンの議論", "サラトガの戦い", 
        "ヴォルムス協約", "大憲章（マグナ・カルタ）", "アヴィニョン捕囚", "ナントの勅令", "ウェストファリア条約", "ロカルノ条約",
        "カルスト地形", "サンゴ礁の離水", "回帰線砂漠", "フィヨルドとエスカー", "アグロフォレストリー",
        "プロテスタントの倫理", "王陽明の知行合一", "ベンサムの最大多数の最大幸福", "ニーチェのルサンチマン", "カントの道徳律", "レヴィ＝ストロースの構造主義",
        "ブロック経済", "ロールズの正義論", "ワイマール憲法", "夜警国家と福祉国家", "コモンズの悲劇", "ペティ＝クラークの法則", "ブレトンウッズ体制"
    ]
    return random.choice(fallback_topics)

# --- 🎯 評価基準を改訂したAI審査員長（正当性・熱量・鑑賞眼を総合評価） ---
def judge_kansho_battle(term_a, reason_a, review_a, term_b, reason_b, review_b, name_a, name_b):
    prompt = f"""あなたは知性と熱血を兼ね備えたカリスマ社会科教師であり、俳句甲子園の審査員長です。
【歴史・社会科用語 鑑賞バトル】（お互いの用語をオープンにし、「選んだ理由・説明」と「相手の用語への鑑賞・分析」で競う形式）のジャッジを行います。

【プレイヤーA: {name_a}】
- 用語: {term_a}
- 選んだ理由・説明: {reason_a}
- 相手（{name_b}）の用語への鑑賞・ツッコミ: {review_a}

【プレイヤーB: {name_b}】
- 用語: {term_b}
- 選んだ理由・説明: {reason_b}
- 相手（{name_a}）の用語への鑑賞・ツッコミ: {review_b}

【判定基準（重要）】
※用語がマニアックかどうかは評価基準から除外してください。定番の用語であっても問題ありません。
以下の3点を総合的に審査して勝敗を決めてください：
1. **説明の正当性・的確性**: 用語に対する理解や歴史的・社会科的事実の説明が正しいか。
2. **熱量・プレゼン力**: 選んだ理由や主張に情熱、熱量、説得力があるか。
3. **鑑賞眼・分析力**: 相手の選んだ用語に対する鑑賞・ツッコミが、相手の意図や用語の背景を捉えていて鋭いか。

【出力形式】
勝者を判定し（"A" または "B"）、審判講評コメント（5行程度 / 120〜150文字前後）を作成してください。
※講評では、双方の熱量や正当性、鑑賞眼の良さに触れる熱血で説得力ある解説にしてください。

以下のJSON形式のみで出力してください（他のテキストやマークダウンは不要）：
{{
  "winner": "A" または "B",
  "comment": "5行程度の熱血かつ的確な審判講評コメント"
}}"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(text)
        return data["winner"], data["comment"]
    except Exception as e:
        return "A", f"用語説明の的確さと熱量が激突した名勝負！特に{term_a}に対する説得力溢れる情熱と鋭い鑑賞眼を見せた{name_a}の勝利だァーーッ！"

# ==========================================
# 画面ロジック
# ==========================================
st.title("🏛️ 社会科用語・鑑賞バトル（俳句甲子園風）")

# --- メニュー画面 ---
if st.session_state.page == "menu":
    st.session_state.player_name = st.text_input("あなたの名前", value=st.session_state.player_name)
    
    st.write("---")
    st.markdown("### 📜 ルール：鑑賞バトルとは？")
    st.caption("お互いの社会科用語がオープンになった状態で、①自分の用語の選定理由・熱量説明 と ②相手の用語への鑑賞（分析・ツッコミ）を記入し、正当性・熱量・鑑賞眼で総合勝負します！")
    
    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🌐 オンライン対戦（ルーム戦）", type="primary"):
            st.session_state.game_type = "online"
            st.session_state.page = "lobby"
            st.rerun()
    with col2:
        if st.button("🤖 鑑賞CPUと対戦する"):
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
            st.session_state.round = 1
            st.session_state.score_p1 = 0
            st.session_state.score_p2 = 0
            fb_put(f"rooms/{code}", {
                "host": st.session_state.player_name, "guest": "",
                "status": "waiting", "round": 1,
                "scoreP1": 0, "scoreP2": 0
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
                    st.session_state.round = data.get("round", 1)
                    st.session_state.score_p1 = 0
                    st.session_state.score_p2 = 0
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
    st.subheader("⚙️ 鑑賞バトル（3本勝負）開始")
    st.info("第1段階として、ラウンド開始時に社会科用語をそれぞれオープンします！")
    
    if st.button("3本勝負バトルスタート！", type="primary"):
        st.session_state.round = 1
        st.session_state.score_p1 = 0
        st.session_state.score_p2 = 0
        with st.spinner("🤖 AIが第一試合の用語を選定中..."):
            st.session_state.cpu_term = generate_kansho_cpu_term()
        
        if st.session_state.game_type == "online" and st.session_state.is_host:
            fb_patch(f"rooms/{st.session_state.room_code}", {
                "status": "playing", "round": 1,
                "scoreP1": 0, "scoreP2": 0,
                "hostTerm": "", "hostReason": "", "hostReview": "",
                "guestTerm": "", "guestReason": "", "guestReview": "", "result": None
            })
        st.session_state.page = "input"
        st.rerun()

# --- 入力画面（鑑賞バトルの核心） ---
elif st.session_state.page == "input":
    st.subheader(f"⚔️ 第 {st.session_state.round} ラウンド / 全3戦")
    st.write(f"現在のスコア: あなた **{st.session_state.score_p1}** - **{st.session_state.score_p2}** 相手/CPU")
    
    if st.session_state.game_type == "cpu":
        st.markdown(f"<div class='battle-card'><span class='mode-badge'>相手（CPU）のチョイス用語</span><div class='term-title'>{st.session_state.cpu_term}</div></div>", unsafe_allow_html=True)

    with st.form("kansho_form"):
        my_term = st.text_input("① あなたが勝負に出す社会科用語")
        my_reason = st.text_area("② なぜこの用語を選んだか？（用語の正しい説明＆熱量アピール）")
        
        target_name = "相手（CPU）" if st.session_state.game_type == "cpu" else "対戦相手"
        my_review = st.text_area(f"③ 【鑑賞】{target_name}が選んだ用語に対する分析・洞察・ツッコミ")
        
        submit = st.form_submit_button("🔥 熱量と鑑賞文を提出して判定へ！", type="primary")
        
        if submit:
            if not my_term.strip() or not my_reason.strip() or not my_review.strip():
                st.error("①用語、②理由・熱量説明、③相手への鑑賞のすべてを入力してください！")
            else:
                if st.session_state.game_type == "online":
                    role = "host" if st.session_state.is_host else "guest"
                    fb_patch(f"rooms/{st.session_state.room_code}", {
                        f"{role}Term": my_term, f"{role}Reason": my_reason, f"{role}Review": my_review
                    })
                    st.session_state.page = "wait_result"
                    st.rerun()
                else:
                    with st.spinner("🤖 AI審査員長が双方の正当性・熱量・鑑賞眼を審議中..."):
                        cpu_reason = f"{st.session_state.cpu_term}は時代の構造や社会システムを根底から方向づけた不可欠な用語だ。歴史的ファクトとしてもその重要性は揺るぎない！"
                        cpu_review = f"プレイヤーの選んだ『{my_term}』の正確な理解と情熱は評価できる。しかし、相手の意図を見ぬく鑑賞の深さでは我が{st.session_state.cpu_term}へのアプローチも負けてはいない！"
                        
                        winner, comment = judge_kansho_battle(
                            my_term, my_reason, my_review,
                            st.session_state.cpu_term, cpu_reason, cpu_review,
                            st.session_state.player_name, "鑑賞CPU"
                        )
                    
                    if winner == "A": st.session_state.score_p1 += 1
                    else: st.session_state.score_p2 += 1
                        
                    st.session_state.result = {
                        "termA": my_term, "reasonA": my_reason, "reviewA": my_review,
                        "termB": st.session_state.cpu_term, "reasonB": cpu_reason, "reviewB": cpu_review,
                        "winner": winner, "comment": comment,
                        "nameA": st.session_state.player_name, "nameB": "鑑賞CPU",
                        "scoreP1": st.session_state.score_p1, "scoreP2": st.session_state.score_p2
                    }
                    st.session_state.page = "result"
                    st.rerun()

# --- 結果待機画面（オンライン） ---
elif st.session_state.page == "wait_result":
    st.info("対戦相手の提出とAI鑑賞審判の判定を待っています...")
    time.sleep(2)
    data = fb_get(f"rooms/{st.session_state.room_code}")
    
    if data:
        if st.session_state.is_host and data.get("hostTerm") and data.get("guestTerm") and not data.get("result"):
            winner, comment = judge_kansho_battle(
                data["hostTerm"], data["hostReason"], data["hostReview"],
                data["guestTerm"], data["guestReason"], data["guestReview"],
                data["host"], data["guest"]
            )
            
            p1_score = data.get("scoreP1", 0)
            p2_score = data.get("scoreP2", 0)
            if winner == "A": p1_score += 1
            else: p2_score += 1
            
            res_data = {
                "termA": data["hostTerm"], "reasonA": data["hostReason"], "reviewA": data["hostReview"],
                "termB": data["guestTerm"], "reasonB": data["guestReason"], "reviewB": data["guestReview"],
                "winner": winner, "comment": comment,
                "nameA": data["host"], "nameB": data["guest"],
                "scoreP1": p1_score, "scoreP2": p2_score
            }
            fb_patch(f"rooms/{st.session_state.room_code}", {"result": res_data, "scoreP1": p1_score, "scoreP2": p2_score})
        
        if data.get("result"):
            res = data["result"]
            st.session_state.result = res
            st.session_state.score_p1 = res["scoreP1"]
            st.session_state.score_p2 = res["scoreP2"]
            st.session_state.page = "result"
            st.rerun()
        else:
            st.rerun()

# --- 結果画面 ---
elif st.session_state.page == "result":
    res = st.session_state.result
    st.subheader(f"🏆 第 {st.session_state.round} ラウンド 判定結果")
    
    winner_name = res["nameA"] if res["winner"] == "A" else res["nameB"]
    st.success(f"このラウンドの勝者：**{winner_name}** 👑")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**【{res['nameA']}】**")
        st.info(f"用語: **{res['termA']}**\n\n📌 **理由・説明**: {res['reasonA']}\n\n💬 **鑑賞**: {res['reviewA']}")
    with col2:
        st.markdown(f"**【{res['nameB']}】**")
        st.info(f"用語: **{res['termB']}**\n\n📌 **理由・説明**: {res['reasonB']}\n\n💬 **鑑賞**: {res['reviewB']}")
        
    st.markdown("### 🤖 審査員長AIの熱血講評")
    st.markdown(f"<div class='ai-comment-box'>{res['comment']}</div>", unsafe_allow_html=True)
    
    st.write("---")
    st.write(f"現在のトータルスコア: **{res['nameA']}** `【 {res['scoreP1']}勝 】` - `【 {res['scoreP2']}勝 】` **{res['nameB']}**")
    
    if st.session_state.round < 3:
        if st.button("次ラウンドへ進む ➔", type="primary"):
            st.session_state.round += 1
            with st.spinner("🤖 次ラウンドの用語を選定中..."):
                st.session_state.cpu_term = generate_kansho_cpu_term()
            if st.session_state.game_type == "online" and st.session_state.is_host:
                fb_patch(f"rooms/{st.session_state.room_code}", {
                    "round": st.session_state.round,
                    "hostTerm": "", "hostReason": "", "hostReview": "",
                    "guestTerm": "", "guestReason": "", "guestReview": "", "result": None
                })
            st.session_state.page = "input"
            st.rerun()
    else:
        if st.button("🏆 最終勝者を決定する！", type="primary"):
            st.session_state.page = "final"
            st.rerun()

# --- 最終結果画面 ---
elif st.session_state.page == "final":
    st.balloons()
    st.subheader("🎉 鑑賞バトル 最終結果発表！ 🎉")
    
    p1 = st.session_state.score_p1
    p2 = st.session_state.score_p2
    
    if p1 > p2:
        st.header(f"👑 総合優勝：{st.session_state.player_name} ！！")
        st.caption("的確な用語説明の正当性、あふれ出る熱量、そして相手を見抜く見事な鑑賞眼で勝利を掴み取りました！")
    elif p2 > p1:
        st.header("💀 敗北……勝者：対戦相手 / CPU")
        st.caption("相手の熱量と鋭い鑑賞眼の前に惜敗！次はさらに熱い想いと論理でリベンジだ！")
    else:
        st.header("🤝 決着つかずのドロー！")
        st.caption("互いの知識の正当性と熱量が完全に拮抗した、まさに歴史に残る素晴らしい名勝負でした！")
        
    st.metric(label="最終勝利数", value=f"{p1} 勝 - {p2} 勝")
    
    st.write("---")
    if st.button("タイトルに戻る"):
        st.session_state.page = "menu"
        st.rerun()
