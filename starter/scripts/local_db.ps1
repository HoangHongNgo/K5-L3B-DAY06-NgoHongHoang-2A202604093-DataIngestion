param([switch]$Stop)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$bin = Join-Path $projectRoot '.local\postgres\Library\bin'
$data = Join-Path $projectRoot '.local\pgdata'
$log = Join-Path $projectRoot '.local\postgres.log'
$envFile = Join-Path $PSScriptRoot '..\.env'
$env:PATH = "$bin;$env:PATH"

if (-not (Test-Path -LiteralPath (Join-Path $bin 'pg_ctl.exe')) -or
    -not (Test-Path -LiteralPath (Join-Path $projectRoot '.local\postgres\Library\share\extension\vector.control'))) {
    throw 'Local PostgreSQL with pgvector is missing from .local/postgres.'
}

if ($Stop) {
    if (Test-Path -LiteralPath (Join-Path $data 'PG_VERSION')) {
        & pg_ctl.exe -D $data stop -m fast
        if ($LASTEXITCODE -ne 0) { throw 'Could not stop local PostgreSQL.' }
    }
    exit 0
}

$passwordFile = Join-Path $projectRoot '.local\pg-password.tmp'
if (-not (Test-Path -LiteralPath (Join-Path $data 'PG_VERSION'))) {
    if (Test-Path -LiteralPath $envFile) {
        throw 'starter/.env already exists. Back it up or configure it before initializing a new database.'
    }
    $password = [Convert]::ToHexString(
        [Security.Cryptography.RandomNumberGenerator]::GetBytes(24)
    ).ToLowerInvariant()
    try {
        Set-Content -LiteralPath $passwordFile -Value $password -Encoding ascii -NoNewline
        & initdb.exe -D $data -U postgres -A scram-sha-256 --encoding=UTF8 --locale=C "--pwfile=$passwordFile" --no-instructions
        if ($LASTEXITCODE -ne 0) { throw 'initdb failed.' }
        Set-Content -LiteralPath $envFile -Encoding ascii -Value @(
            "DATABASE_URL=postgresql://postgres:$password@127.0.0.1:55433/day6_lab",
            'EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2'
        )
    } finally {
        Remove-Item -LiteralPath $passwordFile -Force -ErrorAction SilentlyContinue
    }
}

$urlLine = Get-Content -LiteralPath $envFile | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1
if (-not $urlLine) { throw 'DATABASE_URL is missing from starter/.env.' }
$uri = [uri]$urlLine.Substring('DATABASE_URL='.Length)
if ($uri.Host -ne '127.0.0.1' -or $uri.Port -ne 55433 -or $uri.AbsolutePath -ne '/day6_lab') {
    throw 'starter/.env must point to the local day6_lab database on 127.0.0.1:55433.'
}
$parts = $uri.UserInfo.Split(':', 2)
if ($parts.Count -ne 2 -or $parts[0] -ne 'postgres') { throw 'Expected postgres user in starter/.env.' }
$priorPassword = $env:PGPASSWORD
try {
    $env:PGPASSWORD = [uri]::UnescapeDataString($parts[1])
    & pg_ctl.exe -D $data status *> $null
    if ($LASTEXITCODE -ne 0) {
        & pg_ctl.exe -D $data -o '-h 127.0.0.1 -p 55433' -l $log start
        if ($LASTEXITCODE -ne 0) { throw 'Could not start local PostgreSQL.' }
    }
    $exists = & psql.exe -h 127.0.0.1 -p 55433 -U postgres -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = 'day6_lab'"
    if ($LASTEXITCODE -ne 0) { throw 'Could not inspect local PostgreSQL.' }
    if ($exists -ne '1') {
        & createdb.exe -h 127.0.0.1 -p 55433 -U postgres day6_lab
        if ($LASTEXITCODE -ne 0) { throw 'Could not create day6_lab.' }
    }
    & psql.exe -h 127.0.0.1 -p 55433 -U postgres -d day6_lab -c 'CREATE EXTENSION IF NOT EXISTS vector;'
    if ($LASTEXITCODE -ne 0) { throw 'Could not enable pgvector.' }
    Write-Output 'Local PostgreSQL is ready on 127.0.0.1:55433.'
} finally {
    $env:PGPASSWORD = $priorPassword
}
