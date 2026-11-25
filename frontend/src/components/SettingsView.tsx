import React, { useState } from "react";
import { Check, Cpu, Flame, RefreshCw, Save, Sliders } from "lucide-react";
import { api } from "../api";
import {
  KITCHEN_EQUIPMENT_OPTIONS,
  type AppSettings,
  type DietType,
  type LlmHealth,
} from "../types";

interface SettingsViewProps {
  settings: AppSettings;
  llmHealth: LlmHealth | null;
  onSaved: (updated: AppSettings) => void;
  onRefreshAiHealth: () => Promise<void>;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  settings,
  llmHealth,
  onSaved,
  onRefreshAiHealth,
}) => {
  const [form, setForm] = useState<AppSettings>(settings);
  const [excludedText, setExcludedText] = useState(
    settings.excluded_ingredients.join(", ")
  );
  const [saving, setSaving] = useState(false);
  const [savedOk, setSavedOk] = useState(false);
  const [testingAi, setTestingAi] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSavedOk(false);
    try {
      const excluded = excludedText
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const updated = await api.updateSettings({
        ...form,
        excluded_ingredients: excluded,
      });
      onSaved(updated);
      setSavedOk(true);
      await onRefreshAiHealth();
      setTimeout(() => setSavedOk(false), 2500);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSave} className="space-y-6">
      {/* Header */}
      <section className="flex flex-wrap items-center justify-between gap-3 rounded-3xl border border-[#E8E2D9] bg-white p-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#1E2421]">
            Einstellungen & Lokale KI
          </h1>
          <p className="text-xs text-[#6B736E]">
            Makro-Ziele, Haushalt, ALDI-Präferenzen und Ollama / 24-GB-GPU-Anbindung.
          </p>
        </div>
        <button
          disabled={saving}
          type="submit"
          className="inline-flex items-center gap-1.5 rounded-2xl bg-[#2D5A45] px-5 py-2.5 text-xs font-semibold text-white hover:bg-[#234836] disabled:opacity-50"
        >
          {savedOk ? <Check className="h-4 w-4" /> : <Save className="h-4 w-4" />}
          {savedOk ? "Gespeichert!" : saving ? "Speichere…" : "Einstellungen speichern"}
        </button>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Household & Nutrition Targets */}
        <section className="space-y-4 rounded-3xl border border-[#E8E2D9] bg-white p-5">
          <div className="flex items-center gap-2 text-sm font-bold text-[#1E2421]">
            <Sliders className="h-4 w-4 text-[#2D5A45]" />
            Haushalt, Makros & Ernährung
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-[#5A635E]">PLZ (für Angebote)</label>
              <input
                type="text"
                maxLength={5}
                value={form.postal_code}
                onChange={(e) => setForm({ ...form, postal_code: e.target.value })}
                className="mt-1 w-full rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-3 py-2 text-sm font-bold tabular-nums"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-[#5A635E]">
                Standard-Personenzahl
              </label>
              <input
                type="number"
                min={1}
                max={12}
                value={form.default_servings}
                onChange={(e) =>
                  setForm({ ...form, default_servings: Number(e.target.value) })
                }
                className="mt-1 w-full rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-3 py-2 text-sm font-bold tabular-nums"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-[#5A635E]">
                Wochenbudget (€)
              </label>
              <input
                type="number"
                min={15}
                max={400}
                value={form.weekly_budget_eur}
                onChange={(e) =>
                  setForm({ ...form, weekly_budget_eur: Number(e.target.value) })
                }
                className="mt-1 w-full rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-3 py-2 text-sm font-bold tabular-nums"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-[#5A635E]">
                Einkaufs-Strategie
              </label>
              <select
                value={form.max_stores_per_trip}
                onChange={(e) =>
                  setForm({ ...form, max_stores_per_trip: Number(e.target.value) })
                }
                className="mt-1 w-full rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-3 py-2 text-xs font-semibold"
              >
                <option value={1}>1 Markt (bequem bei ALDI)</option>
                <option value={2}>Bis 2 Märkte (Angebote kombinieren)</option>
                <option value={3}>Multi-Markt (max. Ersparnis)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 border-t border-[#EFEAE2] pt-4 sm:grid-cols-3">
            <div>
              <label className="text-xs font-semibold text-[#5A635E]">Kalorien / Tag</label>
              <input
                type="number"
                step={50}
                value={form.kcal_target}
                onChange={(e) =>
                  setForm({ ...form, kcal_target: Number(e.target.value) })
                }
                className="mt-1 w-full rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-3 py-2 text-sm font-bold tabular-nums"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-[#2F6690]">Protein (g)</label>
              <input
                type="number"
                step={5}
                value={form.protein_g_target}
                onChange={(e) =>
                  setForm({ ...form, protein_g_target: Number(e.target.value) })
                }
                className="mt-1 w-full rounded-xl border border-[#CBE0EE] bg-[#F2F8FC] px-3 py-2 text-sm font-bold tabular-nums"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-[#946110]">
                Kohlenhydrate (g)
              </label>
              <input
                type="number"
                step={5}
                value={form.carbs_g_target}
                onChange={(e) =>
                  setForm({ ...form, carbs_g_target: Number(e.target.value) })
                }
                className="mt-1 w-full rounded-xl border border-[#F0DEC0] bg-[#FEF9F0] px-3 py-2 text-sm font-bold tabular-nums"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-emerald-800">
                Ballaststoffe (g)
              </label>
              <input
                type="number"
                step={5}
                value={form.fiber_g_target}
                onChange={(e) =>
                  setForm({ ...form, fiber_g_target: Number(e.target.value) })
                }
                className="mt-1 w-full rounded-xl border border-emerald-200 bg-emerald-50/50 px-3 py-2 text-sm font-bold tabular-nums"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-[#6B3F5E]">Fett (g)</label>
              <input
                type="number"
                step={5}
                value={form.fat_g_target}
                onChange={(e) =>
                  setForm({ ...form, fat_g_target: Number(e.target.value) })
                }
                className="mt-1 w-full rounded-xl border border-[#E7D7E3] bg-[#FAF4F8] px-3 py-2 text-sm font-bold tabular-nums"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-[#5A635E]">Ernährung</label>
              <select
                value={form.diet_type}
                onChange={(e) =>
                  setForm({ ...form, diet_type: e.target.value as DietType })
                }
                className="mt-1 w-full rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-2.5 py-2 text-xs font-semibold"
              >
                <option value="omnivore">Alles (Omnivor)</option>
                <option value="pescatarian">Pescetarisch</option>
                <option value="vegetarian">Vegetarisch</option>
                <option value="vegan">Vegan</option>
              </select>
            </div>
          </div>

          <div className="space-y-2 border-t border-[#EFEAE2] pt-3">
            <div className="flex items-center gap-1.5 text-xs font-bold text-[#1E2421]">
              <Flame className="h-3.5 w-3.5 text-[#C86442]" />
              Meine Küchengeräte (steuert Planer & lokale KI)
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {KITCHEN_EQUIPMENT_OPTIONS.map((eq) => {
                const active = (form.kitchen_equipment || []).includes(eq.id);
                return (
                  <button
                    key={eq.id}
                    type="button"
                    onClick={() => {
                      const current = form.kitchen_equipment || [];
                      const next = active
                        ? current.filter((x) => x !== eq.id)
                        : [...current, eq.id];
                      setForm({ ...form, kitchen_equipment: next });
                    }}
                    className={`rounded-2xl border px-3 py-2 text-left transition ${
                      active
                        ? "border-[#2D5A45] bg-[#EBF3EE] text-[#1E2421]"
                        : "border-[#E8E2D9] bg-[#FAF8F5] text-[#7B847E] hover:border-[#CFC6B9]"
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs font-bold">
                      <span>{eq.label}</span>
                      {active && <Check className="h-3.5 w-3.5 text-[#2D5A45]" />}
                    </div>
                    <div className="mt-0.5 text-[10px] leading-tight opacity-80">
                      {eq.hint}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="space-y-2 border-t border-[#EFEAE2] pt-3">
            <label className="inline-flex cursor-pointer items-center gap-2 text-xs font-semibold text-[#1E2421]">
              <input
                type="checkbox"
                checked={form.prefer_complex_carbs}
                onChange={(e) =>
                  setForm({ ...form, prefer_complex_carbs: e.target.checked })
                }
                className="h-4 w-4 rounded accent-[#2D5A45]"
              />
              Komplexe Kohlenhydrate stark bevorzugen (Hafer, Vollkorn, Hülsenfrüchte, Süßkartoffel)
            </label>
            <div>
              <label className="text-xs font-semibold text-[#5A635E]">
                Ausgeschlossene Zutaten / Allergene (kommagetrennt)
              </label>
              <input
                type="text"
                value={excludedText}
                onChange={(e) => setExcludedText(e.target.value)}
                placeholder="z. B. Pilze, Garnelen, Erdnuss"
                className="mt-1 w-full rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-3 py-2 text-xs"
              />
            </div>
          </div>
        </section>

        {/* Local LLM / Ollama Configuration */}
        <section className="space-y-4 rounded-3xl border border-[#E8E2D9] bg-white p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-bold text-[#1E2421]">
              <Cpu className="h-4 w-4 text-[#C86442]" />
              Lokaler LLM-Server (Ollama / OpenAI-API · 24 GB VRAM)
            </div>
            <button
              type="button"
              onClick={async () => {
                setTestingAi(true);
                await onRefreshAiHealth();
                setTestingAi(false);
              }}
              className="inline-flex items-center gap-1 rounded-xl border border-[#E8E2D9] px-2.5 py-1 text-xs font-semibold hover:bg-[#FAF8F5]"
            >
              <RefreshCw className={`h-3 w-3 ${testingAi ? "animate-spin" : ""}`} />
              Prüfen
            </button>
          </div>

          <div
            className={`rounded-2xl border p-3.5 text-xs ${
              llmHealth?.connected
                ? "border-emerald-200 bg-emerald-50 text-emerald-900"
                : "border-amber-200 bg-amber-50 text-amber-900"
            }`}
          >
            <div className="font-bold">
              Status:{" "}
              {llmHealth?.connected
                ? `Verbunden (${llmHealth.provider})`
                : "Derzeit offline (App läuft voll mit deterministischem Planer)"}
            </div>
            {llmHealth?.error && <p className="mt-1 opacity-85">{llmHealth.error}</p>}
            {llmHealth?.available_models && llmHealth.available_models.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {llmHealth.available_models.map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setForm({ ...form, llm_model: m })}
                    className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                      form.llm_model === m
                        ? "bg-[#2D5A45] text-white"
                        : "bg-white text-[#1E2421]"
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-3">
            <div>
              <label className="text-xs font-semibold text-[#5A635E]">
                OpenAI-kompatible Base-URL
              </label>
              <input
                type="text"
                value={form.llm_base_url}
                onChange={(e) => setForm({ ...form, llm_base_url: e.target.value })}
                className="mt-1 w-full rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-3 py-2 font-mono text-xs"
              />
              <p className="mt-1 text-[11px] text-[#7B847E]">
                Ollama Standard: <code>http://127.0.0.1:11434/v1</code> · LM Studio:{" "}
                <code>http://127.0.0.1:1234/v1</code>
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-[#5A635E]">
                  Modellname
                </label>
                <input
                  type="text"
                  value={form.llm_model}
                  onChange={(e) => setForm({ ...form, llm_model: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-3 py-2 font-mono text-xs"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-[#5A635E]">
                  Temperatur ({form.llm_temperature})
                </label>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.1}
                  value={form.llm_temperature}
                  onChange={(e) =>
                    setForm({ ...form, llm_temperature: Number(e.target.value) })
                  }
                  className="mt-3 w-full accent-[#2D5A45]"
                />
              </div>
            </div>

            <div className="rounded-2xl bg-[#FAF8F5] p-3 text-[11px] text-[#5A635E]">
              <strong>Empfehlung für 24 GB VRAM:</strong>{" "}
              <code>ollama run qwen2.5:14b</code> oder{" "}
              <code>ollama run qwen2.5:32b</code> (sehr zuverlässige deutsche JSON-Schema Structured Outputs).
            </div>
          </div>
        </section>
      </div>
    </form>
  );
};
