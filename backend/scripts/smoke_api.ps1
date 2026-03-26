param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

$suffix = Get-Date -Format "yyyyMMddHHmmss"
$loginId = "smoke$suffix"
$email = "smoke_$suffix@example.com"
$password = "SmokePass!90"
$displayName = "Smoke User"

Write-Host "0) Register"
$register = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/auth/register" -ContentType "application/json" -Body (@{
    loginId = $loginId
    email = $email
    password = $password
    displayName = $displayName
} | ConvertTo-Json)
Write-Host "userId=$($register.userId) loginId=$($register.loginId) contractVersion=$($register.contractVersion)"

Write-Host "1) Login"
$login = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/auth/login" -ContentType "application/json" -Body (@{
    loginId = $loginId
    password = $password
} | ConvertTo-Json)
$accessToken = $login.accessToken
$refreshToken = $login.refreshToken
Write-Host "loginUser=$($login.user.loginId) contractVersion=$($login.contractVersion)"

$authHeader = @{
    Authorization = "Bearer $accessToken"
}

Write-Host "2) Me"
$me = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/users/me" -Headers $authHeader
Write-Host "meLoginId=$($me.loginId) role=$($me.role) contractVersion=$($me.contractVersion)"

Write-Host "3) Upload image URL issue(stub)"
$upload = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/uploads/images" -ContentType "application/json" -Body (@{
    contentType = "image/png"
    fileName = "architecture-sketch.png"
} | ConvertTo-Json)
Write-Host "fileId=$($upload.fileId) url=$($upload.url) contractVersion=$($upload.contractVersion)"

Write-Host "4) Create project"
$project = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/projects" -Headers $authHeader -ContentType "application/json" -Body (@{
    name = "smoke-project-$suffix"
    description = "pipeline smoke v2"
} | ConvertTo-Json)
$projectId = $project.projectId
Write-Host "projectId=$projectId ownerId=$($project.ownerId) contractVersion=$($project.contractVersion)"

Write-Host "5) Create session"
$session = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/projects/$projectId/sessions" -Headers $authHeader -ContentType "application/json" -Body (@{
    inputType = "TEXT"
    inputText = "Build private infra with 1 EC2 and 1 MySQL RDS in ap-northeast-2"
} | ConvertTo-Json)
$sessionId = $session.sessionId
Write-Host "sessionId=$sessionId status=$($session.status) contractVersion=$($session.contractVersion)"

Write-Host "6) Patch status"
$patched = Invoke-RestMethod -Method Patch -Uri "$BaseUrl/api/sessions/$sessionId/status" -Headers $authHeader -ContentType "application/json" -Body (@{
    status = "ANALYZING"
    errorCode = $null
    errorMessage = $null
} | ConvertTo-Json)
Write-Host "patchedStatus=$($patched.status) contractVersion=$($patched.contractVersion)"

Write-Host "7) Save architecture"
$archBody = @{
    schemaVersion = "v1"
    architectureJson = @{
        vpc = $true
        ec2 = @{
            count = 1
            instance_type = "t3.micro"
        }
        rds = @{
            enabled = $true
            engine = "mysql"
        }
        bedrock = @{
            enabled = $false
            model = $null
        }
        additional_services = @("alb", "cloudwatch")
        usage = @{
            monthly_hours = 730
            data_transfer_gb = 120
            storage_gb = 80
            requests_million = 10
        }
        public = $false
        region = "ap-northeast-2"
    }
} | ConvertTo-Json -Depth 10
$arch = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/sessions/$sessionId/architecture" -Headers $authHeader -ContentType "application/json" -Body $archBody
Write-Host "architectureStatus=$($arch.status) contractVersion=$($arch.contractVersion)"

Write-Host "8) Generate terraform"
$terraform = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/sessions/$sessionId/terraform" -Headers $authHeader
Write-Host "terraformStatus=$($terraform.status) validation=$($terraform.validationStatus) contractVersion=$($terraform.contractVersion)"

Write-Host "9) Calculate cost"
$cost = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/sessions/$sessionId/cost" -Headers $authHeader
Write-Host "costStatus=$($cost.status) monthlyTotal=$($cost.monthlyTotal) contractVersion=$($cost.contractVersion)"

Write-Host "10) Create second session for compare"
$session2 = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/projects/$projectId/sessions" -Headers $authHeader -ContentType "application/json" -Body (@{
    inputType = "TEXT"
    inputText = "Build private infra with 2 EC2 and 1 MySQL RDS in ap-northeast-2"
} | ConvertTo-Json)
$sessionId2 = $session2.sessionId
Write-Host "session2Id=$sessionId2 versionNo=$($session2.versionNo)"

Write-Host "11) Save architecture for second session"
$archBody2 = @"
{
  "schemaVersion": "v1",
  "architectureJson": {
    "vpc": true,
    "ec2": {
      "count": 2,
      "instance_type": "t3.micro"
    },
    "rds": {
      "enabled": true,
      "engine": "mysql"
    },
    "bedrock": {
      "enabled": false,
      "model": null
    },
    "additional_services": ["alb"],
    "usage": {
      "monthly_hours": 730,
      "data_transfer_gb": 200,
      "storage_gb": 100,
      "requests_million": 20
    },
    "public": false,
    "region": "ap-northeast-2"
  }
}
"@
$arch2 = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/sessions/$sessionId2/architecture" -Headers $authHeader -ContentType "application/json" -Body $archBody2
Write-Host "architecture2Status=$($arch2.status)"

Write-Host "12) Generate terraform and cost for second session"
$terraform2 = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/sessions/$sessionId2/terraform" -Headers $authHeader
$cost2 = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/sessions/$sessionId2/cost" -Headers $authHeader
Write-Host "terraform2Status=$($terraform2.status) cost2Total=$($cost2.monthlyTotal)"

Write-Host "13) Compare sessions"
$compare = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/sessions/$sessionId2/compare" -Headers $authHeader
Write-Host "compareBaseVersion=$($compare.baseSession.versionNo) compareTargetVersion=$($compare.targetSession.versionNo) jsonDiffCount=$($compare.jsonDiff.Count)"

Write-Host "14) Get detail"
$detail = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/sessions/$sessionId2" -Headers $authHeader
Write-Host "detailStatus=$($detail.status) hasArchitecture=$($null -ne $detail.architecture) hasTerraform=$($null -ne $detail.terraform) hasCost=$($null -ne $detail.cost) contractVersion=$($detail.contractVersion)"

Write-Host "15) Logout"
$logout = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/auth/logout" -ContentType "application/json" -Body (@{
    refreshToken = $refreshToken
} | ConvertTo-Json)
Write-Host "logoutSuccess=$($logout.success) contractVersion=$($logout.contractVersion)"

Write-Host "DONE"
