from typing import Optional


class UserProfile:
    def __init__(self, risk_level: str, investment_horizon: str):
        self.risk_level = risk_level
        self.investment_horizon = investment_horizon

    def is_conservative(self) -> bool:
        return self.risk_level == "conservative"

    def is_aggressive(self) -> bool:
        return self.risk_level == "aggressive"

    def is_short_term(self) -> bool:
        return self.investment_horizon == "short"

    def is_long_term(self) -> bool:
        return self.investment_horizon == "long"


class QueryOptions:
    def __init__(
        self,
        agents: Optional[list[str]] = None,
        max_tokens: int = 1024,
    ):
        self.agents = agents or []
        self.max_tokens = max_tokens


class AgentQuery:
    def __init__(
        self,
        query: str,
        ticker: Optional[str] = None,
        session_id: Optional[str] = None,
        user_profile: Optional[UserProfile] = None,
        options: Optional[QueryOptions] = None,
    ):
        self.query = query
        self.ticker = ticker
        self.session_id = session_id
        self.user_profile = user_profile
        self.options = options or QueryOptions()

    def has_ticker(self) -> bool:
        return self.ticker is not None and len(self.ticker.strip()) > 0

    def has_user_profile(self) -> bool:
        return self.user_profile is not None

    def requested_agents(self) -> list[str]:
        return self.options.agents
