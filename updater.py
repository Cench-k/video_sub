"""실행 전 버전 확인 및 자동 업데이트.

자막추출기_실행.bat 이 app.py 보다 먼저 이 스크립트를 호출한다.

종료 코드
    0  : 그대로 실행해도 됨 (최신이거나, 업데이트했지만 런처는 그대로)
    10 : 런처(bat)가 업데이트됨 -> 실행을 중단하고 사용자에게 재실행을 안내
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
LAUNCHERS = ("자막추출기_실행.bat", "설치_및_실행.bat")
REQ = os.path.join(ROOT, "requirements.txt")
REQ_HASH = os.path.join(ROOT, "venv", ".reqhash")

EXIT_OK = 0
EXIT_LAUNCHER_UPDATED = 10


def out(msg=""):
    print(msg, flush=True)


def git(*args, timeout=60):
    """git 실행 후 (성공여부, stdout) 반환."""
    try:
        p = subprocess.run(
            ("git",) + args,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False, ""
    return p.returncode == 0, (p.stdout or "").strip()


def file_hash(path):
    if not os.path.exists(path):
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def current_version():
    ok, text = git("log", "-1", "--date=format:%Y-%m-%d %H:%M", "--format=%h  %cd  %s")
    return text if ok else ""


def upstream_ref():
    ok, ref = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    return ref if ok and ref else "origin/main"


def sync_requirements(changed):
    """requirements.txt 가 바뀌었으면 패키지를 다시 설치한다."""
    now = file_hash(REQ)
    if not now:
        return
    saved = ""
    if os.path.exists(REQ_HASH):
        with open(REQ_HASH, "r", encoding="utf-8") as f:
            saved = f.read().strip()

    if saved == now:
        return

    # 첫 도입 시점: 이미 설치가 끝난 환경이면 해시만 기록하고 재설치하지 않는다.
    if not saved and not changed:
        with open(REQ_HASH, "w", encoding="utf-8") as f:
            f.write(now)
        return

    out("  - requirements.txt 가 변경되어 패키지를 갱신합니다...")
    py = os.path.join(ROOT, "venv", "Scripts", "python.exe")
    if not os.path.exists(py):
        # 다른 인터프리터에 설치해 버리지 않도록, venv 가 없으면 아무것도 하지 않는다.
        out("  ! venv 를 찾을 수 없어 패키지 갱신을 건너뜁니다.")
        return
    r = subprocess.run([py, "-m", "pip", "install", "-r", REQ], cwd=ROOT)
    if r.returncode != 0:
        out("  ! 패키지 갱신에 실패했습니다. 기존 패키지로 실행을 계속합니다.")
        return
    with open(REQ_HASH, "w", encoding="utf-8") as f:
        f.write(now)
    out("  - 패키지 갱신 완료")


def update_source():
    out("[버전 확인]")

    if shutil.which("git") is None:
        out("  - git 이 없어 업데이트를 건너뜁니다.")
        return EXIT_OK

    ok, _ = git("rev-parse", "--git-dir")
    if not ok:
        out("  - git 저장소가 아니어서 업데이트를 건너뜁니다.")
        return EXIT_OK

    version = current_version()
    if version:
        out("  - 현재 버전: " + version)

    out("  - 최신 버전을 확인하는 중...")
    ok, _ = git("fetch", "--quiet", "origin", timeout=45)
    if not ok:
        out("  - 서버에 연결할 수 없어 현재 버전으로 실행합니다. (오프라인?)")
        sync_requirements(changed=False)
        return EXIT_OK

    ref = upstream_ref()
    ok_local, local = git("rev-parse", "HEAD")
    ok_remote, remote = git("rev-parse", ref)
    if not (ok_local and ok_remote):
        out("  - 원격 버전을 읽을 수 없어 현재 버전으로 실행합니다.")
        sync_requirements(changed=False)
        return EXIT_OK

    if local == remote:
        out("  - 이미 최신 버전입니다.")
        sync_requirements(changed=False)
        return EXIT_OK

    # 원격이 앞서 있는지 확인 (갈라졌으면 손대지 않는다)
    ok_behind, behind = git("rev-list", "--count", "HEAD.." + ref)
    ok_ahead, ahead = git("rev-list", "--count", ref + "..HEAD")
    if not (ok_behind and ok_ahead):
        out("  - 버전 비교에 실패해 현재 버전으로 실행합니다.")
        sync_requirements(changed=False)
        return EXIT_OK
    if ahead != "0":
        out("  ! 로컬에만 있는 커밋이 %s개 있어 자동 업데이트를 건너뜁니다." % ahead)
        out("    (직접 git push 또는 git pull 로 정리해 주세요)")
        sync_requirements(changed=False)
        return EXIT_OK
    if behind == "0":
        sync_requirements(changed=False)
        return EXIT_OK

    # 추적 중인 파일의 수정만 확인한다. 새로 생긴 파일(업로드물 등)은
    # ff-only 병합이 실제로 충돌할 때만 문제가 되므로 막지 않는다.
    _, dirty = git("status", "--porcelain", "--untracked-files=no")
    if dirty:
        out("  ! 수정된 파일이 있어 자동 업데이트를 건너뜁니다:")
        for line in dirty.splitlines()[:5]:
            out("      " + line)
        out("    (수정 내용을 보관하려면 git stash, 버리려면 git checkout -- . )")
        sync_requirements(changed=False)
        return EXIT_OK

    out("  - 새 버전 %s개를 내려받습니다..." % behind)
    before = {name: file_hash(os.path.join(ROOT, name)) for name in LAUNCHERS}

    ok, _ = git("merge", "--ff-only", ref, timeout=120)
    if not ok:
        out("  ! 업데이트에 실패해 현재 버전으로 실행합니다.")
        sync_requirements(changed=False)
        return EXIT_OK

    out("  - 업데이트 완료: " + current_version())
    sync_requirements(changed=True)

    for name in LAUNCHERS:
        if before[name] and before[name] != file_hash(os.path.join(ROOT, name)):
            out("")
            out("  * 실행 파일(%s)이 업데이트되었습니다." % name)
            return EXIT_LAUNCHER_UPDATED

    return EXIT_OK


# ── 엔진(AI 패키지) 버전 ────────────────────────────────────────────
# 자동 최신 유지 대상. torch/torchaudio 는 제외한다: CUDA 빌드가 아닌
# CPU 휠로 조용히 바뀌어 버릴 수 있어 확인만 하고 손대지 않는다.
ENGINE_AUTO = ("funasr", "modelscope", "easyocr", "gradio", "whisperx")
ENGINE_CHECK_ONLY = ("torch", "torchaudio")
ENGINE_STAMP = os.path.join(ROOT, "venv", ".enginecheck")
ENGINE_INTERVAL = 24 * 60 * 60  # 하루에 한 번만 조회


def installed_version(name):
    import importlib.metadata as md

    try:
        return md.version(name)
    except Exception:
        return None


def latest_version(name, timeout=6):
    import json
    import urllib.request

    url = "https://pypi.org/pypi/%s/json" % name
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.load(r)["info"]["version"]
    except Exception:
        return None


def is_older(a, b):
    """a 가 b 보다 낮은 버전이면 True."""
    try:
        from packaging.version import Version

        return Version(a) < Version(b)
    except Exception:
        pass

    def parts(v):
        return [int(x) for x in re.findall(r"\d+", v)[:4]]

    try:
        return parts(a) < parts(b)
    except Exception:
        return False


def due_for_engine_check():
    if os.environ.get("SUBEXT_FORCE_ENGINE_CHECK"):
        return True
    try:
        return (time.time() - os.path.getmtime(ENGINE_STAMP)) > ENGINE_INTERVAL
    except OSError:
        return True


def touch_engine_stamp():
    try:
        with open(ENGINE_STAMP, "w", encoding="utf-8") as f:
            f.write(str(int(time.time())))
    except OSError:
        pass


def check_engines():
    out("")
    out("[엔진 버전]")

    names = [n for n in ENGINE_AUTO if installed_version(n)] + list(ENGINE_CHECK_ONLY)
    for n in ENGINE_AUTO:
        if not installed_version(n):
            out("  - %-12s 설치되지 않음" % n)

    if not due_for_engine_check():
        for n in names:
            out("  - %-12s %s" % (n, installed_version(n) or "없음"))
        out("  (최신 버전 조회는 하루에 한 번만 합니다)")
        return

    outdated = []
    for n in names:
        cur = installed_version(n)
        if not cur:
            continue
        new = latest_version(n)
        if new is None:
            out("  - %-12s %s  (최신 버전 조회 실패)" % (n, cur))
            continue
        if is_older(cur, new):
            mark = "고정" if n in ENGINE_CHECK_ONLY else "갱신 대상"
            out("  - %-12s %s -> %s  [%s]" % (n, cur, new, mark))
            if n in ENGINE_AUTO:
                outdated.append(n)
        else:
            out("  - %-12s %s  (최신)" % (n, cur))

    touch_engine_stamp()

    if not outdated:
        out("  - 갱신할 엔진이 없습니다.")
        return

    if os.environ.get("SUBEXT_CHECK_ONLY"):
        out("  - 확인만 하도록 설정되어 갱신하지 않습니다. (SUBEXT_CHECK_ONLY)")
        return

    py = os.path.join(ROOT, "venv", "Scripts", "python.exe")
    if not os.path.exists(py):
        out("  ! venv 를 찾을 수 없어 엔진 갱신을 건너뜁니다.")
        return

    out("  - 엔진을 갱신합니다: " + ", ".join(outdated))
    r = subprocess.run(
        [py, "-m", "pip", "install", "--upgrade", "--upgrade-strategy", "only-if-needed"]
        + outdated,
        cwd=ROOT,
    )
    if r.returncode != 0:
        out("  ! 엔진 갱신에 실패했습니다. 기존 버전으로 실행을 계속합니다.")
        return
    out("  - 엔진 갱신 완료")
    for n in outdated:
        out("      %-12s %s" % (n, installed_version(n) or "?"))


def main():
    rc = update_source()
    if rc == EXIT_LAUNCHER_UPDATED:
        return rc
    try:
        check_engines()
    except Exception:
        out("  ! 엔진 버전 확인 중 문제가 발생해 건너뜁니다.")
    return EXIT_OK


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
