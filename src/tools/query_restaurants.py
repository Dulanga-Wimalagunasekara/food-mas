from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy import select

from src.db.models import Restaurant
from src.db.session import get_session
from src.state import RestaurantCandidate
from src.tools.base import Err, Ok, Result, ToolError, tool_with_retry


class QueryRestaurantsInput(BaseModel):
    cuisines: list[str]
    city: str
    min_rating: float = 0.0
    limit: int = 10


class QueryRestaurantsOutput(BaseModel):
    restaurants: list[RestaurantCandidate]


@tool_with_retry(timeout_s=10, retries=2)
def query_restaurants(inp: QueryRestaurantsInput) -> Result[QueryRestaurantsOutput, ToolError]:
    """Query MySQL for open restaurants matching cuisine and city filters.

    Uses parameterized queries only — never builds SQL by string concatenation.
    Returns up to `limit` restaurants sorted by rating descending.

    Args:
        inp: Validated query parameters including cuisines, city, min_rating, limit.

    Returns:
        Ok(QueryRestaurantsOutput) with matching restaurants, each with a
        placeholder match_score of 0.5 (scored by the LLM in the agent layer), or
        Err(ToolError) on DB failure.

    Raises:
        Never raises — exceptions are caught and returned as Err.

    Example:
        >>> result = query_restaurants(QueryRestaurantsInput(
        ...     cuisines=["sri_lankan"], city="Colombo"
        ... ))
        >>> result.is_ok()
        True
    """
    try:
        with get_session() as session:
            stmt = (
                select(Restaurant)
                .where(
                    Restaurant.is_open.is_(True),
                    Restaurant.city == inp.city,
                    Restaurant.rating >= inp.min_rating,
                )
            )
            if inp.cuisines:
                stmt = stmt.where(Restaurant.cuisine.in_(inp.cuisines))

            stmt = stmt.order_by(Restaurant.rating.desc()).limit(inp.limit)
            rows = session.execute(stmt).scalars().all()

        candidates = [
            RestaurantCandidate(
                id=r.id,
                name=r.name,
                cuisine=r.cuisine,
                rating=float(r.rating),
                delivery_fee=float(r.delivery_fee),
                avg_delivery_min=r.avg_delivery_min,
                match_score=0.5,
            )
            for r in rows
        ]
        return Ok(QueryRestaurantsOutput(restaurants=candidates))

    except Exception as exc:
        return Err(ToolError(tool="query_restaurants", kind="db_error", message=str(exc)))
