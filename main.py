"""
main.py — CLI entry point for the Query Predictor system.

Usage:
  python main.py setup       # Generate data (both DBs must be running via Docker)
  python main.py genlogs     # Generate 500K query log CSV
  python main.py train       # Train Markov order-2 models
  python main.py benchmark   # Run benchmark (3 scenarios)
  python main.py report      # Generate charts from last benchmark
  python main.py all         # Run full pipeline end-to-end
"""
import sys
import os


def cmd_setup():
    from data.generate_data import populate_site_a, populate_site_b
    from config.settings import SITE_A, SITE_B
    import psycopg2
    print("=== Populating databases ===")
    with psycopg2.connect(**SITE_A) as conn:
        populate_site_a(conn)
    with psycopg2.connect(**SITE_B) as conn:
        populate_site_b(conn)


def cmd_genlogs():
    from data.generate_query_logs import generate_logs, save_logs
    from config.settings import QUERY_LOG_SIZE, LOGS_CSV
    print(f"=== Generating {QUERY_LOG_SIZE:,} query logs ===")
    logs = generate_logs(QUERY_LOG_SIZE)
    save_logs(logs, LOGS_CSV)


def cmd_train():
    from src.ml.model_trainer import train_all
    print("=== Training Markov order-2 models ===")
    train_all()


def cmd_benchmark(n=None):
    from src.benchmark.benchmark_runner import run_all
    from config.settings import BENCHMARK_QUERIES
    print("=== Running benchmark ===")
    return run_all(n_queries=n or BENCHMARK_QUERIES)


def cmd_report(results=None):
    from src.benchmark.report_generator import generate_all
    print("=== Generating report ===")
    generate_all(results)


COMMANDS = {
    "setup": cmd_setup,
    "genlogs": cmd_genlogs,
    "train": cmd_train,
    "benchmark": cmd_benchmark,
    "report": cmd_report,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS and sys.argv[1] != "all":
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "all":
        cmd_genlogs()
        cmd_train()
        results = cmd_benchmark()
        cmd_report(results)
    else:
        COMMANDS[cmd]()


if __name__ == "__main__":
    main()
