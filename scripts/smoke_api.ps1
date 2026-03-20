param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

Write-Host "1) Create project"
$project = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/projects" -ContentType "application/json" -Body (@{
    name = "smoke-project"
    description = "pipeline smoke"
} | ConvertTo-Json)
$projectId = $project.projectId
Write-Host "projectId=$projectId"

Write-Host "2) Create session"
$session = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/projects/$projectId/sessions" -ContentType "application/json" -Body (@{
    inputType = "TEXT"
    inputText = "서울 리전에 EC2 2개 mysql rds 퍼블릭"
} | ConvertTo-Json)
$sessionId = $session.sessionId
Write-Host "sessionId=$sessionId status=$($session.status)"

Write-Host "3) Analyze"
$analyze = Invoke-RestMethod -Method Post -Uri "$BaseUrl/sessions/$sessionId/analyze" -ContentType "application/json" -Body (@{
    input_text = "서울 리전에 EC2 2개 mysql rds 퍼블릭"
} | ConvertTo-Json)
Write-Host "analyzeStatus=$($analyze.status)"

Write-Host "4) Generate terraform"
$terraform = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/sessions/$sessionId/terraform"
Write-Host "terraformStatus=$($terraform.status) validation=$($terraform.validationStatus)"

Write-Host "5) Calculate cost"
$cost = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/sessions/$sessionId/cost"
Write-Host "costStatus=$($cost.status) monthlyTotal=$($cost.monthlyTotal)"

Write-Host "6) Get detail"
$detail = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/sessions/$sessionId"
Write-Host "detailStatus=$($detail.status) hasArchitecture=$($null -ne $detail.architecture) hasTerraform=$($null -ne $detail.terraform) hasCost=$($null -ne $detail.cost)"

Write-Host "7) List sessions in project"
$list = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/projects/$projectId/sessions"
Write-Host "sessionsCount=$($list.Count) latestStatus=$($list[0].status)"

