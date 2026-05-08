# QATrack+ Manager for Windows

A tool to manage QATrack+ installations on Windows Server, following the [official documentation](https://docs.qatrackplus.com/en/stable/install/win.html).

## Features
- **Automated Setup**: (New) Installs Python and Git via `winget` if they are missing.
- **System Scan**: Check for prerequisites (Python, Git, IIS, Chrome, etc.).
- **Service Management**: Control CherryPy and Django Q services.
- **Database Testing**: Support for SQL Server, MySQL, PostgreSQL, and SQLite.
- **Installation Wizard**: (In Progress) Automated setup of QATrack+ on Windows.

## Quick Start

1. **Open PowerShell** as Administrator.
2. Navigate to this folder.
3. Run the bootstrap script:
   ```powershell
   ./bootstrap.ps1
   ```
4. Once setup is complete, run the manager:
   ```powershell
   ./run-manager.ps1
   ```

## Requirements
- Windows Server (or Windows 10/11 for testing)
- Python 3.8+
- Git for Windows
