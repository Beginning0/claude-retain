# Hook Startup — Descubre herramientas disponibles al iniciar sesión y registra en claude-retain L0

$pluginDir = ""
if ($env:CLAUDE_PLUGIN_ROOT) {
    $pluginDir = $env:CLAUDE_PLUGIN_ROOT
}
else {
    $knownPaths = @(
        "$HOME\.claude\plugins\claude-retain",
        (Get-Location).Path
    )
    foreach ($dir in $knownPaths) {
        if (Test-Path "$dir\claude_retain\cli.py") {
            $pluginDir = $dir
            break
        }
    }
}

if (-not $pluginDir) { exit 0 }

# Registrar herramientas disponibles en claude-retain L0 (identidad del agente)
$toolsFile = "$HOME\.claude-retain\tools_available.md"

$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"

Write-Host "[claude-retain] Startup - descubriendo herramientas..."

# Descubrir herramientas
$skills = @()
$skillsDir = "$env:APPDATA\Claude\skills"
if (Test-Path $skillsDir) {
    Get-ChildItem "$skillsDir\*.skill" -ErrorAction SilentlyContinue | ForEach-Object {
        $skills += $_.Name
    }
}

$pluginSkills = @()
$pluginJson = "$pluginDir\.claude-plugin\plugin.json"
if (Test-Path $pluginJson) {
    $config = Get-Content $pluginJson -Raw | ConvertFrom-Json
    if ($config.skills) {
        $config.skills | ForEach-Object { $pluginSkills += $_ }
    }
}

$claude-retainSkills = @()
$skillsDirPath = "$pluginDir\skills"
if (Test-Path $skillsDirPath) {
    Get-ChildItem $skillsDirPath -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $claude-retainSkills += $_.Name
    }
}

$mcpServers = @()
$settingsPath = "$env:APPDATA\Claude\settings.json"
if (Test-Path $settingsPath) {
    $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
    if ($settings.mcpServers) {
        $settings.mcpServers.PSObject.Properties | ForEach-Object {
            $mcpServers += $_.Name
        }
    }
}

# Escribir en claude-retain L0
$toolsContent = @"
---
discovered_at: $timestamp
skills_installed:
$(($skills | ForEach-Object { "  - $_" }) -join "`n")
plugin_skills:
$(($pluginSkills | ForEach-Object { "  - $_" }) -join "`n")
claude-retain_skills:
$(($claude-retainSkills | ForEach-Object { "  - $_" }) -join "`n")
mcp_servers:
$(($mcpServers | ForEach-Object { "  - $_" }) -join "`n")
---
EOF
"@

Set-Content $toolsFile -Value $toolsContent -Encoding utf8
Write-Host "[claude-retain] Startup - herramientas descubiertas y registradas en claude-retain"


