# shellcheck shell=bash
# spec/support/script_extractor.sh - Extract bash scripts from markdown command/agent files

# Extract a specific bash script from a markdown file
# Usage: extract_script "file.md" "script_identifier"
# Identifiers: "default", "dry-run", "no-worktrees" (for clean-gone)
#              Or a unique string that appears before the code block
extract_script() {
  local markdown_file="$1"
  local identifier="$2"

  if [[ ! -f "${markdown_file}" ]]; then
    echo "ERROR: Markdown file not found: ${markdown_file}" >&2
    return 1
  fi

  # Use awk to extract the bash code block following the identifier
  # We use tolower() for case-insensitive matching since awk doesn't have //i
  awk -v id="${identifier}" '
    BEGIN { found=0; in_block=0 }

    {
      line_lower = tolower($0)
    }

    # Look for identifier in text (handles various formats)
    # Match section headers specifically to avoid matching argument-hint lines
    !found && id == "default" && line_lower ~ /\*\*default.*full cleanup/ {
      found=1
      next
    }

    # Match the section header: "With `--dry-run` flag" (skip bold markers, backticks handled by .*)
    !found && id == "dry-run" && line_lower ~ /with.*--dry-run.*flag/ {
      found=1
      next
    }

    # Match the section header: "With `--no-worktrees` flag" (skip bold markers, backticks handled by .*)
    !found && id == "no-worktrees" && line_lower ~ /with.*--no-worktrees.*flag/ {
      found=1
      next
    }

    # Worktree manager: "Readable version" section
    !found && id == "worktree-readable" && line_lower ~ /readable version.*documentation/ {
      found=1
      next
    }

    # Worktree manager: "Actual output" section (single-line script)
    !found && id == "worktree-single-line" && line_lower ~ /actual output.*single line/ {
      found=1
      next
    }

    # Generic identifier match (case-sensitive for custom identifiers)
    # Skip for known identifiers that have specific patterns above
    !found && id != "default" && id != "dry-run" && id != "no-worktrees" && id != "worktree-readable" && id != "worktree-single-line" && $0 ~ id {
      found=1
      next
    }

    # Start of bash code block after finding identifier
    found && /^[[:space:]]*```bash[[:space:]]*$/ {
      in_block=1
      next
    }

    # End of code block
    in_block && /^[[:space:]]*```[[:space:]]*$/ {
      exit
    }

    # Print content inside code block
    in_block { print }
  ' "${markdown_file}"
}

# Extract all bash scripts from a markdown file
# Returns: script_id:line_number for each script found
list_scripts_in_file() {
  local markdown_file="$1"

  if [[ ! -f "${markdown_file}" ]]; then
    echo "ERROR: Markdown file not found: ${markdown_file}" >&2
    return 1
  fi

  awk '
    BEGIN { script_num=0; in_block=0; context="" }

    # Capture context from headers and bold text
    /^##+ / { context=$0; gsub(/^##+ /, "", context) }
    /\*\*[^*]+\*\*/ {
      match($0, /\*\*[^*]+\*\*/)
      context=substr($0, RSTART+2, RLENGTH-4)
    }

    # Start of bash code block
    /^[[:space:]]*```bash[[:space:]]*$/ {
      script_num++
      in_block=1
      start_line=NR
      next
    }

    # End of code block
    in_block && /^[[:space:]]*```[[:space:]]*$/ {
      in_block=0
      print script_num ":" start_line ":" context
    }
  ' "${markdown_file}"
}

# Extract script by line number (more precise)
# Usage: extract_script_at_line "file.md" line_number
extract_script_at_line() {
  local markdown_file="$1"
  local target_line="$2"

  awk -v target="${target_line}" '
    BEGIN { in_block=0 }

    NR == target && /^[[:space:]]*```bash[[:space:]]*$/ {
      in_block=1
      next
    }

    NR > target && !in_block && /^[[:space:]]*```bash[[:space:]]*$/ {
      # We passed the target, this is wrong
      exit 1
    }

    in_block && /^[[:space:]]*```[[:space:]]*$/ {
      exit
    }

    in_block { print }
  ' "${markdown_file}"
}

# Check if a markdown file contains any bash scripts
has_bash_scripts() {
  local markdown_file="$1"

  grep -q '```bash' "${markdown_file}" 2>/dev/null
}

# Get the inner script from a 'bash -c '...'' wrapper
# The clean-gone scripts are wrapped in bash -c, we need the inner content
unwrap_bash_c() {
  local script="$1"

  # Check if it's a bash -c wrapper
  if [[ "${script}" =~ ^[[:space:]]*bash[[:space:]]+-c[[:space:]]+\' ]]; then
    # Extract content between bash -c ' and the final '
    echo "${script}" | sed "s/^[[:space:]]*bash[[:space:]]*-c[[:space:]]*'//; s/'[[:space:]]*$//"
  else
    # Not wrapped, return as-is
    echo "${script}"
  fi
}

# Validate extracted script is not empty
validate_script() {
  local script="$1"
  local source_file="$2"
  local identifier="$3"

  if [[ -z "${script}" ]] || [[ "${script}" =~ ^[[:space:]]*$ ]]; then
    echo "ERROR: Empty script extracted from ${source_file} (identifier: ${identifier})" >&2
    return 1
  fi
  return 0
}
