#!/usr/bin/env python3
"""gitjam - fix real, broken git repos. Offline, no remote, no dependencies.

Usage:
    gitjam list              show all levels
    gitjam start <n>         create a broken repo for level n
    gitjam check [path]      check whether you fixed it (run inside the repo)
    gitjam hint [path]       get a hint for the current level
"""
import os
import subprocess
import sys

__version__ = "0.1.0"

PLAY_DIR = "gitjam-play"
LEVEL_FILE = "gitjam_level"  # stored inside .git so it never shows in `git status`


# --------------------------------------------------------------------------
# git helpers
# --------------------------------------------------------------------------
def git(path, *args, check=True):
    """Run a git command in `path` and return stdout (stripped)."""
    result = subprocess.run(
        ["git", *args],
        cwd=path,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def init_repo(path):
    os.makedirs(path, exist_ok=True)
    git(path, "init", "-q")
    git(path, "symbolic-ref", "HEAD", "refs/heads/main")
    git(path, "config", "user.name", "Gitjam Player")
    git(path, "config", "user.email", "player@gitjam.local")
    git(path, "config", "commit.gpgsign", "false")
    git(path, "config", "core.hooksPath", os.path.join(path, ".git", "gitjam-hooks"))


def write(path, name, text):
    with open(os.path.join(path, name), "w") as f:
        f.write(text)


def read(path, name):
    with open(os.path.join(path, name)) as f:
        return f.read()


def commit(path, name, text, message):
    write(path, name, text)
    git(path, "add", name)
    git(path, "commit", "-q", "-m", message)
    return git(path, "rev-parse", "HEAD")


def log_messages(path, ref="HEAD"):
    out = git(path, "log", "--format=%s", ref, check=False)
    return out.splitlines() if out else []


def branch_exists(path, name):
    return bool(git(path, "branch", "--list", name, check=False))


def is_clean(path):
    return git(path, "status", "--porcelain") == ""


def current_branch(path):
    """Return branch name, or None when HEAD is detached."""
    out = git(path, "symbolic-ref", "--short", "-q", "HEAD", check=False)
    return out or None


# --------------------------------------------------------------------------
# levels: each has setup(path) and check(path) -> (ok, message)
# --------------------------------------------------------------------------
def setup_1(p):
    init_repo(p)
    commit(p, "app.txt", "v1\n", "Initial commit")
    git(p, "branch", "feature")  # feature exists but is empty of new work
    commit(p, "login.txt", "login page\n", "Add login page")  # oops, on main


def check_1(p):
    if current_branch(p) is None:
        return False, "HEAD is detached. Get back on a branch."
    if "Add login page" in log_messages(p, "main"):
        return False, "'Add login page' is still on main."
    if "Add login page" not in log_messages(p, "feature"):
        return False, "'Add login page' isn't on the feature branch yet."
    if not is_clean(p):
        return False, "Working tree isn't clean."
    return True, "main is clean and the work lives on feature."


def setup_2(p):
    init_repo(p)
    first = commit(p, "app.txt", "v1\n", "Initial commit")
    commit(p, "app.txt", "v2\n", "Second commit")
    git(p, "checkout", "-q", first)  # detached HEAD
    commit(p, "important.txt", "do not lose me\n", "Important work")


def check_2(p):
    if not branch_exists(p, "rescue"):
        return False, "There's no branch called 'rescue' yet."
    if "Important work" not in log_messages(p, "rescue"):
        return False, "'rescue' doesn't contain the 'Important work' commit."
    if current_branch(p) is None:
        return False, "HEAD is still detached. Switch onto a branch."
    return True, "Your work is safe on 'rescue'."


def setup_3(p):
    init_repo(p)
    commit(p, "app.txt", "v1\n", "Initial commit")
    commit(p, "payment.txt", "payment code\n", "Add payment feature")
    git(p, "reset", "-q", "--hard", "HEAD~1")  # oh no


def check_3(p):
    if "Add payment feature" not in log_messages(p, "main"):
        return False, "'Add payment feature' is not back on main."
    if current_branch(p) != "main":
        return False, "You should be on main."
    if not os.path.exists(os.path.join(p, "payment.txt")):
        return False, "payment.txt is missing from your working tree."
    return True, "Recovered. The reflog remembers everything."


def setup_4(p):
    init_repo(p)
    commit(p, "greeting.txt", "hello\n", "Initial commit")
    git(p, "checkout", "-q", "-b", "feature")
    commit(p, "greeting.txt", "hello\nfrom feature\n", "Feature greeting")
    git(p, "checkout", "-q", "main")
    commit(p, "greeting.txt", "hello\nfrom main\n", "Main greeting")
    git(p, "merge", "feature", check=False)  # stops with a conflict


def check_4(p):
    if os.path.exists(os.path.join(git_dir(p), "MERGE_HEAD")):
        return False, "The merge is still in progress. Finish it with a commit."
    text = read(p, "greeting.txt")
    if "<<<<<<<" in text or ">>>>>>>" in text or "=======" in text:
        return False, "greeting.txt still has conflict markers."
    if "from main" not in text or "from feature" not in text:
        return False, "Keep BOTH lines: 'from main' and 'from feature'."
    parents = git(p, "rev-list", "--parents", "-n", "1", "HEAD").split()
    if len(parents) != 3:
        return False, "HEAD should be a merge commit (two parents)."
    return True, "Conflict resolved, both sides kept, merge committed."


def setup_5(p):
    init_repo(p)
    commit(p, "config.txt", "debug=false\n", "Initial commit")
    commit(
        p,
        "config.txt",
        "debug=true\npassword=example-only-not-a-real-secret\n",
        "Oops bad config",
    )
    commit(p, "readme.txt", "docs\n", "Add readme")


def check_5(p):
    msgs = log_messages(p)
    if "Oops bad config" not in msgs:
        return False, "Don't rewrite history! The bad commit must stay in the log."
    if "Add readme" not in msgs:
        return False, "The readme commit must stay in the log."
    if "example-only-not-a-real-secret" in read(p, "config.txt"):
        return False, "config.txt still contains the bad password line."
    if not os.path.exists(os.path.join(p, "readme.txt")):
        return False, "readme.txt must still exist."
    if len(msgs) < 4:
        return False, "Undo the bad commit with a NEW commit."
    return True, "Bad change undone, history intact."


LEVELS = {
    1: {
        "title": "Wrong branch",
        "story": (
            "You meant to work on 'feature' but committed 'Add login page' on main.\n"
            "Goal: main should be back to just 'Initial commit', and the login\n"
            "commit should live on 'feature'."
        ),
        "hint": "Look at git log, git branch, and git reset. Moving a commit = point a branch at it, then move the other back.",
        "setup": setup_1,
        "check": check_1,
    },
    2: {
        "title": "Detached HEAD",
        "story": (
            "You checked out an old commit and made 'Important work' there.\n"
            "HEAD is detached, so that commit is one checkout away from vanishing.\n"
            "Goal: save it on a new branch called 'rescue' and be on a branch."
        ),
        "hint": "git branch <name> (or git switch -c <name>) saves where you are.",
        "setup": setup_2,
        "check": check_2,
    },
    3: {
        "title": "The vanishing commit",
        "story": (
            "You ran git reset --hard and 'Add payment feature' disappeared.\n"
            "Goal: get it back on main."
        ),
        "hint": "git reflog shows where HEAD used to be. Then reset back to it.",
        "setup": setup_3,
        "check": check_3,
    },
    4: {
        "title": "Merge conflict",
        "story": (
            "You tried to merge 'feature' into main and git stopped.\n"
            "Goal: keep BOTH greeting lines ('from main' and 'from feature'),\n"
            "remove the conflict markers, and finish the merge."
        ),
        "hint": "Edit greeting.txt, then git add it and git commit.",
        "setup": setup_4,
        "check": check_4,
    },
    5: {
        "title": "Undo without rewriting",
        "story": (
            "'Oops bad config' leaked a password and a newer commit sits on top of it.\n"
            "Goal: undo that change WITHOUT deleting history (others already pulled it)."
        ),
        "hint": "git revert makes a new commit that cancels an old one.",
        "setup": setup_5,
        "check": check_5,
    },
}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def find_repo(arg):
    path = os.path.abspath(arg or ".")
    if not os.path.isdir(path):
        return None
    root = git(path, "rev-parse", "--show-toplevel", check=False)
    if not root:
        return None
    root = os.path.abspath(root)
    if os.path.exists(os.path.join(git_dir(root), LEVEL_FILE)):
        return root
    return None


def git_dir(path):
    """Return the repository's git directory, including for linked worktrees."""
    return git(path, "rev-parse", "--absolute-git-dir")


def level_of(path):
    try:
        level = int(read(git_dir(path), LEVEL_FILE).strip())
    except (OSError, ValueError) as exc:
        raise RuntimeError("Gitjam level metadata is missing or invalid.") from exc
    if level not in LEVELS:
        raise RuntimeError(f"Unknown gitjam level in repository metadata: {level}.")
    return level


def cmd_list():
    print("gitjam levels:\n")
    for n, lvl in LEVELS.items():
        print(f"  {n}. {lvl['title']}")
    print("\nStart one with: gitjam start <n>")


def cmd_start(arg):
    if not arg or not arg.isdigit() or int(arg) not in LEVELS:
        print("Usage: gitjam start <n>   (see: gitjam list)")
        return 2
    n = int(arg)
    path = os.path.join(os.getcwd(), PLAY_DIR, f"level-{n}")
    if os.path.exists(path):
        print(f"{path} already exists. Delete it to restart this level.")
        return 1
    LEVELS[n]["setup"](path)
    write(git_dir(path), LEVEL_FILE, str(n))
    print(f"Level {n}: {LEVELS[n]['title']}\n")
    print(LEVELS[n]["story"])
    print(f"\nFix it here:\n  cd {os.path.relpath(path)}\n")
    print("When you think you're done: gitjam check")
    return 0


def cmd_check(arg):
    path = find_repo(arg)
    if not path:
        print("This isn't a gitjam repo. cd into gitjam-play/level-N first.")
        return 2
    ok, msg = LEVELS[level_of(path)]["check"](path)
    print(("PASS: " if ok else "NOT YET: ") + msg)
    if ok and level_of(path) < len(LEVELS):
        print(f"Next up: gitjam start {level_of(path) + 1}")
    return 0 if ok else 1


def cmd_hint(arg):
    path = find_repo(arg)
    if not path:
        print("This isn't a gitjam repo. cd into gitjam-play/level-N first.")
        return 2
    print("Hint: " + LEVELS[level_of(path)]["hint"])
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, arg = argv[0], (argv[1] if len(argv) > 1 else None)
    if len(argv) > 2 or (cmd in ("list", "--version") and arg is not None):
        print("Too many arguments.\n")
        print(__doc__)
        return 2
    try:
        if cmd == "list":
            cmd_list()
            return 0
        if cmd == "start":
            return cmd_start(arg)
        if cmd == "check":
            return cmd_check(arg)
        if cmd == "hint":
            return cmd_hint(arg)
        if cmd == "--version":
            print(__version__)
            return 0
        print(__doc__)
        return 2
    except (OSError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
