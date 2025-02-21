import sqlite3

from config import DB_PATH

# Подключаемся к базе данных
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Удаляем запись с id = 6
cursor.execute("DELETE FROM products WHERE id = ?", (6,))

# Сохраняем изменения и закрываем соединение
conn.commit()
conn.close()
