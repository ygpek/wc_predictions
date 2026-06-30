import streamlit as st
import requests
import pandas as pd
import hashlib
import json
from datetime import datetime, date
import gspread
import os
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
@st.cache_resource
def get_gspread_client():
    service_account_info = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
    ]

    creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)

    return gspread.authorize(creds)


@st.cache_resource
def get_spreadsheet(_gc):
    spreadsheet_id = st.secrets["SPREADSHEET_ID"]
    return _gc.open_by_key(spreadsheet_id)


@st.cache_resource
def get_worksheets(_sh):
    users_ws = _sh.worksheet("Users")
    preds_ws = _sh.worksheet("Predictions")
    return users_ws, preds_ws


def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


@st.cache_data(ttl=60)
def load_users(_users_ws):
    data = _users_ws.get_all_records()
    return {row["username"]: row for row in data}


def register_user(users_ws, username, password, display_name):
    users = load_users(users_ws)
    if username in users:
        return False, "Username already taken."
    users_ws.append_row([username, hash_password(password), datetime.utcnow().isoformat(), display_name])
    load_users.clear()
    return True, "Account created!"


def login_user(users_ws, username, password):
    users = load_users(users_ws)
    if username not in users:
        return False, "Username not found."
    if users[username]["password_hash"] != hash_password(password):
        return False, "Wrong password."
    return True, users[username]["display_name"]


def change_password(users_ws, username, old_password, new_password):
    users = load_users(users_ws)

    for i, row in enumerate(users.values()):
        if row["username"] == username:
            if row["password_hash"] != hash_password(old_password):
                return False, "Current password is incorrect."

            row_number = i + 2  # header offset
            users_ws.update_cell(row_number, 2, hash_password(new_password))
            load_users.clear()
            return True, "Password updated successfully."

    return False, "User not found."


@st.cache_data(ttl=60)
def load_predictions(_preds_ws):
    return _preds_ws.get_all_records()


def save_prediction(preds_ws, username, match_id, team1, team2, pred_home, pred_away, existing_rows=None):
    rows = existing_rows if existing_rows is not None else load_predictions(preds_ws)
    # Check if prediction already exists → update by overwriting
    for i, row in enumerate(rows):
        if row["username"] == username and row["match_id"] == match_id:
            row_number = i + 2  # 1-indexed + header
            preds_ws.update(f"E{row_number}:G{row_number}", [[pred_home, pred_away, datetime.utcnow().isoformat()]])
            load_predictions.clear()
            return
    # New prediction
    preds_ws.append_row([username, match_id, team1, team2, pred_home, pred_away, datetime.utcnow().isoformat()])
    load_predictions.clear()


# ─── Match data helpers ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_matches():
    try:
        r = requests.get(WC_JSON_URL, timeout=10)
        r.raise_for_status()
        data = r.json()
        matches = data.get("matches", [])

        # Assign stable IDs
        for m in matches:
            m["id"] = f"{m.get('date','')}__{m.get('team1','')}__{m.get('team2','')}"

        # Sort by date (safe parsing)
        matches.sort(key=lambda m: datetime.fromisoformat(m["date"]))

        return matches

    except Exception as e:
        st.error(f"Could not fetch match data: {e}")
        return []


def match_has_result(m):
    score = m.get("score") or {}
    return bool(score and (score.get("ft") is not None or score.get("et") is not None or score.get("p") is not None))


def get_result(m):
    score = m.get("score") or {}
    if not score:
        return None

    if score.get("p") is not None:
        base = score.get("et") or score.get("ft")
        if not base:
            return None

        home = safe_int(base[0])
        away = safe_int(base[1])
        if home is None or away is None:
            return None

        p_home = safe_int(score["p"][0])
        p_away = safe_int(score["p"][1])
        if p_home is None or p_away is None:
            return None

        if p_home > p_away:
            home += 1
        elif p_home < p_away:
            away += 1
        return home, away

    if score.get("et") is not None:
        et = score.get("et")
        if et:
            return int(et[0]), int(et[1])

    ft = score.get("ft")
    if ft:
        return int(ft[0]), int(ft[1])

    return None


def parse_match_date(m):
    return datetime.fromisoformat(m["date"]).date()


def is_upcoming(m):
    try:
        return (not match_has_result(m)) and parse_match_date(m) >= date.today()
    except Exception:
        return False


def is_group_stage(m):
    return "group" in m and m.get("round", "").lower().startswith("matchday")


def tournament_finished(matches):
    return bool(matches) and any(match_has_result(m) for m in matches) and not any(is_upcoming(m) for m in matches)


def score_outcome(home, away):
    if home > away:
        return 1
    if home < away:
        return -1
    return 0


def safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def display_name_for(username, users):
    return users.get(username, {}).get("display_name", username)


def build_prediction_results(predictions, matches):
    match_map = {m["id"]: m for m in matches if match_has_result(m)}
    rows = []

    for pred in predictions:
        match = match_map.get(pred.get("match_id"))
        if not match:
            continue

        ph = safe_int(pred.get("pred_home"))
        pa = safe_int(pred.get("pred_away"))
        result = get_result(match)
        if ph is None or pa is None or result is None:
            continue

        rh, ra = result
        rows.append(
            {
                "username": pred.get("username"),
                "match_id": pred.get("match_id"),
                "match_label": f"{match.get('team1', pred.get('team1', ''))} vs {match.get('team2', pred.get('team2', ''))}",
                "date": match.get("date", ""),
                "team1": match.get("team1", pred.get("team1", "")),
                "team2": match.get("team2", pred.get("team2", "")),
                "pred_home": ph,
                "pred_away": pa,
                "result_home": rh,
                "result_away": ra,
                "exact": ph == rh and pa == ra,
                "outcome_correct": score_outcome(ph, pa) == score_outcome(rh, ra),
                "goal_diff_correct": (ph - pa) == (rh - ra),
                "group_stage": is_group_stage(match),
            }
        )

    return rows


def count_by(rows, predicate):
    counts = {}
    for row in rows:
        if predicate(row):
            username = row["username"]
            counts[username] = counts.get(username, 0) + 1
    return counts


def max_count_items(counts):
    if not counts:
        return []
    best = max(counts.values())
    if best <= 0:
        return []
    return sorted((username, value) for username, value in counts.items() if value == best)


def longest_streak(rows, predicate):
    by_user = {}
    for row in sorted(rows, key=lambda r: (r["date"], r["match_id"])):
        by_user.setdefault(row["username"], []).append(row)

    streaks = {}
    for username, user_rows in by_user.items():
        current = 0
        best = 0
        for row in user_rows:
            if predicate(row):
                current += 1
                best = max(best, current)
            else:
                current = 0
        if best > 0:
            streaks[username] = best
    return streaks


def summarize_match_exact_hits(rows):
    by_match = {}
    for row in rows:
        by_match.setdefault(row["match_id"], {"label": row["match_label"], "exact_users": set(), "total": 0})
        by_match[row["match_id"]]["total"] += 1
        if row["exact"]:
            by_match[row["match_id"]]["exact_users"].add(row["username"])
    return by_match


def tournament_champion(matches):
    completed = [m for m in matches if match_has_result(m)]
    if not completed:
        return None

    final_match = sorted(completed, key=lambda m: m.get("date", ""))[-1]
    result = get_result(final_match)
    if result is None or result[0] == result[1]:
        return None
    return final_match.get("team1") if result[0] > result[1] else final_match.get("team2")


# ─── Session state init ─────────────────────────────────────────────────────────
for key, default in [("logged_in", False), ("username", ""), ("display_name", ""), ("page", "matches")]:
    if key not in st.session_state:
        st.session_state[key] = default

matches = fetch_matches()

# ─── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ WC 2026")
    st.markdown("---")

    gc = get_gspread_client()
    sheets_ok = gc is not None

    if not sheets_ok:
        st.warning("Add Google Sheets credentials to `.streamlit/secrets.toml` to enable accounts & predictions.")

    if st.session_state.logged_in:
        sh = get_spreadsheet(gc)
        st.markdown("### 🔐 Account")
        users_ws, preds_ws = get_worksheets(sh)

        with st.expander("Change password"):
            old_pw = st.text_input("Current password", type="password", key="old_pw")
            new_pw = st.text_input("New password", type="password", key="new_pw")
            confirm_pw = st.text_input("Confirm new password", type="password", key="confirm_pw")

            if st.button("Update password"):
                if not old_pw or not new_pw:
                    st.error("Fill in all fields.")
                elif new_pw != confirm_pw:
                    st.error("New passwords do not match.")
                else:
                    ok, msg = change_password(
                        users_ws,
                        st.session_state.username,
                        old_pw,
                        new_pw,
                    )
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        st.success(f"👤 {st.session_state.display_name}")
        st.markdown("---")
        for label, page in [
            ("📅 Matches & Predictions", "matches"),
            ("🏆 Leaderboard", "leaderboard"),
            ("👤 My Predictions", "mypreds"),
            ("👥 All Predictions", "allpreds"),
        ]:
            if st.button(label, key=f"nav_{page}"):
                st.session_state.page = page
                st.rerun()
        if tournament_finished(matches) and st.button("🏁 Tournament Summary", key="nav_summary"):
            st.session_state.page = "summary"
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
        if "mfilter" not in st.session_state:
            st.session_state["mfilter"] = "Upcoming only"
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
            upcoming = [m for m in matches if is_upcoming(m) and m["id"] not in user_preds]

            if not upcoming:
                st.info("No upcoming matches to predict.")
            else:
                match_options = {f"{m['team1']} vs {m['team2']} ({m['date']})": m for m in upcoming}

                chosen_label = st.selectbox("Pick a match", list(match_options.keys()))
                chosen = match_options[chosen_label]
                mid = chosen["id"]
                existing = user_preds.get(mid)

                # 🚫 block if already predicted
                if mid in user_preds:
                    st.warning("You already submitted a prediction for this match.")
                    st.stop()

                st.markdown(f"**{chosen['team1']}** vs **{chosen['team2']}**")

                c1, c2 = st.columns(2)
                with c1:
                    ph = st.number_input(chosen["team1"], min_value=0, max_value=20, value=0, key=f"ph_{mid}")
                with c2:
                    pa = st.number_input(chosen["team2"], min_value=0, max_value=20, value=0, key=f"pa_{mid}")

                if st.button("Submit prediction", type="primary"):
                    save_prediction(
                        preds_ws,
                        st.session_state.username,
                        mid,
                        chosen["team1"],
                        chosen["team2"],
                        ph,
                        pa,
                        existing_rows=all_predictions,
                    )
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

elif st.session_state.page == "allpreds":
    st.markdown('<div class="section-title">ALL PREDICTIONS</div>', unsafe_allow_html=True)

    if not all_predictions:
        st.info("No predictions available yet.")
    else:
        users = sorted(set(r["username"] for r in all_predictions))

        # get display names
        all_users = load_users(users_ws)

        user_labels = {u: all_users.get(u, {}).get("display_name", u) for u in users}

        selected_user = st.selectbox("Select player", options=users, format_func=lambda u: user_labels[u])

        user_data = [r for r in all_predictions if r["username"] == selected_user]

        result_map = {m["id"]: get_result(m) for m in matches}

        rows = []
        for r in user_data:
            mid = r["match_id"]
            match_result = result_map.get(mid)

            ph, pa = int(r["pred_home"]), int(r["pred_away"])

            if match_result is None:
                status = "⏳ Pending"
                result_str = "—"
            elif ph == match_result[0] and pa == match_result[1]:
                status = "✅ Exact"
                result_str = f"{match_result[0]}–{match_result[1]}"
            else:
                status = "❌ Wrong"
                result_str = f"{match_result[0]}–{match_result[1]}"

            rows.append(
                {
                    "Match": f"{r['team1']} vs {r['team2']}",
                    "Prediction": f"{ph}–{pa}",
                    "Result": result_str,
                    "Status": status,
                }
            )

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # quick stats
        total = len(rows)
        exact = sum(1 for r in rows if r["Status"] == "✅ Exact")

        st.markdown(f"**{exact} / {total}** exact predictions")

elif st.session_state.page == "summary":
    st.markdown('<div class="section-title">TOURNAMENT SUMMARY</div>', unsafe_allow_html=True)

    if not tournament_finished(matches):
        st.info("The tournament summary will appear after there are no upcoming matches left.")
    elif not all_predictions:
        st.info("No predictions available for the tournament summary.")
    else:
        all_users = load_users(users_ws)
        result_rows = build_prediction_results(all_predictions, matches)

        if not result_rows:
            st.info("No completed-match predictions available for the tournament summary.")
        else:
            participants = sorted({row["username"] for row in result_rows})
            exact_counts = count_by(result_rows, lambda r: r["exact"])
            completed_counts = count_by(result_rows, lambda r: True)
            standings = sorted(
                [(username, exact_counts.get(username, 0), completed_counts.get(username, 0)) for username in participants],
                key=lambda item: (-item[1], item[0]),
            )

            podium_rows = []
            for rank, (username, exact, completed) in enumerate(standings[:3], start=1):
                podium_rows.append(
                    {
                        "Rank": rank,
                        "Player": display_name_for(username, all_users),
                        "Exact scores": exact,
                        "Completed predictions": completed,
                    }
                )

            st.markdown("### Final top three")
            st.dataframe(pd.DataFrame(podium_rows), use_container_width=True, hide_index=True)

            st.markdown("### Notable results")

            def show_award(title, winners, value_label):
                if not winners:
                    return
                names = ", ".join(display_name_for(username, all_users) for username, _ in winners)
                value = winners[0][1]
                st.markdown(f"**{title}:** {names} ({value} {value_label})")

            exact_by_date = {}
            for row in result_rows:
                if row["exact"]:
                    key = (row["username"], row["date"])
                    exact_by_date[key] = exact_by_date.get(key, 0) + 1
            best_day_counts = {}
            for (username, _match_date), count in exact_by_date.items():
                best_day_counts[username] = max(best_day_counts.get(username, 0), count)
            show_award("Most exact picks in one match day", max_count_items(best_day_counts), "exact picks")

            show_award(
                "Best group-stage predictor",
                max_count_items(count_by(result_rows, lambda r: r["group_stage"] and r["exact"])),
                "exact picks",
            )
            show_award(
                "Best knockout-stage predictor",
                max_count_items(count_by(result_rows, lambda r: (not r["group_stage"]) and r["exact"])),
                "exact picks",
            )

            match_hits = summarize_match_exact_hits(result_rows)
            matches_with_exact = [
                (match_id, data)
                for match_id, data in match_hits.items()
                if len(data["exact_users"]) > 0
            ]
            if matches_with_exact:
                easy_count = max(len(data["exact_users"]) for _match_id, data in matches_with_exact)
                easy_matches = [data for _match_id, data in matches_with_exact if len(data["exact_users"]) == easy_count]
                easy_labels = "; ".join(data["label"] for data in easy_matches[:3])
                st.markdown(f"**Easiest match to predict:** {easy_labels} ({easy_count} exact hits)")

            show_award("Most active predictor", max_count_items(completed_counts), "completed predictions")

            accuracy = {}
            for username in participants:
                completed = completed_counts.get(username, 0)
                if completed:
                    accuracy[username] = round(100 * exact_counts.get(username, 0) / completed, 1)
            show_award("Highest accuracy", max_count_items(accuracy), "% exact")

            show_award(
                "Most correct outcomes without exact score",
                max_count_items(count_by(result_rows, lambda r: r["outcome_correct"] and not r["exact"])),
                "matches",
            )
            show_award(
                "Most correct goal differences without exact score",
                max_count_items(count_by(result_rows, lambda r: r["goal_diff_correct"] and not r["exact"])),
                "matches",
            )

            show_award(
                "Longest exact-score streak",
                max_count_items(longest_streak(result_rows, lambda r: r["exact"])),
                "matches",
            )
            show_award(
                "Longest outcome streak",
                max_count_items(longest_streak(result_rows, lambda r: r["outcome_correct"])),
                "matches",
            )

            champion = tournament_champion(matches)
            if champion:
                champion_rows = [
                    row
                    for row in result_rows
                    if row["team1"] == champion or row["team2"] == champion
                ]
                champion_attempts = count_by(champion_rows, lambda r: True)
                champion_correct = count_by(champion_rows, lambda r: r["outcome_correct"])
                unlucky = {
                    username: attempts
                    for username, attempts in champion_attempts.items()
                    if attempts > 0 and champion_correct.get(username, 0) == 0
                }
                show_award("Unlucky predictor", max_count_items(unlucky), f"missed {champion} outcomes")

            scoreline_counts = {}
            for row in result_rows:
                scoreline = f"{row['pred_home']}-{row['pred_away']}"
                scoreline_counts[scoreline] = scoreline_counts.get(scoreline, 0) + 1
            if scoreline_counts:
                favorite_scoreline = sorted(scoreline_counts.items(), key=lambda item: (-item[1], item[0]))[0]
                st.markdown(f"**Favorite scoreline:** {favorite_scoreline[0]} ({favorite_scoreline[1]} predictions)")
