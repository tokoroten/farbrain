import sqlite3

conn = sqlite3.connect('farbrain.db')
cursor = conn.cursor()

cursor.execute('''
    SELECT session_id, COUNT(*) as count
    FROM ideas
    GROUP BY session_id
    ORDER BY MAX(timestamp) DESC
    LIMIT 5
''')

print('Recent sessions idea counts:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]} ideas')

conn.close()
