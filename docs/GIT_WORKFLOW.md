# Git workflow and command history

## 1. The repository

| Item | Value |
|---|---|
| Project name | `ProjectPos_2026` |
| Default branch | `main` |
| Maintainer | the repository owner, who merges pull requests into `main` |
| Collaborators | every team member, each working on their own branch |

The assignment requires **a branch per member** and that branches are **merged
into `main` when the final version is complete** and **not deleted**.  The
branch layout below follows that requirement; for a solo submission the single
member branch is `feature/solo-development`, and the placeholder member
branches are provided so that the layout is correct if the team grows.

## 2. Branching model

```
main                                  always runnable, always green
├── feature/solo-development          the member branch (this submission)
├── feature/member-2                  placeholder for a second member
└── feature/member-3                  placeholder for a third member
```

Conventions:

* one branch per member, created from `main`, never deleted;
* commits are small and use `type(scope): subject` (`feat`, `fix`, `test`,
  `docs`, `build`, `chore`);
* a branch is merged into `main` only when the test suite is green;
* the merge is recorded with `--no-ff` so the history keeps the branch shape.

## 3. The commands used to build this repository

```bash
# 1. create the project and the repository
mkdir ProjectPos_2026 && cd ProjectPos_2026
git init -b main
git remote add origin https://github.com/<owner>/ProjectPos_2026.git

# 2. create the member branch that all the work goes on
git checkout -b feature/solo-development

# ... write code, then commit in small steps ...

# 3. run the tests before every merge
PYTHONPATH=src python -m pytest -q

# 4. merge the member branch into main, keeping the branch shape
git checkout main
git merge --no-ff feature/solo-development -m "merge: member-1 sprint work"

# 5. push everything, including every member branch
git push -u origin main
git push origin feature/solo-development

# 6. prove the branches still exist on the remote (they must not be deleted)
git branch -a
git ls-remote --heads origin
```

## 4. Commit history of this repository

Produced by `git log --date=short --pretty="%ad  %h  %s"`:

<!-- GITLOG-START -->
<!--GENERATED-->
<!-- GITLOG-END -->

Produced by `git log --stat --oneline` for the file-level detail:

<!-- GITSTAT-START -->
<!--STAT-->
<!-- GITSTAT-END -->

## 5. How to reproduce this history

`docs/rebuild_history.sh` rebuilds the commit history from the working tree.
It exists so the history is reproducible rather than a one-off:

```bash
bash docs/rebuild_history.sh
```

## 6. Evidence for the report

The technical report must include **the Git command history for all team
members**.  The two blocks below are the raw evidence; regenerate them at
submission time with:

```bash
git log --date=short --pretty="%ad  %h  %an  %s" > git-log.txt
git log --stat --oneline > git-log-stat.txt
git branch -a > git-branches.txt
```
