import argparse

from app.services.backup_service import create_backup


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Create a JSON backup of platform data.")
    parser.add_argument("--quiet", action="store_true", help="Only print errors.")
    args = parser.parse_args(argv)

    result = create_backup()
    if not args.quiet:
        print(f"Backup created: {result['path']}")


if __name__ == "__main__":
    main()
