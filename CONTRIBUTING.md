# Contributing

Thanks for helping improve AI Briefing Agent.

## Setup

```bash
python -m venv venv
venv\Scripts\activate            # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env             # Windows: copy .env.example .env
```

## Before you open a pull request

```bash
ruff check .
python -m pytest tests -q --cov=app --cov-fail-under=80
```

CI runs the same two commands on every push and pull request.

## Rules

- **Tests run offline.** Fake every external service (LLM, SMTP, Telegram, feeds, YouTube) by injecting it. A test that needs the internet or an API key will not be merged.
- **Never commit secrets** (`.env`, API keys, tokens, database files).
- **Schema changes need a migration.** Add a script under `migrations/versions/` and a test that upgrades from the previous revision.
- **Prompts treat retrieved text as data**, never as instructions.
- **Changing ranking, dedup or prompts?** Run `python -m evals.run_eval` before and after and put both scores in the pull request.
- Keep pull requests small and describe what changed and why.

## Reporting security problems

Please do not open a public issue for a vulnerability. Contact the maintainer privately through the email on their GitHub profile.