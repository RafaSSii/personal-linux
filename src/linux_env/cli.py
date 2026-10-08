import argparse
from pathlib import Path

from .core import apply_environment, restore_environment, save_environment
from .detect import detect
from .diff import compare_manifest_to_system


def _print_diff(source: Path) -> None:
    metadata, sections = compare_manifest_to_system(source)
    system = metadata["system"]

    print(f"Comparing current system with {metadata['source']}")

    if system:
        print("\nSystem:")
        for key, values in system.items():
            print(f"  ~ {key}: {values['expected']} -> {values['actual']}")

    changed = False
    for section in sections:
        if not section.changed:
            continue
        changed = True
        print(f"\n{section.name}:")
        for item in section.added:
            print(f"  + {item}")
        for item in section.removed:
            print(f"  - {item}")
        for item in section.modified:
            print(f"  ~ {item}")

    if not changed and not system:
        print("\nEnvironment is in sync.")


def _print_commands(commands: list[list[str]]) -> None:
    for command in commands:
        print("$", " ".join(command))


def _confirm_apply() -> bool:
    answer = input(
        "Apply includes destructive changes. Continue? [y/N] "
    ).strip().lower()
    return answer in {"y", "yes"}


def main():
    parser = argparse.ArgumentParser(prog="linux-env")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("detect")

    save = sub.add_parser("save")
    save.add_argument("destination", type=Path)

    restore = sub.add_parser("restore")
    restore.add_argument("source", type=Path)
    restore.add_argument("--dry-run", action="store_true")

    diff = sub.add_parser(
        "diff",
        help="compare a saved manifest with the current system",
    )
    diff.add_argument("source", type=Path)

    apply = sub.add_parser(
        "apply",
        help="reconcile the current system with a saved manifest",
    )
    apply.add_argument("source", type=Path)
    apply.add_argument(
        "--dry-run",
        action="store_true",
        help="show planned commands without executing them",
    )
    apply.add_argument(
        "--yes",
        action="store_true",
        help="skip confirmation for destructive changes",
    )

    args = parser.parse_args()

    if args.command == "detect":
        for key, value in detect().items():
            print(f"{key}: {value}")
    elif args.command == "save":
        save_environment(args.destination)
        print(f"Environment saved to {args.destination}")
    elif args.command == "restore":
        _print_commands(restore_environment(args.source, args.dry_run))
    elif args.command == "diff":
        _print_diff(args.source)
    elif args.command == "apply":
        commands = apply_environment(
            args.source,
            dry_run=args.dry_run,
            assume_yes=args.yes,
            confirm=_confirm_apply,
        )
        _print_commands(commands)


if __name__ == "__main__":
    main()
