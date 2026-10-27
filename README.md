# Healthcare RCM — Python + Playwright Test Automation

![Tests](https://github.com/kpravinsqa/playwright-python-healthcare-rcm/actions/workflows/tests.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![Playwright](https://img.shields.io/badge/playwright-python-2EAD33) ![Domain](https://img.shields.io/badge/domain-US%20Healthcare%20RCM-0f6e6e)

UI and API automation for a **US-healthcare Revenue Cycle Management (RCM)** application, modelled on the provider-side
workflows I tested on the **HeartBeats MD** project: patient registration, provider onboarding with **NPI check-digit
validation**, encounter capture with **CPT / ICD-10** coding, the **provider dashboard**, claim scrubbing and submission,
and payment posting.

> **Confidentiality note:** original portfolio work. **No PHI, proprietary code, data or screens.** All patients and
> providers are fictitious, and the system under test is a mock app in `mock_app/` that reproduces the domain rules.

## Highlights

* **Role-based access testing**: Admin, Front Desk and Provider personas, with menu visibility, direct-URL denial and API `403`s
* **Healthcare validation rules**: NPI Luhn check digit (`80840` prefix), ICD-10-CM format, CPT fee schedule, timely filing (365 days)
* **Boundary value analysis**: NPI 9/10/11 digits, phone 9/10/11 digits, DOB vs. 120-year limit, timely-filing day 365 vs. 366
* **Defect regression guards** (`-m defect`): the *NPI boundary-value cluster* and *encounter info missing from provider dashboard* defects
* **Hybrid tests**: arrange data through the API, assert through the UI, for fast and stable end-to-end checks
* **Page Object Model**, data-driven JSON, synthetic data factory, parallel execution, and GitHub Actions CI with HTML reports

## Coverage (79 automated checks)

| Suite | Module | Key scenarios |
|---|---|---|
| TS-01 | Login & roles | per-role landing page, invalid login, required fields, menu by role, direct-URL access denied, logout |
| TS-02 | Patient registration | insured / self-pay, 10 field-validation rules, duplicate detection (name + DOB, case-insensitive), MRN/name search |
| TS-03 | Providers & NPI | inline NPI validation (7 data sets), add provider, bad check digit, duplicate NPI |
| TS-04 | Encounters | multi-line charges, live total recalculation, DOS future / before DOB, ICD-10 format, mandatory dx + CPT |
| TS-05 | Provider dashboard | new encounter visible with dx, CPT, charge and KPIs; provider sees only own encounters |
| TS-06 | Claims | create → submit, self-pay scrub rejection, timely filing boundary, partial → full payment, overpayment blocked |
| API | REST | NPI endpoint, MRN generation, 401/403, fee-schedule math, line validation, dashboard summary, duplicate claim, payment rules |

## Getting started

```bash
git clone https://github.com/kpravinsqa/playwright-python-healthcare-rcm.git
cd playwright-python-healthcare-rcm
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium

pytest                 # everything + reports/report.html
pytest -m smoke        # critical path
pytest -m defect       # production-defect regression guards
pytest -n auto         # parallel
```

Run the app yourself: `python -m mock_app.server`, then open http://127.0.0.1:8000
(`billing_admin`, `front_desk` or `dr_smith`, password `Health@123`).

## Project structure

```
api/          RcmClient service object
config/       settings (env overridable)
mock_app/     system under test (stdlib server + HTML/JS)
pages/        Page Objects: login, patients, providers, encounters, dashboard, claims
test_data/    npi.json, patients.json (invalid inputs, ICD-10 samples)
tests/ui      browser tests     tests/api   REST tests
utils/        data_factory (synthetic patients), data_loader, logger
```

## Author

**Pravin Khedkar**, QA Lead / SDET · [@kpravinsqa](https://github.com/kpravinsqa)
