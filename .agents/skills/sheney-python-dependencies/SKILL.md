---
name: sheney-python-dependencies
description: Preferred Python dependency conventions based on Sheñey's development stack. Use when selecting third-party libraries or proposing dependencies for Python projects.
---

# Sheñey Python Dependencies

This skill defines preferred Python dependencies for common development tasks.

These preferences are strongly based on Sheñey's development style.

Do not introduce a dependency merely because it appears in this skill.

Prefer a dependency when:

- The project already uses it.
- The task explicitly benefits from it.
- It significantly improves clarity or maintainability.
- The standard library is insufficient or substantially less appropriate.

Avoid dependency proliferation.

# ================================================== #
# TERMINAL INTERACTION                               #
# ================================================== #

For simple interactive terminal prompts, prefer:

```text
questionary
```

Use it for:

- Text input.
- Selection menus.
- Confirmations.
- Interactive command-line workflows.

For rich terminal output, prefer:

```text
rich
```

Use it for:

- Tables.
- Panels.
- Syntax highlighting.
- Styled output.
- Improved logging presentation.

For complex terminal user interfaces, prefer:

```text
textual
```

Do not introduce Textual for a simple command-line program.

# ================================================== #
# HTTP                                               #
# ================================================== #

For HTTP requests, prefer:

```text
httpx
```

Use it when HTTP communication is required.

Prefer its modern API and async capabilities when asynchronous communication is genuinely useful.

Do not introduce asynchronous HTTP merely because a library supports it.

# ================================================== #
# DATA MODELS                                        #
# ================================================== #

For lightweight Python data containers, prefer:

```text
dataclasses
```

For validation-heavy models and external data boundaries, prefer:

```text
pydantic
```

Choose the simplest abstraction appropriate for the task.

Do not use Pydantic for every internal object when a dataclass is sufficient.

# ================================================== #
# DATA AND NUMERICAL COMPUTATION                      #
# ================================================== #

For tabular data manipulation and analysis, prefer:

```text
pandas
```

For numerical computation, prefer:

```text
numpy
```

Do not introduce Pandas or NumPy for trivial operations that the standard library handles clearly.

# ================================================== #
# MACHINE LEARNING AND AI                            #
# ================================================== #

For conventional machine learning workflows, prefer:

```text
scikit-learn
```

For complex deep learning or advanced AI workflows, prefer:

```text
tensorflow
```

or:

```text
torch
```

Choose one based on the project ecosystem and requirements.

Do not introduce multiple deep-learning frameworks without a clear interoperability requirement.

# ================================================== #
# API DEVELOPMENT                                    #
# ================================================== #

For Python API development, prefer:

```text
fastapi
```

Use it when building HTTP APIs or backend services that benefit from typed request and response models.

# ================================================== #
# COMMAND-LINE INTERFACES                            #
# ================================================== #

For structured command-line interfaces, prefer:

```text
typer
```

Use it when the CLI has:

- Multiple commands.
- Typed arguments.
- Options.
- A reusable command structure.

For very small scripts, ordinary `argparse` or a minimal approach may be sufficient.

# ================================================== #
# WEB SCRAPING                                       #
# ================================================== #

For HTML parsing and conventional web scraping, prefer:

```text
beautifulsoup4
```

Use additional HTTP tooling such as `httpx` when network access is required.

Do not use a browser automation framework when static HTTP and HTML parsing are sufficient.

# ================================================== #
# PDF                                                #
# ================================================== #

For PDF generation and manipulation, prefer:

```text
reportlab
```

Use it when direct programmatic PDF generation is required.

# ================================================== #
# DATA FORMATS                                       #
# ================================================== #

Prefer the standard library when it adequately supports the format.

Recommended tools:

- JSON → `json`
- CSV → `csv`
- YAML → `pyyaml`
- TOML → `tomllib` when available, otherwise a suitable TOML package

Do not introduce a dependency for a format already well-supported by the target Python version's standard library.

# ================================================== #
# ENVIRONMENT VARIABLES                              #
# ================================================== #

For convenient `.env` file loading, prefer:

```text
python-dotenv
```

Use environment variables for environment-specific configuration.

Avoid hardcoding credentials or deployment-specific configuration.

# ================================================== #
# LOGGING                                            #
# ================================================== #

Prefer the standard library:

```text
logging
```

Combine it with:

```text
rich
```

when enhanced terminal presentation is useful.

Do not replace structured logging with `print`.

# ================================================== #
# REGULAR EXPRESSIONS                                #
# ================================================== #

Prefer the standard library:

```text
re
```

Use regular expressions when pattern matching is genuinely clearer than ordinary string operations.

Do not use regex for simple operations such as straightforward prefix checks or splitting.

# ================================================== #
# TESTING                                            #
# ================================================== #

For unit and integration testing, prefer:

```text
pytest
```

Write tests around observable behavior and important domain invariants.

Avoid tests that merely duplicate implementation details.

# ================================================== #
# FILESYSTEM                                         #
# ================================================== #

For file and directory manipulation, prefer:

```text
pathlib
```

Prefer `Path` objects over manually concatenated filesystem strings.

# ================================================== #
# DATE AND TIME                                      #
# ================================================== #

Prefer the standard library:

```text
datetime
```

Use timezone-aware values when the application operates across timezones or interacts with external systems where timezone ambiguity matters.

# ================================================== #
# COMPLEXITY ANALYSIS                                #
# ================================================== #

For explicit code complexity analysis, the preferred tool is:

```text
complexipy
```

Use complexity metrics as feedback rather than as an excuse to fragment simple code into excessive abstractions.

# ================================================== #
# MATH ANIMATION                                     #
# ================================================== #

For mathematical animations, prefer:

```text
manim
```

Use it when producing visual mathematical or educational animations.

# ================================================== #
# DEPENDENCY SELECTION                               #
# ================================================== #

Before adding a dependency, consider:

1. Can the standard library solve this clearly?
2. Is the dependency already part of the project?
3. Does the dependency solve a meaningful problem?
4. Does it reduce complexity?
5. Is it actively compatible with the project's Python version?
6. Would another developer reasonably understand the dependency?

Prefer fewer dependencies when functionality and maintainability remain equivalent.
