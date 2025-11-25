chiedere se il server grpc cambia farlo nell'utente o nel datacollector, noi l'abbiamo fatto nell'utente e lo stub nel datacollector

Abbiamo fatto in modo che ogni volta che viene aggiunto un nuovo utente, e quest'utente aggiunge una preferenza di aereoporto
la funzione get-flights() viene richiamata per aggiornare il database del datacollector e prendere i dati degli aereoporti nuovi.
Inoltre, get-flights() viene chiamata: o in maniera "forzata" (per debug), o in maniera automatica ogni 12 ottenere

-da fare: rendi più modulare il codice

COSE DA AGGIUSTARE:

1. Trikki aeroporto (vedi mess importante)
2. ⁠At most once (vedi registrazione)
3. ⁠Documentazione
4. ⁠Un utente puo togliere gli interessi
5. ⁠abbissare versioni in requirements.txt
6. da controllare meglio la creazione del server grpc
7. aggiungere più errori per duplicazione eventuale di iban o codice fiscale(tipo cod fiscale già registrato o iban già registrato)
8. Controllare creazione e gestione dei thread (tipo per richiedere gli areoporti, se abbiamo + thread è meglio per ogni richiesta)
9. Vedere meglio cosa restituisce l'api perchè volendo si può far restituire solo alcune informazioni utili e non tutte quelle che stampiamo noi
10. Fare meglio i filtri delle query per averli più puliti
11. aggiungere richiesta http per restituire aereoporti per ICAO e il loro conto (pre vedere se effettivamente li prende tutti)
12. volendo, al posto di fare un while true, possiamo usare uno scheduler che ogni 12 ore avvia la raccolta dati
13. Chiedere a morana se il grpc channel va fatto bilaterale
14. Chiedere se è meglio fare due container o due db separati
15. aggiustare il fatto che abbiamo 10 thread forse non ha senso ed è inefficiente
16. aggiungere il fatto che se un utente viene eliminato si eliminano gli interessi e viene ripopolato il db dei voli (forse)
17. Mettere i thread daemon (che si cancellano da soli appena finiscono o chiudi)
18. Fare meglio le query sql (db.execute,db.select ecc)
19. Fare classi per rendere il codice modulare (tipo la richiesta del token)