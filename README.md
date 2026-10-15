
<div align="center">
<a name="readme-top"></a>

<a href="https://www.financescraper.com/" target="_blank" rel="noopener noreferrer">
  <img src="https://raw.githubusercontent.com/sheniey/finance_scraper/refs/heads/main/website/public/icons/fs_banner_dark_px.png" alt="Logo" width="800" />
</a>

<br>

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]

</div>

<br>
<br>
<br>

Finance Scraper is a tool for generating **financial reports** and insights from various data sources with colorful feedbacks, deep analysis, AI explanations, and customizable report formats. Finance Scraper offers a local-first, synchronization source database, privacy-focused, user-friendly, concurrent, extensible, customizable and robust tool for managing and analyzing financial data.

<br>

## 🗂️ Repository Structure
The repository is structured as follows:

```
/
├── desktop_app/          # "GUI"
|   ├── electron/         # Electron logic for the desktop app
|   ├── preload/          # Preload scripts for the Electron app
|   ├── public/           # Public assets for the desktop app
|   ├── shared/           # Shared resources for the desktop app
|   ├── src/              # Source code for the desktop app
|   ├── tests/            # Unit tests about consuming logic
|   └── README.md         # README for the desktop_app folder
|
├── finance_scraper/      # "API & Terminal CLI"
|   ├── api/              # FastAPI backend for the Finance Scraper application
|   ├── bruno/            # Files for API management with Bruno
|   ├── scripts/          # Utilities and scripts for development
|   ├── src/
|   |   ├── datatypes/    # Private datatypes used within the app
|   |   ├── finance/      # Python core for Finance Scraper
|   |   ├── finance_core/ # Rust core for Finance Scraper
|   |   └── nexis/        # Machine Learning integration for Finance Scraper
|   ├── stubs/
|   |   └── finance_core/ # .pyi stubs for the finance_core/
|   ├── tests/            # Pytest unit tests for the finance_scraper folder
|   └── README.md         # README for the finance_scraper folder
|
└── website/              # "Download Landing Page"
    ├── public/           # Public assets for the website
    ├── src/              # Astro.js|React|TypeScript source code for the website
    └── README.md         # README for the website folder
```

<p align="right">
    <strong><a href="#readme-top">↑ To Top ↑</a></strong>
</p>

---

## 🚀 Contributing
We welcome contributions from the community. If you would like to contribute, please follow these steps:

> [!IMPORTANT]
> When contributing, ensure that you are modifying only one section of the repository.

1. Make a **Fork** of this repository.

2. Create a new branch for your feature or bugfix:
```bash
git switch -c {prefix}/{branch_name}
```
Alternatively, you can use `git checkout -b` (Git >= 2.23 is recommended for git switch).

**We recommend following the naming convention for branch names:**

| Prefix | Purpose |
|---------|---------|
| feat/ | New feature |
| fix/ | Bug fix |
| docs/ | Documentation |
| test/ | Tests |
| refactor/ | Refactoring |
| chore/ | Maintenance |
| style/ | Formatting and styling |

**Example:**
- `feat/support-openai-integration`
- `fix/mobile-layout`
- `docs/add-cicd-pipeline`

3. Add your changes to your Fork and commit them:
```bash
git add .
git commit -m "{prefix}: <description>"
```
Use the same prefix for your commit message as your branch name.

4. Push your changes to your branch:
```bash
git push origin {prefix}/{branch_name}
```

> [!WARNING]
> This command must receive the name of your branch and your implementation exactly as defined in step two.

5. Open a Pull Request against the original repository's appropriate branch. Include a clear description of your changes and their purpose.

### ⚠️ Before submitting

Make sure that:
- Your changes are limited to the section of the repository you are working on.
- Your branch follows the recommended naming convention.
- Your commit messages use the appropriate prefix. You can add a scope in parentheses after the prefix if needed.
- Your Pull Request clearly describes your implementation.

<p align="right">
    <strong><a href="#readme-top">↑ To Top ↑</a></strong>
</p>

---

<br>
<br>
<br>

<div align="center">

**Thanks to all the collaborators for their precious contribution!**

[![Contributors](https://contrib.rocks/image?repo=sheniey/finance_scraper&max=500&columns=20)](https://github.com/sheniey/finance_scraper/graphs/contributors)

</div>


<!-- Repository Links -->
[contributors-shield]: https://img.shields.io/github/contributors/sheniey/finance_scraper.svg?style=for-the-badge
[contributors-url]: https://github.com/sheniey/finance_scraper/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/sheniey/finance_scraper.svg?style=for-the-badge
[forks-url]: https://github.com/sheniey/finance_scraper/network/members
[stars-shield]: https://img.shields.io/github/stars/sheniey/finance_scraper.svg?style=for-the-badge
[stars-url]: https://github.com/sheniey/finance_scraper/stargazers
[issues-shield]: https://img.shields.io/github/issues/sheniey/finance_scraper.svg?style=for-the-badge
[issues-url]: https://github.com/sheniey/finance_scraper/issues
<!-- Repository Links -->
