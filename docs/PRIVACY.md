# Privacy Principles and Data Handling

OpenVitals is designed around a single, non-negotiable idea:

> **Your health data belongs to you.**

This document explains how OpenVitals approaches privacy, data ownership, and regulatory responsibility. It is written to be clear, direct, and honest rather than legalistic. It applies to both self-hosted deployments and any future managed or hosted offerings.

---

## Core Privacy Principles

OpenVitals is built on the following principles:

1. **User Ownership** – Individuals own and control their health data at all times.
2. **Local-First by Default** – Self-hosted deployments keep data entirely under the user’s control.
3. **No Implicit Sharing** – Data is never shared, sold, or reused without explicit user consent.
4. **Minimum Necessary Access** – The platform only accesses data required to function.
5. **Defense-in-Depth** – Systems are designed so that data is of limited value if compromised.

These principles guide both current development and all future architectural decisions.

---

## Self-Hosted Deployments

In a self-hosted deployment:

* All wearable health data is stored on infrastructure controlled by the user.
* OpenVitals does not transmit data to any third party by default.
* No telemetry, analytics, or usage data is sent back to the project or its maintainers unless explicitly enabled by the user.
* The OpenVitals maintainers do not have access to self-hosted data.

In this mode, users are fully responsible for their own data security, backups, and access controls.

---

## Managed / Hosted Deployments (Future)

OpenVitals may offer a managed hosting option in the future for users who prefer not to operate their own infrastructure.

If and when such a service is offered, the following commitments apply:

* Data will never be shared with third parties without explicit, opt-in user consent.
* Health data will not be sold, monetized, or used for advertising.
* Data will not be used for research, analytics, or model training without clear, affirmative permission from the user.
* Operational access to data will be limited strictly to what is required to maintain system reliability and security.

Where possible, OpenVitals will favor designs that **avoid storing direct personal identifiers** (such as names, emails, or account-level identity) alongside health datasets.

---

## De-Identification and Data Minimization

OpenVitals is intentionally designed to support architectures where:

* Health datasets can be stored separately from personal identity information.
* Internal identifiers are random, opaque, and non-derivable.
* Personal identifiers can be removed or rotated without destroying analytical value.

The goal is that, in the event of a security incident, any exposed datasets would be **functionally useless without external context**, reducing harm to users.

---

## Consent and Data Sharing

OpenVitals does **not** share data by default.

Any future features that enable:

* research participation
* data donation
* collaborative analytics

will be **explicitly opt-in**, clearly explained, and revocable by the user at any time.

There will be no dark patterns, default enrollment, or implicit consent mechanisms.

---

## Health Data and Regulatory Considerations

Wearable health data may qualify as **Protected Health Information (PHI)** under certain jurisdictions and usage contexts.

OpenVitals takes the following stance:

* Health data is treated as sensitive by default, regardless of whether a specific regulation applies.
* The project is designed to meet or exceed common privacy expectations found in healthcare regulations.
* Managed services, if offered, will be operated with the assumption that health data requires heightened safeguards.

This document is not a legal guarantee of compliance with any specific regulation. Users and organizations remain responsible for understanding and complying with applicable laws in their jurisdiction.

---

## What OpenVitals Does *Not* Do

To be explicit, OpenVitals does not:

* Sell user data
* Share user data with advertisers
* Use health data for targeted marketing
* Collect hidden analytics on user behavior
* Claim ownership over user data

---

## Transparency and Change Management

Privacy commitments are only meaningful if they are stable and visible.

* Any material changes to this privacy policy will be documented and versioned.
* Changes that affect user data handling will be communicated clearly.
* Users will always retain the ability to export and remove their data.

---

## Questions and Contact

If you have questions about privacy, data handling, or security assumptions, please open an issue or contact the project maintainers.

OpenVitals is committed to earning trust through transparency, not through fine print.
