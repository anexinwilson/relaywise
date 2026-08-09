param(
    [string]$Region = "us-east-1",
    [string]$RepositoryName = "cognive-lambda-repo",
    [string]$ImageTag = (Get-Date).ToUniversalTime().ToString("yyyyMMddHHmmss")
)

$ErrorActionPreference = "Stop"
$AccountId = aws sts get-caller-identity --query Account --output text
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($AccountId)) {
    throw "Unable to resolve the active AWS account."
}

$RegistryUrl = "$AccountId.dkr.ecr.$Region.amazonaws.com"
$RepositoryUrl = "$RegistryUrl/$RepositoryName"
$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path

aws ecr describe-repositories `
    --repository-names $RepositoryName `
    --region $Region `
    --output json | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "ECR repository '$RepositoryName' does not exist in account $AccountId ($Region)."
}

Write-Host "Deploying Cognive Lambda images to AWS account $AccountId in $Region." -ForegroundColor Cyan

aws ecr get-login-password --region $Region |
    docker login --username AWS --password-stdin $RegistryUrl
if ($LASTEXITCODE -ne 0) {
    throw "ECR login failed."
}

$Images = @(
    @{
        Name       = "lambda"
        Dockerfile = "Dockerfile"
        Tag        = "cognive-lambda-$ImageTag"
    },
    @{
        Name       = "authorizer"
        Dockerfile = "Dockerfile.authorizer"
        Tag        = "cognive-authorizer-$ImageTag"
    }
)

$Results = @{}

foreach ($Image in $Images) {
    $TaggedUri = "$RepositoryUrl`:$($Image.Tag)"
    Write-Host "Building $($Image.Name) image..." -ForegroundColor Cyan

    docker build `
        --pull `
        --provenance=false `
        --platform linux/amd64 `
        --file (Join-Path $ScriptDirectory $Image.Dockerfile) `
        --tag $TaggedUri `
        $ScriptDirectory
    if ($LASTEXITCODE -ne 0) {
        throw "Docker build failed for $($Image.Name)."
    }

    docker push $TaggedUri
    if ($LASTEXITCODE -ne 0) {
        throw "Docker push failed for $($Image.Name)."
    }

    $Digest = aws ecr describe-images `
        --repository-name $RepositoryName `
        --image-ids "imageTag=$($Image.Tag)" `
        --region $Region `
        --query "imageDetails[0].imageDigest" `
        --output text
    if ($LASTEXITCODE -ne 0 -or $Digest -notmatch '^sha256:[0-9a-f]{64}$') {
        throw "Unable to resolve the ECR digest for $($Image.Name)."
    }

    $Results[$Image.Name] = "$RepositoryUrl@$Digest"
}

Write-Host "Lambda images published successfully." -ForegroundColor Green
Write-Output "lambda_image_uri=$($Results.lambda)"
Write-Output "authorizer_image_uri=$($Results.authorizer)"
