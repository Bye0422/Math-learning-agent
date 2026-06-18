import argparse
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
STREAMLIT = PROJECT_ROOT / ".venv" / "Scripts" / "streamlit.exe"


def run_command(name, command, timeout=None):
    started = time.time()
    print(f"\n== {name} ==")
    print(" ".join(str(part) for part in command))

    result = subprocess.run(
        [str(part) for part in command],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        timeout=timeout,
    )

    elapsed = time.time() - started

    if result.stdout:
        print(result.stdout.rstrip())

    if result.stderr:
        print(result.stderr.rstrip())

    if result.returncode != 0:
        raise RuntimeError(f"{name} failed with exit code {result.returncode}")

    print(f"[OK] {name} completed in {elapsed:.2f}s")


def collect_python_files():
    files = []

    for path in PROJECT_ROOT.rglob("*.py"):
        if ".venv" in path.parts:
            continue

        files.append(path)

    return files


def run_py_compile():
    files = collect_python_files()
    run_command(
        "Python syntax check",
        [PYTHON, "-m", "py_compile", *files],
        timeout=120,
    )


def run_unit_tests():
    run_command(
        "Unit tests",
        [PYTHON, "-m", "unittest", "discover", "-s", "tests", "-v"],
        timeout=120,
    )


def run_env_check(online=False):
    command = [PYTHON, "scripts/check_env.py"]

    if online:
        command.append("--online")

    run_command(
        "Environment check",
        command,
        timeout=120,
    )


def run_streamlit_smoke(port):
    command = [
        STREAMLIT,
        "run",
        "app.py",
        "--server.port",
        str(port),
        "--server.headless",
        "true",
    ]

    print(f"\n== Streamlit smoke test ==")
    print(" ".join(str(part) for part in command))

    process = subprocess.Popen(
        [str(part) for part in command],
        cwd=str(PROJECT_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    output_lines = []

    try:
        deadline = time.time() + 20

        while time.time() < deadline:
            line = process.stdout.readline() if process.stdout else ""

            if line:
                output_lines.append(line.rstrip())
                print(line.rstrip())

                if "Local URL:" in line or "Uvicorn server started" in line:
                    print("[OK] Streamlit reached listening state")
                    return

            if process.poll() is not None:
                break

        raise RuntimeError("Streamlit did not reach listening state within 20 seconds")

    finally:
        if process.poll() is None:
            process.terminate()

            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()


def run_eval_v2():
    run_command(
        "Eval V2",
        [PYTHON, "evals/run_eval_v2.py"],
        timeout=1800,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Run Math-learning-agent validation harness.",
    )
    parser.add_argument(
        "--mode",
        choices=["quick", "full"],
        default="quick",
        help="quick runs syntax/tests/env; full also runs Streamlit smoke and optionally Eval V2.",
    )
    parser.add_argument(
        "--online",
        action="store_true",
        help="Allow online checks in scripts/check_env.py.",
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="Run Eval V2. This may call LLM APIs and take longer.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Port for Streamlit smoke test in full mode.",
    )

    args = parser.parse_args()

    if not PYTHON.exists():
        raise FileNotFoundError(f"Python not found: {PYTHON}")

    run_py_compile()
    run_unit_tests()
    run_env_check(online=args.online)

    if args.mode == "full":
        if not STREAMLIT.exists():
            raise FileNotFoundError(f"Streamlit not found: {STREAMLIT}")

        run_streamlit_smoke(args.port)

        if args.eval:
            run_eval_v2()

    print("\nHarness completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n[FAIL] {exc}", file=sys.stderr)
        sys.exit(1)
