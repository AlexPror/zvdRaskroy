# Simple Git Push Script
Write-Host "Push to GitHub..." -ForegroundColor Cyan

# Step 1: Rename README
if (Test-Path "README_NEW.md") {
    Move-Item README_NEW.md README.md -Force
    Write-Host "README renamed" -ForegroundColor Green
}

# Step 2: Init Git
if (-not (Test-Path ".git")) {
    git init
    Write-Host "Git initialized" -ForegroundColor Green
}

# Step 3: Add remote
$remoteCheck = git remote get-url origin 2>&1
if ($LASTEXITCODE -ne 0) {
    git remote add origin https://github.com/AlexPror/zvdRaskroy.git
    Write-Host "Remote added" -ForegroundColor Green
}

# Step 4: Branch main
git branch -M main
Write-Host "Branch main" -ForegroundColor Green

# Step 5: Add files
git add .
Write-Host "Files added" -ForegroundColor Green

# Step 6: Commit
git commit -m "v2.0: MVP - programa optimalnogo raskroya"
Write-Host "Committed" -ForegroundColor Green

# Step 7: Push
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "SUCCESS!" -ForegroundColor Green
    Write-Host "https://github.com/AlexPror/zvdRaskroy" -ForegroundColor Cyan
} else {
    Write-Host "ERROR! Check authentication" -ForegroundColor Red
}

pause

