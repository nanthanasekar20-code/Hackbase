# Quick end-to-end smoke test for the auth + favorites API.
# Run this from the backend folder while `uvicorn app.main:app --reload`
# is running in another terminal:
#     .\test_auth_flow.ps1

$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:8000/api/v1"

Write-Host "`n=== Register ===" -ForegroundColor Cyan
$registerBody = @{ email = "you@example.com"; password = "testpassword123"; full_name = "Nandy" } | ConvertTo-Json
try {
    $user = Invoke-RestMethod -Uri "$base/auth/register" -Method Post -Body $registerBody -ContentType "application/json"
    $user | Format-List
} catch {
    Write-Host "Register failed (probably already registered from a previous run — that's fine, continuing):" -ForegroundColor Yellow
    Write-Host $_.Exception.Message
}

Write-Host "`n=== Login ===" -ForegroundColor Cyan
$loginBody = @{ email = "you@example.com"; password = "testpassword123" } | ConvertTo-Json
$login = Invoke-RestMethod -Uri "$base/auth/login" -Method Post -Body $loginBody -ContentType "application/json"
$headers = @{ Authorization = "Bearer $($login.access_token)" }
Write-Host "Got token: $($login.access_token.Substring(0,20))..."

Write-Host "`n=== Me ===" -ForegroundColor Cyan
Invoke-RestMethod -Uri "$base/auth/me" -Headers $headers | Format-List

Write-Host "`n=== Add favorite ===" -ForegroundColor Cyan
$favBody = @{ problem_id = "sih:sih25001" } | ConvertTo-Json
Invoke-RestMethod -Uri "$base/favorites" -Method Post -Body $favBody -ContentType "application/json" -Headers $headers | Format-List

Write-Host "`n=== List favorites ===" -ForegroundColor Cyan
Invoke-RestMethod -Uri "$base/favorites" -Headers $headers | Format-Table problem_id, title, domain -AutoSize

Write-Host "`n=== Unauthenticated /me (should fail with 401) ===" -ForegroundColor Cyan
try {
    Invoke-RestMethod -Uri "$base/auth/me"
    Write-Host "UNEXPECTED: this should have failed!" -ForegroundColor Red
} catch {
    Write-Host "Correctly rejected: $($_.Exception.Response.StatusCode)" -ForegroundColor Green
}

Write-Host "`nDone." -ForegroundColor Cyan
