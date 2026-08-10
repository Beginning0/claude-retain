# Verificar estructura del plugin claude-retain
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot -replace '\\scripts$', ''

$success = $true

Write-Host ""
Write-Host "=== Verificacion de estructura del plugin ===" -ForegroundColor Cyan

# 1. Verificar .claude-plugin/plugin.json
$pluginJson = Join-Path $root ".claude-plugin\plugin.json"
if (Test-Path $pluginJson) {
    Write-Host "[OK] .claude-plugin/plugin.json existe" -ForegroundColor Green
    $config = Get-Content $pluginJson | ConvertFrom-Json

    # Verificar campos requeridos
    if ($config.name) { Write-Host "     - name: $($config.name)" -ForegroundColor Gray }
    else { Write-Host "[FAIL] Faltando campo 'name'" -ForegroundColor Red; $success = $false }

    if ($config.version) { Write-Host "     - version: $($config.version)" -ForegroundColor Gray }
    else { Write-Host "[FAIL] Faltando campo 'version'" -ForegroundColor Red; $success = $false }

    if ($config.description) { Write-Host "     - description: $($config.description)" -ForegroundColor Gray }
    else { Write-Host "[FAIL] Faltando campo 'description'" -ForegroundColor Red; $success = $false }

    # Verificar clave commands (obligatoria para slash commands)
    if ($config.commands) {
        Write-Host "     - commands: $($config.commands.Count) archivos" -ForegroundColor Gray
        foreach ($cmd in $config.commands) {
            $path = Join-Path $root $cmd
            if (Test-Path $path) {
                Write-Host "       [OK] $cmd" -ForegroundColor Green
            } else {
                Write-Host "       [FAIL] $cmd NO EXISTE" -ForegroundColor Red
                $success = $false
            }
        }
    } else {
        Write-Host "[FAIL] Faltando clave 'commands' en plugin.json" -ForegroundColor Red
        $success = $false
    }

    # Verificar clave agents (obligatoria para skills/agents)
    if ($config.agents) {
        Write-Host "     - agents: $($config.agents.Count) archivos" -ForegroundColor Gray
        foreach ($agent in $config.agents) {
            $path = Join-Path $root $agent
            if (Test-Path $path) {
                Write-Host "       [OK] $agent" -ForegroundColor Green
            } else {
                Write-Host "       [FAIL] $agent NO EXISTE" -ForegroundColor Red
                $success = $false
            }
        }
    } else {
        Write-Host "[FAIL] Faltando clave 'agents' en plugin.json" -ForegroundColor Red
        $success = $false
    }

    # Nota: hooks ya no se referencian en plugin.json — Claude Code carga hooks/hooks.json automaticamente por convencion

    # Verificar que NO hay clave 'skills' (obsoleta)
    if ($config.skills) {
        Write-Host "[FAIL] La clave 'skills' esta obsoleta, usa 'agents'" -ForegroundColor Red
        $success = $false
    }
} else {
    Write-Host "[FAIL] .claude-plugin/plugin.json NO EXISTE" -ForegroundColor Red
    $success = $false
}

# 2. Verificar hooks/hooks.json
$hooksJson = Join-Path $root "hooks\hooks.json"
if (Test-Path $hooksJson) {
    Write-Host ""
    Write-Host "[OK] hooks/hooks.json existe" -ForegroundColor Green
    $hooks = Get-Content $hooksJson | ConvertFrom-Json
    foreach ($event in $hooks.hooks.PSObject.Properties) {
        Write-Host "     - Evento: $($event.Name) - $($event.Value.Count) hook(s)" -ForegroundColor Gray
    }
} else {
    Write-Host ""
    Write-Host "[WARN] hooks/hooks.json NO EXISTE (los hooks no se cargaran)" -ForegroundColor Yellow
}

# 3. Verificar que los archivos de agente tienen frontmatter valido
Write-Host ""
Write-Host "=== Verificacion de archivos de agente ===" -ForegroundColor Cyan
$agentsDir = Join-Path $root "agents"
if (Test-Path $agentsDir) {
    $agentFiles = Get-ChildItem $agentsDir -Filter "*.md"
    Write-Host "[OK] Directorio agents/ con $($agentFiles.Count) archivos" -ForegroundColor Green
    foreach ($file in $agentFiles) {
        $content = Get-Content $file.FullName -Raw
        $hasFrontmatter = ($content -match "^---") -and ($content -match "name:") -and ($content -match "description:")
        if ($hasFrontmatter) {
            Write-Host "  [OK] $($file.Name)" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] $($file.Name) - frontmatter invalido (falta name o description)" -ForegroundColor Red
            $success = $false
        }
    }
} else {
    Write-Host ""
    Write-Host "[FAIL] Directorio agents/ NO EXISTE" -ForegroundColor Red
    $success = $false
}

# 4. Verificar que los archivos de command tienen frontmatter valido
Write-Host ""
Write-Host "=== Verificacion de slash commands ===" -ForegroundColor Cyan
$commandsDir = Join-Path $root "commands"
if (Test-Path $commandsDir) {
    $cmdFiles = Get-ChildItem $commandsDir -Filter "*.md"
    Write-Host "[OK] Directorio commands/ con $($cmdFiles.Count) archivos" -ForegroundColor Green
    foreach ($file in $cmdFiles) {
        $content = Get-Content $file.FullName -Raw
        $hasFrontmatter = ($content -match "^---") -and ($content -match "name:") -and ($content -match "description:")
        if ($hasFrontmatter) {
            Write-Host "  [OK] $($file.Name)" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] $($file.Name) - frontmatter invalido (falta name o description)" -ForegroundColor Red
            $success = $false
        }
    }
} else {
    Write-Host ""
    Write-Host "[FAIL] Directorio commands/ NO EXISTE" -ForegroundColor Red
    $success = $false
}

# 5. Verificar que .skill-bundle/ no existe (obsoleto)
$skillBundle = Join-Path $root ".skill-bundle"
if (Test-Path $skillBundle) {
    Write-Host ""
    Write-Host "[WARN] .skill-bundle/ existe - formato obsoleto, puede eliminarse" -ForegroundColor Yellow
}

# 6. Verificar que settings.local.json no tiene skill_triggers (obsoleto)
$settingsLocal = Join-Path $root ".claude\settings.local.json"
if (Test-Path $settingsLocal) {
    $localSettings = Get-Content $settingsLocal | ConvertFrom-Json
    if ($localSettings.skill_triggers) {
        Write-Host ""
        Write-Host "[WARN] settings.local.json tiene 'skill_triggers' - no reconocido por Claude Code" -ForegroundColor Yellow
    }
}

# Resultado final
Write-Host ""
if ($success) {
    Write-Host "=== RESULTADO: ESTRUCTURA VALIDA ===" -ForegroundColor Green
    exit 0
} else {
    Write-Host "=== RESULTADO: ERRORES ENCONTRADOS (ver arriba) ===" -ForegroundColor Red
    exit 1
}
