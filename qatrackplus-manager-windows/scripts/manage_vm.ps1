# Helper script for managing the Vagrant Test VM
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop", "status", "rdp", "snapshot-save", "snapshot-restore", "destroy")]
    $Action,
    
    [Parameter(Mandatory=$false)]
    $Name = "pre-install"
)

switch ($Action) {
    "start" {
        Write-Host "Starting QATrack+ Manager Test VM..." -ForegroundColor Cyan
        vagrant up --provider=virtualbox
    }
    "stop" {
        Write-Host "Stopping VM..." -ForegroundColor Yellow
        vagrant halt
    }
    "status" {
        vagrant status
    }
    "rdp" {
        Write-Host "Connecting to VM via RDP..." -ForegroundColor Green
        vagrant rdp
    }
    "snapshot-save" {
        Write-Host "Saving snapshot '$Name'..." -ForegroundColor Cyan
        vagrant snapshot save $Name
    }
    "snapshot-restore" {
        Write-Host "Restoring snapshot '$Name'..." -ForegroundColor Cyan
        vagrant snapshot restore $Name
    }
    "destroy" {
        if ((Read-Host "Are you sure you want to DESTROY the VM? (y/N)") -eq 'y') {
            vagrant destroy -f
        }
    }
}
