# Hook LoopUpdate — Evalúa el resultado de una iteración LOOP y actualiza claude-retain
# Lee el contexto del tool call de stdin (JSON)

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

# Verificar si hay un LOOP activo
$loopState = "$HOME\.claude\loop-task.local.md"
if (-not (Test-Path $loopState)) { exit 0 }

# Leer estado actual del LOOP
$loopConfig = Get-Content $loopState -Raw | ConvertFrom-Markdown
$iteration = if ($loopConfig.Framework.PSObject.Properties['iteration']) { $loopConfig.Framework.PSObject.Properties['iteration'].Value } else { 1 }

# Leer el resultado del tool call
$inputText = [Console]::In.ReadToEnd()
if ([string]::IsNullOrWhiteSpace($inputText)) { exit 0 }

$toolInput = $inputText | ConvertFrom-Json
$toolName = if ($toolInput.tool_name) { $toolInput.tool_name } else { "" }

# Determinar si la iteración fue exitosa
$result = "unknown"
if ($toolInput.input -and $toolInput.input.exit_code) {
    $result = if ($toolInput.input.exit_code -eq 0) { "success" } else { "failure" }
}

# Actualizar evaluación en claude-retain
$evalDir = "$HOME\.claude-retain\evaluations"
if (-not (Test-Path $evalDir)) {
    New-Item -ItemType Directory -Force -Path $evalDir | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$evalFile = "$evalDir\loop-$timestamp.md"

$taskName = ""
try {
    $taskContent = Get-Content $loopState -Raw
    # Extraer el título de la tarea (después del frontmatter)
    $taskLines = $taskContent -split "`n"
    $inFrontmatter = $true
    foreach ($line in $taskLines) {
        if ($inFrontmatter -and $line.Trim() -match '^---$') {
            $inFrontmatter = $false
            continue
        }
        if (-not $inFrontmatter -and $line.Trim()) {
            $taskName = $line
            break
        }
    }
} catch {
    $taskName = "unknown"
}

$evaluation = @"
---
task: $taskName
iteration: $iteration
mode: loop
tool_used: $toolName
result: $result
updated_at: $(Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
---
EOF
"@

Set-Content $evalFile -Value $evaluation -Encoding utf8
Write-Host "[claude-retain] LoopUpdate - iteracion $iteration evaluada: $result"


