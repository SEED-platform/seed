# SEED API Test Script
# This script helps you get started with the SEED API

Write-Host "🔧 SEED API Setup Script" -ForegroundColor Green
Write-Host "=========================" -ForegroundColor Green

# Get JWT Token
Write-Host "`n1. Getting JWT Token..." -ForegroundColor Yellow
$tokenResponse = Invoke-RestMethod -Uri "http://localhost/api/token/" -Method POST -ContentType "application/json" -Body '{"username": "user@seed-platform.org", "password": "super-secret-password"}'

$token = $tokenResponse.access
Write-Host "✅ Token obtained successfully!" -ForegroundColor Green
Write-Host "Token: $($token.Substring(0, 20))..." -ForegroundColor Cyan

# Test Health Check
Write-Host "`n2. Testing Health Check..." -ForegroundColor Yellow
$healthResponse = Invoke-RestMethod -Uri "http://localhost/api/health_check/" -Method GET
Write-Host "✅ Health Check: $($healthResponse.status)" -ForegroundColor Green

# Get Organizations
Write-Host "`n3. Getting Organizations..." -ForegroundColor Yellow
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

$orgsResponse = Invoke-RestMethod -Uri "http://localhost/api/v3/organizations/" -Method GET -Headers $headers
Write-Host "✅ Found $($orgsResponse.results.Count) organization(s)" -ForegroundColor Green

if ($orgsResponse.results.Count -gt 0) {
    $orgId = $orgsResponse.results[0].id
    Write-Host "First Organization ID: $orgId" -ForegroundColor Cyan
}

# Get Cycles
Write-Host "`n4. Getting Cycles..." -ForegroundColor Yellow
$cyclesResponse = Invoke-RestMethod -Uri "http://localhost/api/v3/cycles/" -Method GET -Headers $headers
Write-Host "✅ Found $($cyclesResponse.results.Count) cycle(s)" -ForegroundColor Green

if ($cyclesResponse.results.Count -gt 0) {
    $cycleId = $cyclesResponse.results[0].id
    Write-Host "First Cycle ID: $cycleId" -ForegroundColor Cyan
}

# Test Analysis Stats
if ($orgId -and $cycleId) {
    Write-Host "`n5. Testing Analysis Stats..." -ForegroundColor Yellow
    try {
        $statsResponse = Invoke-RestMethod -Uri "http://localhost/api/v4/analyses/stats/?cycle_id=$cycleId" -Method GET -Headers $headers
        Write-Host "✅ Analysis Stats: $($statsResponse.total_records) records found" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Analysis Stats failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`n🎉 Setup Complete!" -ForegroundColor Green
Write-Host "Use these values in Postman:" -ForegroundColor Yellow
Write-Host "BASE_URL: http://localhost" -ForegroundColor Cyan
Write-Host "TOKEN: $token" -ForegroundColor Cyan
Write-Host "ORGANIZATION_ID: $orgId" -ForegroundColor Cyan
Write-Host "CYCLE_ID: $cycleId" -ForegroundColor Cyan 