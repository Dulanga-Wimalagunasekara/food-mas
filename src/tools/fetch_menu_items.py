from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy import select

from src.db.models import MenuItem
from src.db.session import get_session
from src.tools.base import Err, Ok, Result, ToolError, tool_with_retry


class MenuItemRecord(BaseModel):
    id: int
    name: str
    description: str
    price: float
    category: str
    dietary_tags: list[str]
    in_stock: bool


class FetchMenuItemsInput(BaseModel):
    restaurant_id: int
    dietary_exclude: list[str] = []


class FetchMenuItemsOutput(BaseModel):
    items: list[MenuItemRecord]


@tool_with_retry(timeout_s=10, retries=2)
def fetch_menu_items(inp: FetchMenuItemsInput) -> Result[FetchMenuItemsOutput, ToolError]:
    """Fetch in-stock menu items for a restaurant, filtered by dietary exclusions at the DB layer.

    Dietary exclusion filtering uses JSON_OVERLAPS at the application layer (not SQL
    string interpolation) to ensure no excluded tags appear in any returned item.

    Args:
        inp: Restaurant ID and list of dietary tags to exclude.

    Returns:
        Ok(FetchMenuItemsOutput) with filtered, in-stock items, or
        Err(ToolError) on DB failure or if restaurant has no eligible items.

    Raises:
        Never raises — exceptions are caught and returned as Err.

    Example:
        >>> result = fetch_menu_items(FetchMenuItemsInput(
        ...     restaurant_id=1, dietary_exclude=["seafood"]
        ... ))
        >>> result.is_ok()
        True
    """
    try:
        with get_session() as session:
            stmt = (
                select(MenuItem)
                .where(
                    MenuItem.restaurant_id == inp.restaurant_id,
                    MenuItem.in_stock.is_(True),
                )
            )
            rows = session.execute(stmt).scalars().all()

            exclude_set = set(inp.dietary_exclude)
            items = [
                MenuItemRecord(
                    id=row.id,
                    name=row.name,
                    description=row.description or "",
                    price=float(row.price),
                    category=row.category,
                    dietary_tags=row.dietary_tags if isinstance(row.dietary_tags, list) else [],
                    in_stock=row.in_stock,
                )
                for row in rows
                if not exclude_set.intersection(
                    row.dietary_tags if isinstance(row.dietary_tags, list) else []
                )
            ]

        return Ok(FetchMenuItemsOutput(items=items))

    except Exception as exc:
        return Err(ToolError(tool="fetch_menu_items", kind="db_error", message=str(exc)))
