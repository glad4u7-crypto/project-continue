"""In-container nbclient entrypoint. Runs only inside the networkless sandbox."""
import argparse
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
    executed = client.execute()
    nbformat.validate(executed)
    destination.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(executed, destination)
    if destination.stat().st_size > 256 * 1024:
        raise RuntimeError("executed notebook output exceeds the 256 KiB artifact limit")


if __name__ == "__main__":
    main()
