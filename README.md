## Description
Homework2 del corso Distributed Systems and Big data svolto verso l'università degli studi di Catania.

## Quick Start

```bash
docker-compose up --build 
```

**Porte**: User Manager 5000 | Data Collector 5001 | PostgreSQL 5432
## File ENV
Per testare le chiamate API, è necessaria l'aggiunta di un file .env che contenga le credenziali generate dall'API: OPENSKY_CLIENT_ID = "", e OPENSKY_CLIENT_SECRET = ""
Anche per le email SMTP va compilato il campo: SMTP_PASSWORD = ""
## Testing (Postman)

1. Import `postman_test_data.json` in Postman
2. Test endpoints (esempi sotto)

## Endpoint Quick Reference

| Metodo | Endpoint | Porta | Body |
|--------|----------|-------|------|
| POST | `/addUser` | 5000 | `{message_id, email, name, surname, fiscal_code, bank_info}` |
| GET | `/users` | 5000 | - |
| DELETE | `/deleteUser` | 5000 | `{email}` |
| DELETE | `/removeAirportInterest` | 5000 | `{email, airport_code}` |
| POST | `/register_airports` | 5001 | `{email, airports: [{code, high_value, low_value}]}` |
| DELETE | `/airports/deleteThresholds` | 5001 | `{email, airport_code}` |
| GET | `/user_info/<email>` | 5001 | - |
| GET | `/airports/<code>/last_flight` | 5001 | - |
| GET | `/airports/<code>/average_flights?days=7` | 5001 | - |
| GET | `/airports/<code>/busiest_hour` | 5001 | - |


## Arresto

```bash
docker-compose down      # Ferma i container
docker-compose down -v   # Ferma e rimuove volumi (reset)
```

## Database

- **userdb** (User Manager): users, message_ids
- **datadb** (Data Collector): user_airports, flights
- PostgreSQL: `postgresql://user:password@postgres:5432/`

