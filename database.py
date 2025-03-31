import sqlite3
import logging
from config import DATABASE_NAME
import threading

logger = logging.getLogger(__name__)

# Use thread-local storage for database connections
local_storage = threading.local()

def get_db_connection():
    """Gets a thread-safe database connection."""
    if not hasattr(local_storage, 'connection'):
        local_storage.connection = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
        local_storage.connection.row_factory = sqlite3.Row # Return rows as dict-like objects
    return local_storage.connection

def close_db_connection():
    """Closes the thread-safe database connection."""
    if hasattr(local_storage, 'connection'):
        local_storage.connection.close()
        del local_storage.connection

def initialize_database():
    """Initializes the database and creates tables if they don't exist."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # User configuration: stores base group and current state
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users_config (
                user_id INTEGER PRIMARY KEY,
                base_group_id INTEGER UNIQUE,
                base_group_name TEXT,
                user_state TEXT  -- e.g., 'idle', 'awaiting_base_forward', 'awaiting_dest_forward'
            )
        """)
        # Destination groups linked to a user
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS destination_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                dest_group_id INTEGER NOT NULL,
                dest_group_name TEXT,
                FOREIGN KEY (user_id) REFERENCES users_config (user_id) ON DELETE CASCADE,
                UNIQUE (user_id, dest_group_id) -- Each user can only add a destination once
            )
        """)
        # Index for faster lookups, especially for conflict checking
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dest_group_id ON destination_groups (dest_group_id);
        """)
        
        # Tabla known_chats para almacenar grupos conocidos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS known_chats (
                chat_id INTEGER PRIMARY KEY,
                chat_title TEXT NOT NULL,
                chat_type TEXT NOT NULL,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        conn.commit()
        logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Database initialization failed: {e}")
        raise # Re-raise the exception to indicate failure
    # Do not close the connection here if using thread-local storage for long-running apps

def set_user_state(user_id: int, state: str | None):
    """Sets the state for a given user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users_config (user_id, user_state) VALUES (?, ?)", (user_id, state))
    cursor.execute("UPDATE users_config SET user_state = ? WHERE user_id = ?", (state, user_id))
    conn.commit()

def get_user_state(user_id: int) -> str | None:
    """Gets the current state for a given user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_state FROM users_config WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result['user_state'] if result else None

def set_base_group(user_id: int, group_id: int, group_name: str):
    """Sets the base group for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Insert or update user config, ensuring user_id exists
        cursor.execute("INSERT OR IGNORE INTO users_config (user_id) VALUES (?)", (user_id,))
        cursor.execute("""
            UPDATE users_config
            SET base_group_id = ?, base_group_name = ?, user_state = 'idle'
            WHERE user_id = ?
        """, (group_id, group_name, user_id))
        conn.commit()
        logger.info(f"User {user_id} set base group to {group_id} ({group_name})")
    except sqlite3.IntegrityError:
        conn.rollback()
        logger.warning(f"Base group {group_id} is already configured by another user.")
        raise ValueError(f"El grupo '{group_name}' (ID: {group_id}) ya está siendo usado como grupo base por otro usuario.")
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Error setting base group for user {user_id}: {e}")
        raise

def get_base_group(user_id: int) -> tuple[int, str] | None:
    """Gets the base group ID and name for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT base_group_id, base_group_name FROM users_config WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return (result['base_group_id'], result['base_group_name']) if result and result['base_group_id'] else None

def clear_base_group(user_id: int):
    """Clears the base group for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users_config SET base_group_id = NULL, base_group_name = NULL WHERE user_id = ?", (user_id,))
    conn.commit()
    logger.info(f"Cleared base group for user {user_id}")

def add_destination_group(user_id: int, group_id: int, group_name: str):
    """Adds a destination group for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Ensure user exists in config table
        cursor.execute("INSERT OR IGNORE INTO users_config (user_id) VALUES (?)", (user_id,))
        cursor.execute("INSERT INTO destination_groups (user_id, dest_group_id, dest_group_name) VALUES (?, ?, ?)",
                       (user_id, group_id, group_name))
        conn.commit()
        set_user_state(user_id, 'idle') # Reset state after adding
        logger.info(f"User {user_id} added destination group {group_id} ({group_name})")
    except sqlite3.IntegrityError:
        conn.rollback()
        logger.warning(f"User {user_id} tried to add duplicate destination group {group_id}")
        raise ValueError(f"Ya tienes añadido el grupo '{group_name}' (ID: {group_id}) como destino.")
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Error adding destination group for user {user_id}: {e}")
        raise

def remove_destination_group(user_id: int, group_id: int):
    """Removes a specific destination group for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM destination_groups WHERE user_id = ? AND dest_group_id = ?", (user_id, group_id))
    conn.commit()
    if cursor.rowcount > 0:
        logger.info(f"User {user_id} removed destination group {group_id}")
        return True
    logger.warning(f"User {user_id} tried to remove non-existent destination group {group_id}")
    return False

def get_destination_groups(user_id: int) -> list[tuple[int, str]]:
    """Gets all destination group IDs and names for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT dest_group_id, dest_group_name FROM destination_groups WHERE user_id = ?", (user_id,))
    return [(row['dest_group_id'], row['dest_group_name']) for row in cursor.fetchall()]

def get_all_forwarding_configs() -> dict[int, list[int]]:
    """
    Gets a dictionary mapping base_group_id to a list of destination_group_ids
    across all users. Used for efficient message forwarding lookup.
    Returns: dict[base_group_id, list[dest_group_id]]
    """
    configs = {}
    conn = get_db_connection()
    cursor = conn.cursor()
    # Get all users with a configured base group
    cursor.execute("SELECT user_id, base_group_id FROM users_config WHERE base_group_id IS NOT NULL")
    users_with_base = cursor.fetchall()

    for user_row in users_with_base:
        user_id = user_row['user_id']
        base_group_id = user_row['base_group_id']
        # Get destination groups for this user
        cursor.execute("SELECT dest_group_id FROM destination_groups WHERE user_id = ?", (user_id,))
        dest_groups = [row['dest_group_id'] for row in cursor.fetchall()]
        if dest_groups: # Only add if there are destinations
            if base_group_id not in configs:
                configs[base_group_id] = []
            # Add only unique destination IDs for this base group across all users
            # (Shouldn't happen with current logic, but good practice)
            for dest_id in dest_groups:
                 if dest_id not in configs[base_group_id]:
                     configs[base_group_id].append(dest_id)

    return configs


def check_destination_conflict(base_group_id_to_check: int, dest_group_id_to_check: int) -> bool:
    """
    Checks if ANY user is already forwarding FROM base_group_id_to_check TO dest_group_id_to_check.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Find all user_ids that have base_group_id_to_check as their base group
    cursor.execute("SELECT user_id FROM users_config WHERE base_group_id = ?", (base_group_id_to_check,))
    users_with_this_base = [row['user_id'] for row in cursor.fetchall()]

    if not users_with_this_base:
        return False # No conflict if no one uses this base group

    # Check if any of these users have dest_group_id_to_check as a destination
    placeholders = ','.join('?' for _ in users_with_this_base)
    query = f"""
        SELECT 1 FROM destination_groups
        WHERE user_id IN ({placeholders}) AND dest_group_id = ?
        LIMIT 1
    """
    params = users_with_this_base + [dest_group_id_to_check]
    cursor.execute(query, params)

    return cursor.fetchone() is not None # Conflict exists if a row is found

# Consider adding functions to periodically close idle connections if using thread-local storage
# in a very long-running or high-concurrency scenario, though for typical bot usage,
# keeping them open per thread might be acceptable. 