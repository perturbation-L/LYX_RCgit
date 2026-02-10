from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PROBLEMS_FILE = DATA_DIR / "problems.json"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


def ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not PROBLEMS_FILE.exists():
        PROBLEMS_FILE.write_text("[]", encoding="utf-8")


def load_problems() -> list[dict[str, Any]]:
    ensure_storage()
    return json.loads(PROBLEMS_FILE.read_text(encoding="utf-8"))


def save_problems(problems: list[dict[str, Any]]) -> None:
    PROBLEMS_FILE.write_text(json.dumps(problems, ensure_ascii=False, indent=2), encoding="utf-8")


def run_python(code: str, stdin_data: str, time_limit: float) -> tuple[bool, str, str, float]:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        file_name = f.name

    started = time.perf_counter()
    try:
        result = subprocess.run(
            ["python3", file_name],
            input=stdin_data,
            text=True,
            capture_output=True,
            timeout=time_limit,
            check=False,
        )
        elapsed = time.perf_counter() - started
        return result.returncode == 0, result.stdout, result.stderr, elapsed
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - started
        return False, "", "Time Limit Exceeded", elapsed
    finally:
        try:
            os.remove(file_name)
        except OSError:
            pass


class Handler(BaseHTTPRequestHandler):
    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        body = self.rfile.read(length).decode("utf-8")
        return json.loads(body)

    def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_file(TEMPLATES_DIR / "index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/api/problems":
            self._send_json(load_problems())
            return
        if parsed.path.startswith("/static/"):
            rel = parsed.path.removeprefix("/static/")
            file_path = STATIC_DIR / rel
            ctype = "text/plain; charset=utf-8"
            if rel.endswith(".css"):
                ctype = "text/css; charset=utf-8"
            elif rel.endswith(".js"):
                ctype = "application/javascript; charset=utf-8"
            self._send_file(file_path, ctype)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/problems":
            self._create_problem()
            return
        if parsed.path == "/api/judge":
            self._judge()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def _create_problem(self) -> None:
        payload = self._read_json()
        title = str(payload.get("title", "")).strip()
        description = str(payload.get("description", "")).strip()
        time_limit = float(payload.get("time_limit") or 1.0)
        testcases = payload.get("testcases") or []

        if not title:
            self._send_json({"error": "题目标题不能为空"}, HTTPStatus.BAD_REQUEST)
            return
        if not isinstance(testcases, list) or not testcases:
            self._send_json({"error": "至少需要一个测试点"}, HTTPStatus.BAD_REQUEST)
            return

        clean_cases = []
        for case in testcases:
            clean_cases.append({
                "input": str(case.get("input", "")),
                "output": str(case.get("output", "")),
            })

        problems = load_problems()
        new_problem = {
            "id": len(problems) + 1,
            "title": title,
            "description": description,
            "time_limit": max(0.1, time_limit),
            "testcases": clean_cases,
        }
        problems.append(new_problem)
        save_problems(problems)
        self._send_json(new_problem, HTTPStatus.CREATED)

    def _judge(self) -> None:
        payload = self._read_json()
        problem_id = int(payload.get("problem_id", 0))
        code = str(payload.get("code", ""))

        problems = load_problems()
        problem = next((item for item in problems if item["id"] == problem_id), None)
        if problem is None:
            self._send_json({"error": "题目不存在"}, HTTPStatus.NOT_FOUND)
            return
        if not code.strip():
            self._send_json({"error": "代码不能为空"}, HTTPStatus.BAD_REQUEST)
            return

        accepted = True
        details = []
        for idx, case in enumerate(problem["testcases"], start=1):
            ok, stdout, stderr, elapsed = run_python(code, case["input"], float(problem["time_limit"]))
            expected = case["output"].strip()
            actual = stdout.strip()
            passed = ok and actual == expected
            if not passed:
                accepted = False
            details.append({
                "case": idx,
                "passed": passed,
                "expected": expected,
                "actual": actual,
                "stderr": stderr.strip(),
                "time_ms": round(elapsed * 1000, 2),
            })

        self._send_json({"accepted": accepted, "details": details})


def run(host: str = "0.0.0.0", port: int = 5000) -> None:
    ensure_storage()
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Server running: http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
