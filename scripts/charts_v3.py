"""Charts for the 1000-question run → charts/v3-*.png (only ids answered by every model)."""
import json, csv, sys, importlib, collections, statistics as st
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import os
FONT = os.environ.get('CHART_FONT', 'CaveatBrush-Regular.ttf')   # optional: Caveat Brush (Google Fonts, OFL)
if os.path.exists(FONT): fm.fontManager.addfont(FONT); FN = fm.FontProperties(fname=FONT).get_name()
else: FN = 'DejaVu Sans'
BG, W, Y, P, B, G, D = '#0b0b0c', '#f3f0e6', '#ffe27a', '#ff8fab', '#86d3ff', '#9be89b', '#8b8f98'
plt.rcParams.update({'font.family': FN, 'font.size': 22, 'text.color': W, 'axes.labelcolor': W, 'xtick.color': W, 'ytick.color': W,
                     'axes.edgecolor': D, 'figure.facecolor': BG, 'axes.facecolor': BG, 'savefig.facecolor': BG})
M = [('jev', 'Jev', W, 'results/jev-latest.jsonl'), ('nimble', 'Nimble 9B', Y, 'results/nimble.jsonl'),
     ('tev1', 'tev1 4B', B, 'results/tev1-4b.jsonl'), ('strands', 'Strands Decider 2B', P, 'results/strands.jsonl')]
rows = {int(r['id']): r for r in csv.DictReader(open('data/questions.csv'))}
RES = {k: {r['id']: r for r in map(json.loads, open(f))} for k, _, _, f in M}
ids = sorted(set(rows).intersection(*[RES[k].keys() for k in RES]))
N = len(ids)
cat = lambda i: rows[i]['category']
def acc(k, f=lambda i: True):
    xs = [i for i in ids if f(i)]
    return 100 * sum(RES[k][i]['correct'] for i in xs) / len(xs) if xs else np.nan
def fig(title, sub):
    f, ax = plt.subplots(figsize=(16, 9), dpi=100)
    f.text(0.5, 0.94, title, ha='center', fontsize=44, color=Y); f.text(0.5, 0.885, sub, ha='center', fontsize=23, color=D)
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
    return f, ax
def bars(ax, vals, fmt):
    x = np.arange(len(M))
    bs = ax.bar(x, vals, 0.6, color='none', edgecolor=[c for _, _, c, _ in M], linewidth=4, hatch='//')
    for b, v, (_, _, c, _) in zip(bs, vals, M): ax.text(b.get_x() + b.get_width() / 2, v + max(vals) * 0.02, fmt(v), ha='center', fontsize=30, color=c)
    ax.set_xticks(x); ax.set_xticklabels([n for _, n, _, _ in M], fontsize=26)
def grouped(ax, groups, labels):
    x = np.arange(len(groups)); w = 0.8 / len(M)
    for j, (k, n, c, _) in enumerate(M):
        vals = [acc(k, f) for f in groups]
        bs = ax.bar(x + (j - 1.5) * w, vals, w, color='none', edgecolor=c, linewidth=3, hatch='//', label=n)
        for b, v in zip(bs, vals): ax.text(b.get_x() + b.get_width() / 2, v + 1, f'{v:.0f}', ha='center', fontsize=17, color=c)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=19); ax.set_ylim(0, 118); ax.set_ylabel('accuracy (%)')
    ax.legend(frameon=False, ncol=4, loc='upper center', bbox_to_anchor=(0.5, 1.04), fontsize=22)
sub = f'{N} English questions · identical /v1/systemone JSON request to every model'
# 1 overall
f, ax = fig('Overall accuracy', sub); bars(ax, [acc(k) for k, *_ in M], lambda v: f'{v:.1f}%')
ax.set_ylim(0, 110); ax.set_ylabel('accuracy (%)'); plt.subplots_adjust(top=0.82, bottom=0.1); f.savefig('charts/v3-1-overall.png'); plt.close(f)
# 2 types
T = [('choice', 'choice'), ('yes_no', 'yes / no'), ('score', 'score 1–10')]
f, ax = fig('By answer type', 'a score counts as correct when it lands in the accepted range')
grouped(ax, [lambda i, t=t: rows[i]['type'] == t for t, _ in T], [f'{l}\n({sum(rows[i]["type"] == t for i in ids)})' for t, l in T])
plt.subplots_adjust(top=0.8, bottom=0.14); f.savefig('charts/v3-2-types.png'); plt.close(f)
# 3 categories
C = ['customer messages', 'agent tool calls', 'code & commits', 'grounding & RAG', 'safety & judging', 'product (voice, browser, SQL)', 'business (leads, fraud, hiring)']
f, ax = fig('By category', 'which model struggles where')
grouped(ax, [lambda i, c=c: cat(i) == c for c in C], [c.replace(' (', '\n(').replace(' & ', ' &\n').replace(', ', ',\n', 1) + f'\n[{sum(cat(i) == c for i in ids)}]' for c in C])
plt.subplots_adjust(top=0.8, bottom=0.2); f.savefig('charts/v3-3-categories.png'); plt.close(f)
# 4 trap heatmap
traps = collections.defaultdict(list)
for i in ids: traps[rows[i]['trap']].append(i)
ta = {t: [acc(k, lambda i, t=t: rows[i]['trap'] == t) for k, *_ in M] for t, v in traps.items() if len(v) >= 6 and t != 'control_easy'}
top = sorted(ta, key=lambda t: np.mean(ta[t]))[:12]
mat = np.array([ta[t] for t in top])
f, ax = plt.subplots(figsize=(16, 9), dpi=100); f.text(0.5, 0.94, 'Where each model gets fooled', ha='center', fontsize=44, color=Y)
f.text(0.5, 0.885, 'accuracy % on the 12 hardest trap types (questions per trap in brackets)', ha='center', fontsize=23, color=D)
ax.imshow(mat, cmap=LinearSegmentedColormap.from_list('c', ['#ff5c7a', '#3a2a12', '#9be89b']), vmin=0, vmax=100, aspect='auto')
for a in range(mat.shape[0]):
    for b in range(mat.shape[1]): ax.text(b, a, f'{mat[a, b]:.0f}%', ha='center', va='center', fontsize=21, color=W)
ax.set_xticks(range(len(M))); ax.set_xticklabels([n for _, n, _, _ in M], fontsize=24); ax.xaxis.tick_top()
ax.set_yticks(range(len(top))); ax.set_yticklabels([f"{t.replace('_', ' ')} ({len(traps[t])})" for t in top], fontsize=20)
for s in ax.spines.values(): s.set_visible(False)
plt.subplots_adjust(top=0.8, left=0.27, right=0.96, bottom=0.03); f.savefig('charts/v3-4-traps.png'); plt.close(f)
# 5 confidently wrong
cw = [sum(1 for i in ids if not RES[k][i]['correct'] and (RES[k][i]['p_answer'] or 0) >= .9) for k, *_ in M]
f, ax = fig('Confidently wrong', 'wrong answers the model gave with ≥ 90% probability')
bars(ax, cw, lambda v: f'{v}'); ax.set_ylim(0, max(cw) * 1.2); ax.set_ylabel('questions')
plt.subplots_adjust(top=0.82, bottom=0.1); f.savefig('charts/v3-5-confident-wrong.png'); plt.close(f)
# 6 calibration
f, ax = fig("Is the confidence honest?", "accuracy vs the model's own probability for its answer (buckets with ≥ 10 answers)")
bk = [(0, .5), (.5, .7), (.7, .9), (.9, .99), (.99, 1.01)]; lab = ['<50%', '50–70%', '70–90%', '90–99%', '≥99%']
for k, n, c, _ in M:
    ys = []
    for lo, hi in bk:
        xs = [i for i in ids if RES[k][i]['p_answer'] is not None and lo <= RES[k][i]['p_answer'] < hi]
        ys.append(100 * sum(RES[k][i]['correct'] for i in xs) / len(xs) if len(xs) >= 10 else np.nan)
    ax.plot(lab, ys, marker='o', markersize=12, linewidth=3.5, color=c, label=n)
ax.set_ylim(0, 105); ax.set_ylabel('accuracy (%)'); ax.set_xlabel('model confidence'); ax.legend(frameon=False, fontsize=21, loc='lower right')
plt.subplots_adjust(top=0.82, bottom=0.13); f.savefig('charts/v3-6-calibration.png'); plt.close(f)
# 7 latency
lat = [st.median(RES[k][i]['ms'] for i in ids) for k, *_ in M]
f, ax = fig('Speed per question', 'median ms · Jev = hosted API incl. network · others local on one Apple-silicon Mac')
bars(ax, lat, lambda v: f'{v:.0f} ms'); ax.set_ylim(0, max(lat) * 1.2); ax.set_ylabel('milliseconds')
plt.subplots_adjust(top=0.82, bottom=0.1); f.savefig('charts/v3-7-latency.png'); plt.close(f)
print('N', N); print({n: round(acc(k), 1) for k, n, *_ in M}); print('cw', cw, 'lat', lat)
for c in C: print(c, [round(acc(k, lambda i: cat(i) == c), 1) for k, *_ in M])
