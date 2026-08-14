#!/usr/bin/env bash
#
# Builds, pushes, and optionally deploys Lambda images.
#
#   ./scripts/build-and-push.sh worker --deploy   # build and ship, one step
#   ./scripts/build-and-push.sh worker            # build only, prints digests
#   ./scripts/build-and-push.sh --deploy          # all three images
#   ./scripts/build-and-push.sh api authorizer
#
# Prefer --deploy. Building and deploying as separate commands means copying a
# sha256 by hand between them, and forgetting the second half leaves a change
# that looks shipped but is not running anywhere.
#
# Three images share one ECR repository, separated by tag prefix:
#
#   api-*         AppSync resolvers + FastAPI webhook surface  (api/Dockerfile)
#   authorizer-*  Clerk JWT verification            (api/Dockerfile.authorizer)
#   worker-*      LangGraph agent, SQS-driven       (backend/Dockerfile.worker)
#
# Terraform wants digests, never mutable tags: a tag can be repointed after a
# deploy, a digest cannot, which is what makes a rollback mean anything.
#
# This replaces build-and-push.ps1, which cannot authenticate on Windows.
# PowerShell 5.1 mangles `aws ecr get-login-password | docker login
# --password-stdin`, and ECR rejects the result with 400 Bad Request. The same
# pipe works correctly under bash. Naming the images to build also matters in
# practice: only one of the three usually changes, and rebuilding all of them
# to ship a worker fix wastes several minutes.

set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
REPOSITORY_NAME="${ECR_REPOSITORY:-relaywise-lambda-repo}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_TAG="$(date -u +%Y%m%d%H%M%S)"

# Note the lack of an `exit` here: this runs inside $(...), so exiting would
# only kill the subshell and the build would carry on with a bad name. Unknown
# images are rejected up front instead, in the main shell.
dockerfile_for() {
  case "$1" in
    api)        echo "api/Dockerfile api" ;;
    authorizer) echo "api/Dockerfile.authorizer api" ;;
    worker)     echo "backend/Dockerfile.worker backend" ;;
  esac
}

usage() {
  sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
}

DEPLOY=false
TARGETS=()
for arg in "$@"; do
  case "$arg" in
    --deploy)      DEPLOY=true ;;
    -h|--help)     usage; exit 0 ;;
    api|authorizer|worker) TARGETS+=("$arg") ;;
    *)
      echo "unknown argument: $arg" >&2
      echo >&2
      usage >&2
      exit 2
      ;;
  esac
done
[ ${#TARGETS[@]} -gt 0 ] || TARGETS=(api authorizer worker)

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
REGISTRY_URL="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
REPOSITORY_URL="$REGISTRY_URL/$REPOSITORY_NAME"

aws ecr describe-repositories \
  --repository-names "$REPOSITORY_NAME" --region "$REGION" >/dev/null

echo "Publishing to $REPOSITORY_URL"
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$REGISTRY_URL"

declare -a APPLY_ARGS=()

for name in "${TARGETS[@]}"; do
  read -r dockerfile context <<<"$(dockerfile_for "$name")"
  tag="$name-$IMAGE_TAG"
  tagged="$REPOSITORY_URL:$tag"

  echo
  echo "Building $name"

  # --platform because Lambda runs linux/amd64 whatever the build host is.
  # --provenance=false keeps the manifest single-arch, which Lambda requires.
  docker build --pull --provenance=false --platform linux/amd64 \
    --file "$REPO_ROOT/$dockerfile" \
    --tag "$tagged" \
    "$REPO_ROOT/$context"

  docker push "$tagged"

  digest="$(aws ecr describe-images \
    --repository-name "$REPOSITORY_NAME" \
    --image-ids "imageTag=$tag" --region "$REGION" \
    --query "imageDetails[0].imageDigest" --output text)"

  case "$digest" in
    sha256:*) ;;
    *) echo "could not resolve digest for $name" >&2; exit 1 ;;
  esac

  case "$name" in
    api)        APPLY_ARGS+=(--api "$REPOSITORY_URL@$digest") ;;
    authorizer) APPLY_ARGS+=(--authorizer "$REPOSITORY_URL@$digest") ;;
    worker)     APPLY_ARGS+=(--worker "$REPOSITORY_URL@$digest") ;;
  esac
done

echo

if [ "$DEPLOY" = true ]; then
  exec "$REPO_ROOT/scripts/apply-infra.sh" --apply "${APPLY_ARGS[@]}"
fi

# Printing the command and trusting a human to run it is how an image gets
# built and then never deployed — the change looks shipped, the running code
# is unchanged, and the next person debugs the wrong version. Use --deploy.
echo "Published, NOT deployed. Ship it with:"
echo
echo "  ./scripts/build-and-push.sh ${TARGETS[*]} --deploy"
echo
echo "or apply these digests on their own:"
echo
echo "  ./scripts/apply-infra.sh --apply ${APPLY_ARGS[*]}"
