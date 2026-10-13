
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

## 🗂️ Folder About

This folder contains the official Finance Scraper website.

The localized Home page is served at `/{locale}/home`. Visiting `/` selects a supported browser language (falling back to Spanish), and `/{locale}` redirects to that locale's Home page.

The website is built with Astro.js and Tailwind CSS and is responsible for:
- Shared, localized site navigation
- Product information and executable downloads
- Documentation access
- SEO optimization
- Internationalization

<p align="right">
    <strong><a href="#readme-top">↑ To Top ↑</a></strong>
</p>

---

## 🚀 Getting Started
The step by step guide to launch the website locally.

> [!IMPORTANT]
> Make sure you have `pnpm` installed globally before proceeding. You can install it using `npm install -g pnpm`.

1. Clone the repository and navigate to the website folder:
```bash
git clone https://github.com/sheniey/finance_scraper.git
cd finance_scraper/website
```

2. Install the dependencies:
```bash
pnpm install
```

3. Start the local development server:
```bash
pnpm dev
```

> [!NOTE]
> To build the production site, use `pnpm build` instead of `pnpm dev`.

4. Go to your browser and open `http://localhost:4321`:

<br>

| Command                   | Action                                           |
| :------------------------ | :----------------------------------------------- |
| `pnpm install`             | Installs dependencies                            |
| `pnpm dev`             | Starts local dev server at `localhost:4321`      |
| `pnpm build`           | Build your production site to `./dist/`          |
| `pnpm preview`         | Preview your build locally, before deploying     |
| `pnpm astro ...`       | Run CLI commands like `astro add`, `astro check` |
| `pnpm astro -- --help` | Get help using the Astro CLI                     |

<p align="right">
    <strong><a href="#readme-top">↑ To Top ↑</a></strong>
</p>

---

## 🚀 Contributing
We welcome contributions from the community. If you would like to contribute, please follow these steps:

> [!IMPORTANT]
> When contributing, ensure that you are modifying only one section of the repository. In this case, only the `website` section.

1. Make a **Fork** of this repository.

2. Create a new branch for your feature or bugfix:
```bash
git checkout -b {branch}/{branch_name}

# Recommended : Git >= 2.23.
git switch -c {branch}/{branch_name}
```

**We recommend following the pattern below when naming a branch for your feature:**

| Prefix | Purpose |
|---------|---------|
| feat/ | New feature |
| fix/ | Bug fix |
| docs/ | Documentation |
| test/ | Tests |
| refactor/ | Refactoring |
| chore/ | Maintenance |
| style/ | Formatting and styling |

3. Add your changes to your Fork and commit them:
```bash
git add .
git commit -m "{branch}: <description>"
```

4. Push your changes to your branch:
```bash
git push origin {branch}/{branch_name}
```

> [!WARNING]
> This command must receive the name of your branch and your implementation exactly as defined in step two.

5. Open a Pull Request and describe the changes you have made.

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
