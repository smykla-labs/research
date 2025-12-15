"""Command-line interface for macOS Verified Screenshot."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Annotated

import typer

from .actions import capture_verified
from .core import find_target_window
from .models import (
    CaptureBackend,
    CaptureConfig,
    RetryStrategy,
    ScreenshotError,
    VerificationStrategy,
)

app = typer.Typer(
    name="verified-screenshot",
    help="Capture macOS screenshots with verification and retry logic.",
)


# =============================================================================
# Option dataclasses for grouping related CLI options
# =============================================================================


@dataclass(frozen=True)
class WindowFilterOptions:
    """Window filter options for finding target windows."""

    app_name: str | None = None
    title: str | None = None
    pid: int | None = None
    path_contains: str | None = None
    path_excludes: str | None = None
    args_contains: str | None = None


@dataclass(frozen=True)
class CaptureOptions:
    """Capture options for screenshot settings."""

    no_activate: bool = False
    settle_ms: int = 1000
    shadow: bool = False
    backend: str = "auto"


@dataclass(frozen=True)
class OutputOptions:
    """Output options for file path and format."""

    output: str | None = None
    json_output: bool = False


@dataclass(frozen=True)
class VerificationOptions:
    """Verification options for screenshot validation."""

    verify: list[str] | None = None
    expected_text: list[str] | None = None
    hash_threshold: int = 5


@dataclass(frozen=True)
class RetryOptions:
    """Retry options for capture attempts."""

    retries: int = 5
    retry_delay: int = 500
    retry_strategy: str = "fixed"


# =============================================================================
# Common type aliases for Typer options
# =============================================================================

# Window filter options
TitleOpt = Annotated[str | None, typer.Option("--title", "-t", help="Regex for window title")]
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

# Output options
OutputOpt = Annotated[str | None, typer.Option("--output", "-o", help="Output path")]
JsonOpt = Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")]

# Capture options
NoActivateOpt = Annotated[bool, typer.Option("--no-activate", help="Don't activate window first")]
SettleMsOpt = Annotated[
    int, typer.Option("--settle-ms", help="Wait time after activation (default: 1000)")
]
ShadowOpt = Annotated[bool, typer.Option("--shadow", help="Include window shadow")]
BackendOpt = Annotated[
    str,
    typer.Option("--backend", "-b", help="Capture backend: auto, quartz, screencapturekit"),
]

# Verification options
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

# Retry options
RetriesOpt = Annotated[
    int, typer.Option("--retries", "-r", help="Maximum retry attempts (default: 5)")
]
RetryDelayOpt = Annotated[
    int, typer.Option("--retry-delay", help="Delay between retries in ms (default: 500)")
]
RetryStrategyOpt = Annotated[
    str,
    typer.Option("--retry-strategy", help="Retry strategy: fixed, exponential, reactivate"),
]


# =============================================================================
# Helper functions for building option objects
# =============================================================================


def _build_capture_options(
    no_activate: bool,
    settle_ms: int,
    shadow: bool,
    backend: str,
) -> CaptureOptions:
    """Build capture options from CLI params."""
    return CaptureOptions(
        no_activate=no_activate,
        settle_ms=settle_ms,
        shadow=shadow,
        backend=backend,
    )


def _build_output_options(
    output: str | None,
    json_output: bool,
) -> OutputOptions:
    """Build output options from CLI params."""
    return OutputOptions(
        output=output,
        json_output=json_output,
    )


def _build_verification_options(
    verify: list[str] | None,
    expected_text: list[str] | None,
    hash_threshold: int,
) -> VerificationOptions:
    """Build verification options from CLI params."""
    return VerificationOptions(
        verify=verify,
        expected_text=expected_text,
        hash_threshold=hash_threshold,
    )


def _build_retry_options(
    retries: int,
    retry_delay: int,
    retry_strategy: str,
) -> RetryOptions:
    """Build retry options from CLI params."""
    return RetryOptions(
        retries=retries,
        retry_delay=retry_delay,
        retry_strategy=retry_strategy,
    )


# =============================================================================
# Parsing functions
# =============================================================================


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


def parse_backend(backend: str) -> CaptureBackend:
    """Parse backend string to enum value."""
    mapping = {
        "auto": CaptureBackend.AUTO,
        "quartz": CaptureBackend.QUARTZ,
        "screencapturekit": CaptureBackend.SCREENCAPTUREKIT,
        "sck": CaptureBackend.SCREENCAPTUREKIT,  # alias
    }
    return mapping.get(backend.lower(), CaptureBackend.AUTO)


def build_config(
    filter_opts: WindowFilterOptions,
    capture_opts: CaptureOptions,
    output_opts: OutputOptions,
    verify_opts: VerificationOptions,
    retry_opts: RetryOptions,
) -> CaptureConfig:
    """Build CaptureConfig from option objects."""
    return CaptureConfig(
        app_name=filter_opts.app_name,
        title_pattern=filter_opts.title,
        pid=filter_opts.pid,
        path_contains=filter_opts.path_contains,
        path_excludes=filter_opts.path_excludes,
        args_contains=filter_opts.args_contains,
        output_path=output_opts.output,
        activate_first=not capture_opts.no_activate,
        settle_ms=capture_opts.settle_ms,
        no_shadow=not capture_opts.shadow,
        backend=parse_backend(capture_opts.backend),
        verification_strategies=parse_verification_strategies(verify_opts.verify),
        expected_text=tuple(verify_opts.expected_text) if verify_opts.expected_text else (),
        hash_threshold=verify_opts.hash_threshold,
        max_retries=retry_opts.retries,
        retry_delay_ms=retry_opts.retry_delay,
        retry_strategy=parse_retry_strategy(retry_opts.retry_strategy),
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
def find_cmd(  # noqa: PLR0913
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
        filter_opts = WindowFilterOptions(
            app_name=app_name,
            title=title,
            pid=pid,
            path_contains=path_contains,
            path_excludes=path_excludes,
            args_contains=args_contains,
        )
        config = build_config(
            filter_opts, CaptureOptions(), OutputOptions(json_output=json_output),
            VerificationOptions(), RetryOptions()
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
def capture_cmd(  # noqa: PLR0913
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
    backend: BackendOpt = "auto",
    verify: VerifyOpt = None,
    expected_text: ExpectedTextOpt = None,
    hash_threshold: HashThresholdOpt = 5,
    retries: RetriesOpt = 5,
    retry_delay: RetryDelayOpt = 500,
    retry_strategy: RetryStrategyOpt = "fixed",
) -> None:
    """Capture screenshot of window with verification."""
    try:
        filter_opts = WindowFilterOptions(
            app_name=app_name,
            title=title,
            pid=pid,
            path_contains=path_contains,
            path_excludes=path_excludes,
            args_contains=args_contains,
        )
        capture_opts = _build_capture_options(no_activate, settle_ms, shadow, backend)
        output_opts = _build_output_options(output, json_output)
        verify_opts = _build_verification_options(verify, expected_text, hash_threshold)
        retry_opts = _build_retry_options(retries, retry_delay, retry_strategy)

        config = build_config(filter_opts, capture_opts, output_opts, verify_opts, retry_opts)
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
