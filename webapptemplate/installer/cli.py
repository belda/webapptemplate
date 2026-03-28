"""
webapptemplate CLI — entry point: `webapptemplate`

Usage:
    webapptemplate init            scaffold a new project interactively
    webapptemplate init --help     show options
    webapptemplate version         print version
"""
import argparse
import sys


def cmd_init(args):
    from webapptemplate.installer.scaffold import run_wizard
    run_wizard()


def cmd_version(args):
    from webapptemplate import __version__
    print(f"webapptemplate {__version__}")


def main():
    parser = argparse.ArgumentParser(
        prog="webapptemplate",
        description="webapptemplate project scaffolding tool",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    init_parser = subparsers.add_parser("init", help="scaffold a new project")
    init_parser.set_defaults(func=cmd_init)

    version_parser = subparsers.add_parser("version", help="print version and exit")
    version_parser.set_defaults(func=cmd_version)

    args = parser.parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)


if __name__ == "__main__":
    main()
