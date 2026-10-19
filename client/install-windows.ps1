# Family RO client installer for Windows.
#
# Downloads Gravity's own kRO full client (Ragnarok_200304.zip, ~3.8 GB),
# applies the small exe patch in this folder (the same changes NEMO makes),
# drops in the do-nothing CDClient.dll, writes a clientinfo.xml that points
# at the server, and puts a shortcut on the desktop. Nothing of Gravity's is
# redistributed: the client comes from their server, the patch is a few
# dozen bytes.
#
# Run it through install-windows.bat (double-click), or:
#   powershell -ExecutionPolicy Bypass -File install-windows.ps1 [-Dir C:\Games\FamilyRO] [-Server ro.example.com]
param(
    [string]$Dir = (Join-Path $env:USERPROFILE 'FamilyRO'),
    [string]$Server = 'ro.numbawon.xyz',
    [string]$ZipUrl = 'http://rofull.gnjoy.com/Ragnarok_200304.zip',
    [string]$ZipSha256 = 'a00bd56f591c097ad84567128a6a2ccadc2ea98dbec7fa58b3a6c5fa94b8d092',
    [string]$OverlayUrl = 'https://github.com/NumbaWon/hercules-docker/releases/download/client-english-1/english-overlay-2020-02-19.zip',
    [string]$OverlaySha256 = '9c3ffeb8c6509f7db45a6888d730b4fe207d1fa78e62445d1b407e84c84a36c1',
    [switch]$NoEnglish
)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

function Sha256($path) { (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLower() }
function HexBytes($h) { $b = New-Object byte[] ($h.Length / 2); for ($i = 0; $i -lt $b.Length; $i++) { $b[$i] = [Convert]::ToByte($h.Substring(2 * $i, 2), 16) }; ,$b }

New-Item -ItemType Directory -Force -Path $Dir | Out-Null
$zip = Join-Path $Dir 'Ragnarok_200304.zip'

# 1. download (resumable, curl.exe ships with Windows 10 and 11)
if (-not (Test-Path $zip) -or (Sha256 $zip) -ne $ZipSha256) {
    Write-Host "Downloading the client (3.8 GB), this takes a while..."
    & curl.exe -L -C - --fail -o $zip $ZipUrl
    if ($LASTEXITCODE -ne 0) { throw "download failed (curl exit $LASTEXITCODE)" }
}
if ((Sha256 $zip) -ne $ZipSha256) { throw 'the downloaded client does not match the expected build, stopping' }

# 2. unpack
Add-Type -AssemblyName System.IO.Compression.FileSystem
if (-not (Test-Path (Join-Path $Dir 'Ragexe.exe'))) {
    Write-Host 'Unpacking...'
    [IO.Compression.ZipFile]::ExtractToDirectory($zip, $Dir)
}

# 2b. English text (translation tables and textures, laid over the client)
if (-not $NoEnglish) {
    $ov = Join-Path $Dir 'english-overlay.zip'
    if (-not (Test-Path $ov) -or (Sha256 $ov) -ne $OverlaySha256) {
        Write-Host 'Downloading the English text...'
        & curl.exe -L -C - --fail -o $ov $OverlayUrl
        if ($LASTEXITCODE -ne 0) { throw "download failed (curl exit $LASTEXITCODE)" }
    }
    if ((Sha256 $ov) -ne $OverlaySha256) { throw 'the English overlay does not match the expected file, stopping' }
    $za = [IO.Compression.ZipFile]::OpenRead($ov)
    foreach ($e in $za.Entries) {
        if ($e.FullName.EndsWith('/')) { continue }
        $target = Join-Path $Dir $e.FullName
        New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
        [IO.Compression.ZipFileExtensions]::ExtractToFile($e, $target, $true)
    }
    $za.Dispose()
}

# 3. patch the exe
$src = Join-Path $Dir 'Ragexe.exe'
$dst = Join-Path $Dir 'Ragexe_patched.exe'
$lines = Get-Content (Join-Path $here 'ragexe-2020-02-19.patch') | Where-Object { $_ -and -not $_.StartsWith('#') }
$srcHash = ($lines | Where-Object { $_ -like 'source-sha256 *' }).Split(' ')[1]
$dstHash = ($lines | Where-Object { $_ -like 'result-sha256 *' }).Split(' ')[1]
if ((Sha256 $src) -ne $srcHash) { throw 'Ragexe.exe is not the 2020-02-19 build this patch is for' }
$bytes = [IO.File]::ReadAllBytes($src)
$tail = New-Object System.Collections.Generic.List[byte]
foreach ($l in $lines | Where-Object { $_ -notlike '*-sha256 *' }) {
    if ($l.StartsWith('append ')) { $tail.AddRange([byte[]](HexBytes $l.Substring(7))); continue }
    $o, $old, $new = $l.Split(' ')
    $off = [Convert]::ToInt32($o, 16)
    $oldb = HexBytes $old; $newb = HexBytes $new
    for ($i = 0; $i -lt $oldb.Length; $i++) { if ($bytes[$off + $i] -ne $oldb[$i]) { throw "unexpected byte at 0x$o" } }
    [Array]::Copy($newb, 0, $bytes, $off, $newb.Length)
}
[IO.File]::WriteAllBytes($dst, ([byte[]]$bytes + $tail.ToArray()))
if ((Sha256 $dst) -ne $dstHash) { throw 'patched exe does not match the expected result' }

# 4. stub anti-cheat DLL, GRF list, server address
Copy-Item (Join-Path $here 'CDClient.dll') (Join-Path $Dir 'CDClient.dll') -Force
Copy-Item (Join-Path $here 'DATA.INI') (Join-Path $Dir 'DATA.INI') -Force
New-Item -ItemType Directory -Force -Path (Join-Path $Dir 'data') | Out-Null
(Get-Content (Join-Path $here 'clientinfo.xml') -Raw).Replace('ro.numbawon.xyz', $Server) |
    Set-Content (Join-Path $Dir 'data\clientinfo.xml') -Encoding ASCII

# 5. run as administrator, Windows 7 mode (the client's usual needs)
$key = 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers'
New-Item -Force -Path $key | Out-Null
Set-ItemProperty -Path $key -Name $dst -Value '~ RUNASADMIN WIN7RTM'

# 6. desktop shortcut
$sh = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Family RO.lnk'))
$sh.TargetPath = $dst
$sh.WorkingDirectory = $Dir
$sh.Save()

Write-Host "Done. Start 'Family RO' from the desktop. To register, log in as yourname_M or yourname_F (any password) the first time."
