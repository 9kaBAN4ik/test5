import sqlite3
from datetime import datetime

from config import DB_PATH

# Подключаемся к базе данных
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Данные для вставки
id_value = 2
referrer_id = 238508371
referred_id = 974567196
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Текущая дата и время
level = 1

# Вставка данных в таблицу referrals
cursor.execute(""" 
    INSERT INTO referrals (id, referrer_id, referred_id, timestamp, level)
    VALUES (?, ?, ?, ?, ?)
""", (id_value, referrer_id, referred_id, timestamp, level))

# Сохраняем изменения и закрываем соединение
conn.commit()
conn.close()
