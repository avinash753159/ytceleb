import sys
import time
sys.path.insert(0, 'pipeline')
from pathlib import Path
import clean_windows as cw

tests = [
    ('dossier/mrbeast/sources/7r3ORKgNUjw.mp4', 140.0, 4.0,
     'Coach P captions', 'REJECT'),
    ('dossier/mrbeast/sources/7r3ORKgNUjw.mp4', 552.0, 4.0,
     'INBF competition', 'REJECT'),
    ('dossier/mrbeast/sources/WwVs1qVaOb4.mp4', 236.0, 4.0,
     '30 SECONDS overlay', 'REJECT'),
    ('dossier/mrbeast/archive/AKJfakEsgy0.mp4', 30.0, 4.0,
     'archive bedroom', 'CLEAN'),
    ('dossier/mrbeast/sources/cLRLEnPaJLM.mp4', 5266.0, 4.0,
     'Rogan studio', 'CLEAN'),
    ('dossier/mrbeast/sources/9IQ_ldV9z_A.mp4', 731.0, 4.0,
     'Colin and Samir', 'CLEAN'),
    ('dossier/mrbeast/sources/7r3ORKgNUjw.mp4', 1150.0, 4.0,
     'Airrack late', '?'),
]

start = time.time()
for p, t0, d, note, exp in tests:
    ok, why = cw.is_clean(Path(p), t0, d, frames=2)
    got = 'CLEAN' if ok else 'REJECT'
    mark = '  ' if exp == '?' else ('ok' if got == exp else '!!')
    print('%s %-6s %-16s %8.1f  %-20s %s'
          % (mark, got, Path(p).name, t0, note, why[:58]))
cw.save_cache()
elapsed = time.time() - start
print('%.1fs per window' % (elapsed / max(1, len(tests))))
