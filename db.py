import mysql.connector
import streamlit as st


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "110806",
    "database": "tn_transport",
}


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def run_query(query, params=None, fetch=True):
    connection = cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params or ())
        if fetch:
            return cursor.fetchall()
        connection.commit()
        return True
    except mysql.connector.Error as exc:
        st.error(f"Database error: {exc}")
        return [] if fetch else False
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def get_table_columns(table_name):
    try:
        return {row["Field"] for row in run_query(f"SHOW COLUMNS FROM {table_name}") if "Field" in row}
    except Exception:
        return set()


def ensure_columns(table_name, column_defs):
    existing = get_table_columns(table_name)
    for column, definition in column_defs.items():
        if column not in existing:
            run_query(f"ALTER TABLE {table_name} ADD COLUMN {column} {definition}", fetch=False)


def ensure_schema():
    run_query(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(64) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP NULL DEFAULT NULL
        )
        """,
        fetch=False,
    )
    run_query(
        """
        CREATE TABLE IF NOT EXISTS enquiry_logs (
            enquiry_id INT AUTO_INCREMENT PRIMARY KEY,
            source VARCHAR(50) NOT NULL,
            destination VARCHAR(50) NOT NULL,
            enquiry_mode VARCHAR(20) NOT NULL,
            voice_text VARCHAR(255),
            result_count INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        fetch=False,
    )
    ensure_columns(
        "enquiry_logs",
        {
            "source": "VARCHAR(50) NOT NULL",
            "destination": "VARCHAR(50) NOT NULL",
            "enquiry_mode": "VARCHAR(20) NOT NULL",
            "voice_text": "VARCHAR(255)",
            "result_count": "INT DEFAULT 0",
            "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        },
    )


@st.cache_data(show_spinner=False, ttl=60)
def fetch_search_results(src, dst):
    return run_query(
        """
        SELECT t.transport_id, t.vehicle_name, t.vehicle_type, r.source, r.destination, t.departure_time, t.fare
        FROM transport t
        JOIN routes r ON t.route_id = r.route_id
        WHERE r.source = %s AND r.destination = %s
        ORDER BY t.departure_time
        """,
        (src, dst),
    )


@st.cache_data(show_spinner=False, ttl=300)
def fetch_transport_table():
    return run_query(
        """
        SELECT
            t.transport_id, t.vehicle_name, t.vehicle_type, r.source, r.destination,
            t.route_id, t.departure_time, t.fare, t.seats_available, t.service_rating
        FROM transport t
        JOIN routes r ON t.route_id = r.route_id
        ORDER BY t.transport_id DESC
        """
    )


@st.cache_data(show_spinner=False, ttl=300)
def fetch_route_options():
    return run_query("SELECT route_id, source, destination FROM routes ORDER BY source, destination")


@st.cache_data(show_spinner=False, ttl=300)
def fetch_supported_cities(known_cities):
    rows = run_query("SELECT source AS city FROM routes UNION SELECT destination AS city FROM routes ORDER BY city")
    known = set(known_cities)
    cities = [row["city"] for row in rows if row["city"] in known]
    return cities if cities else sorted(known)


@st.cache_data(show_spinner=False, ttl=180)
def fetch_users():
    return run_query("SELECT user_id, username, created_at, last_login FROM users ORDER BY username")


@st.cache_data(show_spinner=False, ttl=180)
def fetch_recent_enquiries():
    columns = get_table_columns("enquiry_logs")
    select_cols = [col for col in ["enquiry_id", "source", "destination", "enquiry_mode", "voice_text", "result_count", "created_at"] if col in columns]
    if not select_cols:
        return []
    order_clause = " ORDER BY created_at DESC" if "created_at" in columns else ""
    return run_query(f"SELECT {', '.join(select_cols)} FROM enquiry_logs{order_clause} LIMIT 10")


@st.cache_data(show_spinner=False, ttl=300)
def fetch_stats():
    routes = run_query("SELECT COUNT(*) AS total FROM routes")
    transport = run_query("SELECT COUNT(*) AS total FROM transport")
    avg_fare = run_query("SELECT AVG(fare) AS avg_fare FROM transport")
    mode_stats = run_query("SELECT enquiry_mode, COUNT(*) AS total FROM enquiry_logs GROUP BY enquiry_mode ORDER BY total DESC")
    popular = run_query("SELECT source, destination, COUNT(*) AS total FROM enquiry_logs GROUP BY source, destination ORDER BY total DESC LIMIT 5")
    return {
        "routes": routes[0]["total"] if routes else 0,
        "transport": transport[0]["total"] if transport else 0,
        "avg_fare": round(avg_fare[0]["avg_fare"], 2) if avg_fare and avg_fare[0]["avg_fare"] is not None else 0,
        "mode_stats": mode_stats,
        "popular_enquiries": popular,
    }
