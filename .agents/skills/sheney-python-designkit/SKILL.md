---
name: sheney-python-designkit
description: DesignKit-specific development conventions based on Sheñey's Python design philosophy. Use when the project uses DesignKit or when explicitly requested to implement an appropriate DesignKit abstraction.
---

# Sheñey DesignKit

This skill defines how to use the `designkit` package according to Sheñey's development philosophy.

DesignKit is intended for:

- Design patterns.
- Domain-oriented types.
- Assertions and validation helpers.
- Matching and searching abstractions.
- Singleton behavior.
- State machines.
- Structural and behavioral patterns.
- Specialized utility types.

Do not introduce DesignKit automatically into every Python project.

Use DesignKit when:

- It is already a dependency of the project.
- The task explicitly requests it.
- A DesignKit abstraction provides a clear improvement over a custom implementation.

# ================================================== #
# INSTALLATION                                       #
# ================================================== #

Install DesignKit using:

```bash
pip install designkit
```

# ================================================== #
# PACKAGE ORGANIZATION                               #
# ================================================== #

DesignKit concepts are organized around:

```text
designkit.behavioral
designkit.structural
designkit.creational
```

Use these namespaces according to the kind of abstraction being implemented.

# ================================================== #
# BEHAVIORAL PATTERNS                                #
# ================================================== #

Use behavioral abstractions when the problem primarily concerns:

- State transitions.
- Matching.
- Searching.
- Interaction patterns.
- Runtime behavior.

Examples may include:

```python
from designkit.behavioral.matcher import Matcher, Searcher
from designkit.behavioral.state import StateMachine
from designkit.behavioral.typing import Assertion, classname
```

Use `StateMachine` when an application genuinely has:

- States.
- Transitions.
- Guards.
- Transition rules.
- Lifecycle behavior.

Do not use a state machine merely because a sequence of `if` statements exists.

# ================================================== #
# MATCHER                                            #
# ================================================== #

Use `Matcher` when matching multiple structured patterns is central to the problem.

Example structure:

```python
derivate: Matcher = Matcher()


@derivate.case(REGEX_PATTERN)
def resolve(search: Searcher) -> str:
    """
    Resolve a matching expression.
    """

    ...
```

Use pattern-based matchers when they simplify the problem.

Do not replace simple conditionals with complex matching infrastructure without a clear benefit.

# ================================================== #
# ASSERTION                                          #
# ================================================== #

Use `Assertion` for explicit validation when it improves the readability of domain validation.

Example:

```python
Assertion(amount).must_be(
    Decimal,
    custom_expt=InvalidAmountError,
)
```

Use `should_be` for boolean validation when the abstraction improves readability.

Use assertion-style helpers to communicate domain expectations.

Do not obscure simple validation behind abstraction when:

```python
isinstance(value, ExpectedType)
```

is clearer.

# ================================================== #
# CREATIONAL TYPES                                   #
# ================================================== #

Use DesignKit domain types when they represent meaningful concepts.

Examples include:

```python
from designkit.creational.types import (
    Currency,
    Currencies,
    Email,
    Money,
    Percentage,
    PhoneNumber,
    URL,
)
```

Prefer domain types over raw primitives when the domain benefits from:

- Validation.
- Parsing.
- Conversion.
- Explicit semantics.

Example:

```python
email: Email = Email(
    quest.text(
        'Please enter your email: ',
        validate=Email.validate,
    ).ask()
)
```

Use a raw `str` when introducing a domain type provides no meaningful benefit.

# ================================================== #
# URL AND TEXT PARSING                               #
# ================================================== #

Use specialized types such as `URL` when parsing and validating URL values is central to the feature.

Example:

```python
url: URL = URL.parse(TEXT)
```

Keep parsing behavior close to the domain abstraction rather than scattering parsing logic throughout unrelated modules.

# ================================================== #
# MONEY AND CURRENCY                                 #
# ================================================== #

Use `Money` and `Currency` when a feature genuinely represents monetary values.

Example:

```python
def exchange_money(
    money: Money,
    target_currency: Currency,
) -> Money:
    """
    Convert money into a target currency.
    """

    return currency.convert(money, target_currency)
```

Do not represent important financial domain behavior as arbitrary tuples or unrelated primitive values when a domain abstraction is already available.

# ================================================== #
# SINGLETON                                          #
# ================================================== #

Use the DesignKit singleton abstraction when a class genuinely requires one shared instance.

Example:

```python
from designkit.creational.singleton import singleton


@singleton
class Config:
    ...
```

Before using a singleton, consider whether:

- Dependency injection.
- Explicit configuration passing.
- Module-level configuration.

would be simpler.

Do not use a singleton merely for convenience.

# ================================================== #
# STRUCTURAL PATTERNS                                #
# ================================================== #

Use structural abstractions when they improve composition or interface behavior.

Example:

```python
from designkit.structural.decorator import decorator
```

Use patterns to solve a structural problem.

Do not introduce decorators or pattern infrastructure solely to make a simple implementation appear more sophisticated.

# ================================================== #
# CLASSNAME                                          #
# ================================================== #

Use `classname` when producing messages that benefit from a consistent representation of runtime types.

Example:

```python
class InvalidAmountError(ValueError):
    """
    Raised when an amount is invalid.
    """

    def __init__(self, value: Decimal) -> None:
        self.__value: Decimal = value
        self.message: str = (
            f'{classname(self)}: '
            f'Invalid amount for the type {classname(value)}'
        )

        super().__init__(self.message)
```

# ================================================== #
# DESIGNKIT AND EXCEPTIONS                           #
# ================================================== #

When DesignKit validation or domain types fail, preserve meaningful error semantics.

Prefer custom domain exceptions when translating low-level failures into application-specific failures.

Example:

```python
try:
    Assertion(amount).must_be(
        Decimal,
        custom_expt=InvalidAmountError,
    )
except InvalidAmountError as e:
    raise PaymentError(amount) from e
```

Only translate exceptions when doing so provides a clearer domain boundary.

# ================================================== #
# DESIGNKIT SELECTION                                #
# ================================================== #

Before introducing a DesignKit abstraction, ask:

1. Does this represent a real design concept?
2. Does DesignKit reduce custom infrastructure?
3. Does it improve type safety or domain clarity?
4. Is the abstraction already familiar within this project?
5. Is the DesignKit implementation clearer than the direct Python implementation?

If the answer is no, prefer ordinary Python.

# ================================================== #
# GENERAL DESIGNKIT PHILOSOPHY                       #
# ================================================== #

DesignKit should strengthen architecture.

It should not become mandatory ceremony.

Prefer:

- Domain clarity.
- Strong types.
- Explicit behavior.
- Reusable abstractions.
- Meaningful patterns.

Avoid:

- Pattern usage without a problem.
- Wrapping simple values unnecessarily.
- Introducing state machines for simple flows.
- Introducing matchers for trivial conditions.
- Using singletons as global-variable replacements.

Use DesignKit where its abstractions make the resulting code more expressive, more maintainable, or more semantically precise.
