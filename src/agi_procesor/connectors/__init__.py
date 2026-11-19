"""Data source connectors for Deep Research."""

from agi_procesor.connectors._stubs import (
    Attachment,
    BaseConnector,
    Document,
    SyncStatus,
)
from agi_procesor.connectors.store import KnowledgeStore

__all__ = ["Attachment", "BaseConnector", "Document", "KnowledgeStore", "SyncStatus"]

# Auto-register built-in connectors
import agi_procesor.connectors.obsidian  # noqa: F401

try:
    import agi_procesor.connectors.gmail  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.gmail_imap  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.gdrive  # noqa: F401
except ImportError:
    pass  # httpx may not be installed

try:
    import agi_procesor.connectors.notion  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.granola  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.gcontacts  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.imessage  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.apple_notes  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.apple_music  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.apple_contacts  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.apple_calendar  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.slack_connector  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.outlook  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.imap  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.gcalendar  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.dropbox  # noqa: F401
except ImportError:
    pass  # httpx may not be installed

try:
    import agi_procesor.connectors.whatsapp  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.oura  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.apple_health  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.strava  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.spotify  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.google_tasks  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.weather  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.github_notifications  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.hackernews  # noqa: F401
except ImportError:
    pass

try:
    import agi_procesor.connectors.news_rss  # noqa: F401
except ImportError:
    pass
