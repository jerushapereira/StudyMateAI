import sqlite3
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash


class AuthService:
    def __init__(self, database_path: str):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def create_user(self, name: str, email: str, password: str):
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO users (name, email, password_hash)
                    VALUES (?, ?, ?)
                    """,
                    (name.strip(), email.strip().lower(), generate_password_hash(password)),
                )
                user_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

        return self.get_user_by_id(user_id)

    def authenticate(self, email: str, password: str):
        user = self.get_user_by_email(email)
        if not user or not check_password_hash(user["password_hash"], password):
            return None
        return self._public_user(user)

    def get_user_by_id(self, user_id: int):
        with self._connect() as connection:
            user = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return self._public_user(user) if user else None

    def get_user_by_email(self, email: str):
        with self._connect() as connection:
            return connection.execute(
                "SELECT * FROM users WHERE email = ?",
                (email.strip().lower(),),
            ).fetchone()

    def _public_user(self, user):
        return {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
        }
