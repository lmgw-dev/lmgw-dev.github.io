#!/usr/bin/env python3
"""Turn a run of lmgw's live API compatibility check into data/compat.json for the compatibility page.

Usage: scripts/compat-export.py [RUN] [--lmgw-version V] [--lmgw-dir DIR] [-o data/compat.json]
       (`just compat` runs it)

RUN is a results.json, a run directory, or a runs directory (its newest run is taken); the default
is the newest run under $LMGW_DIR/target/compat/runs (LMGW_DIR defaults to ../lmgw).

The output is built from an allowlist: a fixed set of fields is copied or derived, nothing else
passes. The input is checked the same way, so a field a later version of the check adds stops the
export until someone has decided whether it may be public. Request and response excerpts, base
URLs, hostnames, paths, usage, cost and timings never reach the output; each failure's reason is
one of the plain sentences below, found by its rule id. A rule without a sentence stops the export.
Stdlib only.
"""
import argparse
import datetime
import json
import os
import pathlib
import re
import sys

RESULT_KEYS = {"key", "requests", "scenario", "route", "mode", "usage", "seconds", "evidence",
               "notes", "reason", "model", "model_notes", "violations", "status"}
RUN_KEYS = {"started", "base", "models", "routes", "modes", "scenarios", "requests", "cost_note",
            "cost_usd", "unpriced_models", "totals", "previous", "seconds", "lmgw_version"}
TOP_KEYS = {"run", "diff", "results"}
STATUSES = ["pass", "fail", "model", "unsupported", "skipped"]

ROUTES = {
    "chat": {"label": "Chat Completions", "path": "/v1/chat/completions"},
    "responses": {"label": "Responses", "path": "/v1/responses"},
    "messages": {"label": "Anthropic Messages", "path": "/v1/messages"},
}
MODES = ["plain", "stream"]

# The scenario catalogue, as the check documents it.
SCENARIOS = {
    "text": "One-word answer",
    "system": "System prompt obeyed",
    "multi_turn": "Two text turns, the first answer replayed as history",
    "tool_noargs": "Tool without arguments, result sent back, final answer",
    "tool_nested": "Tool with object and array arguments, result, replay",
    "tool_parallel": "Two tool calls in one turn, both results, final answer",
    "tool_error": "Tool result flagged as an error",
    "tool_forced": "tool_choice naming one of two tools",
    "tool_none": "tool_choice none with tools present",
    "image": "Image input",
    "json_schema": "Structured output (JSON schema)",
    "stop_seq": "Stop sequence",
    "max_tokens": "Token cap: the length finish reason",
    "reasoning_tool": "Reasoning, tool call, replay with reasoning, final answer",
    "prev_response": "Second turn through previous_response_id",
    "count_tokens": "The route's token counter",
    "error_unknown_model": "Unknown model: 404 in the route's error shape",
    "error_malformed": "Truncated JSON body: 400 in the route's error shape",
}

ROUTE_ONLY = {"error_unknown_model", "error_malformed"}

EGRESSES = [
    ("kilo", "OpenAI-compatible upstream", "through an OpenAI-compatible gateway service"),
    ("anthropic", "Anthropic API", "native"),
    ("openai", "OpenAI API", "native"),
    ("aistudio", "Gemini API", "native"),
    ("local", "llama.cpp", "local model"),
]
FAMILIES = {"anthropic": "Claude", "openai": "GPT", "google": "Gemini"}

FINISH_CAP = ("A reply cut off by the token cap ends as completed, where OpenAI reports incomplete "
              "(max_output_tokens).")
NOARGS = "A call to a tool without arguments carries empty arguments (\"\") instead of {}."
REPLAY_FAILED = ("The turn that replays the tool result ends as failed, without a response.completed "
                 "event or a final answer.")

# Plain sentences, by rule id (the part of a violation before its first colon, without "turn N: ").
RULE_TEXT = {
    "sdk.schema.responses.event":
        "Streamed text events lack the logprobs field that the OpenAI SDK's types require.",
    "chat.sse.tool_call.arguments": NOARGS,
    "responses.sse.function_call.arguments": NOARGS,
    "responses.sse.arguments.deltas":
        "A streamed tool call announces its arguments as {} and then streams the real ones, so the "
        "argument deltas do not add up to the final arguments.",
    "stop_sequence":
        "The text runs past the stop sequence instead of ending at it.",
    "stop_sequence.reason":
        "The stop reason is end_turn with no stop_sequence, where the matched stop sequence should "
        "be reported.",
    "finish_reason": FINISH_CAP,
    "finish_reason.failed": REPLAY_FAILED,
    "route.served":
        "/v1/responses/input_tokens is not supported yet (HTTP 405).",
    "count.object":
        "/v1/responses/input_tokens is not supported yet (HTTP 405).",
    "tool_args.empty_object": NOARGS,
    "responses.function_call.arguments": NOARGS,
    "responses.status": REPLAY_FAILED,
    "text": REPLAY_FAILED,
    "sdk.exception": REPLAY_FAILED,
}
# An HTTP error's sentence, by its detail; an unknown detail stops the export.
HTTP_TEXT = [
    (re.compile(r"tool_use\.input: Input should be an object"),
     "The request that replays the tool call was rejected with HTTP 400: the call's input was not an "
     "object."),
    (re.compile(r"HTTP 504 \(api_error\): upstream timeout$"),
     "The upstream did not answer within the timeout configured for it, so lmgw answered HTTP 504."),
    (re.compile(r"HTTP 400 \(\w+\): Unsupported parameter: 'stop' is not supported with this model\.$"),
     "The model refuses the stop parameter with HTTP 400, and lmgw passes that refusal on."),
]
# One sentence for a whole cell, when one of its violations names what went wrong for all of them.
CELL_TEXT = [
    (re.compile(r"^chat\.sse\.done_last: the last event is .*, not \[DONE\]$"),
     "The upstream stopped sending partway through the stream, and lmgw kept the stream open with no "
     "end and no error event until the client timed out."),
]
# Why a cell was not run, by the run's own reason.
SKIP_TEXT = {
    "the model card lists no reasoning control":
        "Not run: lmgw's model card for this model lists no reasoning control.",
}
# A rule whose detail is free text only gets its sentence when the detail is the known one.
DETAIL = {
    "finish_reason": re.compile(r"'completed' maps to 'stop', expected \['length'\]"),
    "sdk.exception": re.compile(r"Didn't receive a `response\.completed` event"),
}
# Soft checks (status "model": the protocol held, the model did something else).
NOTE_TEXT = [
    (re.compile(r"^turn \d+ called \[.*\] again instead of answering$"),
     "After the tool's error result the model called the tool again instead of answering."),
    (re.compile(r"^the answer with the tool call carried no reasoning / thinking content$"),
     "The model sent no reasoning content with its tool call, so the reasoning replay was not exercised."),
    (re.compile(r"^the answer does not use the tool result: '.*'$"),
     "The final answer did not use the tool result."),
]


def die(msg):
    sys.exit(f"compat-export: {msg}")


def find_results(arg, lmgw_dir):
    p = pathlib.Path(arg) if arg else pathlib.Path(lmgw_dir) / "target/compat/runs"
    if p.is_file():
        return p
    if (p / "results.json").is_file():
        return p / "results.json"
    runs = sorted(p.glob("*/results.json")) if p.is_dir() else []
    if not runs:
        die(f"no results.json under {p}")
    return runs[-1]


def rule_of(violation):
    v = re.sub(r"^turn \d+: ", "", violation)
    rid = v.split(":", 1)[0].strip()
    if rid == "finish_reason" and "'other:failed'" in v:
        return "finish_reason.failed"
    return rid


def public_reason(r):
    if r["status"] == "pass":
        return []
    if r["status"] == "model":
        texts = []
        for n in r["model_notes"]:
            hit = [t for rx, t in NOTE_TEXT if rx.match(n)]
            if not hit:
                die(f"unmapped model note in {r['key']}: {n!r}; add a sentence to NOTE_TEXT")
            texts.append(hit[0])
    elif r["status"] == "fail" and r["violations"]:
        for v in r["violations"]:
            hit = [t for rx, t in CELL_TEXT if rx.match(re.sub(r"^turn \d+: ", "", v))]
            if hit:
                return hit[:1]
        texts = []
        for v in r["violations"]:
            rid = rule_of(v)
            if rid == "http":
                hit = [t for rx, t in HTTP_TEXT if rx.search(v)]
                if not hit:
                    die(f"unmapped HTTP error in {r['key']}: {v!r}; add a sentence to HTTP_TEXT")
                texts.append(hit[0])
                continue
            if rid not in RULE_TEXT or (rid in DETAIL and not DETAIL[rid].search(v)):
                die(f"unmapped rule {rid!r} in {r['key']}; add a sentence to RULE_TEXT")
            texts.append(RULE_TEXT[rid])
    elif r["status"] == "skipped" and r.get("reason") in SKIP_TEXT:
        texts = [SKIP_TEXT[r["reason"]]]
    else:
        die(f"{r['key']}: status {r['status']!r} without a mappable reason; extend the export")
    return list(dict.fromkeys(texts))


def egress_of(model):
    if "/" not in model:
        return "local", ""
    head = model.split("/", 1)[0]
    if head not in {e for e, _, _ in EGRESSES} or head == "local":
        die(f"model {model!r} has an unknown alias prefix")
    fam = ""
    if head == "kilo":
        seg = model.split("/")
        if len(seg) < 3 or seg[1] not in FAMILIES:
            die(f"unknown model family in {model!r}")
        fam = FAMILIES[seg[1]]
    return head, fam


def sdk_versions(lmgw_dir):
    req = pathlib.Path(lmgw_dir) / "scripts/compat_live/requirements.txt"
    out = {}
    if req.is_file():
        for line in req.read_text().splitlines():
            m = re.fullmatch(r"(openai|anthropic)==([0-9][0-9A-Za-z.]*)", line.strip())
            if m:
                out[m[1]] = m[2]
    if set(out) != {"openai", "anthropic"}:
        die(f"could not read the openai and anthropic SDK pins from {req}")
    return out


def lmgw_version(lmgw_dir):
    cargo = pathlib.Path(lmgw_dir) / "Cargo.toml"
    m = re.search(r'^version\s*=\s*"([0-9][^"]*)"', cargo.read_text(), re.M) if cargo.is_file() else None
    if not m:
        die("no lmgw version found: pass --lmgw-version")
    return m[1]


def scan_public(obj, path="$"):
    """Last line of defence: no URL, path, address, key or e-mail in any string that goes out."""
    bad = re.compile(r"https?://|/home/|/tmp/|\b\d{1,3}(?:\.\d{1,3}){3}\b|sk-|@|\bBearer\b|\.ts\.net")
    if isinstance(obj, str):
        if bad.search(obj):
            die(f"suspicious string at {path}: {obj!r}")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            scan_public(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            scan_public(v, f"{path}[{i}]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", nargs="?", default="")
    ap.add_argument("--lmgw-version", default="")
    ap.add_argument("--lmgw-dir", default=os.environ.get("LMGW_DIR", "../lmgw"))
    ap.add_argument("-o", "--out", default="data/compat.json")
    a = ap.parse_args()

    src = find_results(a.run, a.lmgw_dir)
    d = json.loads(src.read_text())
    if set(d) != TOP_KEYS:
        die(f"unexpected top-level fields: {sorted(set(d) ^ TOP_KEYS)}")
    run = d["run"]
    if set(run) - RUN_KEYS:
        die(f"unexpected run fields: {sorted(set(run) - RUN_KEYS)}")
    for r in d["results"]:
        if set(r) - RESULT_KEYS or not RESULT_KEYS - {"evidence"} <= set(r):
            die(f"unexpected result fields in {r.get('key')}: {sorted(set(r) ^ RESULT_KEYS)}")

    started = datetime.datetime.strptime(run["started"], "%Y%m%dT%H%M%SZ")
    version = a.lmgw_version or run.get("lmgw_version") or lmgw_version(a.lmgw_dir)

    for s in run["scenarios"]:
        if s not in SCENARIOS:
            die(f"scenario {s!r} has no title; add it to SCENARIOS")
    for r in run["routes"]:
        if r not in ROUTES:
            die(f"unknown route {r!r}")
    if set(run["modes"]) - set(MODES):
        die(f"unknown mode in {run['modes']}")

    models = []
    for m in run["models"]:
        eid, fam = egress_of(m)
        models.append({"id": m, "family": fam, "egress": eid})

    findings = {}
    cells = []
    for r in d["results"]:
        if r["status"] not in STATUSES:
            die(f"unknown status {r['status']!r} in {r['key']}")
        if r["scenario"] not in SCENARIOS or r["route"] not in ROUTES or r["mode"] not in MODES:
            die(f"unknown scenario, route or mode in {r['key']}")
        model = r["model"]
        if r["scenario"] in ROUTE_ONLY:
            # Checked once per route, with a made-up alias: no model of the run.
            model = "*"
        elif model not in run["models"]:
            die(f"result for a model that is not in the run: {model!r}")
        reasons = public_reason(r)
        cell = {"scenario": r["scenario"], "route": r["route"], "mode": r["mode"],
                "model": model, "egress": egress_of(model)[0] if model != "*" else "",
                "status": r["status"]}
        if reasons:
            cell["reason"] = " ".join(reasons)
            cell["_keys"] = []
            for text in reasons:
                key = (r["status"], r["route"], text)
                f = findings.setdefault(key, {"status": r["status"], "route": r["route"],
                                              "reason": text, "cells": []})
                f["cells"].append([r["scenario"], r["mode"], model])
                cell["_keys"].append(key)
        cells.append(cell)

    order = {s: i for i, s in enumerate(STATUSES)}
    route_order = list(ROUTES)
    scen_order = list(SCENARIOS)
    flist = sorted(findings.values(), key=lambda f: (order[f["status"]], route_order.index(f["route"]),
                                                      -len(f["cells"])))
    ids = {}
    for i, f in enumerate(flist):
        f["id"] = i + 1
        ids[(f["status"], f["route"], f["reason"])] = f["id"]
        f["count"] = len(f["cells"])
        f["scenarios"] = sorted({c[0] for c in f["cells"]}, key=scen_order.index)
        f["models"] = [m for m in run["models"] if any(c[2] == m for c in f["cells"])]
        f["modes"] = [m for m in MODES if any(c[1] == m for c in f["cells"])]
        del f["cells"]
    for c in cells:
        if "_keys" in c:
            c["findings"] = [ids[k] for k in c.pop("_keys")]

    out = {
        "lmgw_version": version,
        "run_date": started.strftime("%Y-%m-%d"),
        "sdks": sdk_versions(a.lmgw_dir),
        "statuses": STATUSES,
        "routes": [{"id": r, **ROUTES[r]} for r in ROUTES if r in run["routes"]],
        "modes": [m for m in MODES if m in run["modes"]],
        "scenarios": [{"id": s, "title": SCENARIOS[s]} for s in run["scenarios"]],
        "egresses": [{"id": e, "label": lab, "note": n,
                      "models": [{"id": m["id"], "family": m["family"]} for m in models
                                 if m["egress"] == e]} for e, lab, n in EGRESSES],
        "models": [{"id": m["id"], "family": m["family"], "egress": m["egress"]} for m in models],
        "cells": cells,
        "findings": flist,
    }
    scan_public(out)
    dest = pathlib.Path(a.out)
    tmp = dest.with_suffix(".json.new")
    tmp.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    tmp.replace(dest)
    counts = {s: sum(c["status"] == s for c in cells) for s in STATUSES}
    print(f"{dest}: lmgw {version}, run {out['run_date']}, {len(cells)} cells {counts}, "
          f"{len(flist)} findings")


if __name__ == "__main__":
    main()
