import argparse

from src.infrastructure.persistence.init_db import init_database


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize and optionally seed database")
    parser.add_argument("--seed", action="store_true", help="Insert development seed data")
    parser.add_argument(
        "--force-seed",
        action="store_true",
        help="Delete existing sample data and reseed",
    )
    args = parser.parse_args()

    init_database(seed=args.seed, force_seed=args.force_seed)
    print("Database bootstrap completed.")


if __name__ == "__main__":
    main()
