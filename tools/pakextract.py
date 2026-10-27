# usage: pakextract.py PAK OUTDIR member [member...]
import sys, zipfile, os
pak, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(pak) as z:
    for m in sys.argv[3:]:
        dest = os.path.join(out, *m.split('/'))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(z.read(m))
        print(dest)
