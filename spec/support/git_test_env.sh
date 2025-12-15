# shellcheck shell=bash
# spec/support/git_test_env.sh - Create isolated git environments for testing
#
# Depends on: cleanup_tracker.sh (for _TEST_CONTEXT_DIR and register_artifact)
# All artifacts are created within the current test context directory.

# Create a new isolated test git repository
# Usage: create_test_repo [name]
# Returns: path to the repo (also sets TEST_REPO variable)
create_test_repo() {
  local name="${1:-repo-$$-$RANDOM}"
  local repo_path="${_TEST_CONTEXT_DIR}/${name}"

  mkdir -p "${repo_path}"
  git -C "${repo_path}" init --quiet
  git -C "${repo_path}" config user.email "test@shellspec.local"
  git -C "${repo_path}" config user.name "Shellspec Test"
  git -C "${repo_path}" config commit.gpgsign false

  # Create initial commit so we have a valid repo
  echo "# Test Repository" > "${repo_path}/README.md"
  git -C "${repo_path}" add README.md
  git -C "${repo_path}" commit --quiet -m "Initial commit"

  # Register for cleanup
  register_artifact "repo" "${repo_path}"

  TEST_REPO="${repo_path}"
  export TEST_REPO
  echo "${repo_path}"
}

# Create a bare remote repository (for simulating origin/upstream)
# Usage: create_bare_remote [name]
create_bare_remote() {
  local name="${1:-remote-$$-$RANDOM}"
  local remote_path="${_TEST_CONTEXT_DIR}/${name}.git"

  git init --bare --quiet "${remote_path}"

  register_artifact "repo" "${remote_path}"

  TEST_REMOTE="${remote_path}"
  export TEST_REMOTE
  echo "${remote_path}"
}

# Add a remote to a test repo
# Usage: add_remote repo_path remote_name remote_url
add_remote() {
  local repo_path="$1"
  local remote_name="$2"
  local remote_url="$3"

  git -C "${repo_path}" remote add "${remote_name}" "${remote_url}"
}

# Create a branch with optional commits
# Usage: create_branch repo_path branch_name [num_commits]
create_branch() {
  local repo_path="$1"
  local branch_name="$2"
  local num_commits="${3:-0}"
  # Sanitize branch name for filename (replace / with -)
  local safe_name="${branch_name//\//-}"

  # Determine default branch BEFORE switching away from it
  local default_branch="main"
  if git -C "${repo_path}" show-ref --verify --quiet "refs/heads/master"; then
    default_branch="master"
  fi

  git -C "${repo_path}" checkout --quiet -b "${branch_name}"

  for ((i=1; i<=num_commits; i++)); do
    echo "Commit ${i} on ${branch_name}" >> "${repo_path}/${safe_name}.txt"
    git -C "${repo_path}" add "${safe_name}.txt"
    git -C "${repo_path}" commit --quiet -m "Commit ${i} on ${branch_name}"
  done

  # Return to main/master
  git -C "${repo_path}" checkout --quiet "${default_branch}"
}

# Create a worktree for a branch
# Usage: create_worktree repo_path branch_name [worktree_name]
create_worktree() {
  local repo_path="$1"
  local branch_name="$2"
  local worktree_name="${3:-${branch_name//\//-}-wt}"
  local worktree_path="${_TEST_CONTEXT_DIR}/${worktree_name}"

  # Create worktree (errors visible for debugging)
  if ! git -C "${repo_path}" worktree add --quiet "${worktree_path}" "${branch_name}" 2>&1; then
    echo "ERROR: Failed to create worktree at ${worktree_path} for branch ${branch_name}" >&2
    return 1
  fi

  # Verify worktree exists and is registered with git
  if ! git -C "${repo_path}" worktree list | grep -q "${worktree_path}"; then
    echo "ERROR: Worktree created but not found in git worktree list" >&2
    return 1
  fi

  register_artifact "worktree" "${worktree_path}"

  LAST_WORKTREE_PATH="${worktree_path}"
  export LAST_WORKTREE_PATH
}

# Push a branch to a remote
# Usage: push_branch repo_path remote_name branch_name
push_branch() {
  local repo_path="$1"
  local remote_name="$2"
  local branch_name="$3"

  git -C "${repo_path}" push --quiet "${remote_name}" "${branch_name}"
}

# Set up remote tracking for a branch
# Usage: setup_tracking repo_path branch_name remote_name
setup_tracking() {
  local repo_path="$1"
  local branch_name="$2"
  local remote_name="$3"

  git -C "${repo_path}" branch --set-upstream-to="${remote_name}/${branch_name}" "${branch_name}" >/dev/null 2>&1 || true
}

# Delete a branch from remote (simulates "gone" state after fetch --prune)
# Usage: delete_remote_branch repo_path remote_name branch_name
delete_remote_branch() {
  local repo_path="$1"
  local remote_name="$2"
  local branch_name="$3"

  local remote_url
  remote_url=$(git -C "${repo_path}" remote get-url "${remote_name}")

  git -C "${remote_url}" branch -D "${branch_name}" >/dev/null 2>&1 || true
}

# Delete branch directly from bare remote path (silent)
# Usage: delete_branch_from_bare bare_repo_path branch_name
delete_branch_from_bare() {
  local bare_path="$1"
  local branch_name="$2"
  git -C "${bare_path}" branch -D "${branch_name}" >/dev/null 2>&1 || true
}

# Fetch with prune (silent)
# Usage: fetch_prune repo_path remote_name
fetch_prune() {
  local repo_path="$1"
  local remote_name="$2"
  git -C "${repo_path}" fetch --prune "${remote_name}" >/dev/null 2>&1
}

# Checkout branch (silent)
# Usage: checkout_branch repo_path branch_name
checkout_branch() {
  local repo_path="$1"
  local branch_name="$2"
  git -C "${repo_path}" checkout "${branch_name}" >/dev/null 2>&1
}

# Push to remote (silent)
# Usage: push_to_remote repo_path remote_name branch_name
push_to_remote() {
  local repo_path="$1"
  local remote_name="$2"
  local branch_name="$3"
  git -C "${repo_path}" push "${remote_name}" "${branch_name}" >/dev/null 2>&1
}

# Rename remote (silent)
# Usage: rename_remote repo_path old_name new_name
rename_remote() {
  local repo_path="$1"
  local old_name="$2"
  local new_name="$3"
  git -C "${repo_path}" remote rename "${old_name}" "${new_name}" >/dev/null 2>&1
}

# Fetch from remote (silent, no prune)
# Usage: fetch_remote repo_path remote_name
fetch_remote() {
  local repo_path="$1"
  local remote_name="$2"
  git -C "${repo_path}" fetch "${remote_name}" >/dev/null 2>&1
}

# Set upstream tracking (silent)
# Usage: set_upstream repo_path branch_name remote_branch
set_upstream() {
  local repo_path="$1"
  local branch_name="$2"
  local remote_branch="$3"
  git -C "${repo_path}" branch --set-upstream-to="${remote_branch}" "${branch_name}" >/dev/null 2>&1
}

# Set up HEAD for remote (so symbolic-ref works)
# Usage: setup_remote_head repo_path remote_name default_branch
setup_remote_head() {
  local repo_path="$1"
  local remote_name="$2"
  local default_branch="${3:-main}"

  git -C "${repo_path}" remote set-head "${remote_name}" "${default_branch}"
}

# Create a complete test environment with remote
# Usage: setup_full_test_env "context-name"
# Creates test context, then sets up TEST_REPO and TEST_REMOTE
setup_full_test_env() {
  local name="${1:-test-$$-$RANDOM}"

  # Create isolated test context first
  create_test_context "${name}" >/dev/null

  # Create bare remote
  create_bare_remote "remote" >/dev/null

  # Create main repo
  create_test_repo "repo" >/dev/null

  # Add remote
  add_remote "${TEST_REPO}" "origin" "${TEST_REMOTE}"

  # Push main and set up tracking
  git -C "${TEST_REPO}" push --quiet -u origin main 2>/dev/null || \
    git -C "${TEST_REPO}" push --quiet -u origin master

  # Set remote HEAD
  setup_remote_head "${TEST_REPO}" "origin" "main" 2>/dev/null || \
    setup_remote_head "${TEST_REPO}" "origin" "master"
}

# Clean up a specific test repo and its worktrees
cleanup_test_repo() {
  local repo_path="$1"

  if [[ ! -d "${repo_path}" ]]; then
    return 0
  fi

  # Remove all worktrees first
  git -C "${repo_path}" worktree list --porcelain 2>/dev/null | \
    grep "^worktree " | \
    sed 's/^worktree //' | \
    tail -n +2 | \
    while read -r wt; do
      [[ -d "${wt}" ]] && git -C "${repo_path}" worktree remove --force "${wt}" 2>/dev/null
    done

  # Remove the repo
  rm -rf "${repo_path}"
}

# Verify a branch exists
# Usage: branch_exists repo_path branch_name
branch_exists() {
  local repo_path="$1"
  local branch_name="$2"

  git -C "${repo_path}" show-ref --verify --quiet "refs/heads/${branch_name}"
}

# Verify a worktree exists
# Usage: worktree_exists repo_path worktree_path
worktree_exists() {
  local repo_path="$1"
  local worktree_path="$2"

  git -C "${repo_path}" worktree list | grep -q "${worktree_path}"
}

# Get branch tracking status
# Usage: get_tracking_status repo_path branch_name
get_tracking_status() {
  local repo_path="$1"
  local branch_name="$2"

  git -C "${repo_path}" for-each-ref --format="%(upstream:track)" "refs/heads/${branch_name}"
}

# Simulate a squash merge (commits exist in main but branch has different SHAs)
# Usage: simulate_squash_merge repo_path branch_name
simulate_squash_merge() {
  local repo_path="$1"
  local branch_name="$2"

  # Get the changes from the branch and apply as a single commit to main
  local current_branch
  current_branch=$(git -C "${repo_path}" branch --show-current)

  git -C "${repo_path}" checkout --quiet main 2>/dev/null || git -C "${repo_path}" checkout --quiet master

  # Squash merge the branch (suppress all output including "Squash commit" message)
  git -C "${repo_path}" merge --squash --quiet "${branch_name}" >/dev/null 2>&1
  git -C "${repo_path}" commit --quiet -m "Squash merge ${branch_name}"

  # Return to original branch if different
  if [[ "${current_branch}" != "main" ]] && [[ "${current_branch}" != "master" ]]; then
    git -C "${repo_path}" checkout --quiet "${current_branch}" 2>/dev/null || true
  fi
}
