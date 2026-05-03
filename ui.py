import base64
from pathlib import Path

import pandas as pd
import streamlit as st

from auth import ADMIN_PASSWORD, authenticate_user, register_user
from db import fetch_recent_enquiries, fetch_route_options, fetch_search_results, fetch_stats, fetch_supported_cities, fetch_transport_table, fetch_users


MENU_OPTIONS = ["Voice Enquiry", "Manual Enquiry", "DBMS Analytics", "Admin"]
MENU_ICONS = {
    "Voice Enquiry": "\U0001F3A4",
    "Manual Enquiry": "\U0001F9ED",
    "DBMS Analytics": "\U0001F4CA",
    "Admin": "\U0001F6E0",
}


def load_background_image():
    image_path = Path(__file__).parent / "assets" / "transport_bg.svg"
    return "" if not image_path.exists() else base64.b64encode(image_path.read_bytes()).decode("utf-8")


def apply_styles():
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background: linear-gradient(rgba(247,251,255,.14), rgba(238,245,255,.20)), url("data:image/svg+xml;base64,__BG__"); background-size: cover; background-position: center top; background-attachment: fixed; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #07152c 0%, #14325e 100%); }
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span, [data-testid="stSidebar"] div, [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] strong { color: #fff !important; -webkit-text-fill-color: #fff !important; opacity: 1 !important; }
    [data-testid="stAppViewContainer"] p, [data-testid="stAppViewContainer"] li, [data-testid="stAppViewContainer"] label, [data-testid="stAppViewContainer"] span, [data-testid="stAppViewContainer"] .stMarkdown, [data-testid="stAppViewContainer"] .stText, [data-testid="stAppViewContainer"] .stCaption, [data-testid="stAppViewContainer"] div:not(.hero):not(.hero *):not([data-testid="stSidebar"] *):not([data-testid="stMetric"] *), [data-testid="stAppViewContainer"] label p { color: #0f172a !important; }
    .hero, .hero *,.pill { color: #fff !important; -webkit-text-fill-color: #fff !important; opacity: 1 !important; }
    [data-testid="stMetric"] { background: rgba(255,255,255,.55); border: 1px solid rgba(15,23,42,.08); border-radius: 16px; padding: .8rem 1rem; }
    [data-testid="stMetricLabel"] { color: #475569 !important; }
    [data-testid="stMetricValue"] { color: #0f172a !important; font-family: 'Space Grotesk', sans-serif !important; font-weight: 700 !important; }
    [data-baseweb="select"] *, [data-baseweb="slider"] *, .stMultiSelect *, .stSelectbox *, .stSlider *, .stTextInput *, .stNumberInput *, .stTextArea * { color: #0f172a !important; }
    [data-baseweb="select"] > div, [data-baseweb="select"] div[role="button"], .stSelectbox [data-baseweb="select"] > div, .stMultiSelect [data-baseweb="select"] > div, [data-testid="stTextInputRootElement"] input, [data-testid="stNumberInput"] input, textarea { background: #fff !important; color: #0f172a !important; border: 1px solid rgba(15,23,42,.12) !important; }
    [data-testid="stTextInputRootElement"] label, [data-testid="stNumberInput"] label, .stSelectbox label, .stMultiSelect label, .stSlider label, [data-testid="stAlert"] * { color: #0f172a !important; font-weight: 600 !important; }
    [data-testid="stTextInputRootElement"] button, [data-testid="stTextInputRootElement"] button svg, [data-testid="stTextInputRootElement"] [role="button"], [data-testid="stTextInputRootElement"] [role="button"] svg, .stButton > button, .stForm button, .stForm button *, .stFormSubmitButton button, .stFormSubmitButton button * { color: #fff !important; fill: #fff !important; stroke: #fff !important; -webkit-text-fill-color: #fff !important; }
    [data-testid="stTextInputRootElement"] button, [data-testid="stTextInputRootElement"] [role="button"] { background: #1e293b !important; border-radius: 10px !important; }
    [data-testid="stDataFrame"] [role="grid"] { background: #fff !important; color: #0f172a !important; }
    [data-testid="stDataFrame"] [role="columnheader"] { background: #dbeafe !important; color: #0f172a !important; font-weight: 700 !important; }
    [data-testid="stDataFrame"] [role="gridcell"], [data-testid="stDataFrame"] * { background: #f8fbff !important; color: #0f172a !important; }
    .hero { background: linear-gradient(135deg, #07152c 0%, #16448f 58%, #e67f22 130%); padding: 2rem 2.2rem; border-radius: 24px; box-shadow: 0 24px 60px rgba(7,21,44,.22); margin-bottom: 1rem; }
    .hero-kicker { text-transform: uppercase; letter-spacing: .14em; opacity: .82; font-size: .82rem; }
    .hero-title { font-family: 'Space Grotesk', sans-serif; font-size: 2.6rem; font-weight: 700; margin: .6rem 0; }
    .hero-copy { max-width: 780px; opacity: .92; }
    .pills,.badges { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1rem; }
    .pill,.badge { background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.18); padding: .4rem .8rem; border-radius: 999px; font-size: .88rem; }
    .badge { background: #eaf2ff; color: #1847a4 !important; border: none; font-size: .82rem; font-weight: 600; margin-top: 0; }
    .card,.feature,.mini,.route-card,.sidebar-panel,.profile-tile,.login-card { border-radius: 20px; border: 1px solid rgba(15,23,42,.06); box-shadow: 0 14px 32px rgba(15,23,42,.06); }
    .card { background: rgba(255,255,255,.82); padding: 1.05rem; margin-bottom: 1rem; }
    .login-card { max-width: 620px; margin: 1rem auto 0; background: rgba(255,255,255,.94); padding: 1.25rem 1.3rem 1rem; box-shadow: 0 24px 50px rgba(15,23,42,.14); }
    .login-title,.feature-title,.section-title,.route-title,.sidebar-brand { font-family: 'Space Grotesk', sans-serif; font-weight: 700; color: #0f172a; }
    .login-title { font-size: 1.55rem; margin-bottom: .3rem; }
    .login-copy,.feature-copy,.section-copy,.route-meta,.mini-label { color: #64748b; }
    .feature { background: linear-gradient(180deg, #fff, #f6faff); padding: 1rem; min-height: 150px; }
    .route-card { background: linear-gradient(180deg, #fff, #f7fbff); padding: 1rem; margin-bottom: .8rem; }
    .route-title { font-size: 1.03rem; }
    .route-meta { font-size: .92rem; margin: .25rem 0 .45rem; }
    .mini { background: rgba(255,255,255,.72); padding: .85rem; }
    .mini-value { font-family: 'Space Grotesk', sans-serif; font-size: 1.45rem; font-weight: 700; color: #0f172a; }
    .city-list { margin: .35rem 0 0; padding-left: 1rem; }
    .city-list li { color: #0f172a !important; margin-bottom: .4rem; font-weight: 600; }
    .sidebar-panel,.profile-tile { background: linear-gradient(180deg, rgba(255,255,255,.10), rgba(255,255,255,.04)); border-color: rgba(255,255,255,.10); padding: .85rem .9rem; margin-bottom: .9rem; }
    .sidebar-heading,.profile-label { color: rgba(255,255,255,.82); font-size: .82rem; letter-spacing: .12em; text-transform: uppercase; margin-bottom: .55rem; }
    .sidebar-brand { color: #fff; font-size: 1.2rem; line-height: 1.3; }
    .sidebar-subtext,.profile-role { color: rgba(255,255,255,.88); font-size: .93rem; margin-top: .35rem; }
    .profile-tile { display: flex; align-items: center; gap: .8rem; }
    .profile-icon { width: 42px; height: 42px; border-radius: 50%; background: linear-gradient(135deg, #f97316, #fb923c); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; font-weight: 700; flex-shrink: 0; }
    .profile-name { color: #fff; font-size: 1rem; font-weight: 700; }
    [data-testid="stSidebar"] .stButton > button { border-radius: 10px !important; border: 1px solid rgba(255,255,255,.16) !important; background: rgba(255,255,255,.08) !important; min-height: 2.35rem !important; font-size: .95rem !important; text-align: left !important; justify-content: flex-start !important; padding: .35rem .8rem !important; box-shadow: none !important; }
    [data-testid="stSidebar"] .stButton > button:hover { background: rgba(255,255,255,.16) !important; border-color: rgba(255,255,255,.28) !important; }
    [data-testid="stSidebar"] .stButton > button[kind="primary"] { background: linear-gradient(90deg, #f97316, #fb923c) !important; border-color: transparent !important; }
    </style>
    """.replace("__BG__", load_background_image())
    st.markdown(css, unsafe_allow_html=True)


def init_session_state():
    defaults = {
        "login": False,
        "role": "",
        "username": "",
        "current_menu": "Voice Enquiry",
        "sidebar_expanded": True,
        "search_active": False,
        "src": None,
        "dst": None,
        "voice_text": "",
        "last_search_count": 0,
        "last_search_mode": "manual",
        "last_logged_key": None,
        "last_auto_spoken_key": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def clear_caches(*funcs):
    for func in funcs:
        try:
            func.clear()
        except Exception:
            pass


def clear_transport_caches():
    clear_caches(fetch_transport_table, fetch_route_options, fetch_supported_cities, fetch_search_results, fetch_stats)


def rerun_after(message, *funcs):
    clear_caches(*funcs)
    st.success(message)
    st.rerun()


def rerun_after_transport_change(message):
    clear_transport_caches()
    st.success(message)
    st.rerun()


def hero(title, copy, pills):
    pill_markup = "".join(f"<span class='pill'>{item}</span>" for item in pills)
    st.markdown(f"<div class='hero'><div class='hero-kicker'>DBMS Project Showcase</div><div class='hero-title'>{title}</div><div class='hero-copy'>{copy}</div><div class='pills'>{pill_markup}</div></div>", unsafe_allow_html=True)


def section(title, copy):
    st.markdown(f"<div class='section-title'>{title}</div><div class='section-copy'>{copy}</div>", unsafe_allow_html=True)


def visible_table(df):
    return df if isinstance(df, pd.DataFrame) else pd.DataFrame(df)


def render_table(df):
    table_df = visible_table(df)
    if isinstance(table_df, pd.DataFrame):
        st.table(table_df.reset_index(drop=True))
    else:
        st.table(pd.DataFrame(table_df).reset_index(drop=True))


def score_route(distance_km, duration_min, fare, vehicle_type):
    speed = distance_km / duration_min if duration_min else 0
    raw = 60 + (7 if vehicle_type.lower() == "train" else 4) + min(speed * 8, 16) - min(float(fare) / 45, 16)
    return max(62, min(96, round(raw)))


def enrich_results(results, route_data):
    df = pd.DataFrame(results)
    if df.empty:
        return df
    visible_keys = [col for col in ["vehicle_name", "vehicle_type", "source", "destination", "departure_time", "fare"] if col in df.columns]
    df = df.drop_duplicates(subset=visible_keys or None).copy()
    df["distance_km"] = round(route_data["distance_km"], 1)
    df["duration_min"] = round(route_data["duration_min"])
    df["fare_numeric"] = pd.to_numeric(df["fare"], errors="coerce").fillna(0)
    df["fare_display"] = df["fare_numeric"].apply(lambda value: f"Rs. {value:,.2f}")
    df["comfort_score"] = df.apply(lambda row: score_route(row["distance_km"], row["duration_min"], row["fare_numeric"], row["vehicle_type"]), axis=1)
    df["departure_time"] = df["departure_time"].astype(str)
    return df


def format_results_table(df):
    if df.empty:
        return df
    return df[["transport_id", "vehicle_name", "vehicle_type", "source", "destination", "departure_time", "fare_display", "comfort_score"]].rename(
        columns={
            "transport_id": "Transport ID",
            "vehicle_name": "Vehicle Name",
            "vehicle_type": "Type",
            "source": "Source",
            "destination": "Destination",
            "departure_time": "Departure Time",
            "fare_display": "Fare",
            "comfort_score": "Smart Score",
        }
    )


def build_voice_response(src, dst, filtered_df, route_data):
    if filtered_df.empty:
        return f"No transport options were found from {src.title()} to {dst.title()}. Please try another route or adjust your search."
    best = filtered_df.iloc[0]
    return (
        f"Search results for {src.title()} to {dst.title()}. I found {len(filtered_df)} transport options. "
        f"The best option is {best['vehicle_name']} {best['vehicle_type']}, departing at {best['departure_time']}, "
        f"with fare {int(best['fare_numeric'])} rupees. Estimated route distance is {route_data['distance_km']:.1f} kilometers "
        f"and travel time is {route_data['duration_min']:.0f} minutes."
    )


def speak_text(text, auto_speak=False, button_key="speak_result"):
    safe_text = text.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    if auto_speak:
        st.components.v1.html(f"<script>const t=`{safe_text}`;window.speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(t);u.rate=1;u.pitch=1;window.speechSynthesis.speak(u);</script>", height=0)
    if st.button("Speak Results", key=button_key, use_container_width=True):
        st.components.v1.html(f"<script>const u=new SpeechSynthesisUtterance(`{safe_text}`);u.rate=1;u.pitch=1;window.speechSynthesis.cancel();window.speechSynthesis.speak(u);</script>", height=0)


def stop_speech():
    st.components.v1.html("<script>window.speechSynthesis.cancel();</script>", height=0)


def render_result_cards(df):
    for _, row in df.iterrows():
        st.markdown(
            f"<div class='route-card'><div class='route-title'>{row['vehicle_name']} ({row['vehicle_type']})</div><div class='route-meta'>{row['source'].title()} to {row['destination'].title()} - Departure {row['departure_time']}</div><div class='badges'><span class='badge'>{row['fare_display']}</span><span class='badge'>Smart Score {row['comfort_score']}</span><span class='badge'>{row['duration_min']} min</span></div></div>",
            unsafe_allow_html=True,
        )


def render_login():
    hero("Voice-Based Transport Enquiry System", "A unique DBMS mini-project that combines voice search, route comparison, enquiry logging, transport analytics, and admin-side data management.", ["Voice enquiry", "MySQL-backed history", "Route intelligence", "Admin dashboard"])
    _, center, _ = st.columns([1.1, 1.6, 1.1])
    with center:
        st.markdown("<div class='login-card'>", unsafe_allow_html=True)
        st.markdown("<div class='login-title'>Project Access Dashboard</div><div class='login-copy'>Register once, then sign in anytime with the same username and password. Admin access stays separate.</div>", unsafe_allow_html=True)
        tab1, tab2, tab3 = st.tabs(["User Login", "Register", "Admin Login"])
        with tab1:
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login as User", use_container_width=True, type="primary"):
                if not username.strip() or not password.strip():
                    st.warning("Enter both username and password.")
                else:
                    user = authenticate_user(username.strip(), password)
                    if user:
                        st.session_state.login, st.session_state.role, st.session_state.username = True, "user", user["username"]
                        st.rerun()
                    st.error("Invalid username or password.") if not user else None
        with tab2:
            username = st.text_input("Create Username", key="register_username")
            password = st.text_input("Create Password", type="password", key="register_password")
            confirm = st.text_input("Confirm Password", type="password", key="confirm_password")
            if st.button("Register User", use_container_width=True):
                if not username.strip() or not password.strip():
                    st.warning("Username and password are required.")
                elif password != confirm:
                    st.warning("Passwords do not match.")
                else:
                    ok, message = register_user(username.strip(), password)
                    st.success(message) if ok else st.error(message)
                    if ok:
                        clear_caches(fetch_users)
        with tab3:
            password = st.text_input("Admin Password", type="password", key="admin_password")
            if st.button("Admin Login", use_container_width=True):
                if password == ADMIN_PASSWORD:
                    st.session_state.login, st.session_state.role, st.session_state.username = True, "admin", "admin"
                    st.rerun()
                st.error("Incorrect admin password.") if password != ADMIN_PASSWORD else None
        st.markdown("</div>", unsafe_allow_html=True)
    section("Why This Project Feels Unique", "It is not just a transport search screen. Every enquiry can be stored in MySQL, analyzed later, and used to show user behavior and popular routes.")
    for col, item in zip(st.columns(3), [("Voice Module", "Recognizes spoken source and destination names for transport enquiry."), ("DBMS Core", "Stores routes, transport records, and enquiry history for reporting."), ("Analytics Layer", "Shows popular routes, usage mode split, and recent enquiry activity.")]):
        with col:
            st.markdown(f"<div class='feature'><div class='feature-title'>{item[0]}</div><div class='feature-copy'>{item[1]}</div></div>", unsafe_allow_html=True)


def render_sidebar():
    expanded = st.session_state.sidebar_expanded
    if not expanded:
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"] { min-width: 78px !important; max-width: 78px !important; }
            [data-testid="stSidebar"] .stButton > button { background: transparent !important; border: none !important; min-height: 4.35rem !important; box-shadow: none !important; justify-content: center !important; padding: 0.1rem !important; font-size: 2.55rem !important; line-height: 1 !important; }
            [data-testid="stSidebar"] .stButton > button[kind="primary"] { background: transparent !important; color: #fb923c !important; }
            [data-testid="stSidebar"] hr { margin: 0.9rem 0 !important; }
            </style>
            """,
            unsafe_allow_html=True,
        )
    if st.sidebar.button("\u2630  Menu" if expanded else "\u2630", use_container_width=True, key="sidebar_toggle"):
        st.session_state.sidebar_expanded = not expanded
        st.rerun()
    if expanded:
        st.sidebar.markdown(
            f"""<div class="sidebar-panel"><div class="sidebar-heading">Voice-Based Transport</div><div class="sidebar-brand">Voice-Based Transport Enquiry System</div><div class="sidebar-subtext">DBMS project dashboard</div><div class="sidebar-subtext">Role: <strong>{st.session_state.role.title()}</strong></div></div>
            <div class="profile-tile"><div class="profile-icon">U</div><div><div class="profile-label">Logged In User</div><div class="profile-name">{st.session_state.username or 'Guest'}</div><div class="profile-role">{st.session_state.role.title()}</div></div></div>
            <div class='sidebar-heading'>Navigation</div>""",
            unsafe_allow_html=True,
        )
    for option in MENU_OPTIONS:
        label = f"{MENU_ICONS[option]}  {option}" if expanded else MENU_ICONS[option]
        if st.sidebar.button(label, use_container_width=True, type="primary" if st.session_state.current_menu == option else "secondary", key=f"nav_{option}"):
            st.session_state.current_menu = option
            st.rerun()
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout" if expanded else "\u21e6", use_container_width=True, key="sidebar_logout"):
        st.session_state.clear()
        init_session_state()
        st.rerun()
    return st.session_state.current_menu
