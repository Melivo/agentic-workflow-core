"""Actual OpenCode 2.0.25 server + deterministic local HTTP provider + original CLIs.

No FakeHookhost. Gortex receipts are explicitly rebased CONTRACT REPLAYS, never
fresh daemon mutations in /tmp. Runtime setup/install is a separate command.
"""
import ast
from concurrent.futures import ThreadPoolExecutor
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('habit_package_check',ROOT/'scripts/check_habit_feedback.py')
package = importlib.util.module_from_spec(spec); spec.loader.exec_module(package)
HOST_VERSION = 'opencode v2.0.25'
PLUGIN_ID = 'opencode-habit-feedback'
MARKER = 'LOCAL_HABIT_FIXTURE:'
# Exact receipt from this tracked T03 run's real Gortex edit.write (package.json).
# Only path is rebound for a contract replay against an existing fixture file.
REAL_RECEIPT = {'applied_generation':623,'bytes_written':955,'disk_status':'committed',
 'graph_status':'fresh','mutation_receipt':'commit-285',
 'new_sha':'743257f8040812c4ff271cfa15007739301f2a28',
 'path':'agentic-workflow-core/.apm/skills/core-devops/assets/opencode-habit-feedback/package.json',
 'reindex_generation':622,'reindexed':True,'status':'overwritten'}
# Gortex's observed applied receipt is supported, rather than inventing status.
REAL_APPLIED = {'applied_generation':626,'bytes_written':34262,'disk_status':'committed',
 'graph_status':'fresh','mutation_receipt':'commit-287','new_sha':'0bbb828ebcc64c6d5743d10a66cd0b11fc3b9f94',
 'path':'agentic-workflow-core/.apm/skills/core-devops/assets/opencode-habit-feedback/hook/habit_feedback_hook.py',
 'reindex_generation':625,'reindexed':True,'replacements':1,'status':'applied'}
SMELLY = 'def callback(a, b, c, d, e, f, g, h):\n    return a + b + c + d + e + f + g + h\n'
CLEAN = 'def total(values):\n    return sum(values)\n'
OLD_NESTED = 'def decision(value):\n' + ''.join('    '*(i+1)+'if value & %s:\n'%(1<<i) for i in range(12)) + '    '*13+'return 1\n    return 0\n'
IMPROVED = ''.join('def _part%s(value):\n'%part + ''.join('    if not value & %s:\n        return 0\n'%(1<<i) for i in range(part*6,(part+1)*6)) + '    return 1\n\n' for part in range(2)) + 'def decision(value):\n    return _part0(value) * _part1(value)\n'
BAD_METRIC = 'def decision(value):\n    return 0\n'
BASELINE_CASES = frozenset(('native-write-0','active-project-0','portable-core-0','no-detector-writes-0','native-edit-0',
 'native-write-1','active-project-1','portable-core-1','no-detector-writes-1','native-edit-1',
 'original-error-preserved','unqualified-not-clean','unknown-execute-not-scanned','no-files-not-false-clean',
 'receipt-contract-replay','actual-execute-envelope','receipt-overwritten-contract-replay','receipt-original-outside-scope','receipt-dry-run',
 'nested-before','same-branches-improvement','bad-metric-change-rejected-by-safety-net','legitimate-protocol-warning-no-autofix',
 'wrong-config','executable-override','same-version-replacement','disabled','removed','missing-tool','model-visible-original-guide'))

ROUND_ONE_REVIEW_CASES = frozenset(
    ['shadow-'+tool+'-'+directory+'-'+str(link)+suffix
     for tool in ('ruff','deptry','jscpd') for directory in ('.venv-bin','node_modules-.bin')
     for link in (False,True) for suffix in ('','-provider')]
    + ['advisory-real','advisory-provider','advisory-exit-zero-not-empty','repository-md','repository-symlink',
       'guide-config-escape','scope-config-before-spawn','scope-no-repository-helper','scope-ruff-and-gap','scope-provider-gap',
       'optional-repository-detectors-absent','opaque-bash','opaque-provider-bash','opaque-unknownpatch','opaque-provider-unknownpatch',
       'opaque-custom_mcp_mutate','opaque-provider-custom_mcp_mutate','readonly-no-scan',
       'cleanup-timeout','cleanup-overflow','cleanup-exit-race','cleanup-bridge-SIGTERM'])

PREVIOUS_NINETY_CASES = BASELINE_CASES | ROUND_ONE_REVIEW_CASES | frozenset(
    ['round2-path-'+name for name in ('absolute-repository','relative-repository','empty-cwd','directory-symlink-alias','file-symlink-alias')]
    + ['round2-qualified-external-positive','cleanup-concurrent','cleanup-concurrent-disjoint',
       'options-global-a','options-global-b','options-instance-local-env-unchanged',
       'options-bad-sensor-option','options-bad-toolroots-option','options-bad-state-option'])

def branches(source):
    return sum(isinstance(node,ast.If) for node in ast.walk(ast.parse(source)))

def behavior(source):
    ns={}; exec(compile(source,'trusted-test-fixture','exec'),ns)
    return [ns['decision'](x) for x in range(8192)]

def tree(root):
    return {p.relative_to(root).as_posix():package.sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}

def project_inventory(root):
    result=tree(root)
    result.update({p.relative_to(root).as_posix()+'/':'directory' for p in root.rglob('*') if p.is_dir()})
    return result

def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]

class LocalProvider:
    """Implements only deterministic local chat-completion SSE, not an LLM mock host."""
    def __init__(self):
        self.plans={};self.served=set();self.requests=[];self.lock=threading.Lock()
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):
                pass
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                messages=body.get('messages',[])
                text=' '.join(json.dumps(x.get('content','')) for x in messages if x.get('role')=='user')
                ids=[key for key in owner.plans if MARKER+key in text]
                key=ids[-1] if ids else None
                with owner.lock:
                    owner.requests.append({'case':key,'path':self.path,'messages':messages})
                    call=owner.plans.get(key) if key not in owner.served else None
                    if call:owner.served.add(key)
                if call:
                    delta={'role':'assistant','tool_calls':[{'index':0,'id':'call_'+key,'type':'function',
                           'function':{'name':call['tool'],'arguments':json.dumps(call['input'])}}]}
                    finish='tool_calls'
                else:
                    delta={'role':'assistant','content':'Local fixture complete.'};finish='stop'
                self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                chunk={'id':'local-fixture','object':'chat.completion.chunk','created':1,'model':'fixture',
                       'choices':[{'index':0,'delta':delta,'finish_reason':finish}]}
                self.wfile.write(('data: '+json.dumps(chunk)+'\n\ndata: [DONE]\n\n').encode())
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
    @property
    def url(self):
        return 'http://127.0.0.1:%s/v1'%self.server.server_port
    def close(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=3)

class ActualHost:
    def __init__(self,root,installed,provider,*,plugin_options=None,**overrides):
        self.root=root;self.installed=installed;self.provider=provider
        self.env=package.isolated_env(root)
        self.env.update(HABIT_FEEDBACK_STATE_ROOT=str(root/'hook-state'),
                        HABIT_FEEDBACK_PYTHON=str(package.CI/'venv/bin/python3'),
                        HABIT_FEEDBACK_SENSOR=str(package.CI/'venv/bin/habit-sensors'),
                        HABIT_FEEDBACK_MAPPER=str(package.CI/'venv/bin/habit-mapper'))
        if plugin_options is not None:
            for key in ('HABIT_FEEDBACK_SENSOR','HABIT_FEEDBACK_MAPPER','HABIT_FEEDBACK_PYTHON','HABIT_FEEDBACK_STATE_ROOT','HABIT_FEEDBACK_TRUSTED_TOOL_ROOTS'):
                self.env.pop(key,None)
        self.env.update(overrides)
        registration=str(installed) if plugin_options is None else {'package':str(installed),'options':plugin_options}
        self.config=Path(self.env['XDG_CONFIG_HOME'])/'opencode/opencode.json'
        self.config.parent.mkdir(parents=True,exist_ok=True)
        observer=root/'receipt-observer';observer.mkdir()
        self.observer=observer
        self.events=root/'actual-hook-events.jsonl'
        # A separate REAL plugin records host events before the packaged hook.
        # It never replaces host execution or manufactures event envelopes.
        (observer/'index.js').write_text('import fs from "node:fs"; export default {id:"local.habit.observer",async setup(ctx){await ctx.tool.hook("execute.after",event=>{fs.appendFileSync('+json.dumps(str(self.events))+',JSON.stringify(event)+"\\n")})}};')
        self.settings={'plugins':['*',str(observer),registration],'snapshots':False,'update':'disable',
          'model':'fixture/fixture','providers':{'fixture':{'package':'@opencode/ai/providers/openai-compatible',
          'settings':{'baseURL':provider.url},'models':{'fixture':{'modelID':'fixture',
          'capabilities':{'tools':True,'input':['text'],'output':['text']},'limit':{'context':32768,'output':8192}}}}},
          'experimental':{'policies':[{'action':'provider.use','resource':'*','effect':'deny'},
                                     {'action':'provider.use','resource':'fixture','effect':'allow'}]}}
        self.write_config()
        binary=shutil.which('opencode')
        package.require(binary is not None,'OpenCode host missing; no auto-download')
        package.require(package.run([binary,'--version'],root,self.env).strip()==HOST_VERSION,'host version mismatch')
        self.port=free_port();self.url='http://127.0.0.1:%s'%self.port
        self.logs=[];self.password=None;self.ready=threading.Event()
        self.process=subprocess.Popen([binary,'serve','--hostname','127.0.0.1','--port',str(self.port),'--print-logs'],
                   cwd=root,env=self.env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        def drain():
            for line in self.process.stdout:
                if line.startswith('server password '):
                    self.password=line.strip().split('server password ',1)[1];self.ready.set()
                    self.logs.append('[redacted isolated server authentication]\n')
                else:self.logs.append(line)
        self.reader=threading.Thread(target=drain,daemon=True);self.reader.start()
        if not self.ready.wait(20):
            self.close();raise package.CheckError('isolated server failed to become ready: '+''.join(self.logs)[-2000:])
        # Actual host's live schema proves V2 endpoint contracts, not V1 defaults.
        schema=self.api('/openapi.json')
        for path in ('/api/session','/api/session/{sessionID}/prompt','/api/plugin'):
            package.require(path in schema['paths'],'live V2 schema endpoint missing: '+path)
        (root/'openapi.json').write_text(json.dumps(schema))
        self.cases=[]
    def write_config(self):
        self.config.write_text(json.dumps(self.settings))
    def api(self,path,data=None):
        auth=base64.b64encode(('opencode:'+self.password).encode()).decode()
        request=urllib.request.Request(self.url+path,data=json.dumps(data).encode() if data is not None else None,
                    headers={'Authorization':'Basic '+auth,'Content-Type':'application/json'})
        try:
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(request,timeout=120) as response:raw=response.read()
        except urllib.error.HTTPError as exc:
            raise package.CheckError('isolated API error %s: %s'%(exc.code,exc.read().decode()[:2000])) from exc
        return json.loads(raw) if raw else None
    def plugins(self,project):
        return self.api('/api/plugin?location%5Bdirectory%5D='+str(project))['data']
    def plugin_state(self,project):
        rows=[p for p in self.plugins(project) if p['id']==PLUGIN_ID]
        return rows[0] if rows else None
    def await_plugin(self,project,predicate):
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            state=self.plugin_state(project)
            if predicate(state):return state
            time.sleep(.1)
        raise package.CheckError('actual plugin lifecycle transition not observed: '+repr(state))
    def call(self,key,project,tool,input):
        before=project_inventory(project)
        self.provider.plans[key]={'tool':tool,'input':input}
        sid=self.api('/api/session',{'location':{'directory':str(project)},'title':key,
                'model':{'providerID':'fixture','id':'fixture'},
                'permissions':[{'action':'*','resource':'*','effect':'allow'}]})['data']['id']
        self.api('/api/session/'+sid+'/prompt',{'text':MARKER+key})
        self.api('/api/experimental/session/'+sid+'/wait',{})
        messages=self.api('/api/session/'+sid+'/message')
        tools=[p for m in messages['data'] for p in m.get('content',[]) if p.get('type')=='tool']
        package.require(len(tools)==1 and tools[0]['name']==tool,'real host did not execute exactly the requested tool: '+repr(tools))
        state=tools[0]['state']; content=state.get('content',[])
        text=content if isinstance(content,str) else '\n'.join(p.get('text','') for p in content if p.get('type')=='text')
        after=project_inventory(project)
        changed={name for name in set(before)|set(after) if before.get(name)!=after.get(name)}
        allowed=set()
        if tool in ('write','edit') and state['status']=='completed':
            target=Path(input['path']).resolve()
            if target.is_relative_to(project):
                allowed.add(target.relative_to(project).as_posix())
                allowed.update(parent.relative_to(project).as_posix()+'/' for parent in target.parents if parent!=project and parent.is_relative_to(project))
        package.require(changed<=allowed, 'detector/config side effects in project: '+repr(changed-allowed))
        record={'case':key,'session':sid,'project':str(project),'tool':tool,'state':state,'text':text,'project_changes':sorted(changed)}
        self.cases.append(record)
        (self.root/('case-'+key+'.json')).write_text(json.dumps(messages,indent=2))
        return text,state
    def close(self):
        if hasattr(self,'process'):
            if self.process.poll() is None:
                self.process.terminate()
                try:self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=5)
            self.reader.join(timeout=3)
            self.process.stdout.close()
            (self.root/'server.log').write_text(''.join(self.logs))
        self.password=None

def process_identity(pid):
    try:
        data=Path('/proc/%s/stat'%pid).read_text().rsplit(')',1)[1].split()
        return {'pid':pid,'ppid':int(data[1]),'pgid':int(data[2]),'start':int(data[19]),'state':data[0]}
    except (OSError,ValueError,IndexError):return None

def owned_survivors(records):
    return [now for record in records if (now:=process_identity(record['pid'])) and now['start']==record['start']]

def trusted_detector(directory,record_file,mode):
    """Explicitly trusted test detector OUTSIDE the scanned repo; no guard bypass."""
    directory.mkdir(parents=True,exist_ok=True)
    source = r'''import os,sys,time,json,subprocess,signal
from pathlib import Path
record=Path(RECORD)
def identity(pid,kind):
 try:
  tail=Path('/proc/%s/stat'%pid).read_text().rsplit(')',1)[1].split()
  return {'pid':pid,'ppid':int(tail[1]),'pgid':int(tail[2]),'start':int(tail[19]),'state':tail[0],'kind':kind}
 except OSError:return None
def put(pid,kind):
 row=identity(pid,kind)
 if row:
  with record.open('a') as f:f.write(json.dumps(row)+'\n')
put(os.getpid(),'detector')
put(os.getppid(),'original-helper')
helper=identity(os.getppid(),'helper')
if helper:put(helper['ppid'],'original-cli')
child_code="import os,time,json;from pathlib import Path;p=Path("+repr(str(record))+");s=Path('/proc/%s/stat'%os.getpid()).read_text().rsplit(')',1)[1].split();f=p.open('a');f.write(json.dumps({'pid':os.getpid(),'ppid':int(s[1]),'pgid':int(s[2]),'start':int(s[19]),'state':s[0],'kind':'detached-child'})+'\\n');f.close();time.sleep(20)"
child=subprocess.Popen([sys.executable,'-B','-c',child_code],start_new_session=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
end=time.monotonic()+2
while time.monotonic()<end and 'detached-child' not in record.read_text():time.sleep(.01)
if MODE=='overflow':
 print(json.dumps([{'code':'PLR0913','filename':'src/target.py','location':{'row':1,'column':1},'message':'x'*30000}]),flush=True)
elif MODE=='exit-race':print('[]',flush=True)
else:time.sleep(20)
'''.replace('RECORD',repr(str(record_file))).replace('MODE',repr(mode))
    path=directory/'ruff';path.write_text('#!'+str(package.CI/'venv/bin/python3')+'\n'+source);path.chmod(0o700)
    return path

CLEANUP_DRIVER = r'''import importlib.util,json,os,sys,subprocess,time,threading
sys.dont_write_bytecode=True
from pathlib import Path
installed,project,detectors,work,mode=sys.argv[1:]
work=Path(work);trusted=work/'mapper';trusted.mkdir()
(trusted/'config.toml').write_text('plugins=["generic","python"]\nfiles=["**/*.py"]\n')
spec=importlib.util.spec_from_file_location('packed_cleanup_adapter',Path(installed)/'adapter/habit_feedback_pipeline.py')
a=importlib.util.module_from_spec(spec);sys.modules[spec.name]=a;spec.loader.exec_module(a)
def identity(pid):
 s=a._proc_stat(pid)
 return {'pid':pid,'ppid':s[0],'pgid':s[1],'start':s[2],'state':s[3]} if s else None
def rows(path):return [json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
def remaining(records):return [r for r in records if (s:=a._proc_stat(r['pid'])) and s[2]==r['start']]
controls=[];owners=[];stop=threading.Event();signals=[];reaps=[]
def own_control(label,delay=0):
 if delay:time.sleep(delay)
 p=subprocess.Popen([sys.executable,'-B','-c','import time;time.sleep(20)'],start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
 item={'label':label,'before':identity(p.pid)};controls.append(item)
 stop.wait(15)
 item['after']=identity(p.pid)
 p.terminate();item['owner_exit']=p.wait(timeout=3)
def owner(label,delay=0):
 t=threading.Thread(target=own_control,args=(label,delay),name='owner-'+label);t.start();owners.append(t)
owner('before')
while not controls:time.sleep(.01)
time.sleep(.12)
# Delegated real OS calls, never fake signalling/reaping or broad env inspection.
oldkill,oldkillpg,oldwait=os.kill,os.killpg,os.waitpid
def kill(pid,sig):signals.append({'kind':'kill','id':pid,'signal':sig});return oldkill(pid,sig)
def killpg(pgid,sig):signals.append({'kind':'killpg','id':pgid,'signal':sig});return oldkillpg(pgid,sig)
def waitpid(pid,flags):
 out=oldwait(pid,flags)
 if out[0]:reaps.append({'requested':pid,'returned':out[0],'status':out[1]})
 return out
os.kill,os.killpg,os.waitpid=kill,killpg,waitpid
def concurrent_controls():
 deadline=time.monotonic()+5
 while not (work/'pids.jsonl').exists():
  if time.monotonic()>deadline:raise RuntimeError('original detector never started')
  time.sleep(.005)
 owner('during');owner('after-stage-begin',.2)
watch=threading.Thread(target=concurrent_controls,name='during-stage-control');watch.start()
env=dict(os.environ,PATH=detectors+':'+os.environ['PATH'],TMPDIR=str(work),RUFF_CACHE_DIR=str(work/'ruff-cache'),PYTHONDONTWRITEBYTECODE='1')
def run(directory,deadline,limit):
 local_env=dict(env,PATH=str(directory)+':'+os.environ['PATH'])
 return a.run_pipeline(Path(project),sensor_executable=Path(os.environ['HABIT_CI'])/'venv/bin/habit-sensors',mapper_executable=Path(os.environ['HABIT_CI'])/'venv/bin/habit-mapper',file='src/target.py',trusted_config_root=trusted,mapper_project_root=trusted,env=local_env,trusted_tool_roots=[Path(directory)],sensor_timeout_s=deadline,max_output_bytes=limit)
other={};thread=None;other_after_first=[]
try:
 if mode=='concurrent':
  second=Path(detectors).parent/'second-stage-bin'
  def parallel():other['result']=run(second,3.5,1000000)
  thread=threading.Thread(target=parallel,name='second-original-pipeline');thread.start()
 result=run(Path(detectors),1.5 if mode in ('timeout','concurrent') else 5,4096 if mode=='overflow' else 1000000)
 if mode=='concurrent':
  second_rows=rows(work/'second-pids.jsonl');other_after_first=remaining(second_rows)
  thread.join(timeout=8)
  if thread.is_alive():raise RuntimeError('parallel original pipeline failed to close')
 watch.join(timeout=6)
 # Wait until both ordinary-child owners actually created their own processes.
 deadline=time.monotonic()+3
 while len(controls)<3 and time.monotonic()<deadline:time.sleep(.01)
 records=rows(work/'pids.jsonl');survivors=remaining(records)
 other_records=rows(work/'second-pids.jsonl') if mode=='concurrent' else []
 live_controls=[identity(c['before']['pid']) for c in controls]
 os.kill,os.killpg,os.waitpid=oldkill,oldkillpg,oldwait
 stop.set()
 for t in owners:t.join(timeout=4)
 ids={c['before']['pid'] for c in controls};groups={c['before']['pgid'] for c in controls}
 unrelated_signals=[s for s in signals if s['id'] in (groups if s['kind']=='killpg' else ids)]
 unrelated_reaps=[s for s in reaps if s['returned'] in ids]
 print(json.dumps({'status':result.sensor.status,'records':records,'survivors':survivors,'controls':controls,'controls_alive_after_cleanup':all(s is not None and s['state']!='Z' for s in live_controls),'unrelated_signals':unrelated_signals,'unrelated_reaps':unrelated_reaps,'signals':signals,'reaps':reaps,'other_records':other_records,'other_alive_after_first_cleanup':other_after_first,'other_status':other.get('result').sensor.status if other.get('result') else None,'other_survivors':remaining(other_records),'gaps':result.not_scanned}),flush=True)
finally:
 os.kill,os.killpg,os.waitpid=oldkill,oldkillpg,oldwait
 stop.set()
 for t in owners:t.join(timeout=4)
 if thread:thread.join(timeout=8)
'''


def fixture_tools(host,driver,installed):
    """Real SDK tools with enumerated fixture actions; opaque events execute no code."""
    folder=host.root/'fixture-tools';folder.mkdir()
    source='''import {spawn} from "node:child_process";import fs from "node:fs";
export default {id:"local.habit.review.fixtures",async setup(ctx){
 await ctx.tool.hook("execute.after",event=>{fs.appendFileSync(POST,JSON.stringify(event)+"\\n")});
 await ctx.tool.transform(e=>{
 for(const name of ["bash","unknownpatch","custom_mcp_mutate"]) e.add({name,options:{codemode:false},output:{type:"object",additionalProperties:true},description:"Controlled opaque event fixture; does not execute commands",input:{type:"object",properties:{opaque:{type:"string"}},required:["opaque"],additionalProperties:false},execute:async()=>({content:"controlled event ORIGINAL",output:{fixture:true},metadata:{controlledEventOnly:true}})});
 e.add({name:"habit_fixture_cleanup",options:{codemode:false},output:{type:"object",additionalProperties:true},description:"Trusted cleanup test of the actual installed original CLI pipeline",input:{type:"object",properties:{args:{type:"array",items:{type:"string"}}},required:["args"]},execute:({args})=>new Promise((resolve,reject)=>{
 const p=spawn(PYTHON,["-B",DRIVER,INSTALLED,...args],{env:{...process.env,HABIT_CI:CI},stdio:["ignore","pipe","pipe"]});let out="",err="";
 p.stdout.on("data",b=>out+=b);p.stderr.on("data",b=>err+=b);p.on("error",reject);p.on("close",code=>{if(code)reject(Error(err));else resolve({content:out,output:JSON.parse(out),metadata:{originalCLI:true,trustedFixtureDetector:true}})});
 })});
 });}};
'''
    source=source.replace('HABIT_CI:CI','HABIT_CI:'+json.dumps(str(package.CI)))
    for name,value in [('PYTHON',str(package.CI/'venv/bin/python3')),('DRIVER',str(driver)),('INSTALLED',str(installed)),('POST',str(host.root/'post-hook-events.jsonl'))]:source=source.replace(name,json.dumps(value))
    (folder/'index.js').write_text(source)
    host.settings['plugins']=['*',str(host.observer),str(installed),str(folder)];host.write_config()

def verify_effective_coverage_runtime(root,installed,provider):
    """Manual RV06: delegate actual installed bridge, observe machine + SDK + HTTP."""
    area=root/'manual-rv06';area.mkdir();projects=[area/'project-a',area/'project-b']
    for p in projects:(p/'src').mkdir(parents=True);(p/'.habit-hooks').mkdir()
    tape=area/'original-bridge-machine-results.jsonl';binary_dir=area/'qualified-bridge-observer-bin';binary_dir.mkdir()
    python=binary_dir/'python3'
    source='''import sys,os,json,subprocess
from pathlib import Path
sys.dont_write_bytecode=True
payload=sys.stdin.buffer.read()
p=subprocess.run([PYTHON,"-B",*sys.argv[1:]],input=payload,capture_output=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1"))
# Transport observation only: no pattern matching, smell routing or output rewriting.
if p.returncode==0:
 record={"id":json.loads(payload)["id"],"machine":json.loads(p.stdout)}
 with Path(TAPE).open('a') as f:f.write(json.dumps(record)+'\\n')
sys.stdout.buffer.write(p.stdout);sys.stderr.buffer.write(p.stderr);sys.exit(p.returncode)
'''.replace('PYTHON,',json.dumps(str(package.CI/'venv/bin/python3'))+',').replace('TAPE',repr(str(tape)))
    python.write_text('#!'+str(package.CI/'venv/bin/python3')+'\n'+source);python.chmod(0o700)
    options={'sensor':str(package.CI/'venv/bin/habit-sensors'),'mapper':str(package.CI/'venv/bin/habit-mapper'),
             'python':str(python),'trustedToolRoots':[],'stateRoot':str(area/'controlled-state')}
    base='plugins=["generic","python"]\nfiles=["**/*.py"]\n'
    oversized=CLEAN+'\n'+''.join('# inert padding %s\n'%i for i in range(230))
    # Preference tables remain byte-identical: no force enabling or custom matcher.
    cases=[('enabled-ruff',base,SMELLY,None,'too-many-parameters',False),
      ('disabled-ruff',base+'[sensors.ruff]\ndisabled=true\n',SMELLY,'ruff',None,False),
      ('excluded-ruff',base+'[sensors.ruff]\nfiles=["unrelated/*.py"]\n',SMELLY,'ruff',None,False),
      ('matching-ruff-unqualified',base+'[sensors.ruff]\nfiles=["src/*.py"]\n',SMELLY,'ruff','too-many-parameters',False),
      ('disabled-line-count',base+'[sensors.line-count]\ndisabled=true\n',oversized,'line-count',None,False),
      ('excluded-line-count',base+'[sensors.line-count]\nfiles=["unrelated/*.py"]\n',oversized,'line-count',None,False),
      ('matching-line-count-unqualified',base+'[sensors.line-count]\nfiles=["src/*.py"]\n',oversized,'line-count','oversized-file',False),
      ('enabled-line-count',base,oversized,None,'oversized-file',False),
      ('partial-measured-line-count',base+'[sensors.ruff]\ndisabled=true\n',oversized,'ruff','oversized-file',False),
      ('partial-advisory-line-count',base+'[sensors.ruff]\ndisabled=true\n[smells.oversized-file]\nseverity="suggest"\n',oversized,'ruff','oversized-file',True)]
    host=None;results=[];observations=[]
    try:
        host=ActualHost(area/'host',installed,provider,plugin_options=options,PATH='/usr/bin:/bin')
        for i,project in enumerate(projects):
            for name,config,content,missing,finding,advisory in cases:
                key='rv06-'+str(i)+'-'+name;cfg=project/'.habit-hooks/config.toml';cfg.write_text(config)
                before=package.sha(cfg.read_bytes());target=project/'src'/(name+'.py')
                text,state=host.call(key,project,'write',{'path':str(target),'content':content})
                rows=[json.loads(s) for s in tape.read_text().splitlines()]
                entry=next(r['machine']['scanned'][0] for r in rows if r['id']=='call_'+key)
                visible=' '.join(json.dumps(m) for req in provider.requests if req['case']==key for m in req['messages'] if m.get('role')=='tool')
                package.require(state['status']=='completed' and 'Created file successfully' in text and package.sha(cfg.read_bytes())==before,'RV06 preference/result changed: '+key)
                if missing:
                    package.require(not entry['complete'] and not entry['clean'] and any("sensor '"+missing+"'" in gap for gap in entry['not_scanned']), 'missing machine coverage: '+key+' '+repr(entry))
                    package.require(missing in text and missing in visible and 'coverage is partial' in text and ': clean (' not in text,'missing SDK/provider partial warning: '+key+' '+text)
                else:
                    package.require(entry['complete'] and entry['findings']>=1 and ': clean (' not in text,'enabled original control missing or advisory hidden: '+key)
                if finding:
                    package.require(entry['findings']>=1 and finding in entry['verdict'] and finding in text and 'Core guidance' in text and 'Core guidance' in visible,'actual measured coaching hidden: '+key+' '+text)
                else:
                    package.require(entry['findings']==0,'excluded sensor was force enabled or invented finding: '+key)
                if advisory:
                    package.require(entry['advisory'] and entry['stages']['mapper']['exit_code']==0 and 'Core guidance' in text,'partial advisory semantics lost: '+key)
                observations.append({'case':key,'config':config,'config_preserved':True,'entry':entry,'provider_visible':True})
                results.append(key)
        (area/'coverage-report.json').write_text(json.dumps(observations,indent=2)+'\n')
        return {'cases':results,'projects':[str(p) for p in projects],'evidence':str(area),'original_bridge_machine_tape':str(tape),'matching_policy':'no local matcher; non-None original files overrides conservatively unqualified'}
    finally:
        if host:host.close()

def verify_options_runtime(root,installed,provider):
    """Persistent global V2 package/options, two actual locations, no launch grants."""
    area=root/'persistent-options';area.mkdir();results=[];host=None
    projects=[area/'project-a',area/'project-b']
    for p in projects:(p/'src').mkdir(parents=True)
    options={'sensor':str(package.CI/'venv/bin/habit-sensors'),
             'mapper':str(package.CI/'venv/bin/habit-mapper'),
             'python':str(package.CI/'venv/bin/python3'),
             'trustedToolRoots':[], 'stateRoot':str(area/'owned-options-state')}
    tape=area/'env-and-result-observers.jsonl'
    def observer(folder,phase):
        folder.mkdir()
        source='''import fs from "node:fs";import crypto from "node:crypto";
export default {id:ID,async setup(ctx){
 const snapshot=()=>({envDigest:crypto.createHash("sha256").update(JSON.stringify(Object.entries(process.env).sort())).digest("hex"),hasSensor:Object.hasOwn(process.env,"HABIT_FEEDBACK_SENSOR"),hasMapper:Object.hasOwn(process.env,"HABIT_FEEDBACK_MAPPER"),hasPython:Object.hasOwn(process.env,"HABIT_FEEDBACK_PYTHON"),hasToolRoots:Object.hasOwn(process.env,"HABIT_FEEDBACK_TRUSTED_TOOL_ROOTS"),hasStateRoot:Object.hasOwn(process.env,"HABIT_FEEDBACK_STATE_ROOT")});
 fs.appendFileSync(TAPE,JSON.stringify({phase:PHASE+"-setup",directory:ctx.location.directory,...snapshot()})+"\\n");
 await ctx.tool.hook("execute.after",event=>fs.appendFileSync(TAPE,JSON.stringify({phase:PHASE,...snapshot(),event})+"\\n"));
}};
'''
        for key,value in [('ID','local.options.'+phase),('TAPE',str(tape)),('PHASE',phase)]:source=source.replace(key,json.dumps(value))
        (folder/'index.js').write_text(source)
    before=area/'observer-before';after=area/'observer-after';observer(before,'before');observer(after,'after')
    try:
        host=ActualHost(area/'host',installed,provider,plugin_options=options,PATH='/usr/bin:/bin')
        forbidden=('HABIT_FEEDBACK_SENSOR','HABIT_FEEDBACK_MAPPER','HABIT_FEEDBACK_PYTHON','HABIT_FEEDBACK_TRUSTED_TOOL_ROOTS','HABIT_FEEDBACK_STATE_ROOT')
        package.require(not any(k in host.env for k in forbidden),'options-only fixture leaked launch bindings')
        launch_before=dict(host.env)
        host.settings['plugins']=['*',str(before),str(host.observer),{'package':str(installed),'options':options},str(after)];host.write_config()
        registrations=json.loads(host.config.read_text())['plugins']
        package.require(any(isinstance(x,dict) and x.get('options')==options for x in registrations),'global object registration missing')
        keys=['options-global-a','options-global-b']
        # Preseed names to keep provider plan iteration stable during concurrent sessions.
        for key,p in zip(keys,projects):provider.plans[key]={'tool':'write','input':{'path':str(p/'src/callback.py'),'content':SMELLY}}
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(host.call,key,p,'write',{'path':str(p/'src/callback.py'),'content':SMELLY}) for key,p in zip(keys,projects)]
            actual=[f.result() for f in futures]
        events=[json.loads(s) for s in tape.read_text().splitlines()]
        for key,p,(text,state) in zip(keys,projects,actual):
            package.require(state['status']=='completed' and 'Created file successfully' in text and 'Core guidance' in text and 'INCOMPLETE' not in text,'options-only original pipeline failed: '+text)
            pair={e['phase']:e for e in events if e.get('event',{}).get('id')=='call_'+key}
            package.require(set(pair)=={'before','after'},'parallel observer event pair missing')
            original=pair['before']['event']['result'];modified=pair['after']['event']['result']
            package.require(original.get('metadata')==modified.get('metadata') and original.get('output')==modified.get('output'),'options content transport lost original metadata/output')
            initial=original.get('content');final=modified.get('content')
            preserved=final.startswith(initial) if isinstance(initial,str) and isinstance(final,str) else isinstance(initial,list) and final[:len(initial)]==initial
            package.require(preserved and 'Core guidance' in json.dumps(final),'original content not preserved')
            visible=' '.join(json.dumps(m) for req in provider.requests if req['case']==key for m in req['messages'] if m.get('role')=='tool')
            package.require('Core guidance' in visible and str(p) in str(host.cases),'options guidance did not reach actual provider')
            results.append(key)
        package.require(len({e['envDigest'] for e in events})==1 and host.env==launch_before,'instance/global process environment mutated')
        package.require(all(not any(e.get(k) for k in ('hasSensor','hasMapper','hasPython','hasToolRoots','hasStateRoot')) for e in events),'parallel plugin received leaked environment grant')
        package.require(len({e['directory'] for e in events if e['phase'].endswith('-setup')})==2,'two actual plugin locations not observed')
        results.append('options-instance-local-env-unchanged')
        host.close();host=None
        for key,override in [('bad-sensor-option',{'sensor':17}),('bad-toolroots-option',{'trustedToolRoots':'not-an-array'}),('bad-state-option',{'stateRoot':str(projects[0])})]:
            host=ActualHost(area/key,installed,provider,plugin_options=dict(options,**override),PATH='/usr/bin:/bin')
            text,state=host.call('options-'+key,projects[0],'write',{'path':str(projects[0]/('src/'+key+'.py')),'content':SMELLY})
            package.require(state['status']=='completed' and 'Created file successfully' in text and ('NOT RUN' in text or 'NOT SCANNED' in text or 'INCOMPLETE' in text) and 'Core guidance' not in text,'bad option was silent/fell back: '+text)
            results.append('options-'+key)
            host.close();host=None
        return {'cases':results,'evidence':str(area),'registration':'global isolated V2 package/options object','projects':[str(p) for p in projects],'process_env_grants_present':False,'env_mutation':False}
    finally:
        if host:host.close()

def verify_round_two_path_cases(area,project,installed,provider,positive_host):
    results=[];marker=area/'round2-repo-marker.executed'
    tools=project/'tools';tools.mkdir();program=tools/'ruff'
    program.write_text('#!/bin/sh\nprintf marker > '+str(marker)+'\nprintf "[]"\n');program.chmod(0o700)
    (project/'ruff').symlink_to(program)
    alias=area/'external-directory-alias';alias.symlink_to(tools,target_is_directory=True)
    alias_bin=area/'external-file-alias-bin';alias_bin.mkdir();(alias_bin/'ruff').symlink_to(program)
    base=positive_host.env['PATH']
    forms={'absolute-repository':str(tools)+':'+base,'relative-repository':'tools:'+base,
           'empty-cwd':':'+base,'directory-symlink-alias':str(alias)+':'+base,'file-symlink-alias':str(alias_bin)+':'+base}
    for name,path in forms.items():
        testhost=None
        try:
            testhost=ActualHost(area/('path-host-'+name),installed,provider,PATH=path)
            key='round2-path-'+name
            text,state=testhost.call(key,project,'write',{'path':str(project/'src/path_target.py'),'content':SMELLY+'\n# '+name+'\n'})
            package.require(state['status']=='completed' and 'file successfully' in text and ('INCOMPLETE' in text or 'NOT RUN' in text) and ': clean' not in text and not marker.exists(),'repository PATH program executed/hidden: '+name+' '+text)
            visible=' '.join(json.dumps(m) for req in provider.requests if req['case']==key for m in req['messages'] if m.get('role')=='tool')
            package.require('habit-feedback' in visible,'PATH refusal not model-visible: '+name)
            results.append(key)
        finally:
            if testhost:testhost.close()
    text,state=positive_host.call('round2-qualified-external-positive',project,'write',{'path':str(project/'src/qualified.py'),'content':SMELLY})
    package.require('Core guidance' in text and 'INCOMPLETE' not in text and not marker.exists(),'qualified external original pipeline failed: '+text)
    results.append('round2-qualified-external-positive')
    return results

def verify_review_runtime(root,installed,provider):
    """RV01-05 + Jinja trust regressions through actual host executions."""
    area=root/'review-repros';area.mkdir();project=area/'project';(project/'src').mkdir(parents=True)
    results=[];process_reports=[];host=None;scope_host=None;bridge_host=None;no_repo_host=None
    def check(name,text,ok):
        package.require(ok,'review repro failed '+name+': '+text[:2000]);results.append(name)
    def provider_text(key):
        return '\n'.join(json.dumps(m) for r in provider.requests if r['case']==key for m in r['messages'] if m.get('role')=='tool')
    try:
        host=ActualHost(area/'host',installed,provider)
        # Every detector/directory/form, without ever executing shadows for version checks.
        for tool in ('ruff','deptry','jscpd'):
            for relative in ('.venv/bin','node_modules/.bin'):
                for symlink in (False,True):
                    key='shadow-'+tool+'-'+relative.replace('/','-')+'-'+str(symlink)
                    marker=area/(key+'.executed');external=area/(key+'.program')
                    external.write_text('#!/bin/sh\nprintf marker > '+str(marker)+'\nprintf "[]"\n');external.chmod(0o700)
                    shadow=project/relative/tool;shadow.parent.mkdir(parents=True,exist_ok=True)
                    if symlink:shadow.symlink_to(external)
                    else:shutil.copyfile(external,shadow);shadow.chmod(0o700)
                    text,state=host.call(key,project,'write',{'path':str(project/'src/target.py'),'content':SMELLY+'\n# '+key+'\n'})
                    check(key,text,not marker.exists() and 'file successfully' in text and ('INCOMPLETE' in text or 'not scanned:' in text))
                    check(key+'-provider',provider_text(key),'habit-feedback' in provider_text(key))
                    shadow.unlink()
        results.extend(verify_round_two_path_cases(area,project,installed,provider,host))
        # Actual suggest finding/exit-zero coaching, not a fabricated mapper output.
        hh=project/'.habit-hooks';hh.mkdir()
        (hh/'config.toml').write_text('plugins=["generic","python"]\nfiles=["**/*.py"]\n[smells.too-many-parameters]\nseverity="suggest"\n')
        text,state=host.call('advisory-real',project,'write',{'path':str(project/'src/advisory.py'),'content':SMELLY})
        check('advisory-real',text,'advisory coaching below' in text and 'Core guidance' in text and ': clean' not in text and 'not scanned:' in text)
        check('advisory-provider',provider_text('advisory-real'),'Core guidance' in provider_text('advisory-real') and 'advisory coaching' in provider_text('advisory-real'))
        spec=importlib.util.spec_from_file_location('advisory_original_adapter',installed/'adapter/habit_feedback_pipeline.py')
        adapter=importlib.util.module_from_spec(spec);sys.modules[spec.name]=adapter;spec.loader.exec_module(adapter)
        mapper_root=next((host.root/'hook-state').glob('*/runtime/config.toml')).parent
        direct=adapter.run_pipeline(project,sensor_executable=package.CI/'venv/bin/habit-sensors',mapper_executable=package.CI/'venv/bin/habit-mapper',file='src/advisory.py',trusted_config_root=mapper_root,mapper_project_root=mapper_root,env=host.env)
        check('advisory-exit-zero-not-empty',direct.mapper.stdout,direct.complete and direct.mapper.exit_code==0 and len(direct.findings)==1 and 'Core guidance' in direct.mapper.stdout)
        (area/'advisory-stage-evidence.json').write_text(json.dumps({'mapper_exit':direct.mapper.exit_code,'findings':direct.findings,'complete':direct.complete,'not_scanned':direct.not_scanned},indent=2))
        # Jinja sentinel must not be rendered/executed, even without custom plugin recipes.
        sentinel=area/'jinja-executed';jinja="{{ cycler.__init__.__globals__.os.popen("+repr('touch '+str(sentinel))+").read() }}"
        guides=hh/'generic/guides';guides.mkdir(parents=True)
        (guides/'too-many-parameters.md').write_text(jinja)
        for form in ('repository-md','repository-symlink'):
            if form.endswith('symlink'):
                (guides/'too-many-parameters.md').unlink();outside=area/'sentinel.md';outside.write_text(jinja);(guides/'too-many-parameters.md').symlink_to(outside)
            text,state=host.call(form,project,'write',{'path':str(project/'src/guide.py'),'content':SMELLY+'\n# '+form+'\n'})
            check(form,text,'Jinja guides refused' in text and not sentinel.exists() and 'INCOMPLETE' in text)
        shutil.rmtree(hh/'generic')
        with (hh/'config.toml').open('a') as f:f.write('guide="../../sentinel.md"\n')
        text,state=host.call('guide-config-escape',project,'write',{'path':str(project/'src/guide.py'),'content':SMELLY})
        check('guide-config-escape',text,'unsafe guide' in text and not sentinel.exists())
        shutil.rmtree(hh)
        # Real CLI instrumentation, not a sensor replacement: exported entry point unchanged.
        ledger=area/'original-dispatch.jsonl';tracer_bin=area/'qualified-cli-observer-bin';tracer_bin.mkdir();tracer=tracer_bin/'habit-sensors';
        tracer.write_text('#!'+str(package.CI/'venv/bin/python3')+'\n'+'''import importlib.metadata as m,json,sys,subprocess,tomllib
from pathlib import Path
record=Path(RECORD)
cfg=Path(sys.argv[sys.argv.index('--config')+1]);doc=tomllib.loads(cfg.read_text())
with record.open('a') as f:f.write(json.dumps({'argv':sys.argv,'config':doc})+'\\n')
original=subprocess.Popen
def traced(*a,**kw):
 with record.open('a') as f:f.write(json.dumps({'spawn':list(a[0])})+'\\n')
 return original(*a,**kw)
subprocess.Popen=traced
next(ep for ep in m.entry_points(group='console_scripts') if ep.name=='habit-sensors').load()()
'''.replace('RECORD',repr(str(ledger))));tracer.chmod(0o700)
        unrelated='\n'.join('def duplicated_%s(x): return x + %s'%(i,i) for i in range(30))+'\n'
        for name in ('unrelated_a.py','unrelated_b.py'):(project/'src'/name).write_text(unrelated)
        (project/'pyproject.toml').write_text('[project]\nname="fixture"\nversion="0.1.0"\ndependencies=["unrelated-nonexistent"]\n')
        external_scope=area/'external-scope';external_scope.mkdir();(external_scope/'outside.py').write_text(unrelated)
        (project/'.jscpd.json').write_text(json.dumps({'path':[str(external_scope)],'minLines':1,'minTokens':1}))
        scope_host=ActualHost(area/'scoped-host',installed,provider,HABIT_FEEDBACK_SENSOR=str(tracer))
        text,state=scope_host.call('scoped-original',project,'write',{'path':str(project/'src/target.py'),'content':SMELLY})
        dispatch=[json.loads(s) for s in ledger.read_text().splitlines()]
        cfg=next(row['config'] for row in dispatch if 'config' in row);spawns=[row['spawn'] for row in dispatch if 'spawn' in row]
        check('scope-config-before-spawn',repr(dispatch),cfg['sensors']['jscpd']['disabled'] and cfg['sensors']['deptry']['disabled'])
        check('scope-no-repository-helper',repr(spawns),bool(spawns) and not any('jscpd.py' in str(a) or 'deptry_sensor.py' in str(a) or str(external_scope) in str(a) or 'unrelated_' in str(a) for a in spawns))
        check('scope-ruff-and-gap',text,'too-many-parameters' in text and 'Core guidance' in text and 'not scanned: duplicated-code' in text and 'not scanned: unused-dependency' in text)
        check('scope-provider-gap',provider_text('scoped-original'),'not scanned: duplicated-code' in provider_text('scoped-original'))
        # The scoped pipeline also succeeds without optional repository detectors.
        only_ruff=area/'only-qualified-ruff';only_ruff.mkdir();(only_ruff/'ruff').symlink_to(package.CI/'venv/bin/ruff')
        path=str(only_ruff)+':/usr/bin:/bin'
        package.require(shutil.which('jscpd',path=path) is None and shutil.which('deptry',path=path) is None,'optional detector absence fixture invalid')
        no_repo_host=ActualHost(area/'no-repository-detectors-host',installed,provider,PATH=path,HABIT_FEEDBACK_SENSOR=str(package.CI/'venv/bin/habit-sensors'),HABIT_FEEDBACK_MAPPER=str(package.CI/'venv/bin/habit-mapper'),HABIT_FEEDBACK_TRUSTED_TOOL_ROOTS=json.dumps([str(only_ruff)]))
        text,state=no_repo_host.call('optional-repository-detectors-absent',project,'write',{'path':str(project/'src/without_optional.py'),'content':SMELLY})
        check('optional-repository-detectors-absent',text,'Core guidance' in text and 'not scanned: duplicated-code' in text and 'not scanned: unused-dependency' in text and 'INCOMPLETE' not in text)
        # Enumerated controlled event tools execute no command or arbitrary input code.
        driver=area/'cleanup-driver.py';driver.write_text(CLEANUP_DRIVER)
        fixture_tools(host,driver,installed)
        deadline=time.monotonic()+15
        while not any(p['id']=='local.habit.review.fixtures' and p['state']['status']=='active' for p in host.plugins(project)):
            package.require(time.monotonic()<deadline,'controlled fixture plugin did not activate')
            time.sleep(.1)
        for name in ('bash','unknownpatch','custom_mcp_mutate'):
            text,state=host.call('opaque-'+name,project,name,{'opaque':'NEVER_PARSE_THIS_PATH_OR_COMMAND'})
            post=[json.loads(s) for s in (host.root/'post-hook-events.jsonl').read_text().splitlines()]
            actual=next(e['result'] for e in post if e['id']=='call_opaque-'+name)
            check('opaque-'+name,text,state['status']=='completed' and 'controlled event ORIGINAL' in text and 'NOT RUN' in text and 'NEVER_PARSE' not in text and actual['output']=={'fixture':True} and actual['metadata']['controlledEventOnly'] is True and 'NOT RUN' in json.dumps(actual['content']))
            check('opaque-provider-'+name,provider_text('opaque-'+name),'NOT RUN' in provider_text('opaque-'+name))
        before=ledger.read_text();text,state=scope_host.call('readonly-real',project,'read',{'path':str(project/'src/target.py')})
        check('readonly-no-scan',text,'habit-feedback' not in text and ledger.read_text()==before)
        # Actual SDK tool launches packaged adapter + actual CLIs, trusted fixtures only.
        for mode in ('timeout','overflow','exit-race','concurrent'):
            work=area/('cleanup-'+mode);work.mkdir();record=work/'pids.jsonl';detectors=work/'trusted-bin';trusted_detector(detectors,record,mode)
            if mode=='concurrent':trusted_detector(work/'second-stage-bin',work/'second-pids.jsonl','concurrent')
            text,state=host.call('cleanup-'+mode,project,'habit_fixture_cleanup',{'args':[str(project),str(detectors),str(work),mode]})
            outcome=json.loads(text);process_reports.append(dict(case=mode,**outcome))
            expected={'timeout':'timed_out','overflow':'output_too_large','exit-race':'ok','concurrent':'timed_out'}[mode]
            check('cleanup-'+mode,text,outcome['status']==expected and not outcome['survivors'] and outcome['controls_alive_after_cleanup'] and len(outcome['controls'])==3 and all(c['owner_exit']==-15 for c in outcome['controls']) and not outcome['unrelated_signals'] and not outcome['unrelated_reaps'] and any(r['kind']=='detached-child' and r['pgid']==r['pid'] for r in outcome['records']))
            if mode=='concurrent':
                check('cleanup-concurrent-disjoint',text,len(outcome['other_alive_after_first_cleanup'])==4 and outcome['other_status']=='timed_out' and not outcome['other_survivors'] and not ({r['pid'] for r in outcome['records']} & {r['pid'] for r in outcome['other_records']}))
        work=area/'cleanup-bridge';work.mkdir();record=work/'pids.jsonl';detectors=work/'trusted-bin';trusted_detector(detectors,record,'bridge')
        # An explicitly qualified common fixture installation preserves the
        # original CLI bytes via external symlinks and selects its trusted
        # lifetime detector without relying on inherited PATH precedence.
        for binary in ('habit-sensors','habit-mapper'):(detectors/binary).symlink_to(package.CI/'venv/bin'/binary)
        bridge_host=ActualHost(area/'bridge-host',installed,provider,PATH=str(detectors)+':'+host.env['PATH'],HABIT_FEEDBACK_SENSOR=str(detectors/'habit-sensors'),HABIT_FEEDBACK_MAPPER=str(detectors/'habit-mapper'),HABIT_FEEDBACK_BRIDGE_TIMEOUT_MS='1500',HABIT_FEEDBACK_TRUSTED_TOOL_ROOTS=json.dumps([str(detectors)]))
        text,state=bridge_host.call('cleanup-bridge',project,'write',{'path':str(project/'src/bridge.py'),'content':SMELLY})
        rows=[json.loads(s) for s in record.read_text().splitlines()];deadline=time.monotonic()+4
        while owned_survivors(rows) and time.monotonic()<deadline:time.sleep(.05)
        survivors=owned_survivors(rows);process_reports.append({'case':'bridge-SIGTERM','records':rows,'survivors':survivors})
        check('cleanup-bridge-SIGTERM',text,'bridge timed out' in text and 'Created file successfully' in text and not survivors)
        (area/'process-evidence.json').write_text(json.dumps(process_reports,indent=2)+'\n')
        return {'cases':results,'processes':process_reports,'evidence':str(area),'trust':'controlled test detectors explicitly outside repo; opaque event tools do not execute input'}
    finally:
        for instance in (bridge_host,no_repo_host,scope_host,host):
            if instance:instance.close()

def preflight(root):
    env=package.isolated_env(root)
    pins={'habit-hooks':'1.5.0','habit-hooks-generic':'1.5.0','habit-hooks-python':'1.5.0','ruff':'0.14.5'}
    output=package.run([str(package.CI/'venv/bin/python3'),'-B','-c',
                       'import importlib.metadata as m,json; print(json.dumps({k:m.version(k) for k in '+repr(list(pins))+'}))'],root,env)
    package.require(json.loads(output)==pins,'original pipeline package version mismatch')
    for command,version in [('habit-sensors','1.5.0'),('habit-mapper','1.5.0'),('ruff','0.14.5'),('node','v22.23.3')]:
        output=package.run([command,'--version'],root,env)
        package.require(version in output,command+' version mismatch: '+output)
        if command in ('jscpd','node'):
            expected=('jscpd '+version) if command=='jscpd' else version
            package.require(output.strip()==expected,command+' exact version mismatch')
    sdk=Path('/tmp/opencode/opencode-plugin-sdk')
    metadata=json.loads((sdk/'meta.json').read_text())['versions']['2.0.25']
    integrity='sha512-'+base64.b64encode(hashlib.sha512((sdk/'pkg.tgz').read_bytes()).digest()).decode()
    package.require(integrity==metadata['dist']['integrity'],'pinned plugin tarball integrity mismatch')
    for name in ('plugin','schema','client'):
        package.require(json.loads((package.SDK/'@opencode'/name/'package.json').read_text())['version']=='2.0.25','SDK version mismatch')
    return {'pins':pins,'plugin_integrity':integrity,'host':HOST_VERSION,'node':'v22.23.3','repository_sensors':'jscpd/deptry disabled; optional for separately authorized repository scans'}

def verify_runtime(report):
    root=Path(tempfile.mkdtemp(prefix='habit-integration-',dir='/tmp/opencode'))
    source_before=package.source_files(); foreign_before=package.sha((ROOT/'opencode.jsonc').read_bytes())
    versions=preflight(root)
    # Runtime copies come only from the actual offline npm-installed tarball,
    # preserving every inventoried byte. No installation/downloader during checks.
    installed=Path(report['installed']); slots=[]
    for name in ('slot-original','slot-replaced'):
        target=root/name/'opencode-habit-feedback';shutil.copytree(installed,target)
        package.require(tree(target)==report['files'],'runtime package differs from npm installation')
        slots.append(target)
    projects=[root/'project-a',root/'project-b']
    for p in projects:(p/'src').mkdir(parents=True)
    provider=LocalProvider();host=None;extra=None;results=[]
    def checked(key,text,condition):
        package.require(condition,'runtime case failed: '+key+'; output='+text[:3000]);results.append(key)
    try:
        host=ActualHost(root/'host',slots[0],provider)
        for i,project in enumerate(projects):
            path=project/'src/callback.py'; key='native-write-'+str(i)
            text,state=host.call(key,project,'write',{'path':str(path),'content':SMELLY})
            checked(key,text,state['status']=='completed' and path.read_text()==SMELLY and
                    'Created file successfully' in text and 'too-many-parameters' in text and 'Core guidance' in text and 'INCOMPLETE' not in text)
            row=host.plugin_state(project)
            checked('active-project-'+str(i),repr(row),row is not None and row['state']['status']=='active')
            checked('portable-core-'+str(i),text,str(slots[0]/'core/.apm') in text and
                    (slots[0]/'core/.apm/skills/core-architecture/references/boundaries-and-abstractions.md').is_file())
            snapshot=tree(project)
            # Execute.after scans must not leave detector caches/config in the project.
            checked('no-detector-writes-'+str(i),repr(snapshot),set(snapshot)=={'src/callback.py'})
            text,state=host.call('native-edit-'+str(i),project,'edit',{'path':str(path),'oldString':SMELLY,'newString':CLEAN})
            checked('native-edit-'+str(i),text,state['status']=='completed' and path.read_text()==CLEAN and 'clean (qualified plugins only; not-scanned smells excluded)' in text and 'not scanned: duplicated-code' in text and 'not scanned: unused-dependency' in text)
        project=projects[0]
        text,state=host.call('error-edit',project,'edit',{'path':str(project/'src/callback.py'),'oldString':'no such text','newString':'x'})
        checked('original-error-preserved',text,state['status']=='error' and '[habit-feedback' not in text)
        text,state=host.call('unqualified-file',project,'write',{'path':str(project/'note.txt'),'content':'not Python'})
        checked('unqualified-not-clean',text,'INCOMPLETE' in text and 'clean (qualified' not in text)
        text,state=host.call('unknown-execute',project,'execute',{'code':'return {nested:{path:"src/callback.py",status:"applied"}}'})
        checked('unknown-execute-not-scanned',text,'NOT SCANNED' in text or 'scan NOT RUN' in text)
        text,state=host.call('no-files-execute',project,'execute',{'code':'return []'})
        checked('no-files-not-false-clean',text,'clean (qualified' not in text)
        # Actual execute tool, explicitly only a rebased receipt CONTRACT REPLAY.
        receipt=dict(REAL_APPLIED,path=str(project/'src/callback.py'))
        text,state=host.call('receipt-contract-replay',project,'execute',{'code':'return '+json.dumps(receipt)})
        checked('receipt-contract-replay',text,'[habit-feedback' in text and 'clean (qualified plugins only; not-scanned smells excluded)' in text)
        observed=[json.loads(line) for line in host.events.read_text().splitlines() if line]
        envelope=next(e['result']['output'] for e in observed if e['id']=='call_receipt-contract-replay')
        checked('actual-execute-envelope',repr(envelope),set(envelope)=={'output','toolCalls','files'} and json.loads(envelope['output'])==receipt)
        text,state=host.call('receipt-overwritten-contract-replay',project,'execute',{'code':'return '+json.dumps(dict(REAL_RECEIPT,path=str(project/'src/callback.py')))})
        checked('receipt-overwritten-contract-replay',text,'clean (qualified plugins only; not-scanned smells excluded)' in text)
        text,state=host.call('receipt-original-outside-scope',project,'execute',{'code':'return '+json.dumps(REAL_APPLIED)})
        checked('receipt-original-outside-scope',text,'NOT SCANNED' in text and 'clean (qualified' not in text)
        text,state=host.call('receipt-dry-run',project,'execute',{'code':'return '+json.dumps(dict(receipt,status='would_apply',dry_run=True))})
        checked('receipt-dry-run',text,'clean (qualified' not in text and 'coaching below' not in text)
        nested=project/'src/decision.py'
        text,state=host.call('nested-before',project,'write',{'path':str(nested),'content':OLD_NESTED})
        checked('nested-before',text,'high-complexity' in text and 'INCOMPLETE' not in text)
        text,state=host.call('same-branches-improvement',project,'edit',{'path':str(nested),'oldString':OLD_NESTED,'newString':IMPROVED})
        checked('same-branches-improvement',text,branches(OLD_NESTED)==branches(IMPROVED)==12 and behavior(OLD_NESTED)==behavior(IMPROVED) and
                'high-complexity' not in text and 'clean (qualified plugins only; not-scanned smells excluded)' in text)
        text,state=host.call('bad-metric-change',project,'edit',{'path':str(nested),'oldString':IMPROVED,'newString':BAD_METRIC})
        checked('bad-metric-change-rejected-by-safety-net',text,branches(BAD_METRIC)<branches(IMPROVED) and
                behavior(BAD_METRIC)!=behavior(OLD_NESTED) and 'clean (qualified plugins only; not-scanned smells excluded)' in text)
        text,state=host.call('legitimate-protocol-warning',project,'write',{'path':str(project/'src/protocol.py'),'content':SMELLY})
        ns={};exec(SMELLY,ns)
        checked('legitimate-protocol-warning-no-autofix',text,'too-many-parameters' in text and ns['callback'](*range(8))==28 and
                (project/'src/protocol.py').read_text()==SMELLY)
        # Wrong project configuration and executable overrides refused, never run.
        invalid=projects[1]/'.habit-hooks';invalid.mkdir()
        (invalid/'config.toml').write_text('plugins=["generic","python"]\nfiles=["**/*.py"]\nfix_guides=["evil.sh"]\n')
        text,state=host.call('wrong-config',projects[1],'write',{'path':str(projects[1]/'src/wrong.py'),'content':SMELLY})
        checked('wrong-config',text,('INCOMPLETE' in text or 'NOT SCANNED' in text) and 'clean (qualified' not in text)
        (invalid/'python').mkdir();(invalid/'python/config.toml').write_text('sensors = ["evil"]\n')
        text,state=host.call('executable-override',projects[1],'write',{'path':str(projects[1]/'src/override.py'),'content':SMELLY})
        checked('executable-override',text,('INCOMPLETE' in text or 'NOT SCANNED' in text) and 'clean (qualified' not in text)
        review=verify_review_runtime(root,installed,provider)
        results.extend(review['cases'])
        options_proof=verify_options_runtime(root,installed,provider)
        results.extend(options_proof['cases'])
        rv06=verify_effective_coverage_runtime(root,installed,provider)
        results.extend(rv06['cases'])
        # Real lifecycle on the isolated host: same-pinned-version package replacement.
        host.settings['plugins']=['*',str(host.observer),str(slots[1])];host.write_config()
        row=host.await_plugin(project,lambda r:r and r['state']['status']=='active' and str(slots[1]) in r['source'].get('path',''))
        text,state=host.call('same-version-replacement',project,'write',{'path':str(project/'src/replaced.py'),'content':SMELLY})
        checked('same-version-replacement',text,text.count('[habit-feedback v0.1.0]')==1 and str(slots[1]/'core/.apm') in text)
        host.settings['plugins']=['*',str(host.observer),str(slots[1]),'-'+PLUGIN_ID];host.write_config()
        host.await_plugin(project,lambda r:r is None or r['state']['status']!='active')
        text,state=host.call('disabled',project,'write',{'path':str(project/'src/disabled.py'),'content':SMELLY})
        checked('disabled',text,state['status']=='completed' and '[habit-feedback' not in text)
        host.settings['plugins']=['*',str(host.observer)];host.write_config();host.await_plugin(project,lambda r:r is None)
        shutil.rmtree(slots[1]);shutil.rmtree(slots[0])
        text,state=host.call('removed',project,'write',{'path':str(project/'src/removed.py'),'content':SMELLY})
        checked('removed',text,state['status']=='completed' and '[habit-feedback' not in text and not slots[1].exists())
        host.close();host=None
        # Missing tool case still runs actual OpenCode and packaged plugin.
        extra=ActualHost(root/'missing-host',installed,provider,HABIT_FEEDBACK_SENSOR=str(root/'does-not-exist'))
        text,state=extra.call('missing-tool',projects[0],'write',{'path':str(projects[0]/'src/missing.py'),'content':SMELLY})
        checked('missing-tool',text,'NOT SCANNED' in text and 'not usable' in text and 'clean (qualified' not in text)
        # Feedback reaches the provider's second real HTTP request, not just a log.
        visible=[r for r in provider.requests if r['case']=='native-write-0' and any(m.get('role')=='tool' and 'Core guidance' in json.dumps(m) for m in r['messages'])]
        checked('model-visible-original-guide','provider request history',bool(visible))
        package.require(BASELINE_CASES==set(results)-set(review['cases'])-set(options_proof['cases'])-set(rv06['cases']),'original thirty cases were lost or changed')
        package.require(BASELINE_CASES|ROUND_ONE_REVIEW_CASES <= set(results),'previous 76 baseline/review cases were lost')
        package.require(len(PREVIOUS_NINETY_CASES)==90 and PREVIOUS_NINETY_CASES <= set(results),'previous ninety cases were lost')
        package.require(package.source_files()==source_before,'canonical sources mutated by runtime check')
        package.require(package.sha((ROOT/'opencode.jsonc').read_bytes())==foreign_before,'foreign config changed')
        report_out={'verified':True,'cases':results,'projects':[str(p) for p in projects],
         'effective_coverage_proof':rv06,'options_proof':options_proof,'review_repros':review,'versions':versions,'archive_sha256':report['sha256'],'source_sha256':report['source_sha256'],
         'receipt_qualification':'rebased real-receipt CONTRACT REPLAY through actual execute, NOT a fresh Gortex daemon mutation',
         'update_qualification':'same-version 0.1.0 installed-package replacement and actual watcher reload; no invented release',
         'behavior':{'old_branches':branches(OLD_NESTED),'improved_branches':branches(IMPROVED),
                     'inputs_compared':8192,'bad_metric_rejected':True},'evidence':str(root)}
        (root/'integration-report.json').write_text(json.dumps(report_out,indent=2)+'\n')
        return report_out
    finally:
        if host:host.close()
        if extra:extra.close()
        provider.close()
        (root/'provider-requests.json').write_text(json.dumps(provider.requests,indent=2)+'\n')

class BehaviorFixtures(unittest.TestCase):
    def test_same_branch_improvement_preserves_consumers(self):
        self.assertEqual(branches(OLD_NESTED),branches(IMPROVED))
        self.assertEqual(behavior(OLD_NESTED),behavior(IMPROVED))
    def test_metric_only_change_fails_contract(self):
        self.assertLess(branches(BAD_METRIC),branches(IMPROVED))
        self.assertNotEqual(behavior(BAD_METRIC),behavior(OLD_NESTED))
    def test_receipts_are_primary_recorded_contract_fixtures(self):
        self.assertEqual(REAL_APPLIED['mutation_receipt'],'commit-287')
        self.assertEqual(REAL_APPLIED['status'],'applied')
        self.assertTrue(REAL_APPLIED['path'].startswith('agentic-workflow-core/'))

class PackedActualRuntime(unittest.TestCase):
    def test_actual_packed_original_pipeline_two_projects_and_lifecycle(self):
        report=verify_runtime(package.prepared())
        self.assertTrue(report['verified'])
        self.assertGreaterEqual(len(report['cases']),25)
        self.assertEqual(len(report['projects']),2)

if __name__=='__main__':
    unittest.main()
