---
name: identity-adopt
description: Bring one idfkit touchpoint (a web host or a public README) to an identity-YYYY.N tag of idfkit-brand. Use when the maintainer asks to adopt, bump, or move a touchpoint to an identity tag, or to vendor the identity derivation into a repository. Builds the tag locally, copies dist/ into the vendored paths, moves the declaration and the check workflow's ref, runs the check, and opens the pull request.
---

# identity-adopt

Adoption is a procedure, not a script (contracts/identity-standard.md section 5). Given a
touchpoint id from `touchpoints.toml` and a tag, follow the six steps below in order and stop on
any failure. Nothing is downloaded: the tag's `dist` is rebuilt from this checkout, and the check
compares the vendored bytes against it. Write nowhere a step does not name.

Invocation: "adopt `<tag>` in `<touchpoint>`", for example "adopt identity-2026.1 in developers".
Paths below are from the workspace root, where the repositories are siblings.

## 1. Read the roster entry

Open `idfkit-brand/touchpoints.toml` and find the `[[touchpoint]]` whose `id` matches. Note its
`kind`, `repository`, `host`, `mechanisms`, `declared_at`, `vendored`, `identity_bearing` and
`notes`. The `notes` field carries what is particular to this touchpoint: where it serves the host
directory, what else must be copied, which placement keeps its own build rules. Read it before
copying anything. The touchpoint's checkout is the folder named after the repository, except
`idfkit/idfkit-app`, which is `envelop/`, and `idfkit/.github`, which is `idfkit-org/`.

For a `readme` touchpoint, skip to step 7.

A repository may hold both a host touchpoint and a README touchpoint. Move them together, on one
branch: the check reads the header's addresses as the same declaration, so a host at the new tag
fails assertions 2 and 5 until step 7 has also run on its README.

## 2. Build the tag in this checkout

```bash
cd idfkit-brand
git fetch --tags origin
git checkout "<tag>"
python build.py --out dist --tag "<tag>"
git checkout -
```

Rasters built here may differ in bytes from the ones CI attached to the release; the check compares
rasters by decoded pixels, so that is expected. Everything else is byte-identical by construction.

## 3. Copy the derivations into the vendored paths

For each mechanism in the entry's `mechanisms`, copy `idfkit-brand/dist/<mechanism>/` into the
vendored location, and copy `idfkit-brand/dist/hosts/<host>/` beside it, replacing what is there
and deleting what the tag no longer produces. The vendored location is the entry's `vendored`
path: where that path is a container (`docs/identity/`, `src/identity/`, `identity/`), each
mechanism lands in a subdirectory of its own name (`docs/identity/material/`,
`docs/identity/hosts/developers.idfkit.com/`); where the vendored paths name the mechanisms
themselves (`brand/css/`, `brand/hero/`, `brand/hosts/`, `brand/brand-page/` on the marketing
site), each lands in its own path.

Then apply the entry's `notes`:

- **idfkit.com** serves `brand/hosts/idfkit.com/` at `/brand/hosts/idfkit.com/`: rewrite the
  paths in the copied `head.html` to that prefix (the check normalises the prefix when comparing).
  Copy `brand/brand-page/index.html` to `brand/index.html` so that `/brand/` resolves; the two
  stay identical.
- **The Material sites** keep the derivation under `docs/identity/` so the site builds from `docs/`
  and `mkdocs.yml` alone; exclude the directory from formatting hooks as the other vendored trees
  are.
- **The applications** (`envelop/`, `idfkit-auth/`) copy the favicon set from the vendored
  `hosts/<host>/` into `public/` as well, since Vite serves `public/` at the root.

Edit nothing inside a vendored directory. A vendored file is served as the tag wrote it.

## 4. Move the declaration and the check's ref

Set the value at `declared_at` to the tag:

| Form | Where | What |
| ---- | ----- | ---- |
| `toml-key` | `pyproject.toml` | `[tool.idfkit.identity] level = "<tag>"` |
| `json-pointer` | `package.json` or `brand/identity.json` | `"idfkit": {"identity": "<tag>"}` or `{"level": "<tag>"}` |

Remove any `lag` or `identityLag` beside it, since the touchpoint is no longer behind. In the
touchpoint's `.github/workflows/check-identity.yml`, set both the `uses:` ref and the input to the
same tag:

```yaml
jobs:
  identity:
    uses: idfkit/idfkit-brand/.github/workflows/check-touchpoint.yml@<tag>
    with:
      identity_level: <tag>
```

Create the workflow with exactly that job if the touchpoint has none yet.

## 5. Run the check against the local dist

From the workspace root:

```bash
python idfkit-brand/tools/check_touchpoint.py --root <touchpoint> --level <tag> --dist idfkit-brand/dist
```

Every finding names a file and a place. Stop on any finding: a byte that differs is a vendored file
that was edited or not copied (step 3); a stray literal is an identity value the touchpoint's own
file still carries and must read through a property instead; a declaration mismatch is step 4. Do
not change a vendored file to make the check pass; fix the touchpoint, or fix the standard and cut
a new tag.

## 6. Commit on a branch and open the pull request

Run the touchpoint's own gate first (`make check && make test`, or `npm run lint && npm run
test:run`, as its CLAUDE.md says). Then commit on a branch named `identity-<tag>` and open a pull
request whose body lists the vendored paths replaced and the tag moved from and to, with a
changelog entry where the repository keeps one. Nothing is pushed to a default branch.

## 7. A README touchpoint

A README vendors nothing: its declaration is the tag inside the three image addresses of its header
(contracts/readme-header.md section 1). Steps 2 to 4 are one edit: rewrite the tag in every
`https://raw.githubusercontent.com/idfkit/idfkit-brand/<old-tag>/marks/` address of the header to the
new tag, leaving the file names as they are. Then run assertion 5 against the rewritten file:

```bash
python idfkit-brand/tools/check_touchpoint.py --root <touchpoint> --level <tag> --kind readme
```

and continue at step 6.

A repository may hold several README entries, its root README and one per package it publishes
(`readme_kind = "package"`, section 7 of that contract). They move together, because the check runs
over all of them. A package README is the file at the entry's `declared_at.path`. Where a generator
writes it, as `scripts/emit-types.mjs` does in `idfkit-js`, change the generator and regenerate. A
private repository has package entries only: its root README stays outside until it is public.
