## Standard Energy Efficiency Data (SEED) Platform™

[![Build Status][build-img]][build-url] [![Coverage Status][coveralls-img]][coveralls-url]

The SEED Platform is a web-based application that helps organizations easily
manage data on the energy performance of large groups of buildings. Users can
combine data from multiple sources, clean and validate it, and share the
information with others. The software application provides an easy, flexible,
and cost-effective method to improve the quality and availability of data to
help demonstrate the economic and environmental benefits of energy efficiency,
to implement programs, and to target investment activity.

The SEED application is written in Python/Django. The front end includes the
legacy AngularJS application and a newer Angular application in the
`ng_seed/seed-angular` submodule. The back-end database is PostgreSQL with
PostGIS; Docker development currently uses the repository's configured
TimescaleDB/Postgres image.

The SEED web application provides both a browser-based interface for users to
upload and manage their building data, as well as a full set of APIs that app
developers can use to access these same data management functions. From a
running server, the Swagger API documentation can be found at `/api/swagger`
or from the front end by clicking the API documentation link in the sidebar.

### Installation

- Production on Amazon Web Service: See [Installation Notes][production-aws-url]
- Development on macOS or Windows: [Installation Notes][development-local]
- Development using Docker: [Installation Notes][development-docker]

For local development, initialize the Angular UI submodule before installing
dependencies or building Docker images:

```bash
git submodule update --init ng_seed/seed-angular
```

### Starting SEED Platform

In production the following two commands will run the web server (Hypercorn) and
the background task manager (Celery) with:

```bash
bin/start_hypercorn.sh
bin/start_celery.sh
```

For basic local development only, run Celery tasks eagerly in the Django process
by setting `CELERY_TASK_ALWAYS_EAGER = True` and
`CELERY_TASK_EAGER_PROPAGATES = True` in `config/settings/local_untracked.py`.
Then start Django with:

```bash
uv run manage.py runserver
```

Run Django management commands through `uv` as `uv run manage.py <command>`.

Testing workflows that need real asynchronous behavior and production
deployments should run Celery as a separate worker/task. For that mode, set
`CELERY_TASK_ALWAYS_EAGER = False` and run the worker separately:

```bash
uv run celery -A seed worker -l INFO -c 4 --max-tasks-per-child 1000 -EBS django_celery_beat.schedulers:DatabaseScheduler
```

The legacy AngularJS app is served at `/app/`. The newer Angular app is served
at `/ng-app/` after its static assets have been built.

### Deployment appearance

Both UIs read deployment settings from Django. With no overrides, their current
appearance, navigation, and integrations remain unchanged. To customize a deployment (custom logo, remove specific functionality, etc.), set environment variables on the web container (and the Celery worker for integration policy). The SEED_HOME_CONTENT_MODE can be set to custom to replace the content on the home page or dashboard page (accessible after login). If this variable is set to custom, the SEED_HOME_HERO_IMAGE_URL can be used to replace to large image at the top of the page, and SEED_HOME_HEADING and SEED_HOME_TEXT can be used to add a custom heading and some custom text.  Similarly, SEED_BRAND_LOGO_URL can be used to replace the SEED logo on the login page and in the top left of the site with a custom logo. And SEED_HIDDEN_NAVIGATION can be assigned a list of links to hide from the UI. See below for the full list of environment variables that can be used to customize your SEED instance.

| Variable | Default | Effect |
| --- | --- | --- |
| `SEED_BRAND_LOGO_URL` | unset | Public `/branding/...` SVG, PNG, or WebP path; replaces the Angular sign-in, splash, and left-nav logos, and appears beside the legacy header text and above its configured sign-in form. Suggested logo image ratio 2:1 to 3:1. |
| `SEED_HOME_HERO_IMAGE_URL` | unset | Public `/branding/...` image path for the home-page hero; can also replace the stock legacy login background when branding is configured. Suggested size 2000 × 800 px. |
| `SEED_LOGIN_HEADING`, `SEED_LOGIN_TEXT` | unset | Sign-in heading and supporting copy. The legacy sign-in displays these above the form instead of its split marketing panel. |
| `SEED_HOME_HEADING`, `SEED_HOME_TEXT` | unset | Home heading and copy. Text is displayed as plain text, not HTML. |
| `SEED_HOME_CONTENT_MODE` | `default` | Set `custom` to replace legacy Getting Started buttons and show custom content on the new home page. |
| `SEED_HIDDEN_NAVIGATION` | empty | Comma-separated navigation IDs: `documentation,api,contact,about`. |
| `SEED_SALESFORCE_ENABLED`, `SEED_BETTER_ENABLED` | `true` | Set either to `false` to hide its UI and block its backend actions. Audit Template remains separate. |
| `SEED_BRANDING_DIR` | `./branding` | Compose host directory mounted read-only at `/seed/branding` for nginx. Set an absolute host path in production. |

```text
SEED_BRAND_LOGO_URL=/branding/client-logo.svg
SEED_HOME_HERO_IMAGE_URL=/branding/client-home.webp
SEED_LOGIN_HEADING=Welcome to the client portal
SEED_LOGIN_TEXT=Sign in with your account.
SEED_HOME_HEADING=Client buildings
SEED_HOME_TEXT=Your deployment-specific home page copy.
SEED_HOME_CONTENT_MODE=custom
SEED_HIDDEN_NAVIGATION=documentation,api,contact,about
SEED_SALESFORCE_ENABLED=false
SEED_BETTER_ENABLED=false
```

Only root-relative `/branding/` image paths are allowed. Copy the corresponding image
files into a deployment-owned directory, not this repository: Compose mounts
`${SEED_BRANDING_DIR:-./branding}` read-only at `/seed/branding` in the web container.
Set `SEED_BRANDING_DIR` to an absolute host path in production. Non-Compose deployments
must mount that directory at `/seed/branding` for nginx; Django's debug server uses the
repository's ignored `branding/` directory. The logo is public so it works before sign-in.
Use a suitably sized SVG or WebP and confirm both image URLs load before enabling them.
For a local preview, place `us-army.svg` in that ignored directory, start Django with
`SEED_BRAND_LOGO_URL=/branding/us-army.svg`, and restart the Angular dev server so its
`/branding/` proxy is loaded. No frontend rebuild is needed when the image or Django
settings change. Leave image variables unset when no corresponding file is present.

`custom` replaces the legacy Getting Started buttons with `SEED_HOME_TEXT` and shows
custom copy on the new home page; leaving it unset retains each UI's existing home.
The custom hero appears above the heading and text at the content width, with its
full aspect ratio preserved instead of being cropped to a fixed height.
Hidden navigation only removes menu entries; direct URLs and other outbound links
remain accessible. Audit Template is independent of the Salesforce and BETTER flags.

### Developer Resources

- Source code documentation is on the [SEED website][code-documentation] and there are links to [older versions][code-documentations-links] as needed.
- Several notes regarding Django and AngularJS integration: See [Developer Resources][developer-resources]

#### Testing

- Running tests: See [Testing Notes][developer-testing-notes]

### Copyright

See the information in the [LICENSE.md](LICENSE.md) file.

[code-documentation]: https://seed-platform.org/code_documentation/latest/
[code-documentation-links]: https://seed-platform.org/developer_resources/
[development-docker]: https://github.com/SEED-platform/seed/blob/develop/docs/source/setup_docker.rst
[development-local]: https://github.com/SEED-platform/seed/blob/develop/docs/source/setup_osx.rst
[production-aws-url]: https://github.com/seed-platform/seed/wiki/Installation
[developer-resources]: https://github.com/SEED-platform/seed/blob/develop/docs/source/developer_resources.rst
[developer-testing-notes]: https://github.com/SEED-platform/seed/blob/develop/docs/source/developer_resources.rst#testing
[build-img]: https://github.com/SEED-platform/seed/workflows/CI/badge.svg?branch=develop
[build-url]: https://github.com/SEED-platform/seed/actions?query=branch%3Adevelop
[coveralls-img]: https://coveralls.io/repos/github/SEED-platform/seed/badge.svg?branch=HEAD
[coveralls-url]: https://coveralls.io/github/SEED-platform/seed?branch=HEAD
