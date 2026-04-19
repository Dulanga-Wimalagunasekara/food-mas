from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Restaurant(Base):
    __tablename__ = "restaurants"
    __table_args__ = (Index("idx_cuisine_city", "cuisine", "city"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    cuisine = Column(String(60), nullable=False)
    city = Column(String(60), nullable=False)
    rating = Column(Numeric(2, 1), nullable=False)
    avg_delivery_min = Column(Integer, nullable=False)
    delivery_fee = Column(Numeric(8, 2), nullable=False)
    is_open = Column(Boolean, nullable=False, default=True)

    menu_items = relationship("MenuItem", back_populates="restaurant", cascade="all, delete-orphan")


class MenuItem(Base):
    __tablename__ = "menu_items"
    __table_args__ = (Index("idx_restaurant", "restaurant_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    name = Column(String(120), nullable=False)
    description = Column(Text)
    price = Column(Numeric(8, 2), nullable=False)
    category = Column(String(40), nullable=False)  # starter, main, dessert, drink
    dietary_tags = Column(JSON, nullable=False)     # ["vegetarian", "spicy", "gluten_free"]
    in_stock = Column(Boolean, nullable=False, default=True)

    restaurant = relationship("Restaurant", back_populates="menu_items")
