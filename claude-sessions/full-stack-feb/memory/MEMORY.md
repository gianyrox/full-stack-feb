# Project Memory

## Git Workflow (FOLLOW EVERY SESSION — parallel-safe, beads-integrated)

**Multiple sessions may be active simultaneously on different branches. NEVER force push or overwrite.**

At the **start** of each session:
1. `cd /home/gian/Projects/full-stack-feb/full-stack-feb`
2. `git checkout main && git pull origin main`
3. Create a UNIQUE feature branch: `git checkout -b <descriptive-branch-name>`
4. `bd ready` — find unblocked work
5. `bd update <id> --claim` — claim the bead

While working:
- **After EVERY meaningful change** (new file, function complete, bug fix): commit AND push immediately
- `git add <files> && git commit -m "description (bead-id)" && git push origin <branch-name>`
- Do NOT batch up work — if the session dies, unpushed work is LOST
- Aim for a commit+push every 5-10 minutes of active work

**Before ANY merge to main (MANDATORY):**
- `cd frontend && npx tsc --noEmit` — TypeScript type-check MUST pass
- Fix ALL type errors on the feature branch before proceeding

At the **end** of each session (merge safely):
1. Commit and push all work on the feature branch
2. `bd close <id> --reason "Completed"` — close the bead
3. `git checkout main && git pull origin main`
4. `git checkout <branch-name>` — go BACK to feature branch
5. `git merge main` — merge main INTO your branch, resolve conflicts HERE
6. `cd frontend && npx tsc --noEmit` — type-check MUST pass after merge
7. `git checkout main && git merge <branch-name>` — fast-forward merge to main
8. `git push origin main`
9. `git push origin --delete <branch-name>` && `git branch -d <branch-name>`

**CRITICAL RULES:**
- NEVER `git push --force` to main
- NEVER merge to main without `npx tsc --noEmit` passing first
- NEVER merge directly on main without pulling first
- ALWAYS resolve conflicts on the feature branch, not on main
- If `git push origin main` fails (another session pushed), repeat steps 3-8
- Before merging, CHECK `git log origin/main --oneline -5` to see if other sessions pushed

## Issue Tracking — bd (beads)

- Uses Steve Yegge's Beads system backed by Dolt (version-controlled SQL)
- `.beads/` directory in project root — do NOT delete
- `bd ready` to find unblocked work, `bd update <id> --claim` to claim
- `bd close <id> --reason "Done"` when complete
- Include bead ID in commit messages: `git commit -m "Add scraper (full-stack-feb-mw1)"`
- Do NOT use markdown TODOs or TASKS.md — bd is the single source of truth
- Never use `bd edit` (interactive) — use `bd update <id> --description "text"`
- See AGENTS.md for full agent workflow

## Repository

- Remote: https://github.com/gianyrox/full-stack-feb.git
- Working dir: `/home/gian/Projects/full-stack-feb/full-stack-feb`
- Main branch: `main`

## Project

- Oscar Medical Guidelines scraper + criteria tree explorer (timed coding challenge)
- Uses OpenAI API (key in .env)
- See CLAUDE.md for full project spec summary
