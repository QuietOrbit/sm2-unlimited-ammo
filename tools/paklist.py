import sys, zipfile, re
pak = sys.argv[1]
pat = re.compile(sys.argv[2], re.I) if len(sys.argv) > 2 else None
with zipfile.ZipFile(pak) as z:
    names = z.namelist()
    print(f"# {len(names)} entries")
    for n in names:
        if pat is None or pat.search(n):
            print(n)
