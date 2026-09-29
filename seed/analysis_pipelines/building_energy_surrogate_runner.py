"""Subprocess entry point that runs the building-energy surrogate model calculator.

SEED itself runs on a Python/NumPy stack that is incompatible with the pinned
scientific dependencies of ``calculator_179d`` (and its pickled scikit-learn
models). To keep those dependencies isolated, SEED invokes this script with the
calculator's *own* virtual environment interpreter (see the
``BUILDING_ENERGY_SURROGATE_PYTHON`` setting). Communication is JSON over
stdin/stdout:

    <calculator_python> building_energy_surrogate_runner.py  < inputs.json  > outputs.json

``inputs.json`` must be a single JSON object matching ``PropertyInfo``. On
success the script writes the flattened ``CalculatorOutputs`` dict to stdout and
exits 0. On failure it writes ``{"error": "..."}`` to stdout and exits 1.

This module only depends on ``calculator_179d`` and the standard library so it
can run under the isolated interpreter (it must NOT import Django/SEED code).
"""

import contextlib
import json
import sys


def main() -> int:
    try:
        raw = sys.stdin.read()
        inputs = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        json.dump({"error": f"Could not parse JSON input: {exc}"}, sys.stdout)
        return 1

    try:
        from calculator_179d.data_types import PropertyInfo
        from calculator_179d.main_calculator import calculate_savings
    except Exception as exc:  # noqa: BLE001
        json.dump({"error": f"calculator_179d is not importable: {exc}"}, sys.stdout)
        return 1

    try:
        property_info = PropertyInfo.from_dict(inputs)
        # calculate_savings emits stray print() output on some branches; keep
        # stdout clean for JSON by routing that chatter to stderr.
        with contextlib.redirect_stdout(sys.stderr):
            results = calculate_savings(property_info=property_info)
        payload = results.to_dict()
    except Exception as exc:  # noqa: BLE001
        json.dump({"error": str(exc)}, sys.stdout)
        return 1

    json.dump(payload, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
