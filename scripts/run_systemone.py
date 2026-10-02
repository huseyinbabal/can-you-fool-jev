"""Send every row of data/questions.csv to one model's /v1/systemone endpoint (Jev-compatible API).
Usage: python3 scripts/run_systemone.py <model>  →  results/<model>.jsonl (resumable) + results/requests-<model>.jsonl
  choice → type 'choice', criteria {option: ''}
  yes_no → type 'noul', criteria {'true': …, 'false': …} taken from the 'yes = … ; no = …' part of the question
  score  → type 'score', criteria ['1'..'10']; the answer is the API's probability-weighted score, rounded
Env: SYSTEMONE_HOST (default Ollama, http://localhost:11434), SYSTEMONE_KEY (Bearer token, for Jev),
     DATASET, PREFIX (output prefix, default results/), VERBOSE=1 (one line per row), SYSTEMONE_PAUSE (s between calls)"""
import csv, json, os, re, sys, time, urllib.request
MODEL = sys.argv[1]
HOST = os.environ.get('SYSTEMONE_HOST', 'http://localhost:11434')
KEY = os.environ.get('SYSTEMONE_KEY')
PAUSE = float(os.environ.get('SYSTEMONE_PAUSE', '0'))
DATASET = os.environ.get('DATASET', 'data/questions.csv')
PREFIX = os.environ.get('PREFIX', 'results/')
OUT = f"{PREFIX}{MODEL.replace(':', '-').replace('/', '_')}.jsonl"
done = {json.loads(l)['id'] for l in open(OUT)} if os.path.exists(OUT) else set()
def call(body):
    h = {'Content-Type': 'application/json', **({'Authorization': f'Bearer {KEY}'} if KEY else {})}
    req = urllib.request.Request(HOST + '/v1/systemone', data=json.dumps(body).encode(), headers=h)
    return json.load(urllib.request.urlopen(req, timeout=300))
def split_yesno(q):
    m = re.search(r'^(.*?)\s*yes\s*=\s*(.*?);\s*no\s*=\s*(.*)$', q, re.S | re.I)
    return (m.group(1).strip(), {'true': m.group(2).strip(), 'false': m.group(3).strip().rstrip('.')}) if m else (q, {})
rows = list(csv.DictReader(open(DATASET)))
REQLOG = open(f"{PREFIX}requests-{MODEL.replace(':', '-').replace('/', '_')}.jsonl", 'a')   # exact request bodies sent
with open(OUT, 'a') as fh:
    for r in rows:
        if int(r['id']) in done: continue
        if r['type'] == 'yes_no':
            instr, crit = split_yesno(r['question']); q = {'type': 'noul', 'instructions': instr, 'criteria': crit}
        elif r['type'] == 'score':
            lo_, hi_ = map(int, r['options'].split('-')); q = {'type': 'score', 'instructions': r['question'], 'criteria': [str(i) for i in range(lo_, hi_ + 1)]}
        else:
            q = {'type': 'choice', 'instructions': r['question'], 'criteria': {o: '' for o in r['options'].split('|')}}
        rec = {'id': int(r['id']), 'type': r['type'], 'trap': r['trap'], 'expected': r['expected'], 'accept': r['accept'], 'error': None}
        try:
            import time; t0 = time.time()
            body = {'model': MODEL, 'state': r['input'], 'questions': {'q': q}}
            REQLOG.write(json.dumps({'id': int(r['id']), 'body': body}, ensure_ascii=False) + '\n'); REQLOG.flush()
            a = call(body)['answers']['q']; rec['ms'] = round((time.time() - t0) * 1000)
            if r['type'] == 'yes_no':
                p = a['noul']; ans = 'yes' if p >= 0.5 else 'no'; probs = {'yes': p, 'no': 1 - p}
            elif r['type'] == 'score':
                lg = a.get('legend') or {str(i): str(i) for i in range(len(a['probabilities']))}
                probs = {lg[k]: v for k, v in a['probabilities'].items()}; ans = lg[str(int(round(a['score'])))]; rec['score_raw'] = a['score']; rec['argmax'] = max(probs, key=probs.get)
            else:
                probs = a['probabilities']; ans = a['choice']
            rec.update(answer=ans, probs=probs, p_answer=probs.get(ans), p_expected=probs.get(r['expected']), api_confidence=a.get('confidence'))
            if r['type'] == 'score':
                lo, hi = map(int, r['accept'].split('-')); rec['correct'] = lo <= int(ans) <= hi
            else:
                rec['correct'] = ans == r['expected']
        except Exception as e:
            rec.update(answer=None, correct=False, probs={}, p_answer=None, p_expected=None, error=str(e)[:300], ms=None)
        fh.write(json.dumps(rec, ensure_ascii=False) + '\n'); fh.flush()
        if os.environ.get('VERBOSE'):
            print(f"#{rec['id']:<5} {r['type']:<7} expected {r['expected']:<8} got {str(rec['answer']):<8} {'✓' if rec['correct'] else '✗'}  {rec['ms']} ms", flush=True)
        if PAUSE: time.sleep(PAUSE)
        if rec['id'] % 100 == 0: print(MODEL, rec['id'], flush=True)
print('done', MODEL)
