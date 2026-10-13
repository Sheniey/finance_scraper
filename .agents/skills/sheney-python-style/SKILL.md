---
name: sheney-python-style
description: Strongly opinionated Python coding style based on Sheñey's coding conventions. Use when writing, rewriting, reviewing, or modifying Python code.
---

# Sheñey Python Style

This skill defines how Python code should look and be written.

It is strongly based on Sheñey's original coding style. The primary goals are:

- Explicit and readable code.
- Strong type annotations.
- Consistent visual structure.
- Predictable formatting.
- Clear separation between code sections.
- Modern Python syntax.
- Minimal ambiguity in implementation decisions.

Apply these conventions consistently unless an existing project convention explicitly conflicts with them.

# ================================================== #
# DOCSTRINGS                                        #
# ================================================== #

- Use triple double quotes (`"""`) for all docstrings.
- Place a newline immediately after the opening triple quotes.
- This newline convention does not apply to very short exception docstrings when the project already uses single-line exception documentation.
- Include a brief summary of the purpose of a function or class.
- Keep docstrings concise and informative.
- For complex functions or classes, document:
    - Parameters.
    - Return values.
    - Raised exceptions.
    - Important behavior or invariants.

Example:

```python
def add(a: int, b: int) -> int:
    """
    Add two integers.
    """

    return a + b
```

For more complex behavior:

```python
def divide(a: int, b: int) -> float:
    """
    Divide two integers.

    Parameters:
        a (int): The numerator.
        b (int): The denominator.

    Returns:
        float: The result of the division.

    Raises:
        ValueError: If the denominator is zero.
    """

    if b == 0:
        raise ValueError('Denominator cannot be zero.')

    return a / b
```

# ================================================== #
# STRINGS AND QUOTES                                 #
# ================================================== #

- Prefer single quotes for ordinary strings.
- Use double quotes when single quotes would require unnecessary escaping or reduce readability.
- Always use triple double quotes for docstrings.

Preferred:

```python
name: str = 'Sheñey'
message: str = "Sheñey's coding style"
```

Avoid unnecessary double quotes:

```python
name: str = "Sheñey"
```

# ================================================== #
# IMPORTS                                            #
# ================================================== #

Keep imports at the top of the file, immediately after the module-level docstring when one exists.

Organize imports into the following groups:

1. Standard library.
2. Third-party dependencies.
3. First-party application imports.
4. Local application imports when applicable.

Separate groups with a blank line.

Prefer absolute imports.

Avoid wildcard imports.

Prefer logically grouped multi-line imports when importing multiple related symbols.

Example:

```python
import os
import sys

from dataclasses import dataclass
from typing import Any, Callable

import httpx
from pydantic import BaseModel

from api.core import some_core_function
from api.some_module import some_function

from finance.config import settings
from finance.services.mymodule import myservice
from finance.services.mymodule.exceptions import (
    ACustomError,
    AnotherCustomError,
    MyCustomException,
)
```

# ================================================== #
# NEWLINES AND FILE STRUCTURE                         #
# ================================================== #

Use intentional blank lines to visually separate concepts.

For modules containing multiple kinds of code, prefer the following order:

```text
module docstring

imports


exceptions


type aliases


dataclasses, models and typed dictionaries


helper functions


functions and classes


features


main execution


if __name__ == '__main__':
```

Do not compress unrelated declarations together merely to reduce the number of lines.

Prefer visual separation when moving between different conceptual sections.

# ================================================== #
# TYPE ANNOTATIONS                                   #
# ================================================== #

Use type annotations for:

- Function parameters.
- Return values.
- Class attributes.
- Important internal variables when the annotation improves clarity.

Avoid multiple unrelated variable definitions on a single line.

Prefer meaningful aliases for complex types.

Example:

```python
type Hook[T] = Callable[[T, list[Any], dict[str, Any]], None]
```

Use `TypedDict` for structured dictionaries when a dictionary is genuinely the appropriate abstraction.

Do not overuse type aliases for trivial primitive types.

Prefer:

```python
type RenderingMode = Literal['pdf', 'html']
```

over repeatedly writing a complex type throughout the codebase.

# ================================================== #
# MODERN TYPING                                      #
# ================================================== #

Prefer modern Python typing syntax when supported by the project's minimum Python version.

Prefer:

```python
str | None
```

over:

```python
Optional[str]
```

unless compatibility or a specific API requires `Optional`.

Prefer:

```python
int | str
```

over:

```python
Union[int, str]
```

when the project supports modern union syntax.

Use `Literal` for constrained literal values.

Use `Final` aliased as `Const` for constants when explicit constant typing is valuable.

Example:

```python
from typing import Final as Const, Literal


type Status = Literal['success', 'failure']

MAX_RETRIES: Const[int] = 5
```

# ================================================== #
# GENERICS                                           #
# ================================================== #

Use generics when they provide meaningful type safety or reusability.

Avoid introducing generic abstractions when a concrete implementation is simpler.

For projects targeting modern Python versions, prefer modern type parameter syntax where available.

Example:

```python
class Box[T, E: Enum]:
    """
    Store typed content with a constrained state type.
    """

    def __init__(self, content: T, possible_state: E) -> None:
        self.__content: T = content
        self.__possible_state: E = possible_state
```

# ================================================== #
# SECTION COMMENTS                                   #
# ================================================== #

Use section comments to clearly delineate important parts of a module.

Do not use section comments for the module docstring or imports.

Use the following format:

```python
# ================================================== #
# SECTION NAME                                       #
# ================================================== #
```

Section names must be uppercase.

Example:

```python
# ================================================== #
# TYPE ALIASES                                       #
# ================================================== #

type UserId = int


# ================================================== #
# GLOBAL EXCEPTIONS                                  #
# ================================================== #

class ApplicationException(Exception):
    """
    Base exception for the application.
    """

    pass
```

Do not create excessive sections for very small modules.

# ================================================== #
# MATCH VS IF-ELSE                                   #
# ================================================== #

Use `match` when multiple branches depend primarily on:

- The value of one variable.
- The shape or type of one value.
- A small structured tuple or pattern.

Example:

```python
match value:
    case 1:
        print('Value is 1')
    case 2:
        print('Value is 2')
    case _:
        print('Value is something else')
```

Use `if` and `elif` for general conditional logic involving:

- Independent conditions.
- Complex expressions.
- Boolean combinations.
- Conditions that do not naturally represent pattern matching.

Do not force `match` into situations where ordinary conditionals are clearer.

# ================================================== #
# CLASSES                                            #
# ================================================== #

Prefer explicit encapsulation for class-owned state.

When an attribute represents internal state or should not be manipulated directly, prefer double underscore private attributes:

```python
class Counter:
    """
    Represent a mutable counter.
    """

    def __init__(self, value: int) -> None:
        self.__value: int = value

    @property
    def value(self) -> int:
        return self.__value
```

Use:

- `@property` for controlled access.
- `@staticmethod` for behavior independent of instance and class state.
- `@classmethod` for behavior related to class construction or class-level state.

Prefer read-only properties by default.

Add setters or deleters only when mutation through the public API is genuinely required.

Implement special methods such as:

- `__str__`
- `__repr__`
- `__hash__`
- `__eq__`
- arithmetic methods

when they provide meaningful semantics for the class.

Do not implement special methods merely as boilerplate.

# ================================================== #
# EXCEPTIONS                                         #
# ================================================== #

Prefer specific exceptions over generic exceptions.

Use custom exceptions for meaningful domain-specific failure cases.

Global application exceptions should normally end in `Exception`.

Focused failures should normally end in `Error` or `Warning`.

Keep exception classes simple unless they need contextual information.

When an exception contains important runtime context:

- Store that context explicitly.
- Build a formatted message.
- Pass the message to the parent exception.

Example:

```python
class StateMachineException(Exception):
    """
    Base exception for state machine errors.
    """

    pass


class GuardRejectedError(StateMachineException):
    """
    Raised when a guard condition is rejected.
    """

    def __init__(self, guard: Callable[..., object]) -> None:
        self.guard: Callable[..., object] = guard
        self.message: str = f'Guard condition {guard} was rejected.'

        super().__init__(self.message)
```

# ================================================== #
# TRY AND EXCEPT                                     #
# ================================================== #

Keep `try` blocks minimal.

Catch specific exceptions.

Avoid bare `except`.

When translating one exception into another, preserve the original traceback:

```python
try:
    result: float = divide(10, 0)
except ValueError as e:
    raise DivideByZeroError('Cannot divide by zero.') from e
```

# ================================================== #
# CONSTANTS AND LITERALS                             #
# ================================================== #

Use uppercase letters and underscores for constants.

Prefix private or helper constants with an underscore.

Example:

```python
from typing import Final as Const


MAX_RETRIES: Const[int] = 5
_DEFAULT_TIMEOUT: Const[int] = 30
```

Do not create constants for every literal.

A literal should remain a literal when giving it a name does not improve meaning, reuse, or maintainability.

# ================================================== #
# MODULE NAMES                                       #
# ================================================== #

Use:

- Lowercase names.
- Underscores when necessary.
- Short and descriptive names.

Prefer names that describe responsibility.

Recommended names include:

- `exceptions.py`
- `repository.py`
- `core.py`
- `config.py`
- `settings.py`
- `models.py`
- `schemas.py`
- `utils.py`
- `helpers.py`

Avoid vague module names such as:

- `stuff.py`
- `misc.py`
- `classes.py`

Avoid generic dumping-ground modules.

Prefer a domain-specific module name over:

```text
constants.py
const.py
literals.py
```

when the values belong naturally to a specific domain.

# ================================================== #
# PASS VS ELLIPSIS                                   #
# ================================================== #

Use `pass` when a syntactically required code block intentionally performs no operation.

Use `...` when representing an intentionally omitted implementation, abstract placeholder, or stub where ellipsis communicates that intent more clearly.

Example:

```python
class FutureImplementation:
    ...
```

```python
class EmptyMarker:
    pass
```

# ================================================== #
# GENERAL PRINCIPLES                                 #
# ================================================== #

When multiple implementations are technically valid:

1. Prefer clarity.
2. Prefer explicit typing when it adds useful information.
3. Prefer consistent structure.
4. Prefer modern Python syntax supported by the project.
5. Prefer specific domain concepts over vague abstractions.
6. Avoid unnecessary cleverness.
7. Do not introduce complexity merely to satisfy a stylistic rule.
