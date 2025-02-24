import sqlite3
import os
import logging

# Configuración del logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Obtiene la ruta al directorio donde se ejecuta el script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define la ruta al archivo de la base de datos en el mismo directorio del script
DB_PATH = os.path.join(BASE_DIR, 'my_database.db')

def create_connection():
    """ Crea y devuelve una conexión a la base de datos SQLite. """
    try:
        conn = sqlite3.connect(DB_PATH)
        return conn
    except Exception as e:
        logger.error(f"Error al conectar a la base de datos SQLite: {e}")
    return None

def create_table_if_not_exists():
    """ Crea la tabla si no existe en la base de datos. """
    conn = create_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_question TEXT,
                    message_content TEXT,
                    chat_id INTEGER,
                    role TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            conn.commit()
        except Exception as e:
            logger.error("Error al crear la tabla:", e)
        finally:
            cur.close()
            conn.close()