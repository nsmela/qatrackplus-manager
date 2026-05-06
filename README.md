# QA Track Plus Manager

A Python-based management tool for QA Track Plus installations on Ubuntu. This tool replaces the legacy bash manager with a more robust, layered architecture.

## Features
- **Auto-Update**: Automatically checks for and installs updates from GitHub on startup.
- **System Scan**: Comprehensive check of server health, database services, and application state.
- **Install/Upgrade**: Automates the installation and upgrade process for QA Track Plus v3 and v4.
- **Backup/Restore**: Handles full backups of databases (Postgres, MySQL, SQL Server, SQLite) and media files.
- **Local & Remote**: Supports running locally on the server or remotely over SSH.

## Installation

To install the manager on a new Ubuntu server, run the following command:

```bash
curl -sSL https://raw.githubusercontent.com/nsmela/qatrackplus-manager/main/bootstrap.sh | sudo bash
```

## Usage

After installation, run the manager using:

```bash
sudo qatrackplus-manager
```

## Development

The project uses `setuptools` and `pyproject.toml`. To install for development:

```bash
pip install -e .
```
