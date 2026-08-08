from pathlib import Path
import json
import pandas as pd

CANONICAL_FIELDS={"name","first_name","last_name","roll_number","card_number","tribe","nation","category","age","sex","birth_year","residence","source_url","citation"}

def load_records(path: str) -> list[dict]:
    p=Path(path)
    if p.suffix.lower()==".csv":
        rows=pd.read_csv(p).fillna("").to_dict(orient="records")
    elif p.suffix.lower() in {".json",".jsonl"}:
        if p.suffix.lower()==".jsonl": rows=[json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
        else:
            obj=json.loads(p.read_text(encoding="utf-8")); rows=obj if isinstance(obj,list) else obj.get("records",[])
    else: raise ValueError("Supported archival imports: CSV, JSON, JSONL")
    return [{str(k).strip().lower():v for k,v in row.items()} for row in rows]

def normalize_roll_records(path: str, collection: str) -> list[dict]:
    records=[]
    for i,row in enumerate(load_records(path)):
        records.append({"collection":collection,"record_id":f"{collection}:{i}","fields":row,"search_text":" | ".join(str(v) for v in row.values() if str(v).strip())})
    return records

# Operators supply lawfully obtained source exports. The importer intentionally does not scrape genealogy paywalls.
