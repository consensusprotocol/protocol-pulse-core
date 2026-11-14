"""The moments-first exam (order 03:00 ET 2026-11-12): corpora + harness for law L-s (context integrity), the VO
fidelity gate (L-o item 11 / L-t) and the hard exclusions (L-u).

1. The corpora themselves, always (CPU, no network): indexes and hashes (no answer in INDEX.json); the order's counts
   per class; honest origin labels; every REAL case rebuilt verbatim from the editorial store (a missing store FAILS:
   nothing measured is never a pass, law L-m); sentence ids cross-checked against pp-selectid's own code at the
   commit the cases name; the package carries the selected sentences; blinding hides the answer; no single package
   field separates the verdicts (a format-only gate cannot sit the exam).
2. The harness, always: toy gates prove that it fails a gate that rejects everything, accepts everything, answers
   by position, crashes, exits, peeks or reaches the network, that an absent gate is ABSENT (never a pass), and that
   the thresholds are reachable at all.
3. The real gates: each corpus through $PP_MOMENTS_GATES (default `moments_gate_adapter`) in a subprocess
   (tests/adversarial/moments_exam.py); a missing module or function SKIPS with the reason, never passes.

    PP_MOMENTS_GATES=<module> PP_MOMENTS_PATH=<dir with it> python3 -m pytest tests/adversarial/test_moments_gates.py -q -s

A model-backed gate needs PP_MOMENTS_ALLOW_NETWORK=1 (otherwise its first connect is an ERROR); PP_MOMENTS_JOBS=N
runs N cases at once on threads (gates that declare THREAD_SAFE = True); PP_MOMENTS_TIMEOUT_S bounds each corpus
(default 3 h)."""
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import types

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(HERE, "corpora"))
import moments_exam as ME  # noqa: E402

CI_FAIL = ("steelman", "quoting_opponent", "sarcasm", "hypothetical", "conditional_split", "unresolved_referent",
           "some_people_say", "answer_without_question", "later_retraction", "reading_aloud", "wrong_speaker",
           "stale_time_reference", "false_dialogue", "title_adds_thesis")
CI_PASS = ("clean_assertion", "clean_conjunction_opener")
VO_FAIL_V1 = ("stance_flip", "could_to_will", "number_swapped", "number_rounded", "invented_agreement",
              "fact_not_in_clips", "absent_name", "banned_framing", "financial_imperative")
VO_PASS_V1 = ("faithful_paraphrase", "manifest_language")
# v1.1 (orchestrator order 05:25 ET 2026-11-12): line classes A attribution / B fact / C production / D host commentary
VO_FAIL_V11 = ("commentary_smuggles_number", "commentary_smuggles_name", "commentary_recharacterises",
               "certainty_upgrade", "invented_relation", "commentary_predicts", "commentary_imperative",
               "commentary_accuses", "stale_price_title", "stale_price_line", "commentary_as_quote")
VO_PASS_V11 = ("host_commentary", "hedge_matched_attribution")
VO_FAIL, VO_PASS = VO_FAIL_V1 + VO_FAIL_V11, VO_PASS_V1 + VO_PASS_V11
EX_EXCLUDE = ("accusation", "partner_attack", "imperative", "guaranteed_return", "single_source_breaking",
              "ad_read", "third_party_media", "altcoin")
EX_KEEP = ("policy_criticism", "framed_prediction", "neutral_company")
# the order's minimums; every must-accept set has >= 11 cases so that one false reject stays <= 10%
CLASSES = {"context_integrity": (CI_FAIL, CI_PASS, "fail", "pass", 40, 20),
           "vo_fidelity": (VO_FAIL, VO_PASS, "fail", "pass", 25, 11),
           "exclusions": (EX_EXCLUDE, EX_KEEP, "exclude", "keep", len(EX_EXCLUDE), 11)}
SCHEMA = {"context_integrity": ("pp.ci_case/1",), "vo_fidelity": ("pp.vo_case/1", "pp.vo_case/1.1"),
          "exclusions": ("pp.excl_case/1",)}
K_COMMIT = "d809a1f8"                     # pp-selectid's commit the cases' sentence ids are computed against


@pytest.fixture(scope="module")
def corpora():
    return {name: ME.load_corpus(name) for name in ME.GATES}


# ── 1. the corpora ──

def test_every_index_matches_its_files_and_carries_no_answer(corpora):
    for name, cases in corpora.items():
        d = os.path.join(ME.CORPORA, name)
        files = {f for f in os.listdir(d) if f.endswith(".json") and f != "INDEX.json"}
        assert files == {c["id"] + ".json" for c in cases}, f"{name}: files on disk differ from INDEX.json"
        assert len({c["id"] for c in cases}) == len(cases), f"{name}: duplicate ids"
        with open(os.path.join(d, "INDEX.json")) as f:
            rows = json.load(f)["cases"]
        assert all(set(r) == {"id", "file", "sha256"} for r in rows), f"{name}: INDEX.json carries more than v1"
        keys = [hashlib.sha256(r["id"].encode()).hexdigest() for r in rows]
        assert keys == sorted(keys), f"{name}: INDEX.json is not in hash order (an order can tell the verdict)"
        for c in cases:
            assert c["schema"] in SCHEMA[name], c["id"]
            if name == "vo_fidelity":                    # a class lives in one format version only
                v11 = c["expected"]["class"] in VO_FAIL_V11 + VO_PASS_V11
                assert c["schema"] == ("pp.vo_case/1.1" if v11 else "pp.vo_case/1"), c["id"]
            corpus, cls, nn = c["id"].split("__")
            assert corpus == name and cls == c["expected"]["class"] and nn.isdigit(), c["id"]


def test_counts_and_classes_meet_the_order(corpora):
    for name, (bad, good, v_bad, v_good, n_bad, n_good) in CLASSES.items():
        cases = corpora[name]
        got_bad = [c for c in cases if c["expected"]["verdict"] == v_bad]
        got_good = [c for c in cases if c["expected"]["verdict"] == v_good]
        assert len(got_bad) + len(got_good) == len(cases), f"{name}: a verdict outside {v_bad}/{v_good}"
        assert len(got_bad) >= n_bad and len(got_good) >= n_good, (name, len(got_bad), len(got_good))
        assert {c["expected"]["class"] for c in got_bad} == set(bad), f"{name}: must-reject classes differ"
        assert {c["expected"]["class"] for c in got_good} == set(good), f"{name}: must-accept classes differ"
        for c in cases:
            assert c["expected"]["why"].strip(), c["id"]


def test_vo_v11_meets_the_order(corpora):
    """Order 05:25 ET: >= 15 must-pass honest class-D lines, >= 10 must-pass hedge-matched attributions, >= 20
    must-fail lines that look like commentary but smuggle a number, a name, a recharacterisation, a certainty
    upgrade, an invented relation, a prediction, an imperative, an accusation or a stale price (the title 'Bitcoin ran
    from 16K to 126K' against a universe at ~$73,000 included); each case carries its expected class and verdict."""
    v11 = [c for c in corpora["vo_fidelity"] if c["schema"] == "pp.vo_case/1.1"]
    by = {}
    for c in v11:
        by.setdefault((c["expected"]["verdict"], c["expected"]["class"]), []).append(c)
    assert len(by.get(("pass", "host_commentary"), [])) >= 15
    assert len(by.get(("pass", "hedge_matched_attribution"), [])) >= 10
    assert sum(len(v) for (verdict, _), v in by.items() if verdict == "fail") >= 20
    assert {cls for verdict, cls in by if verdict == "fail"} == set(VO_FAIL_V11)
    title = [c for c in by[("fail", "stale_price_title")] if c["title"] == "Bitcoin ran from 16K to 126K"]
    assert len(title) == 1 and title[0]["expected"]["bad_title"] is True
    assert any("$73,500" in n["headline"] for n in title[0]["universe"]["news"]), title[0]["universe"]
    for c in v11:
        e = c["expected"]
        assert len(e["line_classes"]) == len(c["lines"]) and set(e["line_classes"]) <= set("ABCD"), c["id"]
        assert e["title_class"] in ("A", "B", "C", "D") and c["title"].strip(), c["id"]
        if e["class"] == "host_commentary":            # its own lines are all class D
            assert "D" in e["line_classes"] and set(e["line_classes"]) <= {"C", "D"}, c["id"]
        if e["class"] == "hedge_matched_attribution":
            assert "A" in e["line_classes"], c["id"]
        if e["verdict"] == "fail":
            assert e["rule"] and (e["bad_title"] or e["bad_line"] is not None), c["id"]


def test_origin_is_honest(corpora):
    """REAL = store record + hash; CONSTRUCTED only for a class with no REAL instance (the order), with the search
    that found none recorded."""
    for name, cases in corpora.items():
        real_classes = {c["expected"]["class"] for c in cases if c["origin"] == "REAL"}
        for c in cases:
            assert c["origin"] in ("REAL", "CONSTRUCTED"), c["id"]
            if c["origin"] == "CONSTRUCTED":
                assert c["provenance"]["record"] is None and c["expected"]["class"] not in real_classes, c["id"]
                assert c["provenance"]["found_by"].startswith("searched for a real instance"), c["id"]
                assert c["expected"]["why"].startswith("CONSTRUCTED"), c["id"]
            elif name != "vo_fidelity":
                assert c["provenance"]["record"] and len(c["provenance"]["record_sha256"]) == 64, c["id"]


def test_every_case_rebuilds_verbatim_from_the_store(corpora):
    """Each case is exactly what build_corpora.py extracts from the store records it names (sha256 of the record
    bytes included): no sentence was retyped, trimmed or reordered."""
    import store_extract
    if not os.path.isdir(os.path.join(store_extract.STORE, "transcripts")):
        pytest.fail(f"editorial store not found at {store_extract.STORE} (set PP_EDITORIAL_STORE): the corpus "
                    f"cannot be verified, and an unverified corpus is not a pass (law L-m)")
    import build_corpora
    built = build_corpora.build_all()
    for name, cases in corpora.items():
        by_id = {c["id"]: c for c in cases}
        assert sorted(c["id"] for c in built[name]) == sorted(by_id), f"{name}: case list differs"
        for b in built[name]:
            assert json.loads(json.dumps(b)) == by_id[b["id"]], f"{b['id']}: differs from a fresh extraction"


def _git_show(path):
    p = subprocess.run(["git", "-C", REPO, "show", f"{K_COMMIT}:{path}"], capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else None


def _function(src, name):
    tree = ast.parse(src)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(src, node)


def test_sentence_ids_match_pp_selectid_at_the_named_commit(corpora):
    """The cases claim k = pp-selectid d809a1f8's split; this runs THAT code (its tokens_from_record and
    split_sentences, with its own sentence_law, read from the git object, never from a working tree) on every
    record the corpora use and compares sentence k's text and times."""
    srcs = {p: _git_show(p) for p in ("pipeline/select_by_id.py", "pipeline/eligibility.py",
                                      "pipeline/sentence_law.py", "pipeline/transcript_store.py")}
    missing = [p for p, s in srcs.items() if s is None]
    if missing:
        pytest.skip(f"git objects of pp-selectid {K_COMMIT} not available ({missing}): cross-check not run")
    law = types.ModuleType("sentence_law_d809a1f8")
    law_src = srcs["pipeline/sentence_law.py"]
    head = _function(law_src, "is_terminal")
    consts = "\n".join(line for line in law_src.splitlines() if re.match(r"^(_TERMINAL|_ABBREV)\s*=", line))
    exec("import re\n" + consts + "\n" + head, law.__dict__)                              # noqa: S102
    ns = {"sentence_law": law, "html": __import__("html"), "re": re}
    ts_src = srcs["pipeline/transcript_store.py"]
    exec(next(line for line in ts_src.splitlines() if line.startswith("_SPLIT_TOKEN")) + "\n"
         + _function(ts_src, "read_text"), ns)                                              # noqa: S102
    exec(_function(srcs["pipeline/select_by_id.py"], "tokens_from_record"), ns)            # noqa: S102
    exec(_function(srcs["pipeline/eligibility.py"], "split_sentences"), ns)                # noqa: S102
    import store_extract as X
    seen = {}
    for cases in corpora.values():
        for c in cases:
            rec = (c.get("provenance") or {}).get("record")
            segs = [c] if rec else []
            segs += [s for s in c.get("package", {}).get("segments", []) + c.get("segments", [])]
            for s in segs:
                pv = s.get("provenance") or {}
                if pv.get("record") and pv["record"] not in seen:
                    with open(os.path.join(X.STORE, pv["record"]), "rb") as f:
                        seen[pv["record"]] = json.loads(f.read())
    assert len(seen) >= 30, f"only {len(seen)} records referenced"
    for rel, rec in seen.items():
        _, toks = ns["tokens_from_record"](rec)
        theirs = ns["split_sentences"](toks)
        _, mine = X.sentences(rec)
        assert len(theirs) == len(mine), rel
        for k, (a, b) in enumerate(theirs):
            text = ns["read_text"](" ".join(t["word"] for t in toks[a:b + 1]))
            assert (text, toks[a]["start"], toks[b]["end"]) == (mine[k]["text"], mine[k]["start"], mine[k]["end"]), \
                (rel, k)


def test_the_package_carries_the_selected_sentences(corpora):
    for c in corpora["context_integrity"]:
        w = c["window"]
        a, b = w["selected"]
        sel = " ".join(s["text"] for s in w["sentences"][a:b + 1])
        moment = [s for s in c["package"]["segments"] if s["role"] == "moment"]
        assert len(moment) == 1 and moment[0]["text"] == sel, c["id"]
        assert [s["n"] for s in w["sentences"]] == list(range(len(w["sentences"]))), c["id"]
        t0, t1 = w["sentences"][a]["start"], w["sentences"][b]["end"]
        assert w["sentences"][0]["end"] > t0 - w["before_s"] and w["sentences"][-1]["start"] < t1 + w["after_s"]
        adj = [s for s in c["package"]["segments"] if s["role"] == "adjacent"]
        assert len(adj) == 1 and adj[0]["text"].strip() and adj[0]["video_id"] != moment[0]["video_id"], c["id"]
        if c["expected"]["verdict"] == "pass":
            assert adj[0]["channel"] != moment[0]["channel"], f"{c['id']}: one channel twice in a must-pass package"
    for c in corpora["vo_fidelity"]:
        labels = {s["label"] for s in c["segments"]}
        assert all(set(ln["cites"]) <= labels for ln in c["lines"]), c["id"]
        assert c["segments"][0]["video_id"] != c["segments"][1]["video_id"], c["id"]
        bad = c["expected"]["bad_line"]
        bad_title = c["expected"].get("bad_title", False)
        assert (bad is None and not bad_title) == (c["expected"]["verdict"] == "pass"), c["id"]
        assert bad is None or 0 <= bad < len(c["lines"]), c["id"]
        if c["schema"] == "pp.vo_case/1.1":             # lines in play order: before A, after A, after B
            order = [{None: 0, "A": 1, "B": 2}[ln["after"]] for ln in c["lines"]]
            assert order == sorted(order) and c["lines"][0]["slot"] == "intro" and c["lines"][-1]["slot"] == "signoff"


def _keys(x):
    if isinstance(x, dict):
        return set(x) | set().union(*(_keys(v) for v in x.values())) if x else set()
    if isinstance(x, list):
        return set().union(*(_keys(v) for v in x)) if x else set()
    return set()


def test_blinding_hides_the_answer(corpora):
    for name, cases in corpora.items():
        for c in cases:
            b = ME.blind(c, salt="s1")
            assert not _keys(b) & {"expected", "provenance", "origin"}, c["id"]
            assert b["id"].startswith("case-") and b["id"] != ME.blind(c, salt="s2")["id"], c["id"]
            text = json.dumps(b)
            assert c["id"] not in text and "CONSTRUCTED" not in text, c["id"]
            if name == "exclusions":
                assert "video_id" not in b["source"] and "url" not in b["source"] and "k" not in _keys(
                    [b["moment"], b["context"]]), c["id"]


# what a format-only gate could key on; the trap-carrying fields of a class are exempt for that class only
def _ci_fields(cases):
    chans = sorted({s["channel"] for c in cases for s in c["package"]["segments"]}, key=len, reverse=True)

    def norm(t):
        for ch in chans:
            t = t.replace(ch, "<CH>")
        t = re.sub(r"<CH>'s (show|channel)", "<CH>", t)          # a person-named channel is credited as a show
        return re.sub(r"\(\d{4}-\d\d-\d\d\)", "(D)", t)
    return {"intro": lambda c: norm(c["package"]["vo"]["intro"]),
            "bridge": lambda c: norm(c["package"]["vo"]["bridges"][0]),
            "signoff": lambda c: c["package"]["vo"]["signoff"],
            "order": lambda c: "".join(s["role"][0] for s in c["package"]["segments"]),
            "caption": lambda c: norm(c["package"]["caption"]),
            "window": lambda c: (c["window"]["before_s"], c["window"]["after_s"]),
            "timing": lambda c: c["window"]["timing"],
            "date": lambda c: c["package"]["date"]}


def _vo_fields(cases):
    chans = sorted({s["channel"] for c in cases for s in c["segments"]}, key=len, reverse=True)

    def norm(t):
        for ch in chans:
            t = t.replace(ch, "<CH>")
        return re.sub(r"<CH>'s (show|channel)", "<CH>", t)
    return {"slots": lambda c: tuple(ln["slot"] for ln in c["lines"]),
            "n_lines": lambda c: len(c["lines"]),
            "intro": lambda c: (norm(c["lines"][0]["text"]), tuple(c["lines"][0]["cites"])),
            "b_only_line": lambda c: any(ln["cites"] == ["B"] for ln in c["lines"]),
            "signoff_template": lambda c: norm(c["lines"][-1]["text"]) if c["lines"][-1]["slot"] == "signoff" else "",
            # v1.1 fields (a v1 case has none of them)
            "title_template": lambda c: norm(c.get("title") or ""),
            "positions": lambda c: tuple(ln.get("after", "-") for ln in c["lines"]),
            "universe": lambda c: json.dumps(c.get("universe"), sort_keys=True)}


def _sents(c):
    return c["context"]["before"] + c["moment"]["sentences"] + c["context"]["after"]


def _decimals(c):
    return max(len(f"{t:.6f}".rstrip("0").split(".")[1]) if isinstance(t, float) else 0
               for s in _sents(c) for t in (s["start"], s["end"]))


def _ex_fields(cases):
    return {"n_moment": lambda c: len(c["moment"]["sentences"]),
            "small_context": lambda c: (len(c["context"]["before"]) < 6, len(c["context"]["after"]) < 6),
            "timing": lambda c: c["moment"].get("timing"),
            "has_description": lambda c: c["source"].get("description") is not None,
            "time_decimals": _decimals}


def _span_after(c):
    a = c["context"]["after"]
    return a[-1]["end"] - c["moment"]["sentences"][-1]["end"] if a else 0.0


def test_constructed_cases_look_like_real_ones(corpora):
    """Each CONSTRUCTED exclusion case's shape (context sizes, time precision, span, description length, publish
    time) also occurs among the REAL cases; and no two constructed cases share a context sentence."""
    cases = corpora["exclusions"]
    real = [c for c in cases if c["origin"] == "REAL"]
    con = [c for c in cases if c["origin"] == "CONSTRUCTED"]
    feats = {"n_before_bucket": lambda c: min(len(c["context"]["before"]) // 5, 4),
             "n_after_bucket": lambda c: min(len(c["context"]["after"]) // 5, 4),
             "time_decimals": _decimals,
             "desc_len_bucket": lambda c: min(len(c["source"].get("description") or "") // 150, 4),
             "round_publish_time": lambda c: (c["source"].get("published_at") or "")[14:19] == "00:00",
             "context_span_40s": lambda c: (_span_after(c) >= 40.0,
                                            (c["moment"]["sentences"][0]["start"] - c["context"]["before"][0]["start"]
                                             if c["context"]["before"] else 0.0) >= 40.0)}
    for name, f in feats.items():
        real_vals = {f(c) for c in real}
        for c in con:
            assert f(c) in real_vals, f"{c['id']}: {name} = {f(c)!r} never occurs in a real case"
    seen = {}
    for c in con:
        for s in c["context"]["before"] + c["context"]["after"]:
            assert seen.setdefault(s["text"], c["id"]) == c["id"], f"shared filler: {s['text']!r}"


def test_no_package_field_separates_the_verdicts(corpora):
    """For each field a format-only gate could key on: a lookup gate that rejects every value seen in any
    must-reject case would also reject > 10% of the must-accept cases, so it cannot sit the exam; and no value of
    the field is used ONLY by one must-reject class (a free per-class win), except where the field is that class's
    trap (false_dialogue: bridge, order; unresolved_referent: order)."""
    exempt = {("context_integrity", "false_dialogue"): {"bridge", "order"},
              ("context_integrity", "unresolved_referent"): {"order"},
              ("vo_fidelity", "financial_imperative"): {"signoff_template"},     # the imperative IS the sign-off
              ("vo_fidelity", "stale_price_title"): {"title_template"}}          # the title IS the trap
    for name, fields in (("context_integrity", _ci_fields), ("vo_fidelity", _vo_fields), ("exclusions", _ex_fields)):
        cases = [ME.blind(c) | {"expected": c["expected"]} for c in corpora[name]]
        v_bad = CLASSES[name][2]
        bad = [c for c in cases if c["expected"]["verdict"] == v_bad]
        good = [c for c in cases if c["expected"]["verdict"] != v_bad]
        for fname, f in fields(cases).items():
            bad_vals = {f(c) for c in bad}
            fr = sum(1 for c in good if f(c) in bad_vals) / len(good)
            assert fr > ME.FALSE_REJECT_MAX, f"{name}.{fname}: a lookup on this field alone passes the exam ({fr:.0%})"
            good_vals = {f(c) for c in good}
            for c in bad:
                if fname in exempt.get((name, c["expected"]["class"]), ()):
                    continue
                others = {f(o) for o in bad if o["expected"]["class"] != c["expected"]["class"]}
                assert f(c) in good_vals or f(c) in others, \
                    f"{name}.{fname} = {f(c)!r} appears only in class {c['expected']['class']}"


# ── 2. the harness itself ──

def _run(gates, corpus, tmp_path, env_extra=None, timeout=600, args=()):
    report = tmp_path / f"{corpus}.json"
    env = {k: v for k, v in os.environ.items() if not k.startswith("PP_MOMENTS_")}
    env.update(env_extra or {})
    p = subprocess.run([sys.executable, os.path.join(HERE, "moments_exam.py"), "--gates", gates, "--corpus", corpus,
                        "--report", str(report), *args], capture_output=True, text=True, env=env, timeout=timeout)
    rep = json.loads(report.read_text()) if report.exists() else None
    return p.returncode, rep, p.stdout + p.stderr


@pytest.mark.parametrize("corpus", list(ME.GATES))
def test_a_gate_that_rejects_everything_fails(corpus, tmp_path):
    status, rep, out = _run("moments_toy_gates.reject_all", corpus, tmp_path)
    t = rep["corpora"][corpus]["table"]["total"]
    assert status == 1 and t["missed"] == 0 and t["false_reject_rate"] == 1.0 and not t["ok"], out


@pytest.mark.parametrize("corpus", list(ME.GATES))
def test_an_uncertain_gate_is_a_rejecting_gate(corpus, tmp_path):
    status, rep, out = _run("moments_toy_gates.uncertain_all", corpus, tmp_path)
    t = rep["corpora"][corpus]["table"]["total"]
    assert status == 1 and t["missed"] == 0 and t["false_reject_rate"] == 1.0, out


@pytest.mark.parametrize("corpus", list(ME.GATES))
def test_a_gate_that_accepts_everything_fails(corpus, tmp_path):
    status, rep, out = _run("moments_toy_gates.accept_all", corpus, tmp_path)
    t = rep["corpora"][corpus]["table"]["total"]
    assert status == 1 and t["missed"] == t["must_reject"] > 0 and t["false_rejects"] == 0, out


@pytest.mark.parametrize("corpus", list(ME.GATES))
def test_a_gate_that_answers_by_position_fails(corpus, tmp_path):
    status, rep, out = _run("moments_toy_gates.by_position", corpus, tmp_path, args=("--seed", "7"))
    t = rep["corpora"][corpus]["table"]["total"]
    assert status == 1 and not t["ok"] and rep["seed"] == 7, out


@pytest.mark.parametrize("corpus", list(ME.GATES))
def test_a_crash_or_an_invalid_verdict_is_an_error(corpus, tmp_path):
    status, rep, out = _run("moments_toy_gates.broken", corpus, tmp_path)
    t = rep["corpora"][corpus]["table"]["total"]
    assert status == 2 and t["errors"] == t["must_reject"] + t["must_accept"] and not t["ok"], out
    if corpus == "context_integrity":                       # a crash keeps where it happened, for the builder
        assert all("toy: gate crashed" in r["traceback"] for r in rep["corpora"][corpus]["rows"]), out


def test_a_gate_that_exits_is_an_error_never_absent(tmp_path):
    status, rep, out = _run("moments_toy_gates.exits", "context_integrity", tmp_path)
    t = rep["corpora"]["context_integrity"]["table"]["total"]
    assert status == 2 and t["absent"] == 0 and t["errors"] == t["must_reject"] + t["must_accept"], out


def test_a_missing_gate_is_absent_never_a_pass(tmp_path):
    status, rep, out = _run("moments_toy_gates.no_such_module", "context_integrity", tmp_path)
    assert status == 3 and rep["absent_reason"] and "ABSENT" in out, out
    status, rep, out = _run("moments_toy_gates.partial", "vo_fidelity", tmp_path,
                            env_extra={"PP_MOMENTS_SALT": "x"})
    t = rep["corpora"]["vo_fidelity"]["table"]["total"]
    assert status == 3 and t["absent"] == t["must_reject"] + t["must_accept"] and not t["ok"], out


def test_the_gate_never_sees_the_answer(tmp_path):
    status, rep, out = _run("moments_toy_gates.peeks", "context_integrity", tmp_path)
    rows = rep["corpora"]["context_integrity"]["rows"]
    assert status == 2 and all(r["verdict"] == ME.ERROR and "KeyError" in r["why"] for r in rows), out


@pytest.mark.parametrize("gate", ["moments_toy_gates.network", "moments_toy_gates.network_reverse"])
def test_the_network_is_refused_unless_allowed(gate, tmp_path):
    """The RUNNER's own guard refuses (NetworkRefused, 'moments_exam: ...'), not only this suite's child guard (the
    runner is a Python child of this suite, so tests/adversarial/child_guard is under it too and would refuse with its
    own message): a connect, and the reverse lookups gethostbyaddr / getnameinfo (integrator batch 78: the runner let
    gethostbyaddr out). The prefix is the runner's ERROR row format, `{type(e).__name__}: {e}` (moments_exam._judge):
    a change there fails this test, on purpose. It also holds only because refuse_network() sets its wrappers over the
    child guard's unconditionally (a 'patch only if unpatched' runner would fail it, rightly)."""
    status, rep, out = _run(gate, "exclusions", tmp_path)
    rows = rep["corpora"]["exclusions"]["rows"]
    assert status == 2 and all(r["why"].startswith("NetworkRefused: moments_exam: network is disabled")
                               for r in rows), out
    if gate.endswith("_reverse"):                    # the toy alternates per case: both need >= 2 rows (33 today)
        assert {n for n in ("gethostbyaddr", "getnameinfo") if any(f"({n} of " in r["why"] for r in rows)} == \
            {"gethostbyaddr", "getnameinfo"}, (len(rows), [r["why"][:120] for r in rows[:4]])


def test_the_runner_refuses_every_call_of_the_suites_list():
    """One list, three guards (integrator batch 78): after refuse_network() every call of child_guard/netguard_names.py
    is the runner's own refusal. Run in a child, because refuse_network patches the socket module for good."""
    probe = ("import importlib.util, socket, sys; "
             f"s = importlib.util.spec_from_file_location('me', {os.path.join(HERE, 'moments_exam.py')!r}); "
             "m = importlib.util.module_from_spec(s); s.loader.exec_module(m); m.refuse_network(); "
             "ng = m._netguard_names(); "
             "print(' '.join([getattr(socket.socket, n).__name__ for n in ng.INET_METHODS] + "
             "[getattr(socket, n).__name__ for n in ng.LOOKUPS]))")
    out = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, timeout=60)
    names = out.stdout.split()
    if len(names) < 9:
        pytest.fail(f"CONTROL (test setup, not the pinned defect): the probe ran: {out.stderr[-300:]}")
    expected = ("connect", "connect_ex", "sendto", "sendmsg",                     # pinned here, not read from the list
                "getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr", "getnameinfo")
    assert names == [f"_exam_no_{n}" for n in expected], names


@pytest.mark.parametrize("corpus", list(ME.GATES))
def test_the_thresholds_are_reachable(corpus, tmp_path):
    status, rep, out = _run("moments_toy_gates.oracle", corpus, tmp_path, env_extra={"PP_MOMENTS_SALT": "control"})
    t = rep["corpora"][corpus]["table"]["total"]
    assert status == 0 and t["ok"] and t["false_reject_rate"] == 0.0, out
    n_apart = sum(1 for c in ME.load_corpus(corpus) if c["expected"].get("stratum") in ME.APART)
    assert t["apart"]["n"] == n_apart and t["apart"]["rejected"] == n_apart, out
    assert t["must_reject"] + t["must_accept"] + n_apart == len(ME.load_corpus(corpus)), out


# ── 3. the real gates ──

@pytest.mark.parametrize("corpus", list(ME.GATES))
def test_the_gate_sits_the_exam(corpus, tmp_path):
    """100% of must-fail rejected; false rejects on the must-pass set <= 10% (the number is printed: it is PBX's
    supply); no ERROR. Skipped with the reason, never passed, when the gate is absent (the report must show it
    absent: an exit status alone never makes a skip)."""
    gates = os.environ.get("PP_MOMENTS_GATES", "moments_gate_adapter")
    env = {k: v for k, v in os.environ.items()          # the committed corpus, always: PP_MOMENTS_CORPORA is not passed
           if k.startswith("PP_MOMENTS_") and k not in ("PP_MOMENTS_REPORT", "PP_MOMENTS_SALT", "PP_MOMENTS_CORPORA")}
    status, rep, out = _run(gates, corpus, tmp_path, env,
                            timeout=float(os.environ.get("PP_MOMENTS_TIMEOUT_S", "10800")))
    print(out)
    report = os.environ.get("PP_MOMENTS_REPORT")
    if report and rep:
        with open(f"{report}.{corpus}.json", "w") as f:
            json.dump(rep, f, indent=1)
    rows = (rep or {}).get("corpora", {}).get(corpus, {}).get("rows", [])
    if status == 3 and rep is not None and (rep.get("absent_reason") or (rows and all(
            r["verdict"] == ME.ABSENT for r in rows))):
        pytest.skip(f"{corpus}: gate absent ({gates}): {rep.get('absent_reason') or 'function not defined'}")
    # an exit status is never the verdict: the report must exist, cover every committed case, and meet the
    # thresholds when the table is recomputed here from its rows
    assert rep is not None, f"{corpus}: no report (status {status})\n{out}"
    assert sorted(r["id"] for r in rows) == sorted(c["id"] for c in ME.load_corpus(corpus)), \
        f"{corpus}: the report does not cover exactly the committed corpus"
    t = ME.table(corpus, rows)
    print(ME.render(corpus, t))
    assert status == 0 and t["total"]["ok"], f"{corpus}: the gate does not meet the thresholds (status {status})\n{out}"
