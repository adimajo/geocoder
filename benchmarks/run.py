"""Run find/near on benchmarks/cases.json, print timings and (optionally) dump results.

Usage: python benchmarks/run.py [--dump out.json]
Compare two dumps with: python benchmarks/run.py --diff a.json b.json
"""
import json
import sys
import time


def score(cases, results):
    """Accuracy against the coordinates of the address the query was made from"""
    from geocoder.geocoding.spatial import haversine

    by_kind = {}
    for case, result in zip(cases, results):
        stats = by_kind.setdefault(case["kind"], [0, 0, 0])
        stats[0] += 1
        if result["longitude"] is not None:
            d = float(haversine(result["longitude"], result["latitude"], *case["truth"]))
            stats[1] += d <= 100  # the right address
            stats[2] += d <= 1000  # the right street / neighbourhood
    print(f"{'kind':14s}{'n':>5s}{'<100m':>8s}{'<1km':>8s}")
    for kind, (n, near, close) in sorted(by_kind.items()):
        print(f"{kind:14s}{n:5d}{near / n:8.0%}{close / n:8.0%}")
    n, near, close = (sum(v[i] for v in by_kind.values()) for i in range(3))
    print(f"{'all':14s}{n:5d}{near / n:8.0%}{close / n:8.0%}")


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
    score(cases["find"], out["find"])
    if "--dump" in sys.argv:
        with open(sys.argv[sys.argv.index("--dump") + 1], "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, sort_keys=True, default=str)


if __name__ == "__main__":
    main()
