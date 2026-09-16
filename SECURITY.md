# Security Policy

## Driver Integrity & Signature Verification
Windows 10 and 11 require all 64-bit kernel-mode drivers to possess valid digital signatures. 

**Windows Driver Updater adheres strictly to this policy:**
- **No Unsigned Drivers**: The updater will never attempt to install unsigned, self-signed, or test-signed drivers.
- **Official CDN Only**: Driver packages are retrieved exclusively from Microsoft's official CDN (`download.windowsupdate.com`).
- **No Modified Packages**: Archives are expanded using Windows native utilities and installed directly into the protected Driver Store.

## Reporting a Vulnerability
If you discover a potential security flaw in this application, please report it responsibly by opening a private security advisory on GitHub or contacting the repository owner at [Abdul Moiz Ansari](https://github.com/AbdulMoizAns).
