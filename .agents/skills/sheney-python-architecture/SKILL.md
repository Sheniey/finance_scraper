---
name: sheney-python-architecture
description: Architecture and code organization conventions based on Sheñey's Python development philosophy. Use when designing modules, classes, application structure, exceptions, abstractions, and larger Python features.
---

# Sheñey Python Architecture

This skill defines how Python code should be organized and designed.

The primary architectural philosophy is:

- Explicit structure.
- Strong domain modeling.
- Clear ownership of responsibilities.
- Custom exceptions for meaningful failures.
- Strong typing.
- Encapsulation where state and invariants require it.
- Reusable abstractions without unnecessary overengineering.
- Predictable module organization.

# ================================================== #
# MODULE RESPONSIBILITY                              #
# ================================================== #

Every module should have a clear responsibility.

Avoid modules that become generic containers for unrelated functionality.

Prefer domain-oriented modules.

Examples:

```text
user/
    models.py
    repository.py
    exceptions.py
    service.py
```

Prefer this over:

```text
utils.py
misc.py
stuff.py
classes.py
```

when the code has a clear domain.

Use `utils.py` or `helpers.py` only for genuinely general-purpose functionality that does not belong naturally to another domain.

# ================================================== #
# MODULE STRUCTURE                                   #
# ================================================== #

When a module contains several categories of declarations, prefer the following conceptual order:

1. Module documentation.
2. Imports.
3. Global exceptions.
4. Focused exceptions.
5. Type aliases.
6. Dataclasses, models, and typed dictionaries.
7. Helper functions.
8. Main classes and functions.
9. Features or high-level behavior.
10. Main execution.

Example:

```text
module docstring

imports


global exceptions


focused exceptions


type aliases


models


helpers


classes


functions


features


main
```

Not every module needs every section.

Do not create empty structural categories merely to satisfy the ordering.

# ================================================== #
# EXCEPTION HIERARCHY                                #
# ================================================== #

Create exception hierarchies around meaningful domains.

Prefer a global base exception:

```python
class PaymentException(Exception):
    """
    Base exception for payment failures.
    """

    pass
```

Then derive focused failures:

```python
class InvalidAmountError(PaymentException, ValueError):
    """
    Raised when a payment amount is invalid.
    """

    def __init__(self, amount: Decimal) -> None:
        self.amount: Decimal = amount
        self.message: str = f'Invalid payment amount: {amount}.'

        super().__init__(self.message)
```

Use exception inheritance to communicate relationships between failures.

Do not create custom exceptions for trivial failures that are already adequately represented by built-in exceptions.

# ================================================== #
# DATA MODELS                                        #
# ================================================== #

Choose the simplest appropriate data abstraction.

Prefer:

- `dataclass` for lightweight Python data structures.
- `Pydantic` models for validation and external data boundaries.
- `TypedDict` for dictionary-shaped structures that should remain dictionaries.
- Ordinary classes when behavior and invariants are central.

Do not use a class merely to wrap a single value unless the value represents an important domain concept.

Do not use `TypedDict` as a replacement for every model.

# ================================================== #
# ENCAPSULATION                                      #
# ================================================== #

Encapsulate state when the class owns:

- Mutable internal state.
- Validation rules.
- Invariants.
- Lifecycle behavior.
- Derived state.

Prefer private double-underscore attributes for internal class state when external mutation should be discouraged.

Expose behavior instead of exposing unnecessary mutable implementation details.

Example:

```python
class Account:
    """
    Represent a bank account.
    """

    def __init__(self, balance: Money) -> None:
        self.__balance: Money = balance

    @property
    def balance(self) -> Money:
        return self.__balance

    def deposit(self, amount: Money) -> None:
        self.__balance += amount
```

Do not create getters and setters mechanically.

A public immutable or simple data attribute may be appropriate when no encapsulation benefit exists.

# ================================================== #
# CLASS RESPONSIBILITIES                             #
# ================================================== #

A class should represent a coherent concept.

Prefer one class with a clear responsibility over a class that combines:

- Persistence.
- HTTP communication.
- Validation.
- Formatting.
- Business rules.
- CLI behavior.

Separate these responsibilities when doing so improves clarity.

Do not split a simple feature into many classes merely to imitate enterprise architecture.

# ================================================== #
# HELPER FUNCTIONS                                   #
# ================================================== #

Helper functions should support a specific module or feature.

Use a leading underscore for internal helpers:

```python
def _normalize_email(value: str) -> str:
    """
    Normalize an email value.
    """

    return value.strip().lower()
```

Promote a helper into a public abstraction only when:

- It represents a meaningful concept.
- It is reused across modules.
- It deserves an explicit API.

# ================================================== #
# FEATURES                                           #
# ================================================== #

A feature should be composed from smaller responsibilities where appropriate.

Prefer:

```text
input
    ↓
validation
    ↓
domain behavior
    ↓
persistence or external communication
    ↓
presentation
```

Avoid mixing all stages into one large function when the feature is sufficiently complex to benefit from separation.

For small features, keep the implementation simple and local.

# ================================================== #
# MAIN EXECUTION                                     #
# ================================================== #

Separate reusable behavior from execution entry points.

Prefer:

```python
def main() -> None:
    """
    Execute the application.
    """

    ...


if __name__ == '__main__':
    main()
```

The `main` function should orchestrate behavior rather than contain every implementation detail.

# ================================================== #
# DESIGN PRINCIPLES                                  #
# ================================================== #

Prefer abstractions when they solve an existing problem.

Do not introduce:

- Base classes.
- Generic frameworks.
- Registries.
- Factories.
- Patterns.
- Custom infrastructure.

without a concrete reason.

When deciding whether to introduce an abstraction, ask:

1. Is there meaningful duplication?
2. Is there a stable concept being represented?
3. Is variation expected?
4. Does the abstraction simplify the public API?
5. Does it reduce complexity rather than relocate it?

If the answer is mostly no, prefer the simpler implementation.

# ================================================== #
# TYPING AS ARCHITECTURE                             #
# ================================================== #

Use types to communicate architecture.

Meaningful aliases can represent important concepts:

```python
type UserId = int
type Callback[T] = Callable[[T], None]
```

Use domain-specific classes when a primitive alias is not sufficient to communicate behavior or validation.

Prefer stronger domain types when misuse of a primitive would represent a meaningful bug.

# ================================================== #
# SPECIAL METHODS                                    #
# ================================================== #

Implement special methods intentionally.

Consider:

- `__repr__` for useful developer representation.
- `__str__` for meaningful human representation.
- `__eq__` for value semantics.
- `__hash__` only when hashability is semantically correct.

Do not automatically make mutable objects hashable.

Use dataclass-generated methods when they correctly represent the intended semantics.

# ================================================== #
# ARCHITECTURAL PRIORITIES                           #
# ================================================== #

When architectural choices conflict, prioritize:

1. Correctness.
2. Clear responsibility boundaries.
3. Explicit domain behavior.
4. Maintainability.
5. Type safety.
6. Simplicity.
7. Reusability.

Do not sacrifice simplicity merely to demonstrate an architectural pattern.
