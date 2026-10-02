"""One line per model: accuracy, confidently-wrong count (≥ 90% probability) and median latency."""
import json, statistics as st
M = [('Jev', 'jev-latest'), ('Nimble 9B', 'nimble'), ('tev1 4B', 'tev1-4b'), ('Strands 2B', 'strands')]
print(f"{'model':<12}{'answered':>9}{'accuracy':>10}{'sure & wrong':>14}{'median ms':>11}")
for n, k in M:
    R = [json.loads(l) for l in open(f'results/{k}.jsonl')]
    acc = 100 * sum(r['correct'] for r in R) / len(R)
    cw = sum(1 for r in R if not r['correct'] and (r['p_answer'] or 0) >= .9)
    print(f"{n:<12}{len(R):>9}{acc:>9.1f}%{cw:>14}{st.median(r['ms'] for r in R):>11.0f}")
