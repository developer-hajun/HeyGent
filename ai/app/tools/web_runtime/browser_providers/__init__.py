"""Cloud browser provider abstraction.

Import the ABC so callers can do::

    from app.tools.web_runtime.browser_providers import CloudBrowserProvider
"""

from app.tools.web_runtime.browser_providers.base import CloudBrowserProvider

__all__ = ["CloudBrowserProvider"]
