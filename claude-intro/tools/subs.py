"""Subtitle cues from the voice timeline (events.json) and the measured line lengths → out/cues.json.
Same timing rule as the burned-in toasts in film.js: hold max(1.8 s, speech + 0.6 s), never into the next line."""
import os, json
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ev = json.load(open(os.path.join(D, 'events.json')))
tl = next(e for e in ev['ev'] if e['type'] == 'timeline'); VO = tl['VO']
lines = {l['id']: l for l in json.load(open(os.path.join(D, 'lines.json')))}
durs = json.load(open(os.path.join(D, 'voices', 'dur.json')))
ids = list(VO.keys()); cues = []
for k, i in enumerate(ids):
    t0 = VO[i]; nxt = VO[ids[k + 1]] - 0.15 if k + 1 < len(ids) else ev['dur']
    cues.append({'t0': t0, 't1': min(nxt, t0 + max(1.8, durs[i] + 0.6)), 'text': lines[i]['text']})
os.makedirs(os.path.join(D, 'out'), exist_ok=True)
json.dump(cues, open(os.path.join(D, 'out', 'cues.json'), 'w'), ensure_ascii=False, indent=1)
print(len(cues), 'cues')
