# Contributing to Windows Driver Updater

Thank you for your interest in contributing to **Windows Driver Updater**! This project aims to provide a safe, lightweight, and completely transparent alternative to commercial driver tools.

## How Can You Help?
- **Bug Reports**: If a device fails to scan or an update fails to install, open an issue with the device class and Hardware ID.
- **Feature Requests**: Propose new driver repositories, UI enhancements, or automation scripts.
- **Code Contributions**: Submit Pull Requests for enhancements or bug fixes.

## Development Workflow
1. Fork this repository on GitHub.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/win-driver-updater.git
   cd win-driver-updater
   ```
3. Create a feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```
4. Test your changes locally:
   ```powershell
   python main.py --scan
   ```
5. Commit and push your changes:
   ```bash
   git commit -m "feat: Add support for PCI vendor database lookup"
   git push origin feature/my-feature
   ```
6. Submit a Pull Request.

## Code Style
- Use standard Python PEP 8 conventions.
- Ensure all subprocess calls handle exceptions gracefully and avoid blocking the main UI thread.
