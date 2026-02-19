# Environment and configuration

**.env** is reserved for **secrets only**. Nothing other than secrets (passwords, API keys, tokens) belongs in `.env`. Do not put ports, hostnames, feature flags, or other non-secret settings in `.env`.

**config.yaml** holds **all other options, variables, and settings**: ports, hostnames, deployment environment, feature flags, database host/user/name (but not passwords), and any non-secret configuration. Application code and deployment scripts read `config.yaml` for behavior; they read `.env` only for secrets.

Copy templates from `templates/.env.template` and `templates/.config.template` to the repo root as `.env` and `config.yaml`. Never commit `.env` or `config.yaml`; both are gitignored.
