"""Fix agent_profiles: update model from llama3.2:1b to mistral:7b"""
import sqlite3
from pathlib import Path

conn = sqlite3.connect(Path("data") / "dev.db")
cur = conn.cursor()

# Show current state
print("=== Current agent profiles ===")
for r in cur.execute("SELECT slug, model FROM agent_profiles ORDER BY slug"):
    print(f"  {r[0]:20s}  {r[1]}")

# Fix: update any profile still using llama3.2:1b to mistral:7b
cur.execute(
    "UPDATE agent_profiles SET model='mistral:7b' WHERE model='llama3.2:1b'"
)
print(f"\nUpdated {cur.rowcount} profile(s) from llama3.2:1b -> mistral:7b")
conn.commit()

print("\n=== Updated agent profiles ===")
for r in cur.execute("SELECT slug, model FROM agent_profiles ORDER BY slug"):
    print(f"  {r[0]:20s}  {r[1]}")

conn.close()
