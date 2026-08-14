<#
.SYNOPSIS
    Builds and pushes all three Relaywise Lambda images, then prints their
    digest-pinned URIs for `terraform apply`.

.DESCRIPTION
    Three images share one ECR repository, distinguished by tag prefix:

      api-*         AppSync resolvers + FastAPI webhook surface   (api/Dockerfile)
      authorizer-*  Clerk JWT verification                        (api/Dockerfile.authorizer)
      worker-*      LangGraph agent, SQS-driven                   (backend/Dockerfile.worker)

    Terraform requires digest-pinned URIs, never mutable tags: a tag can be
    repointed after a deploy, a digest cannot, so this is what makes a rollback
    mean something.

.EXAMPLE
    ./scripts/build-and-push.ps1
    ./scripts/build-and-push.ps1 -Region us-east-1 -RepositoryName relaywise-lambda-repo
#>

param(
    [string]$Region = "us-east-1",
    [string]$RepositoryName = "relaywise-lambda-repo",
    [string]$ImageTag = (Get-Date).ToUniversalTime().ToString("yyyyMMddHHmmss")
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

$AccountId = aws sts get-caller-identity --query Account --output text
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($AccountId)) {
    throw "Unable to resolve the active AWS account. Run 'aws configure' first."
}

$RegistryUrl = "$AccountId.dkr.ecr.$Region.amazonaws.com"
$RepositoryUrl = "$RegistryUrl/$RepositoryName"

aws ecr describe-repositories --repository-names $RepositoryName --region $Region --output json | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "ECR repository '$RepositoryName' does not exist. Apply terraform/api with deployment_phase=bootstrap first."
}

Write-Host "Publishing Relaywise images to $RepositoryUrl" -ForegroundColor Cyan

aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $RegistryUrl
if ($LASTEXITCODE -ne 0) { throw "ECR login failed." }

$Images = @(
    @{ Name = "api";        Dockerfile = "api/Dockerfile";            Context = "api" }
    @{ Name = "authorizer"; Dockerfile = "api/Dockerfile.authorizer"; Context = "api" }
    @{ Name = "worker";     Dockerfile = "backend/Dockerfile.worker"; Context = "backend" }
)

$Results = @{}

foreach ($Image in $Images) {
    $Tag = "$($Image.Name)-$ImageTag"
    $TaggedUri = "$RepositoryUrl`:$Tag"

    Write-Host "`nBuilding $($Image.Name)..." -ForegroundColor Cyan

    # --platform is required: Lambda runs linux/amd64 regardless of build host.
    # --provenance=false keeps the manifest single-arch, which Lambda requires.
    docker build --pull --provenance=false --platform linux/amd64 `
        --file (Join-Path $RepoRoot $Image.Dockerfile) `
        --tag $TaggedUri `
        (Join-Path $RepoRoot $Image.Context)
    if ($LASTEXITCODE -ne 0) { throw "Build failed for $($Image.Name)." }

    docker push $TaggedUri
    if ($LASTEXITCODE -ne 0) { throw "Push failed for $($Image.Name)." }

    $Digest = aws ecr describe-images --repository-name $RepositoryName `
        --image-ids "imageTag=$Tag" --region $Region `
        --query "imageDetails[0].imageDigest" --output text
    if ($LASTEXITCODE -ne 0 -or $Digest -notmatch '^sha256:[0-9a-f]{64}$') {
        throw "Could not resolve the ECR digest for $($Image.Name)."
    }

    $Results[$Image.Name] = "$RepositoryUrl@$Digest"
}

Write-Host "`nAll images published.`n" -ForegroundColor Green
Write-Host "Apply with:" -ForegroundColor Cyan
Write-Host "  cd terraform/api"
Write-Host "  terraform apply ``"
Write-Host "    -var deployment_phase=complete ``"
Write-Host "    -var lambda_image_uri=$($Results.api) ``"
Write-Host "    -var authorizer_image_uri=$($Results.authorizer) ``"
Write-Host "    -var worker_image_uri=$($Results.worker)"
