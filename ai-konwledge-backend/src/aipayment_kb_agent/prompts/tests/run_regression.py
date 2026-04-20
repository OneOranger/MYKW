from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml


def _post_json(url: str, payload: dict[str, Any], timeout_sec: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url=url,
        method="POST",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout_sec) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def _to_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _check_case(case: dict[str, Any], response: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expect = case.get("expect", {})
    meta = response.get("meta", {}) or {}
    hits = response.get("hits", []) or []
    content = str(response.get("content", "") or "")
    fallback = _to_bool(meta.get("fallbackUsed"), default=False)

    if "fallback" in expect and fallback != _to_bool(expect.get("fallback"), default=False):
        errors.append(f"fallback mismatch: expect={expect.get('fallback')} actual={fallback}")

    if "min_hits" in expect:
        min_hits = int(expect.get("min_hits") or 0)
        if len(hits) < min_hits:
            errors.append(f"hits too few: expect>={min_hits} actual={len(hits)}")

    if "max_hits" in expect:
        max_hits = int(expect.get("max_hits") or 0)
        if len(hits) > max_hits:
            errors.append(f"hits too many: expect<={max_hits} actual={len(hits)}")

    if "min_content_chars" in expect:
        min_chars = int(expect.get("min_content_chars") or 0)
        if len(content) < min_chars:
            errors.append(f"content too short: expect>={min_chars} actual={len(content)}")

    must_any = [str(x) for x in (expect.get("must_contain_any") or []) if str(x).strip()]
    if must_any and not any(token in content for token in must_any):
        errors.append(f"missing required terms: one of {must_any}")

    forbid_terms = [str(x) for x in (expect.get("forbid_terms") or []) if str(x).strip()]
    for token in forbid_terms:
        if token in content:
            errors.append(f"forbidden term detected: {token}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Run prompt regression cases against local API.")
    parser.add_argument(
        "--cases",
        default=str(Path(__file__).with_name("regression_cases.yaml")),
        help="Path to cases yaml.",
    )
    parser.add_argument("--endpoint", default="", help="Override API endpoint.")
    parser.add_argument("--top-k", type=int, default=0, help="Override top_k for all cases.")
    parser.add_argument("--timeout-sec", type=int, default=0, help="Override timeout seconds.")
    args = parser.parse_args()

    cases_path = Path(args.cases)
    if not cases_path.exists():
        print(f"[FATAL] cases file not found: {cases_path}")
        return 2

    payload = yaml.safe_load(cases_path.read_text(encoding="utf-8")) or {}
    defaults = payload.get("defaults", {}) or {}
    endpoint = args.endpoint or str(defaults.get("endpoint") or "http://127.0.0.1:8000/api/v1/query")
    timeout_sec = args.timeout_sec or int(defaults.get("timeout_sec") or 45)
    top_k = args.top_k or int(defaults.get("top_k") or 8)

    cases = payload.get("cases", []) or []
    if not cases:
        print("[FATAL] no cases defined.")
        return 2

    total = 0
    failed = 0
    for index, case in enumerate(cases, start=1):
        total += 1
        case_id = str(case.get("id") or f"case-{index}")
        message = str(case.get("message") or "").strip()
        session_id = str(case.get("session_id") or f"prompt-regression-{index}")
        category = case.get("category")
        if not message:
            failed += 1
            print(f"[FAIL] {case_id}: empty message")
            continue

        req = {
            "session_id": session_id,
            "message": message,
            "auto_upgrade": False,
            "top_k": top_k,
        }
        if category:
            req["category"] = category

        try:
            resp = _post_json(endpoint, req, timeout_sec=timeout_sec)
        except urllib.error.HTTPError as exc:
            failed += 1
            body = exc.read().decode("utf-8", errors="ignore")
            print(f"[FAIL] {case_id}: HTTP {exc.code} {exc.reason} body={body[:220]}")
            continue
        except Exception as exc:
            failed += 1
            print(f"[FAIL] {case_id}: request error: {exc}")
            continue

        errors = _check_case(case, resp)
        if errors:
            failed += 1
            print(f"[FAIL] {case_id}")
            for item in errors:
                print(f"  - {item}")
            continue

        meta = resp.get("meta", {}) or {}
        hits = resp.get("hits", []) or []
        print(
            f"[PASS] {case_id} "
            f"fallback={meta.get('fallbackUsed')} "
            f"hits={len(hits)} "
            f"chars={len(str(resp.get('content', '') or ''))}"
        )

    print(f"\nSummary: total={total}, failed={failed}, passed={total - failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
