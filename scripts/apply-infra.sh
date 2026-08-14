#!/usr/bin/env bash
#
# Applies terraform/api against digest-pinned Lambda images.
#
#   ./scripts/apply-infra.sh                  # plan only
#   ./scripts/apply-infra.sh --apply          # plan, then apply
#   ./scripts/apply-infra.sh --apply \
#       --worker <uri> --api <uri> --authorizer <uri>
#
# Terraform demands a digest-pinned URI for each of the three functions, and
# build-and-push.ps1 stops at printing them. Copying three sha256 URIs by hand
# on every run is how a laptop-local value ended up as COMPOSIO_CACHE_DIR in
# production: the manual step invites shortcuts like `aws lambda
# update-function-configuration`, which Terraform does not know about.
#
# So the images default to WHAT IS ALREADY DEPLOYED. A configuration change
# then reconciles config and nothing else — no rebuild, no code moving. Pass
# the flags explicitly (with the output of build-and-push.ps1) when you do
# intend to ship new images.

set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STACK="$REPO_ROOT/terraform/api"

APPLY=false
WORKER_URI=""
API_URI=""
AUTHORIZER_URI=""

while [ $# -gt 0 ]; do
  case "$1" in
    --apply)       APPLY=true ;;
    --worker)      WORKER_URI="$2"; shift ;;
    --api)         API_URI="$2"; shift ;;
    --authorizer)  AUTHORIZER_URI="$2"; shift ;;
    -h|--help)     sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)             echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

# The URI currently live on a function, so an unspecified image means "leave
# this one exactly where it is".
deployed_image() {
  aws lambda get-function \
    --function-name "$1" \
    --region "$REGION" \
    --query "Code.ImageUri" \
    --output text
}

require_digest() {
  case "$2" in
    *@sha256:*) ;;
    *) echo "$1 is not digest-pinned: $2" >&2; exit 1 ;;
  esac
}

[ -n "$WORKER_URI" ]      || WORKER_URI="$(deployed_image relaywise-agent-worker)"
[ -n "$API_URI" ]         || API_URI="$(deployed_image relaywise-api)"
[ -n "$AUTHORIZER_URI" ]  || AUTHORIZER_URI="$(deployed_image relaywise-authorizer)"

require_digest worker "$WORKER_URI"
require_digest api "$API_URI"
require_digest authorizer "$AUTHORIZER_URI"

cd "$STACK"

terraform plan -out=tfplan \
  -var "worker_image_uri=$WORKER_URI" \
  -var "lambda_image_uri=$API_URI" \
  -var "authorizer_image_uri=$AUTHORIZER_URI"

if [ "$APPLY" != true ]; then
  echo
  echo "Plan only. Re-run with --apply to execute it."
  rm -f tfplan
  exit 0
fi

# Applying the saved plan, not re-planning: what you reviewed above is exactly
# what runs, even if something changed in AWS in between.
terraform apply tfplan
rm -f tfplan
