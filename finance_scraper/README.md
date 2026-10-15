
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

## 🗂️ API & CLI Section

This project folder contains the Finance Scraper's core, so it includes the API and CLI official components. The pipeline for handle a new report request by api follow these steps:

```json
API
---
1. POST `/login`
   - Request: { "email": "fulanito@example.com", "password": "12345678" }
   - Response: { "access_token": "q1wet31qwq.sa3gdh864ryre.n2ffdgs3" }
2. POST `/reports`
   - Headers: { "Authorization": "Bearer q1wet31qwq.sa3gdh864ryre.n2ffdgs3" }
   - Request: { "ticker": "AAPL", "llm_explanation": true, "filename": "report.pdf", ... }
   - Response: { "report_id": "rpt_1234567890" }
3. GET `/reports/rep_1234567890`
   - Headers: { "Authorization": "Bearer q1wet31qwq.sa3gdh864ryre.n2ffdgs3" }
   - Response: { "status": "completed" }
4. GET `/reports/rep_1234567890/download`
   - Headers: { "Authorization": "Bearer q1wet31qwq.sa3gdh864ryre.n2ffdgs3" }
   - Response: report.pdf
```

<p align="right">
    <strong><a href="#readme-top">↑ To Top ↑</a></strong>
</p>

---

## 🚀 API - Getting Started
The step by step guide to launch the API locally.

> [!IMPORTANT]
> Make sure you have `uv` installed globally before proceeding. You can install it using `pip install uv`.

1. Clone the repository and navigate to the finance_scraper folder:
```bash
git clone https://github.com/sheniey/finance_scraper.git
cd finance_scraper/finance_scraper
```

2. Install the dependencies:
```bash
uv sync
```

3. Start the local development server:
```bash
python -m finance-cli api serve --foreground/--background
```

> [!NOTE]
> To stop in foreground mode, use `Ctrl+C`. To stop in background mode, use `python -m finance-cli api stop`.

4. The API for default runs at `http://0.0.0.0:8765`; **0.0.0.0** refers to all available network interfaces.

<br>

> [!INFO]
> The API documentation (made automatically using OpenAPI Specification) is available at the `/docs` endpoint.

<p align="right">
    <strong><a href="#readme-top">↑ To Top ↑</a></strong>
</p>

---

## 🚀 CLI - Getting Started
The step by step guide to make a report using the CLI locally.

> [!IMPORTANT]
> Make sure you have `uv` installed globally before proceeding. You can install it using `pip install uv`.

1. Clone the repository and navigate to the finance_scraper folder:
```bash
git clone https://github.com/sheniey/finance_scraper.git
cd finance_scraper/finance_scraper
```

2. Install the dependencies:
```bash
uv sync
```

3. Get help for CLI commands:
```bash
python -m finance-cli --help
```

| Command | Action  |
|---------|---------|
| `python -m finance-cli analyze ...` | Analyze a stock and generate a custom report  |
| `python -m finance-cli send ...` | Sends the generated report via email |
| `python -m finance-cli dispatch ...` | Generate all stock reports for an account's watchlist |

3. Get help for DEV-CLI commands:
```bash
python -m finance-dev --help
```

| Command | Action  |
|---------|---------|
| `python -m finance-dev run ...` | Run a script defined in `pyproject.toml:[tool.scripts]` |

> [!INFO]
> Some utils scripts that you can run using `... finance-dev run ...` are `deeptrain_nexis` to train the predictor model (Nexis) and self-adjust its hyperparameters, `train_nexis` to just train the model (Nexis), `build` to build the project, `api-dev` to run the api server in development mode, `test` to run the unit tests, etc...


<br>

> [!INFO]
> The API documentation (made automatically using OpenAPI Specification) is available at the `/docs` endpoint.

<p align="right">
    <strong><a href="#readme-top">↑ To Top ↑</a></strong>
</p>

---

## 🚀 Contributing
We welcome contributions from the community. If you would like to contribute, please follow these steps:

> [!IMPORTANT]
> When contributing, make sure to modify **only the `finance_scraper` section** of the repository. Changes to other sections are outside the scope of this contribution process.

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
- `feat/improve-performance`
- `fix/login-endpoint`
- `docs/add-complexity-analysis`

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
- Your changes are limited to the finance_scraper section.
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

---
