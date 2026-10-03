import argparse
import ast
from pathlib import Path

from cfg import CFG

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("pythonfile", help="The python file to be analyzed")
    parser.add_argument("format", help="Analyzing format")
    args = parser.parse_args()

    file = Path(args.pythonfile)
    file_text = file.read_text()
    parsed_ast = ast.parse(file_text)

    if args.format == "ast":
        print(ast.dump(parsed_ast, indent=1))
    elif args.format == "cfg":
        print(CFG.from_ast(parsed_ast.body))
    else:
        raise ValueError(args.format)
