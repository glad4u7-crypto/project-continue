"""Bounded GitHub issue command bridge; fixed diagnostics only, never a remote shell."""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys, time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from scripts.colab_dashboard_status import check_local_streamlit

REPOSITORY = "glad4u7-crypto/project-continue"
API_ROOT = f"https://api.github.com/repos/{REPOSITORY}"
AUTHORIZED_LOGIN = "glad4u7-crypto"
COMMAND_RE = re.compile(r"^/pc-run (phase18-tests|compile|dashboard-health|git-status)$")
STATE_PATH = Path(os.environ.get("PROJECT_CONTINUE_AGENT_STATE", "/content/.project_continue_agent_state.json"))
REPO_ROOT = Path(__file__).resolve().parents[1]
TASKS = {
 "phase18-tests": [sys.executable,"-m","pytest","-q","tests/test_dashboard_health_check.py","tests/test_colab_dashboard_status.py","tests/test_colab_control_agent.py"],
 "compile": [sys.executable,"-m","compileall","-q","app.py","core","database","integrations","services","ui","scripts"],
 "git-status": ["git","status","--short","--branch"],
}
def get_token():
 token=os.environ.get("PROJECT_CONTINUE_CONTROL_TOKEN","").strip()
 if token: return token
 try:
  from google.colab import userdata
  return str(userdata.get("PROJECT_CONTINUE_CONTROL_TOKEN") or "").strip()
 except Exception: return ""
def api_request(token,method,url,payload=None):
 data=json.dumps(payload).encode() if payload is not None else None
 req=Request(url,data=data,method=method,headers={"Accept":"application/vnd.github+json","Authorization":f"Bearer {token}","Content-Type":"application/json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"Project-Continue-Colab-Control-Agent/1.0"})
 with urlopen(req,timeout=15) as response:
  raw=response.read(1000000)
  return json.loads(raw.decode()) if raw else None
def load_state():
 try:
  value=json.loads(STATE_PATH.read_text())
  return value if isinstance(value,dict) else {"last_comment_id":0}
 except (OSError,ValueError): return {"last_comment_id":0}
def save_state(state):
 STATE_PATH.parent.mkdir(parents=True,exist_ok=True)
 tmp=STATE_PATH.with_suffix(".tmp")
 tmp.write_text(json.dumps(state))
 tmp.replace(STATE_PATH)
def run_task(task):
 if task=="dashboard-health": return check_local_streamlit()
 command=TASKS.get(task)
 if command is None: return False,"Task is not allow-listed."
 try:
  result=subprocess.run(command,cwd=REPO_ROOT,capture_output=True,text=True,timeout=600 if task=="phase18-tests" else 120,check=False,shell=False,env={**os.environ,"CI":"1","PYTHONDONTWRITEBYTECODE":"1"})
 except subprocess.TimeoutExpired: return False,"Task timed out; no retry was started."
 output=(result.stdout+"\\n"+result.stderr).strip()
 return result.returncode==0,f"Exit code: {result.returncode}\\n{output[-3500:] or '(no output)'}"
def process_comments(token,issue_number,state):
 comments=api_request(token,"GET",f"{API_ROOT}/issues/{issue_number}/comments?per_page=100")
 if not isinstance(comments,list): raise ValueError("Unexpected GitHub comment list.")
 last_id=int(state.get("last_comment_id",0)); processed=0
 for comment in comments:
  cid=int(comment.get("id",0))
  if cid<=last_id: continue
  state["last_comment_id"]=cid
  author=(comment.get("user") or {}).get("login","")
  match=COMMAND_RE.fullmatch(str(comment.get("body") or "").strip())
  if author!=AUTHORIZED_LOGIN or not match: continue
  task=match.group(1); passed,detail=run_task(task)
  report=f"Colab Control Agent: {'PASS' if passed else 'FAIL'}\\nRequest: {cid}\\nTask: {task}\\n\\n{detail[:3500]}\\n\\nArbitrary shell, source edits, restart, deployment and deletion are unsupported."
  api_request(token,"POST",f"{API_ROOT}/issues/{issue_number}/comments",{"body":report})
  processed+=1; save_state(state)
 save_state(state)
 return processed
def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument("--issue",type=int,default=int(os.environ.get("PROJECT_CONTINUE_CONTROL_ISSUE","0")))
 parser.add_argument("--interval-seconds",type=int,default=0)
 args=parser.parse_args(argv)
 if args.issue<=0 or (args.interval_seconds!=0 and not 15<=args.interval_seconds<=86400):
  print("FAIL: positive issue number and interval 0 or 15-86400 required."); return 2
 token=get_token()
 if not token: print("FAIL: configure PROJECT_CONTINUE_CONTROL_TOKEN in Colab Secrets."); return 2
 state=load_state()
 try:
  while True:
   count=process_comments(token,args.issue,state)
   print(f"Control poll complete; {count} task(s) executed.")
   if args.interval_seconds==0: return 0
   time.sleep(args.interval_seconds)
 except KeyboardInterrupt:
  print("Agent stopped; Colab runtime and Streamlit were not stopped."); return 0
 except (HTTPError,URLError,TimeoutError,OSError,ValueError) as exc:
  print(f"FAIL: control bridge unavailable ({type(exc).__name__})."); return 1
if __name__=="__main__": raise SystemExit(main())
