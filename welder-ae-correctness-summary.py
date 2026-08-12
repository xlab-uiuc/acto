"""Scan chactos workdirs for oracle violations."""

import glob
import json
import sys

from acto.result import OracleResults


def main():
    workdirs = sys.argv[1:]
    if not workdirs:
        print(
            "usage: welder-ae-correctness-summary.py <workdir> [<workdir> ...]",
            file=sys.stderr,
        )
        sys.exit(1)

    total = 0
    violations = []
    for workdir in workdirs:
        for path in glob.glob(
            f"{workdir}/**/generation-*-runtime.json", recursive=True
        ):
            total += 1
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            oracle = OracleResults.model_validate(data["oracle_result"])
            if oracle.is_error():
                violations.append(path)

    print(f"Scanned {total} fault-injection test results across {len(workdirs)} workdirs")
    if violations:
        print(f"{len(violations)} potential violation(s) found:")
        for v in violations:
            print(f"  {v}")
        sys.exit(1)
    else:
        print("No oracle violations found (matches paper's claim: 0 bugs found)")


if __name__ == "__main__":
    main()
