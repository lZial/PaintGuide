<#
.SYNOPSIS
    Открывает PaintGuide в интернете по временной ссылке.

.DESCRIPTION
    Поднимает SSH-туннель через localhost.run: приложение остаётся на вашем
    компьютере, а по ссылке https://<домен>.lhr.life к нему может зайти
    любой — с телефона, с другого компьютера, из-за пределов вуза.

    Соединение с localhost.run нестабильно, поэтому скрипт переподключается
    сам и печатает новую ссылку.

    Требуется запущенное приложение (python run.py).

.PARAMETER Port
    Локальный порт приложения. По умолчанию 5000.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\tunnel.ps1
#>
param(
    [int]$Port = 5000,
    [string]$Host = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    $python = "python"
}

& $python (Join-Path $PSScriptRoot "tunnel.py") --port $Port --host $Host
