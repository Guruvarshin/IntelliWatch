from pydantic import BaseModel


class CompetitorIn(BaseModel):
    """Body for creating a competitor. Per-source fields are optional --
    decision 11/20: a competitor doesn't have to configure every source."""

    name: str
    since_days: int = 7
    github_repo: str | None = None
    hn_query: str | None = None
    youtube_channel_id: str | None = None
    jobs_board_type: str | None = None
    jobs_board_token: str | None = None
    pricing_url: str | None = None
    news_query: str | None = None
    blog_rss_url: str | None = None


class ApiKeysIn(BaseModel):
    """Body for PUT /me/api-keys. Fields absent from the request body are
    left untouched; an empty string clears the stored key; a non-empty
    string is encrypted and stored. Use model_dump(exclude_unset=True) to
    distinguish "absent" from "explicit empty string"."""

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None


class CompetitorUpdate(BaseModel):
    """Body for partial updates. All fields optional; only fields present
    in the request are applied (via model_dump(exclude_unset=True))."""

    name: str | None = None
    since_days: int | None = None
    github_repo: str | None = None
    hn_query: str | None = None
    youtube_channel_id: str | None = None
    jobs_board_type: str | None = None
    jobs_board_token: str | None = None
    pricing_url: str | None = None
    news_query: str | None = None
    blog_rss_url: str | None = None
