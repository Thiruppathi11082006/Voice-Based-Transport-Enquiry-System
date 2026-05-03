import hashlib

from db import run_query


ADMIN_PASSWORD = "110806"


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def register_user(username, password):
    if run_query("SELECT user_id FROM users WHERE username = %s", (username,)):
        return False, "Username already exists."
    success = run_query(
        "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
        (username, hash_password(password)),
        fetch=False,
    )
    return (True, "Registration successful. You can log in now.") if success else (False, "Unable to register user.")


def authenticate_user(username, password):
    result = run_query(
        "SELECT user_id, username FROM users WHERE username = %s AND password_hash = %s",
        (username, hash_password(password)),
    )
    if not result:
        return None
    run_query("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = %s", (result[0]["user_id"],), fetch=False)
    return result[0]


def update_user_account(user_id, username, password=""):
    if run_query("SELECT user_id FROM users WHERE username = %s AND user_id <> %s", (username, int(user_id))):
        return False, "That username is already used by another account."
    query = "UPDATE users SET username = %s WHERE user_id = %s"
    params = (username, int(user_id))
    if password.strip():
        query = "UPDATE users SET username = %s, password_hash = %s WHERE user_id = %s"
        params = (username, hash_password(password), int(user_id))
    success = run_query(query, params, fetch=False)
    return (True, f"User ID {user_id} updated successfully.") if success else (False, "Unable to update user.")


def delete_user_account(user_id):
    success = run_query("DELETE FROM users WHERE user_id = %s", (int(user_id),), fetch=False)
    return (True, f"User ID {user_id} deleted successfully.") if success else (False, "Unable to delete user.")
