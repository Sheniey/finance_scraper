
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Role:
    name: str
    permissions: frozenset[str]

    def has_permission(self, permission: str) -> bool:
        return 'everything' in self.permissions or permission in self.permissions
