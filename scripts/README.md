# scripts

Repeatable repository tooling. One-off probes and diagnostics belong in the
git-ignored `tests/` directory instead.

| Script | Purpose |
| --- | --- |
| `build-and-push.sh` | Builds and pushes Lambda images, prints the deploy command |
| `apply-infra.sh` | Applies `terraform/api` against digest-pinned images, defaulting to the ones already deployed |
| `build-and-push.ps1` | Superseded by `build-and-push.sh`; cannot authenticate to ECR on Windows |
| `apps_catalog.py` | Regenerates `frontend/src/apps_catalog.json` from the Composio toolkit list |

## build-and-push.sh

```bash
./scripts/build-and-push.sh worker --deploy   # build and ship, one step
./scripts/build-and-push.sh worker            # build only, prints digests
./scripts/build-and-push.sh --deploy          # all three images
```

Use `--deploy`. Without it the script only prints digests, and a build that is
never deployed looks shipped while the old code keeps running — which has
already cost real debugging time here.

Name the images you actually changed. Only one of the three usually moves, and
rebuilding all of them to ship a worker fix costs several minutes for nothing.

The PowerShell version is kept only for reference. PowerShell 5.1 corrupts
`aws ecr get-login-password | docker login --password-stdin`, and ECR answers
400 Bad Request; the identical pipe works under bash.

## apply-infra.sh

```bash
./scripts/apply-infra.sh                      # plan only
./scripts/apply-infra.sh --apply              # plan, then apply
./scripts/apply-infra.sh --apply --worker <uri> --api <uri> --authorizer <uri>
```

Images default to whatever is currently deployed, so a configuration change
reconciles configuration and moves no code. Pass the flags — with the URIs
`build-and-push.ps1` prints — only when you mean to ship new images.

The default exists because the manual copy of three `sha256` URIs was enough
friction to invite `aws lambda update-function-configuration` instead, and a
laptop-local `COMPOSIO_CACHE_DIR` reached production that way. Terraform never
saw the change; the agent worker then failed at import on every invocation.

## apps_catalog.py

Run rarely — only when Composio adds toolkits worth surfacing in the
integrations UI. The generated JSON is committed, so the frontend has no
runtime dependency on this script.

```bash
pip install -r requirements.txt
python apps_catalog.py
```

It still calls `bedrock-runtime` to summarise descriptions, which predates the
move to Mantle. Harmless because it runs locally and offline from the
application, but worth porting if it is ever run again.
