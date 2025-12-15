"""Command-line interface for macOS Verified Screenshot."""

from __future__ import annotations

import json
import sys
from typing import Annotated

import typer

from .actions import capture_verified
from .core import find_target_window
from .models import (
    CaptureConfig,
    RetryStrategy,
    ScreenshotError,
    VerificationStrategy,
)

app = typer.Typer(
    name="verified-screenshot",
    help="Capture macOS screenshots with verification and retry logic.",
)

# Common type aliases for options
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
    str | None, typer.Option("--args", "--args-contains", help="Command line contains STR")
]
OutputOpt = Annotated[str | None, typer.Option("--output", "-o", help="Output path")]
JsonOpt = Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")]
NoActivateOpt = Annotated[
    bool, typer.Option("--no-activate", help="Don't activate window first")
]
SettleMsOpt = Annotated[
    int, typer.Option("--settle-ms", help="Wait time after activation (default: 1000)")
]
ShadowOpt = Annotated[bool, typer.Option("--shadow", help="Include window shadow")]
VerifyOpt = Annotated[
    list[str] | None,
    typer.Option(
        "--verify",
        "-v",
        help="Verification strategies: basic, dimensions, content, text, all, none",
    ),
]
ExpectedTextOpt = Annotated[
    list[str] | None, typer.Option("--expected-text", help="Text to verify via OCR")
]
HashThresholdOpt = Annotated[
    int, typer.Option("--hash-threshold", help="Hamming distance threshold (default: 5)")
]
RetriesOpt = Annotated[
    int, typer.Option("--retries", "-r", help="Maximum retry attempts (default: 5)")
]
RetryDelayOpt = Annotated[
    int, typer.Option("--retry-delay", help="Delay between retries in ms (default: 500)")
]
RetryStrategyOpt = Annotated[
    str,
    typer.Option(
        "--retry-strategy", help="Retry strategy: fixed, exponential, reactivate"
    ),
]


def parse_verification_strategies(
    strategies: list[str] | None,
) -> tuple[VerificationStrategy, ...]:
    """Parse verification strategy strings to enum values."""
    if strategies is None:
        strategies = ["basic", "content"]

    if "none" in strategies:
        return ()
    if "all" in strategies:
        return (VerificationStrategy.ALL,)

    mapping = {
        "basic": VerificationStrategy.BASIC,
        "dimensions": VerificationStrategy.DIMENSIONS,
        "content": VerificationStrategy.CONTENT,
        "text": VerificationStrategy.TEXT,
    }
    return tuple(mapping[s] for s in strategies if s in mapping)


def parse_retry_strategy(strategy: str) -> RetryStrategy:
    """Parse retry strategy string to enum value."""
    mapping = {
        "fixed": RetryStrategy.FIXED,
        "exponential": RetryStrategy.EXPONENTIAL,
        "reactivate": RetryStrategy.REACTIVATE,
    }
    return mapping.get(strategy, RetryStrategy.FIXED)


def build_config(
    app_name: str,
    *,
    title: str | None = None,
    pid: int | None = None,
    path_contains: str | None = None,
    path_excludes: str | None = None,
    args_contains: str | None = None,
    output: str | None = None,
    no_activate: bool = False,
    settle_ms: int = 1000,
    shadow: bool = False,
    verify: list[str] | None = None,
    expected_text: list[str] | None = None,
    hash_threshold: int = 5,
    retries: int = 5,
    retry_delay: int = 500,
    retry_strategy: str = "fixed",
) -> CaptureConfig:
    """Build CaptureConfig from parameters."""
    return CaptureConfig(
        app_name=app_name,
        title_pattern=title,
        pid=pid,
        path_contains=path_contains,
        path_excludes=path_excludes,
        args_contains=args_contains,
        output_path=output,
        activate_first=not no_activate,
        settle_ms=settle_ms,
        no_shadow=not shadow,
        verification_strategies=parse_verification_strategies(verify),
        expected_text=tuple(expected_text) if expected_text else (),
        hash_threshold=hash_threshold,
        max_retries=retries,
        retry_delay_ms=retry_delay,
        retry_strategy=parse_retry_strategy(retry_strategy),
    )


def _handle_find(config: CaptureConfig, *, json_output: bool = False) -> int:
    """Handle find action."""
    target = find_target_window(config)

    if json_output:
        print(json.dumps(target.to_dict(), indent=2))
    else:
        print(f"Found: {target.app_name}")
        print(f"  Title: {target.window_title}")
        print(f"  Window ID: {target.window_id}")
        print(f"  PID: {target.pid}")
        if target.exe_path:
            print(f"  Path: {target.exe_path}")
        if target.cmdline:
            print(f"  Args: {' '.join(target.cmdline[:3])}...")
        print(f"  Space: {target.space_index or 'unknown'}")
        print(f"  Bounds: {int(target.bounds_width)}x{int(target.bounds_height)}")

    return 0


def _handle_capture(config: CaptureConfig, *, json_output: bool = False) -> int:
    """Handle capture action."""
    result = capture_verified(config)

    if json_output:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        status = "verified" if result.verified else "unverified"
        print(f"Screenshot saved: {result.path} ({status})")
        print(f"  Window: {result.app_name} - {result.window_title}")
        print(f"  Attempt: {result.attempt}/{config.max_retries}")
        print(f"  Dimensions: {result.actual_width}x{result.actual_height}")

        if result.verifications:
            print("  Verifications:")
            for v in result.verifications:
                icon = "✓" if v.passed else "✗"
                print(f"    {icon} {v.strategy.value}: {v.message}")

    return 0 if result.verified else 1


@app.command("find")
def find_cmd(
    app_name: Annotated[str, typer.Argument(help="Application name")],
    title: TitleOpt = None,
    pid: PidOpt = None,
    path_contains: PathContainsOpt = None,
    path_excludes: PathExcludesOpt = None,
    args_contains: ArgsContainsOpt = None,
    json_output: JsonOpt = False,
) -> None:
    """Find window without capturing."""
    try:
        config = build_config(
            app_name,
            title=title,
            pid=pid,
            path_contains=path_contains,
            path_excludes=path_excludes,
            args_contains=args_contains,
        )
        result = _handle_find(config, json_output=json_output)
        if result != 0:
            raise typer.Exit(result)

    except ScreenshotError as e:
        if json_output:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e


@app.command("capture")
def capture_cmd(
    app_name: Annotated[str, typer.Argument(help="Application name")],
    title: TitleOpt = None,
    pid: PidOpt = None,
    path_contains: PathContainsOpt = None,
    path_excludes: PathExcludesOpt = None,
    args_contains: ArgsContainsOpt = None,
    output: OutputOpt = None,
    json_output: JsonOpt = False,
    no_activate: NoActivateOpt = False,
    settle_ms: SettleMsOpt = 1000,
    shadow: ShadowOpt = False,
    verify: VerifyOpt = None,
    expected_text: ExpectedTextOpt = None,
    hash_threshold: HashThresholdOpt = 5,
    retries: RetriesOpt = 5,
    retry_delay: RetryDelayOpt = 500,
    retry_strategy: RetryStrategyOpt = "fixed",
) -> None:
    """Capture screenshot of window with verification."""
    try:
        config = build_config(
            app_name,
            title=title,
            pid=pid,
            path_contains=path_contains,
            path_excludes=path_excludes,
            args_contains=args_contains,
            output=output,
            no_activate=no_activate,
            settle_ms=settle_ms,
            shadow=shadow,
            verify=verify,
            expected_text=expected_text,
            hash_threshold=hash_threshold,
            retries=retries,
            retry_delay=retry_delay,
            retry_strategy=retry_strategy,
        )
        result = _handle_capture(config, json_output=json_output)
        if result != 0:
            raise typer.Exit(result)

    except ScreenshotError as e:
        if json_output:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1) from e


def main(argv: list[str] | None = None) -> int:
    """Main entry point for verified-screenshot CLI.

    Args:
        argv: Command-line arguments (default: sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    if argv is not None:
        sys.argv = ["verified-screenshot", *list(argv)]
    try:
        app(prog_name="verified-screenshot")
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1


if __name__ == "__main__":
    sys.exit(main())
