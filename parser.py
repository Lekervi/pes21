import os
import shutil
import json
import base64
import time
import re
from datetime import datetime
from openai import OpenAI

INCOMING_DIR = 'incoming'
ARCHIVE_DIR = 'archive'
HISTORY_FILE = 'history.json'

client = OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_history(data):
    # Стандартное сохранение для локальных нужд
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    # Копируем свежий файл сразу в папку-мост для отправки на сайт
    try:
        with open('pes21/history.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Не удалось скопировать файл в папку pes21: {e}")

def process_pair(img1_name, img2_name):
    history = load_history()
    img1_path = os.path.join(INCOMING_DIR, img1_name)
    img2_path = os.path.join(INCOMING_DIR, img2_name)

    print(f"\n📸 Найдена пара скриншотов: {img1_name} и {img2_name}")
    print("🧠 Нейросеть анализирует данные, подожди...")

    match_date = datetime.now().strftime('%d.%m.%Y')

    SYSTEM_PROMPT = """Ты эксперт по извлечению данных. Проанализируй два скриншота из игры PES 2021. 
Один скриншот содержит общую статистику матча, второй - список авторов голов.

КРИТИЧЕСКИ ВАЖНОЕ ПРАВИЛО СЧЕТА: 
Итоговое количество голов (параметр "goals") бери СТРОГО из больших цифр общего счета матча на экране! Запрещено высчитывать счет путем подсчета количества игроков в списке.

ДОМАШНИЕ И ВЫЕЗДНЫЕ МАТЧИ (is_home):
Внимательно посмотри на скриншот с общим счетом.
- Если флаг и название команды находятся в ЛЕВОЙ части экрана, то она играет дома. Укажи ей параметр "is_home": true.
- Если флаг и название команды находятся в ПРАВОЙ части экрана, то она играет на выезде. Укажи ей параметр "is_home": false.

СПЕЦИФИКА ГОЛОВ:
В списке авторов голов ищи пометки:
- Пенальти (Pen, Penalty) -> "type": "penalty"
- Автогол (OG, Own Goal) -> "type": "own_goal"
- Без пометок -> "type": "normal"

Верни строго JSON по шаблону ниже. Имена ключей менять запрещено!
Команда 1 - всегда ГЕРМАНИЯ (Фарид), Команда 2 - всегда ИСПАНИЯ (Эмиль).

ШАБЛОН ОТВЕТА:
{
  "team_1": {
    "name": "ГЕРМАНИЯ",
    "player": "Фарид",
    "is_home": true,
    "goals": 5,
    "scorers": [
      {
        "name": "L. KLOSTERMANN",
        "minute": 25,
        "type": "normal"
      }
    ],
    "stats": {
      "possession_pct": 57,
      "shots": 14,
      "shots_on_target": 9,
      "fouls": 5,
      "offsides": 2,
      "corners": 4,
      "free_kicks": 7,
      "total_passes": 253,
      "successful_passes": 205,
      "crosses": 10,
      "interceptions": 29,
      "tackles": 4,
      "saves": 4
    }
  },
  "team_2": {
    "name": "ИСПАНИЯ",
    "player": "Эмиль",
    "is_home": false,
    "goals": 4,
    "scorers": [],
    "stats": {
      "possession_pct": 43,
      "shots": 15,
      "shots_on_target": 11,
      "fouls": 7,
      "offsides": 0,
      "corners": 2,
      "free_kicks": 4,
      "total_passes": 213,
      "successful_passes": 166,
      "crosses": 7,
      "interceptions": 25,
      "tackles": 3,
      "saves": 5
    }
  }
}
Никакого лишнего текста или форматирования markdown, только чистый валидный JSON."""

    try:
        base64_image1 = encode_image(img1_path)
        base64_image2 = encode_image(img2_path)

        response = client.chat.completions.create(
            model="local-model",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": "Извлеки статистику в JSON строго по шаблону. Помни про правило счета, спецификацию голов и определение домашней команды!"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image1}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image2}"}}
                ]}
            ],
            temperature=0.1
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Интеллектуальный поиск JSON (игнорирует любой мусор до и после)
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        
        if not json_match:
            print("\n❌ Нейросеть вернула странный ответ вместо JSON!")
            print(f"Вот её ответ:\n{result_text}\n")
            return False

        clean_json = json_match.group(0)
        raw_match_data = json.loads(clean_json)
        
        # --- ЖЕСТКАЯ ВАЛИДАЦИЯ И ОЧИСТКА МИНУТ ОТ ИНОРОДНЫХ СИМВОЛОВ (АПОСТРОФЫ, БУКВЫ, КАВЫЧКИ) ---
        for team_key in ["team_1", "team_2"]:
            if team_key in raw_match_data and "scorers" in raw_match_data[team_key]:
                for scorer in raw_match_data[team_key]["scorers"]:
                    if "minute" in scorer:
                        raw_minute = str(scorer["minute"])
                        # Регулярным выражением удаляем всё, что не является цифрой (\D)
                        clean_minute = re.sub(r'\D', '', raw_minute)
                        
                        if clean_minute.isdigit():
                            scorer["minute"] = int(clean_minute)
                        else:
                            # Дефолтное значение на случай, если модель прислала критический мусор
                            scorer["minute"] = 0
        # ----------------------------------------------------------------------------------------
        
        # --- ГЕНЕРАЦИЯ УНИКАЛЬНОГО ID ---
        match_num = len(history) + 1
        t1_is_home = raw_match_data.get("team_1", {}).get("is_home", True)
        g1 = raw_match_data.get("team_1", {}).get("goals", 0)
        g2 = raw_match_data.get("team_2", {}).get("goals", 0)
        
        date_slug = datetime.now().strftime('%d-%m-%Y')
        
        if not t1_is_home:
            # Испания играет дома
            match_id = f"{match_num}_spain_ger_{g2}_{g1}_{date_slug}"
        else:
            # Германия играет дома
            match_id = f"{match_num}_ger_spain_{g1}_{g2}_{date_slug}"
            
        # Формируем итоговый объект, ставя ID и дату на первое место
        match_data = {
            "id": match_id,
            "date": match_date
        }
        match_data.update(raw_match_data)
        # -------------------------------
        
        history.append(match_data)
        save_history(history)
        
        shutil.move(img1_path, os.path.join(ARCHIVE_DIR, img1_name))
        shutil.move(img2_path, os.path.join(ARCHIVE_DIR, img2_name))
        
        print(f"✅ Матч {match_id} успешно добавлен в базу, картинки перенесены в архив!")
        return True

    except Exception as e:
        print(f"\n❌ Ошибка при обработке этой пары: {e}")
        print("Скрипт продолжит работу. Файлы остались в папке incoming.")
        return False

def main():
    os.makedirs(INCOMING_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    print("==================================================")
    print("🚀 Сканер папки PES 2021 запущен!")
    print("==================================================")

    valid_ext = ('.png', '.jpg', '.jpeg')

    while True:
        files = [f for f in os.listdir(INCOMING_DIR) if f.lower().endswith(valid_ext)]
        files.sort()

        if len(files) >= 2:
            time.sleep(2)
            # Перепроверяем файлы после паузы
            files = [f for f in os.listdir(INCOMING_DIR) if f.lower().endswith(valid_ext)]
            files.sort()
            
            if len(files) >= 2:
                success = process_pair(files[0], files[1])
                if success:
                    time.sleep(3)
                continue
        
        # Если файлов меньше двух - выходим из цикла
        print("✅ Все пары обработаны. Завершаю работу скрипта.")
        break

if __name__ == "__main__":
    main()