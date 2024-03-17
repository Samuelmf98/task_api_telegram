from fastapi import FastAPI, Request as FastAPIRequest
from dotenv import load_dotenv
from openai import OpenAI
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel
import psycopg2
import os
from messages_db import create_table_if_not_exists
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext
from telegram.ext.filters import Filters
import logging

logging.basicConfig(level=logging.INFO)

# Crea una instancia del logger
logger = logging.getLogger(__name__)
#logger.info("")

create_table_if_not_exists()


def get_db_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=RealDictCursor)


def insert_message(message_question, message_content, chat_id, role):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO messages (message_question, message_content, chat_id, role, created_date)
                    VALUES (%s, %s, %s, %s, NOW())
                """,
                    (message_question, message_content, chat_id, role),
                )
    except Exception as e:
        print(f"Error al insertar mensaje: {e}")


def get_session_messages(chat_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT message_question, message_content, chat_id, role FROM messages
                    WHERE chat_id = %s
                    ORDER BY created_date ASC
                    """,
                    (chat_id,),
                )
                messages = cur.fetchall()
                return messages
    except Exception as e:
        print(f"Error al recuperar mensajes: {e}")
        return []


load_dotenv()

GPT_TOKEN = OpenAI(api_key=os.getenv("GPT_TOKEN"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")




class Query(BaseModel):
    ask: str

def question(message_question, chat_id):
    if message_question:
        messages = get_session_messages(
            chat_id
            
        )  # Obtiene todos los mensajes de la sesión

        #Contexto inicial del asistente
        context_messages = [
            {
                "role": "system",
                "content": "Eres un asistente muy amable y util, y espero que me ayudes a responder cada una de mis preguntas",
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
            model="gpt-4-0125-preview",
            messages=context_messages,
        )

        # Obtiene el mensaje de respuesta de la API GPT
        response_message = completion.choices[0].message

    
        # Inserta el mensaje de respuesta en la base de datos
        insert_message(message_question, response_message.content, chat_id, "user")

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
