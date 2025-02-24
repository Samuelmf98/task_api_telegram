from dotenv import load_dotenv
from openai import OpenAI
import sqlite3
from messages_db import create_table_if_not_exists
from telegram import Update
from telegram.ext import Updater, MessageHandler, CallbackContext
from telegram.ext.filters import Filters
import logging
import os

# Crea una instancia del logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Obtiene la ruta al directorio donde se ejecuta el script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Define la ruta al archivo de la base de datos en el mismo directorio del script
DB_PATH = os.path.join(BASE_DIR, 'my_database.db')

# Carga variables de entorno
load_dotenv()
GPT_TOKEN = OpenAI(api_key=os.getenv("GPT_TOKEN"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

def create_connection():
    """ Crea y devuelve una conexión a la base de datos SQLite. """
    try:
        conn = sqlite3.connect(DB_PATH)
        return conn
    except Exception as e:
        logger.error(f"Error al conectar a la base de datos SQLite: {e}")
    return None

# Crea la tabla si no existe
create_table_if_not_exists()


# Funcion para insertar mensajes en la base de datos
def insert_message(message_question, message_content, chat_id, role):
    conn = create_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO messages (message_question, message_content, chat_id, role, created_date)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
            (message_question, message_content, chat_id, role),
        )
        conn.commit()
    except sqlite3.Error as e:
        logger.info("Error al insertar mensaje: {e}")
    finally:
        cur.close()
        conn.close()

# Funcion para obtener mensajes de la base de datos
def get_session_messages(chat_id):
    conn = create_connection()
    messages = []
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT message_question, message_content, chat_id, role FROM messages
                WHERE chat_id = ?
                ORDER BY created_date ASC
                """,
                (chat_id,)
            )
            rows = cur.fetchall()
            # Convertir cada tupla en un diccionario
            messages = [{'message_question': row[0], 'message_content': row[1], 'chat_id': row[2], 'role': row[3]} for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error al recuperar mensajes: {e}")
        finally:
            cur.close()
            conn.close()
    return messages

# Se extrae los mensajes de la base de datos y se realizam diversos append para crear el historial de la conversacion.
# Cada vez que el usuario envia un mensaje se recuperar todo el historial desde el principio y se le envía a la API.
# Esto es ineficiente en terminos de velocidad, pero la solución es limitar los mensajes a las ultimas 24 horas por ejemplo.
# Este enfoque es el apropiado si se usa el chat para interactuar con usuarios/clientes en una página web.
def question(message_question, chat_id):
    if message_question:
        messages = get_session_messages(
            chat_id
            
        )  # Obtiene todos los mensajes de la sesión

        #Contexto inicial del asistente
        context_messages = [
            {
                "role": "system",
                "content": "Eres un asistente muy amable y util, y espero que me ayudes a responder cada una de mis preguntas. Se claro y conciso en tus respuestas.",
            }
        ]

        # Agrega todos los mensajes anteriores al contexto
        for msg in messages:

            context_messages.append(
                {
                    "role": "user",
                    "content": msg["message_question"],
                }
            )

            context_messages.append(
                {
                    "role": "assistant",  # Usa 'role' para determinar el emisor del mensaje
                    "content": msg["message_content"],  # Asegúrate de usar 'content'
                }
            )


        # Añade la pregunta actual al contexto fuera del bucle
        context_messages.append(
            {
                "role": "user",
                "content": message_question,
            }
        )
        logger.info(context_messages)

        # Envía la solicitud a la API GPT con el contexto completo
        completion = GPT_TOKEN.chat.completions.create(
            model="gpt-4o-mini",
            messages=context_messages,
        )

        # Obtiene el mensaje de respuesta de la API GPT
        response_message = completion.choices[0].message

    
        # Inserta el mensaje de respuesta en la base de datos
        insert_message(message_question, response_message.content, chat_id, "assistant")

        # Retorna la respuesta
        return {"message": response_message.content}
    
def handle_text(update: Update, context: CallbackContext):

    message = update.message.text
    chat_id = update.message.chat_id

    reply_text = "No se recibió ningún mensaje válido."

    if message:
        try:
            # Suponiendo que question devuelve un diccionario con una clave 'message'
            reply_dict = question(message, chat_id)
            reply_text = reply_dict['message']
        except Exception as e:
            logger.error(f"Error llamando al servicio de ChatCompletion: {e}")
            reply_text = "Error llamando al servicio de ChatCompletion"

    # Envía reply_text como respuesta
    context.bot.send_message(chat_id=chat_id, text=reply_text)

def main():
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)

    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text, handle_text))

    updater.start_polling()
    updater.idle()
if __name__ == '__main__':
    main()
