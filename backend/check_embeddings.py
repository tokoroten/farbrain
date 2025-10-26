import sqlite3
import json
import numpy as np

conn = sqlite3.connect('farbrain.db')
cursor = conn.cursor()

# Get the most recent test session
cursor.execute('''
    SELECT id, title FROM sessions
    ORDER BY created_at DESC
    LIMIT 1
''')
session = cursor.fetchone()
session_id = session[0]
session_title = session[1]

print(f"Checking session: {session_title} ({session_id})")
print()

# Get a few ideas from this session
cursor.execute('''
    SELECT id, formatted_text, embedding
    FROM ideas
    WHERE session_id = ?
    LIMIT 5
''', (session_id,))

ideas = cursor.fetchall()

for idx, (idea_id, text, embedding_json) in enumerate(ideas):
    embedding = json.loads(embedding_json)
    embedding_array = np.array(embedding)

    print(f"Idea {idx + 1}:")
    print(f"  Text: {text[:50]}...")
    print(f"  Embedding type: {type(embedding)}")
    print(f"  Embedding length: {len(embedding)}")
    print(f"  Embedding shape: {embedding_array.shape}")
    print(f"  First 5 values: {embedding_array[:5]}")
    print(f"  All zeros?: {np.all(embedding_array == 0)}")
    print(f"  All same value?: {len(np.unique(embedding_array)) == 1}")
    print()

conn.close()
