# AGI PROCESOR changes and attribution

AGI PROCESOR is a modified distribution of OpenJarvis. OpenJarvis is available
at <https://github.com/open-jarvis/OpenJarvis> under the Apache License 2.0.

This file records the main classes of changes made by the AGI PROCESOR project:

- product-facing names, assistant identity, UI copy, and desktop metadata;
- an educational market-risk analysis module;
- a local paper-trading ledger;
- a non-transactional alert subsystem with explicit WATCH, CAUTION, and AVOID
  states, atomic local persistence, cooldown/deduplication, and explicitly
  confirmed delivery adapters for email, Telegram, ntfy, and optional SMS
  gateways;
- a disclosed affiliate call-to-action;
- removal of the inherited giveaway prompt and automatic leaderboard sharing;
- external browser analytics disabled unless the operator explicitly builds
  with `VITE_AGI_ENABLE_EXTERNAL_ANALYTICS=true`;
- inherited desktop and CLI update paths disabled so an upstream OpenJarvis
  release cannot replace the AGI PROCESOR fork;
- documentation and tests for the additions above.

The inherited OpenJarvis leaderboard UI is also disabled by default. Restoring
it requires both configured upstream credentials and the explicit build flag
`VITE_AGI_ENABLE_OPENJARVIS_LEADERBOARD=true`. Local performance measurements
remain separate and stay on the device.

If an operator deliberately enables external browser analytics, the inherited
default receiver is the OpenJarvis team's PostHog service. The UI discloses
that receiver before any manually exposed opt-in control can be used.

The MVP temporarily retains inherited upstream application icon artwork while
original AGI PROCESOR icons are prepared. The icons are compatibility assets,
not a claim of upstream endorsement, and should be replaced before a public
branded release.

Automatic update checks and self-update commands are intentionally unavailable.
Updates must be reviewed and installed from the trusted AGI PROCESOR repository;
the upstream `openjarvis` package on PyPI is not an update source for this fork.

The internal `openjarvis` package, compatibility identifiers, and `jarvis` CLI
are intentionally retained. This minimizes unnecessary divergence and makes it
possible to incorporate upstream security updates.

AGI PROCESOR is independent of OpenJarvis, Stanford University, and Fomo Labs.
No endorsement or partnership is implied. "AGI PROCESOR" is a product name and
does not assert that the software has achieved artificial general intelligence.

Modified text and source files carry an AGI PROCESOR modification notice near
the beginning of the file. Newly created files carry a corresponding creation
notice. Formats that do not allow comments, such as Tauri JSON configuration,
state the modified-distribution status in a user-facing metadata field. Git
history provides the detailed line-by-line change record.

The original Apache License remains in `LICENSE` and applies subject to its
terms. Existing copyright, patent, trademark, and attribution notices are
retained. Upstream names that remain in package namespaces, compatibility
identifiers, citations, or attribution are not presented as endorsements.
