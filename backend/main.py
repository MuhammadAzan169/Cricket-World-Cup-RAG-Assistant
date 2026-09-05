"""
Cricket World Cup Chatbot — Main CLI Application
==================================================
Interactive CLI-based RAG chatbot for ICC Cricket World Cup queries (2003–2023).

Features:
    - Semantic search over cricket match data
    - AI-powered responses using OpenRouter
    - Query classification and optimized retrieval
    - Conversation history and context
    - Interactive CLI with commands

Usage:
    python main.py                    # Interactive CLI
    python main.py --query "Who won the 2011 World Cup?"
    python main.py --status           # Show system status
    python main.py --build-index      # Build/rebuild FAISS index
"""

import hashlib
import json
import logging
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from dotenv import load_dotenv

# Load environment
load_dotenv()

from embeddings_utils import EmbeddingsManager

# ────────────────────────────────────────────────────────────
# CHAT HISTORY
# ────────────────────────────────────────────────────────────

HISTORY_FILE = Path(__file__).parent / "history.txt"

def save_chat_history(question: str, answer: str, query_type: str = "unknown") -> None:
    """Save chat history to history.txt file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Format the entry
    entry = f"""[{timestamp}] Query Type: {query_type}
Question: {question}
Answer: {answer}
{'-' * 80}

"""

    # Append to history file
    try:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as e:
        logger.warning(f"Failed to save chat history: {e}")

# ────────────────────────────────────────────────────────────
# LOGGING
# ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)s │ %(levelname)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("cricket_chatbot")

# ────────────────────────────────────────────────────────────
# LLM CONFIGURATION
# ────────────────────────────────────────────────────────────

# Auto-discover all OPENROUTER_API_KEY* vars, sorted for consistent ordering
_openrouter_keys = sorted(
    [(k, v.strip()) for k, v in os.environ.items()
     if k.startswith("OPENROUTER_API_KEY") and v.strip()],
    key=lambda x: x[0],
)

# Build the full key pool: explicit LLM_API_KEY first, then all OPENROUTER_API_KEY*
_explicit_key = os.getenv("LLM_API_KEY", "").strip()
ALL_API_KEYS: List[str] = []
if _explicit_key and _explicit_key not in ("your_api_key_here", "your-api-key-here", ""):
    ALL_API_KEYS.append(_explicit_key)
for _, v in _openrouter_keys:
    if v not in ALL_API_KEYS:
        ALL_API_KEYS.append(v)

# Only the API key is truly required — everything else has a sensible default
if not ALL_API_KEYS:
    raise ValueError(
        "Missing API key. Set LLM_API_KEY or OPENROUTER_API_KEY1 (and more) in your environment / Render dashboard."
    )

LLM_PROVIDER   = os.getenv("LLM_PROVIDER",   "openrouter")
LLM_MODEL      = os.getenv("LLM_MODEL",      "openai/gpt-oss-20b:free")
LLM_API_KEY    = ALL_API_KEYS[0]
LLM_BASE_URL   = os.getenv("LLM_BASE_URL",   os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS",   "3000"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

# Bound the worst case: with many keys/models configured, trying every single
# combination on every retryable failure can mean hundreds of network round
# trips for one question — hanging the request for minutes and outliving any
# reasonable client/proxy timeout. Cap how many keys we try per model, and cap
# the total wall-clock time for one generate() call.
LLM_MAX_KEYS_PER_MODEL = int(os.getenv("LLM_MAX_KEYS_PER_MODEL", "6"))
LLM_REQUEST_BUDGET_SECONDS = float(os.getenv("LLM_REQUEST_BUDGET_SECONDS", "45"))

logger.info(f"Loaded {len(ALL_API_KEYS)} API key(s) for rotation")

# Auto-discover all OPENROUTER_MODEL_* vars, sorted for consistent ordering
_model_vars = sorted(
    [(k, v.strip()) for k, v in os.environ.items()
     if k.startswith("OPENROUTER_MODEL_") and v.strip()],
    key=lambda x: x[0],
)
ALL_MODELS: List[str] = [v for _, v in _model_vars]
if not ALL_MODELS:
    ALL_MODELS = [os.getenv("LLM_MODEL", "openai/gpt-oss-20b:free")]

logger.info(f"Loaded {len(ALL_MODELS)} model(s) for rotation: {ALL_MODELS}")

# ────────────────────────────────────────────────────────────
# PLAYER NAME RESOLUTION
# ────────────────────────────────────────────────────────────

# Maps common names / nicknames → scorecard names used in the dataset
PLAYER_ALIASES: Dict[str, List[str]] = {
    "virat kohli": ["V Kohli", "Kohli"],
    "kohli": ["V Kohli", "Kohli"],
    "sachin tendulkar": ["SR Tendulkar", "Tendulkar", "Sachin"],
    "sachin": ["SR Tendulkar", "Tendulkar", "Sachin"],
    "tendulkar": ["SR Tendulkar", "Tendulkar"],
    "ms dhoni": ["MS Dhoni", "Dhoni"],
    "dhoni": ["MS Dhoni", "Dhoni"],
    "rohit sharma": ["RG Sharma", "Rohit Sharma", "Rohit"],
    "rohit": ["RG Sharma", "Rohit Sharma", "Rohit"],
    "ricky ponting": ["RT Ponting", "Ponting", "Ricky Ponting"],
    "ponting": ["RT Ponting", "Ponting"],
    "kumar sangakkara": ["KC Sangakkara", "Sangakkara"],
    "sangakkara": ["KC Sangakkara", "Sangakkara"],
    "adam gilchrist": ["AC Gilchrist", "Gilchrist"],
    "gilchrist": ["AC Gilchrist", "Gilchrist"],
    "mitchell starc": ["MA Starc", "Starc", "Mitchell Starc"],
    "starc": ["MA Starc", "Starc"],
    "lasith malinga": ["SL Malinga", "Malinga", "Lasith Malinga"],
    "malinga": ["SL Malinga", "Malinga"],
    "glenn mcgrath": ["GD McGrath", "McGrath"],
    "mcgrath": ["GD McGrath", "McGrath"],
    "ab de villiers": ["AB de Villiers", "de Villiers"],
    "de villiers": ["AB de Villiers", "de Villiers"],
    "david warner": ["DA Warner", "Warner"],
    "warner": ["DA Warner", "Warner"],
    "yuvraj singh": ["Yuvraj Singh", "Yuvraj"],
    "yuvraj": ["Yuvraj Singh", "Yuvraj"],
    "ben stokes": ["BA Stokes", "Stokes", "Ben Stokes"],
    "stokes": ["BA Stokes", "Stokes"],
    "chris gayle": ["CH Gayle", "Gayle", "Chris Gayle"],
    "gayle": ["CH Gayle", "Gayle"],
    "shane warne": ["SK Warne", "Warne"],
    "warne": ["SK Warne", "Warne"],
    "brett lee": ["B Lee", "Lee"],
    "wasim akram": ["Wasim Akram", "Akram"],
    "akram": ["Wasim Akram", "Akram"],
    "brian lara": ["BC Lara", "Lara", "Brian Lara"],
    "lara": ["BC Lara", "Lara"],
    "sourav ganguly": ["SC Ganguly", "Ganguly"],
    "ganguly": ["SC Ganguly", "Ganguly"],
    "eoin morgan": ["EJG Morgan", "Morgan", "Eoin Morgan"],
    "morgan": ["EJG Morgan", "Morgan"],
    "kane williamson": ["KS Williamson", "Williamson", "Kane Williamson"],
    "williamson": ["KS Williamson", "Williamson"],
    "babar azam": ["Babar Azam", "Babar"],
    "babar": ["Babar Azam", "Babar"],
    "pat cummins": ["PJ Cummins", "Cummins", "Pat Cummins"],
    "cummins": ["PJ Cummins", "Cummins"],
    "mohammed shami": ["Mohammed Shami", "Shami"],
    "shami": ["Mohammed Shami", "Shami"],
    "jasprit bumrah": ["JJ Bumrah", "Bumrah"],
    "bumrah": ["JJ Bumrah", "Bumrah"],
    "martin guptill": ["MJ Guptill", "Guptill"],
    "guptill": ["MJ Guptill", "Guptill"],
    "shakib al hasan": ["Shakib Al Hasan", "Shakib"],
    "shakib": ["Shakib Al Hasan", "Shakib"],
    "mahela jayawardene": ["DPMD Jayawardene", "Jayawardene"],
    "jayawardene": ["DPMD Jayawardene", "Jayawardene"],
    "muttiah muralitharan": ["M Muralitharan", "Muralitharan", "Murali"],
    "muralitharan": ["M Muralitharan", "Muralitharan"],
    "murali": ["M Muralitharan", "Muralitharan"],
    "kevin o'brien": ["KJ O'Brien", "O'Brien"],
    "travis head": ["TM Head", "Head", "Travis Head"],
    "head": ["TM Head", "Head"],
    "sehwag": ["V Sehwag", "Sehwag"],
    "virender sehwag": ["V Sehwag", "Sehwag"],
    "dravid": ["R Dravid", "Dravid"],
    "rahul dravid": ["R Dravid", "Dravid"],
}

# Team name aliases
TEAM_ALIASES: Dict[str, str] = {
    "india": "India", "ind": "India", "indian": "India",
    "australia": "Australia", "aus": "Australia", "aussies": "Australia",
    "england": "England", "eng": "England", "english": "England",
    "new zealand": "New Zealand", "nz": "New Zealand", "kiwis": "New Zealand",
    "south africa": "South Africa", "sa": "South Africa", "proteas": "South Africa",
    "pakistan": "Pakistan", "pak": "Pakistan",
    "sri lanka": "Sri Lanka", "sl": "Sri Lanka", "lanka": "Sri Lanka",
    "bangladesh": "Bangladesh", "ban": "Bangladesh",
    "west indies": "West Indies", "wi": "West Indies", "windies": "West Indies",
    "afghanistan": "Afghanistan", "afg": "Afghanistan",
    "ireland": "Ireland", "ire": "Ireland",
    "zimbabwe": "Zimbabwe", "zim": "Zimbabwe",
    "netherlands": "Netherlands", "ned": "Netherlands", "holland": "Netherlands",
    "scotland": "Scotland", "sco": "Scotland",
    "kenya": "Kenya", "ken": "Kenya",
    "canada": "Canada", "can": "Canada",
    "namibia": "Namibia", "nam": "Namibia",
    "bermuda": "Bermuda",
    "uae": "United Arab Emirates", "united arab emirates": "United Arab Emirates",
}


def resolve_player_names(query: str) -> List[str]:
    """Extract and resolve player names mentioned in a query."""
    q = query.lower()
    found = []
    for alias, scorecard_names in PLAYER_ALIASES.items():
        if alias in q:
            found.extend(scorecard_names)
    return list(set(found))


def resolve_team_names(query: str) -> List[str]:
    """Extract and resolve team names mentioned in a query."""
    q = query.lower()
    found = []
    for alias, canonical in TEAM_ALIASES.items():
        # Use word boundary matching for short aliases
        if len(alias) <= 3:
            if re.search(rf'\b{re.escape(alias)}\b', q):
                found.append(canonical)
        else:
            if alias in q:
                found.append(canonical)
    return list(set(found))


# ────────────────────────────────────────────────────────────
# QUERY REWRITER — Handles context switching, ambiguity, corrections
# ────────────────────────────────────────────────────────────

class QueryRewriter:
    """
    Pre-processes user queries to handle:
    - Self-corrections ("No, I meant...")
    - Context switching ("Wait, I mean the 2007 final")
    - Ambiguous references
    - Temporal references ("yesterday", "last year")
    """

    CORRECTION_PATTERNS = [
        r"(?:no|wait|actually|sorry|i mean|i meant|correction|clarify|not that)[,.]?\s*(?:i(?:'m)?\s+(?:asking|talking)\s+about\s+)?(.+)",
        r".*?(?:but|however|actually)[,.]?\s+(?:i(?:'m)?\s+(?:asking|talking)\s+about\s+)?(.+)",
    ]

    @staticmethod
    def rewrite(query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Rewrite / clean the user query for optimal retrieval.
        Handles corrections, temporal references, and ambiguity.
        """
        q = query.strip()

        # 1. Handle self-corrections — extract the corrected intent
        q_lower = q.lower()
        for pattern in QueryRewriter.CORRECTION_PATTERNS:
            match = re.search(pattern, q_lower, re.IGNORECASE)
            if match:
                corrected = match.group(1).strip()
                # Only use corrected part if it's substantial
                if len(corrected) > 15:
                    q = corrected
                    break

        # 2. Handle temporal references
        q = QueryRewriter._resolve_temporal(q)

        # 3. Clean up redundant phrasing
        q = re.sub(r'^(can you |could you |please |tell me |i want to know |what is |what are )', '', q, flags=re.IGNORECASE).strip()

        return q if q else query.strip()

    @staticmethod
    def _resolve_temporal(query: str) -> str:
        """Replace temporal references with explicit notes."""
        temporal_map = {
            r"\byesterday'?s?\b": "(Note: no live/recent match data — World Cup data covers 2003-2023 tournaments only)",
            r"\btoday'?s?\b": "(Note: no live/recent match data — World Cup data covers 2003-2023 tournaments only)",
            r"\blast week\b": "(Note: World Cup data covers 2003-2023 tournaments only)",
            r"\brecent(ly)?\b": "latest World Cup 2023",
            r"\bcurrent\b": "2023",
            r"\blatest\b": "2023",
        }
        for pattern, replacement in temporal_map.items():
            if re.search(pattern, query, re.IGNORECASE):
                query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)
        return query


# ────────────────────────────────────────────────────────────
# QUERY CLASSIFIER WITH ENHANCED PARAMETERS
# ────────────────────────────────────────────────────────────

class QueryClassifier:
    """
    Classifies user queries to optimize retrieval and prompt strategy.
    """

    STATISTICAL_PATTERNS = [
        r"\b(most|highest|lowest|best|worst|top|maximum|minimum)\b",
        r"\b(average|total|aggregate|leading|record)\b",
        r"\b(how many|how much|count|number of)\b",
        r"\b(runs|wickets|centuries|fifties|catches|sixes|fours)\b.*\b(most|top|highest)\b",
        r"\b(table|list|ranking|rank|standings|leaderboard)\b",
        r"\b(statistics|stats|figures|numbers)\b.*\b(world cup|wc)\b",
        r"\b(strike rate|economy|average|run rate)\b",
        r"\b(scored|took|conceded|made)\b.*\b(\d+)\b",
    ]

    COMPARATIVE_PATTERNS = [
        r"\bcompare\b",
        r"\bvs\.?\b|\bversus\b",
        r"\bbetter\b|\bworse\b",
        r"\bdifference\b.*\bbetween\b",
        r"\b(\w+)\s+or\s+(\w+)\b.*\b(who|which|better)\b",
        r"\bhead.?to.?head\b",
    ]

    MATCH_PATTERNS = [
        r"\b(final|semi.?final|quarter.?final|group)\b.*\b(20\d{2})\b",
        r"\b(20\d{2})\b.*\b(final|semi.?final|quarter.?final|group)\b",
        r"\b(\w+)\s+vs\.?\s+(\w+)\b.*\b(20\d{2})\b",
        r"\b(20\d{2})\b.*\b(\w+)\s+vs\.?\s+(\w+)\b",
        r"\bmatch\s+number\b",
    ]

    TOURNAMENT_PATTERNS = [
        r"\b(won|winner|champion)\b.*\b(world cup|wc|tournament)\b",
        r"\b(world cup|wc|tournament)\b.*\b(won|winner|champion)\b",
        r"\b(20\d{2})\s*(world cup|wc|tournament)\b",
        r"\b(world cup|wc|tournament)\s*(20\d{2})\b",
        r"\b(host|venue|format)\b.*\b(20\d{2})\b",
        r"\b(finalists?|semi.?finalists?|runner.?up)\b",
    ]

    PLAYER_PATTERNS = [
        r"\b(stats?|statistics?|performance|record|career)\b",
        r"\b(sachin|tendulkar|kohli|virat|ponting|dhoni|rohit|warner|sangakkara|jayawardene|babar|starc|shami|cummins|gayle|malinga|mcgrath|stokes|morgan|williamson|sehwag|dravid|yuvraj|bumrah|guptill|de villiers|shakib|muralitharan|gilchrist|lee|warne|head|marsh)\b",
        r"\b(batting|bowling|fielding)\s*(average|record|stats?)\b",
        r"\b(player|batsman|batter|bowler|all.?rounder|fielder)\b",
        r"\bplayer of the (match|tournament)\b",
        r"\b(man of the match|mom|potm|pot)\b",
    ]

    AWARD_PATTERNS = [
        r"\b(award|trophy|prize|spirit of cricket)\b",
        r"\bplayer of the (tournament|series)\b",
        r"\b(man of the match|mom|motm)\b.*\b(most|total|how many)\b",
    ]

    PROCEDURAL_PATTERNS = [
        r"\b(rule|format|structure|stage|super.?(eight|six|over)|group|pool|knockout)\b",
        r"\b(reserve day|dls|duckworth|rain|umpire|drs|review)\b",
        r"\b(points?|carry|carried)\s*(forward|over)\b",
        r"\b(toss|decision|bat first|field first|chose to)\b",
        r"\b(semi.?finalist|quarter.?finalist|finalist)s?\b",
        r"\b(venue|stadium|ground|host)\b",
    ]

    CROSS_TOURNAMENT_PATTERNS = [
        r"\b(across|all|every|each)\b.*\b(world cup|tournament|edition)\b",
        r"\b(2003|from)\b.*\b(to|through|until)\b.*\b(2023)\b",
        r"\b2003.?2023\b",
        r"\b(overall|career|total|all.?time|history|lifetime)\b",
        r"\b(between|from)\s+\d{4}\s+(and|to)\s+\d{4}\b",
        r"\bwhich\s+(world cup|tournament)\b",
        r"\beach\s+(world cup|tournament|year|edition)\b",
    ]

    @staticmethod
    def classify(query: str) -> str:
        """Classify a query into a type for retrieval optimization."""
        q = query.lower().strip()

        # Check comparative first (often has "vs" which overlaps with match)
        for pattern in QueryClassifier.COMPARATIVE_PATTERNS:
            if re.search(pattern, q):
                return "comparative"

        for pattern in QueryClassifier.STATISTICAL_PATTERNS:
            if re.search(pattern, q):
                return "statistical"

        for pattern in QueryClassifier.MATCH_PATTERNS:
            if re.search(pattern, q):
                return "match_specific"

        for pattern in QueryClassifier.TOURNAMENT_PATTERNS:
            if re.search(pattern, q):
                return "tournament"

        for pattern in QueryClassifier.PLAYER_PATTERNS:
            if re.search(pattern, q):
                return "player"

        for pattern in QueryClassifier.AWARD_PATTERNS:
            if re.search(pattern, q):
                return "tournament"  # Awards are tournament-level info

        for pattern in QueryClassifier.PROCEDURAL_PATTERNS:
            if re.search(pattern, q):
                return "tournament"  # Rules/format are tournament-level

        # If specific player names are detected even without keyword markers
        resolved_players = resolve_player_names(q)
        if resolved_players:
            return "player"

        return "general"

    @staticmethod
    def is_cross_tournament(query: str) -> bool:
        """Check if query spans multiple tournaments."""
        q = query.lower().strip()
        return any(
            re.search(p, q) for p in QueryClassifier.CROSS_TOURNAMENT_PATTERNS
        )

    @staticmethod
    def get_search_params(query_type: str, is_cross: bool = False) -> Dict[str, Any]:
        """Get optimized search parameters based on query type."""
        from config import QUERY_SEARCH_PARAMS
        params = QUERY_SEARCH_PARAMS.copy()
        p = params.get(query_type, params["general"]).copy()
        if is_cross:
            p["top_k"] = min(p["top_k"] + 15, 45)
            p["score_threshold"] = max(p["score_threshold"] - 0.02, 0.01)
        return p

# ────────────────────────────────────────────────────────────
# QUERY ENHANCEMENT UTILITIES
# ────────────────────────────────────────────────────────────

WORLD_CUP_YEARS = ["2003", "2007", "2011", "2015", "2019", "2023"]

def enhance_query_with_years(query: str) -> str:
    """
    Enhance query by extracting and appending relevant years for better semantic search.
    """
    # Extract years mentioned in query
    years_in_query = re.findall(r'\b(2003|2007|2011|2015|2019|2023)\b', query)
    
    # For tournament-wide questions, add all years
    tournament_keywords = [
        "between", "from.*to", "all", "each edition", "every world cup",
        "all tournaments", "2003 to 2023", "2003-2023", "each year",
        "across", "overall", "history", "all-time"
    ]
    
    query_lower = query.lower()
    if any(keyword in query_lower for keyword in tournament_keywords):
        years_in_query.extend(WORLD_CUP_YEARS)
    
    # Add unique years to query
    unique_years = list(set(years_in_query))
    if unique_years:
        enhanced_query = query + " ICC Cricket World Cup " + " ".join(unique_years)
        return enhanced_query
    
    return query + " ICC Cricket World Cup"

def generate_sub_queries(query: str, query_type: str) -> List[str]:
    """
    Generate multiple sub-queries for comprehensive retrieval.
    Especially useful for cross-tournament, comparative, and player queries.
    Uses entity extraction for targeted searches.
    """
    queries = [query]
    q_lower = query.lower()
    
    # Extract entities for targeted retrieval
    resolved_players = resolve_player_names(query)
    resolved_teams = resolve_team_names(query)
    mentioned_years = re.findall(r'\b(2003|2007|2011|2015|2019|2023)\b', query)
    
    # Check if it's a cross-tournament query
    is_cross = QueryClassifier.is_cross_tournament(query)
    
    # ── Player queries: search for each player's stats + their match appearances ──
    if query_type == "player" or resolved_players:
        for player in resolved_players[:3]:  # Limit to top 3
            queries.append(f"Player: {player} batting bowling statistics world cup")
            queries.append(f"{player} performance runs wickets world cup")
            if mentioned_years:
                for year in mentioned_years:
                    queries.append(f"{player} {year} world cup match performance")
            elif is_cross:
                for year in WORLD_CUP_YEARS:
                    queries.append(f"{player} {year} world cup")
        # Also search the all_player_statistics file
        queries.append(f"ICC Cricket World Cup Player Statistics {' '.join(resolved_players[:2])}")
    
    # ── Cross-tournament queries: search each year ──
    if is_cross:
        years_to_search = mentioned_years if mentioned_years else WORLD_CUP_YEARS
        for year in years_to_search:
            sub_q = re.sub(
                r'\b(across all|from \d{4} to \d{4}|2003.?2023|all world cups?|every world cup|each world cup)\b',
                f'{year}',
                q_lower,
                flags=re.IGNORECASE
            )
            if sub_q != q_lower:
                queries.append(f"{sub_q} {year} world cup tournament summary")
            else:
                queries.append(f"{query} {year} world cup")
        
        # Also search for tournament summaries directly
        queries.append("ICC Cricket World Cup tournament summary winners 2003 2007 2011 2015 2019 2023")
        queries.append("team performance standings win percentage all world cups")
    
    # ── Comparative queries: search each entity separately ──
    if query_type == "comparative":
        for player in resolved_players[:2]:
            queries.append(f"Player: {player} batting bowling world cup statistics career")
        for team in resolved_teams[:2]:
            queries.append(f"{team} world cup team performance wins losses")
        if resolved_players:
            queries.append(f"ICC Cricket World Cup Player Statistics {' '.join(resolved_players[:2])}")
    
    # ── Statistical queries: targeted searches ──
    if query_type == "statistical":
        queries.append(f"{query} tournament summary team performance")
        if "captain" in q_lower:
            queries.append("captain performance win percentage world cup captaincy record")
            for year in WORLD_CUP_YEARS:
                queries.append(f"Captain Performance {year} World Cup")
        if any(w in q_lower for w in ["century", "centuries", "hundred", "100"]):
            queries.append("centuries scored world cup batting highlights hundred")
            queries.append("ICC Cricket World Cup Player Statistics centuries")
        if any(w in q_lower for w in ["run", "runs", "scorer", "batting"]):
            queries.append("top run scorer batting world cup player statistics")
            queries.append("ICC Cricket World Cup Player Statistics batting runs average")
        if any(w in q_lower for w in ["wicket", "bowling", "bowler", "economy"]):
            queries.append("top wicket taker bowling world cup player statistics economy")
            queries.append("ICC Cricket World Cup Player Statistics bowling wickets")
        if any(w in q_lower for w in ["six", "sixes", "four", "fours", "boundary"]):
            queries.append("ICC Cricket World Cup Player Statistics sixes fours batting")
        if any(w in q_lower for w in ["death", "powerplay", "middle"]):
            queries.append("death overs powerplay bowling batting statistics analysis")
        if any(w in q_lower for w in ["extras", "wide", "no ball"]):
            queries.append("extras conceded world cup team performance statistics")
        if any(w in q_lower for w in ["hat trick", "hat-trick"]):
            queries.append("hat trick hat-trick world cup bowling")
        if any(w in q_lower for w in ["defend", "chase", "total", "score"]):
            queries.append("defended total chased world cup match results scores")
        if any(w in q_lower for w in ["partnership", "opening", "pair"]):
            queries.append("opening partnership batting pair world cup runs")
        if any(w in q_lower for w in ["win loss", "win-loss", "ratio", "record"]):
            for team in resolved_teams:
                queries.append(f"{team} world cup wins losses matches team performance")
    
    # ── Match-specific queries: search for the specific match ──
    if query_type == "match_specific":
        for team in resolved_teams:
            year_str = " ".join(mentioned_years) if mentioned_years else ""
            queries.append(f"{team} {year_str} world cup match")
        # Search for specific match stages
        for stage in ["final", "semi-final", "quarter-final"]:
            if stage in q_lower or stage.replace("-", " ") in q_lower:
                for year in (mentioned_years or WORLD_CUP_YEARS):
                    queries.append(f"{year} {stage} world cup match result")
    
    # ── Tournament queries: fetch tournament summaries ──
    if query_type == "tournament":
        for year in (mentioned_years or WORLD_CUP_YEARS):
            queries.append(f"ICC Cricket World Cup {year} Tournament Summary")
        if any(w in q_lower for w in ["player of tournament", "player of the tournament", "pot", "award"]):
            for year in (mentioned_years or WORLD_CUP_YEARS):
                queries.append(f"Player of Tournament {year} World Cup award")
        if any(w in q_lower for w in ["semi-finalist", "semifinalist", "finalist"]):
            for year in (mentioned_years or WORLD_CUP_YEARS):
                queries.append(f"Semi-finalists Finalists {year} World Cup")
        if any(w in q_lower for w in ["venue", "stadium", "ground", "host"]):
            queries.append("venue stadium host world cup")
        if any(w in q_lower for w in ["format", "rule", "structure", "super", "reserve"]):
            for year in (mentioned_years or WORLD_CUP_YEARS):
                queries.append(f"Format structure rules {year} World Cup")
    
    # ── Team-specific queries ──
    if resolved_teams and query_type not in ("match_specific",):
        for team in resolved_teams[:2]:
            queries.append(f"{team} world cup team performance wins losses run scored")
            if is_cross or not mentioned_years:
                for year in WORLD_CUP_YEARS:
                    queries.append(f"{team} {year} world cup team performance")
    
    # ── Obscure detail queries: add very specific keyword searches ──
    obscure_keywords = ["unusual", "rare", "dismissal", "obstructing", "handled", "retired hurt",
                        "controversial", "umpire", "drs", "boundary rope", "run out"]
    if any(kw in q_lower for kw in obscure_keywords):
        queries.append(f"{query} key moments match highlights")
        if mentioned_years:
            for year in mentioned_years:
                queries.append(f"{year} world cup key moments match highlights unusual")
    
    # ── Memorable moments queries: always include for context-rich answers ──
    memorable_keywords = ["memorable", "moment", "drama", "dramatic", "exciting", "greatest",
                          "best match", "upset", "super over", "boundary countback", "hat trick",
                          "record", "fastest", "highest", "lowest", "first", "last", "iconic",
                          "turning point", "controversial", "shocking", "heartbreak"]
    if any(kw in q_lower for kw in memorable_keywords):
        if mentioned_years:
            for year in mentioned_years:
                queries.append(f"{year} world cup memorable moments records upsets")
        else:
            queries.append("world cup memorable moments records upsets dramatic")
    
    # ── Final-specific queries: always search memorable moments for finals ──
    if "final" in q_lower:
        if mentioned_years:
            for year in mentioned_years:
                queries.append(f"{year} world cup final result winner score")
                queries.append(f"{year} world cup memorable moments final")
        else:
            queries.append("world cup final result winner score memorable moments")
    
    # ── Cross-tournament records: search the records file ──
    records_keywords = ["all-time", "record", "history", "who has the most", "total", "career",
                        "world cup winners", "how many titles"]
    if any(kw in q_lower for kw in records_keywords):
        queries.append("ICC Cricket World Cup All-Time Records Cross-Tournament Facts")
        queries.append("world cup winners complete list titles")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_queries = []
    for sq in queries:
        sq_normalized = sq.strip().lower()
        if sq_normalized not in seen:
            seen.add(sq_normalized)
            unique_queries.append(sq)
    
    return unique_queries

def validate_context_coverage(context_text: str, query: str) -> str:
    """
    Check if retrieved context covers relevant years and return coverage note.
    """
    # Extract all tournament years from context
    years_in_context = set()
    for year in WORLD_CUP_YEARS:
        if year in context_text:
            years_in_context.add(year)
    
    # Extract years mentioned in query
    query_years = set(re.findall(r'\b(2003|2007|2011|2015|2019|2023)\b', query))
    
    # Check for tournament-wide queries
    is_cross = QueryClassifier.is_cross_tournament(query)
    
    if is_cross:
        all_years = set(WORLD_CUP_YEARS)
        missing_years = all_years - years_in_context
        if missing_years:
            return f"Note: Retrieved context covers years: {', '.join(sorted(years_in_context))}. Missing: {', '.join(sorted(missing_years))}."
    
    elif query_years:
        missing_years = query_years - years_in_context
        if missing_years:
            return f"Note: Context is missing data for year(s): {', '.join(sorted(missing_years))}."
    
    return ""

# ────────────────────────────────────────────────────────────
# LLM CLIENT
# ────────────────────────────────────────────────────────────

class LLMClient:
    """
    LLM client with automatic key rotation and model fallback.

    Failure strategy:
      - Key fail (401 / 429 / 502 / 503) → try next key, same model.
      - Model unavailable (404 / model error) → skip immediately to next model.
      - All keys exhausted for a model → rotate to next model, retry all keys.
      - All models exhausted → return error message.
    """

    def __init__(
        self,
        api_keys: Optional[List[str]] = None,
        models: Optional[List[str]] = None,
        base_url: str = LLM_BASE_URL,
        max_tokens: int = LLM_MAX_TOKENS,
        temperature: float = LLM_TEMPERATURE,
    ):
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._api_keys: List[str] = api_keys if api_keys is not None else list(ALL_API_KEYS)
        self._models: List[str] = models if models is not None else list(ALL_MODELS)
        self._base_url = base_url
        self._clients: Dict[str, Any] = {}
        # All keys hit the same base_url, so share one underlying connection
        # pool instead of letting every openai.OpenAI() instance open its own
        # httpx.Client — with dozens of keys that's dozens of redundant socket
        # pools, which adds up fast on a memory-constrained host.
        self._shared_http_client = None
        self._current_key_idx = 0
        self._current_model_idx = 0

    @property
    def model(self) -> str:
        if self._models:
            return self._models[self._current_model_idx]
        return LLM_MODEL

    def _get_client(self, api_key: str):
        if api_key not in self._clients:
            try:
                import httpx
                import openai
                if self._shared_http_client is None:
                    self._shared_http_client = httpx.Client(timeout=30.0)
                self._clients[api_key] = openai.OpenAI(
                    api_key=api_key,
                    base_url=self._base_url,
                    http_client=self._shared_http_client,
                )
            except ImportError:
                raise ImportError("openai package required. Install with: pip install openai")
        return self._clients[api_key]

    def _rotate_model(self):
        self._current_model_idx = (self._current_model_idx + 1) % len(self._models)
        logger.info(f"Rotated to model {self._current_model_idx + 1}/{len(self._models)}: {self._models[self._current_model_idx]}")

    def _compute_max_tokens(self, system_prompt: str) -> int:
        n = len(system_prompt)
        if n > 15000:
            return max(self.max_tokens, 6000)
        if n > 10000:
            return max(self.max_tokens, 5000)
        if n > 6000:
            return max(self.max_tokens, 4000)
        if n > 4000:
            return max(self.max_tokens, 3500)
        return self.max_tokens

    @staticmethod
    def _is_model_error(error_msg: str) -> bool:
        """Return True if the error indicates the model itself is unavailable."""
        msg = error_msg.lower()
        return "404" in error_msg or (
            "model" in msg and any(x in msg for x in ["not found", "unavailable", "does not exist", "invalid"])
        )

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        if not self._api_keys:
            return (
                "⚠️ LLM API key not configured.\n"
                "Please set LLM_API_KEY or OPENROUTER_API_KEY1 in your .env file.\n"
                "Get keys from https://openrouter.ai/keys"
            )

        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history[-6:])
        messages.append({"role": "user", "content": user_message})

        effective_max_tokens = self._compute_max_tokens(system_prompt)
        total_chars = sum(len(m.get("content", "")) for m in messages)
        logger.info(f"LLM request: {len(messages)} messages, ~{total_chars} chars, max_tokens={effective_max_tokens}")

        request_start = time.time()
        keys_per_model = min(len(self._api_keys), LLM_MAX_KEYS_PER_MODEL)

        for model_attempt in range(len(self._models)):
            current_model = self._models[self._current_model_idx]
            model_num = self._current_model_idx + 1
            logger.info(f"Trying model {model_num}/{len(self._models)}: {current_model}")
            skip_model = False

            for key_attempt in range(keys_per_model):
                if time.time() - request_start > LLM_REQUEST_BUDGET_SECONDS:
                    logger.warning(f"LLM request budget ({LLM_REQUEST_BUDGET_SECONDS}s) exceeded, aborting remaining attempts")
                    return "⚠️ All models and API keys are currently unavailable. Please try again in a moment."

                key_idx = (self._current_key_idx + key_attempt) % len(self._api_keys)
                key = self._api_keys[key_idx]
                key_num = key_idx + 1

                for retry in range(2):
                    try:
                        client = self._get_client(key)
                        response = client.chat.completions.create(
                            model=current_model,
                            messages=messages,
                            max_tokens=effective_max_tokens,
                            temperature=self.temperature,
                        )
                        answer = (response.choices[0].message.content or "").strip()
                        if answer:
                            logger.info(f"LLM success: model={current_model} key={key_num}/{len(self._api_keys)}, {len(answer)} chars")
                            self._current_key_idx = key_idx
                            return answer
                        logger.warning(f"Empty response: model={current_model} key={key_num}, retry {retry + 1}/2")
                        if retry == 0:
                            import time as _time
                            _time.sleep(1.0)
                            continue
                        break  # try next key
                    except Exception as e:
                        error_msg = str(e)
                        if "401" in error_msg or "unauthorized" in error_msg.lower():
                            logger.warning(f"Key {key_num}/{len(self._api_keys)} auth failed, trying next key")
                            break
                        elif self._is_model_error(error_msg):
                            logger.warning(f"Model {current_model} unavailable, skipping to next model: {error_msg[:120]}")
                            skip_model = True
                            break
                        elif any(c in error_msg for c in ["429", "503", "502"]) or "rate" in error_msg.lower():
                            logger.warning(f"Key {key_num}/{len(self._api_keys)} rate/server error (retry {retry + 1}/2): {error_msg[:100]}")
                            if retry == 0:
                                import time as _time
                                _time.sleep(1.5)
                                continue
                            logger.warning(f"Key {key_num} retries exhausted, trying next key")
                            break
                        elif any(x in error_msg.lower() for x in ["timeout", "timed out", "connection", "temporarily unavailable", "ssl", "reset by peer"]):
                            logger.warning(f"Key {key_num}/{len(self._api_keys)} network error (retry {retry + 1}/2): {error_msg[:100]}")
                            if retry == 0:
                                import time as _time
                                _time.sleep(1.5)
                                continue
                            logger.warning(f"Key {key_num} network retries exhausted, trying next key")
                            break
                        else:
                            # Don't leak raw exception text to the user — log it server-side
                            # and move on to the next key/model instead of failing the whole request.
                            logger.error(f"Non-retryable LLM error (key {key_num}, model {current_model}): {error_msg}")
                            break

                if skip_model:
                    break

            if not skip_model:
                logger.warning(f"All {len(self._api_keys)} keys exhausted for model {current_model}, rotating model")
            self._rotate_model()

        logger.error(f"All {len(self._models)} models and {len(self._api_keys)} API keys exhausted")
        return "⚠️ All models and API keys are currently unavailable. Please try again in a moment."

    @property
    def is_configured(self) -> bool:
        return bool(self._api_keys)

    def generate_stream(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ):
        if not self._api_keys:
            yield "⚠️ LLM API key not configured."
            return

        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history[-6:])
        messages.append({"role": "user", "content": user_message})

        effective_max_tokens = self._compute_max_tokens(system_prompt)

        request_start = time.time()
        keys_per_model = min(len(self._api_keys), LLM_MAX_KEYS_PER_MODEL)

        for model_attempt in range(len(self._models)):
            current_model = self._models[self._current_model_idx]
            model_num = self._current_model_idx + 1
            logger.info(f"Stream trying model {model_num}/{len(self._models)}: {current_model}")
            skip_model = False

            for key_attempt in range(keys_per_model):
                if time.time() - request_start > LLM_REQUEST_BUDGET_SECONDS:
                    logger.warning(f"Stream LLM request budget ({LLM_REQUEST_BUDGET_SECONDS}s) exceeded, aborting remaining attempts")
                    yield "⚠️ All models and API keys are currently unavailable. Please try again in a moment."
                    return

                key_idx = (self._current_key_idx + key_attempt) % len(self._api_keys)
                key = self._api_keys[key_idx]
                key_num = key_idx + 1

                for retry in range(2):
                    try:
                        client = self._get_client(key)
                        response = client.chat.completions.create(
                            model=current_model,
                            messages=messages,
                            max_tokens=effective_max_tokens,
                            temperature=self.temperature,
                            stream=True,
                        )
                        token_count = 0
                        for chunk in response:
                            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                                token_count += 1
                                yield chunk.choices[0].delta.content
                        if token_count > 0:
                            logger.info(f"Stream success: model={current_model} key={key_num}/{len(self._api_keys)}")
                            self._current_key_idx = key_idx
                            return
                        logger.warning(f"Stream 0 tokens: model={current_model} key={key_num}, retry {retry + 1}/2")
                        if retry == 0:
                            import time as _time
                            _time.sleep(1.0)
                            continue
                        break  # try next key
                    except Exception as e:
                        error_msg = str(e)
                        if "401" in error_msg or "unauthorized" in error_msg.lower():
                            logger.warning(f"Stream key {key_num}/{len(self._api_keys)} auth failed, trying next key")
                            break
                        elif self._is_model_error(error_msg):
                            logger.warning(f"Stream model {current_model} unavailable, skipping to next model: {error_msg[:120]}")
                            skip_model = True
                            break
                        elif any(c in error_msg for c in ["429", "503", "502"]) or "rate" in error_msg.lower():
                            logger.warning(f"Stream key {key_num}/{len(self._api_keys)} rate/server error (retry {retry + 1}/2): {error_msg[:100]}")
                            if retry == 0:
                                import time as _time
                                _time.sleep(1.5)
                                continue
                            break
                        elif any(x in error_msg.lower() for x in ["timeout", "timed out", "connection", "temporarily unavailable", "ssl", "reset by peer"]):
                            logger.warning(f"Stream key {key_num}/{len(self._api_keys)} network error (retry {retry + 1}/2): {error_msg[:100]}")
                            if retry == 0:
                                import time as _time
                                _time.sleep(1.5)
                                continue
                            break
                        else:
                            # Don't leak raw exception text into the chat — log it server-side
                            # and move on to the next key/model instead of failing the stream.
                            logger.error(f"Non-retryable stream error (key {key_num}, model {current_model}): {error_msg}")
                            break

                if skip_model:
                    break

            if not skip_model:
                logger.warning(f"Stream: all {len(self._api_keys)} keys exhausted for model {current_model}, rotating model")
            self._rotate_model()

        yield "⚠️ All models and API keys are currently unavailable. Please try again in a moment."

# ────────────────────────────────────────────────────────────
# ENHANCED PROMPT TEMPLATES
# ────────────────────────────────────────────────────────────

class PromptTemplates:
    """Enhanced prompt templates for natural, comprehensive answers."""

    BASE_SYSTEM = """You are a Cricket World Cup analyst. Your ONLY data source is the CONTEXT DATA below.

**ABSOLUTE RULES — FOLLOW STRICTLY:**
1. ONLY use facts from the CONTEXT DATA below. Do NOT invent, guess, or fill gaps with outside knowledge.
2. If the context does not contain enough data to answer, say: "Based on the available data, I can provide the following..." and answer with ONLY what the context contains. Then note what data is missing.
3. NEVER fabricate statistics, scores, match results, or player performances. Every number must come from the context.
4. NEVER mention "database", "dataset", "context", or "supplied data" — speak naturally.
5. For multi-tournament queries, combine data from ALL relevant context chunks.
6. If a question asks about data not present in context (e.g., exact match times, umpire decisions, fielding catches), say the information is not available in your records rather than making something up.

**FORMATTING:**
- Use **bold** for key facts and player names.
- Use markdown tables for stats/comparisons. Format:
  | Column A | Column B |
  | --- | --- |
  | value | value |
- Use bullet points (`- `) for lists. Numbered lists (`1. `) for rankings.
- Use `###` headings for sections. Never use HTML tags.

**ACCURACY — CRITICAL (VIOLATIONS WILL PRODUCE WRONG ANSWERS):**
- Use EXACT numbers from context. If a number is not in the context, do NOT provide it.
- NEVER fabricate Super Overs, tie-breakers, boundary countbacks, or match margins.
- NEVER invent player scores for matches not in the context.
- Do NOT make up economy rates, strike rates, or averages unless you can calculate them from context data.
- VERIFIED FACTS (use these ONLY when context doesn't cover the match):
  - 2003 WC final: Australia 359/2 beat India 234 by 125 runs at Johannesburg. Ponting 140*.
  - 2007 WC final: Australia beat Sri Lanka by 53 runs (D/L) at Kensington Oval, Barbados. NOT Lord's.
  - 2011 WC final: India 277/4 beat Sri Lanka 274/6 by 6 wickets at Wankhede, Mumbai. Dhoni 91*.
  - 2015 WC final: Australia 186/3 beat New Zealand 183 by 7 wickets at MCG, Melbourne.
  - 2019 WC final: England vs New Zealand. BOTH innings tied at 241. Super Over ALSO tied at 15-15. England won by BOUNDARY COUNTBACK (26 boundaries vs 17). NOT by wickets.
  - 2023 WC final: Australia 241/4 beat India 240 by 6 wickets at Ahmedabad. Travis Head 137. NO Super Over.
- Player name mappings: V Kohli=Virat Kohli, RT Ponting=Ricky Ponting, SR Tendulkar=Sachin Tendulkar, MS Dhoni, RG Sharma=Rohit Sharma, DPMD Jayawardene=Mahela Jayawardene, KC Sangakkara=Kumar Sangakkara.
- For head-to-head: list EVERY match found in context. Do not skip any. Do not add matches not in context.
- For "best/most/top" queries: scan ALL context chunks, rank by actual data. Include all entries found.
- Rohit Sharma has NEVER scored a double century in ODI World Cups. His highest WC score is 140.
- AB de Villiers' highest WC score is 162* vs West Indies in 2015, NOT 106* in every tournament.

**COVERAGE:** 2003 (South Africa), 2007 (West Indies), 2011 (India/SL/Bangladesh), 2015 (Australia/NZ), 2019 (England), 2023 (India)."""

    @staticmethod
    def get_system_prompt(query_type: str, context: str, coverage_note: str = "") -> str:
        """Get query-type-specific system prompt with context."""
        
        type_instructions = {
            "statistical": """
**STATISTICAL QUERY**:
- Present ONLY numbers found in the context data in a clean markdown table.
- For "most/best/highest/top" queries: scan EVERY chunk in context, list ALL candidates found, rank them.
- For aggregate queries: SUM data across ALL tournaments found in context.
- Compute averages/strike rates ONLY from raw data in context.
- If context has partial data, explicitly state which tournaments/players are covered and which are missing.
- Add a brief "Key Takeaways" section with 2-3 bullet points after the table.
- NEVER fill gaps with made-up numbers. State what data is available and what is not.""",

            "comparative": """
**COMPARISON QUERY**:
- Create a side-by-side comparison table with metrics found IN CONTEXT (matches, runs, average, SR, 100s, 50s, HS).
- Only include metrics that the context actually provides. Mark missing data as "N/A" or "not in data".
- Cover tournaments found in context — note which WCs have data for each player.
- End with a verdict based ONLY on the data presented.
- Do NOT guess or approximate stats that aren't in the context.""",

            "match_specific": """
**MATCH QUERY**:
- Include ONLY details found in context: teams, venue, date, toss, result with exact margin.
- Scorecard: list batters and bowlers AS THEY APPEAR in context data. Do NOT invent scores.
- For head-to-head: list EVERY match found in context as a table. Do NOT add matches not in context.
- NEVER fabricate Super Overs, tie-breakers, or boundary countbacks unless context explicitly describes one.
- Do NOT mix up details from different matches.
- If asked for ball-by-ball data not in context, say it's not available at that level of detail.""",

            "tournament": """
**TOURNAMENT QUERY**:
- Include Winner, Runner-up, Semi-finalists, Host country, Format.
- Key awards: Player of Tournament, Top Run Scorer (with runs), Top Wicket-Taker (with wickets).
- For cross-tournament queries, present ALL years in a comprehensive table.
- Hosts: 2003=SA, 2007=WI, 2011=Ind/SL/Ban, 2015=Aus/NZ, 2019=Eng, 2023=Ind.
- Winners: 2003=Aus, 2007=Aus, 2011=Ind, 2015=Aus, 2019=Eng, 2023=Aus.
- Add 2-3 sentences of narrative about the tournament's defining moments.""",

            "player": """
**PLAYER QUERY**:
- Present stats ONLY from context data in a table. Include only columns where you have actual data.
- Show year-by-year breakdown if context has data for multiple WCs.
- Mention key innings/milestones ONLY if they appear in the context.
- If context has limited data for this player, state clearly what WCs/matches are covered.
- Do NOT confuse WC stats with overall ODI career stats. Do NOT invent career totals.""",

            "general": """
**GENERAL QUERY**:
- Provide a comprehensive, well-rounded answer.
- Ground in context data, supplement with cricket knowledge.
- Use tables for any structured data.
- Be engaging and conversational like a passionate cricket analyst.""",
        }

        instruction = type_instructions.get(query_type, type_instructions["general"])

        context_section = context if context else "No specific data was retrieved for this query. Inform the user that the requested information is not available in the current data set. You may provide the verified final results listed in the system prompt, but do NOT fabricate any other statistics or details."
        
        coverage_section = f"\n\n**DATA COVERAGE NOTE**: {coverage_note}" if coverage_note else ""

        return f"""{PromptTemplates.BASE_SYSTEM}

{instruction}
{coverage_section}

--- CONTEXT DATA ---
{context_section}
--- END CONTEXT ---"""

# ────────────────────────────────────────────────────────────
# CRICKET CHATBOT
# ────────────────────────────────────────────────────────────

class CricketChatbot:
    """
    Main chatbot orchestrating embeddings search, query classification,
    RAG, and LLM response generation.
    """

    def __init__(self):
        self._embeddings: Optional[EmbeddingsManager] = None
        self._llm: Optional[LLMClient] = None
        self._classifier = QueryClassifier()
        self._rewriter = QueryRewriter()
        self._conversation_history: List[Dict[str, str]] = []
        self._initialized = False
        self._response_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 300  # 5 minutes

    def initialize(self) -> None:
        """Initialize all components: embeddings + LLM."""
        logger.info("═" * 50)
        logger.info("  Initializing Cricket World Cup Chatbot")
        logger.info("═" * 50)

        # Initialize embeddings manager
        self._embeddings = EmbeddingsManager()
        self._embeddings.initialize()

        # Initialize LLM client
        self._llm = LLMClient()

        self._initialized = True

        # Status report
        stats = self._embeddings.get_stats()
        logger.info(f"  Vectors loaded:  {stats['total_vectors']}")
        logger.info(f"  Chunks loaded:   {stats['total_chunks']}")
        logger.info(f"  LLM models:      {len(self._llm._models)} configured")
        logger.info(f"  LLM model[0]:    {self._llm.model}")
        logger.info(f"  LLM keys:        {len(self._llm._api_keys)} configured")
        logger.info(f"  LLM configured:  {self._llm.is_configured}")
        logger.info("═" * 50)

    def ask(self, question: str) -> Dict[str, Any]:
        """
        Process a user question through the full RAG pipeline.
        Uses query rewriting, entity extraction, multi-query search,
        and intelligent context assembly.
        """
        if not self._initialized:
            raise RuntimeError("Chatbot not initialized. Call initialize() first.")

        start_time = time.time()
        question = question.strip()

        if not question:
            return {
                "answer": "Please enter a question about Cricket World Cups (2003–2023).",
                "query_type": "empty",
                "sources": [],
                "search_results": 0,
                "processing_time": 0.0,
            }

        # Check cache for recent identical queries
        cache_key = question.strip().lower()
        if cache_key in self._response_cache:
            cached = self._response_cache[cache_key]
            if time.time() - cached["_cached_at"] < self._cache_ttl:
                logger.info(f"Cache hit for: '{question[:40]}...'")
                result = {k: v for k, v in cached.items() if not k.startswith("_")}
                result["processing_time"] = 0.01
                return result

        # Steps 1-8: query rewriting, classification, and retrieval.
        # Wrapped defensively so a bug here degrades to a "no context" answer
        # instead of leaking a raw Python exception to the user.
        try:
            # Step 1: Rewrite query (handle corrections, temporal refs, ambiguity)
            rewritten_query = self._rewriter.rewrite(question, self._conversation_history)
            if rewritten_query != question:
                logger.info(f"Query rewritten: '{question[:60]}...' → '{rewritten_query[:60]}...'")

            # Step 2: Classify query
            query_type = self._classifier.classify(rewritten_query)
            is_cross = self._classifier.is_cross_tournament(rewritten_query)
            search_params = self._classifier.get_search_params(query_type, is_cross)
            logger.info(f"Query type: {query_type} | Cross-tournament: {is_cross} | Params: {search_params}")

            # Step 3: Extract entities for targeted retrieval
            resolved_players = resolve_player_names(rewritten_query)
            resolved_teams = resolve_team_names(rewritten_query)
            logger.info(f"Entities — Players: {resolved_players[:3]}, Teams: {resolved_teams[:3]}")

            # Step 4: Generate sub-queries for comprehensive retrieval
            sub_queries = generate_sub_queries(rewritten_query, query_type)

            # Step 5: Enhance each sub-query with years
            enhanced_queries = [enhance_query_with_years(sq) for sq in sub_queries]

            # Cap the number of sub-queries to avoid excessive search
            max_sub_queries = 8 if is_cross else 6
            enhanced_queries = enhanced_queries[:max_sub_queries]

            logger.info(f"Searching with {len(enhanced_queries)} sub-queries")

            # Step 6: Multi-query semantic + BM25 hybrid search
            bm25_weight = search_params.get("bm25_weight", None)
            if len(enhanced_queries) > 1:
                context_text, sources = self._embeddings.multi_query_context(
                    queries=enhanced_queries,
                    top_k=search_params["top_k"],
                    score_threshold=search_params["score_threshold"],
                    max_total=25,
                    bm25_weight=bm25_weight,
                )
            else:
                context_text, sources = self._embeddings.get_context_text(
                    query=enhanced_queries[0],
                    top_k=search_params["top_k"],
                    score_threshold=search_params["score_threshold"],
                    bm25_weight=bm25_weight,
                )

            # Step 7: Validate context coverage
            coverage_note = validate_context_coverage(context_text, rewritten_query)
        except Exception:
            logger.exception(f"Retrieval pipeline failed for question: '{question[:80]}...'")
            query_type, context_text, sources, coverage_note = "general", "", [], ""

        # Step 8: Build prompt
        system_prompt = PromptTemplates.get_system_prompt(
            query_type, context_text, coverage_note
        )

        # Step 9: Generate LLM response
        answer = self._llm.generate(
            system_prompt=system_prompt,
            user_message=question,  # Send original question to LLM (more natural)
            conversation_history=self._conversation_history,
        )
        if not answer or not answer.strip():
            answer = "⚠️ I couldn't generate a response for that question. Please try again in a moment."

        # Step 10: Save to chat history file
        save_chat_history(question, answer, query_type)

        # Step 11: Update conversation history
        self._conversation_history.append({"role": "user", "content": question})
        self._conversation_history.append({"role": "assistant", "content": answer})

        # Keep history manageable (last 10 turns = 20 messages)
        if len(self._conversation_history) > 20:
            self._conversation_history = self._conversation_history[-20:]

        processing_time = round(time.time() - start_time, 2)

        result = {
            "answer": answer,
            "query_type": query_type,
            "sources": sources,
            "search_results": len(sources),
            "processing_time": processing_time,
        }

        # Cache the response
        self._response_cache[cache_key] = {**result, "_cached_at": time.time()}
        # Evict old cache entries
        if len(self._response_cache) > 50:
            oldest = min(self._response_cache, key=lambda k: self._response_cache[k].get("_cached_at", 0))
            del self._response_cache[oldest]

        return result

    def ask_stream(self, question: str):
        """
        Streaming version of ask(). Yields (event_type, data) tuples.
        Events: 'meta' (query_type, sources), 'token' (text chunk), 'done' (final).
        """
        if not self._initialized:
            raise RuntimeError("Chatbot not initialized. Call initialize() first.")

        import json as _json
        start_time = time.time()
        question = question.strip()

        if not question:
            yield ("done", _json.dumps({"answer": "Please enter a question about Cricket World Cups (2003–2023).", "query_type": "empty", "sources": [], "search_results": 0, "processing_time": 0.0}))
            return

        # Rewrite, classify, search (same as ask) — defensively wrapped so a
        # retrieval bug degrades to a "no context" answer instead of raising
        # mid-stream (which would surface a raw Python error to the user).
        try:
            rewritten_query = self._rewriter.rewrite(question, self._conversation_history)
            query_type = self._classifier.classify(rewritten_query)
            is_cross = self._classifier.is_cross_tournament(rewritten_query)
            search_params = self._classifier.get_search_params(query_type, is_cross)

            sub_queries = generate_sub_queries(rewritten_query, query_type)
            enhanced_queries = [enhance_query_with_years(sq) for sq in sub_queries]
            max_sub_queries = 8 if is_cross else 6
            enhanced_queries = enhanced_queries[:max_sub_queries]

            bm25_weight = search_params.get("bm25_weight", None)
            if len(enhanced_queries) > 1:
                context_text, sources = self._embeddings.multi_query_context(
                    queries=enhanced_queries,
                    top_k=search_params["top_k"],
                    score_threshold=search_params["score_threshold"],
                    max_total=20,
                    bm25_weight=bm25_weight,
                )
            else:
                context_text, sources = self._embeddings.get_context_text(
                    query=enhanced_queries[0],
                    top_k=search_params["top_k"],
                    score_threshold=search_params["score_threshold"],
                    bm25_weight=bm25_weight,
                )

            coverage_note = validate_context_coverage(context_text, rewritten_query)
        except Exception:
            logger.exception(f"Retrieval pipeline failed for question: '{question[:80]}...'")
            query_type, context_text, sources, coverage_note = "general", "", [], ""

        system_prompt = PromptTemplates.get_system_prompt(query_type, context_text, coverage_note)

        # Emit metadata
        yield ("meta", _json.dumps({
            "query_type": query_type,
            "sources": sources,
            "search_results": len(sources),
        }))

        # Stream LLM tokens
        full_answer = []
        for token in self._llm.generate_stream(
            system_prompt=system_prompt,
            user_message=question,
            conversation_history=self._conversation_history,
        ):
            full_answer.append(token)
            # JSON-encode token so newlines (\n) survive SSE transport intact
            yield ("token", _json.dumps(token))

        answer = "".join(full_answer)
        if not answer.strip():
            answer = "⚠️ I couldn't generate a response for that question. Please try again in a moment."
            yield ("token", _json.dumps(answer))

        # Save history
        save_chat_history(question, answer, query_type)
        self._conversation_history.append({"role": "user", "content": question})
        self._conversation_history.append({"role": "assistant", "content": answer})
        if len(self._conversation_history) > 20:
            self._conversation_history = self._conversation_history[-20:]

        processing_time = round(time.time() - start_time, 2)
        yield ("done", _json.dumps({"processing_time": processing_time}))

    def build_index(self, force_rebuild: bool = False) -> Dict[str, int]:
        """Build or rebuild the FAISS index from Cricket Data."""
        if not self._initialized:
            self._embeddings = EmbeddingsManager()
            self._embeddings.initialize()
            self._initialized = True

        return self._embeddings.build_index(force_rebuild=force_rebuild)

    def clear_history(self) -> None:
        """Clear conversation history."""
        self._conversation_history.clear()

        # Also clear the history file
        try:
            if HISTORY_FILE.exists():
                HISTORY_FILE.unlink()  # Delete the file
                logger.info("Chat history file cleared")
        except Exception as e:
            logger.warning(f"Failed to clear chat history file: {e}")

        logger.info("Conversation history cleared")

    def get_status(self) -> Dict[str, Any]:
        """Get full chatbot status."""
        status = {
            "initialized": self._initialized,
            "llm_model": self._llm.model if self._llm else LLM_MODEL,
            "llm_models_total": len(self._llm._models) if self._llm else 0,
            "llm_provider": LLM_PROVIDER,
            "llm_keys_total": len(self._llm._api_keys) if self._llm else 0,
            "llm_configured": self._llm.is_configured if self._llm else False,
            "conversation_turns": len(self._conversation_history) // 2,
        }
        if self._embeddings:
            status.update(self._embeddings.get_stats())
        return status

# ────────────────────────────────────────────────────────────
# CLI INTERFACE
# ────────────────────────────────────────────────────────────

def print_banner():
    """Print welcome banner."""
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║     🏏 ICC Cricket World Cup Chatbot (2003–2023)    ║")
    print("║         Powered by RAG + Semantic Search            ║")
    print("╠══════════════════════════════════════════════════════╣")
    print("║  Commands:                                          ║")
    print("║    /status  — Show system status                    ║")
    print("║    /history — Show chat history                     ║")
    print("║    /clear   — Clear conversation history            ║")
    print("║    /build   — Rebuild embeddings index              ║")
    print("║    /help    — Show this help                        ║")
    print("║    /quit    — Exit chatbot                          ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()


def print_answer(result: Dict[str, Any]):
    """Pretty-print a chatbot response."""
    print()
    print("─" * 55)
    print(result["answer"])
    print("─" * 55)
    print()


def print_status(chatbot: CricketChatbot):
    """Print system status."""
    status = chatbot.get_status()
    print()
    print("┌─────────────────────────────────────┐")
    print("│         System Status                │")
    print("├─────────────────────────────────────┤")
    for key, value in status.items():
        label = key.replace("_", " ").title()
        print(f"│  {label:<20} {str(value):>14} │")
    print("└─────────────────────────────────────┘")
    print()


def interactive_cli(chatbot: CricketChatbot):
    """Run the interactive CLI chatbot loop."""
    print_banner()

    while True:
        try:
            user_input = input("🏏 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye! 🏏")
            break

        if not user_input:
            continue

        # Handle commands
        cmd = user_input.lower()

        if cmd in ("/quit", "/exit", "/q"):
            print("\nGoodbye! 🏏")
            break

        elif cmd == "/help":
            print_banner()
            continue

        elif cmd == "/status":
            print_status(chatbot)
            continue

        elif cmd == "/clear":
            chatbot.clear_history()
            print("  ✓ Conversation history cleared\n")
            continue

        elif cmd == "/history":
            if HISTORY_FILE.exists():
                print("  Chat History:")
                print("  " + "=" * 50)
                try:
                    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                        content = f.read()
                        if content.strip():
                            print(content)
                        else:
                            print("  No chat history found.")
                except Exception as e:
                    print(f"  Error reading history: {e}")
            else:
                print("  No chat history file found.")
            print()
            continue

        elif cmd == "/build":
            print("  Building index (this may take a few minutes)...")
            stats = chatbot.build_index()
            print(f"  ✓ Index built: {stats.get('chunks_created', 0)} chunks, "
                  f"{stats.get('vectors_added', 0)} vectors\n")
            continue

        elif cmd.startswith("/"):
            print(f"  Unknown command: {cmd}. Type /help for available commands.\n")
            continue

        # Process question
        print("  Thinking...", end="", flush=True)
        result = chatbot.ask(user_input)
        print("\r" + " " * 20 + "\r", end="")  # Clear "Thinking..."
        print_answer(result)


def main():
    """Main entry point with CLI argument handling."""
    import argparse

    parser = argparse.ArgumentParser(
        description="ICC Cricket World Cup Chatbot (2003–2023)"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Ask a single question (non-interactive mode)"
    )
    parser.add_argument(
        "--build-index",
        action="store_true",
        help="Build/rebuild the FAISS embeddings index"
    )
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force full index rebuild (wipes existing)"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show system status and exit"
    )

    args = parser.parse_args()

    chatbot = CricketChatbot()

    # Handle --build-index
    if args.build_index:
        chatbot.initialize()
        print("Building embeddings index from Cricket World Cup data...")
        stats = chatbot.build_index(force_rebuild=args.force_rebuild)
        print(f"\n✓ Index built successfully!")
        print(f"  Files processed:     {stats.get('files_processed', 0)}")
        print(f"  Chunks created:      {stats.get('chunks_created', 0)}")
        print(f"  Duplicates skipped:  {stats.get('chunks_skipped_duplicate', 0)}")
        print(f"  Vectors added:       {stats.get('vectors_added', 0)}")
        print(f"  Errors:              {stats.get('errors', 0)}")
        return

    # Initialize chatbot
    chatbot.initialize()

    # Handle --status
    if args.status:
        print_status(chatbot)
        return

    # Handle --query (single question mode)
    if args.query:
        result = chatbot.ask(args.query)
        print_answer(result)
        return

    # Default: interactive CLI
    interactive_cli(chatbot)


if __name__ == "__main__":
    main()