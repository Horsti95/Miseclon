from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    postal_code: Mapped[str] = mapped_column(String(10), default="50667")
    primary_store_chain: Mapped[str] = mapped_column(String(40), default="aldi_sued")
    enabled_stores_json: Mapped[str] = mapped_column(
        Text, default='["aldi_sued", "aldi_nord", "lidl", "rewe", "edeka", "kaufland"]'
    )
    default_servings: Mapped[int] = mapped_column(Integer, default=2)
    default_days: Mapped[int] = mapped_column(Integer, default=7)
    default_max_effort: Mapped[int] = mapped_column(Integer, default=2)
    weekly_budget_eur: Mapped[float] = mapped_column(Float, default=75.0)
    kcal_target: Mapped[int] = mapped_column(Integer, default=2200)
    protein_g_target: Mapped[int] = mapped_column(Integer, default=150)
    carbs_g_target: Mapped[int] = mapped_column(Integer, default=230)
    fiber_g_target: Mapped[int] = mapped_column(Integer, default=35)
    fat_g_target: Mapped[int] = mapped_column(Integer, default=70)
    prefer_complex_carbs: Mapped[bool] = mapped_column(Boolean, default=True)
    diet_type: Mapped[str] = mapped_column(String(30), default="omnivore")
    excluded_ingredients_json: Mapped[str] = mapped_column(Text, default="[]")
    kitchen_equipment_json: Mapped[str] = mapped_column(
        Text, default='["airfryer", "stove_2_burners", "oven"]'
    )
    max_stores_per_trip: Mapped[int] = mapped_column(Integer, default=1)
    llm_base_url: Mapped[str] = mapped_column(
        String(255), default="http://127.0.0.1:11434/v1"
    )
    llm_model: Mapped[str] = mapped_column(String(120), default="qwen2.5:14b")
    llm_api_key: Mapped[str] = mapped_column(String(255), default="ollama")
    llm_temperature: Mapped[float] = mapped_column(Float, default=0.4)
    auto_sync_offers_on_start: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    default_unit: Mapped[str] = mapped_column(String(16), default="g")  # g, ml, stk
    grams_per_unit: Mapped[float] = mapped_column(Float, default=1.0)
    kcal_100: Mapped[float] = mapped_column(Float, default=0.0)
    protein_100: Mapped[float] = mapped_column(Float, default=0.0)
    carbs_100: Mapped[float] = mapped_column(Float, default=0.0)
    sugar_100: Mapped[float] = mapped_column(Float, default=0.0)
    fiber_100: Mapped[float] = mapped_column(Float, default=0.0)
    fat_100: Mapped[float] = mapped_column(Float, default=0.0)
    carb_type: Mapped[str] = mapped_column(
        String(20), default="none"
    )  # complex, simple, mixed, none
    is_pantry_staple: Mapped[bool] = mapped_column(Boolean, default=False)
    default_shelf_life_days: Mapped[int] = mapped_column(Integer, default=14)
    default_pack_size: Mapped[float] = mapped_column(Float, default=500.0)
    reference_price_eur: Mapped[float] = mapped_column(Float, default=1.99)
    reference_price_per_base_unit: Mapped[float] = mapped_column(Float, default=3.98)
    reference_store: Mapped[str] = mapped_column(String(60), default="ALDI")
    nutrition_source: Mapped[str] = mapped_column(String(40), default="bls_curated")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    aliases: Mapped[list["IngredientAlias"]] = relationship(
        back_populates="ingredient", cascade="all, delete-orphan"
    )
    pantry_items: Mapped[list["PantryItem"]] = relationship(
        back_populates="ingredient", cascade="all, delete-orphan"
    )


class IngredientAlias(Base):
    __tablename__ = "ingredient_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"), index=True
    )
    alias: Mapped[str] = mapped_column(String(160), index=True)
    exclude_keywords_json: Mapped[str] = mapped_column(Text, default="[]")

    ingredient: Mapped["Ingredient"] = relationship(back_populates="aliases")


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chain: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    postal_code: Mapped[str] = mapped_column(String(10), default="50667")
    external_store_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=10)


class PriceOffer(Base):
    __tablename__ = "price_offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int | None] = mapped_column(
        ForeignKey("stores.id", ondelete="SET NULL"), nullable=True
    )
    store_name: Mapped[str] = mapped_column(String(100), index=True)
    source_provider: Mapped[str] = mapped_column(String(50), default="marktguru")
    external_offer_id: Mapped[str] = mapped_column(String(120), index=True)
    raw_title: Mapped[str] = mapped_column(String(255))
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_eur: Mapped[float] = mapped_column(Float)
    base_price_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    base_unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    pack_size_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    pack_size_unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_promo: Mapped[bool] = mapped_column(Boolean, default=True)
    is_organic: Mapped[bool] = mapped_column(Boolean, default=False)
    valid_from: Mapped[str | None] = mapped_column(String(32), nullable=True)
    valid_to: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    raw_payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class IngredientOfferMatch(Base):
    __tablename__ = "ingredient_offer_matches"
    __table_args__ = (
        UniqueConstraint("ingredient_id", "offer_id", name="uq_ingredient_offer"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"), index=True
    )
    offer_id: Mapped[int] = mapped_column(
        ForeignKey("price_offers.id", ondelete="CASCADE"), index=True
    )
    match_method: Mapped[str] = mapped_column(String(30), default="fuzzy")
    confidence: Mapped[float] = mapped_column(Float, default=0.75)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_rejected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    ingredient: Mapped["Ingredient"] = relationship()
    offer: Mapped["PriceOffer"] = relationship()


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"), index=True
    )
    store_name: Mapped[str] = mapped_column(String(100), default="ALDI")
    price_eur: Mapped[float] = mapped_column(Float)
    pack_size_value: Mapped[float] = mapped_column(Float)
    pack_size_unit: Mapped[str] = mapped_column(String(16))
    base_price_eur: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(40), default="user_purchase")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    ingredient: Mapped["Ingredient"] = relationship()


class PantryItem(Base):
    __tablename__ = "pantry_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"), index=True
    )
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(16), default="g")
    location: Mapped[str] = mapped_column(
        String(20), default="pantry"
    )  # fridge, freezer, pantry
    opened_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    expires_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    use_priority: Mapped[str] = mapped_column(
        String(20), default="normal"
    )  # normal, use_soon, urgent
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    ingredient: Mapped["Ingredient"] = relationship(back_populates="pantry_items")


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    servings: Mapped[int] = mapped_column(Integer, default=2)
    prep_time_min: Mapped[int] = mapped_column(Integer, default=10)
    cook_time_min: Mapped[int] = mapped_column(Integer, default=15)
    effort_level: Mapped[int] = mapped_column(
        Integer, default=1, index=True
    )  # 1=Ultra-Simpel, 2=Alltag, 3=Ambitioniert
    diet_type: Mapped[str] = mapped_column(String(30), default="omnivore")
    meal_types_json: Mapped[str] = mapped_column(Text, default='["lunch", "dinner"]')
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    instructions_json: Mapped[str] = mapped_column(Text, default="[]")
    source: Mapped[str] = mapped_column(String(40), default="seed")
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_emoji: Mapped[str] = mapped_column(String(16), default="🍽️")
    kcal_per_serving: Mapped[float] = mapped_column(Float, default=0.0)
    protein_g: Mapped[float] = mapped_column(Float, default=0.0)
    carbs_g: Mapped[float] = mapped_column(Float, default=0.0)
    sugar_g: Mapped[float] = mapped_column(Float, default=0.0)
    fiber_g: Mapped[float] = mapped_column(Float, default=0.0)
    fat_g: Mapped[float] = mapped_column(Float, default=0.0)
    complex_carb_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_cost_per_serving: Mapped[float] = mapped_column(Float, default=0.0)
    macros_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="RecipeIngredient.display_order",
    )


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"), index=True
    )
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="CASCADE"), index=True
    )
    amount: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(16), default="g")
    preparation_note: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    recipe: Mapped["Recipe"] = relationship(back_populates="ingredients")
    ingredient: Mapped["Ingredient"] = relationship()


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(160), default="Wochenplan")
    week_start_date: Mapped[str] = mapped_column(String(20), index=True)
    days_count: Mapped[int] = mapped_column(Integer, default=7)
    servings_per_meal: Mapped[int] = mapped_column(Integer, default=2)
    max_effort_level: Mapped[int] = mapped_column(Integer, default=2)
    target_budget_eur: Mapped[float] = mapped_column(Float, default=75.0)
    active_slots_json: Mapped[str] = mapped_column(
        Text, default='["breakfast", "lunch", "dinner", "snack"]'
    )
    batch_cooking: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    estimated_cost_eur: Mapped[float] = mapped_column(Float, default=0.0)
    llm_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    entries: Mapped[list["MealPlanEntry"]] = relationship(
        back_populates="meal_plan",
        cascade="all, delete-orphan",
        order_by="(MealPlanEntry.day_of_week, MealPlanEntry.id)",
    )


class MealPlanEntry(Base):
    __tablename__ = "meal_plan_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meal_plan_id: Mapped[int] = mapped_column(
        ForeignKey("meal_plans.id", ondelete="CASCADE"), index=True
    )
    day_of_week: Mapped[int] = mapped_column(Integer)  # 0=Mo .. 6=So
    slot: Mapped[str] = mapped_column(
        String(20)
    )  # breakfast, lunch, dinner, snack
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"), index=True
    )
    servings: Mapped[int] = mapped_column(Integer, default=2)
    is_leftover_from_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("meal_plan_entries.id", ondelete="SET NULL"), nullable=True
    )
    is_cooked: Mapped[bool] = mapped_column(Boolean, default=False)
    cooked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    meal_plan: Mapped["MealPlan"] = relationship(back_populates="entries")
    recipe: Mapped["Recipe"] = relationship()


class ShoppingList(Base):
    __tablename__ = "shopping_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meal_plan_id: Mapped[int] = mapped_column(
        ForeignKey("meal_plans.id", ondelete="CASCADE"), unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    items: Mapped[list["ShoppingListItem"]] = relationship(
        back_populates="shopping_list",
        cascade="all, delete-orphan",
        order_by="(ShoppingListItem.category, ShoppingListItem.id)",
    )


class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shopping_list_id: Mapped[int] = mapped_column(
        ForeignKey("shopping_lists.id", ondelete="CASCADE"), index=True
    )
    ingredient_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingredients.id", ondelete="SET NULL"), nullable=True
    )
    custom_name: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(80), default="Sonstiges")
    needed_amount: Mapped[float] = mapped_column(Float, default=0.0)
    pantry_deducted_amount: Mapped[float] = mapped_column(Float, default=0.0)
    to_buy_amount: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(16), default="g")
    pack_size: Mapped[float] = mapped_column(Float, default=0.0)
    suggested_pack_count: Mapped[int] = mapped_column(Integer, default=1)
    remainder_amount: Mapped[float] = mapped_column(Float, default=0.0)
    selected_offer_id: Mapped[int | None] = mapped_column(
        ForeignKey("price_offers.id", ondelete="SET NULL"), nullable=True
    )
    assigned_store_name: Mapped[str] = mapped_column(String(80), default="ALDI")
    estimated_price_eur: Mapped[float] = mapped_column(Float, default=0.0)
    actual_price_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_confidence: Mapped[str] = mapped_column(
        String(20), default="estimated"
    )  # promo, verified, estimated
    is_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    added_to_pantry: Mapped[bool] = mapped_column(Boolean, default=False)
    manual_addition: Mapped[bool] = mapped_column(Boolean, default=False)

    shopping_list: Mapped["ShoppingList"] = relationship(back_populates="items")
    ingredient: Mapped["Ingredient | None"] = relationship()
    selected_offer: Mapped["PriceOffer | None"] = relationship()


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(60))
    postal_code: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20))  # success, partial, failed
    offers_fetched: Mapped[int] = mapped_column(Integer, default=0)
    matches_created: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class LlmGenerationLog(Base):
    __tablename__ = "llm_generation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_type: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20))
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    retries: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
