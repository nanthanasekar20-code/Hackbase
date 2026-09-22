from datetime import datetime, timezone


def assume_utc(value):
    """
    SQLite doesn't preserve tzinfo on stored datetimes (unlike Postgres),
    so a value read back from the DB is naive even though every write uses
    func.now(), which is always UTC. Left naive, FastAPI/Pydantic
    serializes it without a 'Z'/offset (e.g. "2026-09-02T06:51:47"), and
    JS's `new Date(...)` silently treats a naive ISO string as *local*
    time — misreading a UTC timestamp as local time throws off every
    relative "X ago" display by the machine's UTC offset. Attach UTC
    explicitly here so the API always emits an unambiguous offset,
    regardless of which DB backend is configured.
    """
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
