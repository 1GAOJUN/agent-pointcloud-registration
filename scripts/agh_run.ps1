[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$PromptFile,

    [string]$RunLabel = "agh_run",
    [string]$OutputRoot,
    [string]$Profile = "local-dev",
    [string]$Model,
    [string]$AghEntry,
    [string]$AghHome,
    [string]$PermissionPolicy,
    [ValidateSet("policy")]
    [string]$PermissionMode = "policy"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$aghRoot = "D:\STUDY\darker\agnes-harness"
$promptPath = [System.IO.Path]::GetFullPath($PromptFile)

if (-not (Test-Path -LiteralPath $promptPath -PathType Leaf)) {
    throw "Prompt file not found: $promptPath"
}
if (-not $OutputRoot) {
    $OutputRoot = Join-Path $projectRoot "outputs\development\headless_agh"
}
$OutputRoot = [System.IO.Path]::GetFullPath($OutputRoot)

# Permission is a mandatory, versioned project input. Validate it before starting AGH.
if (-not $PermissionPolicy) {
    $PermissionPolicy = Join-Path $projectRoot "configs\agh_headless_permissions.json"
}
$permissionPolicyPath = [System.IO.Path]::GetFullPath($PermissionPolicy)
if (-not (Test-Path -LiteralPath $permissionPolicyPath -PathType Leaf)) {
    throw "Headless permission policy not found (fail closed): $permissionPolicyPath"
}
try {
    $policy = Get-Content -LiteralPath $permissionPolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    throw "Headless permission policy is invalid JSON (fail closed): $permissionPolicyPath"
}
if ($policy.schema -ne "agh-headless-permissions/v1" -or -not $policy.agh_preset) {
    throw "Unsupported or incomplete headless permission policy (fail closed): $permissionPolicyPath"
}
if (-not $policy.enforcement -or -not $policy.enforcement.preset_source -or -not $policy.enforcement.preset_sha256 `
    -or -not $policy.enforcement.profile_source -or -not $policy.enforcement.profile_sha256) {
    throw "Permission policy lacks enforcement source/hash (fail closed): $permissionPolicyPath"
}
$presetSource = [System.IO.Path]::GetFullPath([string]$policy.enforcement.preset_source)
if (-not (Test-Path -LiteralPath $presetSource -PathType Leaf)) {
    throw "Permission preset source not found (fail closed): $presetSource"
}
$expectedPresetHash = ([string]$policy.enforcement.preset_sha256).ToLowerInvariant()
$actualPresetHash = (Get-FileHash -LiteralPath $presetSource -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualPresetHash -ne $expectedPresetHash) {
    throw "Permission preset hash mismatch (fail closed): expected $expectedPresetHash, got $actualPresetHash"
}
$permissionPolicyHash = (Get-FileHash -LiteralPath $permissionPolicyPath -Algorithm SHA256).Hash.ToLowerInvariant()
$aghPreset = [string]$policy.agh_preset
$profileSource = [System.IO.Path]::GetFullPath([string]$policy.enforcement.profile_source)
if (-not (Test-Path -LiteralPath $profileSource -PathType Leaf)) {
    throw "Permission profile source not found (fail closed): $profileSource"
}
$expectedProfileHash = ([string]$policy.enforcement.profile_sha256).ToLowerInvariant()
$actualProfileHash = (Get-FileHash -LiteralPath $profileSource -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualProfileHash -ne $expectedProfileHash) {
    throw "Permission profile source hash mismatch (fail closed): expected $expectedProfileHash, got $actualProfileHash"
}
$effectiveAghHome = if ($AghHome) { [System.IO.Path]::GetFullPath($AghHome) } else { Join-Path $env:USERPROFILE ".agh" }
$deployedProfile = Join-Path $effectiveAghHome "profiles\$Profile\profile.yaml"
if (-not (Test-Path -LiteralPath $deployedProfile -PathType Leaf)) {
    throw "Audited permission profile is not deployed (fail closed): $deployedProfile"
}
$deployedProfileHash = (Get-FileHash -LiteralPath $deployedProfile -Algorithm SHA256).Hash.ToLowerInvariant()
if ($deployedProfileHash -ne $expectedProfileHash) {
    throw "Deployed permission profile hash mismatch (fail closed): expected $expectedProfileHash, got $deployedProfileHash"
}

if (-not $AghEntry) {
    $candidate = Get-ChildItem -LiteralPath (Join-Path $aghRoot "packages\cli\dist") -Directory |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "agnes.mjs") } |
        Sort-Object Name -Descending |
        Select-Object -First 1
    if (-not $candidate) {
        throw "No built AGH CLI entry found under $aghRoot\packages\cli\dist"
    }
    $AghEntry = Join-Path $candidate.FullName "agnes.mjs"
}
$AghEntry = [System.IO.Path]::GetFullPath($AghEntry)
if (-not (Test-Path -LiteralPath $AghEntry -PathType Leaf)) {
    throw "AGH CLI entry not found: $AghEntry"
}

$safeLabel = ($RunLabel -replace '[^A-Za-z0-9._-]', '_').Trim('_')
if (-not $safeLabel) { $safeLabel = "agh_run" }
$timestamp = Get-Date -Format "yyyyMMdd_HHmmssfff"
$evidenceRunId = "${safeLabel}_${timestamp}"
$runDirectory = Join-Path $OutputRoot $evidenceRunId
New-Item -ItemType Directory -Path $runDirectory -Force | Out-Null
Copy-Item -LiteralPath $promptPath -Destination (Join-Path $runDirectory "prompt_snapshot.md")
Copy-Item -LiteralPath $permissionPolicyPath -Destination (Join-Path $runDirectory "permission_policy_snapshot.json")

function Write-JsonFile {
    param([string]$Path, [object]$Value)
    $json = $Value | ConvertTo-Json -Depth 12
    [System.IO.File]::WriteAllText($Path, $json + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
}

function Quote-ProcessArgument {
    param([string]$Value)
    if ($Value -notmatch '[\s"]') { return $Value }
    return '"' + (($Value -replace '(\\*)"', '$1$1\"') -replace '(\\+)$', '$1$1') + '"'
}

function Invoke-CapturedProcess {
    param(
        [string]$Executable,
        [string[]]$ArgumentList,
        [string]$WorkingDirectory,
        [AllowEmptyString()][string]$StandardInput = "",
        [hashtable]$Environment = @{}
    )

    $start = [System.Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $Executable
    $start.Arguments = (($ArgumentList | ForEach-Object { Quote-ProcessArgument $_ }) -join ' ')
    $start.WorkingDirectory = $WorkingDirectory
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardInput = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    foreach ($key in $Environment.Keys) {
        $start.EnvironmentVariables[$key] = [string]$Environment[$key]
    }

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $start
    if (-not $process.Start()) { throw "Failed to start: $Executable" }
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    if ($StandardInput) {
        $inputBytes = [System.Text.UTF8Encoding]::new($false).GetBytes($StandardInput)
        $process.StandardInput.BaseStream.Write($inputBytes, 0, $inputBytes.Length)
    }
    $process.StandardInput.Close()
    $process.WaitForExit()
    return [pscustomobject]@{
        ExitCode = $process.ExitCode
        Stdout = $stdoutTask.GetAwaiter().GetResult()
        Stderr = $stderrTask.GetAwaiter().GetResult()
        Arguments = $start.Arguments
    }
}

$childEnvironment = @{}
if ($AghHome) {
    $childEnvironment["AGH_HOME"] = [System.IO.Path]::GetFullPath($AghHome)
}

$prompt = [System.IO.File]::ReadAllText($promptPath)
$aghArguments = @($AghEntry, "-p", "--mode", "json", "--profile", $Profile, "--preset", $aghPreset, "--cwd", $projectRoot)
if ($Model) { $aghArguments += @("--model", $Model) }

$invocationStarted = (Get-Date).ToUniversalTime().ToString("o")
Write-JsonFile (Join-Path $runDirectory "invocation.json") ([ordered]@{
    schema = "devx-agh-invocation/v1"
    evidence_run_id = $evidenceRunId
    started_at_utc = $invocationStarted
    launcher = $PSCommandPath
    prompt_source = $promptPath
    prompt_snapshot = "prompt_snapshot.md"
    workspace = $projectRoot
    output_directory = $runDirectory
    agh_entry = $AghEntry
    profile = $Profile
    model_override = $(if ($Model) { $Model } else { "PROFILE_DEFAULT" })
    permission_mode = $PermissionMode
    permission_policy = $permissionPolicyPath
    permission_policy_sha256 = $permissionPolicyHash
    permission_policy_snapshot = "permission_policy_snapshot.json"
    agh_preset = $aghPreset
    agh_preset_source = $presetSource
    agh_preset_sha256 = $actualPresetHash
    profile_source = $profileSource
    profile_sha256 = $actualProfileHash
    deployed_profile = $deployedProfile
    agh_home_override = $(if ($AghHome) { [System.IO.Path]::GetFullPath($AghHome) } else { "NOT_SET" })
    command = @("node") + $aghArguments
    prompt_transport = "stdin"
})
Write-JsonFile (Join-Path $runDirectory "permission_policy.json") ([ordered]@{
    schema = "devx-permission-policy-evidence/v1"
    source = $permissionPolicyPath
    snapshot = "permission_policy_snapshot.json"
    sha256 = $permissionPolicyHash
    agh_preset = $aghPreset
    preset_source = $presetSource
    preset_sha256 = $actualPresetHash
    profile_source = $profileSource
    profile_sha256 = $actualProfileHash
    deployed_profile = $deployedProfile
    validation = "PASS"
    behavior = "fail-closed"
})

$nodeVersion = (& node --version 2>&1 | Out-String).Trim()
$cliVersion = (& node $AghEntry --version 2>&1 | Out-String).Trim()
Write-JsonFile (Join-Path $runDirectory "environment.json") ([ordered]@{
    schema = "devx-agh-environment/v1"
    captured_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    computer_name = $env:COMPUTERNAME
    os_version = [System.Environment]::OSVersion.VersionString
    powershell_version = $PSVersionTable.PSVersion.ToString()
    node_version = $nodeVersion
    agh_cli_version = $cliVersion
    agh_entry = $AghEntry
    agh_entry_sha256 = (Get-FileHash -LiteralPath $AghEntry -Algorithm SHA256).Hash.ToLowerInvariant()
    workspace = $projectRoot
    profile = $Profile
    permission_mode = $PermissionMode
    permission_policy_sha256 = $permissionPolicyHash
    agh_preset = $aghPreset
    agh_preset_sha256 = $actualPresetHash
    permission_profile_sha256 = $actualProfileHash
    permission_note = "AGH approval.command_policy is selected explicitly with --preset; unmatched approval requests fail closed."
})

$result = $null
$launcherError = $null
try {
    $result = Invoke-CapturedProcess -Executable "node" -ArgumentList $aghArguments `
        -WorkingDirectory $projectRoot -StandardInput $prompt -Environment $childEnvironment
} catch {
    $launcherError = $_.Exception.Message
    $result = [pscustomobject]@{ ExitCode = 2; Stdout = ""; Stderr = $launcherError; Arguments = "" }
}

[System.IO.File]::WriteAllText((Join-Path $runDirectory "stdout.log"), $result.Stdout, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText((Join-Path $runDirectory "stderr.log"), $result.Stderr, [System.Text.UTF8Encoding]::new($false))

$resultRecord = $null
foreach ($line in @($result.Stdout -split "`r?`n")) {
    if (-not $line.Trim()) { continue }
    try {
        $candidate = $line | ConvertFrom-Json
        if ($candidate.v -eq "agnes-cli-result/v1") { $resultRecord = $candidate }
    } catch {
        # stdout is retained verbatim; non-JSON lines are not reinterpreted.
    }
}

$sessionId = if ($resultRecord -and $resultRecord.sessionId) { [string]$resultRecord.sessionId } else { $null }
Write-JsonFile (Join-Path $runDirectory "agh_identifiers.json") ([ordered]@{
    schema = "devx-agh-identifiers/v1"
    session_id = $(if ($sessionId) { $sessionId } else { "NOT_AVAILABLE" })
    task_id = "NOT_AVAILABLE"
    native_run_id = "NOT_AVAILABLE"
    evidence_run_id = $evidenceRunId
    source = $(if ($sessionId) { "agnes-cli-result/v1 stdout" } else { "NOT_AVAILABLE" })
})

$nativeExport = [ordered]@{
    availability = "NOT_AVAILABLE"
    format = "agnes"
    path = "NOT_AVAILABLE"
    exit_code = "NOT_AVAILABLE"
    note = "No AGH session identifier was returned."
}
if ($sessionId) {
    $exportPath = Join-Path $runDirectory "agh_session_export.jsonl"
    $exportArguments = @($AghEntry, "export", $sessionId, "--format", "agnes", "--out", $exportPath, "--profile", $Profile)
    $exportResult = Invoke-CapturedProcess -Executable "node" -ArgumentList $exportArguments `
        -WorkingDirectory $projectRoot -Environment $childEnvironment
    [System.IO.File]::WriteAllText((Join-Path $runDirectory "export_stdout.log"), $exportResult.Stdout, [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText((Join-Path $runDirectory "export_stderr.log"), $exportResult.Stderr, [System.Text.UTF8Encoding]::new($false))
    Write-JsonFile (Join-Path $runDirectory "export_status.json") ([ordered]@{
        exit_code = $exportResult.ExitCode
        completed_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    })
    if ($exportResult.ExitCode -eq 0 -and (Test-Path -LiteralPath $exportPath -PathType Leaf)) {
        $nativeExport.availability = "AVAILABLE"
        $nativeExport.path = "agh_session_export.jsonl"
        $nativeExport.exit_code = 0
        $nativeExport.note = "AGH-native event/session export; default redaction retained."
    } else {
        $nativeExport.exit_code = $exportResult.ExitCode
        $nativeExport.note = "AGH export command failed; see export_stderr.log."
    }
}
Write-JsonFile (Join-Path $runDirectory "agh_native_records.json") $nativeExport

Write-JsonFile (Join-Path $runDirectory "exit_status.json") ([ordered]@{
    schema = "devx-agh-exit-status/v1"
    agh_process_exit_code = $result.ExitCode
    agh_result_exit_code = $(if ($resultRecord) { $resultRecord.exitCode } else { "NOT_AVAILABLE" })
    reason = $(if ($resultRecord) { $resultRecord.reason } else { "NOT_AVAILABLE" })
    session_id = $(if ($sessionId) { $sessionId } else { "NOT_AVAILABLE" })
    launcher_error = $(if ($launcherError) { $launcherError } else { "NONE" })
    completed_at_utc = (Get-Date).ToUniversalTime().ToString("o")
})

Write-Output "Evidence: $runDirectory"
Write-Output "AGH exit code: $($result.ExitCode)"
Write-Output "AGH session id: $(if ($sessionId) { $sessionId } else { 'NOT_AVAILABLE' })"
exit $result.ExitCode
