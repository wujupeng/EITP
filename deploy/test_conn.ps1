$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "C:\Program Files\PuTTY\plink.exe"
$psi.Arguments = '-ssh -pw 9090 debian@192.168.1.70 "echo CONNECTED"'
$psi.UseShellExecute = $false
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$p = [System.Diagnostics.Process]::Start($psi)
Start-Sleep -Milliseconds 500
if (-not $p.HasExited) {
    $p.StandardInput.WriteLine("y")
}
$p.WaitForExit(10000) | Out-Null
$stdout = $p.StandardOutput.ReadToEnd()
$stderr = $p.StandardError.ReadToEnd()
Write-Output "STDOUT: $stdout"
Write-Output "STDERR: $stderr"
Write-Output "EXIT: $($p.ExitCode)"