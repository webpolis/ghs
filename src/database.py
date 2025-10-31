import os
import threading
from typing import List, Optional, Tuple

try:
    import pysqlite3 as sqlite3
except ImportError:
    import sqlite3
import sqlite_vec
from sqlite_vec import serialize_float32


class StarDatabase:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_dir = os.path.expanduser("~/.config/ghs")
            os.makedirs(db_dir, exist_ok=True)
            self.db_path = os.path.join(db_dir, "stars.db")
        else:
            self.db_path = db_path

        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self):
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY,
                repo_id INTEGER UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                url TEXT NOT NULL,
                stars INTEGER,
                language TEXT,
                created_at TEXT,
                updated_at TEXT,
                readme_content TEXT,
                readme_type TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_repositories USING vec0(
                repo_id INTEGER PRIMARY KEY,
                embedding FLOAT[384]
            )
        """)

        self.conn.commit()

    def repository_exists(self, repo_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM repositories WHERE repo_id = ?", (repo_id,))
        return cursor.fetchone() is not None

    def insert_repository(
        self,
        repo_id: int,
        full_name: str,
        name: str,
        description: Optional[str],
        url: str,
        stars: int,
        language: Optional[str],
        created_at: str,
        updated_at: str,
        readme_content: Optional[str],
        readme_type: Optional[str],
        embedding: Optional[List[float]]
    ):
        with self._lock:
            cursor = self.conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO repositories
                (repo_id, full_name, name, description, url, stars, language,
                 created_at, updated_at, readme_content, readme_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (repo_id, full_name, name, description, url, stars, language,
                  created_at, updated_at, readme_content, readme_type))

            if embedding is not None:
                cursor.execute("""
                    INSERT OR REPLACE INTO vec_repositories (repo_id, embedding)
                    VALUES (?, ?)
                """, (repo_id, serialize_float32(embedding)))

            self.conn.commit()

    def search_similar(self, query_embedding: List[float], limit: int = 10) -> List[Tuple]:
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT
                r.repo_id,
                r.full_name,
                r.description,
                r.url,
                r.stars,
                distance
            FROM vec_repositories v
            INNER JOIN repositories r ON v.repo_id = r.repo_id
            WHERE embedding MATCH ?
            AND k = ?
            ORDER BY distance
        """, (serialize_float32(query_embedding), limit))

        return cursor.fetchall()

    def get_statistics(self) -> dict:
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM repositories")
        total_repos = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM vec_repositories")
        embedded_repos = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM repositories WHERE readme_content IS NOT NULL")
        repos_with_readme = cursor.fetchone()[0]

        return {
            "total_repositories": total_repos,
            "embedded_repositories": embedded_repos,
            "repositories_with_readme": repos_with_readme
        }

    def get_all_repo_ids(self) -> List[int]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT repo_id FROM repositories")
        return [row[0] for row in cursor.fetchall()]

    def delete_repository(self, repo_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM repositories WHERE repo_id = ?", (repo_id,))
        cursor.execute("DELETE FROM vec_repositories WHERE repo_id = ?", (repo_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()
