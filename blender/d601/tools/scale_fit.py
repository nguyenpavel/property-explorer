"""Least-squares scale from dimension strings (mm) against the drawn linework (pt)."""
dims = [(3300, 499.72, 686.81), (4090, 91.39, 323.26), (7245, 115.34, 526.08), (3750, 335.73, 548.33),
        (5130, 115.34, 406.18), (3215, 554.85, 737.12), (1840, 204.35, 308.67), (2815, 91.39, 250.98),
        (4445, 241.20, 493.20), (1230, 253.53, 323.26), (950, 315.19, 369.04), (1935, 137.31, 247.01),
        (1850, 384.07, 488.95), (2645, 97.06, 247.01), (2030, 119.60, 234.68), (1060, 257.50, 317.59),
        (2000, 373.15, 486.54), (1600, 579.66, 670.37), (220, 78.91, 91.39), (2590, 115.34, 262.18),
        (900, 262.18, 313.20), (3755, 313.20, 526.08), (2130, 406.18, 526.93), (250, 526.93, 541.11)]
num = sum(mm * (b - a) for mm, a, b in dims); den = sum((b - a) ** 2 for mm, a, b in dims)
s = num / den
res = [mm - s * (b - a) for mm, a, b in dims]
print(f'{len(dims)} dimensions: {s:.4f} mm/pt (1:50 is {25.4/72*50:.4f}); worst residual {max(map(abs, res)):.1f} mm, rms {(sum(r*r for r in res)/len(res))**.5:.1f} mm')
# finish allowance that keeps every dry room on its table value
import math
K = 25.4 / 72 * 50 / 1000
dry = {'01': (10.70, None), '02': (7.26, 3.75), '03': (5.13, 3.215), '04': (3.30, 4.09)}
ok = []
for t in [x / 1000 for x in range(0, 31)]:
    a02 = (0.41159 * 17.639 - 2 * t) * (3.75 - 2 * t)
    a03 = (5.13 - 2 * t) * (3.215 - 2 * t)
    a04 = (3.30 - 2 * t) * (4.09 - 2 * t)
    a01 = 10.6995 - 18.37 * t + 4 * t * t
    if all(abs(a - b) < 0.05 for a, b in ((a01, 10.4), (a02, 26.9), (a03, 16.3), (a04, 13.3))): ok.append(t * 1000)
print('plaster allowances (mm) that put all dry rooms on the table:', ok)
