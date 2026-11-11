"""mix.py — score + foley + ambience + voice for 《从一句话开始》 → out/mix.wav
The score is synthesized (no samples): marimba, vibraphone, celesta, pad, sine pulse, shaker, all in D dorian at 96 BPM.
The mess sounds are scattered (detuned by tens of cents, random pans, one timbre per source);
Claude's sounds are one family (felt + glass, in D dorian, centred).
Run from the library root: .venv/bin/python <project>/mix.py
"""
import os, sys, json, numpy as np, soundfile as sf
from scipy.signal import resample_poly
from scipy.ndimage import uniform_filter1d
D = os.path.dirname(os.path.abspath(__file__))
LIB = os.environ.get('LIB') or os.getcwd()
sys.path.insert(0, LIB)
from core.audio.sfx import SR, t_, env_exp, bp, lp, hp, noise, norm, brown, add, compress, limit

EVJ = json.load(open(os.path.join(D, 'events.json')))
DUR = EVJ['dur']; EV = EVJ['ev']
TL = next(e for e in EV if e['type'] == 'timeline'); K = TL['K']; VO = TL['VO']; BEAT = TL['BEAT']
S8, S16 = BEAT / 2, BEAT / 4
rng = np.random.default_rng(1111)
N = int(DUR * SR)
fol = np.zeros((N, 2)); amb = np.zeros((N, 2)); vox = np.zeros((N, 2)); mus = np.zeros((N, 2))
hz = lambda m: 440 * 2 ** ((m - 69) / 12)
DOR = [62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81, 83, 84, 86, 88, 89, 91, 93]

def sine(f, d, tau, ph=0): return np.sin(2 * np.pi * f * t_(d) + ph) * env_exp(d, tau)

# ─────────── instruments ───────────
def marimba(m, v=1.0, d=0.9):
    f = hz(m); x = sine(f, d, .28) + sine(f * 3.93, d, .05) * .35 + sine(f * 9.1, d, .015) * .12
    x += bp(noise(d), 1800, 6000) * env_exp(d, .002) * .15
    return norm(x) * v

def vib(m, v=1.0, d=2.6, trem=5.4):
    f = hz(m); tt = t_(d)
    x = (sine(f, d, 1.1) + sine(f * 4.0, d, .25) * .12) * (1 + .22 * np.sin(2 * np.pi * trem * tt))
    return norm(x * np.minimum(1, tt / .004)) * v

def celesta(m, v=1.0, d=1.4):
    f = hz(m); x = sine(f, d, .45) + sine(f * 2.0, d, .2) * .3 + sine(f * 3.01, d, .08) * .15
    return norm(x) * v

def pad(ms, d, v=1.0, att=.8, rel=1.2, bright=1.0):
    tt = t_(d); x = np.zeros_like(tt)
    for m in ms:
        f = hz(m)
        for det in (-0.07, 0.0, 0.08):
            ff = f * 2 ** (det / 12)
            for h, a in [(1, 1), (2, .35 * bright), (3, .15 * bright), (4, .06 * bright)]:
                x += np.sin(2 * np.pi * ff * h * tt + rng.uniform(0, 6.28)) * a
    e = np.minimum(1, tt / att) * np.minimum(1, np.maximum(0, (d - tt) / rel))
    return norm(lp(x, 2400) * e) * v

def pulse(m, v=1.0, d=.28):
    f = hz(m); x = sine(f, d, .09) + sine(2 * f, d, .06) * .5 + sine(3 * f, d, .04) * .3
    return norm(x * np.minimum(1, t_(d) / .003)) * v

def shaker(v=1.0):
    d = .06; return norm(hp(noise(d), 6000) * env_exp(d, .012)) * v

# ─────────── foley ───────────
def caret_tick(v=1.0):
    d = .03; return norm(bp(noise(d), 1500, 3200) * env_exp(d, .0025) + sine(2100, d, .004) * .6) * v

def key(v=1.0, heavy=False):
    d = .07; p = 1 + rng.uniform(-.08, .08)
    x = bp(noise(d), 1400 * p, 5200 * p) * env_exp(d, .004) + sine(180 * p, d, .012) * (.9 if heavy else .45) + sine(820 * p, d, .006) * .25
    if heavy: x = x + lp(noise(d), 500) * env_exp(d, .02) * .6
    return norm(x) * v

def glass(f, v=1.0, d=.5, bright=1.0):
    x = sine(f, d, d * .35) + sine(2 * f, d, d * .18) * .35 * bright + sine(2.76 * f, d, d * .1) * .22 * bright + hp(noise(d), 5000) * env_exp(d, .002) * .3
    return norm(x) * v

def felt(v=1.0, f=320):
    d = .09; x = sine(f, d, .018) + lp(noise(d), 1400) * env_exp(d, .006) * .7 + sine(f * 2.01, d, .01) * .3
    return norm(x) * v

def whoosh(d=.3, lo=500, hi=4000, v=1.0):
    n = noise(d); out = np.zeros_like(n); L = len(n); step = 480
    for i in range(0, L, step):
        u = i / L; f = lo * (hi / lo) ** u
        w = min(step, L - i); seg = bp(n[max(0, i - 1500):i + w], f * .75, min(f * 1.3, SR / 2 - 100))[-w:]; out[i:i + w] = seg
    return norm(out * np.sin(np.pi * t_(d) / d) ** 1.5) * v

def plop(v=1.0):
    d = .08; tt = t_(d); f = 320 * (1 - .5 * tt / d)
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(d, .02) + bp(noise(d), 2000, 6000) * env_exp(d, .003) * .4) * v

def flick(v=1.0):
    d = .09; return norm(bp(noise(d), 2200, 7500) * np.sin(np.pi * t_(d) / d) ** .6 * env_exp(d, .05)) * v

def pop(v=1.0, f=900):
    d = .12; tt = t_(d); fr = f * (1 + .6 * np.exp(-tt / .01))
    return norm(np.sin(2 * np.pi * np.cumsum(fr) / SR) * env_exp(d, .03)) * v

def blip_down(v=1.0, f=1400):
    d = .09; tt = t_(d); fr = f * np.exp(-tt / .04)
    return norm(np.sin(2 * np.pi * np.cumsum(fr) / SR) * env_exp(d, .03)) * v

def doom(v=1.0):
    d = 2.6; tt = t_(d); f = 40 + 15 * np.exp(-tt / .35)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(d, .55)
    mallet = lp(noise(d), 700) * env_exp(d, .012) * .9 + sine(147, d, .05) * .5 + sine(98, d, .12) * .5
    return norm(sub + mallet + lp(noise(d), 900) * env_exp(d, .5) * .05) * v

def shimmer(d=1.6, v=1.0):
    x = whoosh(d, 3000, 9500, 1) * .7
    for m in (86, 93, 98):
        x += np.sin(2 * np.pi * hz(m) * t_(d)) * np.sin(np.pi * t_(d) / d) ** 2 * .2 * (1 + .3 * np.sin(2 * np.pi * 5 * t_(d)))
    return norm(x) * v

def grains(d=1.0, v=1.0):
    out = np.zeros(int(d * SR)); t = 0.0
    while t < d - .01:
        c = bp(noise(.006), 2500, 9000) * env_exp(.006, .001) * rng.uniform(.4, 1)
        s = int(t * SR); out[s:s + len(c)] += c[:len(out) - s]; t += .03 + rng.uniform(0, .01)
    return norm(out) * v

def crt_off(v=1.0):
    d = .5; tt = t_(d); f = 900 * np.exp(-tt / .12) + 120
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(d, .15) * .5 + whoosh(d, 3000, 300, 1) * .6) * v

def scribble(d, v=1.0):
    x = bp(noise(d), 2500, 7000) * (0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 3.2 * t_(d)))) * .3
    return norm(x * np.minimum(1, t_(d) / .05) * np.minimum(1, (d - t_(d)) / .1)) * v

# ─────────── score ───────────
P = [74, 69, 77, 72, 76, 69, 79, 71]                  # D5 A4 F5 C5 E5 A4 G5 B4
ORDER = [0, 4, 2, 6, 1, 5, 3, 7]                       # additive process: two steps more each bar
BAR = BEAT * 4
p0 = K['press'] + BEAT
def pattern(t0, t1, gain=1.0, additive=False, subtract_from=None):
    b = 0
    while True:
        bs = t0 + b * BAR
        if bs >= t1: break
        n = min(8, 2 * (b + 1)) if additive else 8
        for s in range(8):
            ts = bs + s * S8
            if ts >= t1: break
            if ORDER.index(s) >= n: continue
            if subtract_from is not None and ts >= subtract_from:
                k = int((ts - subtract_from) / S8) + 1
                if ORDER.index(s) >= 8 - 2 * k: continue
            v = gain * (0.85 if s % 2 == 0 else 0.6) * (1.1 if s == 0 else 1)
            add(mus, marimba(P[s], 1, .9), ts, .13 * v, (-.25, .25)[s % 2])
        b += 1

pattern(p0, K['away'] + S8 * 2, 1.0, additive=True, subtract_from=K['away'])
# pad under prompt, then Dm9 bed
add(mus, pad([62, 69], K['press'] - K['tick0'] + .3, 1, 1.2, .4, .6), K['tick0'], .05)
add(mus, pad([62, 65, 69, 72, 76], K['quiet'] - K['whip1'], 1, 1.5, .5, .8), K['whip1'], .05)
# chord at "full" and on the result
for m, a in [(62, .5), (65, .45), (69, .5), (72, .4), (76, .45)]: add(mus, vib(m, 1, 3.0), K['full'], .09 * a)
add(mus, celesta(88, 1, 1.6), K['full'], .05)
# pulse + shaker + vib melody in the skills / agent sections
t = K['emit']
while t < K['away']:
    add(mus, pulse(50 if int(round((t - K['emit']) / S8)) % 8 != 6 else 57, 1), t, .09)
    t += S8
t = K['split']
while t < K['away']:
    if int(round((t - K['split']) / S16)) % 2 == 1: add(fol, shaker(), t, .03, .3)
    t += S16
MEL = [(K['split'], 81, 4), (K['split'] + BAR, 79, 4), (K['split'] + 2 * BAR, 77, 2), (K['split'] + 2 * BAR + 2 * BEAT, 76, 2), (K['split'] + 3 * BAR, 74, 4)]
for t0, m, beats in MEL:
    if t0 < K['away']: add(mus, vib(m, 1, beats * BEAT + 1.2), t0, .07, .1)
for i, ct in enumerate(K['cards']): add(mus, celesta([86, 88, 89, 93][i], 1), ct, .06, (-.3, -.1, .1, .3)[i])
for i, nt in enumerate(K['nodes']): add(mus, celesta([81, 84, 86, 88, 93][i], 1, 1.2), nt, .07)
# number: pad + low pulse, a soft chord on the last lock
add(mus, pad([69, 74], K['reveal'] - K['num'] + 1.0, 1, 1.0, 1.0, .5), K['num'], .045)
t = K['num']
while t < K['collapse']:
    add(mus, pulse(50, 1, .35), t, .06); t += BEAT
for m in (62, 69, 76): add(mus, vib(m, 1, 3.0), K['num'] + S16 * 4, .06)
# the film's own score returns softly inside the preview
pattern(K['reveal'], K['collapse'], 0.45)
# final cadence on the wordmark: Dm9 + celesta echo
for m, a in [(62, .5), (65, .45), (69, .5), (72, .4), (76, .5), (81, .35)]: add(mus, vib(m, 1, 6.5, 4.2), K['word'], .1 * a)
add(mus, pad([62, 65, 69, 72, 76], K['off'] - K['word'] + 0.6, 1, 0.6, 2.2, .7), K['word'], .06)
for k, m in enumerate([93, 88, 86, 81]): add(mus, celesta(m, 1, 1.8), K['word'] + .02 + k * S8, .045 * (1 - k * .18))

# ─────────── ambience ───────────
tt = np.arange(N) / SR
def ramp(a, b, fi=.3, fo=.3):
    e = np.zeros(N); s, e2 = int(a * SR), min(N, int(b * SR)); e[s:e2] = 1
    k = int(fi * SR); e[s:s + k] *= np.linspace(0, 1, k)[:e2 - s]
    k = min(int(fo * SR), e2 - s); e[e2 - k:e2] *= np.linspace(1, 0, k)
    return e
room = lp(brown(DUR), 220) * .010
fan = bp(noise(DUR), 280, 1600) * .03 * np.clip(tt / K['freeze'], 0, 1) ** 1.5
coil = np.sin(2 * np.pi * (6800 + 30 * np.sin(2 * np.pi * .7 * tt)) * tt) * .004 * np.clip((tt - 2.5) / 3.75, 0, 1) ** 2
mono = room * (ramp(0, K['freeze'], .2, .005) + ramp(K['tick0'] - .3, K['off'] + .3, .3, .4)) + (fan + coil) * (tt < K['freeze'])
amb[:, 0] += mono; amb[:, 1] += np.roll(mono, 37)

# ─────────── events ───────────
spawn_gain = lambda t: .025 + .035 * min(1, t / K['freeze'])
for e in EV:
    t, ty = e['t'], e['type']
    if ty == 'spawn':
        pan = e['pan'] * .9; g = spawn_gain(t); kd = e['kind']
        if kd == 'file': add(fol, plop(), t, g * 1.2, pan)
        elif kd == 'photo': add(fol, flick(), t, g * 1.3, pan)
        elif kd == 'notif':
            f = hz(rng.choice(DOR[3:12])) * 2 ** (rng.uniform(-.45, .45) / 12)
            add(fol, pop(1, f), t, g, pan)
        else: add(fol, whoosh(.16, 900, 5000, 1), t - .05, g * 1.1, pan)
    elif ty == 'badgeoff': add(fol, blip_down(1, 1500 + rng.uniform(-80, 80)), t, .012, e['pan'] * .5)
    elif ty == 'absorb':
        m = DOR[(e['cat'] * 2 + e['i'] % 5) % 8 + 9]
        add(fol, glass(hz(m), 1, .22, .6), t, .02, 0)
    elif ty == 'tick': add(fol, caret_tick(), t, .07 if e.get('soft') else .13)
    elif ty == 'key': add(fol, key(), t, .09 if e.get('soft') else .13, -.05)
    elif ty == 'windup': add(fol, whoosh(.35, 300, 1500, 1), t, .04)
    elif ty == 'press': add(fol, doom(), t, .7); add(fol, key(heavy=True), t, .3)
    elif ty == 'whip': add(fol, whoosh(.6, 6000, 250, 1), t, .14)
    elif ty == 'morph': add(fol, felt(1, 280), t + .5, .12)
    elif ty == 'chord': add(fol, felt(1, 294), t, .12)
    elif ty == 'emit': add(fol, whoosh(.4, 300, 4000, 1), t - .1, .1)
    elif ty == 'row': add(fol, felt(1, 300 + 30 * e['i']), t, .11)
    elif ty == 'check': add(fol, glass(hz([86, 88, 91, 93][e['i'] % 4]), 1, .35), t, .05)
    elif ty == 'split': add(fol, whoosh(.45, 500, 5000, 1), t - .1, .1)
    elif ty == 'card': add(fol, felt(1, 330), t, .1)
    elif ty == 'scribble': add(fol, scribble(e['dur']), t, .035, -.4)
    elif ty == 'typing':
        for k in range(int(e['dur'] / .09)): add(fol, key(), t + k * .09 + rng.uniform(0, .02), .035, -.1)
    elif ty == 'flow': add(fol, whoosh(.4, 4000, 600, 1), t - .05, .09)
    elif ty == 'node': add(fol, felt(1, 300 + 20 * e['i']), t, .12)
    elif ty == 'retract': add(fol, felt(1, 340 - 10 * e.get('i', 0)), t, .08)
    elif ty == 'scramble': add(fol, grains(.7), t, .06)
    elif ty == 'lock': add(fol, felt(1, 360 + 30 * e['i']), t, .14)
    elif ty == 'label': add(fol, whoosh(.3, 800, 4000, 1), t - .05, .05)
    elif ty == 'reveal': add(fol, whoosh(.55, 5000, 350, 1), t, .13)
    elif ty == 'collapse': add(fol, whoosh(.35, 600, 3000, 1), t, .07)
    elif ty == 'crt': add(fol, crt_off(), t, .16)
    elif ty == 'sweep': add(fol, shimmer(1.9), t, .1)
    elif ty == 'drop': add(fol, felt(1, 400 - 25 * e['i']), t, .06)
    elif ty == 'squash': add(fol, crt_off(), t, .1)
    elif ty == 'crtoff': add(fol, caret_tick(), t, .05); add(fol, blip_down(1, 900), t, .03)

# ─────────── voice ───────────
lines = json.load(open(os.path.join(D, 'lines.json')))
vo_int = []
for L in lines:
    t0 = VO[L['id']]
    y, sr = sf.read(os.path.join(D, 'voices', L['id'] + '.wav'))
    if y.ndim > 1: y = y.mean(1)
    if sr != SR: y = resample_poly(y, SR, sr)
    y = compress(y / (np.abs(y).max() + 1e-9) * .9, .3, 3.0)
    add(vox, y, t0, .5)
    vo_int.append((t0, t0 + len(y) / SR))

# ─────────── ducking, silences, master ───────────
duck = np.ones(N); duckF = np.ones(N)
for a, b in vo_int:
    s, e = int((a - .08) * SR), int((b + .12) * SR); duck[s:e] = 10 ** (-8 / 20); duckF[s:e] = 10 ** (-4 / 20)
duck = uniform_filter1d(duck, int(.12 * SR)); duckF = uniform_filter1d(duckF, int(.12 * SR))
MUSIC_G = 0.72
mix = mus * MUSIC_G * duck[:, None] + fol * duckF[:, None] + amb + vox
z0, z1 = int(K['freeze'] * SR), int(K['tick0'] * SR)
mix[z0:z1] = 0                                             # the screen pauses: digital zero
q0, q1 = int(K['quiet'] * SR), int(K['num'] * SR)
mix[q0:q1] *= 0.02; mix[q0:q1, 0] += room[q0:q1] * .1; mix[q0:q1, 1] += room[q0:q1] * .1   # near-silence
f = int(.5 * SR); mix[-f:] *= np.linspace(1, 0, f)[:, None]
for c in range(2): mix[:, c] = limit(mix[:, c], .95)
mix[z0:z1] = 0
os.makedirs(os.path.join(D, 'out'), exist_ok=True)
sf.write(os.path.join(D, 'out', 'mix.wav'), mix.astype(np.float32), SR)
if '--stems' in sys.argv:
    for nm, x in [('music', mus * MUSIC_G * duck[:, None]), ('foley', fol * duckF[:, None]), ('amb', amb), ('vox', vox)]:
        sf.write(os.path.join(D, 'out', f'stem_{nm}.wav'), x.astype(np.float32), SR)
print('mix.wav', mix.shape, 'peak %.3f' % np.abs(mix).max(), 'vo', [(round(a, 2), round(b, 2)) for a, b in vo_int])
