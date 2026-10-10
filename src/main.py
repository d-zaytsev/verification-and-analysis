import argparse
import ast
import time
from pathlib import Path

from cfg import CFG


def _analyze(file: Path, format: str) -> None:
    file_text = file.read_text()
    parsed_ast = ast.parse(file_text)

    if format == "ast":
        print(ast.dump(parsed_ast, indent=1))
    elif format == "cfg":
        print(CFG.from_ast(parsed_ast.body))
    elif format == "cfg-dot":
        G = CFG.from_ast(parsed_ast.body).to_dot()
        G.layout(prog="dot")
        G.draw("graph.png")
        print("Image updated!")
    else:
        raise ValueError(format)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("pythonfile", help="The python file to be analyzed")
    parser.add_argument("format", help="Analyzing format")
    parser.add_argument(
        "--interval", type=float, default=0.5, help="Polling interval in seconds"
    )
    args = parser.parse_args()

    file = Path(args.pythonfile)
    last_mtime: int | None = None

    while True:
        if (mtime := file.stat().st_mtime_ns) != last_mtime:
            last_mtime = mtime
            print(f"--- {time.strftime('%H:%M:%S')} {file} changed ---")
            try:
                _analyze(file, args.format)
            except SyntaxError:
                pass

        time.sleep(args.interval)
