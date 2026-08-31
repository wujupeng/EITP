param([string]$Cmd)

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "C:\Windows\System32\OpenSSH\ssh.exe"
$psi.Arguments = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -o KexAlgorithms=ecdh-sha2-nistp256 -o PreferredAuthentications=password -o ConnectTimeout=15 debian@192.168.1.70 `"$Cmd`""
$psi.UseShellExecute = $false
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.EnvironmentVariables["SSH_ASKPASS"] = "C:\Users\DELL\Documents\dev\EITP\deploy\askpass.bat"
$psi.EnvironmentVariables["DISPLAY"] = "1"
$psi.EnvironmentVariables["SSH_ASKPASS_REQUIRE"] = "force"

$p = [System.Diagnostics.Process]::Start($psi)
Start-Sleep -Milliseconds 500
if (-not $p.HasExited) {
    try { $p.StandardInput.WriteLine("9090") } catch {}
}
$p.WaitForExit(55000) | Out-Null
$stdout = $p.StandardOutput.ReadToEnd()
$stderr = $p.StandardError.ReadToEnd()
if ($stdout) { Write-Output $stdout }
if ($stderr -and -not $stderr.Contains("Warning: Permanently added")) { Write-Output "[STDERR] $stderr" }