param([string]$Pasta = $PSScriptRoot)

$ErrorActionPreference = 'Stop'
$Pasta = (Resolve-Path -LiteralPath $Pasta).Path
$nome = 'danasOS-0.2-amd64'
$iso = Join-Path $Pasta "$nome.iso"
$checksums = Join-Path $Pasta "$nome.sha256"
$linha = (Get-Content -LiteralPath $checksums -Raw).Trim()
if ($linha -notmatch '^([0-9a-fA-F]{64})\s+danasOS-0\.2-amd64\.iso$') {
    throw 'Checksum invalido.'
}
$hashEsperado = $Matches[1]
if (Test-Path -LiteralPath $iso) {
    if ((Get-FileHash -LiteralPath $iso -Algorithm SHA256).Hash -ne $hashEsperado) {
        throw 'A ISO existente falhou na verificacao SHA-256.'
    }
    Write-Output "ISO verificada: $iso"
    return
}

$partes = @(Get-ChildItem -LiteralPath $Pasta -File |
    Where-Object Name -Match '^danasOS-0\.2-amd64\.iso\.part-\d{3}$' |
    Sort-Object Name)
if ($partes.Count -lt 2) { throw 'Baixe todas as partes antes de continuar.' }
for ($i = 0; $i -lt $partes.Count; $i++) {
    if ($partes[$i].Name -ne ("$nome.iso.part-{0:D3}" -f $i)) { throw 'Falta uma parte.' }
}

$temporario = Join-Path $Pasta ("$nome-" + [Guid]::NewGuid().ToString('N') + '.tmp')
try {
    $saida = [IO.File]::Open($temporario, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
    try {
        foreach ($parte in $partes) {
            $entrada = $parte.OpenRead()
            try { $entrada.CopyTo($saida) }
            finally { $entrada.Dispose() }
        }
    }
    finally { $saida.Dispose() }
    if ((Get-FileHash -LiteralPath $temporario -Algorithm SHA256).Hash -ne $hashEsperado) {
        throw 'A imagem montada falhou na verificacao SHA-256.'
    }
    [IO.File]::Move($temporario, $iso)
    Write-Output "ISO verificada: $iso"
}
finally {
    if (Test-Path -LiteralPath $temporario) { Remove-Item -LiteralPath $temporario }
}
