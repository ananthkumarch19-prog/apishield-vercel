"""Usage: python -m simulator.run --output report/evidence"""
import argparse
from simulator.engine import run_scenarios, export_results, GROUPS


def main():
    parser = argparse.ArgumentParser(description="Run real HTTP security scenarios on a disposable loopback server")
    parser.add_argument("--group", choices=sorted(GROUPS), default="all")
    parser.add_argument("--output", default="report/evidence")
    args = parser.parse_args()
    result = run_scenarios(args.group)
    export_results(result, args.output)
    for row in result["results"]:
        print(f"{row['test_id']:<4} {'PASS' if row['passed'] else 'FAIL'} expected={row['expected_status']} actual={row['actual_status']} {row['scenario']}")
    print(f"{result['passed']}/{result['total']} passed. Results saved to {args.output}")
    raise SystemExit(0 if not result["failed"] else 1)


if __name__ == "__main__":
    main()
