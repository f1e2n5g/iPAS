import json
import sys

with open("clean_questions.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

start = int(sys.argv[1])
end = int(sys.argv[2])

for i in range(start, min(end, len(questions))):
    q = questions[i]
    print(f"Question {i+1}:")
    print(f"{q['q_text']}")
    print(f"1. {q['options'][0]}")
    print(f"2. {q['options'][1]}")
    print(f"3. {q['options'][2]}")
    print(f"4. {q['options'][3]}")
    print("---")
