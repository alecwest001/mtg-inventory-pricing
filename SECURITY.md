# Security Policy

## Supported Versions

This project is currently under active development and does not maintain multiple released versions.

| Version | Supported          |
| ------- | ------------------ |
| Current | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please do not publicly disclose the details in a GitHub issue.

Instead, please contact the repository owner privately with:

* A description of the vulnerability
* Steps to reproduce the issue
* Any relevant logs, screenshots, or code
* The potential impact of the issue

I will review reported vulnerabilities and respond as soon as reasonably possible.

## API Keys and Sensitive Information

Do not commit API keys, credentials, passwords, or other sensitive information to this repository.

The application uses local configuration files for API credentials. These values should remain local and should never be included in commits, pull requests, or distributed application files.

Users are responsible for protecting their own API credentials. API keys should not be embedded in source code, compiled executables, or other publicly distributed files.

If a credential is accidentally committed or exposed, it should be revoked or rotated immediately.

When reporting a security issue, do not include API keys, passwords, tokens, or other sensitive credentials in the report. Describe the issue without exposing the credential whenever possible.

