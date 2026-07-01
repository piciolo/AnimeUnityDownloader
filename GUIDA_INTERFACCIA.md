# AnimeUnity Downloader — Interfaccia grafica

Versione con **interfaccia grafica** del downloader: cerchi e sfogli gli anime
direttamente collegandoti ad AnimeUnity, scegli gli episodi con un clic e li scarichi,
il tutto **senza usare comandi Python o il terminale**.

L'interfaccia ha un tema scuro moderno: barra di ricerca in alto, griglia di copertine,
scheda dettaglio con lista episodi e una scheda "Download" con le barre di avanzamento.

## Cosa puoi fare

- 🔎 **Cercare** un anime per titolo (collegamento diretto al sito).
- 🔥 **Sfogliare** il catalogo per *Popolari*, *Più visti* o *Migliori*.
- 🇮🇹 Filtrare solo gli anime **doppiati in italiano** (DUB).
- 📺 Aprire una scheda con **trama, copertina e lista episodi**.
- ✅ Selezionare **singoli episodi**, **tutti** o un **intervallo** (es. dal 5 al 12).
- ⬇️ Scaricare in **parallelo** con **barra di avanzamento**, velocità e possibilità di
  **annullare** ogni download.
- 📁 Scegliere la **cartella di destinazione** (viene ricordata al riavvio).

I file vengono salvati come `Nome Anime - Ep 01 [1080p].mp4` dentro una sottocartella
con il nome dell'anime.

## Come avviare l'app

### Opzione A — Eseguibile (consigliata, zero configurazione)

1. Genera l'eseguibile una sola volta (vedi sotto), oppure usa quello già presente in
   `dist/`.
2. Fai **doppio clic** su `dist/AnimeUnity Downloader.exe`. Fine: nessun terminale.

### Opzione B — Avvio rapido con doppio clic (senza creare l'exe)

Fai doppio clic su **`Avvia AnimeUnity.bat`**. Apre direttamente la finestra
(usa `pythonw`, quindi non compare alcuna finestra nera del prompt).

### Opzione C — Da Python (per chi sviluppa)

```bash
pip install -r requirements-gui.txt
python app.py
```

## Come creare l'eseguibile (.exe)

Serve solo la prima volta. Da terminale, nella cartella del progetto:

```bash
pip install pyinstaller
python build_exe.py
```

Al termine troverai il file **`dist/AnimeUnity Downloader.exe`**: puoi spostarlo dove
vuoi (Desktop, chiavetta, ecc.) e lanciarlo con un doppio clic. Non richiede Python
installato sul PC di destinazione.

> Suggerimento: per dare all'exe un'icona personalizzata, metti un file
> `assets/logo.ico` accanto al `logo.png` prima di lanciare `build_exe.py`.

## Come si usa

1. All'avvio vedi già gli anime **Popolari**.
2. Scrivi un titolo nella barra e premi **Invio** (o **Cerca**). Puoi cambiare
   l'ordinamento e attivare **Solo DUB (ITA)**.
3. Clicca su una copertina per aprire la **scheda dell'anime**.
4. Spunta gli episodi che vuoi. Per fare presto usa **Seleziona tutti** oppure imposta
   **Dal … al …** e premi **Seleziona intervallo**.
5. Premi **⬇ Scarica selezionati**: passi in automatico alla scheda **Download**.
6. Nella scheda **Download** vedi l'avanzamento di ognuno; puoi **Annullare** un
   download in corso o **Rimuovere** quelli finiti. Con **Simultanei** regoli quanti
   download avvengono contemporaneamente.

## Note

- L'app riusa la stessa logica di download del tool a riga di comando originale
  (`anime_downloader.py`), che continua a funzionare come prima.
- Se un download fallisce per motivi di rete, puoi semplicemente riavviarlo: gli
  episodi già scaricati vengono riconosciuti e saltati (segnati come "Già presente").
- Requisiti runtime dell'interfaccia: solo `PySide6` e `httpx`
  (vedi `requirements-gui.txt`).
