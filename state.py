from typing import TypedDict, List, Annotated
import operator

class MarketingState(TypedDict):
    # Phase 1: Scouting
    competitor_intel: str
    market_gaps: List[str]
    
    # Phase 2: Strategy
    proposed_calendar: List[dict] # The 5-day plan
    user_approval: bool
    
    # Phase 3 & 4: Production
    # We use Annotated with operator.add so logs append rather than overwrite
    logs: Annotated[List[str], operator.add] 
    output_paths: List[str]