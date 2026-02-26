$AccountId = (aws sts get-caller-identity --query Account --output text)
$Region = "us-east-1"
$RepoName = "cognive-lambda-repo"
$RepoUrl = "$AccountId.dkr.ecr.$Region.amazonaws.com/$RepoName"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Building Docker images in parallel..." -ForegroundColor Cyan

$builds = @(
    @{ Tag = "cognive-lambda";     File = "Dockerfile" },
    @{ Tag = "cognive-authorizer"; File = "Dockerfile.authorizer" }
)

$buildJobs = $builds | ForEach-Object {
    $tag  = $_.Tag
    $file = $_.File
    Start-Job -ScriptBlock {
        Set-Location $using:ScriptDir
        $output = docker build --provenance=false --platform linux/amd64 -t "$using:RepoUrl`:$using:tag" -f $using:file . 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Build failed for $using:tag`n$output"
        }
        $output
    }
}

Write-Host "Waiting for builds to complete..." -ForegroundColor Yellow
$buildJobs | Wait-Job | ForEach-Object {
    $job = $_
    if ($job.State -eq "Failed") {
        Write-Error ($job | Receive-Job 2>&1)
        $buildJobs | Remove-Job -Force
        exit 1
    }
    Receive-Job $job
}
$buildJobs | Remove-Job -Force

Write-Host "All images built successfully." -ForegroundColor Green

Write-Host "Logging into ECR..." -ForegroundColor Cyan
aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $RepoUrl

if ($LASTEXITCODE -ne 0) {
    Write-Error "ECR login failed"
    exit 1
}

Write-Host "Pushing images in parallel..." -ForegroundColor Cyan

$pushJobs = $builds | ForEach-Object {
    $tag = $_.Tag
    Start-Job -ScriptBlock {
        $output = docker push "$using:RepoUrl`:$using:tag" 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Push failed for $using:tag`n$output"
        }
        $output
    }
}

Write-Host "Waiting for pushes to complete..." -ForegroundColor Yellow
$pushJobs | Wait-Job | ForEach-Object {
    $job = $_
    if ($job.State -eq "Failed") {
        Write-Error ($job | Receive-Job 2>&1)
        $pushJobs | Remove-Job -Force
        exit 1
    }
    Receive-Job $job
}
$pushJobs | Remove-Job -Force

Write-Host "Done! All images pushed to ECR." -ForegroundColor Green