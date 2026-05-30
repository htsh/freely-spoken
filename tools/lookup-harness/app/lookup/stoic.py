from app.lookup.base import LookupAdapter, LookupRequest, LookupResult, Reference


class StoicAdapter:
    app_variant = "stoic"

    async def select(self, req: LookupRequest) -> LookupResult:
        return LookupResult(
            primary=Reference(
                ref="",
                shortReason=(
                    "Stoic verse lookup is not yet implemented. "
                    "The catalog is not seeded."
                ),
            ),
            alternates=[],
            provider="none",
            model="none",
        )
