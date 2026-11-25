import React, { useMemo, useState } from "react";
import {
  Check,
  Copy,
  PackageCheck,
  Plus,
  Recycle,
  RefreshCw,
  ShoppingBasket,
  Store,
  Trash2,
} from "lucide-react";
import type { ShoppingList, ShoppingListItem } from "../types";

interface ShoppingListViewProps {
  shoppingList: ShoppingList;
  targetBudget: number;
  onUpdateItem: (
    itemId: number,
    payload: { is_checked?: boolean; actual_price_eur?: number }
  ) => Promise<void>;
  onAddManual: (payload: {
    custom_name: string;
    category: string;
    to_buy_amount: number;
    unit: string;
    estimated_price_eur: number;
  }) => Promise<void>;
  onDeleteItem: (itemId: number) => Promise<void>;
  onMoveToPantry: () => Promise<number>;
  onRebuild: () => Promise<void>;
  onOpenRecipeById: (recipeId: number) => void;
}

export const ShoppingListView: React.FC<ShoppingListViewProps> = ({
  shoppingList,
  targetBudget,
  onUpdateItem,
  onAddManual,
  onDeleteItem,
  onMoveToPantry,
  onRebuild,
  onOpenRecipeById,
}) => {
  const [groupBy, setGroupBy] = useState<"aisle" | "store">("aisle");
  const [hideChecked, setHideChecked] = useState(false);
  const [copied, setCopied] = useState(false);
  const [pantryToast, setPantryToast] = useState<string | null>(null);
  const [editingPriceId, setEditingPriceId] = useState<number | null>(null);
  const [priceDraft, setPriceDraft] = useState<string>("");

  // Quick manual item form
  const [manualName, setManualName] = useState("");
  const [manualAmount, setManualAmount] = useState("1");
  const [manualUnit, setManualUnit] = useState("stk");
  const [manualPrice, setManualPrice] = useState("1.99");

  const grouped = useMemo(() => {
    const map = new Map<string, ShoppingListItem[]>();
    for (const item of shoppingList.items) {
      if (hideChecked && item.is_checked) continue;
      const key = groupBy === "aisle" ? item.category : item.assigned_store_name;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(item);
    }
    return Array.from(map.entries());
  }, [shoppingList.items, groupBy, hideChecked]);

  const handleCopyText = async () => {
    const lines: string[] = [
      `🛒 Einkaufsliste (~${shoppingList.total_actual_eur.toFixed(2)} €)`,
      "",
    ];
    for (const [group, items] of grouped) {
      lines.push(`**${group}**`);
      for (const i of items) {
        const mark = i.is_checked ? "[x]" : "[ ]";
        const packInfo =
          i.pack_size > 0 && !i.manual_addition
            ? ` (${i.suggested_pack_count}× ${i.pack_size}${i.unit})`
            : "";
        lines.push(
          `${mark} ${i.custom_name}: ${i.to_buy_amount} ${i.unit}${packInfo} ~${(
            i.actual_price_eur ?? i.estimated_price_eur
          ).toFixed(2)} €`
        );
      }
      lines.push("");
    }
    try {
      await navigator.clipboard.writeText(lines.join("\n"));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore clipboard restrictions
    }
  };

  const handleAddManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualName.trim()) return;
    await onAddManual({
      custom_name: manualName.trim(),
      category: "Sonstiges",
      to_buy_amount: Math.max(0.1, Number(manualAmount) || 1),
      unit: manualUnit,
      estimated_price_eur: Math.max(0, Number(manualPrice) || 0),
    });
    setManualName("");
  };

  const progressPct =
    shoppingList.total_items_count > 0
      ? Math.round(
          (shoppingList.checked_count / shoppingList.total_items_count) * 100
        )
      : 0;

  return (
    <div className="space-y-6">
      {/* Top Summary Banner */}
      <section className="rounded-3xl border border-[#E8E2D9] bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-[#2D5A45]">
              <ShoppingBasket className="h-4 w-4" />
              <span>Automatisch konsolidiert · Vorrat bereits abgezogen</span>
            </div>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-[#1E2421]">
              Einkaufsliste
            </h1>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
              <span className="rounded-full bg-emerald-50 px-2.5 py-0.5 font-semibold text-emerald-800">
                {shoppingList.promo_items_count} Angebote
              </span>
              <span className="rounded-full bg-blue-50 px-2.5 py-0.5 font-semibold text-blue-800">
                {shoppingList.verified_items_count} Verifiziert
              </span>
              <span className="rounded-full bg-[#F2EDE5] px-2.5 py-0.5 font-semibold text-[#5A635E]">
                {shoppingList.estimated_items_count} ~ALDI-Schätzung
              </span>
            </div>
          </div>

          <div className="text-right tabular-nums">
            <div className="text-xs font-medium text-[#6B736E]">
              Geschätzter Kassenbetrag
            </div>
            <div className="text-3xl font-bold text-[#1E2421]">
              {shoppingList.total_actual_eur.toFixed(2)} €
            </div>
            <div className="text-xs text-[#6B736E]">
              Wochenbudget: {targetBudget.toFixed(0)} € ·{" "}
              {shoppingList.checked_count}/{shoppingList.total_items_count} erledigt
            </div>
          </div>
        </div>

        {/* Store Breakdown + Progress Bar */}
        <div className="mt-4 space-y-2">
          <div className="h-2 w-full overflow-hidden rounded-full bg-[#EFEAE2]">
            <div
              className="h-full rounded-full bg-[#2D5A45] transition-all duration-300"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
            <div className="flex flex-wrap gap-2">
              {Object.entries(shoppingList.store_breakdown).map(([store, sum]) => (
                <span
                  key={store}
                  className="inline-flex items-center gap-1 rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-2.5 py-1 text-xs font-semibold text-[#1E2421] tabular-nums"
                >
                  <Store className="h-3.5 w-3.5 text-[#2D5A45]" />
                  {store}: ~{sum.toFixed(2)} €
                </span>
              ))}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <div className="inline-flex rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] p-0.5 text-xs">
                <button
                  onClick={() => setGroupBy("aisle")}
                  className={`rounded-lg px-2.5 py-1 font-semibold ${
                    groupBy === "aisle" ? "bg-white text-[#1E2421] shadow-xs" : "text-[#6B736E]"
                  }`}
                >
                  Nach Gang
                </button>
                <button
                  onClick={() => setGroupBy("store")}
                  className={`rounded-lg px-2.5 py-1 font-semibold ${
                    groupBy === "store" ? "bg-white text-[#1E2421] shadow-xs" : "text-[#6B736E]"
                  }`}
                >
                  Nach Markt
                </button>
              </div>

              <button
                onClick={() => setHideChecked((v) => !v)}
                className="rounded-xl border border-[#E8E2D9] bg-white px-3 py-1.5 text-xs font-semibold text-[#4E5752] hover:bg-[#FAF8F5]"
              >
                {hideChecked ? "Erledigte zeigen" : "Erledigte ausblenden"}
              </button>

              <button
                onClick={handleCopyText}
                className="inline-flex items-center gap-1.5 rounded-xl border border-[#E8E2D9] bg-white px-3 py-1.5 text-xs font-semibold text-[#1E2421] hover:bg-[#FAF8F5]"
              >
                <Copy className="h-3.5 w-3.5" />
                {copied ? "Kopiert!" : "Liste kopieren"}
              </button>

              <button
                onClick={async () => {
                  const moved = await onMoveToPantry();
                  setPantryToast(
                    moved > 0
                      ? `${moved} abgehakte Artikel in den Vorratsschrank übernommen!`
                      : "Keine neuen abgehakten Artikel zum Übernehmen."
                  );
                  setTimeout(() => setPantryToast(null), 3500);
                }}
                className="inline-flex items-center gap-1.5 rounded-xl bg-[#2D5A45] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#234836]"
              >
                <PackageCheck className="h-3.5 w-3.5" />
                Abgehakte → Vorrat
              </button>

              <button
                onClick={onRebuild}
                className="rounded-xl border border-[#E8E2D9] bg-white p-1.5 text-[#5A635E] hover:bg-[#FAF8F5]"
                title="Einkaufsliste neu aus Wochenplan & Vorrat berechnen"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
            </div>
          </div>
          {pantryToast && (
            <p className="rounded-xl bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-800">
              {pantryToast}
            </p>
          )}
        </div>
      </section>

      {/* Pack Remainder Suggestions (Resteverwertung!) */}
      {shoppingList.remainder_suggestions.length > 0 && (
        <section className="rounded-3xl border border-amber-200 bg-amber-50/50 p-4">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-900">
            <Recycle className="h-4 w-4" />
            Packungs-Resteverwertung (Frischeartikel)
          </div>
          <p className="mt-1 text-xs text-amber-900/80">
            Bei diesen frischen Zutaten bleibt nach dem Kochen etwas von der Packung übrig – passende Rezeptideen für danach:
          </p>
          <div className="mt-3 grid gap-2.5 sm:grid-cols-2">
            {shoppingList.remainder_suggestions.map((rem) => (
              <div
                key={rem.ingredient_id}
                className="rounded-2xl border border-amber-200/80 bg-white px-3.5 py-2.5"
              >
                <div className="text-xs font-bold text-[#1E2421]">
                  {rem.ingredient_name}:{" "}
                  <span className="text-amber-800">
                    +{rem.remainder_amount} {rem.unit} Rest
                  </span>
                </div>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {rem.suggested_recipes.map((sr) => (
                    <button
                      key={sr.recipe_id}
                      onClick={() => onOpenRecipeById(sr.recipe_id)}
                      className="rounded-full bg-[#F4EFE7] px-2.5 py-0.5 text-[11px] font-semibold text-[#2D5A45] hover:bg-[#E7DFD3]"
                    >
                      {sr.title} ({Math.round(sr.protein_g)}g P)
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Manual Quick-Add Bar */}
      <form
        onSubmit={handleAddManualSubmit}
        className="flex flex-wrap items-center gap-2 rounded-2xl border border-[#E8E2D9] bg-white p-3"
      >
        <input
          type="text"
          value={manualName}
          onChange={(e) => setManualName(e.target.value)}
          placeholder="Eigenen Artikel hinzufügen (z. B. Küchenrolle, Kaffee, Spülmittel)…"
          className="min-w-[200px] flex-1 rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-3 py-2 text-xs focus:border-[#2D5A45] focus:bg-white focus:outline-none"
        />
        <input
          type="number"
          step="0.5"
          value={manualAmount}
          onChange={(e) => setManualAmount(e.target.value)}
          className="w-16 rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-2 py-2 text-xs font-semibold tabular-nums"
        />
        <select
          value={manualUnit}
          onChange={(e) => setManualUnit(e.target.value)}
          className="rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-2 py-2 text-xs font-semibold"
        >
          <option value="stk">Stk</option>
          <option value="g">g</option>
          <option value="ml">ml</option>
        </select>
        <input
          type="number"
          step="0.1"
          value={manualPrice}
          onChange={(e) => setManualPrice(e.target.value)}
          className="w-20 rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] px-2 py-2 text-xs font-semibold tabular-nums"
          placeholder="€"
        />
        <button
          type="submit"
          className="inline-flex items-center gap-1 rounded-xl bg-[#1E2421] px-3.5 py-2 text-xs font-semibold text-white hover:bg-[#323B36]"
        >
          <Plus className="h-3.5 w-3.5" />
          Hinzufügen
        </button>
      </form>

      {/* Aisle / Store Grouped List */}
      <div className="space-y-4">
        {grouped.map(([groupName, items]) => (
          <div
            key={groupName}
            className="overflow-hidden rounded-3xl border border-[#E8E2D9] bg-white"
          >
            <div className="flex items-center justify-between border-b border-[#EFEAE2] bg-[#FAF8F5] px-5 py-2.5">
              <h2 className="text-xs font-bold uppercase tracking-wider text-[#4E5752]">
                {groupName}
              </h2>
              <span className="text-xs font-semibold tabular-nums text-[#7B847E]">
                {items.length} Artikel
              </span>
            </div>
            <div className="divide-y divide-[#F2EDE5]">
              {items.map((item) => {
                const displayPrice =
                  item.actual_price_eur ?? item.estimated_price_eur;
                return (
                  <div
                    key={item.id}
                    className={`flex flex-wrap items-center justify-between gap-3 px-5 py-3 transition ${
                      item.is_checked ? "bg-[#FAF8F5]/70" : "hover:bg-[#FCFBF9]"
                    }`}
                  >
                    <div className="flex min-w-0 flex-1 items-center gap-3.5">
                      <button
                        type="button"
                        onClick={() =>
                          onUpdateItem(item.id, { is_checked: !item.is_checked })
                        }
                        className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-lg border transition ${
                          item.is_checked
                            ? "border-[#2D5A45] bg-[#2D5A45] text-white"
                            : "border-[#CFC6B9] bg-white hover:border-[#2D5A45]"
                        }`}
                      >
                        {item.is_checked && <Check className="h-4 w-4" />}
                      </button>

                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span
                            className={`text-sm font-semibold ${
                              item.is_checked
                                ? "text-[#9AA29D] line-through"
                                : "text-[#1E2421]"
                            }`}
                          >
                            {item.custom_name}
                          </span>
                          <span className="rounded-full bg-[#F2EDE5] px-2 py-0.5 text-[11px] font-bold tabular-nums text-[#1E2421]">
                            {item.to_buy_amount} {item.unit}
                          </span>
                          {!item.manual_addition && item.pack_size > 0 && (
                            <span className="text-[11px] tabular-nums text-[#6B736E]">
                              → {item.suggested_pack_count}× {item.pack_size} {item.unit}
                            </span>
                          )}
                          {item.pantry_deducted_amount > 0 && (
                            <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                              -{item.pantry_deducted_amount} {item.unit} im Vorrat
                            </span>
                          )}
                          {item.added_to_pantry && (
                            <span className="rounded-full bg-[#EBF3EE] px-2 py-0.5 text-[10px] font-semibold text-[#2D5A45]">
                              Im Vorrat ✓
                            </span>
                          )}
                        </div>
                        {item.offer_title && (
                          <p className="mt-0.5 text-[11px] text-emerald-700">
                            Angebot ({item.assigned_store_name}): {item.offer_title}
                            {item.offer_valid_to ? ` · bis ${item.offer_valid_to}` : ""}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2.5">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                          item.price_confidence === "promo"
                            ? "bg-emerald-100 text-emerald-800"
                            : item.price_confidence === "verified"
                            ? "bg-blue-100 text-blue-800"
                            : "bg-[#F2EDE5] text-[#6B736E]"
                        }`}
                      >
                        {item.price_confidence === "promo"
                          ? `Angebot · ${item.assigned_store_name}`
                          : item.price_confidence === "verified"
                          ? "Verifiziert"
                          : `~${item.assigned_store_name}`}
                      </span>

                      {editingPriceId === item.id ? (
                        <form
                          onSubmit={async (e) => {
                            e.preventDefault();
                            const val = parseFloat(priceDraft.replace(",", "."));
                            if (!isNaN(val) && val >= 0) {
                              await onUpdateItem(item.id, { actual_price_eur: val });
                            }
                            setEditingPriceId(null);
                          }}
                          className="flex items-center gap-1"
                        >
                          <input
                            autoFocus
                            type="text"
                            value={priceDraft}
                            onChange={(e) => setPriceDraft(e.target.value)}
                            onBlur={() => setEditingPriceId(null)}
                            className="w-16 rounded-lg border border-[#2D5A45] bg-white px-2 py-1 text-right text-xs font-bold tabular-nums"
                          />
                        </form>
                      ) : (
                        <button
                          type="button"
                          onClick={() => {
                            setEditingPriceId(item.id);
                            setPriceDraft(displayPrice.toFixed(2));
                          }}
                          className="min-w-[64px] rounded-lg px-2 py-1 text-right text-sm font-bold tabular-nums text-[#1E2421] hover:bg-[#F2EDE5]"
                          title="Klicken um tatsächlich gezahlten Preis zu speichern"
                        >
                          {displayPrice.toFixed(2)} €
                        </button>
                      )}

                      {item.manual_addition && (
                        <button
                          onClick={() => onDeleteItem(item.id)}
                          className="rounded-lg p-1 text-[#9AA29D] hover:bg-rose-50 hover:text-rose-600"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
