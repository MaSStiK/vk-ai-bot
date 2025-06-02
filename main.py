# -*- coding: utf-8 -*-
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import os, time, json
from datetime import datetime, timezone
import traceback
import threading

# Загрузка кастомных файлов
from config import base_prompt
from utils import log_error, load_memory, save_memory

from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VK_TOKEN = os.getenv("VK_TOKEN")

from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY, base_url="https://openrouter.ai/api/v1")

hash_users = {}
MAX_HISTORY_LENGTH = 20  # Ограничение на количество сообщений в истории
BOT_ID = 817934388

def start_typing_loop(vk, peer_id, stop_event):
    while not stop_event.is_set():
        try:
            vk.messages.setActivity(peer_id=peer_id, type="typing")
        except Exception as e:
            print(f"Ошибка при setActivity: {e}")
        time.sleep(4)

def main():
    session = vk_api.VkApi(token=VK_TOKEN)
    vk = session.get_api()
    longpoll = VkLongPoll(session)
    user_histories = load_memory()
    print("Бот запущен")

    def vk_messages_send(peer_id, message, reply_to=None):
        print("reply_to", reply_to)
        params = {
            "peer_id": peer_id,
            "random_id": 0,
            "message": message
        }
        if reply_to:
            params["reply_to"] = reply_to
        print("params", params)
        vk.messages.send(**params)

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW:
            user_id = event.user_id
            peer_id = event.peer_id
            message_id = event.message_id
            message = event.message
            from_me = event.from_me

            # Получаем имя пользователя
            user_name = hash_users.get(user_id)
            if not user_name:
                try:
                    if user_id > 0:
                        user = vk.users.get(user_id=user_id)[0]
                        user_name = f"{user['first_name']} {user['last_name']}"
                    else:
                        group = vk.groups.getById(group_id=-user_id)[0]
                        user_name = group["name"]
                    hash_users[user_id] = user_name
                except:
                    user_name = f"ID {user_id}"

            if not from_me and "reply" in event.attachments:
                try:
                    reply_data = json.loads(event.attachments['reply'])
                    reply_conv_id = reply_data.get("conversation_message_id")
                    response = vk.messages.getByConversationMessageId(
                        peer_id=peer_id,
                        conversation_message_ids=reply_conv_id
                    )
                    replied_message = response["items"][0]

                    if replied_message["from_id"] == BOT_ID:
                        print(f"Генерация ответа на сообщение: \"{user_name}: {message}\"")

                        # Инициализируем историю пользователя, если её нет
                        if str(user_id) not in user_histories:
                            user_histories[str(user_id)] = []

                        # Добавляем новое сообщение в историю
                        user_histories[str(user_id)].append({"role": "user", "content": f"{user_name}: {message}"})

                        # Обрезаем старую историю при необходимости
                        if len(user_histories[str(user_id)]) > MAX_HISTORY_LENGTH:
                            user_histories[str(user_id)] = user_histories[str(user_id)][-MAX_HISTORY_LENGTH:]

                        stop_typing = threading.Event()
                        typing_thread = threading.Thread(target=start_typing_loop, args=(vk, peer_id, stop_typing))
                        typing_thread.start()

                        try:
                            ai_response = client.chat.completions.create(
                                model="deepseek/deepseek-chat-v3-0324:free",
                                messages=[{"role": "user", "content": base_prompt}, *user_histories[str(user_id)]]
                            )
                            answer = ai_response.choices[0].message.content.strip()

                            # Добавляем ответ ИИ в историю
                            user_histories[str(user_id)].append({"role": "assistant", "content": answer})
                            save_memory(user_histories)

                            print(f"Ответ нейросети: {answer}")
                            if len(answer) >= 4000:
                                print(f"Ответ больше 4000 символов")
                                answer = answer[:4000]
                            vk_messages_send(peer_id=peer_id, message=answer, reply_to=message_id)
                        except:
                            # Если ошибка [913] Too many forwarded messages
                            try:
                                vk_messages_send(peer_id=peer_id, message=answer)
                            except Exception as e:
                                print(f"Ошибка обработки сообщения: {traceback.format_exc()}")
                                log_error(f"Ошибка обработки сообщения: {traceback.format_exc()}")
                        finally:
                            stop_typing.set()
                            typing_thread.join()

                except Exception as e:
                    print(f"Ошибка обработки reply: {e}")
                    log_error(f"Ошибка обработки reply: {e}")


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"Ошибка: {e}")
            log_error(e)
        time.sleep(4)
