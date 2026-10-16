<#
.SYNOPSIS
Operates the Linux/Windows agent mailbox: status, send, claim, complete,
withdraw, and prune.

.DESCRIPTION
Runs unchanged on Windows PowerShell 5.1 (Windows side) and PowerShell 7
(Linux side). The side is detected from the platform; the mailbox root is the
parent of this script's directory. Messages are published atomically by
writing a .tmp file and renaming it.

.EXAMPLE
mailbox.ps1 status

.EXAMPLE
mailbox.ps1 send -Slug 5680-vm-check -Subject "#5680 VM check" -BodyFile body.md -Attach bundle.zip

.EXAMPLE
mailbox.ps1 claim 20261014T140720Z-linux-5680-patched-windows-vm-check.md
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet('status', 'send', 'claim', 'complete', 'withdraw', 'prune')]
    [string]$Command,

    # Message file name for claim, complete, and withdraw.
    [Parameter(Position = 1)]
    [string]$Name,

    # send: lowercase kebab-case slug for the file name.
    [string]$Slug,
    # send: message title.
    [string]$Subject,
    # send: Markdown body holding the three required sections.
    [string]$BodyFile,
    # send: message being answered.
    [string]$ReplyTo = 'none',
    # send: kebab-case name of the work stream; replies inherit it.
    # status: show only this thread's messages.
    [string]$Thread,
    # send: earlier messages this one replaces; unclaimed ones are withdrawn.
    [string[]]$Supersedes = @(),
    # send: files copied to artifacts/<message-stem>/ with SHA-256 recorded.
    [string[]]$Attach = @(),

    # prune: minimum age, from the owning message's timestamp.
    [int]$Days = 30,
    # prune: delete the listed owned artifact directories.
    [switch]$Apply
)

$ErrorActionPreference = 'Stop'

# Under -File, "a,b" arrives as one string rather than an array.
$Supersedes = @($Supersedes | ForEach-Object { $_ -split ',' } | Where-Object { $_ })
$Attach = @($Attach | ForEach-Object { $_ -split ',' } | Where-Object { $_ })

$Root = Split-Path -Parent $PSScriptRoot
$LinuxRoot = '/home/jesper/Shared/windows-dev/agent-bridge'
$WindowsRoot = '\\192.168.122.1\windows-dev\agent-bridge'

# $IsLinux does not exist in Windows PowerShell 5.1; Platform does in both.
if ($PSVersionTable.Platform -eq 'Unix') { $Me = 'linux'; $Peer = 'windows' }
else { $Me = 'windows'; $Peer = 'linux' }

$Inbox = Join-Path $Root "to-$Me"
$Outbox = Join-Path $Root "to-$Peer"
$Working = Join-Path $Root 'working'
$Completed = Join-Path $Root 'completed'
$Withdrawn = Join-Path $Root 'withdrawn'
$Artifacts = Join-Path $Root 'artifacts'
$Queues = @($Inbox, $Outbox, $Working, $Completed, $Withdrawn)
$RequiredSections = @('## Request or result', '## Context', '## Expected response')
$Utf8 = New-Object System.Text.UTF8Encoding $false

function Find-Message([string]$FileName) {
    foreach ($queue in $Queues) {
        $path = Join-Path $queue $FileName
        if (Test-Path -LiteralPath $path -PathType Leaf) { return $path }
    }
    return $null
}

function Get-MessageTime([string]$FileName) {
    if ($FileName -match '^(\d{8}T\d{6}Z)-') {
        return [DateTime]::ParseExact($Matches[1], "yyyyMMdd'T'HHmmss'Z'",
            [Globalization.CultureInfo]::InvariantCulture,
            [Globalization.DateTimeStyles]'AssumeUniversal,AdjustToUniversal')
    }
    return $null
}

function Get-Subject([string]$Path) {
    $first = Get-Content -LiteralPath $Path -TotalCount 1 -Encoding UTF8
    return ($first -replace '^#\s*', '')
}

# Header lines sit between the title and the first section heading.
function Get-Header([string]$Path, [string]$Key) {
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ($line -match '^## ') { break }
        if ($line -match ('^' + [regex]::Escape($Key) + ':\s*(.*?)\s*$')) { return $Matches[1] }
    }
    return ''
}

function Get-Messages([string]$Queue) {
    if (-not (Test-Path -LiteralPath $Queue)) { return @() }
    $messages = @(Get-ChildItem -LiteralPath $Queue -File -Filter '*.md' | Sort-Object Name)
    if ($Thread) { $messages = @($messages | Where-Object { (Get-Header $_.FullName 'Thread') -eq $Thread }) }
    return $messages
}

function Show-Queue([string]$Label, [string]$Queue) {
    $messages = Get-Messages $Queue
    Write-Output ("{0} ({1})" -f $Label, $messages.Count)
    foreach ($m in $messages) {
        $created = Get-MessageTime $m.Name
        $age = if ($created) { '{0}d' -f [int]([DateTime]::UtcNow - $created).TotalDays } else { '?' }
        $threadName = Get-Header $m.FullName 'Thread'
        if (-not $threadName) { $threadName = '-' }
        Write-Output ("  {0}  [{1}]  ({2})  {3}" -f $m.Name, $age, $threadName, (Get-Subject $m.FullName))
    }
    $loose = @(Get-ChildItem -LiteralPath $Queue -File | Where-Object { $_.Extension -ne '.md' })
    foreach ($f in $loose) { Write-Output ("  legacy attachment: {0}" -f $f.Name) }
}

function Move-Message([string]$FileName, [string]$From, [string]$To) {
    $source = Join-Path $From $FileName
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "$FileName is not in $(Split-Path -Leaf $From)/"
    }
    if (-not (Test-Path -LiteralPath $To)) { New-Item -ItemType Directory -Path $To | Out-Null }
    Move-Item -LiteralPath $source -Destination (Join-Path $To $FileName)
    Write-Output ("{0} -> {1}/" -f $FileName, (Split-Path -Leaf $To))
}

function Format-Size([long]$Bytes) {
    if ($Bytes -ge 1MB) { return '{0:N1} MB' -f ($Bytes / 1MB) }
    return '{0:N0} KB' -f [Math]::Ceiling($Bytes / 1KB)
}

switch ($Command) {
    'status' {
        $scope = if ($Thread) { ", thread: $Thread" } else { '' }
        Write-Output "Mailbox: $Root (side: $Me$scope)"
        Show-Queue "Inbox to-$Me, oldest first" $Inbox
        Show-Queue "Sent to-$Peer, unclaimed" $Outbox
        Show-Queue 'Claimed in working/' $Working
    }

    'send' {
        if (-not $Slug -or -not $Subject -or -not $BodyFile) {
            throw 'send requires -Slug, -Subject, and -BodyFile'
        }
        if ($Slug -cnotmatch '^[a-z0-9]+(-[a-z0-9]+)*$') { throw "Slug must be lowercase kebab-case: $Slug" }
        # The sender is already part of the file name.
        if ($Slug -match '^(linux|windows)-') { throw "Slug must not start with a side name: $Slug" }

        $body = [IO.File]::ReadAllText((Resolve-Path -LiteralPath $BodyFile).Path, $Utf8).Trim()
        foreach ($section in $RequiredSections) {
            if ($body -notmatch ('(?m)^' + [regex]::Escape($section) + '\s*$')) {
                throw "Body is missing the '$section' section"
            }
        }
        # Referenced messages must exist so threads stay navigable.
        $referenced = @($Supersedes)
        if ($ReplyTo -ne 'none') { $referenced += $ReplyTo }
        foreach ($ref in $referenced) {
            if (-not (Find-Message $ref)) { throw "Referenced message not found in any queue: $ref" }
        }
        foreach ($old in $Supersedes) {
            if ($old -notmatch "^\d{8}T\d{6}Z-$Me-") { throw "Only your own messages can be superseded: $old" }
        }
        if ($ReplyTo -ne 'none') {
            $parentThread = Get-Header (Find-Message $ReplyTo) 'Thread'
            if (-not $Thread) { $Thread = $parentThread }
            elseif ($parentThread -and $parentThread -ne $Thread) {
                throw "$ReplyTo belongs to thread '$parentThread', not '$Thread'"
            }
        }
        if ($Thread -and $Thread -cnotmatch '^[a-z0-9]+(-[a-z0-9]+)*$') {
            throw "Thread must be lowercase kebab-case: $Thread"
        }

        $now = [DateTime]::UtcNow
        $stem = '{0}-{1}-{2}' -f $now.ToString("yyyyMMdd'T'HHmmss'Z'"), $Me, $Slug
        if (Find-Message "$stem.md") { throw "Message already exists: $stem.md" }

        $lines = New-Object System.Collections.Generic.List[string]
        $lines.Add("# $Subject")
        $lines.Add('')
        $lines.Add("From: $Me")
        $lines.Add("To: $Peer")
        $lines.Add('Created: ' + $now.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'"))
        if ($Thread) { $lines.Add("Thread: $Thread") }
        $lines.Add("Reply-To: $ReplyTo")
        if ($Supersedes.Count -gt 0) { $lines.Add('Supersedes: ' + ($Supersedes -join ', ')) }
        $lines.Add('')
        $lines.Add($body)

        if ($Attach.Count -gt 0) {
            $artifactDir = Join-Path $Artifacts $stem
            New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null
            $lines.Add('')
            $lines.Add('## Attachments')
            $lines.Add('')
            foreach ($file in $Attach) {
                $item = Get-Item -LiteralPath $file
                if ($item.PSIsContainer) { throw "Attach files only; archive the directory first: $file" }
                $target = Join-Path $artifactDir $item.Name
                Copy-Item -LiteralPath $item.FullName -Destination $target
                $hash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
                $recipientPath = if ($Peer -eq 'windows') { "$WindowsRoot\artifacts\$stem\$($item.Name)" }
                                 else { "$LinuxRoot/artifacts/$stem/$($item.Name)" }
                $lines.Add("- ``$recipientPath``")
                $lines.Add("  SHA-256: ``$hash``")
            }
        }

        $tmp = Join-Path $Outbox "$stem.tmp"
        [IO.File]::WriteAllText($tmp, (($lines -join "`n") + "`n"), $Utf8)
        Move-Item -LiteralPath $tmp -Destination (Join-Path $Outbox "$stem.md")
        Write-Output "Sent to-$Peer/$stem.md"

        foreach ($old in $Supersedes) {
            if (Test-Path -LiteralPath (Join-Path $Outbox $old)) {
                Move-Message $old $Outbox $Withdrawn
            }
            elseif (Test-Path -LiteralPath (Join-Path $Working $old)) {
                Write-Output "$old is already claimed; the recipient acts on the Supersedes header."
            }
        }
    }

    'claim' {
        if (-not $Name) { throw 'claim requires a message name' }
        Move-Message $Name $Inbox $Working
    }

    'complete' {
        if (-not $Name) { throw 'complete requires a message name' }
        if ($Name -notmatch "^\d{8}T\d{6}Z-$Peer-") { throw "Only messages from $Peer that you claimed can be completed: $Name" }
        Move-Message $Name $Working $Completed
    }

    'withdraw' {
        if (-not $Name) { throw 'withdraw requires a message name' }
        if ($Name -notmatch "^\d{8}T\d{6}Z-$Me-") { throw "Only your own messages can be withdrawn: $Name" }
        Move-Message $Name $Outbox $Withdrawn
    }

    'prune' {
        $cutoff = [DateTime]::UtcNow.AddDays(-$Days)
        $owned = New-Object System.Collections.Generic.List[object]
        $unowned = New-Object System.Collections.Generic.List[object]
        if (Test-Path -LiteralPath $Artifacts) {
            foreach ($dir in Get-ChildItem -LiteralPath $Artifacts -Directory | Sort-Object Name) {
                $size = (Get-ChildItem -LiteralPath $dir.FullName -Recurse -File | Measure-Object Length -Sum).Sum
                $entry = [pscustomobject]@{ Dir = $dir; Size = [long]$size }
                $settled = (Test-Path -LiteralPath (Join-Path $Completed "$($dir.Name).md")) -or
                           (Test-Path -LiteralPath (Join-Path $Withdrawn "$($dir.Name).md"))
                $created = Get-MessageTime $dir.Name
                if ($settled -and $created -and $created -lt $cutoff) { $owned.Add($entry) }
                elseif (-not $settled -and -not (Find-Message "$($dir.Name).md")) { $unowned.Add($entry) }
            }
        }
        Write-Output ("Prunable: owning message completed or withdrawn, older than {0} days ({1})" -f $Days, $owned.Count)
        foreach ($e in $owned) { Write-Output ("  artifacts/{0}  {1}" -f $e.Dir.Name, (Format-Size $e.Size)) }
        Write-Output ("Unowned artifact directories, left for Jesper ({0})" -f $unowned.Count)
        foreach ($e in $unowned) { Write-Output ("  artifacts/{0}  {1}" -f $e.Dir.Name, (Format-Size $e.Size)) }
        foreach ($queue in $Queues) {
            if (-not (Test-Path -LiteralPath $queue)) { continue }
            foreach ($f in Get-ChildItem -LiteralPath $queue -File | Where-Object { $_.Extension -ne '.md' }) {
                Write-Output ("  legacy attachment: {0}/{1}  {2}" -f (Split-Path -Leaf $queue), $f.Name, (Format-Size $f.Length))
            }
        }
        if ($Apply) {
            foreach ($e in $owned) {
                Remove-Item -LiteralPath $e.Dir.FullName -Recurse
                Write-Output "Deleted artifacts/$($e.Dir.Name)"
            }
        }
        elseif ($owned.Count -gt 0) {
            Write-Output 'Dry run. Rerun with -Apply after Jesper approves this list.'
        }
    }
}
