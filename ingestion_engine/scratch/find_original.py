import json

transcript_path = r"C:\Users\Admin\.gemini\antigravity\brain\50613d68-a72a-4eb8-a6a7-37869f5043a5\.system_generated\logs\transcript.jsonl"

with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
            # Find steps where data_load.py was viewed
            if data.get("type") == "VIEW_FILE" and "data_load.py" in data.get("content", ""):
                print(f"Step {data.get('step_index')}: found data_load.py view content")
                # Write it to a file
                out_path = rf"d:\DATA LOAD ACCELERATORS\ingestion_engine\scratch\data_load_step_{data.get('step_index')}.py"
                with open(out_path, 'w', encoding='utf-8') as out_f:
                    out_f.write(data["content"])
                print(f"Wrote to {out_path}")
        except Exception as e:
            pass
