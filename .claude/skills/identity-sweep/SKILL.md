---
name: identity-sweep
description: Report which idfkit touchpoints are behind the latest identity tag, with their stated lag or none. Use when the maintainer asks who is behind on the identity, whether every host has adopted a tag, or to run the identity sweep. Runs idfkit-brand/tools/sweep_touchpoints.py over the local checkouts; changes no file and opens no issue.
---

# identity-sweep

The answer to "who is behind". Run by the maintainer, never on a schedule (research R3): the sweep
reads every touchpoint's declared identity level from its own checkout in the workspace, compares
it with the latest `identity-YYYY.N` tag of this repository, and reports. The per-touchpoint check
(`check-touchpoint.yml`) answers a different question, "does this touchpoint render what it
claims", and never compares against the latest.

## Steps

1. From the workspace root (the directory the repositories are siblings under), run:

   ```bash
   python idfkit-brand/tools/sweep_touchpoints.py --workspace .
   ```

   The script reads `touchpoints.toml` from this checkout, the latest tag from `git tag` here, each
   touchpoint's declaration from where `declared_at` says, and the Lag beside it. It writes
   `sweep-report.json` in the workspace and prints one line per touchpoint.

2. Report the table in the conversation, one row per touchpoint: its id, its declared tag, the
   latest tag, and its status:

   | Status | Meaning |
   | ------ | ------- |
   | `current` | declares the latest tag |
   | `lagging (deliberate: reason)` or `lagging (not-yet: issue)` | behind, with a stated Lag (FR-006) |
   | `unexplained` | a host behind, or undeclared, with no Lag: the one failure the sweep has |
   | `behind` | a README behind; not a failure, since a README adopts a tag by changing three addresses |
   | `unreachable` | no checkout in the workspace; not a failure, and not a pass |

3. Name the touchpoints to bump: every `unexplained` one first, then the `lagging` ones whose
   reason has expired, then the `behind` READMEs. For each, the next step is the `identity-adopt`
   skill with the touchpoint and the latest tag.

4. Change nothing. The sweep reports; adoption is a pull request in the touchpoint's repository,
   and a Lag is written beside the touchpoint's own declaration, never in the roster.

## Exit codes

`0` nothing unexplained; `1` at least one host is behind without a Lag; `2` the roster or the tags
could not be read, which is never a pass.
