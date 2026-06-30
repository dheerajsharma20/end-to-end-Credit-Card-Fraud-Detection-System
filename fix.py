import struct

# Fix app.py
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = 'conf = str(round(t["confidence"], 1))'
new = '''raw = t["confidence"]
                if isinstance(raw, bytes):
                    try:
                        raw = struct.unpack("f", raw)[0]
                    except:
                        raw = 0.0
                conf = str(round(float(raw), 1))'''

count = content.count(old)
print("Found", count, "occurrences to fix")
content = content.replace(old, new)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("app.py fixed!")

# Fix database.py
with open('database.py', 'r', encoding='utf-8') as f:
    db = f.read()

old_db = '{"amount": r[0], "result": r[1], "confidence": r[2], "checked_at": r[3]}'
new_db = '''{"amount": r[0], "result": r[1], "confidence": struct.unpack("f", r[2])[0] if isinstance(r[2], bytes) else float(r[2] or 0), "checked_at": r[3]}'''

if old_db in db:
    db = 'import struct\n' + db
    db = db.replace(old_db, new_db)
    with open('database.py', 'w', encoding='utf-8') as f:
        f.write(db)
    print("database.py fixed!")
else:
    print("database.py already fixed or pattern not found")

print("All done! Now run: streamlit run app.py")
