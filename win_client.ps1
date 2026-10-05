# ==============================================================================
# Client Storage Monitor per Windows 11 (PowerShell Nativo)
# Rileva gli indirizzi IP e lo spazio di archiviazione dei dischi locali (C:, D:, ecc.)
# e li trasmette al server centrale in tempo reale.
# ==============================================================================

param (
    [string]$ServerUrl = "http://localhost:8080",
    [int]$IntervalSeconds = 10,
    [switch]$Once
)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " 💻 Windows 11 Storage Monitor Client (PowerShell)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Rimuovi trailing slash se presente
if ($ServerUrl.EndsWith("/")) {
    $ServerUrl = $ServerUrl.Substring(0, $ServerUrl.Length - 1)
}

$ReportUrl = "$ServerUrl/api/report"
Write-Host "[+] Server di destinazione: $ReportUrl" -ForegroundColor Yellow
Write-Host "[+] Frequenza aggiornamento: ogni $IntervalSeconds secondi`n" -ForegroundColor Yellow

function Get-LocalIPv4 {
    try {
        $ip = (Get-NetIPAddress -AddressFamily IPv4 | 
            Where-Object { 
                $_.IPAddress -notlike "127.*" -and 
                $_.IPAddress -notlike "169.254.*" -and 
                $_.InterfaceAlias -notlike "*vEthernet*" -and
                $_.InterfaceAlias -notlike "*Loopback*"
            } | Select-Object -First 1).IPAddress

        if (-not $ip) {
            $ip = [System.Net.Dns]::GetHostAddresses([System.Net.Dns]::GetHostName()) | 
                Where-Object { $_.AddressFamily -eq 'InterNetwork' -and $_.IPAddressToString -notlike "127.*" } | 
                Select-Object -First 1 | ForEach-Object { $_.IPAddressToString }
        }

        if (-not $ip) { $ip = "127.0.0.1" }
        return $ip
    } catch {
        return "127.0.0.1"
    }
}

function Send-StorageReport {
    $hostname = $env:COMPUTERNAME
    $localIp = Get-LocalIPv4
    $osVersion = (Get-CimInstance Win32_OperatingSystem).Caption
    $username = $env:USERDOMAIN + "\" + $env:USERNAME

    # Ottieni dischi fisici fissi (DriveType = 3)
    $disks = Get-CimInstance Win32_LogicalDisk | Where-Object { $_.DriveType -eq 3 -and $_.Size -gt 0 }

    $drivesList = @()
    foreach ($disk in $disks) {
        $totalGB = [math]::Round($disk.Size / 1GB, 2)
        $freeGB = [math]::Round($disk.FreeSpace / 1GB, 2)
        $usedGB = [math]::Round(($disk.Size - $disk.FreeSpace) / 1GB, 2)
        $pctUsed = [math]::Round((($disk.Size - $disk.FreeSpace) / $disk.Size) * 100, 1)

        $drivesList += @{
            drive        = $disk.DeviceID
            label        = if ($disk.VolumeName) { $disk.VolumeName } else { "Disco Locale" }
            total_gb     = $totalGB
            used_gb      = $usedGB
            free_gb      = $freeGB
            percent_used = $pctUsed
        }
    }

    # Cartelle critiche / spazzatura
    function Get-FolderSizeMB ($path) {
        if (Test-Path $path) {
            try {
                $size = (Get-ChildItem -Path $path -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
                if ($size) { return [math]::Round($size / 1MB, 2) }
            } catch {}
        }
        return 0
    }

    $userTempPath = $env:TEMP
    $bloatList = @(
        @{ name = "Temp Utente (%TEMP%)"; path = $userTempPath; size_mb = (Get-FolderSizeMB $userTempPath) },
        @{ name = "Temp di Sistema"; path = "C:\Windows\Temp"; size_mb = (Get-FolderSizeMB "C:\Windows\Temp") },
        @{ name = "Cestino (Recycle Bin)"; path = "C:\$Recycle.Bin"; size_mb = (Get-FolderSizeMB "C:\$Recycle.Bin") },
        @{ name = "Cache Windows Update"; path = "C:\Windows\SoftwareDistribution\Download"; size_mb = (Get-FolderSizeMB "C:\Windows\SoftwareDistribution\Download") },
        @{ name = "File di Log Windows"; path = "C:\Windows\Logs"; size_mb = (Get-FolderSizeMB "C:\Windows\Logs") }
    )

    $payload = @{
        hostname      = $hostname
        ip            = $localIp
        os            = $osVersion
        username      = $username
        drives        = $drivesList
        bloat_folders = $bloatList
    }

    $jsonBody = $payload | ConvertTo-Json -Depth 5

    try {
        $response = Invoke-RestMethod -Uri $ReportUrl -Method Post -Body $jsonBody -ContentType "application/json" -TimeoutSec 5
        $timestamp = Get-Date -Format "HH:mm:ss"
        Write-Host "[$timestamp] ✅ Report inviato con successo! Host: $hostname ($localIp) | Dischi: $($drivesList.Count)" -ForegroundColor Green
    } catch {
        $timestamp = Get-Date -Format "HH:mm:ss"
        Write-Host "[$timestamp] ❌ Errore durante l'invio del report a $ReportUrl : $_" -ForegroundColor Red
    }
}

# Esecuzione principale
do {
    Send-StorageReport
    if ($Once) { break }
    Start-Sleep -Seconds $IntervalSeconds
} while ($true)
