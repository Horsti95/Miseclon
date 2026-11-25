# Miseclon — Lokaler Meal-Planner & ALDI-Einkaufs-Assistent

Eine lokal gehostete, schlanke Windows-Web-App (inspiriert von **Mise**) ohne Docker-Overhead:
- **Wochenplaner** mit einstellbarer **Personenzahl (1–6)**, **Koch-Einfachheit (Stufe 1–3)**, **Tage**, **Wochenbudget** & **Batch-Cooking**
- **Transparenz pro Mahlzeit** wie in Mise: `kcal`, `Protein`, `Kohlenhydrate` (inkl. Komplexe-KH-% & Ballaststoffe), `Fett` + komplette **Schritt-für-Schritt-Zubereitung**
- **ALDI-Grundzutaten-Katalog (~114+ Fundamentals)** mit geschätzten ALDI-Preisen & Packungsgrößen (alle direkt editierbar) + optionalem **PLZ-Wochenangebots-Sync (Marktguru)**
- **Automatische Einkaufsliste** (`Wochenplan − Vorratsschrank`), nach Supermarkt-Gang gruppiert, inkl. Packungs-Resteverwertung, Ist-Preis-Gedächtnis und Smartphone-Ansicht im WLAN
- **42+ kuratierte High-Protein-/Komplexe-KH-Rezepte** vorinstalliert + **1-Klick-URL-Importer** (z. B. Chefkoch, EatSmarter, REWE) + **lokale KI-Anbindung (Ollama / OpenAI-API auf 24-GB-GPU)**

---

## Schnellstart unter Windows (Out of the Box)

Einfach doppelklicken auf **`start.bat`** (oder in PowerShell `.\start.ps1` ausführen):

```powershell
.\start.ps1
```

Die App öffnet sich automatisch unter **`http://127.0.0.1:8000`**.  
Im selben WLAN kannst du die Einkaufsliste direkt am Smartphone über `http://<DEINE-PC-IP>:8000` öffnen und abhaken.

---

## Lokale KI (Ollama auf 24-GB-VRAM-GPU) verbinden

1. Starte Ollama lokal (z. B. `ollama serve`) und lade ein starkes Modell, z. B.:
   ```powershell
   ollama pull qwen2.5:14b
   ```
   *(Alternativ für 24 GB VRAM: `qwen2.5:32b`, `qwen3:14b` oder `gemma3:27b`)*
2. Öffne in Miseclon den Tab **Einstellungen** → **Lokaler LLM-Server** → **Prüfen**: Alle installierten Modelle werden automatisch erkannt und sind per Klick auswählbar.
3. Danach kannst du sowohl **Wochenpläne mit lokaler KI planen** als auch im Tab **Rezepte → Mit lokaler KI erfinden** neue Rezepte generieren.  
*(Hinweis: Auch wenn Ollama nicht läuft, funktioniert die gesamte App vollständig offline mit dem deterministischen Planer.)*

---

## Entwicklung & Tests

```powershell
# Backend-Tests ausführen
.\.venv\Scripts\pytest.exe

# Frontend neu bauen (falls du Änderungen im UI machst)
cd frontend
npm run build
```

Die gesamte Datenbank liegt in einer einzigen Datei unter `data/mise.db` (Backup = einfach Datei kopieren).
