# Buchino
Buchino è un bot telegram ([@buchinobot](https://t.me/buchinobot)) che ti notifica quando si liberano posti per il vaccino in Lombardia.

## Chi sono e perchè ho realizzato questo bot
Sono [Fabio Fontana](https://fabifont.github.io/), studente di informatica presso l'università di Genova.
L'idea della realizzazione di questo bot è nata mentre cercavo di prenotare il vaccino e le prime date disponibili erano lontane di almeno un mese. Alcune persone mi hanno detto che giornalmente vengono disdetti molti appuntamenti ma non avevo il tempo di controllare ogni ora se fosse comparsa una nuova data disponibile. Così cercando online ho visto che [Alberto Granzotto](https://www.granzotto.net/) aveva sviluppato un bot che controllava le date disponibili in Veneto ([@Serenissimobot](https://t.me/serenissimo_bot)). A quel punto ho deciso di realizzare un servizio simile per la Lombardia, da qui `Buchino`. Buchino funziona leggermente diversamente da Serenissimo in quanto i siti delle regioni sono diversi.

Per i più esperti:
Le API del sito della regione Lombardia sono protette da RecaptchaV3, il quale non permette l'utilizzo tramite semplici richieste HTTP (a differenza del sito del Veneto). Non avevo intenzione di implementare un captcha solver, anche perchè generalmente sono lenti e a pagamento. Perciò ho deciso di fare scraping con Selenium con Firefox in modalità headless.
Questo ovviamente ha un grande impatto sulla velocità del controllo che è notevolmente ridotta.


## Dati richiesti
Buchino controlla la disponibilità di un appuntamento per il vaccino al tuo posto, perciò ha bisogno dei seguenti dati richiesti dal [sito ufficiale della regione Lombardia](https://start.prenotazionevaccinicovid.regione.lombardia.it):
- numero tessera sanitaria
- codice fiscale
- provincia
- comune
- cap
- numero di telefono

### Informativa sulla privacy
- i dati vengono utilizzati ESCLUSIVAMENTE per controllare la disponibilità di un appuntamento per la vaccinazione sul sito https://start.prenotazionevaccinicovid.regione.lombardia.it
- è possibile cancellare tutti i dati con il comando `/cancella`
- il codice del bot è opensource e chiunque può verificarne il funzionamento

## Comandi e funzionamento
Di seguito sono elencati i comandi che puoi utilizzare nel bot:
- `/start`: avvia il bot (non la ricerca)
- `/registra`: avvia il processo di registrazione
- `/annulla`: annulla il processo di registrazione
- `/stop`: termina la ricerca e disabilita le notifiche
- `/reset`: abilita nuovamente le notifiche
- `/cancella`: cancella tutti i tuoi dati
- `/info`: stampa tutti i comandi ed informazioni aggiuntive

Quando un utente viene registato i suoi dati vengono salvati in un database per essere riutilizzati per la ricerca.
Per ogni utente salvato nel database, in modo sequenziale, viene effettuata la ricerca dei posti.
Se l'utente ha già prenotato un appuntamento le sue notifiche saranno disabilitate in quanto non è permesso cercare altre date (a patto che si annulli la prenotazione precedente).
Per questo se si decidesse di annullare la prenotazione è necessario segnalarlo al bot in modo che questo possa tornare nuovamente ad effettuare la ricerca per tale utente.


## Come contribuire

### Requisiti
Per contribuire allo sviluppo e al miglioramento del bot è richiesto:
- `firefox`
- `geckodriver`
- `mongodb`

Inoltre sono necessarie le sequenti dipendenze in Python:
- `selenium`
- `numpy`
- `aiogram`
- `mongoengine`
- `codicefiscale`
- `phonenumbers`

### Eseguire Buchino
1. Avviare mongodb: `systemctl start mongodb`
2. Lanciare `init.py` per inserire i dati statici come province, comuni e CAP (solo la prima volta):
   ```
   python3 -c "from init import init_places();init_places()"
   ```
3. Creare il file `config.ini` basandosi su `config.ini.example` e inserendo il token del proprio bot
4. Lanciare `main.py` per eseguire buchino: `python3 main.py`


### Offrimi un caffè
[![paypal](https://www.paypalobjects.com/en_US/IT/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=4MQQGEC9RVDD2)
