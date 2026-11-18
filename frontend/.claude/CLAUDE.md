# CLAUDE.md

AI agent guidance for this repository is maintained in a **single canonical file** so it stays DRY
and never drifts between agents.

## Start here

- **[`.github/copilot-instructions.md`](../.github/copilot-instructions.md)** — the authoritative,
  agent-facing guide: project context, setup & commands, architecture, linting & code style, key
  conventions (TypeScript/Angular, RxJS, CSS & UI, translations, empty/loading states,
  accessibility), change discipline, and the definition of done. **Read this first and follow it.**

## Additional rules

- When working on the new UI, don't alter existing v3 views. If completely necessary for performance or updated patterns, add a v4 endpoint.
- When I say that everything looks good, can you run the precommit / linting rules (from the repo's CI configs) to ensure none of those tests will fail when pushed to github
- When making changes, please consider section 508 accessibility rules
- Always report untranslated items so I can add them to Lokalise

-Be consistent with visual elements (looks of buttons, badges, etc.)

## Deeper references (all linked from the file above)

- **[`../DEVELOPER.md`](../DEVELOPER.md)** — the full human coding-standards guide
  (Angular/TypeScript/RxJS/CSS conventions).
- **[`../MIGRATION.md`](../MIGRATION.md)** — the legacy-AngularJS → Angular migration playbook plus
  the tracked page/route status (what's done, what's left, what won't be ported).
- **[`../docs/porting-forms.md`](../docs/porting-forms.md)** — the form/modal porting recipe.
- **[`../docs/local-testing.md`](../docs/local-testing.md)** — stand up a throwaway backend + seed
  data and click through your change with the Playwright MCP tools before calling it done.

> Everything that previously lived in this file now lives in `.github/copilot-instructions.md`.
> Keep a single source of truth rather than duplicating guidance across agent files.
