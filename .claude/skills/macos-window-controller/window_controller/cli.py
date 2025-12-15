"""Command-line interface for macOS Window Controller."""

from __future__ import annotations

import json
import sys
from typing import Annotated

import typer

from .actions import activate_window, take_screenshot
from .core import find_windows, get_all_windows
from .models import WindowError, WindowFilter

app = typer.Typer(
    name="window-controller",
    help="macOS Window Controller - Find, activate, and screenshot windows.",
)

# Common type aliases for options
AppArg = Annotated[str | None, typer.Argument(help="Application name")]
AppArgRequired = Annotated[str, typer.Argument(help="Application name")]
TitleOpt = Annotated[
    str | None, typer.Option("--title", "-t", help="Regex for window title")
]
PidOpt = Annotated[int | None, typer.Option("--pid", help="Filter by process ID")]
PathContainsOpt = Annotated[
    str | None, typer.Option("--path-contains", help="Exe path must contain STR")
]
PathExcludesOpt = Annotated[
    str | None, typer.Option("--path-excludes", help="Exe path must NOT contain STR")
]
ArgsContainsOpt = Annotated[
    str | None, typer.Option("--args-contains", help="Command line must contain STR")
]
AllWindowsOpt = Annotated[
    bool, typer.Option("--all-windows", help="Include non-main windows")
]
JsonOpt = Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")]


def _build_filter(
    app_name: str | None = None,
    title: str | None = None,
    pid: int | None = None,
    path_contains: str | None = None,
    path_excludes: str | None = None,
    args_contains: str | None = None,
    all_windows: bool = False,
) -> WindowFilter:
    """Build WindowFilter from arguments."""
    return WindowFilter(
        app_name=app_name if app_name else None,
        title_pattern=title,
        pid=pid,
        path_contains=path_contains,
        path_excludes=path_excludes,
        args_contains=args_contains,
        main_window_only=not all_windows,
    )


def _print_windows_table(windows: list, main_only: bool = True) -> None:
    """Print windows in a formatted table."""
    if main_only:
        windows = [w for w in windows if w.layer == 0 and w.window_title]

    if not windows:
        print("No windows found.")
        print("\nTip: Make sure Screen Recording permission is granted.")
        return

    print(f"{'App':<20} {'Title':<40} {'Space':<6} {'PID':<8}")
    print("-" * 80)
    for w in windows:
        space = str(w.space_index) if w.space_index else "-"
        title = w.window_title[:38] if w.window_title else "-"
        print(f"{w.app_name[:18]:<20} {title:<40} {space:<6} {w.pid:<8}")


@app.command("list")
def list_cmd(
    all_windows: AllWindowsOpt = False,
    json_output: JsonOpt = False,
) -> None:
    """List all windows."""
    try:
        windows = get_all_windows()
        if not all_windows:
            windows = [w for w in windows if w.layer == 0 and w.window_title]

        if json_output:
            print(json.dumps([w.to_dict() for w in windows], indent=2))
        else:
            _print_windows_table(windows, main_only=not all_windows)
    except WindowError as e:
        msg = json.dumps({"error": str(e)}) if json_output else f"Error: {e}"
        print(msg, file=sys.stderr)
        raise typer.Exit(1) from e


@app.command("find")
def find_cmd(
    app_name: AppArg = None,
    title: TitleOpt = None,
    pid: PidOpt = None,
    path_contains: PathContainsOpt = None,
    path_excludes: PathExcludesOpt = None,
    args_contains: ArgsContainsOpt = None,
    all_windows: AllWindowsOpt = False,
    json_output: JsonOpt = False,
) -> None:
    """Find window by app name and filters."""
    try:
        f = _build_filter(
            app_name=app_name,
            title=title,
            pid=pid,
            path_contains=path_contains,
            path_excludes=path_excludes,
            args_contains=args_contains,
            all_windows=all_windows,
        )
        windows = find_windows(f)

        if not windows:
            msg = {"error": "No windows found matching filter"}
            print(json.dumps(msg) if json_output else "No windows found matching filter.")
            raise typer.Exit(1)

        if json_output:
            data = windows[0].to_dict() if len(windows) == 1 else [w.to_dict() for w in windows]
            print(json.dumps(data, indent=2))
        else:
            for w in windows:
                print(f"Found: {w.app_name}\n  Title: {w.window_title}")
                print(f"  Window ID: {w.window_id}\n  PID: {w.pid}")
                if w.exe_path:
                    print(f"  Path: {w.exe_path}")
                if w.cmdline:
                    print(f"  Args: {' '.join(w.cmdline[:3])}...")
                print(f"  Space: {w.space_index or 'unknown'}")
                print(f"  Bounds: {int(w.bounds_width)}x{int(w.bounds_height)}\n")

    except WindowError as e:
        msg = json.dumps({"error": str(e)}) if json_output else f"Error: {e}"
        print(msg, file=sys.stderr)
        raise typer.Exit(1) from e


@app.command("activate")
def activate_cmd(
    app_name: AppArgRequired,
    title: TitleOpt = None,
    pid: PidOpt = None,
    path_contains: PathContainsOpt = None,
    path_excludes: PathExcludesOpt = None,
    args_contains: ArgsContainsOpt = None,
    all_windows: AllWindowsOpt = False,
    json_output: JsonOpt = False,
) -> None:
    """Activate window by app name."""
    try:
        f = _build_filter(
            app_name=app_name,
            title=title,
            pid=pid,
            path_contains=path_contains,
            path_excludes=path_excludes,
            args_contains=args_contains,
            all_windows=all_windows,
        )
        window = activate_window(f)

        if json_output:
            print(json.dumps({"activated": window.to_dict()}))
        else:
            print(f"Activated: {window.app_name}\n  Title: {window.window_title}")

    except WindowError as e:
        msg = json.dumps({"error": str(e)}) if json_output else f"Error: {e}"
        print(msg, file=sys.stderr)
        raise typer.Exit(1) from e


@app.command("screenshot")
def screenshot_cmd(
    app_name: AppArgRequired,
    output: Annotated[str | None, typer.Option("--output", "-o", help="Output path")] = None,
    no_activate: Annotated[
        bool, typer.Option("--no-activate", help="Don't activate first")
    ] = False,
    settle_ms: Annotated[
        int, typer.Option("--settle-ms", help="Wait time (default: 1000ms)")
    ] = 1000,
    title: TitleOpt = None,
    pid: PidOpt = None,
    path_contains: PathContainsOpt = None,
    path_excludes: PathExcludesOpt = None,
    args_contains: ArgsContainsOpt = None,
    all_windows: AllWindowsOpt = False,
    json_output: JsonOpt = False,
) -> None:
    """Take screenshot of window."""
    try:
        f = _build_filter(
            app_name=app_name,
            title=title,
            pid=pid,
            path_contains=path_contains,
            path_excludes=path_excludes,
            args_contains=args_contains,
            all_windows=all_windows,
        )
        path = take_screenshot(f, output, not no_activate, settle_ms)

        if json_output:
            print(json.dumps({"screenshot": str(path)}))
        else:
            print(f"Screenshot saved: {path}")

    except WindowError as e:
        msg = json.dumps({"error": str(e)}) if json_output else f"Error: {e}"
        print(msg, file=sys.stderr)
        raise typer.Exit(1) from e


def main(argv: list[str] | None = None) -> int:
    """Main entry point for window-controller CLI.

    Args:
        argv: Command-line arguments (default: sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    if argv is not None:
        sys.argv = ["window-controller", *list(argv)]
    try:
        app(prog_name="window-controller")
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1


if __name__ == "__main__":
    sys.exit(main())
