"""Stoic adapter — stub until the Stoic catalog is seeded.

Returning a structured `StoicStubResult` shape from the HTTP layer is preferable
to having Stoic mimic the Christian shape with empty/fake data. The variant
boundary exists; that's the point. The stub is sized for the HTTP layer to
detect and serialize correctly without having to special-case Christian.
"""

from app.lookup.base import LookupRequest


class StoicAdapter:
    app_variant = "stoic"

    async def select(self, req: LookupRequest) -> dict:
        return {
            "status": "not_implemented",
            "appVariant": "stoic",
            "message": (
                "Stoic passage lookup is not yet implemented. "
                "The catalog has not been seeded."
            ),
        }
