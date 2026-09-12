from __future__ import annotations

import errno
import os
import re
import shutil
import tempfile
import threading
from pathlib import Path
from dotenv import dotenv_values

KEY_PATTERN=re.compile(r"^[A-Z][A-Z0-9_]*$")
LINE_PATTERN=re.compile(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=")
MANAGED_KEYS={
"ACTIVE_STATUS_TEXT","ALLOWED_ORIGINS","CLASH_SETTINGS_TEMPLATE","CLASH_SUBSCRIPTION_TEMPLATE","COMPOSE_PROFILES","CUSTOM_TEMPLATES_DIRECTORY","DASHBOARD_PATH","DEBUG","DISABLED_STATUS_TEXT","DISABLE_RECORDING_NODE_USAGE","DISCORD_WEBHOOK_URL","DOCS","EXPIRED_STATUS_TEXT","EXTERNAL_CONFIG","GRPC_USER_AGENT_TEMPLATE","HOME_PAGE_TEMPLATE","JOB_CORE_HEALTH_CHECK_INTERVAL","JOB_RECORD_NODE_USAGES_INTERVAL","JOB_RECORD_USER_USAGES_INTERVAL","JOB_REVIEW_USERS_INTERVAL","JOB_SEND_NOTIFICATIONS_INTERVAL","JWT_ACCESS_TOKEN_EXPIRE_MINUTES","LIMITED_STATUS_TEXT","LOGIN_NOTIFY_WHITE_LIST","MUX_TEMPLATE","NOTIFY_IF_DATA_USAGE_PERCENT_REACHED","NOTIFY_IF_DAYS_LEFT_REACHED","NOTIFY_LOGIN","NOTIFY_STATUS_CHANGE","NOTIFY_USER_CREATED","NOTIFY_USER_DATA_USED_RESET","NOTIFY_USER_DELETED","NOTIFY_USER_SUB_REVOKED","NOTIFY_USER_UPDATED","NUMBER_OF_RECURRENT_NOTIFICATIONS","ONHOLD_STATUS_TEXT","POSTGRES_DB","POSTGRES_PASSWORD","POSTGRES_USER","RECURRENT_NOTIFICATIONS_TIMEOUT","SINGBOX_CONFIG_PATH","SINGBOX_EXECUTABLE_PATH","SINGBOX_HEALTH_CHECK_INTERVAL","SINGBOX_HYSTERIA_ENABLED","SINGBOX_SETTINGS_TEMPLATE","SINGBOX_SUBSCRIPTION_TEMPLATE","SINGBOX_TRAFFIC_ACCOUNTING_ENABLED","SINGBOX_TRAFFIC_API_HOST","SINGBOX_TRAFFIC_API_PORT","SQLALCHEMY_DATABASE_URL","SQLALCHEMY_POOL_SIZE","SQLIALCHEMY_MAX_OVERFLOW","SUBSCRIPTION_PAGE_TEMPLATE","SUB_CACHE_MAX_ENTRIES","SUB_CACHE_TTL","SUB_ETAG_ENABLED","SUB_PROFILE_TITLE","SUB_RULES_FROM_DB","SUB_SUPPORT_URL","SUB_TOKEN_DEFAULT_TTL_DAYS","SUB_TOKEN_MAX_PER_USER","SUB_UPDATE_INTERVAL","SUDO_PASSWORD","SUDO_USERNAME","TELEGRAM_API_TOKEN","TELEGRAM_DEFAULT_VLESS_FLOW","TELEGRAM_LOGGER_CHANNEL_ID","TELEGRAM_LOGGER_TOPIC_ID","TELEGRAM_PROXY_URL","TIMESCALE_CHUNK_INTERVAL_DAYS","TIMESCALE_COMPRESS_AFTER_DAYS","TIMESCALE_ENABLED","TIMESCALE_RETENTION_DAYS","USERS_AUTODELETE_DAYS","USER_AGENT_TEMPLATE","USER_AUTODELETE_INCLUDE_LIMITED_ACCOUNTS","USE_CUSTOM_JSON_DEFAULT","USE_CUSTOM_JSON_FOR_HAPP","USE_CUSTOM_JSON_FOR_NPVTUNNEL","USE_CUSTOM_JSON_FOR_STREISAND","USE_CUSTOM_JSON_FOR_V2RAYN","USE_CUSTOM_JSON_FOR_V2RAYNG","UVICORN_HOST","UVICORN_PORT","UVICORN_SSL_CA_TYPE","UVICORN_SSL_CERTFILE","UVICORN_SSL_KEYFILE","UVICORN_UDS","V2RAY_SETTINGS_TEMPLATE","V2RAY_SUBSCRIPTION_TEMPLATE","VITE_BASE_API","WEBHOOK_SECRET","XRAY_ASSETS_PATH","XRAY_EXCLUDE_INBOUND_TAGS","XRAY_EXECUTABLE_PATH","XRAY_FALLBACKS_INBOUND_TAG","XRAY_JSON","XRAY_SUBSCRIPTION_PATH","XRAY_SUBSCRIPTION_URL_PREFIX"}
SECRET_PARTS=("PASSWORD","SECRET","TOKEN","PRIVATE","DATABASE_URL","WEBHOOK_URL","API_KEY")
_LOCK=threading.RLock()

def is_secret(key:str)->bool:return any(part in key for part in SECRET_PARTS)
def category(key:str)->str:
 prefix=key.split("_",1)[0]
 return {"SINGBOX":"sing-box","XRAY":"xray","SUB":"subscriptions","TELEGRAM":"telegram","POSTGRES":"database","TIMESCALE":"database","SQLALCHEMY":"database","SQLIALCHEMY":"database","UVICORN":"server","VITE":"server","JOB":"jobs","NOTIFY":"notifications","USE":"subscriptions"}.get(prefix,"general")
def _path(path:str)->Path:
 target=Path(path).expanduser()
 if target.is_symlink():raise ValueError("ENV file must not be a symbolic link")
 return target
def read_environment(path:str)->dict:
 target=_path(path);values={k:v for k,v in (dotenv_values(target) if target.exists() else {}).items() if k in MANAGED_KEYS};entries=[]
 for key in sorted(MANAGED_KEYS):
  value=values.get(key);secret=is_secret(key);active=os.environ.get(key)
  entries.append({"key":key,"category":category(key),"secret":secret,"configured":value is not None,"value":None if secret else value,"active":active is not None,"active_value":None if secret else active,"pending":value is not None and value!=active})
 return {"path":str(target),"exists":target.exists(),"writable":os.access(target if target.exists() else target.parent,os.W_OK),"entries":entries}
def _quoted(value:str)->str:
 if "\x00" in value or "\n" in value or "\r" in value:raise ValueError("ENV values must be single-line strings")
 if len(value)>8192:raise ValueError("ENV value is too long")
 return '"'+value.replace("\\","\\\\").replace('"','\\"')+'"'
def update_environment(path:str,changes:list[dict])->dict:
 target=_path(path);normalized={}
 for item in changes:
  key=item.get("key")
  if not isinstance(key,str) or not KEY_PATTERN.fullmatch(key) or key not in MANAGED_KEYS:raise ValueError(f"Unsupported environment key: {key}")
  delete=bool(item.get("delete",False));value=item.get("value")
  if not delete and not isinstance(value,str):raise ValueError(f"A string value is required for {key}")
  normalized[key]=None if delete else value
 if not normalized:return read_environment(path)
 with _LOCK:
  target.parent.mkdir(parents=True,exist_ok=True);lines=target.read_text(encoding="utf-8").splitlines() if target.exists() else [];output=[];handled=set()
  for line in lines:
   match=LINE_PATTERN.match(line);key=match.group(1) if match else None
   if key not in normalized:output.append(line);continue
   if key in handled:continue
   handled.add(key)
   if normalized[key] is not None:output.append(f"{key}={_quoted(normalized[key])}")
  for key,value in normalized.items():
   if key not in handled and value is not None:output.append(f"{key}={_quoted(value)}")
  if target.exists():shutil.copy2(target,target.with_suffix(target.suffix+".bak"))
  fd,tmp=tempfile.mkstemp(prefix=".marzban-env-",suffix=".tmp",dir=target.parent,text=True)
  try:
   with os.fdopen(fd,"w",encoding="utf-8") as f:f.write("\n".join(output)+"\n");f.flush();os.fsync(f.fileno())
   os.chmod(tmp,0o600)
   try:os.replace(tmp,target)
   except OSError as exc:
    if exc.errno!=errno.EBUSY:raise
    with target.open("wb") as destination,open(tmp,"rb") as source:shutil.copyfileobj(source,destination);destination.flush();os.fsync(destination.fileno())
    os.chmod(target,0o600)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
 return read_environment(path)
