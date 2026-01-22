$AccountId = (aws sts get-caller-identity --query Account --output text)
$Region = "us-east-1"
$RepoName = "cognive-lambda-repo"
$RepoUrl = "$AccountId.dkr.ecr.$Region.amazonaws.com/$RepoName"

Write-Host "Building Docker image..." -ForegroundColor Cyan
docker build --provenance=false --platform linux/amd64 -t "$RepoUrl`:latest" .

if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker build failed"
    exit 1
}

Write-Host "Logging into ECR..." -ForegroundColor Cyan
aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $RepoUrl

if ($LASTEXITCODE -ne 0) {
    Write-Error "ECR login failed"
    exit 1
}

Write-Host "Pushing to ECR..." -ForegroundColor Cyan
docker push "$RepoUrl`:latest"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker push failed"
    exit 1
}

Write-Host "Done! Image pushed to: $RepoUrl`:latest" -ForegroundColor Green