"""SerpApi engine parsers."""

from .google import parse as parse_google
from .jobs import parse as parse_jobs
from .news import parse as parse_news
from .patents import parse as parse_patents
from .scholar import parse as parse_scholar
from .shopping import parse as parse_shopping
from .trends import parse as parse_trends
from .youtube import parse as parse_youtube

PARSERS = {
    "google": parse_google,
    "google_news": parse_news,
    "google_trends": parse_trends,
    "google_scholar": parse_scholar,
    "google_jobs": parse_jobs,
    "google_shopping": parse_shopping,
    "google_patents": parse_patents,
    "youtube": parse_youtube,
}
