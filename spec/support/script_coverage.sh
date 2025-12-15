# shellcheck shell=bash
# spec/support/script_coverage.sh - Check test coverage for bash scripts in claude-code/

# Find all markdown files with executable bash scripts in claude-code/commands
# Note: claude-code/agents/ files are excluded because their bash blocks are
# documentation examples (showing patterns), not actual executable scripts.
# Only commands have executable scripts via !`backtick` pre-exec syntax.
# Usage: list_scripts_with_bash
# Returns: List of command files containing ```bash blocks
list_scripts_with_bash() {
  local search_dirs=("claude-code/commands")

  for dir in "${search_dirs[@]}"; do
    if [[ -d "${dir}" ]]; then
      find "${dir}" -name "*.md" -type f | while read -r file; do
        # Check if file contains bash code blocks (using grep with literal backticks)
        if grep -q $'```bash' "${file}" 2>/dev/null; then
          echo "${file}"
        fi
      done
    fi
  done
}

# Convert a claude-code/ path to its corresponding spec file path
# Usage: get_spec_path "claude-code/commands/git/clean-gone.md"
# Returns: "spec/commands/git/clean_gone_spec.sh"
get_spec_path() {
  local source_path="$1"

  # Remove claude-code/ prefix
  local relative_path="${source_path#claude-code/}"

  # Change .md extension to _spec.sh and replace - with _
  local spec_name
  spec_name=$(basename "${relative_path}" .md | tr '-' '_')
  local spec_dir
  spec_dir=$(dirname "${relative_path}")

  echo "spec/${spec_dir}/${spec_name}_spec.sh"
}

# Check if a script file has corresponding tests
# Usage: has_tests "claude-code/commands/git/clean-gone.md"
# Returns: 0 if tests exist, 1 if not
has_tests() {
  local source_path="$1"
  local spec_path
  spec_path=$(get_spec_path "${source_path}")

  [[ -f "${spec_path}" ]]
}

# List all scripts without tests
# Usage: list_untested_scripts
# Returns: List of markdown files without corresponding spec files
list_untested_scripts() {
  list_scripts_with_bash | while read -r script; do
    if ! has_tests "${script}"; then
      echo "${script}"
    fi
  done
}

# List all scripts with tests
# Usage: list_tested_scripts
# Returns: List of markdown files with corresponding spec files
list_tested_scripts() {
  list_scripts_with_bash | while read -r script; do
    if has_tests "${script}"; then
      local spec_path
      spec_path=$(get_spec_path "${script}")
      echo "${script} -> ${spec_path}"
    fi
  done
}

# Check coverage and report
# Usage: check_coverage
# Returns: 0 if all scripts have tests, 1 if some are missing
check_coverage() {
  local total=0
  local tested=0
  local untested=()

  while IFS= read -r script; do
    ((total++))
    if has_tests "${script}"; then
      ((tested++))
    else
      untested+=("${script}")
    fi
  done < <(list_scripts_with_bash)

  if [[ ${total} -eq 0 ]]; then
    echo "No bash scripts found in claude-code/"
    return 0
  fi

  echo "Script Test Coverage: ${tested}/${total}"
  echo ""

  if [[ ${#untested[@]} -gt 0 ]]; then
    echo "❌ Scripts WITHOUT tests:"
    for script in "${untested[@]}"; do
      local expected_spec
      expected_spec=$(get_spec_path "${script}")
      echo "   ${script}"
      echo "      Expected: ${expected_spec}"
    done
    echo ""
    return 1
  else
    echo "✅ All scripts have corresponding tests"
    return 0
  fi
}

# Run tests for specific script files
# Usage: run_tests_for_scripts "file1.md" "file2.md" ...
# Returns: Exit code from shellspec
run_tests_for_scripts() {
  local specs=()

  for script in "$@"; do
    if has_tests "${script}"; then
      local spec_path
      spec_path=$(get_spec_path "${script}")
      specs+=("${spec_path}")
    fi
  done

  if [[ ${#specs[@]} -eq 0 ]]; then
    echo "No tests found for specified scripts"
    return 0
  fi

  echo "Running tests: ${specs[*]}"
  shellspec "${specs[@]}"
}
