import pandas as pd
import speech_recognition as sr
import streamlit as st

from auth import delete_user_account, update_user_account
from db import (
    ensure_schema,
    fetch_recent_enquiries,
    fetch_route_options,
    fetch_search_results,
    fetch_stats,
    fetch_supported_cities,
    fetch_transport_table,
    fetch_users,
    run_query,
)
from maps import CITY_COORDS, apply_voice_corrections, extract_cities_from_text, get_route_details, render_route_map
from ui import (
    apply_styles,
    build_voice_response,
    enrich_results,
    format_results_table,
    hero,
    init_session_state,
    render_login,
    render_result_cards,
    render_sidebar,
    render_table,
    rerun_after,
    rerun_after_transport_change,
    section,
    speak_text,
    stop_speech,
    visible_table,
)


st.set_page_config(page_title="Voice-Based Transport Enquiry System", layout="wide", initial_sidebar_state="expanded")
apply_styles()
init_session_state()
ensure_schema()


def supported_cities():
    return fetch_supported_cities(tuple(CITY_COORDS))


def set_search(src, dst, mode="manual", voice_text=""):
    st.session_state.src = src
    st.session_state.dst = dst
    st.session_state.search_active = True
    st.session_state.last_search_mode = mode
    if voice_text:
        st.session_state.voice_text = voice_text


def clear_search(keep_voice_text=False):
    st.session_state.search_active = False
    st.session_state.src = None
    st.session_state.dst = None
    st.session_state.last_search_count = 0
    st.session_state.last_auto_spoken_key = ""
    if not keep_voice_text:
        st.session_state.voice_text = ""


def log_enquiry(src, dst, mode, voice_text, result_count):
    key = (src, dst, mode, voice_text or "")
    if st.session_state.last_logged_key == key:
        return
    success = run_query(
        "INSERT INTO enquiry_logs (source, destination, enquiry_mode, voice_text, result_count) VALUES (%s, %s, %s, %s, %s)",
        (src, dst, mode, voice_text, int(result_count)),
        fetch=False,
    )
    if success:
        st.session_state.last_logged_key = key
        fetch_recent_enquiries.clear()
        fetch_stats.clear()


def render_voice_enquiry():
    stop_speech()
    hero("Voice Enquiry Module", "Speak your route naturally, then let the system identify cities and query the database instantly.", ["Speech recognition", "City correction", "DB search"])
    left, right = st.columns([1.2, 0.8], gap="medium")
    with left:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        section("Start Voice Enquiry", "Example: bus from trichy to chennai")
        if st.button("Start Listening", use_container_width=True, type="primary"):
            recognizer = sr.Recognizer()
            try:
                with sr.Microphone() as source:
                    st.info("Listening for source and destination...")
                    recognizer.adjust_for_ambient_noise(source, duration=1)
                    audio = recognizer.listen(source, phrase_time_limit=6)
                processed = apply_voice_corrections(recognizer.recognize_google(audio))
                st.session_state.voice_text = processed
                st.success(f"Recognized: {processed}")
                src, dst = extract_cities_from_text(processed, supported_cities())
                if src and dst and src != dst:
                    set_search(src, dst, mode="voice", voice_text=processed)
                    st.rerun()
                st.warning("Please say two different supported cities.")
            except sr.UnknownValueError:
                st.error("Could not understand the audio clearly.")
            except sr.RequestError:
                st.error("Speech recognition service is unavailable.")
            except OSError as exc:
                st.error(f"Microphone error: {exc}")
        if st.session_state.voice_text:
            st.info(f"Last voice transcript: {st.session_state.voice_text}")
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        section("Supported Cities", "The current database demo works with these city nodes.")
        st.markdown(f"<ul class='city-list'>{''.join(f'<li>{city.title()}</li>' for city in supported_cities())}</ul>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


def render_manual_enquiry():
    stop_speech()
    hero("Manual Enquiry Module", "Choose source and destination manually and explore the transport results with filters and map support.", ["Planner UI", "Fare filter", "Map view"])
    if st.session_state.search_active:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        section("Planner Docked to Results", "The journey planner is now available in the right-side panel while you scroll through results below.")
        st.info("Use the Quick Re-Search panel on the right side to change source and destination without scrolling back to the top.")
        st.markdown("</div>", unsafe_allow_html=True)
        return
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    section("Journey Planner", "Pick any two different cities and launch the enquiry.")
    cities = supported_cities()
    c1, c2, c3 = st.columns([1, 1, 0.7])
    with c1:
        src = st.selectbox("From", cities)
    with c2:
        dst = st.selectbox("To", cities, index=1 if len(cities) > 1 else 0)
    with c3:
        st.write("")
        st.write("")
        if st.button("Search Transport", use_container_width=True, type="primary"):
            if src == dst:
                st.warning("Please choose different cities.")
            else:
                set_search(src, dst, mode="manual")
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_quick_research_panel(src, dst):
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    section("Quick Re-Search", "Change the route here while staying on the results screen.")
    cities = supported_cities()
    new_src = st.selectbox("From", cities, index=cities.index(src) if src in cities else 0, key="dock_src")
    new_dst = st.selectbox("To", cities, index=cities.index(dst) if dst in cities else min(1, len(cities) - 1), key="dock_dst")
    if st.button("Search Again", use_container_width=True, type="primary", key="dock_search"):
        if new_src == new_dst:
            st.warning("Please choose different cities.")
        else:
            set_search(new_src, new_dst, mode="manual")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_results():
    src, dst = st.session_state.src, st.session_state.dst
    if not src or not dst:
        return
    route_data = get_route_details(src, dst)
    filtered = enrich_results(fetch_search_results(src, dst), route_data)
    st.session_state.last_search_count = len(filtered)
    log_enquiry(src, dst, st.session_state.last_search_mode, st.session_state.voice_text if st.session_state.last_search_mode == "voice" else None, len(filtered))
    hero("Enquiry Results", f"Transport options found for {src.title()} to {dst.title()} with DB-backed result tracking.", ["Stored history", "Smart score", "Live route map"])
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Results", len(filtered))
    m2.metric("Lowest Fare", f"Rs. {filtered['fare_numeric'].min():,.2f}" if not filtered.empty else "Rs. 0.00")
    m3.metric("Distance", f"{route_data['distance_km']:.1f} km")
    m4.metric("Time", f"{route_data['duration_min']:.0f} min")
    f1, f2 = st.columns([1, 1])
    with f1:
        options = sorted(filtered["vehicle_type"].unique().tolist()) if not filtered.empty else []
        selected = st.multiselect("Filter by Type", options, default=options)
    with f2:
        max_fare = float(filtered["fare_numeric"].max()) if not filtered.empty else 100.0
        fare_limit = st.slider("Maximum Fare", 0.0, max(100.0, max_fare), max(100.0, max_fare))
    if not filtered.empty:
        filtered = filtered[filtered["vehicle_type"].isin(selected)] if selected else filtered.iloc[0:0]
        filtered = filtered[filtered["fare_numeric"] <= fare_limit].sort_values(["comfort_score", "fare_numeric"], ascending=[False, True])
    voice_response = build_voice_response(src, dst, filtered, route_data)
    auto_key = f"{src}|{dst}|{st.session_state.last_search_mode}|{len(filtered)}|{voice_response}"
    should_auto = st.session_state.last_auto_spoken_key != auto_key
    if should_auto:
        st.session_state.last_auto_spoken_key = auto_key
    speak_text(voice_response, auto_speak=should_auto, button_key=f"speak_results_{src}_{dst}")

    left, right = st.columns([1.15, 0.95], gap="large")
    with left:
        tab1, tab2, tab3 = st.tabs(["Smart Cards", "Table View", "Enquiry History"])
        with tab1:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            if filtered.empty:
                st.warning("No transport data matched the current filters.")
            else:
                st.success(f"Recommended option: {filtered.iloc[0]['vehicle_name']}")
                render_result_cards(filtered)
            st.markdown("</div>", unsafe_allow_html=True)
        with tab2:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            table_df = format_results_table(filtered)
            if table_df.empty:
                st.warning("No results available.")
            else:
                render_table(table_df)
                st.download_button("Download CSV", table_df.to_csv(index=False).encode("utf-8"), file_name=f"{src}_{dst}_enquiry.csv", mime="text/csv")
            st.markdown("</div>", unsafe_allow_html=True)
        with tab3:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            history_df = pd.DataFrame(fetch_recent_enquiries())
            if history_df.empty:
                st.info("No enquiry history available yet.")
            else:
                render_table(history_df)
            st.markdown("</div>", unsafe_allow_html=True)
    with right:
        render_quick_research_panel(src, dst)
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        section("Live Route Map", "The route map now stays fixed on the right side for immediate visual guidance.")
        st.write(f"From: **{src.title()}**")
        st.write(f"To: **{dst.title()}**")
        st.write(f"Search Mode: **{st.session_state.last_search_mode.title()}**")
        st.write(f"Estimated Distance: **{route_data['distance_km']:.1f} km**")
        st.write(f"Estimated Duration: **{route_data['duration_min']:.0f} min**")
        st.caption("Voice response is enabled. The system can speak the result summary after search.")
        if route_data["distance_km"] == 0:
            st.info("Fallback route line is shown because live route details were unavailable.")
        vehicle_name = filtered.iloc[0]["vehicle_name"] if not filtered.empty else None
        vehicle_type = filtered.iloc[0]["vehicle_type"] if not filtered.empty else None
        render_route_map(route_data, src, dst, key_suffix="sidepanel", vehicle_name=vehicle_name, vehicle_type=vehicle_type)
        st.markdown("</div>", unsafe_allow_html=True)


def render_analytics():
    stop_speech()
    stats = fetch_stats()
    hero("DBMS Analytics Module", "This section makes the project stronger for presentation by showing how the database stores and analyzes enquiry behavior.", ["Popular routes", "Mode usage", "Recent logs"])
    a, b, c = st.columns(3)
    a.metric("Total Routes", stats["routes"])
    b.metric("Transport Records", stats["transport"])
    c.metric("Average Fare", f"Rs. {stats['avg_fare']:,.2f}")
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        section("Enquiry Mode Usage", "Compare how users are querying the system.")
        mode_df = pd.DataFrame(stats["mode_stats"])
        if mode_df.empty:
            st.info("No enquiry logs available yet.")
        else:
            display = mode_df.rename(columns={"enquiry_mode": "Mode", "total": "Count"})
            st.bar_chart(display.set_index("Mode"))
            render_table(display)
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        section("Popular Enquiry Routes", "Most frequently requested source-to-destination pairs from the log table.")
        route_df = pd.DataFrame(stats["popular_enquiries"])
        if route_df.empty:
            st.info("No popular route data available yet.")
        else:
            route_df["Route"] = route_df["source"].str.title() + " to " + route_df["destination"].str.title()
            display = route_df[["Route", "total"]].rename(columns={"total": "Count"})
            st.bar_chart(display.set_index("Route"))
            render_table(display)
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    section("Recent Enquiry Log", "Latest transport enquiries captured in MySQL.")
    recent_df = pd.DataFrame(fetch_recent_enquiries())
    if recent_df.empty:
        st.info("No recent enquiries captured yet.")
    else:
        render_table(recent_df)
    st.markdown("</div>", unsafe_allow_html=True)


def render_admin():
    stop_speech()
    if st.session_state.role != "admin":
        st.error("Admin access only.")
        st.stop()
    hero("Admin Module", "Manage transport records, including adding, updating, and deleting entries with full route visibility.", ["Insert transport", "Update record", "Delete record"])
    records_df, users_df = pd.DataFrame(fetch_transport_table()), pd.DataFrame(fetch_users())
    route_options = fetch_route_options()
    route_labels = {route["route_id"]: f"{route['source'].title()} to {route['destination'].title()} (Route ID: {route['route_id']})" for route in route_options}

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    section("Transport Records", "All transport records now show From and To places directly in the table.")
    if records_df.empty:
        st.info("No transport records available.")
    else:
        render_table(records_df.rename(columns={"transport_id": "Transport ID", "vehicle_name": "Vehicle Name", "vehicle_type": "Vehicle Type", "source": "From", "destination": "To", "route_id": "Route ID", "departure_time": "Departure Time", "fare": "Fare", "seats_available": "Seats", "service_rating": "Rating"}))
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    section("Add New Transport", "Insert a new bus or train record using a route with visible source and destination.")
    with st.form("add_transport_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            manual_id = st.text_input("Transport ID (Optional)", placeholder="Enter manual ID like 101")
            name = st.text_input("Vehicle Name")
            vtype = st.selectbox("Vehicle Type", ["Bus", "Train"])
            route_id = st.selectbox("Select Route", options=list(route_labels.keys()), format_func=lambda item: route_labels[item]) if route_labels else None
        with c2:
            time = st.text_input("Departure Time", placeholder="08:30 AM")
            fare = st.number_input("Fare", min_value=0.0, step=10.0, format="%.2f")
            seats = st.number_input("Seats Available", min_value=0, step=1, value=40)
            rating = st.number_input("Service Rating", min_value=0.0, max_value=5.0, step=0.1, value=4.0, format="%.1f")
        add_submitted = st.form_submit_button("Add Transport", use_container_width=True, type="primary")
    if add_submitted:
        if not route_labels:
            st.warning("No active routes are available. Please add routes in the database first.")
        elif not name.strip() or not time.strip():
            st.warning("Vehicle name and departure time are required.")
        else:
            insert_query = "INSERT INTO transport (vehicle_name, vehicle_type, route_id, departure_time, fare, seats_available, service_rating) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            params = (name.strip(), vtype, int(route_id), time.strip(), fare, int(seats), float(rating))
            if manual_id.strip():
                if not manual_id.strip().isdigit():
                    st.warning("Transport ID must be a valid number.")
                    params = None
                else:
                    insert_query = "INSERT INTO transport (transport_id, vehicle_name, vehicle_type, route_id, departure_time, fare, seats_available, service_rating) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                    params = (int(manual_id.strip()), *params)
            if params and run_query(insert_query, params, fetch=False):
                rerun_after_transport_change("Transport record added successfully.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    section("Update or Delete Transport", "Select a transport ID to edit its details or remove that specific transport record.")
    if records_df.empty:
        st.info("Add a transport record first to use update or delete actions.")
    else:
        selected_id = st.selectbox("Select Transport ID", options=records_df["transport_id"].tolist())
        row = records_df[records_df["transport_id"] == selected_id].iloc[0]
        st.caption(f"Selected route: {row['source'].title()} to {row['destination'].title()} | {row['vehicle_name']} | {row['vehicle_type']}")
        with st.form("update_transport_form"):
            u1, u2 = st.columns(2)
            with u1:
                updated_name = st.text_input("Vehicle Name", value=str(row["vehicle_name"]))
                updated_type = st.selectbox("Vehicle Type", ["Bus", "Train"], index=0 if row["vehicle_type"] == "Bus" else 1, key="update_vehicle_type")
                updated_route = st.selectbox("Route", options=list(route_labels.keys()), index=list(route_labels.keys()).index(int(row["route_id"])) if route_labels else 0, format_func=lambda item: route_labels[item], key="update_route_id") if route_labels else None
            with u2:
                updated_time = st.text_input("Departure Time", value=str(row["departure_time"]))
                updated_fare = st.number_input("Fare", min_value=0.0, step=10.0, value=float(row["fare"]), format="%.2f")
                updated_seats = st.number_input("Seats Available", min_value=0, step=1, value=int(row["seats_available"]))
                updated_rating = st.number_input("Service Rating", min_value=0.0, max_value=5.0, step=0.1, value=float(row["service_rating"]), format="%.1f")
            update_submitted = st.form_submit_button("Update Transport", use_container_width=True)
        if update_submitted:
            if not updated_name.strip() or not updated_time.strip():
                st.warning("Vehicle name and departure time are required for update.")
            elif run_query(
                "UPDATE transport SET vehicle_name = %s, vehicle_type = %s, route_id = %s, departure_time = %s, fare = %s, seats_available = %s, service_rating = %s WHERE transport_id = %s",
                (updated_name.strip(), updated_type, int(updated_route), updated_time.strip(), updated_fare, int(updated_seats), float(updated_rating), int(selected_id)),
                fetch=False,
            ):
                rerun_after_transport_change(f"Transport ID {selected_id} updated successfully.")
        if st.button(f"Delete Transport ID {selected_id}", use_container_width=True) and run_query("DELETE FROM transport WHERE transport_id = %s", (int(selected_id),), fetch=False):
            rerun_after_transport_change(f"Transport ID {selected_id} deleted successfully.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    section("Manage User Accounts", "Admin can review registered users, update usernames or passwords, and delete user accounts.")
    if users_df.empty:
        st.info("No registered users found.")
    else:
        render_table(users_df.rename(columns={"user_id": "User ID", "username": "Username", "created_at": "Created At", "last_login": "Last Login"}))
        user_id = st.selectbox("Select User ID", options=users_df["user_id"].tolist(), key="manage_user_id")
        user = users_df[users_df["user_id"] == user_id].iloc[0]
        with st.form("update_user_form"):
            updated_username = st.text_input("Username", value=str(user["username"]))
            updated_password = st.text_input("New Password (Optional)", type="password", placeholder="Leave blank to keep existing password")
            update_user_submitted = st.form_submit_button("Update User", use_container_width=True)
        if update_user_submitted:
            if not updated_username.strip():
                st.warning("Username cannot be empty.")
            else:
                ok, message = update_user_account(user_id, updated_username.strip(), updated_password)
                if ok:
                    rerun_after(message, fetch_users)
                else:
                    st.warning(message)
        if st.button(f"Delete User ID {user_id}", use_container_width=True, key="delete_user_button"):
            ok, message = delete_user_account(user_id)
            if ok:
                rerun_after(message, fetch_users)
            else:
                st.warning(message)
    st.markdown("</div>", unsafe_allow_html=True)


if not st.session_state.login:
    render_login()
    st.stop()

selected_menu = render_sidebar()
previous_menu = st.session_state.get("last_rendered_menu", selected_menu)
if previous_menu != selected_menu and {previous_menu, selected_menu} & {"Voice Enquiry", "Manual Enquiry"}:
    st.session_state.last_rendered_menu = selected_menu
    clear_search(keep_voice_text=selected_menu == "Voice Enquiry")
    st.rerun()

st.session_state.last_rendered_menu = selected_menu
if selected_menu == "Voice Enquiry":
    render_voice_enquiry()
elif selected_menu == "Manual Enquiry":
    render_manual_enquiry()
elif selected_menu == "DBMS Analytics":
    render_analytics()
elif selected_menu == "Admin":
    render_admin()

if st.session_state.search_active and selected_menu in {"Voice Enquiry", "Manual Enquiry"}:
    st.divider()
    render_results()
