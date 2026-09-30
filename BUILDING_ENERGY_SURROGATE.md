# Building Energy Surrogate Models (179D) — SEED analysis

A SEED **analysis pipeline** that runs building-energy surrogate (machine-learning)
models against each selected property to predict whole-building energy/cost
savings for upgrade scenarios. Today it runs the `calculator_179d` models
(from the **BEM-prediction-models** project) and stores the resulting energy/cost
savings and the **§179D tax deduction** back on the property. The name is
intentionally general so additional surrogate-model use cases can be added later.

Because the calculator depends on a pinned scientific-Python / scikit-learn stack
that is **incompatible with SEED's** dependencies, SEED never imports it. It runs
the model **out-of-process** in the calculator's own virtual environment and
exchanges JSON over stdin/stdout.

---

## 0. Running the local SEED stack (prerequisite)

The surrogate analysis runs **inside SEED**, so you need SEED running first. In
this project SEED runs **natively on the host** (via `uv`); only the **database
and cache run in Docker**. The **Celery worker** is what executes the analysis,
so it must be running and configured (§4).

**Architecture of the local dev setup**

| Component | Where it runs | Notes |
|-----------|---------------|-------|
| PostgreSQL / PostGIS | Docker container `seed_postgres` | host port **5433** → container 5432 |
| Redis | Docker container `seed_redis` | host port **6379** |
| SEED web + Celery worker | **host**, `uv run` in the seed repo | `config.settings.dev` → db `seed`, redis db `/1`, port **8000** |
| `calculator_179d` | **host**, its own venv (§3) | invoked out-of-process by the worker |

> A second, optional instance ("Better Buildings") runs the same way from
> `config.settings.seed_bb` (db `seed_bb`, redis db `/2`, port **8001**). Use it
> only if you restored that dataset; the 179D instance below is the primary one.

**Bring it all up**

```bash
# 1. Start the DB + cache containers (Docker Desktop must be running).
docker start seed_postgres seed_redis
#    First time only, if those containers don't exist yet:
#    docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db-postgres db-redis

# 2. From the SEED repo, start the web server (host).
cd ~/Desktop/dev/seed
uv run python manage.py migrate                 # first run / after pulling migrations
uv run python manage.py runserver 0.0.0.0:8000

# 3. In a second shell, start the Celery worker (this runs the analysis).
cd ~/Desktop/dev/seed
uv run celery -A seed worker -l INFO -c 2 --max-tasks-per-child 1000 -E
```

SEED is then at **http://127.0.0.1:8000/app**. Confirm infra health with
`docker exec seed_redis redis-cli ping` (→ `PONG`) and
`docker exec seed_postgres pg_isready -U seed`.

---

## 1. Where it lives

| Path | Role |
|------|------|
| `seed/analysis_pipelines/building_energy_surrogate.py` | The analysis pipeline: gathers per-property inputs, invokes the calculator, persists results. Class `BuildingEnergySurrogatePipeline`. |
| `seed/analysis_pipelines/building_energy_surrogate_runner.py` | The **out-of-process runner**. Imports `calculator_179d`, reads a `PropertyInfo` JSON on stdin, writes a results dict on stdout. Depends only on `calculator_179d` + stdlib — **never** imports Django/SEED. |
| `seed/analysis_pipelines/pipeline.py` | Registers `Analysis.BUILDING_ENERGY_SURROGATE` → `BuildingEnergySurrogatePipeline`. |
| `seed/analysis_pipelines/tasks.py` | Imports the pipeline's Celery `_finish_preparation` / `_run_analysis` tasks. |
| `seed/models/analyses.py` | `Analysis.BUILDING_ENERGY_SURROGATE = 9` service type + its results-summary panel. |
| `seed/models/column_list_profile_columns.py` | `Meta.ordering = ["order", "id"]` so the generated result columns render left-to-right. |
| `config/settings/common.py` | The `BUILDING_ENERGY_SURROGATE_*` settings (see §4). |
| `seed/migrations/0255_*` | Adds the service choice + the column-profile ordering. Apply with `manage.py migrate`. |
| Legacy AngularJS UI (`seed/static/seed/…`) | The **Run Analysis** modal option "Building Energy Surrogate Models", its controller case, and the locale description. |
| `seed/tests/test_analysis_pipelines.py` | `TestBuildingEnergySurrogateTaxPolicy` — pure-Python tax-schedule tests. |

The surrogate model itself (`calculator_179d`) is **not** vendored in this repo —
you install it separately into its own venv (see §3).

---

## 2. How it works

```
SEED property (native columns + extra_data)
   -> build PropertyInfo inputs (units converted to SI; defaults fill blanks)
   -> subprocess: <BUILDING_ENERGY_SURROGATE_PYTHON> building_energy_surrogate_runner.py
        (stdin  = PropertyInfo JSON)
        (stdout = CalculatorOutputs JSON)  <- calculator_179d.calculate_savings()
   -> persist results to the property's extra_data columns
   -> add headline columns to the "179D" column-list profile
   -> results summary panel (Total Energy Cost Savings, Qualifies for 179D, 179D Deduction)
```

- The pipeline pulls inputs from each property (see §5), converts IP→SI units,
  fills any missing "proposed design" inputs from documented defaults, and
  serializes a `PropertyInfo` object.
- `_run_calculator()` launches the runner with the configured interpreter and a
  timeout, capturing JSON on stdout. Any `{"error": …}` payload is surfaced as an
  analysis message on that property.
- Results are written as dynamic `extra_data` columns and, for the headline
  metrics, appended to a column-list profile named **"179D"** (List + Detail
  views) if one exists for the org.
- The §179D deduction schedule is chosen by the building's **Date Placed in
  Service** year (`_tax_policy_for_date`), falling back to a default year.

---

## 3. Dependencies & setup (the calculator venv)

The calculator runs under its **own** Python environment, isolated from SEED. In
this project it lives in a checkout of the **BEM-prediction-models** project next
to the SEED repo, with `calculator_179d` installed into that checkout's venv:

1. Locate/clone **BEM-prediction-models** and create its venv (any Python
   compatible with `calculator_179d`; this project uses the Anaconda base Python):

   ```bash
   cd ~/Desktop/dev/BEM-prediction-models
   python3 -m venv .venv
   .venv/bin/pip install --upgrade pip
   .venv/bin/pip install -e .        # installs calculator_179d from this checkout
   ```

2. Verify `calculator_179d` imports under that interpreter:

   ```bash
   ~/Desktop/dev/BEM-prediction-models/.venv/bin/python \
     -c "import calculator_179d; print('calculator_179d OK')"
   ```

3. Point SEED at that interpreter (see §4). In the local dev setup this is set in
   **`config/settings/local_untracked.py`** (loaded by `config.settings.dev`):

   ```python
   BUILDING_ENERGY_SURROGATE_PYTHON = os.path.expanduser(
       "~/Desktop/dev/BEM-prediction-models/.venv/bin/python"
   )
   ```

4. Sanity-check the runner end-to-end under that interpreter (from the SEED repo):

   ```bash
   cd ~/Desktop/dev/seed
   echo '{}' | ~/Desktop/dev/BEM-prediction-models/.venv/bin/python \
     seed/analysis_pipelines/building_energy_surrogate_runner.py
   # a JSON object (even an {"error": …} about inputs) means calculator_179d imported OK;
   # "calculator_179d is not importable" means the venv is missing the package.
   ```

> **Why a separate venv?** `calculator_179d` pins scientific-Python and pickled
> scikit-learn models that conflict with SEED's stack. Keeping it out-of-process
> avoids dependency collisions and lets the model stack be upgraded independently.
> If the package is on disk but **not** `pip install`ed, expose its parent
> directory via `BUILDING_ENERGY_SURROGATE_PACKAGE_DIR` (§4) instead of step 1's
> `pip install -e .`.

---

## 4. Configuration (SEED settings)

Defined in `config/settings/common.py`, all overridable by environment variable:

| Setting / env var | Default | Purpose |
|-------------------|---------|---------|
| `BUILDING_ENERGY_SURROGATE_PYTHON` | *unset* | **Required.** Absolute path to the calculator venv's Python interpreter (e.g. `/opt/surrogate-venv/bin/python`). When unset, the analysis fails fast with a clear configuration error. |
| `BUILDING_ENERGY_SURROGATE_PACKAGE_DIR` | *unset* | Optional. Extra directory prepended to `PYTHONPATH` when invoking the calculator (use for a non-pip-installed BEM-prediction-models checkout). |
| `BUILDING_ENERGY_SURROGATE_TIMEOUT` | `120` | Seconds before a single-property calculator subprocess is aborted. |

Set these in the SEED runtime environment (the web + Celery workers). In the
**local dev setup** they're set in `config/settings/local_untracked.py` (Python,
not env vars) — see §3. When you'd rather use environment variables (e.g. a
container/prod worker), export them before launching the worker:

```bash
export BUILDING_ENERGY_SURROGATE_PYTHON="$HOME/Desktop/dev/BEM-prediction-models/.venv/bin/python"
# optional:
export BUILDING_ENERGY_SURROGATE_PACKAGE_DIR="$HOME/Desktop/dev/BEM-prediction-models"
export BUILDING_ENERGY_SURROGATE_TIMEOUT=180
```

The **Celery worker** process runs the analysis, so it must have this setting and
be able to execute the interpreter path. After changing `local_untracked.py`,
restart the worker.

---

## 5. Required property inputs

Inputs come from the **179D-portal export fields** on the SEED property. Native
columns and `extra_data` keys:

**From native columns**
- Property Type (building type)
- Gross Floor Area
- Postal Code (used to derive the ASHRAE climate zone)

**From `extra_data` (179D-portal field labels, IP units)**
- `HVAC System`
- `Number of Floors`
- `Aspect Ratio`
- `Vertical Fenestration Percentage`
- `Date Placed in Service` (selects the §179D tax-year schedule)
- *"Building Information (continued)" advanced inputs* — envelope U-factors,
  window SHGC, lighting power density, HVAC efficiencies, heating capacity, and
  service-hot-water specs. **Any advanced input left blank falls back to a
  documented default "proposed design" profile.** Utility rates and the tax-policy
  schedule always come from that profile (the portal doesn't collect them
  per-building).

**Supported scope (properties outside this are skipped with a message):**
- Building types: `small office`, `retail stripmall`
- HVAC systems: `PSZ-HP`, `PSZ-AC with electric coil`, `PSZ-AC with gas coil`,
  `HP RTU`, `MSHP DOAS`, `VRF DOAS`

Advanced users can override individual `PropertyInfo` fields directly via
`extra_data` (e.g. `SEER`, `HSPF`, `roof_u_value_w_per_m2_k`,
`electricity_rate_cents_per_kwh`) — see `OVERRIDE_FIELDS` in the pipeline.

---

## 6. Outputs

Written to each property's `extra_data` as dynamic columns. Headline columns are
added to the **"179D"** column-list profile; baseline columns are persisted but
kept off the display profile.

**Headline (RESULT_COLUMNS)**
- Energy & Power Cost Percent Savings
- Annual Site EUI Savings (kBtu/ft²)
- Electricity Savings (kBtu)
- Energy & Power Cost Savings per SqFt ($/ft²)
- Natural Gas Savings (kBtu)
- 179D Tax Deduction — Energy Only ($/ft²)
- 179D Tax Deduction — All Criteria ($/ft²)

**Baseline (BASELINE_RESULT_COLUMNS, off-profile)**
- Baseline Electricity Use / Natural Gas Use / Total Energy Use (kBtu) — modeled
  pre-retrofit energy, consumed e.g. by the SEED-Agent RFP's baseline section.

**Results-summary panel** (analysis details): Total Energy Cost Savings,
Qualifies for 179D (Yes/No), 179D Deduction (Whole Building).

> To make the headline columns appear on the List/Detail grids, create a
> **column-list profile named `179D`** for the organization before (or after)
> running; the columns are appended to it when the analysis runs.

---

## 7. How to run it

**In the SEED UI (primary path)**
1. Bring up the stack (§0) and configure the calculator venv
   (`BUILDING_ENERGY_SURROGATE_PYTHON`, §3–§4). Ensure the **Celery worker is
   running** — it executes the analysis. Apply migrations (`manage.py migrate`).
2. Ensure the target properties carry the 179D-portal export fields (§5).
3. Open a property (or a selection) → **Actions → Run Analysis** →
   choose **"Building Energy Surrogate Models"** → **Create/Run**.
4. When it finishes, view the results-summary panel and the `179D`-profile
   columns on the inventory/detail pages.

**Via the Analyses API**
Create an analysis with the service type for "Building Energy Surrogate Models"
(`Analysis.BUILDING_ENERGY_SURROGATE = 9`) and the target `property_view_ids`
through the v3 Analyses endpoints, then start it — the same pipeline runs.

---

## 8. Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| Analysis fails immediately: *"BUILDING_ENERGY_SURROGATE_PYTHON is not configured"* | The setting is unset on the worker. Set it in `local_untracked.py` (or export the env var) and restart the Celery worker (§3–§4). |
| Per-property error: *"calculator_179d is not importable"* | The interpreter path is wrong, or the venv doesn't have `calculator_179d`. Reinstall into that venv (or set `BUILDING_ENERGY_SURROGATE_PACKAGE_DIR`). |
| *"179D calculator interpreter not found"* | `BUILDING_ENERGY_SURROGATE_PYTHON` points at a non-existent file. |
| *"179D calculator timed out after Ns"* | Raise `BUILDING_ENERGY_SURROGATE_TIMEOUT`. |
| Property skipped | Its building type or HVAC system is outside the supported set (§5), or required inputs are missing. Check the analysis messages. |
| Result columns don't show on the grid | Create a column-list profile named `179D` for the org and re-open the view. |

---

## 9. Extending

- **New surrogate models:** add another runner/model behind the same
  out-of-process pattern and branch inside `_build_property_info` / `_run_calculator`;
  the pipeline name is deliberately generic.
- **New inputs:** extend the portal field constants / `ADVANCED_INPUT_FIELDS` and
  the default profile; add `OVERRIDE_FIELDS` entries for direct `extra_data`
  overrides.
- **Tax schedule updates:** edit `TAX_POLICY_BY_YEAR` and keep
  `TestBuildingEnergySurrogateTaxPolicy` green (`pytest seed/tests/test_analysis_pipelines.py -k TaxPolicy`).
