# Security Policy

## Reporting a vulnerability

**Do not report security vulnerabilities through public GitHub issues.**

Use GitHub's private vulnerability reporting instead:

1. Open the repository's **Security** tab.
2. Select **Report a vulnerability**.
3. Provide the details requested below.

If private reporting is unavailable, contact the maintainer through the
[iamteedoh GitHub profile](https://github.com/iamteedoh).

## What to include

- A description of the issue and its potential impact
- Reproduction steps or a minimal proof of concept
- The affected release, commit, platform, and component
- A suggested remediation, if known

Never include live bearer tokens, passwords, SSH keys, private hostnames, or
unredacted logs in a report.

## Security-sensitive areas

videoMerge is a local command-line tool that invokes ffmpeg on user-supplied
directories, so the most sensitive surfaces are:

- Construction of ffmpeg command lines from file names and encoder settings
- Generation and escaping of the ffmpeg concat list file (crafted file names)
- Handling of interactively entered filesystem paths (expansion, resolution)
- Creation and cleanup of temporary files and directories inside target folders
- Parsing of external command output (`ffmpeg -encoders`) and `/etc/os-release`

## Supported versions

Security fixes land on `main` and ship in the next tagged source release. Test
against the latest release or `main` before reporting an issue.
