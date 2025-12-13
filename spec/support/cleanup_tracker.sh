# shellcheck shell=bash
# spec/support/cleanup_tracker.sh - Per-test artifact tracking and cleanup
#
# Design: Each test group creates its own isolated context with unique
# artifact directory and manifest. No shared state between tests.

# Create a new isolated test context
# Usage: create_test_context "test-name"
# Sets: _TEST_CONTEXT_DIR, _TEST_CONTEXT_MANIFEST
# Returns: context directory path
create_test_context() {
  local name="${1:-test-$$-$RANDOM}"
  local base_dir="${PROJECT_ROOT:-$(pwd)}/tmp/shellspec-artifacts"
  local context_dir="${base_dir}/${name}"

  mkdir -p "${context_dir}"

  # Export context-local variables
  _TEST_CONTEXT_DIR="${context_dir}"
  _TEST_CONTEXT_MANIFEST="${context_dir}/.manifest"
  export _TEST_CONTEXT_DIR _TEST_CONTEXT_MANIFEST

  # Initialize empty manifest
  : > "${_TEST_CONTEXT_MANIFEST}"

  echo "${context_dir}"
}

# Register an artifact in the current test context
# Usage: register_artifact "type" "path"
# Types: repo, worktree, branch, file, dir
register_artifact() {
  local artifact_type="$1"
  local artifact_path="$2"

  if [[ -z "${_TEST_CONTEXT_MANIFEST:-}" ]]; then
    echo "ERROR: register_artifact called without test context" >&2
    return 1
  fi

  echo "${artifact_type}:${artifact_path}" >> "${_TEST_CONTEXT_MANIFEST}"
}

# Clean all artifacts in the current test context
# Usage: cleanup_test_context
cleanup_test_context() {
  if [[ -z "${_TEST_CONTEXT_DIR:-}" ]] || [[ -z "${_TEST_CONTEXT_MANIFEST:-}" ]]; then
    return 0
  fi

  if [[ ! -f "${_TEST_CONTEXT_MANIFEST}" ]]; then
    # No manifest, just remove the context directory
    [[ -d "${_TEST_CONTEXT_DIR}" ]] && rm -rf "${_TEST_CONTEXT_DIR}"
    unset _TEST_CONTEXT_DIR _TEST_CONTEXT_MANIFEST
    return 0
  fi

  # Process in reverse order (worktrees before repos)
  local artifacts
  artifacts=$(tac "${_TEST_CONTEXT_MANIFEST}" 2>/dev/null || tail -r "${_TEST_CONTEXT_MANIFEST}" 2>/dev/null || cat "${_TEST_CONTEXT_MANIFEST}")

  while IFS=: read -r artifact_type artifact_path; do
    [[ -z "${artifact_path}" ]] && continue

    case "${artifact_type}" in
      worktree)
        if [[ -d "${artifact_path}" ]]; then
          # Find the main repo by looking for .git common dir
          local main_repo
          main_repo=$(git -C "${artifact_path}" rev-parse --show-toplevel 2>/dev/null || true)

          # The main repo is the one that isn't the worktree itself
          if [[ -n "${main_repo}" ]] && [[ "${main_repo}" != "${artifact_path}" ]]; then
            git -C "${main_repo}" worktree remove --force "${artifact_path}" 2>/dev/null || true
          fi

          # Force remove directory if git cleanup failed
          [[ -d "${artifact_path}" ]] && rm -rf "${artifact_path}"
        fi
        ;;
      repo|dir)
        # Remove any lingering git locks before cleanup
        [[ -f "${artifact_path}/.git/index.lock" ]] && rm -f "${artifact_path}/.git/index.lock"
        [[ -d "${artifact_path}" ]] && rm -rf "${artifact_path}"
        ;;
      file)
        [[ -f "${artifact_path}" ]] && rm -f "${artifact_path}"
        ;;
      *)
        [[ -e "${artifact_path}" ]] && rm -rf "${artifact_path}"
        ;;
    esac
  done <<< "${artifacts}"

  # Remove the context directory itself
  rm -rf "${_TEST_CONTEXT_DIR}"

  # Clear context variables
  unset _TEST_CONTEXT_DIR _TEST_CONTEXT_MANIFEST
}

# Verify cleanup was successful (for debugging)
# Usage: verify_cleanup
verify_cleanup() {
  if [[ -z "${_TEST_CONTEXT_DIR:-}" ]]; then
    return 0
  fi

  if [[ -d "${_TEST_CONTEXT_DIR}" ]]; then
    echo "❌ CLEANUP FAILED: Context directory still exists: ${_TEST_CONTEXT_DIR}" >&2
    return 1
  fi
  return 0
}

# Clean any orphaned test artifacts (call once at start of test run)
# Usage: cleanup_orphaned_artifacts
cleanup_orphaned_artifacts() {
  local base_dir="${PROJECT_ROOT:-$(pwd)}/tmp/shellspec-artifacts"

  if [[ -d "${base_dir}" ]]; then
    local orphans
    orphans=$(find "${base_dir}" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | head -5)
    if [[ -n "${orphans}" ]]; then
      echo "⚠️  Cleaning orphaned test artifacts from previous run..." >&2
      rm -rf "${base_dir}"
    fi
  fi
}