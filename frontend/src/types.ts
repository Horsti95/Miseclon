export type SlotType = "breakfast" | "lunch" | "dinner" | "snack";
export type DietType = "omnivore" | "vegetarian" | "vegan" | "pescatarian";
export type LocationType = "fridge" | "freezer" | "pantry";

export interface AppSettings {
  postal_code: string;
  primary_store_chain: string;
  enabled_stores: string[];
  default_servings: number;
  default_days: number;
  default_max_effort: number;
  weekly_budget_eur: number;
  kcal_target: number;
  protein_g_target: number;
  carbs_g_target: number;
  fiber_g_target: number;
  fat_g_target: number;
  prefer_complex_carbs: boolean;
  diet_type: DietType;
  excluded_ingredients: string[];
  kitchen_equipment: string[];
  max_stores_per_trip: number;
  llm_base_url: string;
  llm_model: string;
  llm_api_key: string;
  llm_temperature: number;
  auto_sync_offers_on_start: boolean;
}

export interface Ingredient {
  id: number;
  slug: string;
  name: string;
  category: string;
  default_unit: string;
  grams_per_unit: number;
  kcal_100: number;
  protein_100: number;
  carbs_100: number;
  sugar_100: number;
  fiber_100: number;
  fat_100: number;
  carb_type: string;
  is_pantry_staple: boolean;
  default_shelf_life_days: number;
  default_pack_size: number;
  reference_price_eur: number;
  reference_price_per_base_unit: number;
  reference_store: string;
  nutrition_source: string;
  active_offer_price: number | null;
  active_offer_store: string | null;
}

export interface RecipeIngredient {
  id: number;
  ingredient_id: number;
  ingredient_name: string;
  category: string;
  amount: number;
  unit: string;
  preparation_note: string | null;
  is_optional: boolean;
  carb_type: string;
  estimated_cost_eur: number;
}

export interface Recipe {
  id: number;
  slug: string | null;
  title: string;
  description: string;
  servings: number;
  prep_time_min: number;
  cook_time_min: number;
  total_time_min: number;
  effort_level: number;
  effort_label: string;
  diet_type: string;
  meal_types: string[];
  tags: string[];
  instructions: string[];
  source: string;
  source_url: string | null;
  is_favorite: boolean;
  rating: number | null;
  image_emoji: string;
  kcal_per_serving: number;
  protein_g: number;
  carbs_g: number;
  sugar_g: number;
  fiber_g: number;
  fat_g: number;
  complex_carb_ratio: number;
  estimated_cost_per_serving: number;
  macros_verified: boolean;
  ingredients: RecipeIngredient[];
}

export interface MealPlanEntry {
  id: number;
  day_of_week: number;
  day_label: string;
  slot: SlotType;
  servings: number;
  is_leftover_from_entry_id: number | null;
  is_cooked: boolean;
  notes: string | null;
  recipe: Recipe;
}

export interface DayMacroSummary {
  day_of_week: number;
  day_label: string;
  kcal: number;
  protein_g: number;
  carbs_g: number;
  sugar_g: number;
  fiber_g: number;
  fat_g: number;
  complex_carb_ratio: number;
  estimated_cost_per_person: number;
  estimated_cost_total: number;
  meals_count: number;
  cooked_count: number;
}

export interface MealPlan {
  id: number;
  title: string;
  week_start_date: string;
  days_count: number;
  servings_per_meal: number;
  max_effort_level: number;
  target_budget_eur: number;
  active_slots: SlotType[];
  batch_cooking: boolean;
  status: string;
  estimated_cost_eur: number;
  shopping_cost_after_pantry_eur: number;
  llm_rationale: string | null;
  entries: MealPlanEntry[];
  daily_macros: DayMacroSummary[];
  weekly_avg_kcal: number;
  weekly_avg_protein_g: number;
  weekly_avg_carbs_g: number;
  weekly_avg_fiber_g: number;
  weekly_avg_fat_g: number;
  weekly_avg_complex_carb_ratio: number;
}

export interface ShoppingListItem {
  id: number;
  ingredient_id: number | null;
  custom_name: string;
  category: string;
  needed_amount: number;
  pantry_deducted_amount: number;
  to_buy_amount: number;
  unit: string;
  pack_size: number;
  suggested_pack_count: number;
  remainder_amount: number;
  assigned_store_name: string;
  estimated_price_eur: number;
  actual_price_eur: number | null;
  price_confidence: "promo" | "verified" | "estimated";
  offer_title: string | null;
  offer_valid_to: string | null;
  is_checked: boolean;
  added_to_pantry: boolean;
  manual_addition: boolean;
}

export interface RemainderSuggestion {
  ingredient_id: number;
  ingredient_name: string;
  remainder_amount: number;
  unit: string;
  suggested_recipes: {
    recipe_id: number;
    title: string;
    effort_level: number;
    kcal_per_serving: number;
    protein_g: number;
  }[];
}

export interface ShoppingList {
  id: number;
  meal_plan_id: number;
  status: string;
  total_estimated_eur: number;
  total_actual_eur: number;
  promo_items_count: number;
  verified_items_count: number;
  estimated_items_count: number;
  checked_count: number;
  total_items_count: number;
  store_breakdown: Record<string, number>;
  remainder_suggestions: RemainderSuggestion[];
  items: ShoppingListItem[];
}

export interface PantryItem {
  id: number;
  ingredient_id: number;
  ingredient_name: string;
  category: string;
  quantity: number;
  unit: string;
  location: LocationType;
  opened_at: string | null;
  expires_at: string | null;
  days_until_expiry: number | null;
  use_priority: "normal" | "use_soon" | "urgent";
  notes: string | null;
}

export interface PantrySuggestion {
  recipe: Recipe;
  matched_ingredients: string[];
  missing_count: number;
  coverage_pct: number;
}

export interface Offer {
  id: number;
  store_name: string;
  source_provider: string;
  raw_title: string;
  brand: string | null;
  price_eur: number;
  base_price_eur: number | null;
  base_unit: string | null;
  pack_size_value: number | null;
  pack_size_unit: string | null;
  is_promo: boolean;
  is_organic: boolean;
  valid_from: string | null;
  valid_to: string | null;
  matched_ingredient_id: number | null;
  matched_ingredient_name: string | null;
  match_id: number | null;
  match_confidence: number | null;
  match_confirmed: boolean;
  match_rejected: boolean;
  protein_per_euro: number | null;
}

export interface LlmHealth {
  connected: boolean;
  provider: string;
  base_url: string;
  configured_model: string;
  available_models: string[];
  model_ready: boolean;
  error?: string;
}

export const SLOT_LABELS: Record<SlotType, string> = {
  breakfast: "Frühstück",
  lunch: "Mittagessen",
  dinner: "Abendessen",
  snack: "Snack",
};

export const KITCHEN_EQUIPMENT_OPTIONS: {
  id: string;
  label: string;
  hint: string;
}[] = [
  { id: "airfryer", label: "Airfryer", hint: "Knusprig in 10–16 Min., wenig Öl" },
  { id: "stove_2_burners", label: "Herd (2 Platten)", hint: "Max. 2 Töpfe/Pfannen parallel" },
  { id: "stove_4_burners", label: "Herd (4 Platten)", hint: "Großes Kochfeld" },
  { id: "oven", label: "Backofen", hint: "Blechgerichte & Aufläufe" },
  { id: "microwave", label: "Mikrowelle", hint: "Schnelles Aufwärmen" },
  { id: "blender", label: "Mixer / Pürierstab", hint: "Shakes & cremige Suppen" },
  { id: "rice_cooker", label: "Reiskocher", hint: "Automatisch perfekter Reis" },
];

export const EFFORT_META: Record<
  number,
  { label: string; short: string; desc: string; badgeClass: string }
> = {
  1: {
    label: "Ultra-Simpel",
    short: "Simpel",
    desc: "≤ 15 Min · 1 Topf/No-Cook",
    badgeClass: "bg-emerald-50 text-emerald-800 border-emerald-200",
  },
  2: {
    label: "Alltagstauglich",
    short: "Alltag",
    desc: "15–30 Min · unkompliziert",
    badgeClass: "bg-amber-50 text-amber-800 border-amber-200",
  },
  3: {
    label: "Ambitioniert",
    short: "Genuss",
    desc: "30–50 Min · raffinierter",
    badgeClass: "bg-orange-50 text-orange-800 border-orange-200",
  },
};
