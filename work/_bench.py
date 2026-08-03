"""Benchmark OCR window checking: sequential vs process pool.

Windows uses spawn, so every worker re-imports __main__. Without the
__main__ guard the workers re-run the benchmark and fork-bomb the pool.
"""
import sys
import time
sys.path.insert(0, 'pipeline')
from pathlib import Path
import clean_windows as cw

SRC = Path('dossier/mrbeast/sources/cWEUE8X7p-k.mp4')
N = 16


def main():
    cands = [300.0 + i * 37.0 for i in range(N)]
    c = cw.cache()

    def forget():
        for t in cands:
            c.pop('%s|%.2f|%.2f' % (SRC.name, t, 6.0), None)

    forget()
    t0 = time.time()
    for t in cands[:4]:
        cw.is_clean(SRC, t, 6.0, frames=2)
    seq = (time.time() - t0) / 4
    print('sequential : %.2fs per window' % seq, flush=True)

    forget()
    t0 = time.time()
    pool = cw.clean_pool(SRC, 6.0, count=int(N / 1.8), workers=8)
    elapsed = time.time() - t0
    par = elapsed / N
    print('pool(8)    : %.2fs per window  (%.1fs total, %d clean)'
          % (par, elapsed, len(pool)), flush=True)
    print('speedup    : %.1fx' % (seq / max(par, 0.001)), flush=True)
    cw.save_cache()


if __name__ == '__main__':
    main()
