import React, { useState } from "react";
import {
  Check,
  ChefHat,
  Clock,
  ExternalLink,
  Heart,
  Minus,
  Plus,
  Users,
  Wind,
  X,
} from "lucide-react";
import { EFFORT_META, type Recipe } from "../types";

interface RecipeDetailDrawerProps {
  recipe: Recipe | null;
  initialServings?: number;
  onClose: () => void;
  onToggleFavorite?: (recipeId: number) => void;
}

export const RecipeDetailDrawer: React.FC<RecipeDetailDrawerProps> = ({
  recipe,
  initialServings,
  onClose,
  onToggleFavorite,
}) => {
  const [servings, setServings] = useState<number>(
    initialServings || recipe?.servings || 2
  );
  const [doneSteps, setDoneSteps] = useState<Record<number, boolean>>({});
  const [checkedIngs, setCheckedIngs] = useState<Record<number, boolean>>({});

  React.useEffect(() => {
    if (recipe) {
      setServings(initialServings || recipe.servings || 2);
      setDoneSteps({});
      setCheckedIngs({});
    }
  }, [recipe, initialServings]);

  if (!recipe) return null;

  const scale = servings / Math.max(recipe.servings || 1, 1);
  const effort = EFFORT_META[recipe.effort_level] || EFFORT_META[2];
  const totalCost = recipe.estimated_cost_per_serving * servings;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/35 backdrop-blur-[2px]">
      <div
        className="flex h-full w-full max-w-2xl flex-col bg-[#FAF8F5] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-[#E8E2D9] bg-white px-6 py-5">
          <div className="flex items-start gap-3.5">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[#F2EDE5] text-2xl">
              {recipe.image_emoji}
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${effort.badgeClass}`}
                >
                  <ChefHat className="h-3 w-3" />
                  Stufe {recipe.effort_level}: {effort.label}
                </span>
                {recipe.tags.includes("airfryer") && (
                  <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-[11px] font-semibold text-amber-800">
                    <Wind className="h-3 w-3" />
                    Airfryer
                  </span>
                )}
                <span className="inline-flex items-center gap-1 text-xs text-[#6B736E]">
                  <Clock className="h-3.5 w-3.5" />
                  {recipe.total_time_min} Min ({recipe.prep_time_min} Prep +{" "}
                  {recipe.cook_time_min} Kochen)
                </span>
              </div>
              <h2 className="mt-1.5 text-xl font-bold tracking-tight text-[#1E2421]">
                {recipe.title}
              </h2>
              {recipe.description && (
                <p className="mt-1 text-sm text-[#5A635E]">{recipe.description}</p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {onToggleFavorite && (
              <button
                onClick={() => onToggleFavorite(recipe.id)}
                className={`rounded-xl border p-2 transition ${
                  recipe.is_favorite
                    ? "border-rose-200 bg-rose-50 text-rose-600"
                    : "border-[#E8E2D9] bg-white text-[#6B736E] hover:bg-[#F4F0E9]"
                }`}
                title="Favorit umschalten"
              >
                <Heart
                  className="h-4 w-4"
                  fill={recipe.is_favorite ? "currentColor" : "none"}
                />
              </button>
            )}
            <button
              onClick={onClose}
              className="rounded-xl border border-[#E8E2D9] bg-white p-2 text-[#5A635E] hover:bg-[#F4F0E9]"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 space-y-6 overflow-y-auto px-6 py-5">
          {/* Mise Macro Cards per Serving */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <div className="rounded-2xl border border-[#E8E2D9] bg-white p-3 text-center">
              <div className="text-[11px] font-medium text-[#7B847E]">Kalorien</div>
              <div className="mt-0.5 text-lg font-bold tabular-nums text-[#1E2421]">
                {Math.round(recipe.kcal_per_serving)}
              </div>
              <div className="text-[10px] text-[#7B847E]">kcal / Portion</div>
            </div>
            <div className="rounded-2xl border border-[#CBE0EE] bg-[#F2F8FC] p-3 text-center">
              <div className="text-[11px] font-medium text-[#2F6690]">Protein</div>
              <div className="mt-0.5 text-lg font-bold tabular-nums text-[#1D4B6E]">
                {Math.round(recipe.protein_g)} g
              </div>
              <div className="text-[10px] text-[#2F6690]">pro Portion</div>
            </div>
            <div className="rounded-2xl border border-[#F0DEC0] bg-[#FEF9F0] p-3 text-center">
              <div className="text-[11px] font-medium text-[#946110]">Kohlenhydrate</div>
              <div className="mt-0.5 text-lg font-bold tabular-nums text-[#82540B]">
                {Math.round(recipe.carbs_g)} g
              </div>
              <div className="text-[10px] text-[#946110]">
                {Math.round(recipe.complex_carb_ratio)}% komplex
              </div>
            </div>
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50/70 p-3 text-center">
              <div className="text-[11px] font-medium text-emerald-800">Ballaststoffe</div>
              <div className="mt-0.5 text-lg font-bold tabular-nums text-emerald-900">
                {Math.round(recipe.fiber_g)} g
              </div>
              <div className="text-[10px] text-emerald-700">pro Portion</div>
            </div>
            <div className="rounded-2xl border border-[#E7D7E3] bg-[#FAF4F8] p-3 text-center">
              <div className="text-[11px] font-medium text-[#6B3F5E]">Fett</div>
              <div className="mt-0.5 text-lg font-bold tabular-nums text-[#59304D]">
                {Math.round(recipe.fat_g)} g
              </div>
              <div className="text-[10px] text-[#6B3F5E]">
                ~{recipe.estimated_cost_per_serving.toFixed(2)} € / P.
              </div>
            </div>
          </div>

          {/* Servings Scaler Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-[#E8E2D9] bg-white px-4 py-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-[#1E2421]">
              <Users className="h-4 w-4 text-[#2D5A45]" />
              <span>Zutaten skalieren für:</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="inline-flex items-center rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] p-0.5">
                <button
                  onClick={() => setServings((s) => Math.max(1, s - 1))}
                  className="rounded-lg p-1.5 text-[#1E2421] hover:bg-white"
                >
                  <Minus className="h-3.5 w-3.5" />
                </button>
                <span className="min-w-[84px] text-center text-sm font-bold tabular-nums">
                  {servings} {servings === 1 ? "Person" : "Personen"}
                </span>
                <button
                  onClick={() => setServings((s) => Math.min(12, s + 1))}
                  className="rounded-lg p-1.5 text-[#1E2421] hover:bg-white"
                >
                  <Plus className="h-3.5 w-3.5" />
                </button>
              </div>
              <span className="text-xs font-semibold tabular-nums text-[#2D5A45]">
                ~{totalCost.toFixed(2)} € (ALDI)
              </span>
            </div>
          </div>

          {/* Ingredients Checklist */}
          <div>
            <h3 className="mb-2.5 text-sm font-bold uppercase tracking-wider text-[#6B736E]">
              Zutaten ({recipe.ingredients.length})
            </h3>
            <div className="divide-y divide-[#EFEAE2] overflow-hidden rounded-2xl border border-[#E8E2D9] bg-white">
              {recipe.ingredients.map((ri) => {
                const scaledAmt = Math.round(ri.amount * scale * 10) / 10;
                const checked = !!checkedIngs[ri.id];
                return (
                  <button
                    key={ri.id}
                    type="button"
                    onClick={() =>
                      setCheckedIngs((prev) => ({ ...prev, [ri.id]: !prev[ri.id] }))
                    }
                    className="flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left transition hover:bg-[#FAF8F5]"
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition ${
                          checked
                            ? "border-[#2D5A45] bg-[#2D5A45] text-white"
                            : "border-[#D6CFC4] bg-white"
                        }`}
                      >
                        {checked && <Check className="h-3.5 w-3.5" />}
                      </span>
                      <span
                        className={`text-sm ${
                          checked ? "text-[#9AA29D] line-through" : "text-[#1E2421]"
                        }`}
                      >
                        <strong className="tabular-nums font-semibold">
                          {scaledAmt} {ri.unit}
                        </strong>{" "}
                        {ri.ingredient_name}
                        {ri.preparation_note && (
                          <span className="ml-1.5 text-xs text-[#7B847E]">
                            ({ri.preparation_note})
                          </span>
                        )}
                      </span>
                    </div>
                    <span className="shrink-0 text-xs tabular-nums text-[#7B847E]">
                      ~{(ri.estimated_cost_eur * scale).toFixed(2)} €
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Step-by-Step Preparation (Kochmodus) */}
          <div>
            <div className="mb-2.5 flex items-center justify-between">
              <h3 className="text-sm font-bold uppercase tracking-wider text-[#6B736E]">
                Zubereitung (klicken zum Abhaken)
              </h3>
              {recipe.source_url && (
                <a
                  href={recipe.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-xs font-medium text-[#2D5A45] hover:underline"
                >
                  Original-Quelle <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
            <ol className="space-y-2.5">
              {recipe.instructions.map((step, idx) => {
                const done = !!doneSteps[idx];
                return (
                  <li key={idx}>
                    <button
                      type="button"
                      onClick={() =>
                        setDoneSteps((prev) => ({ ...prev, [idx]: !prev[idx] }))
                      }
                      className={`flex w-full items-start gap-3.5 rounded-2xl border p-4 text-left transition ${
                        done
                          ? "border-emerald-200 bg-emerald-50/50 text-[#7B847E]"
                          : "border-[#E8E2D9] bg-white text-[#1E2421] hover:border-[#2D5A45]/40"
                      }`}
                    >
                      <span
                        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                          done
                            ? "bg-[#2D5A45] text-white"
                            : "bg-[#F0EAE0] text-[#2D5A45]"
                        }`}
                      >
                        {done ? <Check className="h-4 w-4" /> : idx + 1}
                      </span>
                      <p
                        className={`text-sm leading-relaxed ${
                          done ? "line-through" : ""
                        }`}
                      >
                        {step}
                      </p>
                    </button>
                  </li>
                );
              })}
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
};
