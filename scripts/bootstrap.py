"""Create a local environment, migrate the database and seed synthetic data."""
import argparse
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import venv

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run(args):
    subprocess.run([str(arg) for arg in args], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-install", action="store_true", help="Use already installed dependencies.")
    args = parser.parse_args()
    if not PYTHON.exists():
        venv.create(ROOT / ".venv", with_pip=True)
    env_path = ROOT / ".env"
    content = (env_path if env_path.exists() else ROOT / ".env.example").read_text(encoding="utf-8")
    for key in ("EMS_SECRET_KEY", "EMS_DEMO_PASSWORD"):
        match = re.search(rf"(?m)^{key}=(.*)$", content)
        if not match:
            content += f"\n{key}={secrets.token_urlsafe(40)}\n"
        elif not match.group(1).strip().strip('\"\''):
            content = re.sub(rf"(?m)^{key}=.*$", f"{key}={secrets.token_urlsafe(40)}", content)
    env_path.write_text(content, encoding="utf-8")
    if os.name != "nt":
        env_path.chmod(0o600)
    if not args.skip_install:
        run([PYTHON, "-m", "pip", "install", "-r", "backend/requirements.txt"])
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if not npm:
            raise SystemExit("Install Node.js 22.12+ (including npm) before setup.")
        run([npm, "ci"])
    run([PYTHON, "backend/manage.py", "migrate", "--noinput"])
    run([PYTHON, "backend/manage.py", "seed_demo"])
    print("Ready. Start the local application with: npm run dev")
    print("Synthetic passwords and the secret key stay in the ignored .env file.")


if __name__ == "__main__":
    main()
