import React, { useMemo, useState } from "react";
import {
  AlertTriangle,
  Archive,
  Flame,
  Plus,
  Snowflake,
  ThermometerSnowflake,
  Trash2,
} from "lucide-react";
import { api } from "../api";
import type {
  Ingredient,
  LocationType,
  PantryItem,
  PantrySuggestion,
  Recipe,
} from "../types";
import { MacroPills } from "./MacroPills";

interface PantryViewProps {
  pantryItems: PantryItem[];
  ingredients: Ingredient[];
  suggestions: PantrySuggestion[];
  onRefresh: () => Promise<void>;
  onOpenRecipe: (recipe: Recipe) => void;
}

const LOCATION_META: Record<
  LocationType,
  { label: string; icon: React.ReactNode }
> = {
  fridge: {
    label: "Kühlschrank",
    icon: <ThermometerSnowflake className="h-4 w-4 text-sky-700" />,
  },
  pantry: {
    label: "Vorratsschrank",
    icon: <Archive className="h-4 w-4 text-amber-700" />,
  },
  freezer: {
    label: "Gefrierfach",
    icon: <Snowflake className="h-4 w-4 text-indigo-700" />,
  },
};

export const PantryView: React.FC<PantryViewProps> = ({
  pantryItems,
  ingredients,
  suggestions,
  onRefresh,
  onOpenRecipe,
}) => {
  const [selectedIngId, setSelectedIngId] = useState<number>(
    ingredients[0]?.id || 1
  );
  const [ingSearch, setIngSearch] = useState("");
  const [qty, setQty] = useState("250");
  const [location, setLocation] = useState<LocationType>("fridge");
  const [expiresAt, setExpiresAt] = useState("");
  const [priority, setPriority] = useState<"normal" | "use_soon" | "urgent">(
    "normal"
  );

  const filteredIngredients = useMemo(() => {
    if (!ingSearch.trim()) return ingredients;
    const ql = ingSearch.toLowerCase();
    return ingredients.filter(
      (i) =>
        i.name.toLowerCase().includes(ql) || i.category.toLowerCase().includes(ql)
    );
  }, [ingredients, ingSearch]);

  const selectedIng = ingredients.find((i) => i.id === selectedIngId);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedIngId) return;
    await api.addPantryItem({
      ingredient_id: selectedIngId,
      quantity: Math.max(1, Number(qty) || 100),
      unit: selectedIng?.default_unit || "g",
      location,
      expires_at: expiresAt || undefined,
      use_priority: priority,
    });
    setExpiresAt("");
    await onRefresh();
  };

  const groupedByLoc = (loc: LocationType) =>
    pantryItems.filter((i) => i.location === loc);

  return (
    <div className="space-y-6">
      {/* Add to Pantry Card */}
      <section className="rounded-3xl border border-[#E8E2D9] bg-white p-5">
        <h1 className="text-2xl font-bold tracking-tight text-[#1E2421]">
          Vorratsschrank & Resteverwertung
        </h1>
        <p className="mt-0.5 text-xs text-[#6B736E]">
          Alle Vorräte werden automatisch von deiner Einkaufsliste abgezogen und bald ablaufende Zutaten im Wochenplan bevorzugt verplant.
        </p>

        <form onSubmit={handleAdd} className="mt-4 grid gap-2.5 sm:grid-cols-2 lg:grid-cols-6">
          <div className="lg:col-span-2">
            <input
              type="text"
              value={ingSearch}
              onChange={(e) => {
                setIngSearch(e.target.value);
                const first = ingredients.find((i) =>
                  i.name.toLowerCase().includes(e.target.value.toLowerCase())
                );
                if (first) setSelectedIngId(first.id);
              }}
              placeholder="Zutat filtern…"
              className="mb-1.5 w-full rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-3 py-1.5 text-xs"
            />
            <select
              value={selectedIngId}
              onChange={(e) => setSelectedIngId(Number(e.target.value))}
              className="w-full rounded-xl border border-[#E8E2D9] bg-white px-2.5 py-2 text-xs font-semibold"
            >
              {filteredIngredients.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.name} ({i.default_unit})
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col justify-end">
            <label className="mb-1 text-[11px] font-semibold text-[#6B736E]">
              Menge ({selectedIng?.default_unit || "g"})
            </label>
            <input
              type="number"
              step="1"
              value={qty}
              onChange={(e) => setQty(e.target.value)}
              className="rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-3 py-2 text-xs font-bold tabular-nums"
            />
          </div>

          <div className="flex flex-col justify-end">
            <label className="mb-1 text-[11px] font-semibold text-[#6B736E]">
              Lagerort
            </label>
            <select
              value={location}
              onChange={(e) => setLocation(e.target.value as LocationType)}
              className="rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-2.5 py-2 text-xs font-semibold"
            >
              <option value="fridge">Kühlschrank</option>
              <option value="pantry">Vorratsschrank</option>
              <option value="freezer">Gefrierfach</option>
            </select>
          </div>

          <div className="flex flex-col justify-end">
            <label className="mb-1 text-[11px] font-semibold text-[#6B736E]">
              MHD / Priorität
            </label>
            <div className="flex gap-1">
              <input
                type="date"
                value={expiresAt}
                onChange={(e) => setExpiresAt(e.target.value)}
                className="w-full rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-2 py-2 text-xs"
              />
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as any)}
                className="rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-1.5 py-2 text-[11px] font-semibold"
              >
                <option value="normal">Normal</option>
                <option value="use_soon">Bald</option>
                <option value="urgent">Sofort!</option>
              </select>
            </div>
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              className="inline-flex w-full items-center justify-center gap-1.5 rounded-xl bg-[#2D5A45] px-4 py-2 text-xs font-semibold text-white hover:bg-[#234836]"
            >
              <Plus className="h-4 w-4" />
              Einlagern
            </button>
          </div>
        </form>
      </section>

      {/* Pantry Locations */}
      <div className="grid gap-4 lg:grid-cols-3">
        {(["fridge", "pantry", "freezer"] as LocationType[]).map((loc) => {
          const items = groupedByLoc(loc);
          return (
            <section
              key={loc}
              className="overflow-hidden rounded-3xl border border-[#E8E2D9] bg-white"
            >
              <div className="flex items-center justify-between border-b border-[#EFEAE2] bg-[#FAF8F5] px-4 py-3">
                <div className="flex items-center gap-2 text-sm font-bold text-[#1E2421]">
                  {LOCATION_META[loc].icon}
                  {LOCATION_META[loc].label}
                </div>
                <span className="text-xs font-semibold text-[#7B847E]">
                  {items.length}
                </span>
              </div>

              <div className="divide-y divide-[#F2EDE5]">
                {items.length === 0 ? (
                  <p className="p-5 text-center text-xs text-[#9AA29D]">
                    Noch nichts eingetragen.
                  </p>
                ) : (
                  items.map((item) => {
                    const expiringSoon =
                      item.days_until_expiry !== null &&
                      item.days_until_expiry <= 4;
                    return (
                      <div
                        key={item.id}
                        className="flex items-center justify-between gap-2 px-4 py-3"
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5">
                            <span className="truncate text-sm font-semibold text-[#1E2421]">
                              {item.ingredient_name}
                            </span>
                            {(expiringSoon || item.use_priority === "urgent") && (
                              <span className="inline-flex items-center gap-0.5 rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-bold text-rose-700">
                                <AlertTriangle className="h-3 w-3" />
                                {item.days_until_expiry !== null
                                  ? item.days_until_expiry <= 0
                                    ? "Abgelaufen!"
                                    : `${item.days_until_expiry}T`
                                  : "Verbrauchen"}
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] tabular-nums text-[#6B736E]">
                            <strong>
                              {item.quantity} {item.unit}
                            </strong>
                            {item.expires_at ? ` · MHD ${item.expires_at}` : ""}
                          </div>
                        </div>

                        <div className="flex items-center gap-1">
                          <button
                            onClick={async () => {
                              await api.updatePantryItem(item.id, {
                                use_priority:
                                  item.use_priority === "urgent"
                                    ? "normal"
                                    : "urgent",
                              });
                              await onRefresh();
                            }}
                            className={`rounded-lg px-2 py-1 text-[10px] font-semibold ${
                              item.use_priority === "urgent"
                                ? "bg-rose-100 text-rose-700"
                                : "bg-[#F2EDE5] text-[#6B736E] hover:bg-amber-100"
                            }`}
                            title="Als ‚bald verbrauchen‘ markieren"
                          >
                            Prio
                          </button>
                          <button
                            onClick={async () => {
                              await api.deletePantryItem(item.id);
                              await onRefresh();
                            }}
                            className="rounded-lg p-1.5 text-[#9AA29D] hover:bg-rose-50 hover:text-rose-600"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </section>
          );
        })}
      </div>

      {/* Leftover Recipe Suggestions */}
      {suggestions.length > 0 && (
        <section className="rounded-3xl border border-[#E8E2D9] bg-white p-5">
          <div className="flex items-center gap-2">
            <Flame className="h-4 w-4 text-[#C86442]" />
            <h2 className="text-base font-bold text-[#1E2421]">
              Was kann ich jetzt aus meinen Vorräten kochen?
            </h2>
          </div>
          <div className="mt-3.5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {suggestions.map((s) => (
              <button
                key={s.recipe.id}
                onClick={() => onOpenRecipe(s.recipe)}
                className="flex flex-col justify-between rounded-2xl border border-[#E8E2D9] bg-[#FCFBF9] p-4 text-left transition hover:border-[#2D5A45]"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xl">{s.recipe.image_emoji}</span>
                    <span className="rounded-full bg-[#EBF3EE] px-2 py-0.5 text-[10px] font-bold text-[#2D5A45]">
                      {s.coverage_pct}% vorrätig
                    </span>
                  </div>
                  <div className="mt-2 text-sm font-bold text-[#1E2421]">
                    {s.recipe.title}
                  </div>
                  <p className="mt-1 text-[11px] text-[#6B736E]">
                    Nutzt: {s.matched_ingredients.slice(0, 3).join(", ")}
                    {s.missing_count > 0 ? ` · +${s.missing_count} fehlen` : " · komplett da!"}
                  </p>
                </div>
                <div className="mt-3">
                  <MacroPills
                    kcal={s.recipe.kcal_per_serving}
                    protein={s.recipe.protein_g}
                    carbs={s.recipe.carbs_g}
                    compact
                  />
                </div>
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  );
};
