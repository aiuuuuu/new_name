# -*- coding: utf-8 -*-
"""
卒論用 Streamlit アプリ（統合版 main.py）
- RSES 6件法（逆転項目は7-値で処理）
- 自尊感情を元にした AI ミッション自動生成（利用不可時はフォールバック）
- 簡易栄養計算（量を考慮）を拡張
- データ永続化： user_data.json / app_data.json
- CSS（フォント・背景・スマホ対応）を統合
"""

import streamlit as st
import datetime, calendar, os, json
#from dotenv import load_dotenv

# -------------------------
# OpenAI クライアント初期化（新/旧どちらにも対応）
# -------------------------
client = None
openai_client_inited = False
try:
    # prefer new client style (OpenAI)
    from openai import OpenAI
    api_key = None
    try:
        api_key = st.secrets.get("OPENAI_KEY")
    except Exception:
        api_key = None
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            openai_client_inited = True
        except Exception:
            client = None
            openai_client_inited = False
    else:
        client = None
        openai_client_inited = False
except Exception:
    # fallback to legacy openai
    try:
        import openai
        #load_dotenv()
        k = None
        try:
            #k = st.secrets.get("OPENAI_KEY")
            k = st.secrets['test.py']["OPENAI_KEY"]
        except Exception:
            k = None
        if not k:
            k = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
        if k:
            openai.api_key = k
            client = openai
            openai_client_inited = True
        else:
            client = None
            openai_client_inited = False
    except Exception:
        client = None
        openai_client_inited = False

#load_dotenv()

# -------------------------
# 設定
# -------------------------
st.set_page_config(page_title="卒論アプリ（拡張・RSES6＋AIミッション）", layout="centered", initial_sidebar_state="collapsed")

# debug (can remove)
try:
    st.write("DEBUG_API_KEY_PRESENT:", bool(st.secrets.get("OPENAI_KEY")))
    st.write("DEBUG_API_KEY_PRESENT:", bool(st.secrets['test.py']["OPENAI_KEY"]))

except Exception:
    st.write("DEBUG_API_KEY_PRESENT: unknown")

# ============================================
# ▼ CSS（フォント・背景 ＋ スマホ対応）
# ============================================
custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans JP', sans-serif !important;
    color: #111 !important;
    -webkit-font-smoothing: antialiased;
}

body {
    background: #FFF4E8 !important;
}

.main, .block-container {
    background-color: #FFF4E8 !important;
}

.asuken-card, .card {
    background: #ffffff;
    border-radius: 16px;
    padding: 16px 20px;
    margin-bottom: 18px;
    box-shadow: 0 3px 8px rgba(0,0,0,0.08);
}

.asuken-title {
    font-size: 1.4rem;
    font-weight: 700;
    color: #D66A1F;
    margin-bottom: 10px;
}

.asuken-subtitle {
    font-size: 1.1rem;
    font-weight: 500;
    color: #E67E22;
    margin-top: 10px;
}

.stButton>button {
    background-color: #FF9F54 !important;
    color: #ffffff !important;
    border-radius: 10px !important;
    padding: 10px 18px !important;
    font-size: 1rem !important;
}

@media (max-width: 480px) {
    .asuken-card {
        padding: 14px 16px;
        margin-bottom: 14px;
    }
    .asuken-title {
        font-size: 1.25rem;
    }
    .asuken-subtitle {
        font-size: 1.05rem;
    }
    .stButton>button {
        width: 100% !important;
        font-size: 1.1rem !important;
        padding: 14px !important;
    }
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
}

.section { max-width: 760px; margin: 0 auto; padding: 12px; }
input[type="text"], textarea { font-size:16px !important; padding:10px !important; }
.bottom-nav { margin-top:14px; margin-bottom:18px; }
.header-btn { display:flex; justify-content:flex-end; }

</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# -------------------------
# ファイル永続化
# -------------------------
USER_FILE = "user_data.json"
APP_FILE = "app_data.json"

def load_user():
    if os.path.exists(USER_FILE):
        try:
            with open(USER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def save_user(data):
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_app():
    if os.path.exists(APP_FILE):
        try:
            with open(APP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"missions": {}, "meal_data": {}, "feedback": {}}
    return {"missions": {}, "meal_data": {}, "feedback": {}}

def save_app(data):
    with open(APP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# -------------------------
# session init (safe)
# -------------------------
if "registered" not in st.session_state:
    st.session_state.registered = False
if "page" not in st.session_state:
    st.session_state.page = "init_register"
if "user_info" not in st.session_state:
    u = load_user()
    if u:
        st.session_state.user_info = u
        st.session_state.registered = True
    else:
        st.session_state.user_info = {"birth": None, "gender": "", "region": "", "age": 0, "self_esteem_level": ""}
if "app_data" not in st.session_state:
    st.session_state.app_data = load_app()
if "today_date" not in st.session_state:
    st.session_state.today_date = datetime.date.today()
if "show_calendar" not in st.session_state:
    st.session_state.show_calendar = False

# -------------------------
# helpers
# -------------------------
def safe_rerun():
    if hasattr(st, "rerun"): st.rerun()
    elif hasattr(st, "experimental_rerun"): st.experimental_rerun()
    else: pass

def calculate_age(birth_date):
    today = datetime.date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

# -------------------------
# ★ AIミッション生成（Part2のロジックを統合）
# -------------------------
def try_generate_missions():
    fallback = ["野菜を1食とる", "水を1杯飲む", "20分歩く"]
    # if no client available, return fallback
    if not client or not openai_client_inited:
        return fallback

    # gather context
    age = st.session_state.user_info.get("age", 0)
    gender = st.session_state.user_info.get("gender", "")
    self_esteem = st.session_state.user_info.get("self_esteem_level", "")
    today = st.session_state.today_date.strftime("%Y-%m-%d")
    meal_data = st.session_state.app_data.get("meal_data", {}).get(today, {})
    nutrient_totals, tendencies = calc_nutrition(meal_data)

    # build prompt
    prompt = f"""あなたは健康行動支援の専門家です。
以下の情報をもとに、対象者が今日取り組める簡単な行動ミッションを**短く具体的に3つ**提案してください。
各ミッションは3〜7語程度にまとめてください。

【プロフィール】
- 年齢: {age}
- 性別: {gender}
- 自尊感情レベル: {self_esteem}

【簡易栄養（内部単位）】
タンパク質: {nutrient_totals.get('タンパク質', nutrient_totals.get('p',0))}g, 脂質: {nutrient_totals.get('脂質', nutrient_totals.get('f',0))}g, 炭水化物: {nutrient_totals.get('炭水化物', nutrient_totals.get('c',0))}g

【栄養傾向】
{', '.join(tendencies) if tendencies else '特になし'}

出力は1行ずつ「1. ○○」の形式で3行にしてください。
例:
1. 野菜をもう一品追加する
2. 夜に間食を控える
3. 15分間速歩する
"""
    try:
        # support both new OpenAI client and legacy openai
        if hasattr(client, "chat") and hasattr(client.chat, "completions"):
            # new client style
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"system","content":"あなたは親切で実用的な健康支援アドバイザーです。"}, {"role":"user","content":prompt}],
                temperature=0.7, max_tokens=200
            )
            text = resp.choices[0].message.content.strip()
        else:
            # legacy openai
            resp = client.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role":"system","content":"あなたは親切で実用的な健康支援アドバイザーです。"}, {"role":"user","content":prompt}],
                temperature=0.7, max_tokens=200
            )
            text = resp.choices[0].message.content.strip()

        # parse into lines starting with 1. 2. 3.
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        missions = []
        for ln in lines:
            # try to strip "1." or "1)" prefixes
            # handle common patterns
            cleaned = ln
            if ln.startswith(("1.","2.","3.","1)","2)","3)")):
                cleaned = ln[2:].strip()
            elif len(ln) >= 3 and ln[1:3] == ". ":
                cleaned = ln[3:].strip()
            cleaned = cleaned.lstrip('0123456789. )\t-')
            cleaned = cleaned.strip()
            if cleaned:
                missions.append(cleaned)
        # ensure length 3
        out = missions[:3]
        while len(out) < 3:
            out.append(fallback[len(out)])
        return out
    except Exception:
        return fallback

# -------------------------
# フィードバック生成（ラッパー）
# -------------------------
def generate_feedback_from_prompt(prompt):
    """Low-level wrapper: try OpenAI then fallback text."""
    fallback_short = "フィードバックを生成できませんでした。食事改善のポイントを意識してください。"
    if not client or not openai_client_inited:
        return fallback_short
    try:
        if hasattr(client, "chat") and hasattr(client.chat, "completions"):
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "あなたは親切で実用的な栄養指導の専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7, max_tokens=400
            )
            return resp.choices[0].message.content.strip()
        else:
            resp = client.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "あなたは親切で実用的な栄養指導の専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7, max_tokens=400
            )
            return resp.choices[0].message.content.strip()
    except Exception:
        return fallback_short

def try_generate_feedback(age, gender, self_esteem_level, meals, selected_mission=None):
    """
    meals: {"朝食": [ {"item": "...", "intake":"普通"}, ... ], ...}
    """
    # normalize old-style data if necessary
    normalized_meals = {}
    for k in ["朝食","昼食","夕食","間食"]:
        raw_items = meals.get(k, []) if meals else []
        norm = []
        for it in raw_items:
            if isinstance(it, str):
                norm.append({"item": it, "intake": "普通"})
            elif isinstance(it, dict):
                name = it.get("item") or it.get("name")
                intake = it.get("intake") or it.get("amount_label") or "普通"
                norm.append({"item": name, "intake": intake})
        normalized_meals[k] = norm

    # create meal text
    meal_lines = []
    for meal_name, items in normalized_meals.items():
        for it in items:
            meal_lines.append(f"{meal_name}: {it['item']}（量: {it['intake']}）")
    meal_text = "\n".join(meal_lines) if meal_lines else "食事記録がありません。"

    totals, tendencies = calc_nutrition(normalized_meals)

    mission_text = selected_mission or "なし"
    # Build prompt
    prompt = f"""あなたは親切で実用的な栄養指導の専門家です。
以下の情報を踏まえて、5〜8文でフィードバックを作ってください。良い点・改善点・次の行動提案を必ず含めてください。最後は「明日も少しずつ続けていきましょう」で締めてください。

年齢: {age}
性別: {gender}
自尊感情レベル: {self_esteem_level}
今日のミッション: {mission_text}

【食事内容（量付き）】
{meal_text}

【推定栄養（内部単位）】
タンパク質: {totals.get('タンパク質', totals.get('p',0))}g, 脂質: {totals.get('脂質', totals.get('f',0))}g, 炭水化物: {totals.get('炭水化物', totals.get('c',0))}g

【栄養傾向】
{', '.join(tendencies) if tendencies else '特になし'}
"""
    return generate_feedback_from_prompt(prompt)

# -------------------------
# ★ 簡易栄養計算（拡張版）
# -------------------------
def calc_nutrition(meals):
    """
    meals expected:
    {"朝食": [ "卵", {"item":"サラダ","intake":"普通"}, ... ], ... }
    old string-only items are supported and treated as intake="普通".
    Returns totals (タンパク質, 脂質, 炭水化物, cal, 塩分) and tendencies list.
    Works with both simple item lists and the extended meal dicts used elsewhere.
    """
    # Accept also a flat mapping like {"卵":"普通"}: handle gracefully
    intake_factor = {"少なめ": 0.8, "普通": 1.0, "多め": 1.2}
    # expanded nutrition DB (per portion approximate)
    NUTRITION_DB = {
        "ごはん": {"タンパク質":3, "脂質":1, "炭水化物":37, "cal":168, "塩分":0},
        "ご飯": {"タンパク質":3, "脂質":1, "炭水化物":37, "cal":168, "塩分":0},
        "パン": {"タンパク質":4, "脂質":5, "炭水化物":30, "cal":200, "塩分":0.5},
        "パスタ": {"タンパク質":6, "脂質":8, "炭水化物":40, "cal":350, "塩分":0.8},
        "魚": {"タンパク質":20, "脂質":10, "炭水化物":0, "cal":240, "塩分":0.2},
        "肉": {"タンパク質":25, "脂質":20, "炭水化物":0, "cal":300, "塩分":0.3},
        "鶏肉": {"タンパク質":20, "脂質":10, "炭水化物":0, "cal":220, "塩分":0.2},
        "卵": {"タンパク質":6, "脂質":5, "炭水化物":1, "cal":90, "塩分":0.1},
        "サラダ": {"タンパク質":1, "脂質":1, "炭水化物":3, "cal":60, "塩分":0.1},
        "ヨーグルト": {"タンパク質":4, "脂質":2, "炭水化物":5, "cal":80, "塩分":0.05},
        "味噌汁": {"タンパク質":3, "脂質":1, "炭水化物":3, "cal":40, "塩分":1.0},
        "プロテイン": {"タンパク質":20, "脂質":2, "炭水化物":3, "cal":120, "塩分":0.2},
        "サンドイッチ": {"タンパク質":10, "脂質":12, "炭水化物":35, "cal":350, "塩分":1.0},
        "ハンバーグ": {"タンパク質":18, "脂質":20, "炭水化物":5, "cal":350, "塩分":0.8},
        "揚げ物": {"タンパク質":8, "脂質":22, "炭水化物":20, "cal":400, "塩分":0.6},
        "お菓子": {"タンパク質":3, "脂質":15, "炭水化物":45, "cal":300, "塩分":0.2},
        "バナナ": {"タンパク質":1, "脂質":0.2, "炭水化物":22, "cal":90, "塩分":0},
    }

    totals = {"タンパク質":0.0, "脂質":0.0, "炭水化物":0.0, "cal":0.0, "塩分":0.0}
    tendencies = []

    # If meals looks like flat nutrition mapping (not meal->items), try to handle
    if isinstance(meals, dict) and all(isinstance(v, str) for v in meals.values()):
        # e.g. {"卵":"普通", "ごはん":"多め"}
        for name, amount in meals.items():
            matched = None
            for k in NUTRITION_DB.keys():
                if k in name or name == k:
                    matched = NUTRITION_DB[k]; break
            factor = intake_factor.get(amount, 1.0)
            if matched:
                totals["タンパク質"] += matched.get("タンパク質",0) * factor
                totals["脂質"] += matched.get("脂質",0) * factor
                totals["炭水化物"] += matched.get("炭水化物",0) * factor
                totals["cal"] += matched.get("cal",0) * factor
                totals["塩分"] += matched.get("塩分",0) * factor
    else:
        # expected structure: {"朝食":[...],"昼食":[...],...}
        for meal, items in (meals or {}).items():
            if not items:
                continue
            for it in items:
                if isinstance(it, str):
                    name = it
                    intake = "普通"
                elif isinstance(it, dict):
                    name = it.get("item") or it.get("name") or it.get("food") or ""
                    intake = it.get("intake") or it.get("amount") or it.get("amount_label") or "普通"
                else:
                    continue

                matched = None
                if name in NUTRITION_DB:
                    matched = NUTRITION_DB[name]
                else:
                    for k in NUTRITION_DB.keys():
                        if k in name:
                            matched = NUTRITION_DB[k]
                            break

                factor = intake_factor.get(intake, 1.0)
                if matched:
                    totals["タンパク質"] += matched.get("タンパク質",0) * factor
                    totals["脂質"] += matched.get("脂質",0) * factor
                    totals["炭水化物"] += matched.get("炭水化物",0) * factor
                    totals["cal"] += matched.get("cal",0) * factor
                    totals["塩分"] += matched.get("塩分",0) * factor
                else:
                    # fallback heuristics
                    if any(x in name for x in ["肉","魚","鶏","ハンバーグ"]):
                        totals["タンパク質"] += 10 * factor
                    if any(x in name for x in ["揚げ","バター","油","フライ"]):
                        totals["脂質"] += 5 * factor
                    if any(x in name for x in ["ごはん","ご飯","パン","パスタ","麺","うどん","そば"]):
                        totals["炭水化物"] += 30 * factor

    totals = {k: round(v,1) for k,v in totals.items()}

    # tendencies
    if totals["タンパク質"] < 40:
        tendencies.append("タンパク質不足傾向")
    if totals["脂質"] > 70:
        tendencies.append("脂質多めの傾向")
    if totals["炭水化物"] > 300:
        tendencies.append("炭水化物多めの傾向")
    if totals["塩分"] > 6:
        tendencies.append("塩分多めの傾向")

    return totals, tendencies

# -------------------------
# UI helpers
# -------------------------
def show_header(left_text="", right_callable=None):
    cols = st.columns([0.7, 0.3])
    cols[0].markdown(f"### {left_text}")
    if right_callable:
        try:
            right_callable(cols[1])
        except Exception:
            cols[1].markdown("")

PREFECTURES = [
 "北海道","青森県","岩手県","宮城県","秋田県","山形県","福島県",
 "茨城県","栃木県","群馬県","埼玉県","千葉県","東京都","神奈川県",
 "新潟県","富山県","石川県","福井県","山梨県","長野県",
 "岐阜県","静岡県","愛知県","三重県",
 "滋賀県","京都府","大阪府","兵庫県","奈良県","和歌山県",
 "鳥取県","島根県","岡山県","広島県","山口県",
 "徳島県","香川県","愛媛県","高知県",
 "福岡県","佐賀県","長崎県","熊本県","大分県","宮崎県","鹿児島県","沖縄県"
]

# -------------------------
# 初期登録
# -------------------------
def show_init_register():
    show_header("初期登録")
    st.markdown('<div class="section">', unsafe_allow_html=True)
    with st.form("init_form_final"):
        st.subheader("生年月日")
        years = list(range(1950, datetime.date.today().year+1))
        months = list(range(1,13)); days = list(range(1,32))
        c1,c2,c3 = st.columns(3)
        year = c1.selectbox("年", years, index=years.index(2000), key="yr_final")
        month = c2.selectbox("月", months, index=0, key="mo_final")
        day = c3.selectbox("日", days, index=0, key="dy_final")
        st.subheader("性別")
        gender = st.selectbox("性別を選択してください", ["男性","女性","その他"], key="gnd_final")
        st.subheader("地域")
        region = st.selectbox("お住まいの都道府県", PREFECTURES, key="pref_final")
        submitted = st.form_submit_button("登録して次へ", key="init_submit_final")
    if submitted:
        birth = datetime.date(year,month,day)
        age = calculate_age(birth)
        st.session_state.user_info.update({"birth": birth.strftime("%Y-%m-%d"), "gender": gender, "region": region, "age": age})
        st.session_state.registered = True
        save_user(st.session_state.user_info)
        ensure_today_mission()
        st.session_state.page = "self_esteem"
        safe_rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# 自尊感情診断（RSES 6件法）
# -------------------------
def show_self_esteem():
    show_header("タイプ診断")
    st.markdown('<div class="section">', unsafe_allow_html=True)
    questions = [
        "私は自分に満足している",
        "時々、自分には全く価値がないと感じる",
        "私は他の人と同じくらい価値がある人間だと思う",
        "私には誇れるものがほとんどない",
        "私は自分に対してポジティブな態度を持っている",
        "自分のことをもう少し尊敬できたらいいと思う",
        "私は自分を役立つ人間だと思う",
        "時々、自分がダメな人間だと感じる",
        "全体として私は自分に満足している",
        "私は自分に対してあまり自信がない",
    ]

    # 指定どおりの肯定 / 逆転アイテム指示（ユーザー指定を尊重）
    # 肯定項目: 1,2,4,6,7
    positive_idxs = {1,2,4,6,7}
    # 逆転項目: 3,5,8,9,10
    reverse_idxs = {3,5,8,9,10}

    answers = []
    with st.form("se_form_final"):
        st.markdown("**以下は6件法で回答してください（1〜6）**")
        st.markdown("1 = 全くそう思わない, 2 = あまりそう思わない, 3 = ややそう思わない, 4 = ややそう思う, 5 = そう思う, 6 = 非常にそう思う")
        for i,q in enumerate(questions, start=1):
            # default index -> 3 (value 4) to be roughly neutral
            default_val = 4
            val = st.radio(f"{i}. {q}", [1,2,3,4,5,6], index=default_val-1, horizontal=True, key=f"se_final_{i}")
            answers.append(val)
        submitted = st.form_submit_button("診断する", key="se_submit_final")
    if submitted:
        score = 0
        for idx, a in enumerate(answers, start=1):
            if idx in reverse_idxs:
                score += (7 - a)
            else:
                score += a
        # 2段階判定（基準は 35 点以上を高とする。必要なら閾値は調整可能）
        level = "高" if score >= 35 else "低"
        st.session_state.user_info["self_esteem_level"] = level
        # save numeric score too for analysis convenience
        st.session_state.user_info["self_esteem_score"] = score
        save_user(st.session_state.user_info)
        ensure_today_mission()
        st.session_state.page = "mission"
        safe_rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# ミッション画面（AI生成版）
# -------------------------
def show_mission():
    show_header("ミッション")
    st.markdown('<div class="section">', unsafe_allow_html=True)

    today = st.session_state.today_date.strftime("%Y-%m-%d")
    st.session_state.app_data.setdefault("missions", {})

    # date init
    if today not in st.session_state.app_data["missions"]:
        st.session_state.app_data["missions"][today] = {
            "auto": try_generate_missions(),
            "custom": [],
            "selected": None,
            "status": {}
        }
        save_app(st.session_state.app_data)

    data = st.session_state.app_data["missions"][today]

    st.write("#### 今日のミッション（選択して次へ）")

    # 自動生成ミッション一覧表示
    for m in data["auto"]:
        st.markdown(f"- {m}")

    # 選択 UI
    with st.form("mission_form_after_se"):
        custom = st.text_input("自作ミッション（任意）", key="mission_custom_after")
        labels = data["auto"] + ["自作ミッション"]

        sel = st.radio("候補から選択", labels, index=0, key="mission_choice_after")
        # ここは3段階の回答という意図がありましたが既存UIでは選択肢から1つ選ぶ形です。
        # 必要なら別途"達成度: 未達成/部分達成/達成"の UI を追加可能です。
        submitted = st.form_submit_button("選択して次へ")

    if submitted:
        # 自作ミッション
        if sel == "自作ミッション":
            if not custom.strip():
                st.warning("自作ミッションが空です。入力してください。")
                return
            chosen = custom.strip()
            if chosen not in data["custom"]:
                data["custom"].append(chosen)
        else:
            chosen = sel

        # 保存
        data["selected"] = chosen
        data.setdefault("status", {})
        data["status"].setdefault(chosen, False)

        st.session_state.app_data["missions"][today] = data
        save_app(st.session_state.app_data)

        # 次の画面へ
        st.session_state.page = "meal"
        safe_rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# 今日のミッション表示（ホーム下部のボタンで遷移）
# -------------------------
def show_today_mission_display():

    # 右上の「過去」ボタン
    def right_comp(col):
        if col.button("過去"):
            st.session_state.page = "mission_history"
            safe_rerun()

    show_header("ミッション", right_callable=right_comp)
    st.markdown('<div class="section">', unsafe_allow_html=True)

    key_date = st.session_state.today_date.strftime("%Y-%m-%d")
    st.session_state.app_data.setdefault("missions", {})

    # データがない場合は生成
    if key_date not in st.session_state.app_data["missions"]:
        st.session_state.app_data["missions"][key_date] = {
            "auto": try_generate_missions(),
            "custom": [],
            "selected": None,
            "status": {}
        }
        save_app(st.session_state.app_data)

    data = st.session_state.app_data["missions"][key_date]
    chosen = data.get("selected")

    st.markdown("#### 今日のミッション")

    if chosen:
        st.markdown(
            f"<div class='card' style='padding:12px; font-size:18px;'><b>{chosen}</b></div>",
            unsafe_allow_html=True
        )

        data.setdefault("status", {})
        current_status = data["status"].get(chosen, False)

        cols = st.columns(2)

        if cols[0].button("未達成", key="mission_unachieved_btn"):
            data["status"][chosen] = False
            st.session_state.app_data["missions"][key_date] = data
            save_app(st.session_state.app_data)
            safe_rerun()

        if cols[1].button("達成", key="mission_achieved_btn"):
            data["status"][chosen] = True
            st.session_state.app_data["missions"][key_date] = data
            save_app(st.session_state.app_data)
            safe_rerun()

        st.write("---")

    else:
        st.info("ミッションがまだ選択されていません。最初のミッション選択画面で選択してください。")

    c1, c2, c3 = st.columns(3)
    if c1.button("🍱 食事管理"):
        st.session_state.page = "meal"; safe_rerun()
    if c2.button("📝 フィードバック"):
        st.session_state.page = "feedback"; safe_rerun()
    if c3.button("🎯 今日のミッション"):
        st.session_state.page = "today_mission_display"; safe_rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# 過去のミッション画面（修正版）
# -------------------------
def show_mission_history():
    show_header("過去のミッション")

    st.markdown('<div class="section">', unsafe_allow_html=True)

    missions = st.session_state.app_data.get("missions", {})

    if not missions:
        st.write("まだミッション履歴がありません。")
        return

    for day in sorted(missions.keys()):
        data = missions[day]
        selected = data.get("selected")
        if not selected:
            continue

        status = data.get("status", {}).get(selected, None)
        if status is None:
            stat_text = "未設定"
            icon = "⚪"
        elif status:
            stat_text = "達成"
            icon = "✅"
        else:
            stat_text = "未達成"
            icon = "❌"

        cols = st.columns([0.2, 0.6, 0.2])
        cols[0].markdown(f"**{day}**")
        cols[1].markdown(
            f"<div style='text-align:center; padding:10px; font-size:16px; border-radius:8px; background-color:#f0f0f0;'>"
            f"<b>{selected} — {stat_text} {icon}</b>"
            f"</div>",
            unsafe_allow_html=True
        )
        cols[2].markdown("")

        st.write("---")

    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("⬅ 戻る"):
        st.session_state.page = "today_mission_display"
        safe_rerun()

# -------------------------
# カレンダー描画（既存）
# -------------------------
def render_month_calendar(year, month):
    cal = calendar.Calendar(firstweekday=6)
    weeks = cal.monthdayscalendar(year, month)
    st.markdown(f"#### {year}年 {month}月")
    days = ["日","月","火","水","木","金","土"]
    cols = st.columns(7)
    for i,d in enumerate(days):
        cols[i].markdown(f"**{d}**")
    for wk in weeks:
        cols = st.columns(7)
        for i,day in enumerate(wk):
            if day == 0:
                cols[i].write(" ")
            else:
                d = datetime.date(year, month, day)
                label = str(day)
                display_label = f"▶ {label}" if d == st.session_state.today_date else label
                if cols[i].button(display_label, key=f"cal_{year}_{month}_{day}"):
                    st.session_state.today_date = d
                    safe_rerun()

# -------------------------
# 食事管理画面（量選択・削除機能追加）
# -------------------------
def show_meal():
    def hdr_right(col):
        if col.button("📅 カレンダー", key="hdr_cal_main"):
            st.session_state.show_calendar = not st.session_state.show_calendar
    show_header("食事管理", right_callable=hdr_right)
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.markdown(f"**選択中の日付：** {st.session_state.today_date.strftime('%Y-%m-%d')}")
    if st.session_state.show_calendar:
        y = st.session_state.today_date.year
        m = st.session_state.today_date.month
        n1,n2,n3 = st.columns([0.2,0.6,0.2])
        if n1.button("◀", key="cal_prev_main"):
            if m == 1:
                y -= 1; m = 12
            else:
                m -= 1
            st.session_state.today_date = datetime.date(y,m,st.session_state.today_date.day if st.session_state.today_date.day<=calendar.monthrange(y,m)[1] else calendar.monthrange(y,m)[1])
            safe_rerun()
        if n3.button("▶", key="cal_next_main"):
            if m == 12:
                y += 1; m = 1
            else:
                m += 1
            st.session_state.today_date = datetime.date(y,m,st.session_state.today_date.day if st.session_state.today_date.day<=calendar.monthrange(y,m)[1] else calendar.monthrange(y,m)[1])
            safe_rerun()
        render_month_calendar(y,m)
    st.write("---")
    st.subheader("食事入力")
    key_date = st.session_state.today_date.strftime("%Y-%m-%d")

    md = st.session_state.app_data.setdefault("meal_data", {})
    if key_date not in md:
        md[key_date] = {"朝食":[],"昼食":[],"夕食":[],"間食":[]}
    for dkey, dd in md.items():
        for meal in ["朝食","昼食","夕食","間食"]:
            items = dd.get(meal, [])
            new_items = []
            for it in items:
                if isinstance(it, str):
                    new_items.append({"item": it, "intake": "普通"})
                elif isinstance(it, dict) and ("item" in it or "name" in it or "food" in it):
                    name = it.get("item") or it.get("name") or it.get("food")
                    intake = it.get("intake") or it.get("amount_label") or "普通"
                    new_items.append({"item": name, "intake": intake})
                else:
                    pass
            dd[meal] = new_items
        md[dkey] = dd
    st.session_state.app_data["meal_data"] = md

    meals = st.session_state.app_data["meal_data"][key_date]

    for meal in ["朝食","昼食","夕食","間食"]:
        st.markdown(f"**{meal}**")
        if meals.get(meal):
            for i,it in enumerate(meals[meal]):
                cols = st.columns([0.7,0.15,0.15])
                display_name = f"{it['item']}（{it.get('intake','普通')}）" if isinstance(it, dict) else f"{it}（普通）"
                cols[0].write(f"- {display_name}")
                if cols[1].button("編集", key=f"edit_{meal}_{i}_{key_date}"):
                    st.session_state[f"edit_item_{meal}_{i}_{key_date}"] = it
                    st.session_state[f"edit_idx_{meal}_{key_date}"] = i
                    st.session_state[f"edit_meal_{meal}_{key_date}"] = meal
                    st.session_state.page = "edit_item"
                    save_app(st.session_state.app_data)
                    safe_rerun()
                if cols[2].button("削除", key=f"del_{meal}_{i}_{key_date}"):
                    meals[meal].pop(i)
                    st.session_state.app_data["meal_data"][key_date] = meals
                    save_app(st.session_state.app_data)
                    safe_rerun()
        new_key = f"add_{meal}_{key_date}"
        st.text_input(f"{meal} を追加 (例: ハンバーグ)", key=new_key, placeholder="食事名を入力してください")
        intake_key = f"intake_{meal}_{key_date}"
        intake = st.selectbox("量を選択", ["少なめ","普通","多め"], index=1, key=intake_key)
        if st.button("追加", key=f"btn_{new_key}"):
            new_val = st.session_state.get(new_key,"").strip()
            if new_val:
                meals[meal].append({"item": new_val, "intake": intake})
                st.session_state.app_data["meal_data"][key_date] = meals
                save_app(st.session_state.app_data)
                safe_rerun()
            else:
                st.warning("入力が空です。")
    if st.button("保存（全体）", key="save_meals_main"):
        st.session_state.app_data["meal_data"][key_date] = meals
        save_app(st.session_state.app_data)
        st.success("保存しました。")
    c1,c2,c3 = st.columns(3)
    if c1.button("🍱 食事管理", key="nav_meal_main"): st.session_state.page="meal"; safe_rerun()
    if c2.button("📝 フィードバック", key="nav_feedback_main"): st.session_state.page="feedback"; safe_rerun()
    if c3.button("🎯 今日のミッション", key="nav_today_from_meal"): st.session_state.page="today_mission_display"; safe_rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# edit item page (simple)
# -------------------------
def show_edit_item():
    keys = [k for k in st.session_state.keys() if k.startswith("edit_item_")]
    today = st.session_state.today_date.strftime("%Y-%m-%d")
    edit_keys = [k for k in st.session_state.keys() if k.endswith(f"_{today}")]
    if not edit_keys:
        st.session_state.page = "meal"; safe_rerun(); return
    edit_item_key = [k for k in edit_keys if k.startswith("edit_item_")][0]
    edit_idx_key = [k for k in edit_keys if k.startswith("edit_idx_")][0]
    edit_meal_key = [k for k in edit_keys if k.startswith("edit_meal_")][0]

    item = st.session_state.get(edit_item_key)
    idx = st.session_state.get(edit_idx_key)
    meal = st.session_state.get(edit_meal_key)

    show_header("食事編集")
    st.markdown('<div class="section">', unsafe_allow_html=True)

    name = st.text_input("食事名", value=item.get("item",""))
    intake = st.selectbox("量", ["少なめ","普通","多め"], index=["少なめ","普通","多め"].index(item.get("intake","普通")))

    if st.button("保存"):
        key_date = st.session_state.today_date.strftime("%Y-%m-%d")
        md = st.session_state.app_data.setdefault("meal_data", {})
        if key_date in md and meal in md[key_date] and idx < len(md[key_date][meal]):
            md[key_date][meal][idx] = {"item": name, "intake": intake}
            st.session_state.app_data["meal_data"] = md
            save_app(st.session_state.app_data)
        st.session_state.page = "meal"
        for k in [edit_item_key, edit_idx_key, edit_meal_key]:
            if k in st.session_state: del st.session_state[k]
        safe_rerun()

    if st.button("キャンセル"):
        st.session_state.page = "meal"
        for k in [edit_item_key, edit_idx_key, edit_meal_key]:
            if k in st.session_state: del st.session_state[k]
        safe_rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# フィードバック（右上に過去ボタン）
# -------------------------
def show_feedback():
    def hdr_right(col):
        if col.button("過去", key="hdr_past_fb"):
            st.session_state.page = "feedback_history"; safe_rerun()
    show_header("フィードバック", right_callable=hdr_right)
    st.markdown('<div class="section">', unsafe_allow_html=True)

    key_date = st.session_state.today_date.strftime("%Y-%m-%d")
    meals = st.session_state.app_data.get("meal_data", {}).get(key_date, {"朝食":[],"昼食":[],"夕食":[],"間食":[]})
    age = st.session_state.user_info.get("age", 0)
    gender = st.session_state.user_info.get("gender", "")
    self_esteem = st.session_state.user_info.get("self_esteem_level", "")

    st.subheader(f"{key_date} のフィードバック")
    st.write("食事・プロフィール・自尊感情を踏まえたフィードバックを生成します。")

    nutrient_totals, tendencies = calc_nutrition(meals)

    if st.button("フィードバック生成", key="gen_fb_btn"):
        sel_m = st.session_state.app_data.get("missions", {}).get(key_date, {}).get("selected")
        fb_text = try_generate_feedback(age, gender, self_esteem, meals, selected_mission=sel_m)
        st.session_state.app_data.setdefault("feedback", {})[key_date] = {
            "text": fb_text,
            "meta": {
                "age": age,
                "gender": gender,
                "self_esteem": self_esteem,
                "selected_mission": sel_m,
                "nutrient_totals": nutrient_totals,
                "tendencies": tendencies
            }
        }
        save_app(st.session_state.app_data)
        st.success("フィードバックを生成しました。")
        safe_rerun()

    fb_obj = st.session_state.app_data.get("feedback", {}).get(key_date)
    if fb_obj:
        st.markdown("**生成済みフィードバック**")
        meta = fb_obj.get("meta", {})
        with st.expander("プロフィールと簡易栄養結果（表示）", expanded=True):
            st.write(f"年齢: {meta.get('age', age)}")
            st.write(f"性別: {meta.get('gender', gender)}")
            st.write(f"自尊感情レベル: {meta.get('self_esteem', self_esteem)}")
            selm = meta.get('selected_mission') or 'なし'
            st.write(f"選択ミッション: {selm}")
            nt = meta.get('nutrient_totals') or nutrient_totals
            tend = meta.get('tendencies') or tendencies
            st.write("**簡易栄養合計（内部単位）**")
            st.write(f"タンパク質: {nt.get('タンパク質',nt.get('p',0))}")
            st.write(f"脂質: {nt.get('脂質',nt.get('f',0))}")
            st.write(f"炭水化物: {nt.get('炭水化物',nt.get('c',0))}")
            if tend:
                st.write("**栄養傾向**: " + ", ".join(tend))
            else:
                st.write("栄養傾向: 特に問題なしの可能性があります。")
        st.write("---")
        st.write(fb_obj.get("text",""))

    st.write("---")
    c1,c2,c3 = st.columns(3)
    if c1.button("🍱 食事管理", key="nav_meal_fb"):
        st.session_state.page="meal"; safe_rerun()
    if c2.button("📝 フィードバック", key="nav_feedback_fb"):
        st.session_state.page="feedback"; safe_rerun()
    if c3.button("🎯 今日のミッション", key="nav_today_fb"):
        st.session_state.page="today_mission_display"; safe_rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# 過去のフィードバック画面
# -------------------------
def show_feedback_history():
    show_header("過去のフィードバック")
    st.markdown('<div class="section">', unsafe_allow_html=True)
    feedbacks = st.session_state.app_data.get("feedback", {})
    if not feedbacks:
        st.write("まだフィードバックはありません。")
    else:
        for dt in sorted(feedbacks.keys(), reverse=True):
            st.markdown(f"**{dt}**")
            meta = feedbacks[dt].get('meta', {})
            st.write(f"年齢: {meta.get('age','-')}, 性別: {meta.get('gender','-')}, 自尊感情: {meta.get('self_esteem','-')}")
            nt = meta.get('nutrient_totals') or {}
            if nt:
                st.write(f"タンパク質: {nt.get('タンパク質',0)}, 脂質: {nt.get('脂質',0)}, 炭水化物: {nt.get('炭水化物',0)}")

            md = st.session_state.app_data.get("meal_data", {}).get(dt, {})
            if md:
                st.write("**その日の食事（量つき）**")
                for meal_name, items in md.items():
                    for it in items:
                        if isinstance(it, str):
                            st.write(f"- {meal_name}: {it}（普通）")
                        else:
                            st.write(f"- {meal_name}: {it.get('item', it.get('name',''))}（{it.get('intake','普通')}）")

            st.write(feedbacks[dt].get("text",""))
            st.write("---")
    c1,c2,c3 = st.columns(3)
    if c1.button("🍱 食事管理", key="nav_meal_fbh"):
        st.session_state.page="meal"; safe_rerun()
    if c2.button("📝 フィードバック", key="nav_feedback_fbh"):
        st.session_state.page="feedback"; safe_rerun()
    if c3.button("🎯 今日のミッション", key="nav_today_fbh"):
        st.session_state.page="today_mission_display"; safe_rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# 初回判定・ページ遷移
# -------------------------
def ensure_today_mission():
    today = st.session_state.today_date.strftime("%Y-%m-%d")
    missions = st.session_state.app_data.setdefault("missions", {})
    if today not in missions:
        missions[today] = {
            "auto": try_generate_missions(),
            "custom": [],
            "selected": None,
            "status": {}
        }
        save_app(st.session_state.app_data)
    return missions[today]

if "page" not in st.session_state:
    st.session_state.page = "init_register" if not st.session_state.registered else "self_esteem"

if st.session_state.get("registered") and st.session_state.get("page") == "init_register":
    st.session_state.page = "self_esteem"

page = st.session_state.get("page")
if page == "init_register":
    show_init_register()
elif page == "self_esteem":
    show_self_esteem()
elif page == "mission":
    show_mission()
elif page == "meal":
    if st.session_state.page == "edit_item":
        show_edit_item()
    else:
        show_meal()
elif page == "feedback":
    show_feedback()
elif page == "feedback_history":
    show_feedback_history()
elif page == "today_mission_display":
    show_today_mission_display()
elif page == "mission_history":
    show_mission_history()
else:
    st.write("不明なページです。初期画面を表示します。")
    st.session_state.page = "init_register"
    safe_rerun()