
import json
import re
import time
import threading
import requests
import speech_recognition as sr
import pyttsx3
import paho.mqtt.client as mqtt

# =========================
# НАСТРОЙКИ
# =========================

BROKER = "127.0.0.1"
PORT = 1883
MICROPHONE_INDEX = 1

MODEL = "qwen2.5:3b"
OLLAMA_URL = "http://localhost:11434/api/chat"

# Пауза между попытками подключения
RECONNECT_MIN_DELAY = 1
RECONNECT_MAX_DELAY = 30

# =========================
# РАСПОЗНАВАНИЕ РЕЧИ
# =========================

recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.pause_threshold = 0.6

speaker = pyttsx3.init()
speaker.setProperty("rate", 175)

# =========================
# MQTT
# =========================

mqtt_connected = threading.Event()
mqtt_state_lock = threading.Lock()

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id="jarvis-voice"
)

client.reconnect_delay_set(
    min_delay=RECONNECT_MIN_DELAY,
    max_delay=RECONNECT_MAX_DELAY
)

COMMANDS = {
    "light_on": ("home/relay1", "ON"),
    "light_off": ("home/relay1", "OFF"),
    "shutter_open": ("home/shutter", "OPEN"),
    "shutter_close": ("home/shutter", "CLOSE"),
    "shutter_stop": ("home/shutter", "STOP"),
}

RESPONSES = {
    "light_on": "Включаю свет",
    "light_off": "Выключаю свет",
    "shutter_open": "Отправляю команду открыть роллету",
    "shutter_close": "Отправляю команду закрыть роллету",
    "shutter_stop": "Останавливаю роллету",
}

ALLOWED_COMMANDS = set(COMMANDS.keys()) | {"unknown"}

# =========================
# MQTT CALLBACKS
# =========================

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        was_disconnected = not mqtt_connected.is_set()
        mqtt_connected.set()

        print("[MQTT] Соединение установлено")

        if was_disconnected:
            print("[MQTT] Брокер доступен, можно отправлять команды")
    else:
        mqtt_connected.clear()
        print(f"[MQTT] Не удалось подключиться. Код: {reason_code}")


def on_disconnect(
    client, userdata, disconnect_flags, reason_code, properties
):
    was_connected = mqtt_connected.is_set()
    mqtt_connected.clear()

    if was_connected:
        print("[MQTT] Соединение потеряно. Пробую восстановить...")
    else:
        print(f"[MQTT] Отключение. Код: {reason_code}")


client.on_connect = on_connect
client.on_disconnect = on_disconnect

# =========================
# ИНСТРУКЦИЯ ДЛЯ QWEN
# =========================

SYSTEM_PROMPT = """
Ты — языковой модуль домашнего голосового ассистента Джарвис.

Твоя задача — понять смысл русской фразы и выбрать действие.
Пользователь может говорить разговорно, использовать сленг,
мат, ругательства, шутки, обращения и длинные предложения.
Не обращай внимания на оскорбления и определяй именно намерение.

Доступные действия:

light_on — включить свет.
Примеры: "включи свет", "сделай светло",
"темно, нихрена не видно", "зажги лампу".

light_off — выключить свет.
Примеры: "выключи свет", "погаси лампу",
"убери освещение", "хватит светить, выключи".

shutter_open — открыть или поднять роллету.
Примеры: "открой роллету", "подними рольставни".

shutter_close — закрыть или опустить роллету.
Примеры: "закрой роллету", "опусти рольставни".

shutter_stop — остановить движущуюся роллету.
Примеры: "останови роллету", "стой, прекрати движение".

unknown — если действие не относится к этим устройствам,
намерение неясно или пользователь НЕ просит выполнять действие.

ВАЖНО:
1. Учитывай смысл всей фразы, а не отдельные слова.
2. "Не включай свет" означает unknown.
3. "Не выключай свет" означает unknown.
4. Если пользователь сообщает, что темно и плохо видно,
   обычно выбирай light_on.
5. Если пользователь явно просит выключить свет — light_off.
6. Не выполняй команды, которые пользователь отрицает,
   цитирует или обсуждает как пример.
7. Не придумывай другие устройства и действия.
8. Возвращай только JSON следующего вида:
   {"command":"light_on"}
   Вместо light_on используй одно разрешённое действие.
9. Никаких пояснений за пределами JSON.
"""

# =========================
# ГОЛОСОВОЙ ОТВЕТ
# =========================

def say(message):
    print(f"Джарвис: {message}")
    speaker.say(message)
    speaker.runAndWait()


# =========================
# БЫСТРЫЕ КОМАНДЫ
# =========================

def quick_command(text):
    text = text.lower().replace("ё", "е")
    words = re.findall(r"[а-яa-z]+", text)
    w = set(words)

    actions = {
        "включи", "включить", "включай",
        "выключи", "выключить", "выключай",
        "зажги", "погаси", "отключи",
        "открой", "открыть", "открывай",
        "закрой", "закрыть", "закрывай",
        "подними", "опусти", "останови",
        "остановить", "стой"
    }

    for i in range(len(words) - 1):
        if words[i] == "не" and words[i + 1] in actions:
            return None

    light_words = {"свет", "освещение", "лампу", "лампа"}
    shutter_words = {
        "роллету", "роллета", "роллеты",
        "рольставни", "рольставню"
    }

    open_words = {"открой", "открыть", "открывай", "подними"}
    close_words = {"закрой", "закрыть", "закрывай", "опусти"}
    on_words = {"включи", "включить", "включай", "зажги"}
    off_words = {
        "выключи", "выключить", "выключай",
        "погаси", "отключи"
    }
    stop_words = {"останови", "остановить", "стой"}

    if w & shutter_words:
        if w & stop_words:
            return "shutter_stop"
        if w & open_words:
            return "shutter_open"
        if w & close_words:
            return "shutter_close"

    if w & light_words:
        if w & on_words:
            return "light_on"
        if w & off_words:
            return "light_off"

    if len(words) <= 3:
        if w & stop_words and w & shutter_words:
            return "shutter_stop"
        if w & open_words:
            return "shutter_open"
        if w & close_words:
            return "shutter_close"
        if w & on_words:
            return "light_on"
        if w & off_words:
            return "light_off"

    return None


# =========================
# ПОНИМАНИЕ СВОБОДНОЙ РЕЧИ
# =========================

def understand(text):
    start = time.time()

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            "options": {
                "temperature": 0
            }
        },
        timeout=45
    )

    response.raise_for_status()

    content = response.json()["message"]["content"]
    print(f"[QWEN] Ответ: {content}")
    print(f"[ТАЙМИНГ] Qwen: {time.time() - start:.2f} сек")

    result = json.loads(content)
    command = result.get("command", "unknown")

    if command not in ALLOWED_COMMANDS:
        return "unknown"

    return command


# =========================
# ВЫПОЛНЕНИЕ КОМАНД
# =========================

def execute(command):
    if command not in COMMANDS:
        say("Не понял команду. Повтори.")
        return

    if not mqtt_connected.is_set() or not client.is_connected():
        say("Нет соединения с умным домом. Пробую восстановить связь")
        return

    topic, payload = COMMANDS[command]

    try:
        info = client.publish(topic, payload, qos=1)

        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            say("Не удалось отправить команду")
            return

        info.wait_for_publish(timeout=3)

        if not info.is_published():
            say("Команда не подтверждена брокером")
            return

        say(RESPONSES[command])

    except Exception as error:
        print(f"[MQTT] Ошибка отправки: {error}")
        say("Ошибка связи с умным домом")


# =========================
# ПРОСЛУШИВАНИЕ МИКРОФОНА
# =========================

def listen_once():
    try:
        with sr.Microphone(device_index=MICROPHONE_INDEX) as source:
            print("Слушаю...")
            start = time.time()

            audio = recognizer.listen(
                source,
                timeout=8,
                phrase_time_limit=7
            )

        text = recognizer.recognize_google(
            audio,
            language="ru-RU"
        ).strip()

        print(
            f"[ТАЙМИНГ] Распознавание: "
            f"{time.time() - start:.2f} сек"
        )
        print(f"Ты: {text}")

        return text

    except sr.WaitTimeoutError:
        print("Не услышал речь")
    except sr.UnknownValueError:
        print("Не расслышал речь")
    except sr.RequestError as error:
        print(f"[МИКРОФОН] Ошибка распознавания: {error}")
        say("Проблема с распознаванием речи")
    except Exception as error:
        print(f"[МИКРОФОН] Ошибка: {error}")

    return None


# =========================
# ГЛАВНЫЙ ЦИКЛ
# =========================

def main():
    try:
        print(f"Подключаюсь к MQTT: {BROKER}:{PORT}...")

        # connect_async не блокирует запуск, если брокер пока недоступен.
        client.connect_async(BROKER, PORT, keepalive=60)
        client.loop_start()

        say("Джарвис запущен. Подключаюсь к умному дому")

        while True:
            text = listen_once()

            if not text:
                continue

            normalized = text.lower().replace("ё", "е").strip()

            if normalized in {
                "выход",
                "завершить работу",
                "джарвис выключись",
                "джарвис стоп"
            }:
                say("Выключаюсь")
                break

            command = quick_command(text)

            if command:
                print(f"[КОМАНДА] Быстрый режим: {command}")
                execute(command)
                continue

            try:
                command = understand(text)
                print(f"[КОМАНДА] Qwen: {command}")

                if command == "unknown":
                    say("Не понял команду. Повтори.")
                else:
                    execute(command)

            except requests.RequestException as error:
                print(f"[QWEN] Ошибка соединения: {error}")
                say("Не удалось связаться с языковой моделью")
            except (ValueError, KeyError, TypeError) as error:
                print(f"[QWEN] Ошибка ответа: {error}")
                say("Не смог понять фразу. Повтори.")
            except Exception as error:
                print(f"[ОШИБКА] {error}")
                say("Произошла ошибка")

    except KeyboardInterrupt:
        print("\nОстановка Джарвиса")
    except Exception as error:
        print(f"[ЗАПУСК] Ошибка: {error}")
    finally:
        client.loop_stop()
        if client.is_connected():
            client.disconnect()


if __name__ == "__main__":
    main()
