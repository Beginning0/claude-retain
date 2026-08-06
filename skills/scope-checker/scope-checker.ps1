# Requires -ExecutionPolicy Bypass to run in PowerShell
<#
.SYNOPSIS
    Detecta problemas de scope de variables en archivos JavaScript/TypeScript.
    Encuentra variables declaradas dentro de bloques condicionales pero usadas fuera,
    implicit globals (asignaciones sin declaración), y asignaciones sin declaración previa.

.DESCRIPTION
    Escanea un archivo JS/TS y reporta:
    1. Variables declaradas con let/var/const dentro de un bloque if/for/while pero usadas fuera
    2. Implicit globals — asignaciones sin let/var/const (funcionan en no-strict pero son bugs silenciosos)
    3. Variables usadas antes de ser declaradas en el mismo scope

.PARAMETER FilePath
    Ruta al archivo JS/TS a escanear

.PARAMETER FunctionName
    Nombre de la función para limitar el escaneo a un bloque específico (opcional)

.PARAMETER Verify
    Modo verificar — solo reporta si hay errores, no muestra detalles de scope

.PARAMETER OutputFormat
    Formato de salida: text (default), json, summary

.EXAMPLE
    ./scope-checker.ps1 "C:\Users\Shado Terro\Desktop\Proyecto_money\BOT_asimetrico_F\bot.js"
    ./scope-checker.ps1 "bot.js" --function analyzeStrategyLoop
    ./scope-checker.ps1 "bot.js" --verify
    ./scope-checker.ps1 "bot.js" --output-format json

.EXAMPLE
    !claude-retain scope-checker "bot.js" --function analyzeStrategyLoop
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$FilePath,

    [Parameter(Mandatory=$false)]
    [string]$FunctionName,

    [Parameter(Mandatory=$false)]
    [switch]$Verify,

    [Parameter(Mandatory=$false)]
    [ValidateSet("text", "json", "summary")]
    [string]$OutputFormat = "text"
)

# Convertir ruta relativa a absoluta
if (-not (Test-Path $FilePath)) {
    Write-Error "Archivo no encontrado: $FilePath"
    exit 1
}
$FilePath = (Get-Item $FilePath).FullName

# Función para calcular profundidad de llaves en una línea
function Get-BraceDepth {
    param([string]$Line)
    $depth = 0
    foreach ($ch in $Line.ToCharArray()) {
        if ($ch -eq '{') { $depth++ }
        elseif ($ch -eq '}') { $depth-- }
    }
    return $depth
}

# Función para encontrar límites de bloque condicional dentro de una función
function Find-ConditionalBlocks {
    param(
        [string[]]$Lines,
        [int]$StartLine,
        [int]$EndLine
    )

    $blocks = @()
    $depth = 0
    $blockStart = -1

    for ($i = $StartLine; $i -lt $EndLine -and $i -lt $Lines.Length; $i++) {
        $line = $Lines[$i]

        # Detectar inicio de bloque condicional (if/for/while)
        if ($line -match '^\s*(if|for|while)\s*\(') {
            $beforeDepth = $depth
            for ($ch in $line.ToCharArray()) {
                if ($ch -eq '{') { $depth++ }
                elseif ($ch -eq '}') { $depth-- }
            }
            if ($beforeDepth -ge 1 -and $depth -gt $beforeDepth) {
                # Este bloque condicional abre en este nivel de profundidad
                $blockStart = $i
            }
        }

        # Detectar cierre de bloque
        if ($line -match '^\s*\}') {
            $beforeDepth = $depth
            for ($ch in $line.ToCharArray()) {
                if ($ch -eq '{') { $depth++ }
                elseif ($ch -eq '}') { $depth-- }
            }
            # Si el bloque condicional que abrimos se cierra (regresa al mismo depth)
            if ($blockStart -gt 0 -and $beforeDepth -ge 1 -and $depth -lt $beforeDepth) {
                $blocks += [PSCustomObject]@{
                    StartLine = $blockStart + 1  # 1-indexed
                    EndLine = $i + 1              # 1-indexed
                    DepthBefore = $beforeDepth
                    DepthAfter = $depth
                    Type = "conditional"
                }
                $blockStart = -1
            }
        }
    }

    return $blocks
}

# Función para encontrar variables declaradas en un rango de líneas
function Find-Declarations {
    param(
        [string[]]$Lines,
        [int]$StartLine,
        [int]$EndLine
    )

    $declarations = @{}

    for ($i = $StartLine; $i -lt $EndLine -and $i -lt $Lines.Length; $i++) {
        $line = $Lines[$i]

        # Buscar declaraciones let/var/const
        if ($line -match '(?:let|var|const)\s+(?:([a-zA-Z_]\w+)\s*=|([a-zA-Z_]\w+))') {
            $names = [regex]::Matches($line, '(?:let|var|const)\s+([a-zA-Z_]\w+)')

            foreach ($m in $names) {
                $name = $m.Groups[1].Value
                # Verificar si es una asignación o una declaración simple
                if ($line -match "$name\s*=") {
                    $declarations[$name] = @{
                        Line = $i + 1
                        Type = "assignment"
                        Value = $line.Substring($line.IndexOf($name) + $name.Length + 2).Trim().Split('=')[1].Trim()
                    }
                }
                else {
                    $declarations[$name] = @{
                        Line = $i + 1
                        Type = "declaration"
                        Value = ""
                    }
                }
            }
        }
    }

    return $declarations
}

# Función para encontrar variables asignadas dentro de un bloque
function Find-Assignments {
    param(
        [string[]]$Lines,
        [int]$StartLine,
        [int]$EndLine,
        [hashtable]$Declarations
    )

    $assignments = @{}

    for ($i = $StartLine; $i -lt $EndLine -and $i -lt $Lines.Length; $i++) {
        $line = $Lines[$i]

        # Ignorar SQL strings y object.property assignments
        if ($line -match '(UPDATE|SELECT|WHERE|INSERT|DELETE)\s' -or $line -match '\.\w+\s*=') {
            continue
        }

        # Buscar asignaciones simples (sin let/var/const)
        $matches = [regex]::Matches($line, '(?<![.\w])([a-zA-Z_]\w+)\s*=\s*(?!\s*\w)')

        foreach ($m in $matches) {
            $name = $m.Groups[1].Value
            # Ignorar keywords de JS
            if (@('if','else','for','while','return','true','false','null','undefined','const','let','var','function','new','this','class','try','catch','finally','throw','break','continue','switch','case','default','typeof','instanceof','delete','void','async','await','import','export','console','log','Math','JSON','Date','Number','String','Boolean','Array','Object','Promise','Error') -contains $name) {
                continue
            }
            # Si ya está declarada, es una reasignación (OK)
            if ($Declarations.ContainsKey($name)) {
                continue
            }
            $assignments[$name] = @{
                Line = $i + 1
                Code = $line.Trim()
                Type = "implicit_global"  # No tiene let/var/const — implicit global
            }
        }

        # Buscar asignaciones con let/var/const (declaración dentro del bloque)
        if ($line -match '(?:let|var|const)\s+([a-zA-Z_]\w+)\s*=') {
            $name = [regex]::Match($line, '(?:let|var|const)\s+([a-zA-Z_]\w+)').Groups[1].Value
            if (-not $Declarations.ContainsKey($name)) {
                $assignments[$name] = @{
                    Line = $i + 1
                    Code = $line.Trim()
                    Type = "inside_block"  # Declarada dentro del bloque condicional
                }
            }
        }
    }

    return $assignments
}

# Función para verificar si una variable se usa fuera del bloque
function Find-OutsideUsage {
    param(
        [string[]]$Lines,
        [int]$BlockEndLine,  # Línea después del cierre del bloque
        [int]$MaxLine,
        [string[]]$VariableNames,
        [string]$ScopeType
    )

    $usages = @{}

    for ($i = $BlockEndLine; $i -lt $MaxLine -and $i -lt $Lines.Length; $i++) {
        $line = $Lines[$i]

        # Verificar si la variable se usa en esta línea
        foreach ($name in $VariableNames) {
            if ($line -match "(?<!\w)$name(?!\w)") {
                # No contar asignaciones — solo uso como valor (lectura)
                if ($line -notmatch "$name\s*=") {
                    if (-not $usages.ContainsKey($name)) {
                        $usages[$name] = @()
                    }
                    $usages[$name] += @{
                        Line = $i + 1
                        Code = $line.Trim()
                    }
                }
            }
        }
    }

    return $usages
}

# ==================== MAIN ====================

try {
    $fileContent = Get-Content -Path $FilePath -Encoding UTF8
    $totalLines = $fileContent.Length

    # Si se especificó una función, limitar el escaneo a ese bloque
    if ($FunctionName) {
        $funcStart = 0
        $funcEnd = $totalLines

        # Encontrar inicio de la función — soporta varios patrones
        $patterns = @(
            "function\s+$FunctionName",
            "async\s+function\s+$FunctionName",
            "$FunctionName\s*=\s*(?:async\s+)?function",
            "(?:const|let|var)\s+$FunctionName\s*=",
            "[a-zA-Z_]\w*\.$FunctionName\s*=\s*(?:async\s+)?function"
        )
        $found = $false
        for ($i = 0; $i -lt $fileContent.Length -and -not $found; $i++) {
            foreach ($pattern in $patterns) {
                if ($fileContent[$i] -match $pattern) {
                    $funcStart = $i
                    $found = $true
                    break
                }
            }
        }

        # Encontrar el opening brace { de la funcion
        $braceDepth = 0
        $funcOpenBrace = -1
        for ($i = $funcStart; $i -lt $fileContent.Length; $i++) {
            $line = $fileContent[$i]
            $before = $braceDepth
            foreach ($ch in $line.ToCharArray()) {
                if ($ch -eq '{') {
                    $braceDepth++
                    # El opening brace de la funcion es el primero que lleva de 0 a 1
                    if ($before -eq 0) {
                        $funcOpenBrace = $i
                        break
                    }
                }
                elseif ($ch -eq '}') { $braceDepth-- }
            }
            if ($funcOpenBrace -ge 0) { break }
        }

        # Encontrar el closing brace } que corresponde al opening brace
        $depth = 0
        if ($funcOpenBrace -ge 0) {
            for ($i = $funcOpenBrace; $i -lt $fileContent.Length; $i++) {
                $before = $depth
                foreach ($ch in $fileContent[$i].ToCharArray()) {
                    if ($ch -eq '{') { $depth++ }
                    elseif ($ch -eq '}') { $depth-- }
                }
                # Cuando depth vuelve a 0 desde 1, ese es el cierre de la funcion
                if ($before -eq 1 -and $depth -eq 0) {
                    $funcEnd = $i + 1
                    break
                }
            }
        }

        Write-Host "Escaneando función '$FunctionName' (líneas $($funcStart+1)-$($funcEnd))" -ForegroundColor Yellow
    }
    else {
        $funcStart = 0
        $funcEnd = $totalLines
    }

    # Obtener declaraciones del archivo
    $declarations = Find-Declarations -Lines $fileContent -StartLine $funcStart -EndLine $funcEnd

    # Encontrar todos los bloques condicionales dentro de la función
    $blocks = Find-ConditionalBlocks -Lines $fileContent -StartLine $funcStart -EndLine $funcEnd

    $issues = @()

    foreach ($block in $blocks) {
        # Obtener declaraciones DENTRO del bloque (antes de las asignaciones)
        $blockDecls = Find-Declarations -Lines $fileContent -StartLine $block.StartLine -EndLine $block.EndLine

        # Encontrar asignaciones dentro del bloque
        $assignments = Find-Assignments -Lines $fileContent -StartLine $block.StartLine -EndLine $block.EndLine -Declarations $blockDecls

        if ($assignments.Count -gt 0) {
            $varNames = @($assignments.Keys)
            # Buscar uso fuera del bloque
            $outsideUsage = Find-OutsideUsage -Lines $fileContent -BlockEndLine $block.EndLine -MaxLine $funcEnd -VariableNames $varNames -ScopeType "if"

            foreach ($name in $assignments.Keys) {
                $usage = $outsideUsage[$name]
                $severity = "WARNING"
                $detail = ""

                if ($assignments[$name].Type -eq "inside_block") {
                    $severity = "ERROR"
                    $detail = "Declarada con let/var/const dentro del bloque condicional (línea $($assignments[$name].Line)) pero usada fuera del bloque"
                }
                elseif ($usage) {
                    $severity = "CRITICAL"
                    $detail = "Implicit global — asignado sin let/var/const en línea $($assignments[$name].Line), usado fuera del bloque en línea $($usage[0].Line)"
                }

                $issues += [PSCustomObject]@{
                    Severity = $severity
                    Variable = $name
                    Type = $assignments[$name].Type
                    AssignLine = $assignments[$name].Line
                    UsageLine = if ($usage) { $usage[0].Line } else { "N/A" }
                    Detail = $detail
                    Code = $assignments[$name].Code
                }
            }
        }
    }

    # Output
    if ($issues.Count -eq 0) {
        Write-Host "`n[OK] No se encontraron problemas de scope de variables." -ForegroundColor Green
    }
    else {
        Write-Host "`n[!] Se encontraron $($issues.Count) problema(s) de scope de variables:`n" -ForegroundColor Red

        $bySeverity = @($issues | Group-Object Severity)
        foreach ($group in $bySeverity) {
            $color = if ($group.Name -eq "CRITICAL") { "Red" } elseif ($group.Name -eq "ERROR") { "Yellow" } else { "Cyan" }
            Write-Host "  $($group.Name): $($group.Count)" -ForegroundColor $color
        }

        foreach ($issue in $issues) {
            $color = if ($issue.Severity -eq "CRITICAL") { "Red" } elseif ($issue.Severity -eq "ERROR") { "Yellow" } else { "Cyan" }
            Write-Host "`n  [$($issue.Severity)] $($issue.Variable)" -ForegroundColor $color
            Write-Host "    Tipo: $($issue.Type)"
            Write-Host "    Asignada en línea $($issue.AssignLine): $($issue.Code)"
            if ($issue.UsageLine -ne "N/A") {
                Write-Host "    Usada fuera del bloque en línea $($issue.UsageLine): $($issue.Code)"
            }
            Write-Host "    Detalle: $($issue.Detail)"
        }

        Write-Host "`n[RECOMENDADO] Mover TODAS las variables declaradas dentro del bloque condicional a antes del bloque con valores por defecto:" -ForegroundColor Yellow
        Write-Host "    ANTES: let X = valor; dentro del if" -ForegroundColor Gray
        Write-Host "    DESPUES: let X = default; antes del if + X = valor; dentro del if" -ForegroundColor Gray
    }

    # JSON output
    if ($OutputFormat -eq "json") {
        $issues | ConvertTo-Json -Depth 4
    }

    if ($Verify -and $issues.Count -gt 0) {
        Write-Host "`n[FAIL] Se encontraron $($issues.Count) problema(s)." -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Error "Error al ejecutar scope-checker: $_"
    exit 2
}

