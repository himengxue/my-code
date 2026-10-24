"""Shared durable jobs. Unknown writes are never automatically retried."""
from __future__ import annotations
import hashlib
import json
import sqlite3
import time
import uuid
from pathlib import Path


class Ledger:
    def __init__(self, root: Path):
        root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(root / "operator.sqlite", timeout=15)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS jobs(
          id TEXT PRIMARY KEY, kind TEXT NOT NULL, dedupe_key TEXT NOT NULL UNIQUE,
          status TEXT NOT NULL, payload TEXT NOT NULL, result TEXT,
          created REAL NOT NULL, updated REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS events(
          id INTEGER PRIMARY KEY, job_id TEXT, event TEXT NOT NULL, at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS observations(
          key TEXT PRIMARY KEY, value TEXT NOT NULL, updated REAL NOT NULL);
        ''')

    def close(self):
        self.db.close()

    def add(self, kind, payload, key=None):
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        key = key or hashlib.sha256((kind + canonical).encode()).hexdigest()
        now = time.time()
        with self.db:
            old = self.db.execute("SELECT id FROM jobs WHERE dedupe_key=?", (key,)).fetchone()
            if old:
                return {**self.get(old["id"]), "existing": True}
            job_id = uuid.uuid4().hex[:16]
            self.db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?)",
                            (job_id, kind, key, "planned", canonical, None, now, now))
        return self.get(job_id)

    def get(self, job_id):
        row = self.db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise ValueError("任务不存在")
        data = dict(row)
        data["payload"] = json.loads(data["payload"])
        data["result"] = json.loads(data["result"]) if data["result"] else None
        return data

    def list(self, limit=30):
        rows = self.db.execute("SELECT id FROM jobs ORDER BY created DESC LIMIT ?", (max(1, min(limit, 200)),)).fetchall()
        return [self.get(row["id"]) for row in rows]

    def ready(self, job_id, patch):
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            job = self.get(job_id)
            if job["status"] not in {"planned", "ready"}:
                raise ValueError("已提交、已完成或结果未知的任务不能重新准备")
            job["payload"].update(patch)
            self.db.execute("UPDATE jobs SET payload=?,status='ready',updated=? WHERE id=?",
                            (json.dumps(job["payload"], ensure_ascii=False), time.time(), job_id))
        return self.get(job_id)

    def dispatch(self, job_id):
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            changed = self.db.execute("UPDATE jobs SET status='dispatched',updated=? WHERE id=? AND status='ready'", (time.time(), job_id)).rowcount
            if changed != 1:
                raise ValueError("任务未就绪或已有提交记录；必须先核对远端结果，不能重复发送")
            self.db.execute("INSERT INTO events(job_id,event,at) VALUES (?,?,?)", (job_id, "dispatch_recorded_before_click", time.time()))
        return self.get(job_id)

    def finish(self, job_id, confirmed, result):
        with self.db:
            changed = self.db.execute("UPDATE jobs SET status=?,result=?,updated=? WHERE id=? AND status IN ('dispatched','uncertain')",
                                      ("confirmed" if confirmed else "uncertain", json.dumps(result, ensure_ascii=False), time.time(), job_id)).rowcount
            if changed != 1:
                raise ValueError("只能核对已经提交或结果未确认的任务")
        return self.get(job_id)

    def unattempted(self, job_id, result):
        if result.get('clicked') is not False:
            raise ValueError('只有明确未点击的结果可以返回就绪状态')
        with self.db:
            changed=self.db.execute("UPDATE jobs SET status='ready',result=?,updated=? WHERE id=? AND status='dispatched'",
                (json.dumps(result,ensure_ascii=False),time.time(),job_id)).rowcount
            if changed!=1:raise ValueError('任务状态无法回到就绪')
        return self.get(job_id)

    def observe(self, key, value):
        with self.db:
            self.db.execute("INSERT INTO observations VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated=excluded.updated",
                            (key, json.dumps(value, ensure_ascii=False), time.time()))

    def observation(self, key):
        row = self.db.execute("SELECT value,updated FROM observations WHERE key=?", (key,)).fetchone()
        return {"data": json.loads(row["value"]), "observed_at": row["updated"]} if row else None
