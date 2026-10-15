"""Says which pydantic the interpreter that runs this script has, in one line of JSON.

The installer runs it with the interpreter that will start the validator, from the target, with no option. It prints

    {"executable": <sys.executable>, "prefix": <sys.prefix>, "pydantic": <pydantic.VERSION, or null>}

and exits 0. `pydantic` is null when the import raises ImportError; any other exception of the import ends the script
with its traceback and a non-zero exit status, which the installer reads as "cannot tell".

Standard library only. It imports and runs under a Python 3.9 interpreter.
"""
import json
import sys


def main() -> int:
    try:
        import pydantic
    except ImportError:
        version = None
    else:
        version = pydantic.VERSION
    sys.stdout.write(json.dumps({"executable": sys.executable, "prefix": sys.prefix, "pydantic": version}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
