# gitjam

**Learn to repair Git repositories by fixing real, deliberately broken repos.**

gitjam is an offline command-line puzzle game. Each level creates a local Git
repository with a realistic problem—such as a detached `HEAD`, a lost commit,
or a merge conflict—and checks your solution using Git itself. There are no
remotes, network calls, or runtime dependencies.

## Requirements

- Python 3.8 or newer
- Git 2.23 or newer

## Install

From a source checkout:

```shell
python -m pip install .
```

To run without installing:

```shell
python gitjam.py list
```

On Windows, use `py` in place of `python` if that is how Python is installed.

## Play

```text
$ gitjam list
gitjam levels:

  1. Wrong branch
  2. Detached HEAD
  3. The vanishing commit
  4. Merge conflict
  5. Undo without rewriting

$ gitjam start 3
Level 3: The vanishing commit
...
Fix it here:
  cd gitjam-play/level-3

$ cd gitjam-play/level-3
$ git reflog
$ gitjam check
PASS: Recovered. The reflog remembers everything.
```

Levels are created under `gitjam-play` in your current directory. Git commands
such as `reset --hard` are intentionally part of some puzzles, so work only in
the generated level repositories—not in a repository containing your own work.

| Command | What it does |
| --- | --- |
| `gitjam list` | Show all levels |
| `gitjam start <n>` | Create level `<n>` in `./gitjam-play/level-<n>` |
| `gitjam check` | Check the level from its repository or a subdirectory |
| `gitjam hint` | Show a hint for the current level |
| `gitjam --version` | Show the installed version |

To restart a level, remove that level's generated directory and run `gitjam
start <n>` again.

## Development

Run the test suite from the project directory:

```shell
python -m unittest discover -s tests -v
```

A level consists of a setup function that creates the broken repository and a
check function that returns `(ok, message)`. Register both in `LEVELS` and add
tests for the unsolved state and a valid solution.

## License

No license is currently provided. All rights are reserved; publishing this
repository does not grant permission to reuse, modify, or redistribute its
contents. Add a license before accepting contributions or allowing reuse.
