
## Quick Start

```bash
docker-compose up --build 
```

**Porte**: User Manager 5000 | Data Collector 5001 | PostgreSQL 5432

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
| POST | `/register_airports` | 5001 | `{email, airports: []}` |
| GET | `/user_info/<email>` | 5001 | - |
| GET | `/airports/<code>/last_flight` | 5001 | - |
| GET | `/airports/<code>/average_flights?days=7` | 5001 | - |
| GET | `/airports/<code>/busiest_hour` | 5001 | - |

## Testing rapido (curl)

```bash
# Aggiungi utente
curl -X POST http://localhost:5000/addUser \
  -H "Content-Type: application/json" \
  -d '{"message_id":"1","email":"test@example.com","name":"Test","surname":"User","fiscal_code":"ABC123","bank_info":"IT123"}'

# Leggi utenti
curl http://localhost:5000/users

# Registra aeroporti
curl -X POST http://localhost:5001/register_airports \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","airports":["LIRF","LIMC"]}'

# Info utente
curl http://localhost:5001/user_info/test@example.com

# Ultimi voli
curl http://localhost:5001/airports/LIRF/last_flight

# Media voli
curl "http://localhost:5001/airports/LIRF/average_flights?days=7"

# Ora più trafficata
curl http://localhost:5001/airports/LIRF/busiest_hour
```

## Arresto

```bash
docker-compose down      # Ferma i container
docker-compose down -v   # Ferma e rimuove volumi (reset)
```

## Database

- **userdb** (User Manager): users, message_ids
- **datadb** (Data Collector): user_airports, flights
- PostgreSQL: `postgresql://user:password@postgres:5432/`

