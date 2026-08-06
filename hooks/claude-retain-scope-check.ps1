# Hook PreToolUse — Ejecuta scope-checker ANTES de escribir en archivos JS/TS

$PLUGIN_DIR = ""
if ($env:CLAUDE_PLUGIN_ROOT) {
    $PLUGIN_DIR = $env:CLAUDE_PLUGIN_ROOT
} else {
    foreach ($dir in "$HOME\.claude\plugins\claude-retain", (Get-Location).Path) {
        if (Test-Path "$dir\claude_retain\cli.py") {
            $PLUGIN_DIR = $dir
            break
        }
    }
}

if (-not $PLUGIN_DIR) { exit 0 }

# Leer stdin JSON
$INPUT_TEXT = [Console]::In.ReadLine()
if (-not $INPUT_TEXT) { exit 0 }

# Parsear tool name
try {
    $toolName = ($INPUT_TEXT | ConvertFrom-Json).tool_name
} catch {
    exit 0
}

# Solo para Write/Edit
if ($toolName -ne "Write" -and $toolName -ne "Edit") { exit 0 }

# Obtener la ruta del archivo
try {
    $filePath = ($INPUT_TEXT | ConvertFrom-Json).input.file_path
} catch {
    exit 0
}

if (-not $filePath) { exit 0 }

# Solo archivos JS/TS
$ext = [System.IO.Path]::GetExtension($filePath).ToLower()
if ($ext -notin @('.js', '.ts', '.mjs', '.cjs')) { exit 0 }

# Verificar si el archivo existe
if (-not (Test-Path $filePath)) { exit 0 }

# Ejecutar scope-checker
$skillDir = Join-Path $PLUGIN_DIR "skills\scope-checker"
$pyScript = Join-Path $skillDir "scope-checker.py"
$ps1Script = Join-Path $skillDir "scope-checker.ps1"

if (Test-Path $ps1Script) {
    # Preferir PowerShell nativo en Windows
    try {
        $output = & powershell -ExecutionPolicy Bypass -File $ps1Script $filePath --json 2>&1
        if ($LASTEXITCODE -ne 0 -and $output) {
            $issues = ($output | ConvertFrom-Json | Measure-Object).Count
            Write-Host "[claude-retain] scope-checker: Se encontraron $issues problema(s) de scope en $filePath antes de escribir." -ForegroundColor Yellow

            # Mostrar detalles
            foreach ($issue in ($output | ConvertFrom-Json)) {
                Write-Host "  [$($issue.severity)] $($issue.variable) (linea $($issue.assign_line)): $($issue.detail)" -ForegroundColor Red
            }
        }
    } catch {
        : # Ignorar errores de scope-checker
    }
}
elseif (Test-Path $pyScript) {
    try {
        $output = & python $pyScript $filePath --json 2>&1
        if ($LASTEXITCODE -ne 0 -and $output) {
            $issues = ($output | ConvertFrom-Json | Measure-Object).Count
            Write-Host "[claude-retain] scope-checker: Se encontraron $issues problema(s) de scope en $filePath antes de escribir." -ForegroundColor Yellow

            foreach ($issue in ($output | ConvertFrom-Json)) {
                Write-Host "  [$($issue.severity)] $($issue.variable) (linea $($issue.assign_line)): $($issue.detail)" -ForegroundColor Red
            }
        }
    } catch {
        : # Ignorar errores de scope-checker
    }
}


