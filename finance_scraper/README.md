
# Finance Scraper - API & CLI

Finance Scraper is a tool for generating financial reports and insights from various data sources with colorful feedbacks, deep analysis, AI explanations, and customizable report formats. Finance Scraper offers a local-first, synchronization source database, privacy-focused, user-friendly, concurrent, extensible, customizable and robust tool for managing and analyzing financial data.

---

a

## Windows executable and installer

The Windows build uses PyInstaller in onedir mode and packages the Nexis model and the finance YAML, JSON, and SQL resources. Install the build dependency group, then run these commands from the project root:

```powershell
uv sync --group build
uv run --group build pyinstaller --noconfirm --clean finance-cli.spec
ISCC.exe installer.iss
```

The executable is written to `dist/finance-scraper`; the Inno Setup installer is written to `dist/installer`. The installer defaults to a per-user installation, offers an optional desktop shortcut, and can add the install folder to the current user's `PATH` so `finance-scraper` is available in new terminal windows. No administrator access is required.

The frozen app defaults `APP_ENV` to `production` when it is unset. Secrets are not bundled. API keys configured from the desktop app are stored in a local `.env` beside `finance-scraper.exe`; only the supported AI-provider keys are passed to the desktop API.
