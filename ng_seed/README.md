# SEED-Angular

This documentation describes the process of setting up and running the new SEED Angular UI alongside the AngularJS UI.

All the following commands assume that this location is your current working directory (`cd ng_seed/seed-angular`).

> After running `watch` or `build` browse to [http://localhost:8000/ng-app/](http://localhost:8000/ng-app/) to use the
> new UI.

### Install dependencies

```bash
pnpm i
```

### Run in development

**From Angular with hot-reloading:**

```bash
pnpm start
```

Then browse to http://localhost:4200

**From Django:**

```bash
pnpm watch
```

### Build for production

```bash
pnpm build
```

## Submodule commands

This branch adds a git submodule for linking the seed-angular repo.

- When switching to this branch run `git submodule update --init`
- When you need to update the submodule to the latest commit from the seed-angular repo: `git submodule update --remote`
  or `git pull origin task/angular-20`
  - From the SEED root, you can also run `git submodule update --remote ng_seed/seed-angular`
