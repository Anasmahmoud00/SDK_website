# Retry Terraform apply until A1.Flex capacity is available (OCI "Out of host capacity").
# Run from repo root: .\terraform\scripts\retry-apply-a1.ps1
# Or from terraform folder: .\scripts\retry-apply-a1.ps1
#
# Before running:
# - In terraform.tfvars set: instance_shape = "VM.Standard.A1.Flex", availability_domain_index = 0 (or 1, 2), instance_ocpus = 1, instance_memory_in_gbs = 6
# - This will CREATE an instance if you have none, or REPLACE existing instance (destroy + create). Use only when you accept that.

$ErrorActionPreference = "Stop"
$terraformDir = $PSScriptRoot + "\.."
$maxHours = 24
$intervalSeconds = 300   # 5 minutes
$maxAttempts = [int](($maxHours * 3600) / $intervalSeconds)
$attempt = 0

Write-Host "Retrying 'terraform apply -auto-approve' every $($intervalSeconds/60) minutes for up to $maxHours hours (max $maxAttempts attempts)."
Write-Host "Ensure terraform.tfvars has instance_shape = VM.Standard.A1.Flex. Press Ctrl+C to stop."
Write-Host ""

Push-Location $terraformDir
try {
    while ($attempt -lt $maxAttempts) {
        $attempt++
        Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Attempt $attempt / $maxAttempts ..."
        $p = Start-Process -FilePath "terraform" -ArgumentList "apply", "-auto-approve" -NoNewWindow -Wait -PassThru
        if ($p.ExitCode -eq 0) {
            Write-Host "SUCCESS. Instance created. Update OCI_INSTANCE_IP in GitHub secrets with the new public IP."
            exit 0
        }
        if ($attempt -lt $maxAttempts) {
            Write-Host "Apply failed (exit code $($p.ExitCode)). Waiting $($intervalSeconds) seconds before retry."
            Start-Sleep -Seconds $intervalSeconds
        }
    }
    Write-Host "Reached max attempts. Try again later or upgrade to Pay As You Go for priority capacity."
    exit 1
} finally {
    Pop-Location
}
