import React, { useCallback, useEffect, useState } from "react";
import {
  Archive,
  BookOpen,
  CalendarDays,
  Settings,
  ShoppingBasket,
  Tag,
} from "lucide-react";
import { api } from "./api";
import { PantryView } from "./components/PantryView";
import { PricesOffersView } from "./components/PricesOffersView";
import { RecipeDetailDrawer } from "./components/RecipeDetailDrawer";
import { RecipesView } from "./components/RecipesView";
import { SettingsView } from "./components/SettingsView";
import { ShoppingListView } from "./components/ShoppingListView";
import { SwapDrawer } from "./components/SwapDrawer";
import { WeekPlanView } from "./components/WeekPlanView";
import type {
  AppSettings,
  Ingredient,
  LlmHealth,
  MealPlan,
  MealPlanEntry,
  Offer,
  PantryItem,
  PantrySuggestion,
  Recipe,
  ShoppingList,
  SlotType,
} from "./types";

type TabId = "week" | "shopping" | "recipes" | "pantry" | "prices" | "settings";

export default function App() {
  const [tab, setTab] = useState<TabId>("week");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [plan, setPlan] = useState<MealPlan | null>(null);
  const [shoppingList, setShoppingList] = useState<ShoppingList | null>(null);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [pantry, setPantry] = useState<PantryItem[]>([]);
  const [pantrySuggestions, setPantrySuggestions] = useState<PantrySuggestion[]>(
    []
  );
  const [offers, setOffers] = useState<Offer[]>([]);
  const [llmHealth, setLlmHealth] = useState<LlmHealth | null>(null);

  // Drawers
  const [activeRecipe, setActiveRecipe] = useState<{
    recipe: Recipe;
    servings?: number;
  } | null>(null);
  const [swapEntry, setSwapEntry] = useState<MealPlanEntry | null>(null);

  const loadAll = useCallback(async () => {
    try {
      const [s, p, sl, r, ing, pan, sug, off] = await Promise.all([
        api.getSettings(),
        api.getActiveMealPlan(),
        api.getShoppingList(),
        api.listRecipes(),
        api.listIngredients(),
        api.listPantry(),
        api.getPantrySuggestions(),
        api.listOffers(),
      ]);
      setSettings(s);
      setPlan(p);
      setShoppingList(sl);
      setRecipes(r);
      setIngredients(ing);
      setPantry(pan);
      setPantrySuggestions(sug);
      setOffers(off);
      setError(null);
    } catch (err: any) {
      setError(err?.message || "Verbindung zum lokalen Backend fehlgeschlagen.");
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshAiHealth = useCallback(async () => {
    try {
      const h = await api.getAiHealth();
      setLlmHealth(h);
    } catch {
      setLlmHealth(null);
    }
  }, []);

  useEffect(() => {
    loadAll();
    refreshAiHealth();
  }, [loadAll, refreshAiHealth]);

  const refreshPlanAndShopping = async () => {
    const [p, sl, pan, sug] = await Promise.all([
      api.getActiveMealPlan(),
      api.getShoppingList(),
      api.listPantry(),
      api.getPantrySuggestions(),
    ]);
    setPlan(p);
    setShoppingList(sl);
    setPantry(pan);
    setPantrySuggestions(sug);
  };

  const handleGenerate = async (params: {
    days_count: number;
    servings_per_meal: number;
    max_effort_level: number;
    target_budget_eur: number;
    active_slots: SlotType[];
    batch_cooking: boolean;
    use_ai: boolean;
    ai_note?: string;
  }) => {
    setGenerating(true);
    try {
      const nextPlan = await api.generateMealPlan(params);
      setPlan(nextPlan);
      const sl = await api.getShoppingList();
      setShoppingList(sl);
    } finally {
      setGenerating(false);
    }
  };

  const handleScaleWeekServings = async (newServings: number) => {
    if (!plan) return;
    const updated = await api.updatePlanServings(plan.id, newServings);
    setPlan(updated);
    const sl = await api.getShoppingList();
    setShoppingList(sl);
  };

  const handleUpdateEntry = async (
    entryId: number,
    payload: { recipe_id?: number; servings?: number; is_cooked?: boolean }
  ) => {
    const updated = await api.updateMealPlanEntry(entryId, payload);
    setPlan(updated);
    const [sl, pan, sug] = await Promise.all([
      api.getShoppingList(),
      api.listPantry(),
      api.getPantrySuggestions(),
    ]);
    setShoppingList(sl);
    setPantry(pan);
    setPantrySuggestions(sug);
  };

  const handleToggleFavorite = async (recipeId: number) => {
    const updated = await api.toggleFavorite(recipeId);
    setRecipes((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
    if (activeRecipe?.recipe.id === updated.id) {
      setActiveRecipe({ ...activeRecipe, recipe: updated });
    }
  };

  const navItems: { id: TabId; label: string; icon: React.ReactNode; badge?: string }[] = [
    { id: "week", label: "Wochenplan", icon: <CalendarDays className="h-4 w-4" /> },
    {
      id: "shopping",
      label: "Einkaufsliste",
      icon: <ShoppingBasket className="h-4 w-4" />,
      badge: shoppingList
        ? `${shoppingList.total_items_count - shoppingList.checked_count}`
        : undefined,
    },
    {
      id: "recipes",
      label: "Rezepte",
      icon: <BookOpen className="h-4 w-4" />,
      badge: recipes.length ? `${recipes.length}` : undefined,
    },
    {
      id: "pantry",
      label: "Vorrat",
      icon: <Archive className="h-4 w-4" />,
      badge: pantry.length ? `${pantry.length}` : undefined,
    },
    { id: "prices", label: "ALDI & Angebote", icon: <Tag className="h-4 w-4" /> },
    { id: "settings", label: "Einstellungen", icon: <Settings className="h-4 w-4" /> },
  ];

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#FAF8F5] text-sm font-medium text-[#5A635E]">
        Lade Miseclon…
      </div>
    );
  }

  if (error || !settings || !plan || !shoppingList) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-[#FAF8F5] p-6 text-center">
        <p className="text-base font-bold text-[#1E2421]">
          Backend derzeit nicht erreichbar
        </p>
        <p className="max-w-md text-xs text-[#6B736E]">{error}</p>
        <button
          onClick={loadAll}
          className="rounded-xl bg-[#2D5A45] px-4 py-2 text-xs font-semibold text-white"
        >
          Erneut verbinden
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAF8F5] pb-20 md:pb-10">
      {/* Top Mise Navigation Bar */}
      <header className="sticky top-0 z-30 border-b border-[#E8E2D9] bg-[#FAF8F5]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <button
            onClick={() => setTab("week")}
            className="flex items-center gap-2.5 text-left"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-[#2D5A45] text-base font-bold text-white shadow-xs">
              m
            </div>
            <div>
              <div className="text-base font-extrabold tracking-tight text-[#1E2421]">
                mise<span className="text-[#2D5A45]">clon</span>
              </div>
              <div className="text-[10px] font-medium text-[#7B847E]">
                Lokal · Protein & Komplexe KH · ALDI
              </div>
            </div>
          </button>

          {/* Desktop Navigation */}
          <nav className="hidden items-center gap-1 rounded-2xl border border-[#E8E2D9] bg-white p-1 md:flex">
            {navItems.map((item) => {
              const active = tab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setTab(item.id)}
                  className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-semibold transition ${
                    active
                      ? "bg-[#2D5A45] text-white shadow-xs"
                      : "text-[#5A635E] hover:bg-[#FAF8F5] hover:text-[#1E2421]"
                  }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                  {item.badge && (
                    <span
                      className={`rounded-full px-1.5 py-0.2 text-[10px] font-bold tabular-nums ${
                        active
                          ? "bg-white/20 text-white"
                          : "bg-[#F0EAE0] text-[#4E5752]"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Local LLM Status Pill */}
          <button
            onClick={() => setTab("settings")}
            className="hidden items-center gap-1.5 rounded-full border border-[#E8E2D9] bg-white px-3 py-1.5 text-[11px] font-semibold text-[#4E5752] hover:border-[#2D5A45]/40 lg:inline-flex"
            title="Lokaler KI-Server Status"
          >
            <span
              className={`h-2 w-2 rounded-full ${
                llmHealth?.connected ? "bg-emerald-500" : "bg-amber-400"
              }`}
            />
            {llmHealth?.connected
              ? `KI: ${llmHealth.configured_model}`
              : "KI Offline (Lokal aktiv)"}
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        {tab === "week" && (
          <WeekPlanView
            plan={plan}
            settings={settings}
            llmHealth={llmHealth}
            generating={generating}
            onGenerate={handleGenerate}
            onScaleWeekServings={handleScaleWeekServings}
            onUpdateEntry={handleUpdateEntry}
            onOpenRecipe={(recipe, servings) =>
              setActiveRecipe({ recipe, servings })
            }
            onOpenSwap={(entry) => setSwapEntry(entry)}
            onGoToShopping={() => setTab("shopping")}
          />
        )}

        {tab === "shopping" && (
          <ShoppingListView
            shoppingList={shoppingList}
            targetBudget={plan.target_budget_eur}
            onUpdateItem={async (itemId, payload) => {
              const updated = await api.updateShoppingItem(itemId, payload);
              setShoppingList(updated);
            }}
            onAddManual={async (payload) => {
              const updated = await api.addManualShoppingItem(payload);
              setShoppingList(updated);
            }}
            onDeleteItem={async (itemId) => {
              const updated = await api.deleteShoppingItem(itemId);
              setShoppingList(updated);
            }}
            onMoveToPantry={async () => {
              const res = await api.moveCheckedToPantry();
              setShoppingList(res.shopping_list);
              const [pan, sug] = await Promise.all([
                api.listPantry(),
                api.getPantrySuggestions(),
              ]);
              setPantry(pan);
              setPantrySuggestions(sug);
              return res.moved_count;
            }}
            onRebuild={async () => {
              const updated = await api.rebuildShoppingList();
              setShoppingList(updated);
            }}
            onOpenRecipeById={async (recipeId) => {
              const found = recipes.find((r) => r.id === recipeId);
              if (found) {
                setActiveRecipe({ recipe: found, servings: plan.servings_per_meal });
              } else {
                const fetched = await api.getRecipe(recipeId);
                setActiveRecipe({ recipe: fetched, servings: plan.servings_per_meal });
              }
            }}
          />
        )}

        {tab === "recipes" && (
          <RecipesView
            recipes={recipes}
            ingredients={ingredients}
            llmHealth={llmHealth}
            onOpenRecipe={(recipe) =>
              setActiveRecipe({ recipe, servings: plan.servings_per_meal })
            }
            onToggleFavorite={handleToggleFavorite}
            onRecipesChanged={async () => {
              const r = await api.listRecipes();
              setRecipes(r);
            }}
          />
        )}

        {tab === "pantry" && (
          <PantryView
            pantryItems={pantry}
            ingredients={ingredients}
            suggestions={pantrySuggestions}
            onRefresh={refreshPlanAndShopping}
            onOpenRecipe={(recipe) =>
              setActiveRecipe({ recipe, servings: plan.servings_per_meal })
            }
          />
        )}

        {tab === "prices" && (
          <PricesOffersView
            settings={settings}
            ingredients={ingredients}
            offers={offers}
            onRefreshAll={loadAll}
          />
        )}

        {tab === "settings" && (
          <SettingsView
            settings={settings}
            llmHealth={llmHealth}
            onSaved={(updated) => {
              setSettings(updated);
              refreshPlanAndShopping();
            }}
            onRefreshAiHealth={refreshAiHealth}
          />
        )}
      </main>

      {/* Mobile Bottom Navigation (great for Supermarket PWA!) */}
      <nav className="fixed right-0 bottom-0 left-0 z-30 flex items-center justify-around border-t border-[#E8E2D9] bg-white px-2 py-2 md:hidden">
        {navItems.slice(0, 5).map((item) => {
          const active = tab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setTab(item.id)}
              className={`flex flex-col items-center gap-0.5 rounded-xl px-2.5 py-1 text-[10px] font-semibold ${
                active ? "text-[#2D5A45]" : "text-[#7B847E]"
              }`}
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Slide-over Drawers */}
      <RecipeDetailDrawer
        recipe={activeRecipe?.recipe || null}
        initialServings={activeRecipe?.servings}
        onClose={() => setActiveRecipe(null)}
        onToggleFavorite={handleToggleFavorite}
      />

      <SwapDrawer
        entry={swapEntry}
        onClose={() => setSwapEntry(null)}
        onSelectRecipe={async (entryId, recipeId) => {
          await handleUpdateEntry(entryId, { recipe_id: recipeId });
        }}
      />
    </div>
  );
}
