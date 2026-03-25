param(
    [string]$VarFile = "terraform.tfvars"
)

$ErrorActionPreference = "Stop"

function Resolve-TerraformBin {
    $cmd = Get-Command terraform -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $fallback = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages\Hashicorp.Terraform_Microsoft.Winget.Source_8wekyb3d8bbwe\terraform.exe"
    if (Test-Path $fallback) { return $fallback }

    throw "terraform executable not found. Install Terraform or add it to PATH."
}

function Import-AwsEnvFromBackendEnv {
    param(
        [string]$EnvFilePath
    )

    if (-not (Test-Path $EnvFilePath)) { return }

    $targetKeys = @(
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_REGION",
        "AWS_DEFAULT_REGION"
    )

    foreach ($line in Get-Content $EnvFilePath) {
        $trimmed = $line.Trim()
        if ($trimmed -eq "" -or $trimmed.StartsWith("#")) { continue }
        if ($trimmed -notmatch "^[A-Za-z_][A-Za-z0-9_]*=") { continue }

        $pair = $trimmed -split "=", 2
        $key = $pair[0]
        $value = if ($pair.Length -gt 1) { $pair[1] } else { "" }
        if ($targetKeys -contains $key) {
            [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$tfDir = Join-Path $repoRoot "terraform"
$tfVarPath = Join-Path $tfDir $VarFile
$backendEnvPath = Join-Path $repoRoot "backend\.env"
$terraform = Resolve-TerraformBin

if (-not (Test-Path $tfVarPath)) {
    throw "Var file not found: $tfVarPath (copy terraform/terraform.tfvars.example -> terraform/terraform.tfvars)"
}

Import-AwsEnvFromBackendEnv -EnvFilePath $backendEnvPath

Push-Location $tfDir
try {
    & $terraform -version | Out-Null
    & $terraform init -upgrade
    & $terraform plan -var-file $VarFile -out tfplan
    & $terraform apply -auto-approve tfplan
    & $terraform output
}
finally {
    Pop-Location
}
