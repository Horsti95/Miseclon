import React, { useEffect, useState } from "react";
import { ChefHat, Clock, RefreshCw, X } from "lucide-react";
import { api } from "../api";
import { EFFORT_META, SLOT_LABELS, type MealPlanEntry, type Recipe } from "../types";
import { MacroPills } from "./MacroPills";

interface SwapDrawerProps {
  entry: MealPlanEntry | null;
  onClose: () => void;
  onSelectRecipe: (entryId: number, recipeId: number) => Promise<void>;
}

const SWAP_MODES = [
  { id: "balanced", label: "Ausgewogen" },
  { id: "simpler", label: "Einfacher & schneller" },
  { id: "more_protein", label: "Mehr Protein" },
  { id: "cheaper", label: "Günstiger (ALDI)" },
  { id: "pantry", label: "Vorräte nutzen" },
] as const;

export const SwapDrawer: React.FC<SwapDrawerProps> = ({
  entry,
  onClose,
  onSelectRecipe,
}) => {
  const [mode, setMode] = useState<string>("balanced");
  const [candidates, setCandidates] = useState<Recipe[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!entry) return;
    setLoading(true);
    api
      .getEntrySwaps(entry.id, mode)
      .then(setCandidates)
      .catch(() => setCandidates([]))
      .finally(() => setLoading(false));
  }, [entry, mode]);

  if (!entry) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/35 backdrop-blur-[2px]">
      <div className="flex h-full w-full max-w-lg flex-col bg-[#FAF8F5] shadow-2xl">
        <div className="flex items-center justify-between border-b border-[#E8E2D9] bg-white px-5 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-[#2D5A45]">
              {entry.day_label} · {SLOT_LABELS[entry.slot]} tauschen
            </p>
            <h3 className="mt-0.5 text-base font-bold text-[#1E2421]">
              Aktuell: {entry.recipe.title}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="rounded-xl border border-[#E8E2D9] p-2 text-[#5A635E] hover:bg-[#F4F0E9]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Mode Tabs */}
        <div className="flex flex-wrap gap-1.5 border-b border-[#E8E2D9] bg-white px-5 py-3">
          {SWAP_MODES.map((m) => (
            <button
              key={m.id}
              onClick={() => setMode(m.id)}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                mode === m.id
                  ? "bg-[#2D5A45] text-white"
                  : "bg-[#F2EDE5] text-[#4E5752] hover:bg-[#E7DFD3]"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>

        <div className="flex-1 space-y-2.5 overflow-y-auto p-5">
          {loading ? (
            <div className="flex items-center justify-center py-12 text-sm text-[#6B736E]">
              <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
              Suche passende Alternativen…
            </div>
          ) : candidates.length === 0 ? (
            <p className="py-10 text-center text-sm text-[#6B736E]">
              Keine passenden Alternativen gefunden.
            </p>
          ) : (
            candidates.map((r) => {
              const eff = EFFORT_META[r.effort_level] || EFFORT_META[2];
              return (
                <button
                  key={r.id}
                  onClick={async () => {
                    await onSelectRecipe(entry.id, r.id);
                    onClose();
                  }}
                  className="w-full rounded-2xl border border-[#E8E2D9] bg-white p-4 text-left transition hover:border-[#2D5A45] hover:shadow-sm"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <span className="text-xl">{r.image_emoji}</span>
                      <div>
                        <div className="text-sm font-bold text-[#1E2421]">
                          {r.title}
                        </div>
                        <div className="mt-0.5 flex items-center gap-2 text-[11px] text-[#6B736E]">
                          <span
                            className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-semibold ${eff.badgeClass}`}
                          >
                            <ChefHat className="h-3 w-3" />
                            {eff.short}
                          </span>
                          <span className="inline-flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {r.total_time_min} Min
                          </span>
                          <span className="font-semibold text-[#2D5A45]">
                            ~{r.estimated_cost_per_serving.toFixed(2)} €/P.
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="mt-2.5">
                    <MacroPills
                      kcal={r.kcal_per_serving}
                      protein={r.protein_g}
                      carbs={r.carbs_g}
                      complexRatio={r.complex_carb_ratio}
                      compact
                    />
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
