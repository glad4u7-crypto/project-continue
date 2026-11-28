"""In-container nbclient entrypoint. Runs only inside the networkless sandbox."""
import argparse
import base64
from pathlib import Path
import nbformat
from nbclient import NotebookClient


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("destination")
    parser.add_argument("--timeout", type=int, required=True)
    args = parser.parse_args()
    source = Path(args.source)
    destination = Path(args.destination)
    notebook = nbformat.read(source, as_version=4)
    nbformat.validate(notebook)
    client = NotebookClient(
        notebook,
        timeout=args.timeout,
        kernel_name="python3",
        resources={"metadata": {"path": "/tmp"}},
        allow_errors=False,
        record_timing=True,
    )
    execution_error = None
    try:
        executed = client.execute()
    except Exception as exc:
        execution_error = exc
        executed = notebook
    nbformat.validate(executed)
    destination.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(executed, destination)
    if destination.stat().st_size > 256 * 1024:
        raise RuntimeError("executed notebook output exceeds the 256 KiB artifact limit")
    encoded = base64.b64encode(destination.read_bytes()).decode("ascii")
    print("PC_NOTEBOOK_RESULT:" + encoded, flush=True)
    if execution_error is not None:
        raise RuntimeError("notebook execution failed; sanitized traceback artifact was retained") from execution_error


if __name__ == "__main__":
    main()
