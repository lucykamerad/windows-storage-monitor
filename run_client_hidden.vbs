Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & WScript.Arguments(0) & "\win_client.ps1"" -ServerUrl """ & WScript.Arguments(1) & """ -IntervalSeconds 10", 0, False
