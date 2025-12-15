# shellcheck shell=bash
# shellcheck disable=SC2329  # Functions invoked indirectly by shellspec
# spec/commands/git/worktree_spec.sh - Tests for worktree-manager agent scripts
#
# Design: Each test group is fully self-contained with its own isolated
# git environment. No shared state between tests.

# Include helper files
Include "spec/support/cleanup_tracker.sh"
Include "spec/support/script_extractor.sh"
Include "spec/support/git_test_env.sh"

# Source file containing the scripts under test
AGENT_FILE="${PWD}/claude-code/agents/worktree-manager.md"

Describe "worktree-manager agent scripts"
  # Clean orphaned artifacts from previous failed runs (once at start)
  setup() {
    cleanup_orphaned_artifacts
  }
  BeforeAll "setup"

  # Script extraction helpers
  extract_readable_script() {
    extract_script "${AGENT_FILE}" "worktree-readable"
  }

  extract_single_line_script() {
    extract_script "${AGENT_FILE}" "worktree-single-line"
  }

  Describe "script extraction"
    It "extracts the readable script"
      When call extract_readable_script
      The status should be success
      The output should include "set -euo pipefail"
      The output should include "not_tracked()"
      The output should include "git worktree add"
    End

    It "extracts the single-line script"
      When call extract_single_line_script
      The status should be success
      The output should include "set -euo pipefail"
      The output should include "not_tracked()"
      The output should include "PBCOPY="
    End

    It "readable script includes P variable for pbcopy control"
      When call extract_readable_script
      The output should include 'P="1"'
      The output should include '[ -n "$P" ]'
    End

    It "single-line script includes git ls-files check"
      When call extract_single_line_script
      The output should include 'git ls-files'
      The output should include 'not_tracked'
    End
  End

  Describe "not_tracked function"
    setup_env() {
      setup_full_test_env "not-tracked-$$-$RANDOM"
    }
    cleanup_env() {
      cleanup_test_context
    }
    Before "setup_env"
    After "cleanup_env"

    It "returns success for untracked files"
      # Create the not_tracked function inline for testing
      When run bash -c "
        cd '${TEST_REPO}'
        not_tracked() { [ -z \"\$(git ls-files \"\$1\" 2>/dev/null)\" ]; }
        not_tracked 'nonexistent.txt' && echo 'UNTRACKED' || echo 'TRACKED'
      "
      The output should equal "UNTRACKED"
      The status should be success
    End

    It "returns failure for tracked files"
      When run bash -c "
        cd '${TEST_REPO}'
        not_tracked() { [ -z \"\$(git ls-files \"\$1\" 2>/dev/null)\" ]; }
        not_tracked 'README.md' && echo 'UNTRACKED' || echo 'TRACKED'
      "
      The output should equal "TRACKED"
      The status should be success
    End

    It "returns success for gitignored files"
      # Create a .gitignore and an ignored file
      bash -c "
        cd '${TEST_REPO}'
        echo 'ignored.txt' > .gitignore
        echo 'content' > ignored.txt
        git add .gitignore
        git commit -m 'Add gitignore'
      " >/dev/null 2>&1
      When run bash -c "
        cd '${TEST_REPO}'
        not_tracked() { [ -z \"\$(git ls-files \"\$1\" 2>/dev/null)\" ]; }
        not_tracked 'ignored.txt' && echo 'UNTRACKED' || echo 'TRACKED'
      "
      The output should equal "UNTRACKED"
      The status should be success
    End
  End

  Describe "pbcopy control (P variable)"
    It "P='1' enables pbcopy (default)"
      When run bash -c "
        P='1'
        W='/tmp/test'
        [ -n \"\$P\" ] && echo 'PBCOPY_ENABLED' || echo 'PBCOPY_DISABLED'
      "
      The output should equal "PBCOPY_ENABLED"
    End

    It "P='' disables pbcopy (--no-pbcopy)"
      When run bash -c "
        P=''
        W='/tmp/test'
        [ -n \"\$P\" ] && echo 'PBCOPY_ENABLED' || echo 'PBCOPY_DISABLED'
      "
      The output should equal "PBCOPY_DISABLED"
    End
  End

  Describe "symlink creation logic"
    setup_env() {
      setup_full_test_env "symlink-$$-$RANDOM"
    }
    cleanup_env() {
      cleanup_test_context
    }
    Before "setup_env"
    After "cleanup_env"

    Describe "with untracked context files"
      setup_untracked_files() {
        # Create untracked/ignored files in source repo
        bash -c "
          cd '${TEST_REPO}'
          mkdir -p .claude
          echo 'settings' > .claude/settings.json
          mkdir -p tmp
          echo 'temp' > tmp/temp.txt
          echo '.claude/' >> .gitignore
          echo 'tmp/' >> .gitignore
          git add .gitignore
          git commit -m 'Add gitignore'
        " >/dev/null 2>&1
      }
      Before "setup_untracked_files"

      It "symlinks untracked directories"
        When run bash -c "
          cd '${TEST_REPO}'
          not_tracked() { [ -z \"\$(git ls-files \"\$1\" 2>/dev/null)\" ]; }
          if [ -e .claude ] && not_tracked '.claude'; then
            echo 'SHOULD_SYMLINK:.claude'
          else
            echo 'SHOULD_NOT_SYMLINK:.claude'
          fi
        "
        The output should equal "SHOULD_SYMLINK:.claude"
      End

      It "does not symlink tracked files"
        When run bash -c "
          cd '${TEST_REPO}'
          not_tracked() { [ -z \"\$(git ls-files \"\$1\" 2>/dev/null)\" ]; }
          if [ -e README.md ] && not_tracked 'README.md'; then
            echo 'SHOULD_SYMLINK:README.md'
          else
            echo 'SHOULD_NOT_SYMLINK:README.md'
          fi
        "
        The output should equal "SHOULD_NOT_SYMLINK:README.md"
      End
    End

    Describe "with tracked CLAUDE.md"
      setup_tracked_claude() {
        # Create tracked CLAUDE.md in source repo
        bash -c "
          cd '${TEST_REPO}'
          echo '# CLAUDE.md' > CLAUDE.md
          git add CLAUDE.md
          git commit -m 'Add CLAUDE.md'
        " >/dev/null 2>&1
      }
      Before "setup_tracked_claude"

      It "does not symlink tracked CLAUDE.md"
        When run bash -c "
          cd '${TEST_REPO}'
          not_tracked() { [ -z \"\$(git ls-files \"\$1\" 2>/dev/null)\" ]; }
          if [ -e CLAUDE.md ] && not_tracked 'CLAUDE.md'; then
            echo 'SHOULD_SYMLINK:CLAUDE.md'
          else
            echo 'SHOULD_NOT_SYMLINK:CLAUDE.md'
          fi
        "
        The output should equal "SHOULD_NOT_SYMLINK:CLAUDE.md"
      End
    End

    Describe "with untracked CLAUDE.md"
      setup_untracked_claude() {
        # Create untracked CLAUDE.md in source repo
        bash -c "
          cd '${TEST_REPO}'
          echo '# CLAUDE.md' > CLAUDE.md
          echo 'CLAUDE.md' >> .gitignore
          git add .gitignore
          git commit -m 'Ignore CLAUDE.md'
        " >/dev/null 2>&1
      }
      Before "setup_untracked_claude"

      It "symlinks untracked CLAUDE.md"
        When run bash -c "
          cd '${TEST_REPO}'
          not_tracked() { [ -z \"\$(git ls-files \"\$1\" 2>/dev/null)\" ]; }
          if [ -e CLAUDE.md ] && not_tracked 'CLAUDE.md'; then
            echo 'SHOULD_SYMLINK:CLAUDE.md'
          else
            echo 'SHOULD_NOT_SYMLINK:CLAUDE.md'
          fi
        "
        The output should equal "SHOULD_SYMLINK:CLAUDE.md"
      End
    End
  End

  Describe "git excludes configuration"
    setup_env() {
      setup_full_test_env "excludes-$$-$RANDOM"
    }
    cleanup_env() {
      cleanup_test_context
    }
    Before "setup_env"
    After "cleanup_env"

    It "script configures worktreeConfig extension"
      script=$(extract_readable_script)
      The value "${script}" should include "extensions.worktreeConfig true"
    End

    It "script writes symlinked items to excludes file"
      script=$(extract_readable_script)
      The value "${script}" should include 'for i in $X; do echo "$i"; done > "$E"'
    End

    It "script configures core.excludesFile"
      script=$(extract_readable_script)
      The value "${script}" should include "core.excludesFile"
    End
  End

  Describe "script output format"
    It "outputs BRANCH variable"
      script=$(extract_readable_script)
      The value "${script}" should include 'echo "BRANCH=$B"'
    End

    It "outputs PATH variable"
      script=$(extract_readable_script)
      The value "${script}" should include 'echo "PATH=$W"'
    End

    It "outputs TRACKING variable"
      script=$(extract_readable_script)
      The value "${script}" should include 'echo "TRACKING=$R/$D"'
    End

    It "outputs SYMLINKED variable"
      script=$(extract_readable_script)
      The value "${script}" should include 'echo "SYMLINKED=$X"'
    End

    It "outputs PBCOPY variable"
      script=$(extract_readable_script)
      The value "${script}" should include 'echo "PBCOPY=$P"'
    End
  End

  Describe "clipboard command"
    It "includes mise trust in clipboard command"
      script=$(extract_readable_script)
      The value "${script}" should include "mise trust"
    End

    It "includes direnv allow in clipboard command"
      script=$(extract_readable_script)
      The value "${script}" should include "direnv allow"
    End
  End

  Describe "script syntax validation"
    It "readable script has valid bash syntax"
      script=$(extract_readable_script)
      When run bash -n -c "${script}"
      The status should be success
    End

    It "single-line script has valid bash syntax"
      script=$(extract_single_line_script)
      When run bash -n -c "${script}"
      The status should be success
    End
  End
End
