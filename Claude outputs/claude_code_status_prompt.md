Audit the current state of this repository and write a status report. This is a read-only audit — do not edit, fix, or create any file in the project other than the one report file named below. Do not run `git add`, `git commit`, or anything else that changes repo state. If a check requires running a command (tests, linters, etc.), that is fine — just don't modify source files.

Produce a single markdown file at the repo root named `PROJECT_STATUS.md` with these sections:

1. **Feature inventory** — walk `backend/app/` and `frontend/src/` and list, in plain language, every user-facing feature that's actually implemented (not just planned/mentioned in README) — auth, search, scoring, personalization, live hackathons, favorites, plan generation, PDF/PPTX export, admin tools, anything else you find. For each, note whether it has a corresponding route/component wired up and whether it has test coverage.

2. **Test status** — run the full backend suite (`pytest`) and the full frontend suite (Vitest/`npm test`), report pass/fail counts, and list any failing or skipped tests by name with the actual error.

3. **Data completeness** — read `data/processed/problems.json` and report: total problem count, how many have all 9 Gemini score fields (`resume_value_score`, `industry_relevance_score`, `technical_depth_score`, `novelty_score`, `dataset_availability_score`, `hardware_requirement_score`, `competition_potential_score`, `social_impact_score`, `feasibility_score`) vs. how many are missing at least one. Also check `data/processed/live_hackathons.json` — report `per_source_counts` so I can see which live-hackathon scrapers are actually returning data vs. returning zero.

4. **Config / security check** — look at `backend/app/core/config.py`, `backend/.env.example`, and (without printing its contents) confirm whether `backend/.env` exists and is listed in `.gitignore`. Report whether `JWT_SECRET_KEY`, `GEMINI_API_KEY`, `CORS_ORIGINS`, and `DATABASE_URL` are left at their insecure/local-dev defaults in whatever `.env` exists, or have been overridden — don't print the actual secret values, just say "default" or "overridden" for each. Also run `git log --all --full-history -- backend/.env` and report whether that file has ever been committed at any point in history, even if it's gitignored now.

5. **Git state** — `git status` (uncommitted changes, untracked files), current branch, and how many commits ahead/behind of `origin` if a remote is configured.

6. **Known gaps / TODOs** — grep the codebase for `TODO`, `FIXME`, `XXX`, and any comment mentioning "not implemented" or "temporary", and list what you find with file:line.

7. **One-paragraph summary at the top of the file** — plain-language verdict on whether this looks ready to demo/deploy today, and the single biggest thing blocking it if not.

When done, tell me in the chat: the test pass/fail counts, the data-completeness numbers, and whether `backend/.env` has ever been committed — those three things I need to see immediately, don't make me open the file for those.
