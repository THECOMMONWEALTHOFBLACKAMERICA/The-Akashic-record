from datetime import datetime, timezone
import hashlib, json

def sha256_bytes(data:bytes)->str:return hashlib.sha256(data).hexdigest()

def provenance_record(*,source:str,uri:str,content:bytes,metadata:dict|None=None)->dict:
    return {"source":source,"uri":uri,"sha256":sha256_bytes(content),"retrieved_at":datetime.now(timezone.utc).isoformat(),"metadata":metadata or {}}

def canonical_hash(record:dict)->str:
    return sha256_bytes(json.dumps(record,sort_keys=True,separators=(",",":")).encode())
