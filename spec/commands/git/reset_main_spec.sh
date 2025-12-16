# shellcheck shell=bash
# shellcheck disable=SC2329  # Functions invoked indirectly by shellspec
# spec/commands/git/reset_main_spec.sh - Tests for reset-main command scripts

# Include helper files
Include "spec/support/cleanup_tracker.sh"
Include "spec/support/script_extractor.sh"
Include "spec/support/git_test_env.sh"

# Source file containing the scripts under test
COMMAND_FILE="${PWD}/claude-code/commands/git/reset-main.md"

Describe "reset-main command scripts"
  # Clean orphaned artifacts from previous failed runs (once at start)
  setup() {
    cleanup_orphaned_artifacts
  }
  BeforeAll "setup"

  # Script extraction helpers
  extract_with_remote_script() {
    extract_script "${COMMAND_FILE}" "reset-with-remote"
  }

  extract_auto_script() {
    extract_script "${COMMAND_FILE}" "reset-auto"
  }

  Describe "script extraction"
    It "extracts the with-remote script"
      When call extract_with_remote_script
      The status should be success
      The output should include "REMOTE_NAME"
      The output should include "git fetch"
      The output should include "git reset --hard"
      The output should include "unset-upstream"
    End

    It "extracts the auto-detect script"
      When call extract_auto_script
      The status should be success
      The output should include "upstream"
      The output should include "origin"
      The output should include "git fetch"
      The output should include "git reset --hard"
      The output should include "unset-upstream"
    End
  End

  Describe "auto-detect script"
    setup_env() {
      setup_full_test_env "reset-auto-$$-$RANDOM"
    }
    cleanup_env() {
      cleanup_test_context
    }
    Before "setup_env"
    After "cleanup_env"

    Describe "with origin remote only"
      setup_feature_branch() {
        create_branch "${TEST_REPO}" "feature/test" 2
        checkout_branch "${TEST_REPO}" "feature/test"
      }
      Before "setup_feature_branch"

      It "resets to origin/main"
        script=$(extract_auto_script)
        When run bash -c "cd '${TEST_REPO}' && ${script}"
        The output should include "Reset to origin/main"
        The output should include "upstream tracking removed"
        The status should be success
      End

      It "actually resets to main commit"
        script=$(extract_auto_script)
        bash -c "cd '${TEST_REPO}' && ${script}" >/dev/null
        # Should now be on same commit as origin/main
        local_sha=$(git -C "${TEST_REPO}" rev-parse HEAD)
        remote_sha=$(git -C "${TEST_REPO}" rev-parse origin/main)
        When call test "${local_sha}" = "${remote_sha}"
        The status should be success
      End
    End

    Describe "with upstream remote"
      setup_upstream() {
        # Create second bare remote as "upstream"
        local upstream_path="${_TEST_CONTEXT_DIR}/upstream.git"
        git init --bare --quiet "${upstream_path}"
        register_artifact "repo" "${upstream_path}"
        add_remote "${TEST_REPO}" "upstream" "${upstream_path}"
        push_to_remote "${TEST_REPO}" "upstream" "main"
        setup_remote_head "${TEST_REPO}" "upstream" "main"
        # Create feature branch
        create_branch "${TEST_REPO}" "feature/test" 2
        checkout_branch "${TEST_REPO}" "feature/test"
      }
      Before "setup_upstream"

      It "prefers upstream over origin"
        script=$(extract_auto_script)
        When run bash -c "cd '${TEST_REPO}' && ${script}"
        The output should include "Reset to upstream/main"
        The status should be success
      End
    End

    Describe "unsets upstream tracking"
      setup_tracked_branch() {
        create_branch "${TEST_REPO}" "feature/tracked" 1
        push_branch "${TEST_REPO}" "origin" "feature/tracked"
        setup_tracking "${TEST_REPO}" "feature/tracked" "origin"
        checkout_branch "${TEST_REPO}" "feature/tracked"
      }
      Before "setup_tracked_branch"

      It "removes upstream tracking"
        script=$(extract_auto_script)
        bash -c "cd '${TEST_REPO}' && ${script}" >/dev/null
        # Check that upstream is unset (command should fail with "no upstream configured")
        When run git -C "${TEST_REPO}" rev-parse --abbrev-ref --symbolic-full-name @{u}
        The status should be failure
        The stderr should include "no upstream configured"
      End
    End
  End

  Describe "with-remote script"
    setup_env() {
      setup_full_test_env "reset-remote-$$-$RANDOM"
    }
    cleanup_env() {
      cleanup_test_context
    }
    Before "setup_env"
    After "cleanup_env"

    Describe "with explicit remote"
      setup_feature_branch() {
        create_branch "${TEST_REPO}" "feature/explicit" 2
        checkout_branch "${TEST_REPO}" "feature/explicit"
      }
      Before "setup_feature_branch"

      It "uses specified remote"
        script=$(extract_with_remote_script)
        # Replace REMOTE_NAME placeholder with "origin"
        script="${script//REMOTE_NAME/origin}"
        When run bash -c "cd '${TEST_REPO}' && ${script}"
        The output should include "Reset to origin/main"
        The status should be success
      End
    End
  End
End
