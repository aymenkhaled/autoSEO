"""CMS Adapters package — factory and exports."""
from .base import BaseCMSAdapter, CMSPage, ApplyResult
from .wordpress import WordPressAdapter
from .github_adapter import GitHubAdapter


def get_adapter(connection_type: str, **kwargs) -> BaseCMSAdapter:
    """Factory — returns the correct adapter for the given CMS type.

    Args:
        connection_type: 'wordpress', 'github', 'shopify', 'webflow', 'snippet'
        **kwargs: Credentials and config passed to the adapter constructor

    Raises:
        ValueError: If connection_type is not supported yet
    """
    adapters = {
        "wordpress": WordPressAdapter,
        "github": GitHubAdapter,
    }
    cls = adapters.get(connection_type)
    if cls is None:
        raise ValueError(
            f"CMS adapter '{connection_type}' is not implemented yet. "
            f"Supported: {list(adapters.keys())}"
        )
    return cls(**kwargs)


__all__ = [
    "BaseCMSAdapter", "CMSPage", "ApplyResult",
    "WordPressAdapter", "GitHubAdapter",
    "get_adapter",
]
