import React, { useState } from "react";
import {
  ArrowLeftRight,
  Calendar,
  Check,
  ChefHat,
  Clock,
  Flame,
  LayoutGrid,
  List,
  Minus,
  Plus,
  Repeat,
  SlidersHorizontal,
  Sparkles,
  Users,
  Utensils,
  Wind,
} from "lucide-react";
import {
  EFFORT_META,
  SLOT_LABELS,
  type AppSettings,
  type LlmHealth,
  type MealPlan,
  type MealPlanEntry,
  type Recipe,
  type SlotType,
} from "../types";
import { MacroPills, MacroProgressBar } from "./MacroPills";

interface WeekPlanViewProps {
  plan: MealPlan;
  settings: AppSettings;
  llmHealth: LlmHealth | null;
  generating: boolean;
  onGenerate: (params: {
    days_count: number;
    servings_per_meal: number;
    max_effort_level: number;
    target_budget_eur: number;
    active_slots: SlotType[];
    batch_cooking: boolean;
    use_ai: boolean;
    ai_note?: string;
  }) => Promise<void>;
  onScaleWeekServings: (servings: number) => Promise<void>;
  onUpdateEntry: (
    entryId: number,
    payload: { recipe_id?: number; servings?: number; is_cooked?: boolean }
  ) => Promise<void>;
  onOpenRecipe: (recipe: Recipe, servings?: number) => void;
  onOpenSwap: (entry: MealPlanEntry) => void;
  onGoToShopping: () => void;
}

const ALL_SLOTS: SlotType[] = ["breakfast", "lunch", "dinner", "snack"];

export const WeekPlanView: React.FC<WeekPlanViewProps> = ({
  plan,
  settings,
  llmHealth,
  generating,
  onGenerate,
  onScaleWeekServings,
  onUpdateEntry,
  onOpenRecipe,
  onOpenSwap,
  onGoToShopping,
}) => {
  const [selectedDay, setSelectedDay] = useState<number>(0);
  const [viewMode, setViewMode] = useState<"day" | "week">("day");
  const [showControls, setShowControls] = useState<boolean>(true);

  // Planner configuration state
  const [servings, setServings] = useState<number>(plan.servings_per_meal || 2);
  const [daysCount, setDaysCount] = useState<number>(plan.days_count || 7);
  const [maxEffort, setMaxEffort] = useState<number>(plan.max_effort_level || 2);
  const [budget, setBudget] = useState<number>(plan.target_budget_eur || 75);
  const [activeSlots, setActiveSlots] = useState<SlotType[]>(
    plan.active_slots.length ? plan.active_slots : ALL_SLOTS
  );
  const [batchCooking, setBatchCooking] = useState<boolean>(plan.batch_cooking);
  const [aiNote, setAiNote] = useState<string>("");

  React.useEffect(() => {
    setServings(plan.servings_per_meal);
    setDaysCount(plan.days_count);
    setMaxEffort(plan.max_effort_level);
    setBudget(plan.target_budget_eur);
    setBatchCooking(plan.batch_cooking);
    if (selectedDay >= plan.days_count) {
      setSelectedDay(0);
    }
  }, [plan.id]);

  const toggleSlot = (slot: SlotType) => {
    setActiveSlots((prev) => {
      if (prev.includes(slot)) {
        return prev.length > 1 ? prev.filter((s) => s !== slot) : prev;
      }
      return ALL_SLOTS.filter((s) => s === slot || prev.includes(s));
    });
  };

  const dayEntries = plan.entries.filter((e) => e.day_of_week === selectedDay);
  const selectedDaySummary =
    plan.daily_macros.find((d) => d.day_of_week === selectedDay) ||
    plan.daily_macros[0];

  return (
    <div className="space-y-6">
      {/* Top Planner Control Card */}
      <section className="overflow-hidden rounded-3xl border border-[#E8E2D9] bg-white shadow-[0_1px_3px_rgba(30,36,33,0.04)]">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#EFEAE2] px-5 py-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 rounded-full bg-[#EBF3EE] px-2.5 py-0.5 text-xs font-semibold text-[#2D5A45]">
                <Calendar className="h-3.5 w-3.5" />
                Woche ab {plan.week_start_date}
              </span>
              <span className="text-xs font-medium text-[#6B736E]">
                {plan.servings_per_meal}{" "}
                {plan.servings_per_meal === 1 ? "Person" : "Personen"} ·{" "}
                {plan.days_count} Tage
              </span>
            </div>
            <h1 className="mt-1 text-xl font-bold tracking-tight text-[#1E2421]">
              Dein Wochenplan
            </h1>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Live People Count Quick-Scaler for Current Week */}
            <div
              className="inline-flex items-center gap-1.5 rounded-2xl border border-[#E8E2D9] bg-[#FAF8F5] px-2.5 py-1.5"
              title="Personenzahl für diese Woche sofort anpassen"
            >
              <Users className="h-4 w-4 text-[#2D5A45]" />
              <span className="hidden text-xs font-medium text-[#5A635E] sm:inline">
                Diese Woche:
              </span>
              <button
                onClick={() => {
                  const next = Math.max(1, plan.servings_per_meal - 1);
                  setServings(next);
                  onScaleWeekServings(next);
                }}
                className="rounded-lg p-1 hover:bg-white"
              >
                <Minus className="h-3.5 w-3.5" />
              </button>
              <span className="min-w-[20px] text-center text-sm font-bold tabular-nums">
                {plan.servings_per_meal}
              </span>
              <button
                onClick={() => {
                  const next = Math.min(12, plan.servings_per_meal + 1);
                  setServings(next);
                  onScaleWeekServings(next);
                }}
                className="rounded-lg p-1 hover:bg-white"
              >
                <Plus className="h-3.5 w-3.5" />
              </button>
            </div>

            <button
              onClick={() => setShowControls((s) => !s)}
              className="inline-flex items-center gap-1.5 rounded-2xl border border-[#E8E2D9] bg-white px-3.5 py-2 text-xs font-semibold text-[#1E2421] transition hover:bg-[#FAF8F5]"
            >
              <SlidersHorizontal className="h-3.5 w-3.5" />
              {showControls ? "Optionen einklappen" : "Woche konfigurieren"}
            </button>

            <button
              onClick={onGoToShopping}
              className="inline-flex items-center gap-1.5 rounded-2xl bg-[#2D5A45] px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-[#234836]"
            >
              Einkaufsliste (~{plan.shopping_cost_after_pantry_eur.toFixed(0)} €)
            </button>
          </div>
        </div>

        {/* Collapsible Planning Controls */}
        {showControls && (
          <div className="space-y-4 bg-[#FCFBF9] px-5 py-4">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {/* Effort Level Selector (Mise Signature!) */}
              <div className="space-y-1.5 lg:col-span-2">
                <label className="flex items-center gap-1.5 text-xs font-semibold text-[#4E5752]">
                  <ChefHat className="h-3.5 w-3.5 text-[#2D5A45]" />
                  Koch-Einfachheit (wie in Mise)
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[1, 2, 3].map((lvl) => {
                    const meta = EFFORT_META[lvl];
                    const active = maxEffort === lvl;
                    return (
                      <button
                        key={lvl}
                        type="button"
                        onClick={() => setMaxEffort(lvl)}
                        className={`rounded-2xl border px-3 py-2 text-left transition ${
                          active
                            ? "border-[#2D5A45] bg-[#EBF3EE] text-[#1E2421] shadow-xs"
                            : "border-[#E8E2D9] bg-white text-[#5A635E] hover:border-[#CFC6B9]"
                        }`}
                      >
                        <div className="text-xs font-bold">
                          {lvl}. {meta.short}
                        </div>
                        <div className="mt-0.5 text-[10px] leading-tight opacity-80">
                          {meta.desc}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* People & Days */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-[#4E5752]">
                  Personen & Tage
                </label>
                <div className="flex gap-2">
                  <select
                    value={servings}
                    onChange={(e) => setServings(Number(e.target.value))}
                    className="w-1/2 rounded-xl border border-[#E8E2D9] bg-white px-2.5 py-2 text-xs font-semibold text-[#1E2421] focus:border-[#2D5A45] focus:outline-none"
                  >
                    {[1, 2, 3, 4, 5, 6].map((n) => (
                      <option key={n} value={n}>
                        {n} {n === 1 ? "Person" : "Personen"}
                      </option>
                    ))}
                  </select>
                  <select
                    value={daysCount}
                    onChange={(e) => setDaysCount(Number(e.target.value))}
                    className="w-1/2 rounded-xl border border-[#E8E2D9] bg-white px-2.5 py-2 text-xs font-semibold text-[#1E2421] focus:border-[#2D5A45] focus:outline-none"
                  >
                    {[3, 5, 6, 7].map((d) => (
                      <option key={d} value={d}>
                        {d} Tage
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex items-center justify-between pt-1">
                  <label className="inline-flex cursor-pointer items-center gap-2 text-xs font-medium text-[#4E5752]">
                    <input
                      type="checkbox"
                      checked={batchCooking}
                      onChange={(e) => setBatchCooking(e.target.checked)}
                      className="h-3.5 w-3.5 rounded accent-[#2D5A45]"
                    />
                    Batch-Cooking (1× kochen, 2× essen)
                  </label>
                </div>
              </div>

              {/* Budget & Active Slots */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-[#4E5752]">
                  Wochenbudget (€) & Mahlzeiten
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min={20}
                    max={400}
                    step={5}
                    value={budget}
                    onChange={(e) => setBudget(Number(e.target.value))}
                    className="w-24 rounded-xl border border-[#E8E2D9] bg-white px-2.5 py-2 text-xs font-bold tabular-nums focus:border-[#2D5A45] focus:outline-none"
                  />
                  <span className="text-xs text-[#6B736E]">€ / Woche (ALDI)</span>
                </div>
                <div className="flex flex-wrap gap-1 pt-0.5">
                  {ALL_SLOTS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => toggleSlot(s)}
                      className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold transition ${
                        activeSlots.includes(s)
                          ? "bg-[#1E2421] text-white"
                          : "bg-[#EDE7DE] text-[#6B736E]"
                      }`}
                    >
                      {SLOT_LABELS[s]}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Action Row */}
            <div className="flex flex-wrap items-center gap-2.5 border-t border-[#EFEAE2] pt-3.5">
              <input
                type="text"
                value={aiNote}
                onChange={(e) => setAiNote(e.target.value)}
                placeholder="Optionaler KI-Wunsch (z. B. ‚Diese Woche viel Hähnchen & Ofengerichte, abends unter 15 Min‘)…"
                className="min-w-[240px] flex-1 rounded-2xl border border-[#E8E2D9] bg-white px-3.5 py-2 text-xs text-[#1E2421] placeholder:text-[#9AA29D] focus:border-[#2D5A45] focus:outline-none"
              />
              <button
                disabled={generating}
                onClick={() =>
                  onGenerate({
                    days_count: daysCount,
                    servings_per_meal: servings,
                    max_effort_level: maxEffort,
                    target_budget_eur: budget,
                    active_slots: activeSlots,
                    batch_cooking: batchCooking,
                    use_ai: false,
                  })
                }
                className="inline-flex items-center gap-1.5 rounded-2xl bg-[#2D5A45] px-4 py-2 text-xs font-semibold text-white transition hover:bg-[#234836] disabled:opacity-50"
              >
                <Utensils className="h-3.5 w-3.5" />
                {generating ? "Plane Woche…" : "Wochenplan neu generieren"}
              </button>

              <button
                disabled={generating}
                onClick={() =>
                  onGenerate({
                    days_count: daysCount,
                    servings_per_meal: servings,
                    max_effort_level: maxEffort,
                    target_budget_eur: budget,
                    active_slots: activeSlots,
                    batch_cooking: batchCooking,
                    use_ai: true,
                    ai_note: aiNote || undefined,
                  })
                }
                className="inline-flex items-center gap-1.5 rounded-2xl border border-[#C86442]/40 bg-[#FDF2EE] px-4 py-2 text-xs font-semibold text-[#A34728] transition hover:bg-[#FAE4DC] disabled:opacity-50"
                title={
                  llmHealth?.connected
                    ? `Verbunden mit ${llmHealth.configured_model}`
                    : "Nutzt lokalen Ollama-Server (Fallback automatisch falls offline)"
                }
              >
                <Sparkles className="h-3.5 w-3.5" />
                Mit lokaler KI planen
                <span
                  className={`h-2 w-2 rounded-full ${
                    llmHealth?.connected ? "bg-emerald-500" : "bg-amber-400"
                  }`}
                />
              </button>
            </div>
          </div>
        )}
      </section>

      {/* Weekly Average Macros & ALDI Cost Dashboard */}
      <section className="grid gap-4 rounded-3xl border border-[#E8E2D9] bg-white p-5 sm:grid-cols-2 lg:grid-cols-5">
        <MacroProgressBar
          label="Ø Kalorien / Tag"
          value={plan.weekly_avg_kcal}
          target={settings.kcal_target}
          unit="kcal"
          colorClass="bg-[#2D5A45]"
          subtext="pro Person"
        />
        <MacroProgressBar
          label="Ø Protein / Tag"
          value={plan.weekly_avg_protein_g}
          target={settings.protein_g_target}
          unit="g"
          colorClass="bg-[#2F6690]"
          subtext="Muskel- & Sättigungsfokus"
        />
        <MacroProgressBar
          label="Ø Kohlenhydrate"
          value={plan.weekly_avg_carbs_g}
          target={settings.carbs_g_target}
          unit="g"
          colorClass="bg-[#C78623]"
          subtext={`${Math.round(plan.weekly_avg_complex_carb_ratio)}% komplexe KH`}
        />
        <MacroProgressBar
          label="Ø Ballaststoffe"
          value={plan.weekly_avg_fiber_g}
          target={settings.fiber_g_target}
          unit="g"
          colorClass="bg-emerald-600"
          subtext={`Fett Ø ${Math.round(plan.weekly_avg_fat_g)}g / Tag`}
        />
        <div className="flex flex-col justify-between rounded-2xl bg-[#FAF8F5] px-3.5 py-2.5">
          <div className="text-xs font-medium text-[#5A635E]">ALDI-Wochenkosten</div>
          <div className="mt-1 flex items-baseline gap-1.5 tabular-nums">
            <span className="text-xl font-bold text-[#1E2421]">
              ~{plan.estimated_cost_eur.toFixed(0)} €
            </span>
            <span className="text-xs text-[#7B847E]">Verzehrwert</span>
          </div>
          <div className="text-[11px] text-[#6B736E] tabular-nums">
            Einkauf (Packungen): ~{plan.shopping_cost_after_pantry_eur.toFixed(0)} € · Ziel{" "}
            {plan.target_budget_eur.toFixed(0)} €
          </div>
        </div>
      </section>

      {plan.llm_rationale && (
        <div className="rounded-2xl border border-[#E6DFD5] bg-[#F5F1EA] px-4 py-2.5 text-xs text-[#4E5752]">
          <strong className="font-semibold text-[#2D5A45]">Plan-Hinweis:</strong>{" "}
          {plan.llm_rationale}
        </div>
      )}

      {/* Signature Mise 7-Day Week Ribbon + View Mode Toggle */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-1 gap-2 overflow-x-auto pb-1">
          {plan.daily_macros.map((day) => {
            const active = viewMode === "day" && selectedDay === day.day_of_week;
            return (
              <button
                key={day.day_of_week}
                onClick={() => {
                  setSelectedDay(day.day_of_week);
                  setViewMode("day");
                }}
                className={`min-w-[106px] flex-1 rounded-2xl border px-3 py-2.5 text-left transition ${
                  active
                    ? "border-[#2D5A45] bg-[#2D5A45] text-white shadow-sm"
                    : "border-[#E8E2D9] bg-white text-[#1E2421] hover:border-[#2D5A45]/40"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold">
                    {day.day_label.slice(0, 2)}
                  </span>
                  <div className="flex gap-0.5">
                    {Array.from({ length: day.meals_count }).map((_, i) => (
                      <span
                        key={i}
                        className={`h-1.5 w-1.5 rounded-full ${
                          i < day.cooked_count
                            ? active
                              ? "bg-emerald-300"
                              : "bg-emerald-600"
                            : active
                            ? "bg-white/45"
                            : "bg-[#D9D0C3]"
                        }`}
                      />
                    ))}
                  </div>
                </div>
                <div
                  className={`mt-1 text-[11px] font-semibold tabular-nums ${
                    active ? "text-white/95" : "text-[#4E5752]"
                  }`}
                >
                  {Math.round(day.kcal)} kcal
                </div>
                <div
                  className={`text-[10px] tabular-nums ${
                    active ? "text-emerald-100" : "text-[#2F6690]"
                  }`}
                >
                  P {Math.round(day.protein_g)}g · KH {Math.round(day.carbs_g)}g
                </div>
              </button>
            );
          })}
        </div>

        <div className="inline-flex rounded-2xl border border-[#E8E2D9] bg-white p-1">
          <button
            onClick={() => setViewMode("day")}
            className={`inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
              viewMode === "day"
                ? "bg-[#1E2421] text-white"
                : "text-[#5A635E] hover:text-[#1E2421]"
            }`}
          >
            <List className="h-3.5 w-3.5" />
            Tages-Fokus
          </button>
          <button
            onClick={() => setViewMode("week")}
            className={`inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
              viewMode === "week"
                ? "bg-[#1E2421] text-white"
                : "text-[#5A635E] hover:text-[#1E2421]"
            }`}
          >
            <LayoutGrid className="h-3.5 w-3.5" />
            Ganze Woche
          </button>
        </div>
      </div>

      {/* Day Focus View */}
      {viewMode === "day" && selectedDaySummary && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-[#E8E2D9] bg-white px-5 py-3">
            <div className="flex items-center gap-2">
              <Flame className="h-4 w-4 text-[#C86442]" />
              <h2 className="text-base font-bold text-[#1E2421]">
                {selectedDaySummary.day_label}
              </h2>
              <span className="text-xs text-[#6B736E]">
                (pro Person · ~{selectedDaySummary.estimated_cost_per_person.toFixed(2)} €)
              </span>
            </div>
            <MacroPills
              kcal={selectedDaySummary.kcal}
              protein={selectedDaySummary.protein_g}
              carbs={selectedDaySummary.carbs_g}
              fat={selectedDaySummary.fat_g}
              fiber={selectedDaySummary.fiber_g}
              complexRatio={selectedDaySummary.complex_carb_ratio}
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {dayEntries.map((entry) => {
              const r = entry.recipe;
              const eff = EFFORT_META[r.effort_level] || EFFORT_META[2];
              return (
                <article
                  key={entry.id}
                  className={`group flex flex-col justify-between rounded-3xl border bg-white p-5 transition hover:shadow-md ${
                    entry.is_cooked
                      ? "border-emerald-200 bg-emerald-50/25"
                      : "border-[#E8E2D9]"
                  }`}
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold uppercase tracking-wider text-[#2D5A45]">
                          {SLOT_LABELS[entry.slot]}
                        </span>
                        <span
                          className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold ${eff.badgeClass}`}
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
                        {entry.is_leftover_from_entry_id && (
                          <span className="inline-flex items-center gap-1 rounded-full border border-indigo-200 bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold text-indigo-700">
                            <Repeat className="h-2.5 w-2.5" />
                            Rest / Meal-Prep
                          </span>
                        )}
                      </div>
                      <span className="inline-flex items-center gap-1 text-xs text-[#6B736E]">
                        <Clock className="h-3.5 w-3.5" />
                        {entry.is_leftover_from_entry_id
                          ? (settings.kitchen_equipment || []).includes("microwave")
                            ? "Aufwärmen"
                            : "Pfanne / Airfryer"
                          : `${r.total_time_min} Min`}
                      </span>
                    </div>

                    <button
                      type="button"
                      onClick={() => onOpenRecipe(r, entry.servings)}
                      className="mt-2.5 flex items-start gap-3 text-left"
                    >
                      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-[#F4EFE7] text-2xl">
                        {r.image_emoji}
                      </span>
                      <div>
                        <h3 className="text-base font-bold leading-snug text-[#1E2421] group-hover:text-[#2D5A45]">
                          {r.title}
                        </h3>
                        <p className="mt-0.5 line-clamp-2 text-xs text-[#6B736E]">
                          {r.description}
                        </p>
                      </div>
                    </button>

                    {/* Per-Meal Macros (Mise Core!) */}
                    <div className="mt-3.5">
                      <MacroPills
                        kcal={r.kcal_per_serving}
                        protein={r.protein_g}
                        carbs={r.carbs_g}
                        fat={r.fat_g}
                        fiber={r.fiber_g}
                        complexRatio={r.complex_carb_ratio}
                      />
                    </div>
                  </div>

                  {/* Card Footer Controls */}
                  <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-[#F0EAE0] pt-3">
                    <div className="flex items-center gap-2">
                      <div className="inline-flex items-center rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-1 py-0.5 text-xs">
                        <button
                          onClick={() =>
                            onUpdateEntry(entry.id, {
                              servings: Math.max(1, entry.servings - 1),
                            })
                          }
                          className="rounded p-1 hover:bg-white"
                        >
                          <Minus className="h-3 w-3" />
                        </button>
                        <span className="px-1.5 font-semibold tabular-nums">
                          {entry.servings} P.
                        </span>
                        <button
                          onClick={() =>
                            onUpdateEntry(entry.id, {
                              servings: Math.min(12, entry.servings + 1),
                            })
                          }
                          className="rounded p-1 hover:bg-white"
                        >
                          <Plus className="h-3 w-3" />
                        </button>
                      </div>
                      <span className="text-xs font-semibold tabular-nums text-[#2D5A45]">
                        ~{(r.estimated_cost_per_serving * entry.servings).toFixed(2)} €
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => onOpenRecipe(r, entry.servings)}
                        className="rounded-xl border border-[#E8E2D9] bg-white px-2.5 py-1.5 text-xs font-semibold text-[#1E2421] hover:bg-[#FAF8F5]"
                      >
                        Zubereitung
                      </button>
                      <button
                        onClick={() => onOpenSwap(entry)}
                        className="inline-flex items-center gap-1 rounded-xl border border-[#E8E2D9] bg-white px-2.5 py-1.5 text-xs font-semibold text-[#4E5752] hover:bg-[#FAF8F5]"
                      >
                        <ArrowLeftRight className="h-3 w-3" />
                        Tauschen
                      </button>
                      <button
                        onClick={() =>
                          onUpdateEntry(entry.id, { is_cooked: !entry.is_cooked })
                        }
                        className={`inline-flex items-center gap-1 rounded-xl px-2.5 py-1.5 text-xs font-semibold transition ${
                          entry.is_cooked
                            ? "bg-[#2D5A45] text-white"
                            : "border border-[#E8E2D9] bg-[#FAF8F5] text-[#4E5752] hover:border-[#2D5A45]"
                        }`}
                        title="Als gekocht abhaken (bucht Zutaten aus dem Vorratsschrank ab)"
                      >
                        <Check className="h-3.5 w-3.5" />
                        {entry.is_cooked ? "Gekocht" : "Abhaken"}
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      )}

      {/* Full Week Overview Grid */}
      {viewMode === "week" && (
        <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
          {plan.daily_macros.map((day) => {
            const entries = plan.entries.filter(
              (e) => e.day_of_week === day.day_of_week
            );
            return (
              <div
                key={day.day_of_week}
                className="flex flex-col rounded-3xl border border-[#E8E2D9] bg-white p-4"
              >
                <div className="mb-3 flex items-center justify-between border-b border-[#EFEAE2] pb-2.5">
                  <div>
                    <h3 className="text-sm font-bold text-[#1E2421]">
                      {day.day_label}
                    </h3>
                    <p className="text-[11px] tabular-nums text-[#6B736E]">
                      {Math.round(day.kcal)} kcal · P {Math.round(day.protein_g)}g · KH{" "}
                      {Math.round(day.carbs_g)}g ({Math.round(day.complex_carb_ratio)}% kompl.)
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      setSelectedDay(day.day_of_week);
                      setViewMode("day");
                    }}
                    className="rounded-xl bg-[#F4EFE7] px-2.5 py-1 text-[11px] font-semibold text-[#2D5A45] hover:bg-[#E8E0D3]"
                  >
                    Details
                  </button>
                </div>

                <div className="space-y-2">
                  {entries.map((e) => (
                    <div
                      key={e.id}
                      className="flex items-center justify-between gap-2 rounded-2xl border border-[#F0EAE0] bg-[#FCFBF9] p-2.5 transition hover:border-[#2D5A45]/40"
                    >
                      <button
                        type="button"
                        onClick={() => onOpenRecipe(e.recipe, e.servings)}
                        className="flex min-w-0 flex-1 items-center gap-2.5 text-left"
                      >
                        <span className="text-lg">{e.recipe.image_emoji}</span>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase text-[#2D5A45]">
                            <span>{SLOT_LABELS[e.slot]}</span>
                            {e.is_leftover_from_entry_id && (
                              <span className="text-indigo-600">· Rest</span>
                            )}
                          </div>
                          <div className="truncate text-xs font-bold text-[#1E2421]">
                            {e.recipe.title}
                          </div>
                          <div className="text-[10px] tabular-nums text-[#6B736E]">
                            {Math.round(e.recipe.kcal_per_serving)} kcal · P{" "}
                            {Math.round(e.recipe.protein_g)}g · KH{" "}
                            {Math.round(e.recipe.carbs_g)}g
                          </div>
                        </div>
                      </button>
                      <button
                        onClick={() => onOpenSwap(e)}
                        className="rounded-lg p-1.5 text-[#7B847E] hover:bg-white hover:text-[#1E2421]"
                        title="Mahlzeit tauschen"
                      >
                        <ArrowLeftRight className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
