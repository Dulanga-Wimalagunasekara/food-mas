"""Idempotent seed script. Safe to run multiple times — uses upsert logic."""
from __future__ import annotations

import sys
from typing import Any

from sqlalchemy import select

from src.db.models import Base, MenuItem, Restaurant
from src.db.session import SessionLocal, engine

RESTAURANTS: list[dict[str, Any]] = [
    # --- Sri Lankan ---
    {"name": "Laksala Kitchen", "cuisine": "sri_lankan", "city": "Colombo", "rating": 4.5, "avg_delivery_min": 30, "delivery_fee": 150.00, "is_open": True},
    {"name": "Curry Leaf Bistro", "cuisine": "sri_lankan", "city": "Colombo", "rating": 4.2, "avg_delivery_min": 40, "delivery_fee": 120.00, "is_open": True},
    {"name": "The Cinnamon House", "cuisine": "sri_lankan", "city": "Kandy", "rating": 4.7, "avg_delivery_min": 35, "delivery_fee": 180.00, "is_open": True},
    # --- Indian ---
    {"name": "Spice Route", "cuisine": "indian", "city": "Colombo", "rating": 4.3, "avg_delivery_min": 45, "delivery_fee": 200.00, "is_open": True},
    {"name": "Tandoor Palace", "cuisine": "indian", "city": "Colombo", "rating": 4.0, "avg_delivery_min": 50, "delivery_fee": 180.00, "is_open": True},
    # --- Chinese ---
    {"name": "Golden Dragon", "cuisine": "chinese", "city": "Colombo", "rating": 4.1, "avg_delivery_min": 35, "delivery_fee": 160.00, "is_open": True},
    {"name": "Jade Garden", "cuisine": "chinese", "city": "Colombo", "rating": 3.9, "avg_delivery_min": 40, "delivery_fee": 140.00, "is_open": True},
    # --- Italian ---
    {"name": "La Piazza", "cuisine": "italian", "city": "Colombo", "rating": 4.6, "avg_delivery_min": 50, "delivery_fee": 250.00, "is_open": True},
    {"name": "Trattoria Roma", "cuisine": "italian", "city": "Colombo", "rating": 4.4, "avg_delivery_min": 45, "delivery_fee": 220.00, "is_open": True},
    # --- American ---
    {"name": "The Burger Lab", "cuisine": "american", "city": "Colombo", "rating": 4.2, "avg_delivery_min": 25, "delivery_fee": 130.00, "is_open": True},
    {"name": "Smoky Barrel BBQ", "cuisine": "american", "city": "Colombo", "rating": 4.5, "avg_delivery_min": 40, "delivery_fee": 200.00, "is_open": True},
    # --- Japanese ---
    {"name": "Sakura Sushi Bar", "cuisine": "japanese", "city": "Colombo", "rating": 4.8, "avg_delivery_min": 45, "delivery_fee": 300.00, "is_open": True},
    {"name": "Zen Ramen House", "cuisine": "japanese", "city": "Colombo", "rating": 4.3, "avg_delivery_min": 35, "delivery_fee": 200.00, "is_open": True},
    # --- Thai ---
    {"name": "Bangkok Street", "cuisine": "thai", "city": "Colombo", "rating": 4.1, "avg_delivery_min": 40, "delivery_fee": 175.00, "is_open": True},
    {"name": "Thai Orchid", "cuisine": "thai", "city": "Kandy", "rating": 4.4, "avg_delivery_min": 50, "delivery_fee": 190.00, "is_open": True},
]

MENU_ITEMS: dict[str, list[dict[str, Any]]] = {
    "Laksala Kitchen": [
        {"name": "Kottu Roti", "description": "Classic roti stir-fried with vegetables and egg", "price": 450.00, "category": "main", "dietary_tags": ["spicy"], "in_stock": True},
        {"name": "Fish Ambul Thiyal", "description": "Sour fish curry with goraka", "price": 650.00, "category": "main", "dietary_tags": ["spicy", "seafood", "gluten_free"], "in_stock": True},
        {"name": "Dhal Curry", "description": "Red lentil curry with coconut milk", "price": 280.00, "category": "main", "dietary_tags": ["vegetarian", "vegan", "gluten_free"], "in_stock": True},
        {"name": "Pol Sambol", "description": "Coconut relish with chili and lime", "price": 150.00, "category": "starter", "dietary_tags": ["vegetarian", "vegan", "spicy", "gluten_free"], "in_stock": True},
        {"name": "Watalappan", "description": "Traditional coconut custard with jaggery", "price": 320.00, "category": "dessert", "dietary_tags": ["vegetarian", "gluten_free"], "in_stock": True},
        {"name": "Ginger Beer", "description": "House-made ginger beer", "price": 180.00, "category": "drink", "dietary_tags": ["vegan", "gluten_free"], "in_stock": True},
        {"name": "Hoppers", "description": "Bowl-shaped pancakes with egg", "price": 200.00, "category": "starter", "dietary_tags": ["vegetarian"], "in_stock": True},
        {"name": "Chicken Curry", "description": "Slow-cooked chicken in aromatic spices", "price": 580.00, "category": "main", "dietary_tags": ["spicy", "gluten_free"], "in_stock": True},
    ],
    "Curry Leaf Bistro": [
        {"name": "Lamprais", "description": "Rice and curry baked in banana leaf", "price": 750.00, "category": "main", "dietary_tags": ["spicy"], "in_stock": True},
        {"name": "String Hoppers", "description": "Steamed rice noodle cakes", "price": 250.00, "category": "starter", "dietary_tags": ["vegetarian", "vegan", "gluten_free"], "in_stock": True},
        {"name": "Prawn Curry", "description": "Fresh prawns in coconut gravy", "price": 850.00, "category": "main", "dietary_tags": ["spicy", "seafood", "gluten_free"], "in_stock": True},
        {"name": "Jackfruit Curry", "description": "Young jackfruit in spiced coconut milk", "price": 380.00, "category": "main", "dietary_tags": ["vegetarian", "vegan", "gluten_free"], "in_stock": True},
        {"name": "Curd and Treacle", "description": "Buffalo curd with kithul treacle", "price": 220.00, "category": "dessert", "dietary_tags": ["vegetarian", "gluten_free"], "in_stock": True},
        {"name": "King Coconut Water", "description": "Fresh king coconut", "price": 120.00, "category": "drink", "dietary_tags": ["vegan", "gluten_free"], "in_stock": True},
        {"name": "Devilled Chicken", "description": "Spicy stir-fried chicken with capsicum", "price": 620.00, "category": "main", "dietary_tags": ["spicy"], "in_stock": True},
        {"name": "Papadum", "description": "Crispy lentil wafers", "price": 80.00, "category": "starter", "dietary_tags": ["vegetarian", "vegan", "gluten_free"], "in_stock": True},
    ],
    "The Cinnamon House": [
        {"name": "Rice and Curry Platter", "description": "Steamed rice with 6 curries", "price": 900.00, "category": "main", "dietary_tags": ["spicy", "gluten_free"], "in_stock": True},
        {"name": "Isso Wadei", "description": "Prawn-topped lentil fritters", "price": 420.00, "category": "starter", "dietary_tags": ["spicy", "seafood"], "in_stock": True},
        {"name": "Vegetable Kottu", "description": "Kottu roti with mixed vegetables", "price": 380.00, "category": "main", "dietary_tags": ["vegetarian", "spicy"], "in_stock": True},
        {"name": "Mutton Rolls", "description": "Deep-fried pastry with spiced mutton filling", "price": 280.00, "category": "starter", "dietary_tags": ["spicy"], "in_stock": True},
        {"name": "Kavum", "description": "Traditional oil cake with jaggery", "price": 180.00, "category": "dessert", "dietary_tags": ["vegetarian", "vegan"], "in_stock": True},
        {"name": "Faluda", "description": "Rose milk dessert drink with basil seeds", "price": 250.00, "category": "drink", "dietary_tags": ["vegetarian"], "in_stock": True},
        {"name": "Egg Hoppers", "description": "Crispy hoppers with soft egg centre", "price": 180.00, "category": "starter", "dietary_tags": ["vegetarian"], "in_stock": True},
        {"name": "Tuna Curry", "description": "Fresh tuna in tamarind gravy", "price": 700.00, "category": "main", "dietary_tags": ["spicy", "seafood", "gluten_free"], "in_stock": True},
    ],
    "Spice Route": [
        {"name": "Butter Chicken", "description": "Tender chicken in creamy tomato sauce", "price": 720.00, "category": "main", "dietary_tags": [], "in_stock": True},
        {"name": "Paneer Tikka Masala", "description": "Grilled cottage cheese in spiced gravy", "price": 650.00, "category": "main", "dietary_tags": ["vegetarian", "spicy"], "in_stock": True},
        {"name": "Garlic Naan", "description": "Leavened bread with garlic butter", "price": 180.00, "category": "starter", "dietary_tags": ["vegetarian"], "in_stock": True},
        {"name": "Dal Makhani", "description": "Black lentils slow-cooked with butter", "price": 480.00, "category": "main", "dietary_tags": ["vegetarian"], "in_stock": True},
        {"name": "Samosa 2 pcs", "description": "Crispy pastry with spiced potato filling", "price": 220.00, "category": "starter", "dietary_tags": ["vegetarian", "vegan", "spicy"], "in_stock": True},
        {"name": "Gulab Jamun", "description": "Milk solid dumplings in rose syrup", "price": 280.00, "category": "dessert", "dietary_tags": ["vegetarian"], "in_stock": True},
        {"name": "Mango Lassi", "description": "Yoghurt-based mango drink", "price": 250.00, "category": "drink", "dietary_tags": ["vegetarian", "gluten_free"], "in_stock": True},
        {"name": "Lamb Rogan Josh", "description": "Kashmiri braised lamb with aromatic spices", "price": 850.00, "category": "main", "dietary_tags": ["spicy", "gluten_free"], "in_stock": True},
    ],
    "Tandoor Palace": [
        {"name": "Chicken Tandoori", "description": "Marinated chicken roasted in clay oven", "price": 780.00, "category": "main", "dietary_tags": ["spicy", "gluten_free"], "in_stock": True},
        {"name": "Aloo Paratha", "description": "Whole wheat flatbread stuffed with spiced potato", "price": 280.00, "category": "starter", "dietary_tags": ["vegetarian"], "in_stock": True},
        {"name": "Chana Masala", "description": "Chickpeas in tangy spiced tomato gravy", "price": 420.00, "category": "main", "dietary_tags": ["vegetarian", "vegan", "spicy"], "in_stock": True},
        {"name": "Palak Paneer", "description": "Cottage cheese in creamed spinach", "price": 580.00, "category": "main", "dietary_tags": ["vegetarian", "gluten_free"], "in_stock": True},
        {"name": "Onion Bhaji", "description": "Crispy onion fritters", "price": 200.00, "category": "starter", "dietary_tags": ["vegetarian", "vegan", "spicy"], "in_stock": True},
        {"name": "Kheer", "description": "Rice pudding with cardamom and pistachios", "price": 240.00, "category": "dessert", "dietary_tags": ["vegetarian", "gluten_free"], "in_stock": True},
        {"name": "Masala Chai", "description": "Spiced milk tea", "price": 150.00, "category": "drink", "dietary_tags": ["vegetarian"], "in_stock": True},
        {"name": "Prawn Masala", "description": "Prawns in spiced onion-tomato gravy", "price": 900.00, "category": "main", "dietary_tags": ["spicy", "seafood", "gluten_free"], "in_stock": True},
    ],
    "Golden Dragon": [
        {"name": "Dim Sum Basket 6 pcs", "description": "Steamed dumplings with pork and shrimp", "price": 550.00, "category": "starter", "dietary_tags": ["seafood"], "in_stock": True},
        {"name": "Kung Pao Chicken", "description": "Stir-fried chicken with peanuts and chili", "price": 700.00, "category": "main", "dietary_tags": ["spicy", "gluten_free"], "in_stock": True},
        {"name": "Vegetable Fried Rice", "description": "Wok-fried rice with seasonal vegetables", "price": 480.00, "category": "main", "dietary_tags": ["vegetarian", "vegan"], "in_stock": True},
        {"name": "Sweet and Sour Pork", "description": "Crispy pork in tangy sauce", "price": 750.00, "category": "main", "dietary_tags": ["pork"], "in_stock": True},
        {"name": "Spring Rolls 4 pcs", "description": "Crispy rolls with vegetable filling", "price": 320.00, "category": "starter", "dietary_tags": ["vegetarian", "vegan"], "in_stock": True},
        {"name": "Mango Pudding", "description": "Chilled mango dessert", "price": 280.00, "category": "dessert", "dietary_tags": ["vegetarian", "gluten_free"], "in_stock": True},
        {"name": "Jasmine Tea", "description": "Fragrant Chinese tea", "price": 120.00, "category": "drink", "dietary_tags": ["vegan", "gluten_free"], "in_stock": True},
        {"name": "Mapo Tofu", "description": "Soft tofu in spicy bean sauce", "price": 520.00, "category": "main", "dietary_tags": ["vegetarian", "spicy"], "in_stock": True},
    ],
    "Jade Garden": [
        {"name": "Wonton Soup", "description": "Pork and prawn dumplings in clear broth", "price": 420.00, "category": "starter", "dietary_tags": ["seafood"], "in_stock": True},
        {"name": "Beef Chow Mein", "description": "Stir-fried noodles with beef and vegetables", "price": 680.00, "category": "main", "dietary_tags": [], "in_stock": True},
        {"name": "Steamed Fish with Ginger", "description": "Whole fish steamed with soy and ginger", "price": 950.00, "category": "main", "dietary_tags": ["seafood", "gluten_free"], "in_stock": True},
        {"name": "Tofu and Mushroom Stir-fry", "description": "Silken tofu with shiitake mushrooms", "price": 480.00, "category": "main", "dietary_tags": ["vegetarian", "vegan", "gluten_free"], "in_stock": True},
        {"name": "Pork Baozi 3 pcs", "description": "Steamed buns with barbecue pork filling", "price": 350.00, "category": "starter", "dietary_tags": ["pork"], "in_stock": True},
        {"name": "Sesame Balls 4 pcs", "description": "Glutinous rice balls with lotus paste", "price": 260.00, "category": "dessert", "dietary_tags": ["vegetarian", "vegan"], "in_stock": True},
        {"name": "Chrysanthemum Tea", "description": "Floral Chinese herbal tea", "price": 130.00, "category": "drink", "dietary_tags": ["vegan", "gluten_free"], "in_stock": True},
    ],
    "La Piazza": [
        {"name": "Margherita Pizza", "description": "San Marzano tomato, fior di latte, fresh basil", "price": 1200.00, "category": "main", "dietary_tags": ["vegetarian"], "in_stock": True},
        {"name": "Spaghetti Carbonara", "description": "Pasta with guanciale, egg yolk, and pecorino", "price": 1100.00, "category": "main", "dietary_tags": ["pork"], "in_stock": True},
        {"name": "Bruschetta al Pomodoro", "description": "Grilled bread with tomato and basil", "price": 450.00, "category": "starter", "dietary_tags": ["vegetarian", "vegan"], "in_stock": True},
        {"name": "Risotto ai Funghi", "description": "Arborio rice with porcini and truffle oil", "price": 1300.00, "category": "main", "dietary_tags": ["vegetarian", "gluten_free"], "in_stock": True},
        {"name": "Tiramisu", "description": "Classic mascarpone dessert with espresso", "price": 650.00, "category": "dessert", "dietary_tags": ["vegetarian"], "in_stock": True},
        {"name": "Panna Cotta", "description": "Vanilla cream with berry coulis", "price": 580.00, "category": "dessert", "dietary_tags": ["vegetarian", "gluten_free"], "in_stock": True},
        {"name": "Sparkling Water", "description": "Imported Italian mineral water 750ml", "price": 350.00, "category": "drink", "dietary_tags": ["vegan", "gluten_free"], "in_stock": True},
        {"name": "Focaccia al Rosmarino", "description": "Rosemary focaccia with olive oil", "price": 420.00, "category": "starter", "dietary_tags": ["vegetarian", "vegan"], "in_stock": True},
    ],
    "Trattoria Roma": [
        {"name": "Penne Arrabbiata", "description": "Pasta in spicy tomato sauce", "price": 900.00, "category": "main", "dietary_tags": ["vegetarian", "vegan", "spicy"], "in_stock": True},
        {"name": "Quattro Stagioni Pizza", "description": "Four seasons pizza with ham, mushroom, artichoke, olive", "price": 1350.00, "category": "main", "dietary_tags": ["pork"], "in_stock": True},
        {"name": "Caprese Salad", "description": "Fresh mozzarella, tomato, basil", "price": 680.00, "category": "starter", "dietary_tags": ["vegetarian", "gluten_free"], "in_stock": True},
        {"name": "Osso Buco", "description": "Braised veal shank with gremolata", "price": 1800.00, "category": "main", "dietary_tags": ["gluten_free"], "in_stock": True},
        {"name": "Cannoli Siciliani", "description": "Crispy pastry tubes with ricotta cream", "price": 520.00, "category": "dessert", "dietary_tags": ["vegetarian"], "in_stock": True},
        {"name": "Minestrone Soup", "description": "Seasonal vegetable soup with pasta", "price": 480.00, "category": "starter", "dietary_tags": ["vegetarian", "vegan"], "in_stock": True},
        {"name": "Americano", "description": "Double espresso with hot water", "price": 280.00, "category": "drink", "dietary_tags": ["vegan", "gluten_free"], "in_stock": True},
        {"name": "Gnocchi al Pesto", "description": "Potato dumplings with basil pesto", "price": 980.00, "category": "main", "dietary_tags": ["vegetarian"], "in_stock": True},
    ],
    "The Burger Lab": [
        {"name": "Classic Smash Burger", "description": "Double smash patty with American cheese and cornichons", "price": 850.00, "category": "main", "dietary_tags": [], "in_stock": True},
        {"name": "Veggie Black Bean Burger", "description": "Black bean patty with avocado and chipotle mayo", "price": 780.00, "category": "main", "dietary_tags": ["vegetarian"], "in_stock": True},
        {"name": "Crispy Chicken Sandwich", "description": "Buttermilk fried chicken with coleslaw", "price": 820.00, "category": "main", "dietary_tags": [], "in_stock": True},
        {"name": "Loaded Fries", "description": "Fries with bacon, cheese sauce, and jalapeno", "price": 480.00, "category": "starter", "dietary_tags": ["pork", "spicy"], "in_stock": True},
        {"name": "Onion Rings", "description": "Beer-battered onion rings with dipping sauce", "price": 350.00, "category": "starter", "dietary_tags": ["vegetarian"], "in_stock": True},
        {"name": "Chocolate Milkshake", "description": "Thick shake with premium chocolate ice cream", "price": 450.00, "category": "drink", "dietary_tags": ["vegetarian"], "in_stock": True},
        {"name": "Craft Lemonade", "description": "House-squeezed lemonade with mint", "price": 280.00, "category": "drink", "dietary_tags": ["vegan", "gluten_free"], "in_stock": True},
        {"name": "Cheesesteak Sandwich", "description": "Shaved beef with provolone and sauteed peppers", "price": 950.00, "category": "main", "dietary_tags": [], "in_stock": True},
    ],
    "Smoky Barrel BBQ": [
        {"name": "Baby Back Ribs Half Rack", "description": "Hickory-smoked pork ribs with BBQ sauce", "price": 1600.00, "category": "main", "dietary_tags": ["pork"], "in_stock": True},
        {"name": "Brisket Plate", "description": "12-hour smoked beef brisket with sides", "price": 1800.00, "category": "main", "dietary_tags": ["gluten_free"], "in_stock": True},
        {"name": "Pulled Pork Sandwich", "description": "Slow-smoked pulled pork on brioche bun", "price": 950.00, "category": "main", "dietary_tags": ["pork"], "in_stock": True},
        {"name": "Mac and Cheese", "description": "Smoked mac and cheese with breadcrumb topping", "price": 580.00, "category": "starter", "dietary_tags": ["vegetarian"], "in_stock": True},
        {"name": "Coleslaw", "description": "House-made creamy coleslaw", "price": 250.00, "category": "starter", "dietary_tags": ["vegetarian", "gluten_free"], "in_stock": True},
        {"name": "Corn on the Cob", "description": "Grilled corn with compound butter", "price": 320.00, "category": "starter", "dietary_tags": ["vegetarian", "gluten_free"], "in_stock": True},
        {"name": "Banana Pudding", "description": "Layered banana pudding with vanilla wafers", "price": 420.00, "category": "dessert", "dietary_tags": ["vegetarian"], "in_stock": True},
        {"name": "Craft Root Beer Float", "description": "Housemade root beer float", "price": 380.00, "category": "drink", "dietary_tags": ["vegetarian"], "in_stock": True},
    ],
    "Sakura Sushi Bar": [
        {"name": "Salmon Sashimi 8 pcs", "description": "Premium Norwegian salmon, thinly sliced", "price": 1400.00, "category": "main", "dietary_tags": ["seafood", "gluten_free"], "in_stock": True},
        {"name": "Dragon Roll", "description": "Shrimp tempura roll topped with avocado and eel", "price": 1200.00, "category": "main", "dietary_tags": ["seafood"], "in_stock": True},
        {"name": "Edamame", "description": "Salted steamed soybeans", "price": 380.00, "category": "starter", "dietary_tags": ["vegetarian", "vegan", "gluten_free"], "in_stock": True},
        {"name": "Miso Soup", "description": "Traditional miso with tofu and wakame", "price": 280.00, "category": "starter", "dietary_tags": ["vegetarian", "vegan", "gluten_free"], "in_stock": True},
        {"name": "Veggie Tempura Roll", "description": "Avocado, cucumber, and sweet potato roll", "price": 900.00, "category": "main", "dietary_tags": ["vegetarian", "vegan"], "in_stock": True},
        {"name": "Tonkatsu Ramen", "description": "Rich pork-bone broth with noodles and chashu pork", "price": 1100.00, "category": "main", "dietary_tags": ["pork"], "in_stock": True},
        {"name": "Matcha Ice Cream", "description": "House-churned green tea ice cream", "price": 480.00, "category": "dessert", "dietary_tags": ["vegetarian", "gluten_free"], "in_stock": True},
        {"name": "Sencha Green Tea", "description": "Premium Japanese loose-leaf tea", "price": 250.00, "category": "drink", "dietary_tags": ["vegan", "gluten_free"], "in_stock": True},
    ],
    "Zen Ramen House": [
        {"name": "Shoyu Ramen", "description": "Soy-based broth with chicken, bamboo shoots, and soft egg", "price": 980.00, "category": "main", "dietary_tags": [], "in_stock": True},
        {"name": "Spicy Miso Ramen", "description": "Miso-based broth with tofu and spicy paste", "price": 900.00, "category": "main", "dietary_tags": ["vegetarian", "spicy"], "in_stock": True},
        {"name": "Karaage Chicken 5 pcs", "description": "Japanese fried chicken with kewpie mayo", "price": 680.00, "category": "starter", "dietary_tags": ["spicy"], "in_stock": True},
        {"name": "Gyoza 6 pcs", "description": "Pan-fried pork and cabbage dumplings", "price": 520.00, "category": "starter", "dietary_tags": ["pork"], "in_stock": True},
        {"name": "Takoyaki 6 pcs", "description": "Octopus balls with bonito and mayo", "price": 580.00, "category": "starter", "dietary_tags": ["seafood"], "in_stock": True},
        {"name": "Mochi Ice Cream 3 pcs", "description": "Rice cake filled with ice cream", "price": 450.00, "category": "dessert", "dietary_tags": ["vegetarian", "gluten_free"], "in_stock": True},
        {"name": "Ramune Soda", "description": "Japanese marble-bottle soft drink", "price": 280.00, "category": "drink", "dietary_tags": ["vegan", "gluten_free"], "in_stock": True},
        {"name": "Vegetable Ramen", "description": "Clear kombu broth with seasonal vegetables and noodles", "price": 780.00, "category": "main", "dietary_tags": ["vegetarian", "vegan"], "in_stock": True},
    ],
    "Bangkok Street": [
        {"name": "Pad Thai with Shrimp", "description": "Rice noodles with shrimp, egg, bean sprouts, and peanuts", "price": 780.00, "category": "main", "dietary_tags": ["seafood", "spicy"], "in_stock": True},
        {"name": "Green Curry Chicken", "description": "Coconut-based green curry with chicken and Thai basil", "price": 850.00, "category": "main", "dietary_tags": ["spicy", "gluten_free"], "in_stock": True},
        {"name": "Tom Yum Soup", "description": "Spicy and sour lemongrass soup with shrimp", "price": 650.00, "category": "starter", "dietary_tags": ["seafood", "spicy", "gluten_free"], "in_stock": True},
        {"name": "Som Tum", "description": "Green papaya salad with fish sauce and peanuts", "price": 420.00, "category": "starter", "dietary_tags": ["spicy", "gluten_free"], "in_stock": True},
        {"name": "Massaman Curry", "description": "Mild curry with beef, potato, and peanuts", "price": 900.00, "category": "main", "dietary_tags": ["gluten_free"], "in_stock": True},
        {"name": "Mango Sticky Rice", "description": "Sweet sticky rice with fresh mango and coconut milk", "price": 380.00, "category": "dessert", "dietary_tags": ["vegetarian", "vegan", "gluten_free"], "in_stock": True},
        {"name": "Thai Iced Tea", "description": "Creamy orange-spiced tea with condensed milk", "price": 280.00, "category": "drink", "dietary_tags": ["vegetarian", "gluten_free"], "in_stock": True},
        {"name": "Tofu Pad See Ew", "description": "Wide rice noodles with tofu in soy sauce", "price": 680.00, "category": "main", "dietary_tags": ["vegetarian", "vegan"], "in_stock": True},
    ],
    "Thai Orchid": [
        {"name": "Red Curry with Vegetables", "description": "Spicy coconut curry with mixed vegetables", "price": 720.00, "category": "main", "dietary_tags": ["vegetarian", "vegan", "spicy", "gluten_free"], "in_stock": True},
        {"name": "Pork Larb", "description": "Minced pork salad with herbs and toasted rice", "price": 780.00, "category": "main", "dietary_tags": ["pork", "spicy", "gluten_free"], "in_stock": True},
        {"name": "Fresh Spring Rolls 4 pcs", "description": "Fresh rice paper rolls with vegetables and herbs", "price": 380.00, "category": "starter", "dietary_tags": ["vegetarian", "vegan", "gluten_free"], "in_stock": True},
        {"name": "Panang Curry", "description": "Rich coconut curry with beef and kaffir lime", "price": 880.00, "category": "main", "dietary_tags": ["spicy", "gluten_free"], "in_stock": True},
        {"name": "Tom Kha Soup", "description": "Galangal and lemongrass soup with mushrooms", "price": 580.00, "category": "starter", "dietary_tags": ["vegetarian", "gluten_free"], "in_stock": True},
        {"name": "Taro Ball Dessert", "description": "Taro balls in sweet coconut milk", "price": 320.00, "category": "dessert", "dietary_tags": ["vegetarian", "vegan", "gluten_free"], "in_stock": True},
        {"name": "Butterfly Pea Flower Tea", "description": "Colour-changing herbal tea", "price": 220.00, "category": "drink", "dietary_tags": ["vegan", "gluten_free"], "in_stock": True},
        {"name": "Cashew Chicken Stir-fry", "description": "Wok-fried chicken with cashews and dried chili", "price": 820.00, "category": "main", "dietary_tags": ["spicy", "gluten_free"], "in_stock": True},
    ],
}


def seed() -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        for r_data in RESTAURANTS:
            existing = session.execute(
                select(Restaurant).where(Restaurant.name == r_data["name"])
            ).scalar_one_or_none()

            if existing is None:
                restaurant = Restaurant(**r_data)
                session.add(restaurant)
                session.flush()
                r_id = restaurant.id
                print(f"  [+] Restaurant: {r_data['name']} (id={r_id})")
            else:
                r_id = existing.id
                print(f"  [=] Restaurant exists: {r_data['name']} (id={r_id})")

            for item_data in MENU_ITEMS.get(r_data["name"], []):
                existing_item = session.execute(
                    select(MenuItem).where(
                        MenuItem.restaurant_id == r_id,
                        MenuItem.name == item_data["name"],
                    )
                ).scalar_one_or_none()

                if existing_item is None:
                    session.add(MenuItem(restaurant_id=r_id, **item_data))

        session.commit()

    print("\nSeed complete.")
    _print_summary()


def _print_summary() -> None:
    with SessionLocal() as session:
        restaurants = session.execute(select(Restaurant)).scalars().all()
        print(f"\n{'Restaurant':<30} {'Cuisine':<15} {'City':<12} {'Items':>5}")
        print("-" * 65)
        for r in restaurants:
            count = len(
                session.execute(
                    select(MenuItem).where(MenuItem.restaurant_id == r.id)
                ).scalars().all()
            )
            print(f"{r.name:<30} {r.cuisine:<15} {r.city:<12} {count:>5}")


if __name__ == "__main__":
    print("Seeding database...")
    try:
        seed()
    except Exception as e:
        print(f"Seed failed: {e}", file=sys.stderr)
        sys.exit(1)
