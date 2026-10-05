"""One-time bootstrap for the project's NEW isolated local MySQL instance only."""
from pathlib import Path
import MySQLdb
from dotenv import dotenv_values

config = dotenv_values(Path(__file__).resolve().parent.parent / '.env')
assert config['MYSQL_PORT'] == '3307' and config['MYSQL_DATABASE'] == 'reading_room'
connection = MySQLdb.connect(host='127.0.0.1', port=3307, user='root', passwd='')
with connection.cursor() as cursor:
    cursor.execute('CREATE DATABASE reading_room CHARACTER SET utf8mb4')
    cursor.execute("CREATE USER 'reading_room'@'localhost' IDENTIFIED BY %s", [config['MYSQL_PASSWORD']])
    cursor.execute("GRANT ALL ON reading_room.* TO 'reading_room'@'localhost'")
    cursor.execute("GRANT ALL ON test_reading_room.* TO 'reading_room'@'localhost'")
    cursor.execute("ALTER USER 'root'@'localhost' IDENTIFIED BY %s", [config['MYSQL_LOCAL_ROOT_PASSWORD']])
connection.close()
print('Isolated MySQL database created; credentials are saved only in the ignored .env.')
