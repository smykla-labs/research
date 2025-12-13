# shellcheck shell=bash
# shellcheck disable=SC2329  # Functions invoked indirectly by shellspec
# spec/commands/git/clean_gone_spec.sh - Tests for clean-gone command scripts
#
# Design: Each test group is fully self-contained with its own isolated
# git environment. No shared state between tests.

# Include helper files
Include "spec/support/cleanup_tracker.sh"
Include "spec/support/script_extractor.sh"
Include "spec/support/git_test_env.sh"

# Source file containing the scripts under test
COMMAND_FILE="${PWD}/.claude/commands/git/clean-gone.md"

Describe "clean-gone command scripts"
  # Clean orphaned artifacts from previous failed runs (once at start)
  setup() {
    cleanup_orphaned_artifacts
  }
  BeforeAll "setup"

  # Script extraction helpers
  extract_default_script() {
    extract_script "${COMMAND_FILE}" "default"
  }

  extract_dryrun_script() {
    extract_script "${COMMAND_FILE}" "dry-run"
  }

  extract_noworktrees_script() {
    extract_script "${COMMAND_FILE}" "no-worktrees"
  }

  Describe "script extraction"
    It "extracts the default script"
      When call extract_default_script
      The status should be success
      The output should include "git fetch --prune"
      The output should include "git cherry"
    End

    It "extracts the dry-run script"
      When call extract_dryrun_script
      The status should be success
      The output should include "WOULD_DELETE"
      The output should include "WOULD_SKIP"
    End

    It "extracts the no-worktrees script"
      When call extract_noworktrees_script
      The status should be success
      The output should include '\[gone\]'
      The output should not include "git cherry"
    End
  End

  Describe "default script (full cleanup)"
    # Each test gets its own isolated environment
    setup_env() {
      setup_full_test_env "default-$$-$RANDOM"
    }
    cleanup_env() {
      cleanup_test_context
    }
    Before "setup_env"
    After "cleanup_env"

    Describe "with gone branches"
      setup_gone_branch() {
        create_branch "${TEST_REPO}" "feature/gone-branch" 2
        push_branch "${TEST_REPO}" "origin" "feature/gone-branch"
        setup_tracking "${TEST_REPO}" "feature/gone-branch" "origin"
        delete_branch_from_bare "${TEST_REMOTE}" "feature/gone-branch"
        fetch_prune "${TEST_REPO}" "origin"
      }
      Before "setup_gone_branch"

      It "deletes gone branches"
        script=$(extract_default_script)
        When run bash -c "cd '${TEST_REPO}' && ${script}"
        The output should include "DELETED:feature/gone-branch:gone"
        The status should be success
      End

      It "actually removes the branch"
        script=$(extract_default_script)
        bash -c "cd '${TEST_REPO}' && ${script}" >/dev/null
        When call branch_exists "${TEST_REPO}" "feature/gone-branch"
        The status should be failure
      End
    End

    Describe "with squash-merged branches"
      setup_merged_branch() {
        create_branch "${TEST_REPO}" "feature/squash-me" 3
        push_branch "${TEST_REPO}" "origin" "feature/squash-me"
        setup_tracking "${TEST_REPO}" "feature/squash-me" "origin"
        simulate_squash_merge "${TEST_REPO}" "feature/squash-me"
        push_to_remote "${TEST_REPO}" "origin" "main"
      }
      Before "setup_merged_branch"

      It "keeps squash-merged branches (git cherry limitation)"
        script=$(extract_default_script)
        When run bash -c "cd '${TEST_REPO}' && ${script}"
        The output should include "KEPT:feature/squash-me:"
        The output should include "unmerged"
        The status should be success
      End
    End

    Describe "with worktrees"
      setup_branch_with_worktree() {
        create_branch "${TEST_REPO}" "feature/with-wt" 1
        push_branch "${TEST_REPO}" "origin" "feature/with-wt"
        setup_tracking "${TEST_REPO}" "feature/with-wt" "origin"
        create_worktree "${TEST_REPO}" "feature/with-wt" "feature-with-wt"
        delete_branch_from_bare "${TEST_REMOTE}" "feature/with-wt"
        fetch_prune "${TEST_REPO}" "origin"
      }
      Before "setup_branch_with_worktree"

      It "removes worktree before deleting branch"
        script=$(extract_default_script)
        When run bash -c "cd '${TEST_REPO}' && ${script}"
        The output should include "REMOVED_WT:feature-with-wt:feature/with-wt"
        The output should include "DELETED:feature/with-wt:gone"
        The status should be success
      End

      It "actually removes the worktree"
        script=$(extract_default_script)
        bash -c "cd '${TEST_REPO}' && ${script}" >/dev/null
        worktree_path="${_TEST_CONTEXT_DIR}/feature-with-wt"
        When call test -d "${worktree_path}"
        The status should be failure
      End
    End

    Describe "with current branch protection"
      setup_current_as_gone() {
        create_branch "${TEST_REPO}" "feature/current" 1
        push_branch "${TEST_REPO}" "origin" "feature/current"
        setup_tracking "${TEST_REPO}" "feature/current" "origin"
        checkout_branch "${TEST_REPO}" "feature/current"
        delete_branch_from_bare "${TEST_REMOTE}" "feature/current"
        fetch_prune "${TEST_REPO}" "origin"
      }
      Before "setup_current_as_gone"

      It "skips the current branch even if gone"
        script=$(extract_default_script)
        When run bash -c "cd '${TEST_REPO}' && ${script}"
        The output should include "SKIPPED:feature/current:current branch"
        The status should be success
      End

      It "does not delete the current branch"
        script=$(extract_default_script)
        bash -c "cd '${TEST_REPO}' && ${script}" >/dev/null
        When call branch_exists "${TEST_REPO}" "feature/current"
        The status should be success
      End
    End

    Describe "with unmerged branches"
      setup_unmerged_branch() {
        create_branch "${TEST_REPO}" "feature/unmerged" 5
        push_branch "${TEST_REPO}" "origin" "feature/unmerged"
        setup_tracking "${TEST_REPO}" "feature/unmerged" "origin"
      }
      Before "setup_unmerged_branch"

      It "keeps unmerged branches and reports count"
        script=$(extract_default_script)
        When run bash -c "cd '${TEST_REPO}' && ${script}"
        The output should include "KEPT:feature/unmerged:"
        The output should include "unmerged"
        The status should be success
      End
    End

    Describe "with mixed states"
      setup_mixed() {
        create_branch "${TEST_REPO}" "feature/gone" 1
        push_branch "${TEST_REPO}" "origin" "feature/gone"
        setup_tracking "${TEST_REPO}" "feature/gone" "origin"
        delete_branch_from_bare "${TEST_REMOTE}" "feature/gone"

        create_branch "${TEST_REPO}" "feature/merged" 2
        push_branch "${TEST_REPO}" "origin" "feature/merged"
        setup_tracking "${TEST_REPO}" "feature/merged" "origin"
        simulate_squash_merge "${TEST_REPO}" "feature/merged"
        push_to_remote "${TEST_REPO}" "origin" "main"

        create_branch "${TEST_REPO}" "feature/wip" 3
        push_branch "${TEST_REPO}" "origin" "feature/wip"
        setup_tracking "${TEST_REPO}" "feature/wip" "origin"

        fetch_prune "${TEST_REPO}" "origin"
      }
      Before "setup_mixed"

      It "handles all branch states correctly"
        script=$(extract_default_script)
        When run bash -c "cd '${TEST_REPO}' && ${script}"
        The output should include "DELETED:feature/gone:gone"
        The output should include "KEPT:feature/merged:"
        The output should include "KEPT:feature/wip:"
        The status should be success
      End
    End

    Describe "empty state (no branches to clean)"
      It "produces no output for clean repos"
        script=$(extract_default_script)
        When run bash -c "cd '${TEST_REPO}' && ${script}"
        The output should equal ""
        The status should be success
      End
    End

    Describe "main branch protection"
      It "never outputs anything about main branch"
        script=$(extract_default_script)
        When run bash -c "cd '${TEST_REPO}' && ${script}"
        The output should not include ":main:"
        The output should not include "main:gone"
        The output should not include "main:merged"
        The status should be success
      End
    End
  End

  Describe "dry-run script (preview only)"
    setup_env() {
      setup_full_test_env "dryrun-$$-$RANDOM"
    }
    cleanup_env() {
      cleanup_test_context
    }
    Before "setup_env"
    After "cleanup_env"

    Describe "with gone branches"
      setup_gone_branch() {
        create_branch "${TEST_REPO}" "feature/preview-gone" 2
        push_branch "${TEST_REPO}" "origin" "feature/preview-gone"
        setup_tracking "${TEST_REPO}" "feature/preview-gone" "origin"
        delete_branch_from_bare "${TEST_REMOTE}" "feature/preview-gone"
        fetch_prune "${TEST_REPO}" "origin"
      }
      Before "setup_gone_branch"

      It "outputs WOULD_DELETE instead of DELETED"
        script=$(extract_dryrun_script)
        When run bash -c "cd '${TEST_REPO}' && ${script}"
        The output should include "WOULD_DELETE:feature/preview-gone:gone"
        The output should not include "DELETED:"
        The status should be success
      End

      It "does NOT actually delete the branch"
        script=$(extract_dryrun_script)
        bash -c "cd '${TEST_REPO}' && ${script}" >/dev/null
        When call branch_exists "${TEST_REPO}" "feature/preview-gone"
        The status should be success
      End
    End

    Describe "with worktrees"
      setup_wt() {
        create_branch "${TEST_REPO}" "feature/preview-wt" 1
        push_branch "${TEST_REPO}" "origin" "feature/preview-wt"
        setup_tracking "${TEST_REPO}" "feature/preview-wt" "origin"
        create_worktree "${TEST_REPO}" "feature/preview-wt" "preview-wt"
        delete_branch_from_bare "${TEST_REMOTE}" "feature/preview-wt"
        fetch_prune "${TEST_REPO}" "origin"
      }
      Before "setup_wt"

      It "outputs WOULD_REMOVE_WT"
        script=$(extract_dryrun_script)
        When run bash -c "cd '${TEST_REPO}' && ${script}"
        The output should include "WOULD_REMOVE_WT:preview-wt:feature/preview-wt"
        The output should include "WOULD_DELETE:feature/preview-wt:gone"
        The status should be success
      End

      It "does NOT actually remove the worktree"
        script=$(extract_dryrun_script)
        bash -c "cd '${TEST_REPO}' && ${script}" >/dev/null
        worktree_path="${_TEST_CONTEXT_DIR}/preview-wt"
        When call test -d "${worktree_path}"
        The status should be success
      End
    End

    Describe "current branch handling"
      setup_current() {
        create_branch "${TEST_REPO}" "feature/dry-current" 1
        push_branch "${TEST_REPO}" "origin" "feature/dry-current"
        setup_tracking "${TEST_REPO}" "feature/dry-current" "origin"
        checkout_branch "${TEST_REPO}" "feature/dry-current"
        delete_branch_from_bare "${TEST_REMOTE}" "feature/dry-current"
        fetch_prune "${TEST_REPO}" "origin"
      }
      Before "setup_current"

      It "outputs WOULD_SKIP for current branch"
        script=$(extract_dryrun_script)
        When run bash -c "cd '${TEST_REPO}' && ${script}"
        The output should include "WOULD_SKIP:feature/dry-current:current branch"
        The status should be success
      End
    End

    Describe "unmerged branches"
      setup_unmerged() {
        create_branch "${TEST_REPO}" "feature/dry-wip" 5
        push_branch "${TEST_REPO}" "origin" "feature/dry-wip"
        setup_tracking "${TEST_REPO}" "feature/dry-wip" "origin"
      }
      Before "setup_unmerged"

      It "outputs WOULD_KEEP for unmerged branches"
        script=$(extract_dryrun_script)
        When run bash -c "cd '${TEST_REPO}' && ${script}"
        The output should include "WOULD_KEEP:feature/dry-wip:"
        The output should include "unmerged"
        The status should be success
      End
    End
  End

  Describe "no-worktrees script (gone branches only)"
    setup_env() {
      setup_full_test_env "nowt-$$-$RANDOM"
    }
    cleanup_env() {
      cleanup_test_context
    }
    Before "setup_env"
    After "cleanup_env"

    Describe "with gone branches"
      setup_gone() {
        create_branch "${TEST_REPO}" "feature/nowt-gone" 2
        push_branch "${TEST_REPO}" "origin" "feature/nowt-gone"
        setup_tracking "${TEST_REPO}" "feature/nowt-gone" "origin"
        delete_branch_from_bare "${TEST_REMOTE}" "feature/nowt-gone"
        fetch_prune "${TEST_REPO}" "origin"
      }
      Before "setup_gone"

      It "deletes gone branches"
        script=$(extract_noworktrees_script)
        When run bash -c "cd '${TEST_REPO}' && ${script}"
        The output should include "DELETED:feature/nowt-gone:gone"
        The status should be success
      End
    End

    Describe "with merged branches (NOT gone)"
      setup_merged() {
        create_branch "${TEST_REPO}" "feature/nowt-merged" 2
        push_branch "${TEST_REPO}" "origin" "feature/nowt-merged"
        setup_tracking "${TEST_REPO}" "feature/nowt-merged" "origin"
        simulate_squash_merge "${TEST_REPO}" "feature/nowt-merged"
        push_to_remote "${TEST_REPO}" "origin" "main"
      }
      Before "setup_merged"

      It "does NOT delete merged branches (only gone)"
        script=$(extract_noworktrees_script)
        When run bash -c "cd '${TEST_REPO}' && ${script}"
        The output should not include "feature/nowt-merged"
        The status should be success
      End
    End

    Describe "with worktrees on gone branches"
      setup_wt_gone() {
        create_branch "${TEST_REPO}" "feature/nowt-wt" 1
        push_branch "${TEST_REPO}" "origin" "feature/nowt-wt"
        setup_tracking "${TEST_REPO}" "feature/nowt-wt" "origin"
        create_worktree "${TEST_REPO}" "feature/nowt-wt" "nowt-wt"
        delete_branch_from_bare "${TEST_REMOTE}" "feature/nowt-wt"
        fetch_prune "${TEST_REPO}" "origin"
      }
      Before "setup_wt_gone"

      It "does NOT remove worktrees (no-worktrees mode)"
        script=$(extract_noworktrees_script)
        When run bash -c "cd '${TEST_REPO}' && ${script}"
        The output should not include "REMOVED_WT"
        The output should not include "worktree"
        # Script exits non-zero because git branch -D fails for branches with worktrees
        The status should be failure
      End

      It "cannot delete branch with active worktree"
        script=$(extract_noworktrees_script)
        bash -c "cd '${TEST_REPO}' && ${script}" 2>/dev/null || true
        When call branch_exists "${TEST_REPO}" "feature/nowt-wt"
        The status should be success
      End

      It "worktree still exists after script"
        script=$(extract_noworktrees_script)
        bash -c "cd '${TEST_REPO}' && ${script}" 2>/dev/null || true
        worktree_path="${_TEST_CONTEXT_DIR}/nowt-wt"
        When call test -d "${worktree_path}"
        The status should be success
      End
    End
  End

  Describe "remote detection"
    setup_env() {
      setup_full_test_env "remote-$$-$RANDOM"
    }
    cleanup_env() {
      cleanup_test_context
    }
    Before "setup_env"
    After "cleanup_env"

    Describe "with upstream remote instead of origin"
      setup_upstream() {
        rename_remote "${TEST_REPO}" "origin" "upstream"
        fetch_remote "${TEST_REPO}" "upstream"
        set_upstream "${TEST_REPO}" "main" "upstream/main"

        create_branch "${TEST_REPO}" "feature/upstream-gone" 1
        push_branch "${TEST_REPO}" "upstream" "feature/upstream-gone"
        setup_tracking "${TEST_REPO}" "feature/upstream-gone" "upstream"
        delete_branch_from_bare "${TEST_REMOTE}" "feature/upstream-gone"
        fetch_prune "${TEST_REPO}" "upstream"
      }
      Before "setup_upstream"

      It "detects remote from main branch tracking"
        script=$(extract_default_script)
        When run bash -c "cd '${TEST_REPO}' && ${script}"
        The output should include "DELETED:feature/upstream-gone:gone"
        The status should be success
      End
    End
  End
End