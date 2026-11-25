import React, { useMemo, useState } from "react";
import {
  ChefHat,
  Clock,
  Heart,
  Link2,
  Plus,
  Search,
  Sparkles,
  Wind,
  X,
} from "lucide-react";
import { api } from "../api";
import {
  EFFORT_META,
  SLOT_LABELS,
  type Ingredient,
  type LlmHealth,
  type Recipe,
  type SlotType,
} from "../types";
import { MacroPills } from "./MacroPills";

interface RecipesViewProps {
  recipes: Recipe[];
  ingredients: Ingredient[];
  llmHealth: LlmHealth | null;
  onOpenRecipe: (recipe: Recipe) => void;
  onToggleFavorite: (recipeId: number) => Promise<void>;
  onRecipesChanged: () => Promise<void>;
}

export const RecipesView: React.FC<RecipesViewProps> = ({
  recipes,
  ingredients,
  llmHealth,
  onOpenRecipe,
  onToggleFavorite,
  onRecipesChanged,
}) => {
  const [query, setQuery] = useState("");
  const [slotFilter, setSlotFilter] = useState<string>("");
  const [maxEffort, setMaxEffort] = useState<number>(3);
  const [dietFilter, setDietFilter] = useState<string>("");
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  const [airfryerOnly, setAirfryerOnly] = useState(false);

  // Modals
  const [modal, setModal] = useState<"none" | "url" | "ai" | "manual">("none");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // URL Import State
  const [importUrl, setImportUrl] = useState("");

  // AI Generator State
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiEffort, setAiEffort] = useState<number>(1);
  const [aiServings, setAiServings] = useState<number>(2);
  const [aiSlot, setAiSlot] = useState<SlotType>("dinner");

  // Manual Recipe State
  const [mTitle, setMTitle] = useState("");
  const [mDesc, setMDesc] = useState("");
  const [mServings, setMServings] = useState(2);
  const [mPrep, setMPrep] = useState(10);
  const [mCook, setMCook] = useState(15);
  const [mEffort, setMEffort] = useState(1);
  const [mSlot, setMSlot] = useState<SlotType>("dinner");
  const [mSteps, setMSteps] = useState(
    "Zutaten vorbereiten.\nIn einer Pfanne gar kochen und abschmecken."
  );
  const [mIngs, setMIngs] = useState<
    { ingredient_id: number; amount: number; unit: string }[]
  >([
    {
      ingredient_id: ingredients[0]?.id || 1,
      amount: 250,
      unit: ingredients[0]?.default_unit || "g",
    },
  ]);

  const filtered = useMemo(() => {
    return recipes.filter((r) => {
      if (r.effort_level > maxEffort) return false;
      if (favoritesOnly && !r.is_favorite) return false;
      if (airfryerOnly && !r.tags.includes("airfryer")) return false;
      if (slotFilter && !r.meal_types.includes(slotFilter)) return false;
      if (dietFilter === "vegan" && r.diet_type !== "vegan") return false;
      if (
        dietFilter === "vegetarian" &&
        !["vegetarian", "vegan"].includes(r.diet_type)
      )
        return false;
      if (query.trim()) {
        const ql = query.toLowerCase();
        const text = `${r.title} ${r.description} ${r.tags.join(" ")} ${r.ingredients
          .map((i) => i.ingredient_name)
          .join(" ")}`.toLowerCase();
        if (!text.includes(ql)) return false;
      }
      return true;
    });
  }, [recipes, query, slotFilter, maxEffort, dietFilter, favoritesOnly, airfryerOnly]);

  const handleImportUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await api.importRecipeUrl(importUrl.trim());
      await onRecipesChanged();
      setImportUrl("");
      setModal("none");
      onOpenRecipe(created);
    } catch (err: any) {
      setError(err?.message || "Import fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  };

  const handleGenerateAi = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await api.generateAiRecipe({
        prompt: aiPrompt.trim(),
        effort_level: aiEffort,
        servings: aiServings,
        meal_type: aiSlot,
        use_pantry: true,
      });
      await onRecipesChanged();
      setAiPrompt("");
      setModal("none");
      onOpenRecipe(created);
    } catch (err: any) {
      setError(err?.message || "KI-Erstellung fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  };

  const handleCreateManual = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const steps = mSteps
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean);
      const created = await api.createRecipe({
        title: mTitle.trim(),
        description: mDesc.trim(),
        servings: mServings,
        prep_time_min: mPrep,
        cook_time_min: mCook,
        effort_level: mEffort,
        diet_type: "omnivore",
        meal_types: [mSlot],
        tags: ["eigenes-rezept"],
        instructions: steps.length ? steps : ["Nach Wunsch zubereiten."],
        ingredients: mIngs.map((x) => ({
          ingredient_id: x.ingredient_id,
          amount: x.amount,
          unit: x.unit,
        })),
      });
      await onRecipesChanged();
      setMTitle("");
      setMDesc("");
      setModal("none");
      onOpenRecipe(created);
    } catch (err: any) {
      setError(err?.message || "Speichern fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Header & Action Buttons */}
      <section className="rounded-3xl border border-[#E8E2D9] bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-[#1E2421]">
              Rezeptbibliothek
            </h1>
            <p className="text-xs text-[#6B736E]">
              {recipes.length} Rezepte mit exakten Makros, Zubereitung & ALDI-Preisen
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => {
                setError(null);
                setModal("url");
              }}
              className="inline-flex items-center gap-1.5 rounded-2xl border border-[#E8E2D9] bg-white px-3.5 py-2 text-xs font-semibold text-[#1E2421] hover:bg-[#FAF8F5]"
            >
              <Link2 className="h-3.5 w-3.5 text-[#2D5A45]" />
              Per URL importieren (z. B. Chefkoch)
            </button>
            <button
              onClick={() => {
                setError(null);
                setModal("ai");
              }}
              className="inline-flex items-center gap-1.5 rounded-2xl border border-[#C86442]/40 bg-[#FDF2EE] px-3.5 py-2 text-xs font-semibold text-[#A34728] hover:bg-[#FAE4DC]"
            >
              <Sparkles className="h-3.5 w-3.5" />
              Mit lokaler KI erfinden
            </button>
            <button
              onClick={() => {
                setError(null);
                setModal("manual");
              }}
              className="inline-flex items-center gap-1.5 rounded-2xl bg-[#2D5A45] px-3.5 py-2 text-xs font-semibold text-white hover:bg-[#234836]"
            >
              <Plus className="h-3.5 w-3.5" />
              Eigenes Rezept
            </button>
          </div>
        </div>

        {/* Search & Filters */}
        <div className="mt-4 flex flex-wrap items-center gap-2.5">
          <div className="relative min-w-[220px] flex-1">
            <Search className="pointer-events-none absolute top-2.5 left-3 h-4 w-4 text-[#9AA29D]" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Nach Gericht oder Zutat suchen (z. B. Skyr, Linsen, Hähnchen)…"
              className="w-full rounded-2xl border border-[#E8E2D9] bg-[#FAF8F5] py-2 pr-3 pl-9 text-xs focus:border-[#2D5A45] focus:bg-white focus:outline-none"
            />
          </div>

          <select
            value={slotFilter}
            onChange={(e) => setSlotFilter(e.target.value)}
            className="rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-3 py-2 text-xs font-semibold"
          >
            <option value="">Alle Mahlzeiten</option>
            {(Object.keys(SLOT_LABELS) as SlotType[]).map((s) => (
              <option key={s} value={s}>
                {SLOT_LABELS[s]}
              </option>
            ))}
          </select>

          <select
            value={maxEffort}
            onChange={(e) => setMaxEffort(Number(e.target.value))}
            className="rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-3 py-2 text-xs font-semibold"
          >
            <option value={1}>Nur Stufe 1 (Ultra-Simpel)</option>
            <option value={2}>Bis Stufe 2 (Alltag)</option>
            <option value={3}>Alle Stufen (1–3)</option>
          </select>

          <select
            value={dietFilter}
            onChange={(e) => setDietFilter(e.target.value)}
            className="rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-3 py-2 text-xs font-semibold"
          >
            <option value="">Alle Ernährungsformen</option>
            <option value="vegetarian">Vegetarisch</option>
            <option value="vegan">Vegan</option>
          </select>

          <button
            onClick={() => setAirfryerOnly((v) => !v)}
            className={`inline-flex items-center gap-1.5 rounded-xl border px-3 py-2 text-xs font-semibold transition ${
              airfryerOnly
                ? "border-amber-300 bg-amber-50 text-amber-900"
                : "border-[#E8E2D9] bg-white text-[#5A635E]"
            }`}
          >
            <Wind className="h-3.5 w-3.5" />
            Airfryer
          </button>

          <button
            onClick={() => setFavoritesOnly((v) => !v)}
            className={`inline-flex items-center gap-1.5 rounded-xl border px-3 py-2 text-xs font-semibold transition ${
              favoritesOnly
                ? "border-rose-200 bg-rose-50 text-rose-700"
                : "border-[#E8E2D9] bg-white text-[#5A635E]"
            }`}
          >
            <Heart className="h-3.5 w-3.5" fill={favoritesOnly ? "currentColor" : "none"} />
            Favoriten
          </button>
        </div>
      </section>

      {/* Recipe Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((r) => {
          const eff = EFFORT_META[r.effort_level] || EFFORT_META[2];
          return (
            <article
              key={r.id}
              className="group flex flex-col justify-between rounded-3xl border border-[#E8E2D9] bg-white p-5 transition hover:border-[#2D5A45]/40 hover:shadow-md"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span
                      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${eff.badgeClass}`}
                    >
                      <ChefHat className="h-3 w-3" />
                      {eff.short}
                    </span>
                    {r.tags.includes("airfryer") && (
                      <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-800">
                        <Wind className="h-3 w-3" />
                        Airfryer
                      </span>
                    )}
                    <span className="inline-flex items-center gap-1 text-[11px] text-[#6B736E]">
                      <Clock className="h-3 w-3" />
                      {r.total_time_min} Min
                    </span>
                  </div>
                  <button
                    onClick={() => onToggleFavorite(r.id)}
                    className={`rounded-lg p-1 ${
                      r.is_favorite ? "text-rose-500" : "text-[#CFC6B9] hover:text-rose-400"
                    }`}
                  >
                    <Heart
                      className="h-4 w-4"
                      fill={r.is_favorite ? "currentColor" : "none"}
                    />
                  </button>
                </div>

                <button
                  type="button"
                  onClick={() => onOpenRecipe(r)}
                  className="mt-2.5 flex w-full items-start gap-3 text-left"
                >
                  <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-[#F4EFE7] text-2xl">
                    {r.image_emoji}
                  </span>
                  <div>
                    <h3 className="text-sm font-bold leading-snug text-[#1E2421] group-hover:text-[#2D5A45]">
                      {r.title}
                    </h3>
                    <p className="mt-1 line-clamp-2 text-xs text-[#6B736E]">
                      {r.description}
                    </p>
                  </div>
                </button>
              </div>

              <div className="mt-4 space-y-2.5 border-t border-[#F2EDE5] pt-3">
                <MacroPills
                  kcal={r.kcal_per_serving}
                  protein={r.protein_g}
                  carbs={r.carbs_g}
                  complexRatio={r.complex_carb_ratio}
                  compact
                />
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold tabular-nums text-[#2D5A45]">
                    ~{r.estimated_cost_per_serving.toFixed(2)} € / Portion
                  </span>
                  <button
                    onClick={() => onOpenRecipe(r)}
                    className="font-semibold text-[#1E2421] hover:text-[#2D5A45]"
                  >
                    Zubereitung →
                  </button>
                </div>
              </div>
            </article>
          );
        })}
      </div>

      {/* URL Import Modal */}
      {modal === "url" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-[#1E2421]">
                Rezept per URL importieren
              </h3>
              <button onClick={() => setModal("none")} className="p-1 text-[#6B736E]">
                <X className="h-5 w-5" />
              </button>
            </div>
            <p className="mt-1 text-xs text-[#6B736E]">
              Füge einen Rezept-Link ein (z. B. Chefkoch, EatSmarter, REWE, Kitchen Stories). Zutaten, Schritte, Makros & ALDI-Preise werden automatisch berechnet.
            </p>
            <form onSubmit={handleImportUrl} className="mt-4 space-y-3">
              <input
                type="url"
                required
                value={importUrl}
                onChange={(e) => setImportUrl(e.target.value)}
                placeholder="https://www.chefkoch.de/rezepte/..."
                className="w-full rounded-2xl border border-[#E8E2D9] bg-[#FAF8F5] px-4 py-2.5 text-sm focus:border-[#2D5A45] focus:bg-white focus:outline-none"
              />
              {error && (
                <p className="rounded-xl bg-rose-50 px-3 py-2 text-xs text-rose-700">
                  {error}
                </p>
              )}
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setModal("none")}
                  className="rounded-xl border border-[#E8E2D9] px-4 py-2 text-xs font-semibold"
                >
                  Abbrechen
                </button>
                <button
                  disabled={busy}
                  type="submit"
                  className="rounded-xl bg-[#2D5A45] px-4 py-2 text-xs font-semibold text-white hover:bg-[#234836] disabled:opacity-50"
                >
                  {busy ? "Importiere…" : "Jetzt importieren"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* AI Recipe Generator Modal */}
      {modal === "ai" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-[#1E2421]">
                Rezept mit lokaler KI erstellen
              </h3>
              <button onClick={() => setModal("none")} className="p-1 text-[#6B736E]">
                <X className="h-5 w-5" />
              </button>
            </div>
            <p className="mt-1 text-xs text-[#6B736E]">
              Server: <strong>{llmHealth?.configured_model || "Ollama"}</strong>{" "}
              ({llmHealth?.connected ? "verbunden ✓" : "aktuell offline – starte Ollama"})
            </p>
            <form onSubmit={handleGenerateAi} className="mt-4 space-y-3">
              <textarea
                required
                rows={3}
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                placeholder="z. B. ‚Schnelle High-Protein-Pfanne mit Hähnchen, Süßkartoffel und Spinat, max. 15 Min, ALDI-Zutaten‘"
                className="w-full rounded-2xl border border-[#E8E2D9] bg-[#FAF8F5] p-3 text-sm focus:border-[#2D5A45] focus:bg-white focus:outline-none"
              />
              <div className="grid grid-cols-3 gap-2">
                <select
                  value={aiSlot}
                  onChange={(e) => setAiSlot(e.target.value as SlotType)}
                  className="rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-2.5 py-2 text-xs font-semibold"
                >
                  {(Object.keys(SLOT_LABELS) as SlotType[]).map((s) => (
                    <option key={s} value={s}>
                      {SLOT_LABELS[s]}
                    </option>
                  ))}
                </select>
                <select
                  value={aiEffort}
                  onChange={(e) => setAiEffort(Number(e.target.value))}
                  className="rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-2.5 py-2 text-xs font-semibold"
                >
                  <option value={1}>1 · Ultra-Simpel</option>
                  <option value={2}>2 · Alltag</option>
                  <option value={3}>3 · Ambitioniert</option>
                </select>
                <select
                  value={aiServings}
                  onChange={(e) => setAiServings(Number(e.target.value))}
                  className="rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-2.5 py-2 text-xs font-semibold"
                >
                  {[1, 2, 3, 4].map((n) => (
                    <option key={n} value={n}>
                      {n} Portionen
                    </option>
                  ))}
                </select>
              </div>
              {error && (
                <p className="rounded-xl bg-rose-50 px-3 py-2 text-xs text-rose-700">
                  {error}
                </p>
              )}
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setModal("none")}
                  className="rounded-xl border border-[#E8E2D9] px-4 py-2 text-xs font-semibold"
                >
                  Abbrechen
                </button>
                <button
                  disabled={busy}
                  type="submit"
                  className="inline-flex items-center gap-1.5 rounded-xl bg-[#C86442] px-4 py-2 text-xs font-semibold text-white hover:bg-[#AE5233] disabled:opacity-50"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  {busy ? "Generiere mit KI…" : "Rezept generieren"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Manual Recipe Modal */}
      {modal === "manual" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-[#1E2421]">
                Eigenes Rezept anlegen
              </h3>
              <button onClick={() => setModal("none")} className="p-1 text-[#6B736E]">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleCreateManual} className="mt-4 space-y-3.5">
              <input
                required
                value={mTitle}
                onChange={(e) => setMTitle(e.target.value)}
                placeholder="Rezept-Titel"
                className="w-full rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-3 py-2 text-sm font-semibold"
              />
              <input
                value={mDesc}
                onChange={(e) => setMDesc(e.target.value)}
                placeholder="Kurzbeschreibung"
                className="w-full rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-3 py-2 text-xs"
              />
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
                <select
                  value={mSlot}
                  onChange={(e) => setMSlot(e.target.value as SlotType)}
                  className="rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-2 py-2 text-xs font-semibold"
                >
                  {(Object.keys(SLOT_LABELS) as SlotType[]).map((s) => (
                    <option key={s} value={s}>
                      {SLOT_LABELS[s]}
                    </option>
                  ))}
                </select>
                <select
                  value={mEffort}
                  onChange={(e) => setMEffort(Number(e.target.value))}
                  className="rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-2 py-2 text-xs font-semibold"
                >
                  <option value={1}>Stufe 1 Simpel</option>
                  <option value={2}>Stufe 2 Alltag</option>
                  <option value={3}>Stufe 3 Genuss</option>
                </select>
                <input
                  type="number"
                  min={1}
                  max={8}
                  value={mServings}
                  onChange={(e) => setMServings(Number(e.target.value))}
                  className="rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-2 py-2 text-xs"
                  title="Portionen"
                />
                <input
                  type="number"
                  min={0}
                  value={mPrep}
                  onChange={(e) => setMPrep(Number(e.target.value))}
                  className="rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-2 py-2 text-xs"
                  title="Prep-Zeit (Min)"
                />
                <input
                  type="number"
                  min={0}
                  value={mCook}
                  onChange={(e) => setMCook(Number(e.target.value))}
                  className="rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-2 py-2 text-xs"
                  title="Kochzeit (Min)"
                />
              </div>

              {/* Ingredients Rows */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-[#4E5752]">
                    Zutaten (Makros & Kosten werden automatisch berechnet)
                  </span>
                  <button
                    type="button"
                    onClick={() =>
                      setMIngs((prev) => [
                        ...prev,
                        {
                          ingredient_id: ingredients[0]?.id || 1,
                          amount: 100,
                          unit: ingredients[0]?.default_unit || "g",
                        },
                      ])
                    }
                    className="text-xs font-semibold text-[#2D5A45] hover:underline"
                  >
                    + Zutat
                  </button>
                </div>
                {mIngs.map((row, idx) => (
                  <div key={idx} className="flex gap-2">
                    <select
                      value={row.ingredient_id}
                      onChange={(e) => {
                        const ingId = Number(e.target.value);
                        const found = ingredients.find((i) => i.id === ingId);
                        setMIngs((prev) =>
                          prev.map((x, i) =>
                            i === idx
                              ? {
                                  ...x,
                                  ingredient_id: ingId,
                                  unit: found?.default_unit || "g",
                                }
                              : x
                          )
                        );
                      }}
                      className="flex-1 rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-2.5 py-2 text-xs"
                    >
                      {ingredients.map((ing) => (
                        <option key={ing.id} value={ing.id}>
                          {ing.name} ({ing.default_unit})
                        </option>
                      ))}
                    </select>
                    <input
                      type="number"
                      step="1"
                      value={row.amount}
                      onChange={(e) =>
                        setMIngs((prev) =>
                          prev.map((x, i) =>
                            i === idx ? { ...x, amount: Number(e.target.value) } : x
                          )
                        )
                      }
                      className="w-20 rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-2 py-2 text-xs tabular-nums"
                    />
                    <span className="flex w-10 items-center justify-center text-xs text-[#6B736E]">
                      {row.unit}
                    </span>
                  </div>
                ))}
              </div>

              <div>
                <label className="text-xs font-bold text-[#4E5752]">
                  Zubereitung (ein Schritt pro Zeile)
                </label>
                <textarea
                  rows={4}
                  value={mSteps}
                  onChange={(e) => setMSteps(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] p-3 text-xs"
                />
              </div>

              {error && (
                <p className="rounded-xl bg-rose-50 px-3 py-2 text-xs text-rose-700">
                  {error}
                </p>
              )}

              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setModal("none")}
                  className="rounded-xl border border-[#E8E2D9] px-4 py-2 text-xs font-semibold"
                >
                  Abbrechen
                </button>
                <button
                  disabled={busy}
                  type="submit"
                  className="rounded-xl bg-[#2D5A45] px-4 py-2 text-xs font-semibold text-white"
                >
                  {busy ? "Speichere…" : "Rezept speichern"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
