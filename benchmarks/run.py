"""Run find/near on benchmarks/cases.json, print timings and (optionally) dump results.

Usage: python benchmarks/run.py [--dump out.json]
Compare two dumps with: python benchmarks/run.py --diff a.json b.json
"""
import json
import sys
import time


def main():
    if sys.argv[1:2] == ["--diff"]:
        a, b = (json.load(open(p)) for p in sys.argv[2:4])
        n = 0
        for kind in ("find", "near"):
            for i, (x, y) in enumerate(zip(a[kind], b[kind])):
                if x != y:
                    n += 1
                    print(kind, i, "\n  ", x, "\n  ", y)
        print(f"{n} differences")
        return

    import geocoder

    with open("benchmarks/cases.json", encoding="utf-8") as f:
        cases = json.load(f)
    out = {}
    t = time.perf_counter()
    out["find"] = [geocoder.find(c["code_postal"], c["commune"], c["adresse"]) for c in cases["find"]]
    t_find = time.perf_counter() - t
    t = time.perf_counter()
    out["near"] = [geocoder.near(tuple(p)) for p in cases["near"]]
    t_near = time.perf_counter() - t
    print(f"find: {len(cases['find'])} queries in {t_find:.3f}s ({t_find / len(cases['find']) * 1e3:.2f} ms/q)")
    print(f"near: {len(cases['near'])} queries in {t_near:.3f}s ({t_near / len(cases['near']) * 1e3:.2f} ms/q)")
    if "--dump" in sys.argv:
        with open(sys.argv[sys.argv.index("--dump") + 1], "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, sort_keys=True, default=str)


if __name__ == "__main__":
    main()
