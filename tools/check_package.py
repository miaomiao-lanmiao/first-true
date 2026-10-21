from pathlib import Path
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
print("Wheel contains the frontend, local vendor assets and echo-chat entry point.")
