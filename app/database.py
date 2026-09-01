"""Database setup for caching knowledge base and storing user favorites."""
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "bot.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def init_db():
    """Initialize database schema."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Knowledge base cache
    c.execute('''CREATE TABLE IF NOT EXISTS knowledge (
        id INTEGER PRIMARY KEY,
        source TEXT NOT NULL,
        chapter TEXT,
        verse TEXT,
        sanskrit TEXT,
        translation TEXT,
        explanation TEXT,
        UNIQUE(source, chapter, verse)
    )''')
    
    # User favorites
    c.execute('''CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        source TEXT NOT NULL,
        chapter TEXT,
        verse TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, source, chapter, verse)
    )''')
    
    # User preferences
    c.execute('''CREATE TABLE IF NOT EXISTS user_settings (
        user_id INTEGER PRIMARY KEY,
        language TEXT DEFAULT 'de',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()


def insert_knowledge(entries: List[Dict[str, Any]]):
    """Insert knowledge base entries into database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    for entry in entries:
        try:
            c.execute('''INSERT OR REPLACE INTO knowledge 
                (source, chapter, verse, sanskrit, translation, explanation)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (
                    entry.get("source", ""),
                    entry.get("chapter", ""),
                    entry.get("verse", ""),
                    entry.get("sanskrit", ""),
                    json.dumps(entry.get("translation", {})),
                    json.dumps(entry.get("explanation", {}))
                ))
        except Exception as e:
            print(f"Error inserting entry: {e}")
    
    conn.commit()
    conn.close()


def get_all_knowledge() -> List[Dict[str, Any]]:
    """Get all knowledge base entries from database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM knowledge')
    
    entries = []
    for row in c.fetchall():
        entries.append({
            "source": row[1],
            "chapter": row[2],
            "verse": row[3],
            "sanskrit": row[4],
            "translation": json.loads(row[5]) if row[5] else {},
            "explanation": json.loads(row[6]) if row[6] else {}
        })
    
    conn.close()
    return entries


def save_favorite(user_id: int, source: str, chapter: str, verse: str) -> bool:
    """Save a favorite scripture verse for a user."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO favorites (user_id, source, chapter, verse)
                     VALUES (?, ?, ?, ?)''',
                  (user_id, source, chapter, verse))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False  # Already favorited
    except Exception as e:
        print(f"Error saving favorite: {e}")
        return False


def get_favorites(user_id: int) -> List[Dict[str, Any]]:
    """Get all favorites for a user."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT source, chapter, verse, created_at FROM favorites 
                 WHERE user_id = ? ORDER BY created_at DESC''', (user_id,))
    
    favorites = []
    for row in c.fetchall():
        favorites.append({
            "source": row[0],
            "chapter": row[1],
            "verse": row[2],
            "created_at": row[3]
        })
    
    conn.close()
    return favorites


def remove_favorite(user_id: int, source: str, chapter: str, verse: str) -> bool:
    """Remove a favorite for a user."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''DELETE FROM favorites 
                     WHERE user_id = ? AND source = ? AND chapter = ? AND verse = ?''',
                  (user_id, source, chapter, verse))
        conn.commit()
        conn.close()
        return c.rowcount > 0
    except Exception as e:
        print(f"Error removing favorite: {e}")
        return False


def set_user_language(user_id: int, language: str):
    """Set user's preferred language."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO user_settings (user_id, language)
                     VALUES (?, ?)''', (user_id, language))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error setting user language: {e}")


def get_user_language(user_id: int) -> str:
    """Get user's preferred language."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT language FROM user_settings WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else 'de'
    except Exception as e:
        print(f"Error getting user language: {e}")
        return 'de'


# Initialize database on import
init_db()
