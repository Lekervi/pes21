from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import subprocess
import datetime

app = Flask(__name__)
# Разрешаем принимать запросы с телефона
CORS(app)

INCOMING_DIR = "incoming"
os.makedirs(INCOMING_DIR, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload_files():
    # Проверяем, пришли ли оба файла
    if 'scorers' not in request.files or 'stats' not in request.files:
        return jsonify({"error": "Нужны оба файла"}), 400

    f_scorers = request.files['scorers']
    f_stats = request.files['stats']

    # Генерируем уникальное имя на основе времени, чтобы парсер не запутался
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Сохраняем файлы с префиксами _1 и _2 для строгой алфавитной сортировки
    f_scorers.save(os.path.join(INCOMING_DIR, f"{now}_1_scorers.jpg"))
    f_stats.save(os.path.join(INCOMING_DIR, f"{now}_2_stats.jpg"))

    print(f"✅ Получены новые скриншоты матча! Запускаю нейросеть...")

    # Автоматически запускаем твой батник
    # Используем start, чтобы он открылся в новом окне и сервер продолжил работать
    subprocess.Popen('start "" "run_parser.bat"', shell=True)

    return jsonify({"message": "Успешно отправлено!"}), 200

if __name__ == '__main__':
    # Запускаем сервер на порту 5000, доступный в локальной сети
    app.run(host='0.0.0.0', port=5000)