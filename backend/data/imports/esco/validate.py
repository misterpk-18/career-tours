#!/usr/bin/env python3
"""Validate skills.csv and career_skills.csv against careers.csv.

Run from anywhere:  python3 backend/data/imports/esco/validate.py
Exits nonzero if any check fails. Warnings do not affect the exit code.
"""

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGING = HERE / "_staging"

errors: list[str] = []
warnings: list[str] = []


def fail(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def read(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


careers = read(HERE / "careers.csv")
skills = read(HERE / "skills.csv")
pairs = read(HERE / "career_skills.csv")

career_titles = {c["career_title"] for c in careers}
skill_ids = {s["skill_id"] for s in skills}

# ---------------------------------------------------------------- referential

if len(skill_ids) != len(skills):
    dupes = [k for k, n in Counter(s["skill_id"] for s in skills).items() if n > 1]
    fail(f"skills.csv: duplicate skill_id: {dupes[:10]}")

seen_pairs = Counter((p["career_title"], p["skill_id"]) for p in pairs)
dupe_pairs = [k for k, n in seen_pairs.items() if n > 1]
if dupe_pairs:
    fail(f"career_skills.csv: duplicate (career_title, skill_id): {dupe_pairs[:10]}")

orphan_skills = {p["skill_id"] for p in pairs} - skill_ids
if orphan_skills:
    fail(f"career_skills.csv: {len(orphan_skills)} skill_id not in skills.csv: {sorted(orphan_skills)[:10]}")

orphan_careers = {p["career_title"] for p in pairs} - career_titles
if orphan_careers:
    fail(f"career_skills.csv: {len(orphan_careers)} career_title not in careers.csv: {sorted(orphan_careers)[:10]}")

missing = career_titles - {p["career_title"] for p in pairs}
if missing:
    fail(f"{len(missing)} of {len(career_titles)} careers have NO skills: {sorted(missing)[:10]}")

# --------------------------------------------------------------------- values

VALID_CATEGORY = {"technical", "soft", "domain"}
VALID_RELATION = {"essential", "optional"}
VALID_SOURCE = {"esco", "authored"}

bad_cat = {s["skill_category"] for s in skills} - VALID_CATEGORY
if bad_cat:
    fail(f"skills.csv: invalid skill_category values: {sorted(bad_cat)}")

bad_src = {s["source"] for s in skills} - VALID_SOURCE
if bad_src:
    fail(f"skills.csv: invalid source values: {sorted(bad_src)}")

bad_rel = {p["relation_type"] for p in pairs} - VALID_RELATION
if bad_rel:
    fail(f"career_skills.csv: invalid relation_type values: {sorted(bad_rel)}")

for p in pairs:
    try:
        w = int(p["weight"])
    except (ValueError, KeyError):
        fail(f"non-integer weight for {p['career_title']} / {p['skill_id']}: {p.get('weight')!r}")
        continue
    if not 1 <= w <= 100:
        fail(f"weight out of range 1-100 for {p['career_title']} / {p['skill_id']}: {w}")

# ------------------------------------------------------------- per-career shape

by_career = defaultdict(list)
for p in pairs:
    by_career[p["career_title"]].append(p)

for title, ps in sorted(by_career.items()):
    ws = [int(p["weight"]) for p in ps if p["weight"].lstrip("-").isdigit()]
    if not ws:
        continue
    ess = [int(p["weight"]) for p in ps if p["relation_type"] == "essential"]

    if len(ps) < 5:
        fail(f"{title}: only {len(ps)} skills, need >= 5")
    if len(ess) < 3:
        fail(f"{title}: only {len(ess)} essential skills, need >= 3")
    if len(set(ws)) < 4:
        fail(f"{title}: only {len(set(ws))} distinct weights, need >= 4 (flattened weighting)")
    if max(ws) < 70:
        fail(f"{title}: max weight {max(ws)}, need >= 70")
    if sum(1 for w in ws if w > 80) > 0.4 * len(ws):
        fail(f"{title}: {sum(1 for w in ws if w > 80)}/{len(ws)} weights above 80, max 40% allowed")

    opt = [int(p["weight"]) for p in ps if p["relation_type"] == "optional"]
    if ess and opt and (sum(ess) / len(ess)) <= (sum(opt) / len(opt)):
        fail(f"{title}: mean essential weight {sum(ess)/len(ess):.1f} <= mean optional {sum(opt)/len(opt):.1f}")

# ---------------------------------------------------------------- traceability

raw_pairs_path = STAGING / "esco_pairs_raw.csv"
if raw_pairs_path.exists():
    original = {(r["career_title"], r["skill_id"]) for r in read(raw_pairs_path)}
    invented = {
        (p["career_title"], p["skill_id"])
        for p in pairs
        if p["career_source"] == "esco" and (p["career_title"], p["skill_id"]) not in original
    }
    if invented:
        fail(f"{len(invented)} ESCO career pairs not in the upstream ESCO relations: {sorted(invented)[:5]}")
else:
    warn(f"{raw_pairs_path.name} missing - skipped ESCO traceability check")

no_esco_id = [s for s in skills if s["source"] == "esco" and not s["esco_skill_id"]]
if no_esco_id:
    fail(f"{len(no_esco_id)} skills marked source=esco have no esco_skill_id")

# ------------------------------------------------------------------- reporting

print(f"careers.csv       {len(careers):>6} careers")
print(f"skills.csv        {len(skills):>6} skills   {dict(Counter(s['source'] for s in skills))}")
print(f"                         {dict(Counter(s['skill_category'] for s in skills))}")
print(f"career_skills.csv {len(pairs):>6} pairs    {dict(Counter(p['relation_type'] for p in pairs))}")
print(f"                         {dict(Counter(p['career_source'] for p in pairs))}")

if by_career:
    counts = sorted(len(v) for v in by_career.values())
    print(f"skills per career  min={counts[0]} median={counts[len(counts)//2]} max={counts[-1]}")

# per-batch keep rates, if the curation batches are still around
rates = []
for i in range(1, 5):
    import json

    bp = STAGING / f"vocab_batch_{i}.json"
    if bp.exists():
        rows = json.loads(bp.read_text())
        rates.append((i, 100 * sum(1 for r in rows if r.get("keep")) / len(rows)))
if rates:
    spread = max(r for _, r in rates) - min(r for _, r in rates)
    print("vocab keep rates  " + "  ".join(f"batch{i}={r:.0f}%" for i, r in rates) + f"  spread={spread:.0f}pts")
    if spread > 15:
        warn(f"vocabulary keep-rate spread is {spread:.0f} points - agents calibrated differently")

print()
for w in warnings:
    print(f"WARN  {w}")
for e in errors:
    print(f"FAIL  {e}")

if errors:
    print(f"\n{len(errors)} error(s)")
    sys.exit(1)
print("\nall checks passed")
