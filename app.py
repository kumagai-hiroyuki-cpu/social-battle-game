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
if "cpu_difficulty" not in st.session_state: st.session_state.cpu_difficulty = "yukkuri"
if "room_code" not in st.session_state: st.session_state.room_code = ""
if "is_host" not in st.session_state: st.session_state.is_host = False
if "player_name" not in st.session_state: st.session_state.player_name = "プレイヤー1"
if "game_mode" not in st.session_state: st.session_state.game_mode = "waza"
if "round" not in st.session_state: st.session_state.round = 1
if "score_p1" not in st.session_state: st.session_state.score_p1 = 0
if "score_p2" not in st.session_state: st.session_state.score_p2 = 0

MODES = {
    "waza": {"name": "⚡ 必殺技モード", "desc": "用語を必殺技風にアピール！決め台詞とカッコよさ、技としての再現度で勝負！", "label": "必殺技の効果・決め台詞"},
    "impact": {"name": "💥 インパクト部門", "desc": "歴史や社会へ与えた激震・マニアックなチョイスの妙と論理的影響力で勝負！", "label": "社会・歴史へのインパクト＆選定理由"},
    "love": {"name": "❤️ 自由部門（用語愛）", "desc": "その用語がどれだけ好きか・推せるポイントを熱く偏愛的に語る！", "label": "この用語への愛・推しポイント"}
}

# --- ゆっくりモード用の多彩な固定マニアック用語データ ---
YUKKURI_DATA = {
    "waza": [
        {"t": "ハンムラビ法典", "d": "目には目、歯には歯を！容赦ない同害報復で社会の秩序を鉄槌の如く死守する古代の絶対シールド！"},
        {"t": "サラトガの戦い", "d": "独立軍がイギリス軍を初めて全面降伏させ、フランスを参戦に導いた歴史の形勢逆転グランドクロス！"},
        {"t": "三世一身の法", "d": "開墾した土地の私有を三世代まで認め、農民の開墾意欲を限界突破させる古代の錬金術！"},
        {"t": "サンフランシスコ平和条約", "d": "連合国との講和を結び、日本の主権を完全に取り戻す復活の聖別魔法陣！"}
    ],
    "impact": [
        {"t": "エンクロージャー", "d": "農地を囲い込んで農業資本主義を生み出し、あふれ出た農民を産業革命の労働力へと変えた歴史の巨大歯車！"},
        {"t": "カルスト地形", "d": "雨水の溶食作用で大地が削られ、地表のドリーネから地下の鍾乳洞まで作り上げる地球規模の造形芸術！"},
        {"t": "プロテスタントの倫理", "d": "勤勉と蓄財を神聖な使命とし、近代資本主義の精神的土台を根底から作り上げた思想的マグマ！"},
        {"t": "ブロック経済", "d": "植民地を巻き込んで巨大な経済圏を囲い込み、世界を深刻な経済対立へと導いた諸刃の剣！"}
    ],
    "love": [
        {"t": "シーラカンス", "d": "数億年前から姿を変えずに生き抜いてきた『生きた化石』！深海のロマンと神秘が詰まりすぎていて尊すぎる！"},
        {"t": "葛飾北斎", "d": "あの圧倒的な構図と波の躍動感！世界の巨匠たちをも狂わせた、日本が誇る天才絵師を一生推し続けます！"},
        {"t": "土偶", "d": "縄文人の祈りと呪術のロマンが爆発した造形美！宇宙人説すら出るその謎めいたデザインが最高に愛おしい！"},
        {"t": "モールス信号", "d": "「トン・ツー」の単純な音の組み合わせだけで地球の裏側と心を通わせられる、究極に美しくミニマルな通信のロマン！"}
    ]
}

# --- ガチモード用の多彩な動的AIカウンター生成 ---
def generate_gachi_cpu_move(player_term, player_desc, mode_key):
    # ランダム性を高めるためのシード要素
    seed_topics = ["世界史の裏の事件", "地理のディープな地形や気候", "日本史の法制度や経済史", "政治経済の難解な仕組み", "古代文明の神秘"]
    chosen_seed = random.choice(seed_topics)
    
    prompt = f"""あなたは「社会科用語バトル」の最強AIプレイヤー（ガチCPU）です。
対戦モード: 「{MODES[mode_key]['name']}」
今回のインスピレーションテーマ: {chosen_seed}

相手（プレイヤー）が以下の用語とアピールを出してきました。
- 相手の用語: {player_term}
- 相手のアピール: {player_desc}

【あなたの使命】
相手の用語に対抗するため、**毎回必ず異なる、高校レベル以上のマニアックで強力な社会科用語**を1つ選び、その用語を使ったモードにふさわしい熱いアピール文（説明文）を自動生成してください。絶対に同じ用語や似たような用語を選ばないでください。

必ず以下のJSON形式のみで出力してください（他のテキストやマークダウンは不要）：
{{
  "cpu_term": "選んだマニアックな用語（例: ティンカウの農法、カノッサの屈辱、ファラデーの電磁誘導、ミティレンの議論 など）",
  "cpu_desc": "その用語のモードに合わせた熱いアピール・決め台詞（100文字程度）"
}}"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(text)
        return data["cpu_term"], data["cpu_desc"]
    except Exception as e:
        # 万が一のエラー時も固定値にならないよう、バリエーションを持たせる
        fallbacks = [
            ("カノッサの屈辱", "皇帝がローマ教皇の前に3日間雪の中でひざまづいた、中世教権の圧倒的マウンティングバースト！"),
            ("大土地所有制（ラティフンディア）", "奴隷を酷使して広大な農地を支配し、ローマの共和政を内部から崩壊させた巨大経済モンスター！"),
            ("サマルカンド", "シルクロードの十字路として輝き、青の都と称されたイスラム世界の圧倒的文明クロスロード！")
        ]
        fb = random.choice(fallbacks)
        return fb[0], fb[1]

# --- AI審判によるジャッジ（バラエティに富んだ実況） ---
def judge_with_gemini(term_a, desc_a, term_b, desc_b, mode_key, name_a, name_b):
    prompt = f"""あなたは超熱血な社会科のカリスマ教師であり、テンション最高潮のゲーム実況風審判です。
「社会科用語バトル」（モード: {MODES[mode_key]['name']}）の熱い勝負をジャッジしてください。

【プレイヤーA: {name_a}】
- 用語: {term_a}
- アピール: {desc_a}

【プレイヤーB: {name_b}】
- 用語: {term_b}
- アピール: {desc_b}

【ジャッジの基準】
1. 安直で誰でも知っている超定番すぎる用語より、「おっ、マニアックで通なチョイスだ！」というセンスを高く評価。
2. 勝者を判定（"A" または "B"）。
3. コメントは必ず**5行程度（120〜150文字前後）**にし、今回の具体的な用語（{term_a} vs {term_b}）の噛み合わせや勝因に触れた、毎回異なるバリエーション豊かな熱血実況にすること。

以下のJSON形式のみで出力してください（他のテキストやマークダウンは不要）：
{{
  "winner": "A" または "B",
  "comment": "今回の対決内容を踏まえた5行程度の熱血実況解説コメント"
}}"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(text)
        return data["winner"], data["comment"]
    except Exception as e:
        return "A", f"両者一歩も譲らない極上の知略戦！{term_a}の放ったディープな切れ味と熱量がわずかに上回り、このラウンドは{name_a}の勝利だァーーッ！"

# ==========================================
# 画面ロジック
# ==========================================
st.title("🏛️ 社会科用語バトル")

# --- メニュー画面 ---
if st.session_state.page == "menu":
    st.session_state.player_name = st.text_input("あなたの名前", value=st.session_state.player_name)
    
    st.write("---")
    st.subheader("🤖 CPU対戦の難易度を選択")
    cpu_mode_choice = st.radio(
        "CPUの強さを選んでください",
        options=["yukkuri", "gachi"],
        format_func=lambda x: "🐢 ゆっくりモード（気軽に楽しく対戦！）" if x == "yukkuri" else "🔥 ガチモード（最強AIが毎回異なるマニアック用語でカウンター！）",
        index=0
    )
    st.session_state.cpu_difficulty = cpu_mode_choice
    
    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🌐 オンライン対戦（ルーム戦）", type="primary"):
            st.session_state.game_type = "online"
            st.session_state.page = "lobby"
            st.rerun()
    with col2:
        if st.button("🤖 CPUと対戦スタート"):
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
                "status": "waiting", "battleMode": "waza", "round": 1,
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
    diff_name = "ゆっくりモード" if st.session_state.cpu_difficulty == "yukkuri" else "🔥 ガチモード"
    st.subheader(f"⚙️ バトル部門選択（3本勝負 / {diff_name}）")
    selected_mode = st.radio("部門を選択", options=list(MODES.keys()), format_func=lambda x: MODES[x]["name"])
    st.caption(MODES[selected_mode]["desc"])
    
    if st.button("3本勝負バトル開始！", type="primary"):
        st.session_state.game_mode = selected_mode
        st.session_state.round = 1
        st.session_state.score_p1 = 0
        st.session_state.score_p2 = 0
        if st.session_state.game_type == "online" and st.session_state.is_host:
            fb_patch(f"rooms/{st.session_state.room_code}", {
                "status": "playing", "battleMode": selected_mode, "round": 1,
                "scoreP1": 0, "scoreP2": 0,
                "hostTerm": "", "hostDesc": "", "guestTerm": "", "guestDesc": "", "result": None
            })
        st.session_state.page = "input"
        st.rerun()

# --- 入力画面 ---
elif st.session_state.page == "input":
    diff_name = "ゆっくり" if st.session_state.cpu_difficulty == "yukkuri" else "🔥ガチ"
    st.subheader(f"⚔️ 第 {st.session_state.round} ラウンド / 全3戦 ({MODES[st.session_state.game_mode]['name']})")
    st.write(f"現在のスコア: あなた **{st.session_state.score_p1}** - **{st.session_state.score_p2}** ({diff_name}CPU)")
    
    with st.form("input_form"):
        term = st.text_input("社会科用語を入力")
        desc = st.text_area(MODES[st.session_state.game_mode]["label"])
        submit = st.form_submit_button("🔥 提出して勝負する！", type="primary")
        
        if submit:
            if not term.strip() or not desc.strip():
                st.error("用語と説明文の両方を入力してください。")
            else:
                if st.session_state.game_type == "online":
                    role = "host" if st.session_state.is_host else "guest"
                    fb_patch(f"rooms/{st.session_state.room_code}", {
                        f"{role}Term": term, f"{role}Desc": desc
                    })
                    st.session_state.page = "wait_result"
                    st.rerun()
                else:
                    if st.session_state.cpu_difficulty == "yukkuri":
                        cpu_choice = random.choice(YUKKURI_DATA[st.session_state.game_mode])
                        cpu_term, cpu_desc = cpu_choice["t"], cpu_choice["d"]
                    else:
                        with st.spinner("🤖 ガチCPUがあなたを迎え撃つ最強のマニアック用語を思案中..."):
                            cpu_term, cpu_desc = generate_gachi_cpu_move(term, desc, st.session_state.game_mode)
                    
                    winner, comment = judge_with_gemini(
                        term, desc, cpu_term, cpu_desc,
                        st.session_state.game_mode, st.session_state.player_name, f"CPU({diff_name})"
                    )
                    
                    if winner == "A": st.session_state.score_p1 += 1
                    else: st.session_state.score_p2 += 1
                        
                    st.session_state.result = {
                        "termA": term, "descA": desc, "termB": cpu_term, "descB": cpu_desc,
                        "winner": winner, "comment": comment,
                        "nameA": st.session_state.player_name, "nameB": f"CPU({diff_name})",
                        "scoreP1": st.session_state.score_p1, "scoreP2": st.session_state.score_p2
                    }
                    st.session_state.page = "result"
                    st.rerun()

# --- 結果待機画面（オンライン） ---
elif st.session_state.page == "wait_result":
    st.info("対戦相手の提出とAIジャッジを待っています...")
    time.sleep(2)
    data = fb_get(f"rooms/{st.session_state.room_code}")
    
    if data:
        if st.session_state.is_host and data.get("hostTerm") and data.get("guestTerm") and not data.get("result"):
            winner, comment = judge_with_gemini(
                data["hostTerm"], data["hostDesc"], data["guestTerm"], data["guestDesc"],
                data["battleMode"], data["host"], data["guest"]
            )
            
            p1_score = data.get("scoreP1", 0)
            p2_score = data.get("scoreP2", 0)
            if winner == "A": p1_score += 1
            else: p2_score += 1
            
            res_data = {
                "termA": data["hostTerm"], "descA": data["hostDesc"],
                "termB": data["guestTerm"], "descB": data["guestDesc"],
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
        st.info(f"**{res['termA']}**\n\n{res['descA']}")
    with col2:
        st.markdown(f"**【{res['nameB']}】**")
        st.info(f"**{res['termB']}**\n\n{res['descB']}")
        
    st.markdown("### 🤖 カリスマAI審判の実況解説")
    st.markdown(f"<div class='ai-comment-box'>{res['comment']}</div>", unsafe_allow_html=True)
    
    st.write("---")
    st.write(f"現在のトータルスコア: **{res['nameA']}** `【 {res['scoreP1']}勝 】` - `【 {res['scoreP2']}勝 】` **{res['nameB']}**")
    
    if st.session_state.round < 3:
        if st.button("次ラウンドへ進む ➔", type="primary"):
            st.session_state.round += 1
            if st.session_state.game_type == "online" and st.session_state.is_host:
                fb_patch(f"rooms/{st.session_state.room_code}", {
                    "round": st.session_state.round,
                    "hostTerm": "", "hostDesc": "", "guestTerm": "", "guestDesc": "", "result": None
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
    st.subheader("🎉 3本勝負 最終結果発表！ 🎉")
    
    p1 = st.session_state.score_p1
    p2 = st.session_state.score_p2
    
    if p1 > p2:
        st.header(f"👑 総合優勝：{st.session_state.player_name} ！！")
        st.caption("素晴らしい用語センスと知略、そして深い歴史愛が審判の心を撃ち抜きました！")
    elif p2 > p1:
        st.header("💀 敗北……勝者：CPU")
        st.caption("相手の鋭い用語攻勢の前に惜敗！次はさらなる知識でリベンジだ！")
    else:
        st.header("🤝 決着つかずのドロー！")
        st.caption("互いに一歩も譲らない驚異の知識量と熱量！まさに伝説に残る名勝負でした！")
        
    st.metric(label="最終勝利数", value=f"{p1} 勝 - {p2} 勝")
    
    st.write("---")
    if st.button("タイトルに戻る"):
        st.session_state.page = "menu"
        st.rerun()
