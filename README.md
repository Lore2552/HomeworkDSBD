## Description
Homework3 del corso Distributed Systems and Big data svolto presso l'Università degli Studi di Catania.
Questa versione introduce un'architettura completamente basata su **Kubernetes**, con orchestrazione tramite **Kind**, monitoraggio con **Prometheus**, e comunicazione asincrona via **Kafka (KRaft)**.

## Prerequisiti
- Docker
- Kind (Kubernetes in Docker)
- Kubectl

## Quick Start (Kubernetes)

1. **Creare il cluster**:
   ```bash
   kind create cluster --config kind-config.yaml
   ```

2. **Build delle immagini Docker**:
   ```bash
   docker build -t homework3-user-manager:latest -f user-manager/Dockerfile .
   docker build -t homework3-data-collector:latest -f data-collector/Dockerfile .
   docker build -t homework3-alert-system:latest -f alert-system/Dockerfile .
   docker build -t homework3-alert-notifier-system:latest -f alert-notifier-system/Dockerfile .
   ```

3. **Caricare le immagini nel cluster Kind**:
   ```bash
   kind load docker-image homework3-user-manager:latest
   kind load docker-image homework3-data-collector:latest
   kind load docker-image homework3-alert-system:latest
   kind load docker-image homework3-alert-notifier-system:latest
   ```

4. **Configurare i Secret**:
   Prima di applicare i manifest, assicurarsi di aver compilato il file `k8s/secrets.yaml` con le credenziali in Base64 (OpenSky API, SMTP Password, DB Password).

5. **Applicare i Manifest**:
   ```bash
   kubectl apply -f k8s/secrets.yaml
   kubectl apply -f k8s/
   ```

## Accesso ai Servizi

L'accesso al cluster avviene tramite **NGINX Ingress Controller** esposto come NodePort.

| Servizio | URL | Descrizione |
|----------|-----|-------------|
| **API Gateway (HTTP)** | `http://localhost:30080` | Punto di ingresso per tutte le API |
| **API Gateway (HTTPS)** | `https://localhost:30443` | Punto di ingresso sicuro |
| **Prometheus** | `http://localhost:30090` | Dashboard di monitoraggio metriche |
| **Prometheus (via Proxy)** | `http://localhost:30080/prometheus/` | Accesso alternativo via NGINX |

## Endpoint Quick Reference

Tutte le chiamate vanno effettuate verso la porta **30080** (o 30443).

| Metodo | Endpoint | Body |
|--------|----------|------|
| POST | `/addUser` | `{message_id, email, name, surname, fiscal_code, bank_info}` |
| GET | `/users` | - |
| DELETE | `/deleteUser` | `{email}` |
| DELETE | `/removeAirportInterest` | `{email, airport_code}` |
| POST | `/register_airports` | `{email, airports: [{code, high_value, low_value}]}` |
| DELETE | `/airports/deleteThresholds` | `{email, airport_code}` |
| GET | `/user_info/<email>` | - |
| GET | `/airports/<code>/last_flight` | - |
| GET | `/airports/<code>/average_flights?days=7` | - |
| GET | `/airports/<code>/busiest_hour` | - |

## Testing (Postman)
1. Importare `postman_test_data.json` in Postman.
2. Assicurarsi che la variabile `baseUrl` nella collection punti a `http://localhost:30080`.

## Monitoraggio
Il sistema espone metriche Prometheus per i servizi principali:
- **User Manager**: Errori registrazione, messaggi puliti, durata cleanup.
- **Data Collector**: Voli raccolti, errori collezione, durata chiamate API.

## Arresto

```bash
kubectl delete -f k8s/       # Rimuove le risorse
kind delete cluster          # Elimina il cluster intero
```

## Database
- **PostgreSQL**: Accessibile internamente al cluster come `postgres:5432`.
- **Database**: `userdb` (User Manager), `datadb` (Data Collector).

