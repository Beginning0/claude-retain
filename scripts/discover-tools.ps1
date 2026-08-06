# Script de descubrimiento de herramientas disponibles en Claude Code
# Registra: skills instaladas, MCP servers, hooks configurados

$pluginRoot = $env:CLAUDE_PLUGIN_ROOT
if (-not $pluginRoot) {
    # Fallback: buscar desde el directorio actual
    $pluginRoot = (Get-Location).Path
}

$skillsDir = "$env:APPDATA\Claude\skills"
$settingsPath = "$env:APPDATA\Claude\settings.json"

Write-Host "=== Descubriendo herramientas disponibles ==="
Write-Host ""

# 1. Skills instaladas como archivos .skill
Write-Host "Skills (.skill files):"
if (Test-Path $skillsDir) {
    $skillFiles = Get-ChildItem "$skillsDir\*.skill" -ErrorAction SilentlyContinue
    if ($skillFiles.Count -gt 0) {
        foreach ($f in $skillFiles) {
            Write-Host "  - $($f.Name)"
        }
    } else {
        Write-Host "  (ninguno)"
    }
} else {
    Write-Host "  (directorio no encontrado: $skillsDir)"
}

# 2. Skills del plugin.json
Write-Host ""
Write-Host "Skills del plugin:"
$pluginJson = "$pluginRoot\.claude-plugin\plugin.json"
if (Test-Path $pluginJson) {
    $pluginConfig = Get-Content $pluginJson -Raw | ConvertFrom-Json
    if ($pluginConfig.skills) {
        foreach ($skill in $pluginConfig.skills) {
            Write-Host "  - $skill"
        }
    } else {
        Write-Host "  (ninguno configurado)"
    }
}

# 3. MCP Servers
Write-Host ""
Write-Host "MCP Servers:"
if (Test-Path $settingsPath) {
    $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
    if ($settings.mcpServers) {
        foreach ($server in $settings.mcpServers.PSObject.Properties) {
            Write-Host "  - $($server.Name): $($server.Value.command)"
        }
    } else {
        Write-Host "  (ninguno configurado)"
    }
}

# 4. Hooks configurados
Write-Host ""
Write-Host "Hooks configurados:"
if (Test-Path $settingsPath) {
    $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
    if ($settings.hooks) {
        foreach ($hook in $settings.hooks.PSObject.Properties) {
            Write-Host "  $($hook.Name):"
            foreach ($script in $hook.Value) {
                Write-Host "    - $script"
            }
        }
    } else {
        Write-Host "  (ninguno configurado)"
    }
}

# 5. Skills de claude-retain
Write-Host ""
Write-Host "claude-retain Skills:"
$claude-retainSkills = Get-ChildItem "$pluginRoot\skills" -Directory -ErrorAction SilentlyContinue
if ($claude-retainSkills.Count -gt 0) {
    foreach ($s in $claude-retainSkills) {
        Write-Host "  - $($s.Name)"
    }
} else {
    Write-Host "  (ninguno encontrado)"
}

Write-Host ""
Write-Host "=== Fin del descubrimiento ==="

