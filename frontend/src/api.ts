import type {
  AppSettings,
  Ingredient,
  LlmHealth,
  MealPlan,
  Offer,
  PantryItem,
  PantrySuggestion,
  Recipe,
  ShoppingList,
  SlotType,
} from "./types";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
    ...options,
  });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) {
        msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // ignore non-JSON error
    }
    throw new Error(msg);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export const api = {
  // Settings
  getSettings: () => request<AppSettings>("/api/settings"),
  updateSettings: (data: Partial<AppSettings>) =>
    request<AppSettings>("/api/settings", {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  // Meal Plans
  getActiveMealPlan: () => request<MealPlan>("/api/meal-plans/active"),
  generateMealPlan: (payload: {
    days_count: number;
    servings_per_meal: number;
    max_effort_level: number;
    target_budget_eur?: number;
    active_slots: SlotType[];
    batch_cooking: boolean;
    use_ai: boolean;
    ai_note?: string;
    diet_type?: string;
    prefer_pantry_leftovers?: boolean;
    prefer_offers?: boolean;
  }) =>
    request<MealPlan>("/api/meal-plans/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updatePlanServings: (planId: number, servings: number) =>
    request<MealPlan>(`/api/meal-plans/${planId}/servings?servings=${servings}`, {
      method: "PATCH",
    }),
  updateMealPlanEntry: (
    entryId: number,
    payload: {
      recipe_id?: number;
      servings?: number;
      is_cooked?: boolean;
      notes?: string;
    }
  ) =>
    request<MealPlan>(`/api/meal-plans/entries/${entryId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  getEntrySwaps: (entryId: number, mode = "balanced") =>
    request<Recipe[]>(`/api/meal-plans/entries/${entryId}/swaps?mode=${mode}`),

  // Shopping List
  getShoppingList: () => request<ShoppingList>("/api/shopping-list/active"),
  rebuildShoppingList: () =>
    request<ShoppingList>("/api/shopping-list/rebuild", { method: "POST" }),
  updateShoppingItem: (
    itemId: number,
    payload: {
      is_checked?: boolean;
      actual_price_eur?: number;
      to_buy_amount?: number;
    }
  ) =>
    request<ShoppingList>(`/api/shopping-list/items/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  addManualShoppingItem: (payload: {
    custom_name: string;
    category: string;
    to_buy_amount: number;
    unit: string;
    estimated_price_eur: number;
    assigned_store_name?: string;
  }) =>
    request<ShoppingList>("/api/shopping-list/items", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteShoppingItem: (itemId: number) =>
    request<ShoppingList>(`/api/shopping-list/items/${itemId}`, {
      method: "DELETE",
    }),
  moveCheckedToPantry: () =>
    request<{ moved_count: number; shopping_list: ShoppingList }>(
      "/api/shopping-list/move-to-pantry",
      { method: "POST" }
    ),

  // Recipes
  listRecipes: (params?: {
    q?: string;
    slot?: string;
    max_effort?: number;
    diet_type?: string;
    favorites_only?: boolean;
    min_protein?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.q) qs.set("q", params.q);
    if (params?.slot) qs.set("slot", params.slot);
    if (params?.max_effort) qs.set("max_effort", String(params.max_effort));
    if (params?.diet_type) qs.set("diet_type", params.diet_type);
    if (params?.favorites_only) qs.set("favorites_only", "true");
    if (params?.min_protein) qs.set("min_protein", String(params.min_protein));
    const query = qs.toString();
    return request<Recipe[]>(`/api/recipes${query ? `?${query}` : ""}`);
  },
  getRecipe: (id: number) => request<Recipe>(`/api/recipes/${id}`),
  toggleFavorite: (id: number) =>
    request<Recipe>(`/api/recipes/${id}/favorite`, { method: "PATCH" }),
  createRecipe: (payload: {
    title: string;
    description: string;
    servings: number;
    prep_time_min: number;
    cook_time_min: number;
    effort_level: number;
    diet_type: string;
    meal_types: SlotType[];
    tags: string[];
    instructions: string[];
    image_emoji?: string;
    ingredients: {
      ingredient_id: number;
      amount: number;
      unit: string;
      preparation_note?: string;
    }[];
  }) =>
    request<Recipe>("/api/recipes", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteRecipe: (id: number) =>
    request<void>(`/api/recipes/${id}`, { method: "DELETE" }),
  importRecipeUrl: (url: string) =>
    request<Recipe>("/api/recipes/import-url", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),

  // Ingredients
  listIngredients: (q?: string) =>
    request<Ingredient[]>(
      `/api/ingredients${q ? `?q=${encodeURIComponent(q)}` : ""}`
    ),
  updateIngredientPrice: (
    id: number,
    payload: {
      reference_price_eur: number;
      default_pack_size?: number;
      reference_store?: string;
    }
  ) =>
    request<Ingredient>(`/api/ingredients/${id}/price`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  searchOpenFoodFacts: (q: string) =>
    request<
      {
        code: string;
        name: string;
        brand: string;
        quantity: string;
        kcal_100: number;
        protein_100: number;
        carbs_100: number;
        sugar_100: number;
        fiber_100: number;
        fat_100: number;
      }[]
    >(`/api/ingredients/openfoodfacts?q=${encodeURIComponent(q)}`),

  // Pantry
  listPantry: () => request<PantryItem[]>("/api/pantry"),
  addPantryItem: (payload: {
    ingredient_id: number;
    quantity: number;
    unit?: string;
    location: string;
    expires_at?: string;
    use_priority?: string;
    notes?: string;
  }) =>
    request<PantryItem>("/api/pantry", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updatePantryItem: (
    id: number,
    payload: {
      quantity?: number;
      location?: string;
      expires_at?: string;
      use_priority?: string;
    }
  ) =>
    request<PantryItem>(`/api/pantry/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deletePantryItem: (id: number) =>
    request<void>(`/api/pantry/${id}`, { method: "DELETE" }),
  getPantrySuggestions: () =>
    request<PantrySuggestion[]>("/api/pantry/suggestions"),

  // Offers
  listOffers: (store?: string) =>
    request<Offer[]>(
      `/api/offers${store ? `?store=${encodeURIComponent(store)}` : ""}`
    ),
  syncOffers: (postal_code?: string) =>
    request<{
      id: number;
      status: string;
      offers_fetched: number;
      matches_created: number;
      error_message: string | null;
    }>("/api/offers/sync", {
      method: "POST",
      body: JSON.stringify({ postal_code }),
    }),
  reviewOfferMatch: (matchId: number, action: "confirm" | "reject") =>
    request<{ id: number; is_confirmed: boolean; is_rejected: boolean }>(
      `/api/offers/matches/${matchId}?action=${action}`,
      { method: "PATCH" }
    ),
  getSyncRuns: () =>
    request<
      {
        id: number;
        provider: string;
        postal_code: string;
        status: string;
        offers_fetched: number;
        matches_created: number;
        error_message: string | null;
        started_at: string;
      }[]
    >("/api/offers/sync-runs"),

  // AI / Local LLM
  getAiHealth: () => request<LlmHealth>("/api/ai/health"),
  generateAiRecipe: (payload: {
    prompt: string;
    effort_level: number;
    servings: number;
    meal_type: SlotType;
    use_pantry: boolean;
  }) =>
    request<Recipe>("/api/ai/generate-recipe", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getAiLogs: () =>
    request<
      {
        id: number;
        task_type: string;
        model: string;
        status: string;
        duration_ms: number;
        retries: number;
        error_message: string | null;
        created_at: string;
      }[]
    >("/api/ai/logs"),
};
