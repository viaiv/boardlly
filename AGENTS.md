# Repository Guidelines

## Project Structure & Module Organization
Tactyo currently ships an empty scaffold; new application code should reside in `src/`, grouped by feature (for example `src/boards` and `src/sessions`). Shared utilities belong in `src/lib`, while reusable UI or domain components live in `src/components`. Keep documentation updates in `docs/` and static assets (icons, mock data) in `assets/` with descriptive names. Place long-running experiments or prototypes in `labs/` and delete them as soon as they graduate into the main code paths.

## Build, Test, and Development Commands
Add shared scripts to the root `package.json` (or a `Makefile`) so every contributor uses the same workflow. Run them through npm or pnpm:
- `npm install` – set up dependencies before any local work.
- `npm run dev` – start the local development server; keep it free of warnings before pushing.
- `npm test` – execute the automated test suite and confirm it passes before opening a PR.
- `npm run lint` – apply formatting and linting; commit only clean trees.
Document any extra commands you introduce in `docs/commands.md` so newcomers can discover them quickly.

## Coding Style & Naming Conventions
Use 2-space indentation for JavaScript and TypeScript, with trailing commas on multi-line literals to minimise diff noise. Name files and directories in kebab-case (`board-list.tsx`), React components in PascalCase, and helper functions in camelCase. Prefer TypeScript definitions alongside their modules (`board.service.ts` with `board.service.types.ts`). Run Prettier and ESLint locally, and include configuration updates in the same PR as the code they affect.

## Testing Guidelines
Keep fast, deterministic tests under `tests/` or `src/**/__tests__`, naming them with the `.spec.ts` suffix. Use Vitest or Jest for unit coverage and preserve a minimum 80% statement coverage (`npm test -- --coverage`). Document fixtures in `tests/fixtures` and reset state between runs. When adding integration behaviour, sketch scenarios in `docs/test-plan.md` so reviewers can reason about gaps.

## Commit & Pull Request Guidelines
Write Conventional Commit-style messages (`feat:`, `fix:`, `chore:`) in the imperative mood and reference issue numbers when applicable. Squash local fixups before opening a PR. Each PR should explain the problem, the solution, and any follow-up steps; attach screenshots or terminal output when it aids review. Request review only after linting, tests, and local smoke checks pass, and tick off validation steps in the PR description template.

## Security & Configuration Tips
Store secrets and API keys in `.env.local` files ignored by Git; publish masked samples in `.env.example` when necessary. Never commit production credentials or tokens. Rotate any leaked keys immediately and document environment variable expectations in `docs/configuration.md`.
