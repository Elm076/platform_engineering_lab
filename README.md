# DevFest Jaén 2026: "¿Qué pasará conmigo como dev después de la IA? Transición de dev a ingeniero de plataforma con nube + IaC"

## Speaker

- Marcos Manuel Ortega - Indavelopers
- Consultant, architect & trainer - 14 years of experience
- Google Cloud, data/Gemini, Pulumi, finOps
- Google Cloud Authorized Trainer
- [Google Developer Expert in Google Cloud](https://drive.google.com/file/d/1SSB5_mPqR6RmTjyXCkndzRCLp9PTgHEf/view?usp=sharing)
- Puluminary
- Former community organizer: GDG Almería, GDG Cloud Español, DataBeers ALM, Club Python Almería, Hacklab Almería, etc.
- Contact:
  - Email: <info@indavelopers.com>
  - LinkedIn: [linkedin.com/in/marcosmanuelortega](https://www.linkedin.com/in/marcosmanuelortega/)
  - GitHub: [github.com/Indavelopers](https://github.com/Indavelopers)
- Made with ❤️ from Almería, Spain

## Session

- QR to LinkedIn pub: <https://bit.ly/devfestjaen-platformengineer>
- [DevFest Jaén 2026 (21/Nov/26)](https://gdg-jaen.netlify.app)

## Contents

1. Platform engineering as a career step up after agentic AI takes our coding jobs and dooms us all.
1. Platform engineering is mainly done via IaC.
1. New alternatives for IaC available: Python & coding languages vs HCL, Pulumi vs Terraform.
1. Developers can leverage their previous coding experience for platform engineering / IaC.

## Quick start

Want to run this demo on your own Google Cloud project? See the complete [Local & GCP setup guide](SETUP.md).

## Demo progression (clickOps → golden path platform)

This repository uses a single root `Pulumi.yaml` Pulumi project pointing to sequential folders under `steps/` (`main: steps/XX_...`). Switching that line in `Pulumi.yaml` preserves continuous IaC state while keeping every step clean and readable.

| Step | Folder | Platform Engineering Concept |
| :---: | :--- | :--- |
| 0 | [`steps/00_clickops_baseline`](steps/00_clickops_baseline/) | FastAPI JSON API deployed to Cloud Run via clickOps (pre-provisioned with `scripts/setup_clickops.sh`) |
| 1 | [`steps/01_iac_intro`](steps/01_iac_intro/) | First IaC resources in Python (GCS bucket + seed JSON file) + HCL vs. Python comparison |
| 2 | [`steps/02_secrets_lifecycle`](steps/02_secrets_lifecycle/) | IaC CRUD workflow, surgical diffs, and idempotency using Secret Manager |
| 3 | [`steps/03_import_clickops`](steps/03_import_clickops/) | Brownfield adoption: importing existing Cloud Run + Artifact Registry into IaC |
| 4 | [`steps/04_app_cicd`](steps/04_app_cicd/) | Early automation: FastAPI `pytest` unit tests + Cloud Build CI/CD pipeline (`ci/cloudbuild.yaml`) |
| 5 | [`steps/05_multi_env`](steps/05_multi_env/) | Multi-env delivery (`prod` + `dev` stacks) + 2 CI/CD targets |
| 6 | [`steps/06_iac_unit_tests`](steps/06_iac_unit_tests/) | Testing infrastructure (`pytest` + Pulumi mocks w/ 2 planted bugs) |
| 7 | [`steps/07_devsecops_iam`](steps/07_devsecops_iam/) | DevSecOps: replace default Compute Engine SA with dedicated least-privilege IAM per app |
| 8 | [`steps/08_finops_sre_guardrails`](steps/08_finops_sre_guardrails/) | finOps labels/caps + Cloud Monitoring alert policy + Python Policy-as-Code (`policy/`) |
| 9 | [`steps/09_golden_path`](steps/09_golden_path/) | Reusable "golden path" (`PlatformService` ComponentResource + zero-downtime aliases) + 2nd app live |

### Repository structure

```text
.
├── Pulumi.yaml                # Single project; switch `main:` to advance steps
├── Pulumi.prod.yaml           # Production stack config
├── Pulumi.dev.yaml            # Development stack config (step 5 onwards)
├── requirements.txt           # Shared Python dependencies (.venv)
├── SETUP.md                   # GCP project setup, CLI install, auth & cleanup guide
├── app/                       # FastAPI JSON API, Dockerfile & pytest suite
├── ci/cloudbuild.yaml         # Cloud Build app pipeline (pytest → build → push → deploy)
├── policy/                    # Python Policy-as-Code pack (finOps, EU region, security)
├── scripts/                   # setup_clickops.sh, deploy_app.sh, cleanup.sh
└── steps/                     # Progressive step folders 00-09
```

## License

CC BY 4.0 (see `LICENSE.md`).
