import argparse
from pathlib import Path
import subprocess

from .core import (
    apply_environment,
    plan_restore,
    save_environment,
)
from .detect import detect
from .diff import compare_manifest_to_system


def _print_diff(source: Path) -> None:
    metadata, sections = compare_manifest_to_system(source)
    system = metadata["system"]
    print(f"Comparing current system with {metadata['source']}")

    if system:
        print("\\nSystem:")
        for key, values in system.items():
            print(f"  ~ {key}: {values['expected']} -> {values['actual']}")

    changed = False
    for section in sections:
        if not section.changed:
            continue
        changed = True
        print(f"\\n{section.name}:")
        for item in section.added:
            print(f"  + {item}")
        for item in section.removed:
            print(f"  - {item}")
        for item in section.modified:
            print(f"  ~ {item}")

    if not changed and not system:
        print("\\nEnvironment is in sync.")


def _print_commands(commands: list[list[str]]) -> None:
    for command in commands:
        print("$", " ".join(command))


def _confirm_apply() -> bool:
    answer = input(
        "Apply includes destructive changes. Continue? [y/N] "
    ).strip().lower()
    return answer in {"y", "yes"}


def _confirm_restore() -> bool:
    answer = input(
        "Existing dotfiles will be backed up before replacement. Continue? [y/N] "
    ).strip().lower()
    return answer in {"y", "yes"}


def _print_restore_report(report: dict[str, list[str]], conflicts: list[str]) -> None:
    print("Restore summary:")
    print(f"  Packages to install: {len(report['to_install'])}")
    print(f"  Packages already installed (skipped): {len(report['already_installed'])}")
    for category, label in (
        ("skipped_boot", "Boot/kernel packages skipped"),
        ("skipped_hardware", "Hardware-specific packages skipped"),
        ("skipped_distribution", "Distribution-specific/incompatible packages skipped"),
    ):
        items = report[category]
        print(f"  {label}: {len(items)}")
        if items:
            print("    " + ", ".join(items))
    if report["already_installed"]:
        print("  Already installed: " + ", ".join(report["already_installed"]))
    if report["to_install"]:
        print("  To install: " + ", ".join(report["to_install"]))
    if conflicts:
        print("  Existing dotfiles to back up before replacement: " + ", ".join(conflicts))
        print("  Backups will be placed under ~/.local/share/linux-env/restore-backups/")


def main():
    parser = argparse.ArgumentParser(prog="linux-env")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("detect")

    save = sub.add_parser("save")
    save.add_argument("destination", type=Path)

    restore = sub.add_parser("restore")
    restore.add_argument("source", type=Path)
    restore.add_argument("--dry-run", action="store_true")
    restore.add_argument(
        "--yes",
        action="store_true",
        help="skip confirmation before replacing existing dotfiles (a backup is still made)",
    )

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
        commands, report, conflicts = plan_restore(args.source)
        _print_restore_report(report, conflicts)
        _print_commands(commands)
        if not args.dry_run:
            if conflicts and not args.yes and not _confirm_restore():
                raise SystemExit(
                    "Restore cancelled; no commands were executed."
                )
            for command in commands:
                subprocess.run(command, check=True)
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
