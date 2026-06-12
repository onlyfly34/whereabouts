#!/usr/bin/env python3
"""Validate events.yaml structure for PRs. Mirrors what index.html expects."""
import re
import sys

import yaml

CATEGORIES = {"war", "protest", "disaster", "justice", "disease", "missing", "other"}
ARTS = {
    "plane", "blackbox", "report", "search", "ship", "ocean", "tank", "ruins",
    "fire", "flags", "talks", "handshake", "document", "troops", "ballot",
    "gavel", "flagup", "virus", "crowd", "barricade", "scale", "prison", "archive",
}
DATE_RE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")
ID_RE = re.compile(r"^[a-z0-9-]+$")
OPEN_LIMIT = 20

errors: list[str] = []
warnings: list[str] = []


def need_bilingual(obj, where):
    if not isinstance(obj, dict) or not str(obj.get("zh", "")).strip() or not str(obj.get("en", "")).strip():
        errors.append(f"{where}: 需要 zh 與 en 兩個非空欄位")


def main():
    with open("events.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    events = data.get("events")
    if not isinstance(events, list) or not events:
        errors.append("events: 必須是非空清單")
        report()

    seen = set()
    open_count = 0
    for e in events:
        eid = str(e.get("id", "<無 id>"))
        if not ID_RE.fullmatch(eid):
            errors.append(f"{eid}: id 只能用小寫英數與連字號")
        if eid in seen:
            errors.append(f"{eid}: id 重複")
        seen.add(eid)

        if e.get("category") not in CATEGORIES:
            errors.append(f"{eid}: category 必須是 {sorted(CATEGORIES)}")
        status = e.get("status")
        if status not in ("open", "closed"):
            errors.append(f"{eid}: status 必須是 open 或 closed")
        if status == "open":
            open_count += 1
        if e.get("art") not in ARTS:
            errors.append(f"{eid}: art「{e.get('art')}」不在插圖庫 {sorted(ARTS)}")

        for field in ("opened", "last_progress"):
            v = str(e.get(field, ""))
            if not DATE_RE.fullmatch(v):
                errors.append(f"{eid}: {field}「{v}」要寫成 \"YYYY-MM-DD\"（記得加引號）")

        need_bilingual(e.get("title"), f"{eid}.title")
        need_bilingual(e.get("summary"), f"{eid}.summary")
        if status == "open":
            need_bilingual(e.get("stuck"), f"{eid}.stuck")
        if status == "closed":
            outcome = e.get("outcome") or {}
            if not DATE_RE.fullmatch(str(outcome.get("date", ""))):
                errors.append(f"{eid}: closed 事件需要 outcome.date（YYYY-MM-DD）")
            need_bilingual(outcome.get("text"), f"{eid}.outcome.text")

        timeline = e.get("timeline")
        if not isinstance(timeline, list) or not timeline:
            warnings.append(f"{eid}: 沒有 timeline（前端會顯示「還在整理中」佔位頁）")
            continue
        sourced = 0
        for i, n in enumerate(timeline):
            where = f"{eid}.timeline[{i}]"
            if not DATE_RE.fullmatch(str(n.get("date", ""))):
                errors.append(f"{where}: date 要寫成 \"YYYY-MM-DD\" 或 \"YYYY-MM\"")
            need_bilingual(n.get("text"), f"{where}.text")
            if n.get("art") is not None and n["art"] not in ARTS:
                errors.append(f"{where}: art「{n['art']}」不在插圖庫")
            src = n.get("source")
            if src is not None:
                if not str(src.get("name", "")).strip() or not str(src.get("url", "")).startswith("http"):
                    errors.append(f"{where}: source 需要 name 與 http(s) 開頭的 url")
                else:
                    sourced += 1
            if n.get("video") is not None and not re.fullmatch(r"[\w-]{6,}", str(n["video"])):
                errors.append(f"{where}: video 應為 YouTube 影片 id")
        if sourced < 2:
            errors.append(f"{eid}: 只有 {sourced} 個節點有來源（收錄標準：至少 2 個獨立可信來源）")

    if open_count > OPEN_LIMIT:
        warnings.append(f"open 事件 {open_count} 件，超過上限原則 {OPEN_LIMIT} 件——新事件進來前先看看有沒有舊事件該歸檔")

    report()


def report():
    for w in warnings:
        print(f"⚠️  {w}")
    for e in errors:
        print(f"❌ {e}")
    if errors:
        sys.exit(1)
    print(f"✅ events.yaml OK（{len(warnings)} warnings）")
    sys.exit(0)


if __name__ == "__main__":
    main()
