# usage: pakgrep.py PAK NAME_REGEX CONTENT_REGEX [maxfiles]
import sys, zipfile, re
pak, nre, cre = sys.argv[1], re.compile(sys.argv[2], re.I), re.compile(sys.argv[3].encode(), re.I)
maxf = int(sys.argv[4]) if len(sys.argv) > 4 else 50
hits = 0
with zipfile.ZipFile(pak) as z:
    for n in z.namelist():
        if n.endswith('/') or not nre.search(n):
            continue
        data = z.read(n)
        lines = [l for l in data.splitlines() if cre.search(l)]
        if lines:
            hits += 1
            print(f"== {n} ({len(lines)} hits)")
            for l in lines[:8]:
                print("   ", l.decode('utf-8', 'replace').strip()[:200])
            if hits >= maxf:
                break
