chiedere se il server grpc cambia farlo nell'utente o nel datacollector, noi l'abbiamo fatto nell'utente e lo stub nel datacollector

Abbiamo fatto in modo che ogni volta che viene aggiunto un nuovo utente, e quest'utente aggiunge una preferenza di aereoporto
la funzione get-flights() viene richiamata per aggiornare il database del datacollector e prendere i dati degli aereoporti nuovi.
Inoltre, get-flights() viene chiamata: o in maniera "forzata" (per debug), o in maniera automatica ogni 12 ottenere
