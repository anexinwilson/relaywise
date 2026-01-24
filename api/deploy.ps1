$AccountId = (aws sts get-caller-identity --query Account --output text)
$Region = "us-east-1"
$RepoName = "cognive-lambda-repo"
$RepoUrl = "$AccountId.dkr.ecr.$Region.amazonaws.com/$RepoName"

Write-Host "Building Docker images..." -ForegroundColor Cyan
docker build --no-cache --provenance=false --platform linux/amd64 -t "$RepoUrl`:cognive-lambda" -f Dockerfile .
docker build --no-cache --provenance=false --platform linux/amd64 -t "$RepoUrl`:cognive-authorizer" -f Dockerfile.authorizer .
docker build --no-cache --provenance=false --platform linux/amd64 -t "$RepoUrl`:cognive-token-manager" -f Dockerfile.token-manager .

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

Write-Host "Pushing images to ECR..." -ForegroundColor Cyan
docker push "$RepoUrl`:cognive-lambda"
docker push "$RepoUrl`:cognive-authorizer"
docker push "$RepoUrl`:cognive-token-manager"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker push failed"
    exit 1
}

Write-Host "Done! Images pushed to ECR" -ForegroundColor Green