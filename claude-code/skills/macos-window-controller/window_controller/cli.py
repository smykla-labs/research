"""Command-line interface for macOS Window Controller."""

from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer

# Skill name for artifact tracking
SKILL_NAME = "macos-window-controller"

try:
    from _shared.artifacts import (
        ArtifactError,
        save_artifact,
        validate_extension,
    )
except ImportError:
    from datetime import datetime

    class ArtifactError(Exception):  # type: ignore[no-redef]
        pass

    def get_default_artifact_path(
        _skill_name: str, description: str, ext: str
    ) -> Path:
        timestamp = datetime.now().strftime("%y%m%d%H%M%S")
        return Path.cwd() / f"{timestamp}-{description}.{ext}"

    def save_artifact(
        source_path, skill_name, description, output_path=None, allowed_extensions=None
    ):
        import shutil
        from dataclasses import dataclass as dc

        @dc
        class FallbackResult:
            primary_path: Path
            tracking_path: Path
            skill_name: str
            description: str
            timestamp: str
            def to_dict(self):
                return {"primary_path": str(self.primary_path)}

        # Validate extension if allowed_extensions is provided
        if allowed_extensions is not None:
            ext = Path(source_path).suffix.lstrip(".")
            if ext and ext not in allowed_extensions:
                raise ArtifactError(
                    f"Extension '.{ext}' not allowed. Allowed: {allowed_extensions}"
                )

        if output_path:
            resolved = Path(output_path).resolve()
            resolved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, resolved)
            return FallbackResult(resolved, resolved, skill_name, description, "")
        return FallbackResult(
            Path(source_path), Path(source_path), skill_name, description, ""
        )

    def validate_extension(path, allowed=None):
        ext = Path(path).suffix.lstrip(".")
        if not ext:
            raise ArtifactError(f"Path must have extension: {path}")
        if allowed is not None and ext not in allowed:
            raise ArtifactError(f"Extension '.{ext}' not allowed. Allowed: {list(allowed)}")
        return ext

from .actions import activate_window, take_screenshot  # noqa: E402
from .core import find_windows, get_all_windows  # noqa: E402
from .models import WindowError, WindowFilter  # noqa: E402

app = typer.Typer(
    name="window-controller",
    help="macOS Window Controller - Find, activate, and screenshot windows.",
)


# =============================================================================
# Option dataclasses for grouping related CLI options
# =============================================================================


@dataclass(frozen=True)
class WindowFilterOptions:
    """Window filter options for finding target windows."""

    title: str | None = None
    pid: int | None = None
    path_contains: str | None = None
    path_excludes: str | None = None
    args_contains: str | None = None


# =============================================================================
# Common type aliases for Typer options
# =============================================================================

AppArg = Annotated[str | None, typer.Argument(help="Application name")]
AppArgRequired = Annotated[str, typer.Argument(help="Application name")]
TitleOpt = Annotated[str | None, typer.Option("--title", "-t", help="Regex for window title")]
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
AllWindowsOpt = Annotated[bool, typer.Option("--all-windows", help="Include non-main windows")]
JsonOpt = Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")]


# =============================================================================
# Helper functions for building option objects
# =============================================================================


def _build_filter_options(
    title: str | None,
    pid: int | None,
    path_contains: str | None,
    path_excludes: str | None,
    args_contains: str | None,
) -> WindowFilterOptions:
    """Build window filter options from CLI params."""
    return WindowFilterOptions(
        title=title,
        pid=pid,
        path_contains=path_contains,
        path_excludes=path_excludes,
        args_contains=args_contains,
    )


def _build_filter(
    app_name: str | None,
    filter_opts: WindowFilterOptions,
    all_windows: bool,
) -> WindowFilter:
    """Build WindowFilter from option objects."""
    return WindowFilter(
        app_name=app_name if app_name else None,
        title_pattern=filter_opts.title,
        pid=filter_opts.pid,
        path_contains=filter_opts.path_contains,
        path_excludes=filter_opts.path_excludes,
        args_contains=filter_opts.args_contains,
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
def find_cmd(  # noqa: PLR0913
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
        filter_opts = _build_filter_options(title, pid, path_contains, path_excludes, args_contains)
        f = _build_filter(app_name, filter_opts, all_windows)
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
def activate_cmd(  # noqa: PLR0913
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
        filter_opts = _build_filter_options(title, pid, path_contains, path_excludes, args_contains)
        f = _build_filter(app_name, filter_opts, all_windows)
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
def screenshot_cmd(  # noqa: PLR0913
    app_name: AppArgRequired,
    output: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Output path (must have .png extension)"),
    ] = None,
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
        # Validate output extension if provided
        if output is not None:
            try:
                validate_extension(output, ["png"])
            except ArtifactError as e:
                msg = json.dumps({"error": str(e)}) if json_output else f"Error: {e}"
                print(msg, file=sys.stderr)
                raise typer.Exit(1) from e

        # Build filter and find window first to get description
        filter_opts = _build_filter_options(title, pid, path_contains, path_excludes, args_contains)
        f = _build_filter(app_name, filter_opts, all_windows)
        windows = find_windows(f)

        if not windows:
            msg = {"error": "No windows found matching filter"}
            print(json.dumps(msg) if json_output else "No windows found matching filter.")
            raise typer.Exit(1)

        target_window = windows[0]

        # Generate description from window info
        description = f"screenshot_{app_name}"
        if target_window.window_title:
            title_part = target_window.window_title[:20].replace(" ", "_")
            description = f"screenshot_{app_name}_{title_part}"

        # Take screenshot to temp file first
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            take_screenshot(f, str(tmp_path), not no_activate, settle_ms)

            # Save artifact with proper tracking
            result = save_artifact(
                source_path=tmp_path,
                skill_name=SKILL_NAME,
                description=description,
                output_path=output,
                allowed_extensions=["png"],
            )
        finally:
            # Clean up temp file even if an exception occurs
            tmp_path.unlink(missing_ok=True)

        if json_output:
            output_data = {
                "screenshot": str(result.primary_path),
                "tracking_copy": str(result.tracking_path),
                "window": target_window.to_dict(),
            }
            print(json.dumps(output_data, indent=2))
        else:
            print(f"Screenshot saved: {result.primary_path}")
            if result.primary_path != result.tracking_path:
                print(f"Tracking copy: {result.tracking_path}")

    except WindowError as e:
        msg = json.dumps({"error": str(e)}) if json_output else f"Error: {e}"
        print(msg, file=sys.stderr)
        raise typer.Exit(1) from e
    except ArtifactError as e:
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
