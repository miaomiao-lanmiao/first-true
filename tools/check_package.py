from pathlib import Path
import os
import subprocess
import sys
import tempfile
import zipfile

archives = sorted(Path("echo/dist").glob("*.whl"))
assert archives, "Build the wheel first: python -m build echo"
with zipfile.ZipFile(archives[-1]) as archive:
    names = set(archive.namelist())
    for file in ["index.html", "app.js", "styles.css", "vendor/purify.min.js", "vendor/marked.min.js", "vendor/highlight.min.js"]:
        assert f"echo/web_static/{file}" in names, f"Missing Web asset: {file}"
    assert not any("__pycache__" in name or name.endswith(".pyc") for name in names)
    metadata = next(name for name in names if name.endswith("/entry_points.txt"))
    assert "echo-chat = echo.cli:app" in archive.read(metadata).decode()
    package_metadata = next(name for name in names if name.endswith(".dist-info/METADATA"))
    version = next(line[9:] for line in archive.read(package_metadata).decode().splitlines() if line.startswith("Version: "))

with tempfile.TemporaryDirectory(prefix="echo-wheel-check-") as temporary:
    target = Path(temporary) / "installed"
    install = subprocess.run([
        sys.executable, "-m", "pip", "install", "--no-index", "--no-deps", "--disable-pip-version-check",
        "--target", str(target), str(archives[-1].resolve()),
    ], capture_output=True, text=True, timeout=60)
    assert install.returncode == 0, install.stderr
    environment = {**os.environ, "PYTHONPATH": str(target), "ECHO_CONFIG_DIR": str(Path(temporary) / "storage")}
    result = subprocess.run([sys.executable, "-m", "echo", "--version"],
                            cwd=temporary, env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert f"v{version}" in result.stdout
    loaded = subprocess.run([sys.executable, "-c", "import echo; print(echo.__file__); print(echo.__version__)"],
                            cwd=temporary, env=environment, capture_output=True, text=True, timeout=30)
    assert loaded.returncode == 0, loaded.stderr
    assert str(target).lower() in loaded.stdout.lower()
    assert version in loaded.stdout
print("Wheel assets, offline installation, package version and entry point outside the source checkout passed.")
