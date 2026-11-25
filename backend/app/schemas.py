from typing import Literal
from pydantic import BaseModel, Field


UnitType = Literal["g", "ml", "stk"]
CarbType = Literal["complex", "simple", "mixed", "none"]
SlotType = Literal["breakfast", "lunch", "dinner", "snack"]
DietType = Literal["omnivore", "vegetarian", "vegan", "pescatarian"]
LocationType = Literal["fridge", "freezer", "pantry"]


# ---------- Settings ----------

class SettingsOut(BaseModel):
    postal_code: str
    primary_store_chain: str
    enabled_stores: list[str]
    default_servings: int
    default_days: int
    default_max_effort: int
    weekly_budget_eur: float
    kcal_target: int
    protein_g_target: int
    carbs_g_target: int
    fiber_g_target: int
    fat_g_target: int
    prefer_complex_carbs: bool
    diet_type: str
    excluded_ingredients: list[str]
    kitchen_equipment: list[str]
    max_stores_per_trip: int
    llm_base_url: str
    llm_model: str
    llm_api_key: str
    llm_temperature: float
    auto_sync_offers_on_start: bool


class SettingsUpdate(BaseModel):
    postal_code: str | None = None
    primary_store_chain: str | None = None
    enabled_stores: list[str] | None = None
    default_servings: int | None = Field(default=None, ge=1, le=12)
    default_days: int | None = Field(default=None, ge=1, le=7)
    default_max_effort: int | None = Field(default=None, ge=1, le=3)
    weekly_budget_eur: float | None = Field(default=None, ge=10.0, le=500.0)
    kcal_target: int | None = Field(default=None, ge=1000, le=6000)
    protein_g_target: int | None = Field(default=None, ge=30, le=400)
    carbs_g_target: int | None = Field(default=None, ge=20, le=700)
    fiber_g_target: int | None = Field(default=None, ge=10, le=120)
    fat_g_target: int | None = Field(default=None, ge=20, le=250)
    prefer_complex_carbs: bool | None = None
    diet_type: DietType | None = None
    excluded_ingredients: list[str] | None = None
    kitchen_equipment: list[str] | None = None
    max_stores_per_trip: int | None = Field(default=None, ge=1, le=4)
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None
    llm_temperature: float | None = Field(default=None, ge=0.0, le=1.5)
    auto_sync_offers_on_start: bool | None = None


# ---------- Ingredients ----------

class IngredientOut(BaseModel):
    id: int
    slug: str
    name: str
    category: str
    default_unit: str
    grams_per_unit: float
    kcal_100: float
    protein_100: float
    carbs_100: float
    sugar_100: float
    fiber_100: float
    fat_100: float
    carb_type: str
    is_pantry_staple: bool
    default_shelf_life_days: int
    default_pack_size: float
    reference_price_eur: float
    reference_price_per_base_unit: float
    reference_store: str
    nutrition_source: str
    active_offer_price: float | None = None
    active_offer_store: str | None = None


class IngredientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    category: str = "Sonstiges"
    default_unit: UnitType = "g"
    grams_per_unit: float = Field(default=1.0, gt=0)
    kcal_100: float = Field(default=100.0, ge=0)
    protein_100: float = Field(default=5.0, ge=0)
    carbs_100: float = Field(default=10.0, ge=0)
    sugar_100: float = Field(default=2.0, ge=0)
    fiber_100: float = Field(default=2.0, ge=0)
    fat_100: float = Field(default=3.0, ge=0)
    carb_type: CarbType = "mixed"
    is_pantry_staple: bool = False
    default_shelf_life_days: int = Field(default=14, ge=1)
    default_pack_size: float = Field(default=500.0, gt=0)
    reference_price_eur: float = Field(default=1.99, ge=0)
    reference_store: str = "ALDI"


class IngredientPriceUpdate(BaseModel):
    reference_price_eur: float = Field(ge=0.0)
    default_pack_size: float | None = Field(default=None, gt=0)
    reference_store: str | None = None


# ---------- Pantry ----------

class PantryItemOut(BaseModel):
    id: int
    ingredient_id: int
    ingredient_name: str
    category: str
    quantity: float
    unit: str
    location: str
    opened_at: str | None
    expires_at: str | None
    days_until_expiry: int | None
    use_priority: str
    notes: str | None


class PantryItemCreate(BaseModel):
    ingredient_id: int
    quantity: float = Field(gt=0)
    unit: UnitType | None = None
    location: LocationType = "pantry"
    expires_at: str | None = None
    use_priority: Literal["normal", "use_soon", "urgent"] = "normal"
    notes: str | None = None


class PantryItemUpdate(BaseModel):
    quantity: float | None = Field(default=None, ge=0)
    location: LocationType | None = None
    expires_at: str | None = None
    use_priority: Literal["normal", "use_soon", "urgent"] | None = None
    notes: str | None = None


# ---------- Recipes ----------

class RecipeIngredientOut(BaseModel):
    id: int
    ingredient_id: int
    ingredient_name: str
    category: str
    amount: float
    unit: str
    preparation_note: str | None
    is_optional: bool
    carb_type: str
    estimated_cost_eur: float


class RecipeIngredientIn(BaseModel):
    ingredient_id: int
    amount: float = Field(gt=0)
    unit: UnitType = "g"
    preparation_note: str | None = None
    is_optional: bool = False


class RecipeOut(BaseModel):
    id: int
    slug: str | None
    title: str
    description: str
    servings: int
    prep_time_min: int
    cook_time_min: int
    total_time_min: int
    effort_level: int
    effort_label: str
    diet_type: str
    meal_types: list[str]
    tags: list[str]
    instructions: list[str]
    source: str
    source_url: str | None
    is_favorite: bool
    rating: int | None
    image_emoji: str
    kcal_per_serving: float
    protein_g: float
    carbs_g: float
    sugar_g: float
    fiber_g: float
    fat_g: float
    complex_carb_ratio: float
    estimated_cost_per_serving: float
    macros_verified: bool
    ingredients: list[RecipeIngredientOut]


class RecipeCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = ""
    servings: int = Field(default=2, ge=1, le=12)
    prep_time_min: int = Field(default=10, ge=0, le=240)
    cook_time_min: int = Field(default=15, ge=0, le=360)
    effort_level: int = Field(default=1, ge=1, le=3)
    diet_type: DietType = "omnivore"
    meal_types: list[SlotType] = Field(default_factory=lambda: ["lunch", "dinner"])
    tags: list[str] = Field(default_factory=list)
    instructions: list[str] = Field(min_length=1)
    image_emoji: str = "🍽️"
    ingredients: list[RecipeIngredientIn] = Field(min_length=1)


class RecipeUrlImportRequest(BaseModel):
    url: str = Field(min_length=8)


# ---------- Meal Plans ----------

class MealPlanGenerateRequest(BaseModel):
    week_start_date: str | None = None
    days_count: int = Field(default=7, ge=1, le=7)
    servings_per_meal: int = Field(default=2, ge=1, le=12)
    max_effort_level: int = Field(default=2, ge=1, le=3)
    target_budget_eur: float | None = Field(default=None, ge=10.0, le=500.0)
    active_slots: list[SlotType] = Field(
        default_factory=lambda: ["breakfast", "lunch", "dinner", "snack"]
    )
    batch_cooking: bool = True
    use_ai: bool = False
    ai_note: str | None = None
    diet_type: DietType | None = None
    prefer_pantry_leftovers: bool = True
    prefer_offers: bool = True


class MealPlanEntryOut(BaseModel):
    id: int
    day_of_week: int
    day_label: str
    slot: str
    servings: int
    is_leftover_from_entry_id: int | None
    is_cooked: bool
    notes: str | None
    recipe: RecipeOut


class DayMacroSummary(BaseModel):
    day_of_week: int
    day_label: str
    kcal: float
    protein_g: float
    carbs_g: float
    sugar_g: float
    fiber_g: float
    fat_g: float
    complex_carb_ratio: float
    estimated_cost_per_person: float
    estimated_cost_total: float
    meals_count: int
    cooked_count: int


class MealPlanOut(BaseModel):
    id: int
    title: str
    week_start_date: str
    days_count: int
    servings_per_meal: int
    max_effort_level: int
    target_budget_eur: float
    active_slots: list[str]
    batch_cooking: bool
    status: str
    estimated_cost_eur: float
    shopping_cost_after_pantry_eur: float
    llm_rationale: str | None
    entries: list[MealPlanEntryOut]
    daily_macros: list[DayMacroSummary]
    weekly_avg_kcal: float
    weekly_avg_protein_g: float
    weekly_avg_carbs_g: float
    weekly_avg_fiber_g: float
    weekly_avg_fat_g: float
    weekly_avg_complex_carb_ratio: float


class MealPlanEntryUpdate(BaseModel):
    recipe_id: int | None = None
    servings: int | None = Field(default=None, ge=1, le=12)
    is_cooked: bool | None = None
    notes: str | None = None
    is_leftover_from_entry_id: int | None = None


class SwapSuggestionRequest(BaseModel):
    mode: Literal["balanced", "simpler", "more_protein", "cheaper", "pantry"] = "balanced"


# ---------- Shopping List ----------

class ShoppingListItemOut(BaseModel):
    id: int
    ingredient_id: int | None
    custom_name: str
    category: str
    needed_amount: float
    pantry_deducted_amount: float
    to_buy_amount: float
    unit: str
    pack_size: float
    suggested_pack_count: int
    remainder_amount: float
    assigned_store_name: str
    estimated_price_eur: float
    actual_price_eur: float | None
    price_confidence: str
    offer_title: str | None = None
    offer_valid_to: str | None = None
    is_checked: bool
    added_to_pantry: bool
    manual_addition: bool


class ShoppingListOut(BaseModel):
    id: int
    meal_plan_id: int
    status: str
    total_estimated_eur: float
    total_actual_eur: float
    promo_items_count: int
    verified_items_count: int
    estimated_items_count: int
    checked_count: int
    total_items_count: int
    store_breakdown: dict[str, float]
    remainder_suggestions: list[dict]
    items: list[ShoppingListItemOut]


class ShoppingItemUpdate(BaseModel):
    is_checked: bool | None = None
    actual_price_eur: float | None = Field(default=None, ge=0.0)
    to_buy_amount: float | None = Field(default=None, ge=0.0)


class ShoppingItemManualCreate(BaseModel):
    custom_name: str = Field(min_length=1, max_length=150)
    category: str = "Sonstiges"
    to_buy_amount: float = Field(default=1.0, gt=0)
    unit: UnitType = "stk"
    estimated_price_eur: float = Field(default=1.99, ge=0.0)
    assigned_store_name: str = "ALDI"


# ---------- Offers ----------

class OfferOut(BaseModel):
    id: int
    store_name: str
    source_provider: str
    raw_title: str
    brand: str | None
    price_eur: float
    base_price_eur: float | None
    base_unit: str | None
    pack_size_value: float | None
    pack_size_unit: str | None
    is_promo: bool
    is_organic: bool
    valid_from: str | None
    valid_to: str | None
    matched_ingredient_id: int | None = None
    matched_ingredient_name: str | None = None
    match_id: int | None = None
    match_confidence: float | None = None
    match_confirmed: bool = False
    match_rejected: bool = False
    protein_per_euro: float | None = None


class OfferSyncRequest(BaseModel):
    postal_code: str | None = None
    queries: list[str] | None = None


# ---------- AI / Structured Output Schemas ----------

class LlmRecipeIngredientSchema(BaseModel):
    ingredient_name: str = Field(description="Deutscher Standardname der Zutat")
    amount: float = Field(gt=0, description="Menge für die Gesamt-Portionen")
    unit: UnitType = Field(description="Basiseinheit: g, ml oder stk")
    preparation_note: str | None = Field(default=None)


class LlmGeneratedRecipeSchema(BaseModel):
    title: str = Field(min_length=3, max_length=140)
    description: str = Field(min_length=10, max_length=400)
    servings: int = Field(ge=1, le=8)
    prep_time_min: int = Field(ge=0, le=90)
    cook_time_min: int = Field(ge=0, le=120)
    effort_level: int = Field(ge=1, le=3)
    diet_type: DietType
    meal_types: list[SlotType] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    image_emoji: str = Field(default="🍽️", max_length=8)
    ingredients: list[LlmRecipeIngredientSchema] = Field(min_length=3)
    instructions: list[str] = Field(min_length=3)


class LlmWeeklySlotChoice(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    slot: SlotType
    recipe_id: int = Field(ge=1)
    is_leftover_of_day: int | None = Field(default=None, ge=0, le=6)
    reason: str | None = None


class LlmWeeklyPlanDraftSchema(BaseModel):
    rationale: str = Field(min_length=10, max_length=600)
    slots: list[LlmWeeklySlotChoice] = Field(min_length=1)


class AiRecipeRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=500)
    effort_level: int = Field(default=1, ge=1, le=3)
    servings: int = Field(default=2, ge=1, le=8)
    meal_type: SlotType = "dinner"
    use_pantry: bool = True
