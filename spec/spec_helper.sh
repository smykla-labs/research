# shellcheck shell=bash
# spec/spec_helper.sh - Main shellspec helper
#
# Design: Minimal shared setup. Each test file manages its own context
# via cleanup_tracker.sh functions for full isolation.

set -eu

# Project root - shellspec runs from the project root where .shellspec lives
PROJECT_ROOT="${SHELLSPEC_PROJECT_ROOT:-$(pwd)}"
export PROJECT_ROOT

# Load support files
# shellcheck disable=SC1091
. "${PROJECT_ROOT}/spec/support/cleanup_tracker.sh"
# shellcheck disable=SC1091
. "${PROJECT_ROOT}/spec/support/script_extractor.sh"
# shellcheck disable=SC1091
. "${PROJECT_ROOT}/spec/support/git_test_env.sh"
