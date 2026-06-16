import streamlit as st
import requests
import pandas as pd
import hashlib
import json
from datetime import datetime, date
import gspread
from google.oauth2.service_account import Credentials

# ─── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="WC 2026 Predictions",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ────────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500;600&display=swap');

/* Base */
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Header strip */
.wc-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    color: white;
    padding: 2rem 2.5rem 1.5rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    border-left: 5px solid #e94560;
}
.wc-header h1 {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 3rem;
    letter-spacing: 3px;
    margin: 0;
    line-height: 1;
    color: #ffffff;
}
.wc-header .subtitle {
    color: #a0b4cc;
    margin-top: 0.3rem;
    font-size: 0.9rem;
    letter-spacing: 1px;
    text-transform: uppercase;
}

/* Match cards */
.match-card {
    background: #ffffff;
    border: 1px solid #e8ecf0;
    border-radius: 10px;
    padding: 1.1rem 1.2rem;
    margin-bottom: 0.8rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s;
}
.match-card:hover { box-shadow: 0 3px 12px rgba(0,0,0,0.10); }
.match-meta {
    font-size: 0.75rem;
    color: #7a8899;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 0.5rem;
}
.match-teams {
    font-size: 1.15rem;
    font-weight: 600;
    color: #1a1a2e;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}
.match-score {
    background: #0f3460;
    color: white;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.9rem;
    font-weight: 700;
    font-family: monospace;
}
.score-tbd {
    background: #e8ecf0;
    color: #7a8899;
}
.badge {
    display: inline-block;
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 20px;
    font-weight: 600;
    letter-spacing: 0.5px;
}
.badge-group { background: #e0f0ff; color: #0f3460; }
.badge-knockout { background: #ffeae8; color: #c0392b; }
.badge-correct { background: #d4edda; color: #155724; }
.badge-pending { background: #fff3cd; color: #856404; }

/* Leaderboard */
.lb-row {
    display: flex;
    align-items: center;
    padding: 0.7rem 1rem;
    border-radius: 8px;
    margin-bottom: 0.4rem;
    background: #f7f9fc;
    border: 1px solid #e8ecf0;
}
.lb-rank {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.4rem;
    color: #a0b4cc;
    width: 2.5rem;
    flex-shrink: 0;
}
.lb-rank.gold { color: #f0c330; }
.lb-rank.silver { color: #a0a0a0; }
.lb-rank.bronze { color: #cd7f32; }
.lb-name { flex: 1; font-weight: 600; color: #1a1a2e; }
.lb-score {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.6rem;
    color: #e94560;
    min-width: 3rem;
    text-align: right;
}

/* Form elements */
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    border-radius: 8px !important;
}

/* Divider accent */
.section-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.6rem;
    letter-spacing: 2px;
    color: #1a1a2e;
    border-bottom: 3px solid #e94560;
    padding-bottom: 0.3rem;
    margin-bottom: 1rem;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #1a1a2e !important;
}
section[data-testid="stSidebar"] * { color: #e0e8f0 !important; }
section[data-testid="stSidebar"] .stTextInput > div > div > input {
    background: #16213e !important;
    border-color: #0f3460 !important;
    color: white !important;
}
section[data-testid="stSidebar"] .stButton > button {
    background: #e94560 !important;
    color: white !important;
    border: none !important;
    width: 100%;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ─── Constants ──────────────────────────────────────────────────────────────────
WC_JSON_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]


# ─── Google Sheets helpers ───────────────────────────────────────────────────────
def get_gspread_client():
    creds_dict = st.secrets.get("GCP_SERVICE_ACCOUNT", None)
    if creds_dict is None:
        return None
    creds = Credentials.from_service_account_info(dict(creds_dict), scopes=SCOPES)
    return gspread.authorize(creds)


def get_spreadsheet(gc):
    spreadsheet_id = st.secrets["SPREADSHEET_ID"]
    return gc.open_by_key(spreadsheet_id)


def get_worksheets(sh):
    users_ws = sh.worksheet("Users")
    preds_ws = sh.worksheet("Predictions")
    return users_ws, preds_ws


def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


def load_users(users_ws):
    data = users_ws.get_all_records()
    return {row["username"]: row for row in data}


def register_user(users_ws, username, password, display_name):
    users = load_users(users_ws)
    if username in users:
        return False, "Username already taken."
    users_ws.append_row([username, hash_password(password), datetime.utcnow().isoformat(), display_name])
    return True, "Account created!"


def login_user(users_ws, username, password):
    users = load_users(users_ws)
    if username not in users:
        return False, "Username not found."
    if users[username]["password_hash"] != hash_password(password):
        return False, "Wrong password."
    return True, users[username]["display_name"]


def load_predictions(preds_ws):
    return preds_ws.get_all_records()


def save_prediction(preds_ws, username, match_id, team1, team2, pred_home, pred_away):
    rows = load_predictions(preds_ws)
    # Check if prediction already exists → update by overwriting
    for i, row in enumerate(rows):
        if row["username"] == username and row["match_id"] == match_id:
            row_number = i + 2  # 1-indexed + header
            preds_ws.update(f"E{row_number}:G{row_number}", [[pred_home, pred_away, datetime.utcnow().isoformat()]])
            return
    # New prediction
    preds_ws.append_row([username, match_id, team1, team2, pred_home, pred_away, datetime.utcnow().isoformat()])


# ─── Match data helpers ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_matches():
    try:
        r = requests.get(WC_JSON_URL, timeout=10)
        r.raise_for_status()
        data = r.json()
        matches = data.get("matches", [])
        # Assign stable IDs
        for i, m in enumerate(matches):
            m["id"] = f"{m.get('date','')}__{m.get('team1','')}__{m.get('team2','')}"
        return matches
    except Exception as e:
        st.error(f"Could not fetch match data: {e}")
        return []


def match_has_result(m):
    return bool(m.get("score") and m["score"].get("ft"))


def get_result(m):
    if not match_has_result(m):
        return None
    ft = m["score"]["ft"]
    return int(ft[0]), int(ft[1])


def parse_match_date(m):
    try:
        return date.fromisoformat(m["date"])
    except Exception:
        return date.max


def is_upcoming(m):
    return not match_has_result(m) and parse_match_date(m) >= date.today()


def is_group_stage(m):
    return "group" in m and m.get("round", "").lower().startswith("matchday")


# ─── Session state init ─────────────────────────────────────────────────────────
for key, default in [("logged_in", False), ("username", ""), ("display_name", ""), ("page", "matches")]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ WC 2026")
    st.markdown("---")

    gc = get_gspread_client()
    sheets_ok = gc is not None

    if not sheets_ok:
        st.warning("Add Google Sheets credentials to `.streamlit/secrets.toml` to enable accounts & predictions.")

    if st.session_state.logged_in:
        st.success(f"👤 {st.session_state.display_name}")
        st.markdown("---")
        for label, page in [
            ("📅 Matches & Predictions", "matches"),
            ("🏆 Leaderboard", "leaderboard"),
            ("👤 My Predictions", "mypreds"),
        ]:
            if st.button(label, key=f"nav_{page}"):
                st.session_state.page = page
                st.rerun()
        st.markdown("---")
        if st.button("Sign out"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.display_name = ""
            st.rerun()
    else:
        tab = st.radio("", ["Sign in", "Register"], horizontal=True)
        if sheets_ok:
            sh = get_spreadsheet(gc)
            users_ws, preds_ws = get_worksheets(sh)

            if tab == "Sign in":
                u = st.text_input("Username", key="login_u")
                p = st.text_input("Password", type="password", key="login_p")
                if st.button("Sign in"):
                    ok, msg = login_user(users_ws, u.strip(), p)
                    if ok:
                        st.session_state.logged_in = True
                        st.session_state.username = u.strip()
                        st.session_state.display_name = msg
                        st.session_state.page = "matches"
                        st.rerun()
                    else:
                        st.error(msg)
            else:
                dn = st.text_input("Display name", key="reg_dn")
                u = st.text_input("Username", key="reg_u")
                p = st.text_input("Password", type="password", key="reg_p")
                if st.button("Create account"):
                    ok, msg = register_user(users_ws, u.strip(), p, dn.strip() or u.strip())
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
        else:
            st.info("Connect Google Sheets to enable login.")
        st.markdown("---")
        if st.button("📅 Browse matches (guest)", key="nav_guest"):
            st.session_state.page = "matches"
            st.rerun()

# ─── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="wc-header">
  <h1>WORLD CUP 2026</h1>
  <div class="subtitle">Canada · USA · Mexico &nbsp;·&nbsp; June 11 – July 19, 2026</div>
</div>
""",
    unsafe_allow_html=True,
)

# ─── Load data ──────────────────────────────────────────────────────────────────
matches = fetch_matches()

if gc is not None and st.session_state.logged_in:
    sh = get_spreadsheet(gc)
    users_ws, preds_ws = get_worksheets(sh)
    all_predictions = load_predictions(preds_ws)
    user_preds = {r["match_id"]: r for r in all_predictions if r["username"] == st.session_state.username}
else:
    all_predictions = []
    user_preds = {}

# ─── Page: Matches & Predictions ────────────────────────────────────────────────
if st.session_state.page == "matches":
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown('<div class="section-title">MATCH CALENDAR</div>', unsafe_allow_html=True)

        # Filter controls
        fc1, fc2 = st.columns(2)
        with fc1:
            show_filter = st.selectbox("Show", ["All matches", "Upcoming only", "Completed only"], key="mfilter")
        with fc2:
            stage_filter = st.selectbox("Stage", ["All stages", "Group stage", "Knockout stage"], key="sfilter")

        if matches:
            filtered = matches
            if show_filter == "Upcoming only":
                filtered = [m for m in filtered if not match_has_result(m)]
            elif show_filter == "Completed only":
                filtered = [m for m in filtered if match_has_result(m)]
            if stage_filter == "Group stage":
                filtered = [m for m in filtered if is_group_stage(m)]
            elif stage_filter == "Knockout stage":
                filtered = [m for m in filtered if not is_group_stage(m)]

            # Group by date
            by_date = {}
            for m in filtered:
                d = m.get("date", "TBD")
                by_date.setdefault(d, []).append(m)

            for d in sorted(by_date.keys()):
                try:
                    pretty_date = datetime.strptime(d, "%Y-%m-%d").strftime("%A, %B %d")
                except:
                    pretty_date = d
                st.markdown(f"**{pretty_date}**")

                for m in by_date[d]:
                    mid = m["id"]
                    t1, t2 = m.get("team1", "TBD"), m.get("team2", "TBD")
                    result = get_result(m)
                    stage_badge = "badge-group" if is_group_stage(m) else "badge-knockout"
                    stage_label = m.get("group", m.get("round", ""))

                    score_html = ""
                    if result:
                        score_html = f'<span class="match-score">{result[0]} – {result[1]}</span>'
                    else:
                        score_html = '<span class="match-score score-tbd">vs</span>'

                    pred_html = ""
                    if mid in user_preds:
                        p = user_preds[mid]
                        pred_html = f'<span class="badge badge-pending" style="margin-left:0.5rem">Your pick: {p["pred_home"]}–{p["pred_away"]}</span>'
                        if result and int(p["pred_home"]) == result[0] and int(p["pred_away"]) == result[1]:
                            pred_html = f'<span class="badge badge-correct" style="margin-left:0.5rem">✓ {p["pred_home"]}–{p["pred_away"]}</span>'

                    st.markdown(
                        f"""
<div class="match-card">
  <div class="match-meta">
    <span class="badge {stage_badge}">{stage_label}</span>
    &nbsp;{m.get("ground", "")} &nbsp;·&nbsp; {m.get("time", "")}
  </div>
  <div class="match-teams">
    {t1} &nbsp;{score_html}&nbsp; {t2}
    {pred_html}
  </div>
</div>""",
                        unsafe_allow_html=True,
                    )
        else:
            st.info("No match data available right now.")

    with col_right:
        st.markdown('<div class="section-title">MAKE A PREDICTION</div>', unsafe_allow_html=True)

        if not st.session_state.logged_in:
            st.info("Sign in to submit predictions.")
        else:
            upcoming = [m for m in matches if is_upcoming(m)]
            if not upcoming:
                st.info("No upcoming matches to predict.")
            else:
                match_options = {f"{m['team1']} vs {m['team2']} ({m['date']})": m for m in upcoming}
                chosen_label = st.selectbox("Pick a match", list(match_options.keys()))
                chosen = match_options[chosen_label]
                mid = chosen["id"]

                existing = user_preds.get(mid, {})
                default_home = int(existing.get("pred_home", 0)) if existing else 0
                default_away = int(existing.get("pred_away", 0)) if existing else 0

                st.markdown(f"**{chosen['team1']}** vs **{chosen['team2']}**")
                c1, c2 = st.columns(2)
                with c1:
                    ph = st.number_input(chosen["team1"], min_value=0, max_value=20, value=default_home, key="ph")
                with c2:
                    pa = st.number_input(chosen["team2"], min_value=0, max_value=20, value=default_away, key="pa")

                btn_label = "Update prediction" if mid in user_preds else "Submit prediction"
                if st.button(btn_label, type="primary"):
                    save_prediction(preds_ws, st.session_state.username, mid, chosen["team1"], chosen["team2"], ph, pa)
                    st.success(f"Prediction saved: {chosen['team1']} {ph}–{pa} {chosen['team2']}")
                    st.rerun()

                if existing:
                    st.caption(f"Current pick: {existing['pred_home']}–{existing['pred_away']}")

# ─── Page: Leaderboard ──────────────────────────────────────────────────────────
elif st.session_state.page == "leaderboard":
    st.markdown('<div class="section-title">LEADERBOARD</div>', unsafe_allow_html=True)
    st.caption("Only exact score predictions count.")

    if not all_predictions:
        st.info("No predictions submitted yet.")
    else:
        result_map = {m["id"]: get_result(m) for m in matches if match_has_result(m)}

        scores = {}
        for row in all_predictions:
            mid = row["match_id"]
            result = result_map.get(mid)
            if result is None:
                continue
            try:
                ph, pa = int(row["pred_home"]), int(row["pred_away"])
            except (ValueError, KeyError):
                continue
            if ph == result[0] and pa == result[1]:
                scores[row["username"]] = scores.get(row["username"], 0) + 1

        if not scores:
            st.info("No exact score predictions matched yet — keep checking back!")
        else:
            sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
            rank_classes = ["gold", "silver", "bronze"]
            rank_medals = ["🥇", "🥈", "🥉"]

            all_users = load_users(users_ws)
            for i, (uname, pts) in enumerate(sorted_scores):
                rank_cls = rank_classes[i] if i < 3 else ""
                medal = rank_medals[i] if i < 3 else str(i + 1)
                dname = all_users.get(uname, {}).get("display_name", uname)
                st.markdown(
                    f"""
<div class="lb-row">
  <div class="lb-rank {rank_cls}">{medal}</div>
  <div class="lb-name">{dname}</div>
  <div class="lb-score">{pts}</div>
</div>""",
                    unsafe_allow_html=True,
                )

# ─── Page: My Predictions ───────────────────────────────────────────────────────
elif st.session_state.page == "mypreds":
    st.markdown('<div class="section-title">MY PREDICTIONS</div>', unsafe_allow_html=True)

    if not user_preds:
        st.info("You haven't made any predictions yet.")
    else:
        result_map = {m["id"]: (get_result(m), m) for m in matches}

        rows_out = []
        for mid, pred in user_preds.items():
            res_tuple = result_map.get(mid)
            result, match_obj = res_tuple if res_tuple else (None, None)
            match_result = result
            ph, pa = int(pred["pred_home"]), int(pred["pred_away"])

            if match_result is None:
                status = "⏳ Pending"
                correct = False
            elif ph == match_result[0] and pa == match_result[1]:
                status = "✅ Exact!"
                correct = True
            else:
                status = f"❌ ({match_result[0]}–{match_result[1]})"
                correct = False

            rows_out.append(
                {
                    "Match": f"{pred['team1']} vs {pred['team2']}",
                    "Your Pick": f"{ph}–{pa}",
                    "Result": f"{match_result[0]}–{match_result[1]}" if match_result else "—",
                    "Status": status,
                }
            )

        df = pd.DataFrame(rows_out)
        st.dataframe(df, use_container_width=True, hide_index=True)

        total_correct = sum(1 for r in rows_out if "Exact" in r["Status"])
        total_done = sum(1 for r in rows_out if "Pending" not in r["Status"])
        st.markdown(f"**{total_correct}** exact score(s) out of **{total_done}** completed match(es).")
