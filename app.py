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

create_table_if_not_exists()


def get_db_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=RealDictCursor)


def insert_message(message_question, message_content, role):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO messages (message_question, message_content, role, created_date)
                    VALUES (%s, %s, %s, NOW())
                """,
                    (message_question, message_content, role),
                )
    except Exception as e:
        print(f"Error al insertar mensaje: {e}")


def get_session_messages():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT message_question, message_content, role FROM messages
                    ORDER BY created_date ASC
                    """,
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

def question(message_question):
    if message_question:
        messages = get_session_messages(
            
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
                    "role": "user",  # Usa 'role' para determinar el emisor del mensaje
                    "content": msg["message_content"],  # Asegúrate de usar 'content'
                }
            )


        # Añade la pregunta actual al contexto fuera del bucle
        context_messages.append(
            {
                "role": "assistant",
                "content": message_question,
            }
        )

        # Envía la solicitud a la API GPT con el contexto completo
        completion = GPT_TOKEN.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=context_messages,
        )


        # Obtiene el mensaje de respuesta de la API GPT
        response_message = completion.choices[0].message

    
        # Inserta el mensaje de respuesta en la base de datos
        insert_message(message_question, response_message.content, "user")

        # Retorna la respuesta
        return {"message": response_message.content}
    
def handle_text(update: Update, context: CallbackContext):

    message = update.message.text
    chat_id = update.message.chat_id
    if message:

        try:
            reply = question(message)
        except:
            reply = "Error llamando al servicio de ChatCompletion"
            print(reply)
        
    context.bot.send_message(chat_id=chat_id, text=reply['message'])

def main():
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)

    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text, handle_text))

    updater.start_polling()
    updater.idle()
if __name__ == '__main__':
    main()
