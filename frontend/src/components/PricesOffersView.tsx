import React, { useMemo, useState } from "react";
import {
  Check,
  RefreshCw,
  Search,
  Store,
  Tag,
  X,
} from "lucide-react";
import { api } from "../api";
import type { AppSettings, Ingredient, Offer } from "../types";

interface PricesOffersViewProps {
  settings: AppSettings;
  ingredients: Ingredient[];
  offers: Offer[];
  onRefreshAll: () => Promise<void>;
}

export const PricesOffersView: React.FC<PricesOffersViewProps> = ({
  settings,
  ingredients,
  offers,
  onRefreshAll,
}) => {
  const [tab, setTab] = useState<"aldi" | "offers">("aldi");
  const [search, setSearch] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [postalInput, setPostalInput] = useState(settings.postal_code);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editPrice, setEditPrice] = useState("");
  const [editPack, setEditPack] = useState("");

  const filteredIngredients = useMemo(() => {
    if (!search.trim()) return ingredients;
    const ql = search.toLowerCase();
    return ingredients.filter(
      (i) =>
        i.name.toLowerCase().includes(ql) || i.category.toLowerCase().includes(ql)
    );
  }, [ingredients, search]);

  const handleSync = async () => {
    setSyncing(true);
    setSyncMessage(null);
    try {
      const res = await api.syncOffers(postalInput || settings.postal_code);
      await onRefreshAll();
      setSyncMessage(
        res.offers_fetched > 0
          ? `Sync (${res.status}): ${res.offers_fetched} Angebote geladen, ${res.matches_created} mit Grundzutaten verknüpft.`
          : `Sync-Hinweis: ${res.error_message || "Aktuell keine Live-Angebote abrufbar – ALDI-Basispreise bleiben aktiv."}`
      );
    } catch (err: any) {
      setSyncMessage(`Sync fehlgeschlagen: ${err?.message || "Unbekannter Fehler"}`);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="space-y-5">
      <section className="rounded-3xl border border-[#E8E2D9] bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-[#1E2421]">
              ALDI-Preiskatalog & PLZ-Angebote
            </h1>
            <p className="text-xs text-[#6B736E]">
              Alle ~{ingredients.length} Grundzutaten mit ALDI-Basispreisen (direkt editierbar) + optionaler Marktguru-Angebots-Sync für deine PLZ.
            </p>
          </div>
          <div className="inline-flex rounded-2xl border border-[#E8E2D9] bg-[#FAF8F5] p-1 text-xs">
            <button
              onClick={() => setTab("aldi")}
              className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 font-semibold ${
                tab === "aldi" ? "bg-[#2D5A45] text-white" : "text-[#5A635E]"
              }`}
            >
              <Store className="h-3.5 w-3.5" />
              ALDI-Basispreise ({ingredients.length})
            </button>
            <button
              onClick={() => setTab("offers")}
              className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 font-semibold ${
                tab === "offers" ? "bg-[#2D5A45] text-white" : "text-[#5A635E]"
              }`}
            >
              <Tag className="h-3.5 w-3.5" />
              Wochenangebote ({offers.length})
            </button>
          </div>
        </div>

        {/* PLZ Live Offer Sync Bar */}
        <div className="mt-4 flex flex-wrap items-center gap-2 rounded-2xl border border-[#EFEAE2] bg-[#FAF8F5] p-3">
          <span className="text-xs font-semibold text-[#4E5752]">
            Wochenangebote abrufen (Marktguru PLZ):
          </span>
          <input
            type="text"
            maxLength={5}
            value={postalInput}
            onChange={(e) => setPostalInput(e.target.value)}
            className="w-24 rounded-xl border border-[#E8E2D9] bg-white px-3 py-1.5 text-xs font-bold tabular-nums"
            placeholder="PLZ"
          />
          <button
            disabled={syncing}
            onClick={handleSync}
            className="inline-flex items-center gap-1.5 rounded-xl bg-[#2D5A45] px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-[#234836] disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? "Lade Angebote…" : "Jetzt aktualisieren"}
          </button>
          {syncMessage && (
            <span className="text-xs font-medium text-[#2D5A45]">{syncMessage}</span>
          )}
        </div>
      </section>

      {tab === "aldi" && (
        <section className="overflow-hidden rounded-3xl border border-[#E8E2D9] bg-white">
          <div className="border-b border-[#EFEAE2] p-4">
            <div className="relative max-w-md">
              <Search className="pointer-events-none absolute top-2.5 left-3 h-4 w-4 text-[#9AA29D]" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Grundzutat suchen (z. B. Reis, Eier, Quark, Hähnchen)…"
                className="w-full rounded-xl border border-[#E8E2D9] bg-[#FAF8F5] py-2 pr-3 pl-9 text-xs focus:border-[#2D5A45] focus:bg-white focus:outline-none"
              />
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-[#EFEAE2] bg-[#FAF8F5] text-[11px] uppercase tracking-wider text-[#6B736E]">
                <tr>
                  <th className="px-4 py-3">Zutat</th>
                  <th className="px-4 py-3">Abteilung</th>
                  <th className="px-4 py-3 text-right">Makros / 100g</th>
                  <th className="px-4 py-3">KH-Typ</th>
                  <th className="px-4 py-3 text-right">Packung</th>
                  <th className="px-4 py-3 text-right">ALDI-Preis</th>
                  <th className="px-4 py-3 text-right">Grundpreis</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F2EDE5]">
                {filteredIngredients.map((ing) => {
                  const isEditing = editingId === ing.id;
                  return (
                    <tr key={ing.id} className="hover:bg-[#FCFBF9]">
                      <td className="px-4 py-2.5 font-semibold text-[#1E2421]">
                        {ing.name}
                        {ing.active_offer_price !== null && (
                          <span className="ml-2 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-800">
                            Angebot {ing.active_offer_price.toFixed(2)} € ({ing.active_offer_store})
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-[#6B736E]">{ing.category}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-[#4E5752]">
                        {Math.round(ing.kcal_100)} kcal · P {ing.protein_100}g · KH{" "}
                        {ing.carbs_100}g
                      </td>
                      <td className="px-4 py-2.5">
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                            ing.carb_type === "complex"
                              ? "bg-emerald-50 text-emerald-800"
                              : ing.carb_type === "mixed"
                              ? "bg-amber-50 text-amber-800"
                              : "bg-[#F2EDE5] text-[#6B736E]"
                          }`}
                        >
                          {ing.carb_type === "complex"
                            ? "Komplex"
                            : ing.carb_type === "mixed"
                            ? "Gemischt"
                            : ing.carb_type === "simple"
                            ? "Einfach"
                            : "Low-Carb"}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums">
                        {isEditing ? (
                          <input
                            type="number"
                            value={editPack}
                            onChange={(e) => setEditPack(e.target.value)}
                            className="w-16 rounded border border-[#2D5A45] px-1.5 py-0.5 text-right font-bold"
                          />
                        ) : (
                          `${ing.default_pack_size} ${ing.default_unit}`
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums">
                        {isEditing ? (
                          <div className="inline-flex items-center gap-1">
                            <input
                              type="text"
                              value={editPrice}
                              onChange={(e) => setEditPrice(e.target.value)}
                              className="w-16 rounded border border-[#2D5A45] px-1.5 py-0.5 text-right font-bold"
                            />
                            <button
                              onClick={async () => {
                                const p = parseFloat(editPrice.replace(",", "."));
                                const pk = parseFloat(editPack);
                                if (!isNaN(p) && p >= 0) {
                                  await api.updateIngredientPrice(ing.id, {
                                    reference_price_eur: p,
                                    default_pack_size: !isNaN(pk) && pk > 0 ? pk : undefined,
                                  });
                                  await onRefreshAll();
                                }
                                setEditingId(null);
                              }}
                              className="rounded bg-[#2D5A45] p-1 text-white"
                            >
                              <Check className="h-3 w-3" />
                            </button>
                            <button
                              onClick={() => setEditingId(null)}
                              className="rounded bg-[#EFEAE2] p-1 text-[#5A635E]"
                            >
                              <X className="h-3 w-3" />
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => {
                              setEditingId(ing.id);
                              setEditPrice(ing.reference_price_eur.toFixed(2));
                              setEditPack(String(ing.default_pack_size));
                            }}
                            className="rounded-lg px-2 py-1 font-bold text-[#1E2421] hover:bg-[#F2EDE5]"
                            title="ALDI-Preis anpassen"
                          >
                            {ing.reference_price_eur.toFixed(2)} €
                          </button>
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-[#6B736E]">
                        {ing.reference_price_per_base_unit.toFixed(2)} €/
                        {ing.default_unit === "g"
                          ? "kg"
                          : ing.default_unit === "ml"
                          ? "l"
                          : "Stk"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {tab === "offers" && (
        <section className="overflow-hidden rounded-3xl border border-[#E8E2D9] bg-white">
          {offers.length === 0 ? (
            <div className="p-10 text-center text-sm text-[#6B736E]">
              Noch keine Live-Wochenangebote geladen. Klicke oben auf{" "}
              <strong>„Jetzt aktualisieren“</strong>, um Prospekt-Angebote für deine PLZ abzurufen.
            </div>
          ) : (
            <div className="divide-y divide-[#F2EDE5]">
              {offers.map((o) => (
                <div
                  key={o.id}
                  className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-[#1E2421] px-2.5 py-0.5 text-[10px] font-bold text-white">
                        {o.store_name}
                      </span>
                      <span className="text-sm font-bold text-[#1E2421]">
                        {o.raw_title}
                      </span>
                      {o.protein_per_euro && o.protein_per_euro >= 15 && (
                        <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-bold text-blue-800">
                          Top-Deal: {o.protein_per_euro}g Protein/€
                        </span>
                      )}
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-[#6B736E]">
                      {o.matched_ingredient_name ? (
                        <span
                          className={
                            o.match_rejected
                              ? "text-rose-600 line-through"
                              : "font-semibold text-[#2D5A45]"
                          }
                        >
                          → Zugeordnet: {o.matched_ingredient_name} (
                          {Math.round((o.match_confidence || 0) * 100)}%)
                        </span>
                      ) : (
                        <span>Nicht automatisch zugeordnet</span>
                      )}
                      {o.valid_to && <span>· Gültig bis {o.valid_to}</span>}
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-right tabular-nums">
                      <div className="text-base font-bold text-[#1E2421]">
                        {o.price_eur.toFixed(2)} €
                      </div>
                      {o.base_price_eur && (
                        <div className="text-[11px] text-[#6B736E]">
                          {o.base_price_eur.toFixed(2)} €/{o.base_unit}
                        </div>
                      )}
                    </div>

                    {o.match_id && (
                      <div className="flex gap-1">
                        <button
                          onClick={async () => {
                            await api.reviewOfferMatch(o.match_id!, "confirm");
                            await onRefreshAll();
                          }}
                          className={`rounded-lg border p-1.5 ${
                            o.match_confirmed
                              ? "border-emerald-300 bg-emerald-100 text-emerald-800"
                              : "border-[#E8E2D9] text-[#5A635E] hover:bg-emerald-50"
                          }`}
                          title="Zuordnung bestätigen"
                        >
                          <Check className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={async () => {
                            await api.reviewOfferMatch(o.match_id!, "reject");
                            await onRefreshAll();
                          }}
                          className={`rounded-lg border p-1.5 ${
                            o.match_rejected
                              ? "border-rose-300 bg-rose-100 text-rose-700"
                              : "border-[#E8E2D9] text-[#5A635E] hover:bg-rose-50"
                          }`}
                          title="Fehlmatch dauerhaft ablehnen"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
};
