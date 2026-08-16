$ErrorActionPreference = 'Stop'

$Repo = 'https://github.com/badrpk/neuron.git'
$Dest = if ($env:NEURON_HOME) { $env:NEURON_HOME } else { Join-Path $env:LOCALAPPDATA 'Neuron' }
$Build = Join-Path $Dest 'build'

foreach ($cmd in @('git','cmake')) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        throw "Missing required command: $cmd"
    }
}

if (-not (Get-Command 'cl' -ErrorAction SilentlyContinue) -and
    -not (Get-Command 'g++' -ErrorAction SilentlyContinue) -and
    -not (Get-Command 'clang++' -ErrorAction SilentlyContinue)) {
    Write-Warning 'No compiler was found on PATH. CMake may still locate Visual Studio Build Tools automatically.'
}

if (Test-Path (Join-Path $Dest '.git')) {
    git -C $Dest fetch origin --tags --prune
    $dirty = git -C $Dest status --porcelain
    if ($dirty) { throw "Refusing update: $Dest has local changes" }
    git -C $Dest checkout main
    git -C $Dest pull --ff-only origin main
} else {
    if (Test-Path $Dest) { Remove-Item -Recurse -Force $Dest }
    git clone --branch main $Repo $Dest
}

cmake -S $Dest -B $Build -DCMAKE_BUILD_TYPE=Release
cmake --build $Build --config Release --parallel

Write-Host "Neuron installed at $Dest"
Write-Host "Build output: $Build"
