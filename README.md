# Mini-Projet Cloud Computing — Docker Microservices Platform

A production-ready microservices architecture built with Docker Compose, featuring a Flask REST API, PostgreSQL, Redis caching, Nginx reverse proxy, and Prometheus/Grafana monitoring.

## Architecture

```
                         ┌─────────────────┐
                         │   Nginx (:80)   │
                         │  Reverse Proxy  │
                         └────────┬────────┘
                                  │
                  ┌───────────────┼───────────────┐
                  │               │               │
           ┌──────┴──────┐ ┌─────┴───────┐ ┌─────┴───────┐
           │  Flask App  │ │  Flask App  │ │  Flask App  │
           │  Instance 1 │ │  Instance 2 │ │  Instance 3 │
           └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
                  │               │               │
         ┌────────┴───────────────┴───────────────┴────────┐
         │                                                 │
   ┌─────┴──────┐                                   ┌──────┴─────┐
   │ PostgreSQL │                                   │   Redis    │
   │   (:5432)  │                                   │  (:6379)   │
   └────────────┘                                   └────────────┘

   ┌──────────────┐         ┌──────────────┐
   │  Prometheus  │────────▶│   Grafana    │
   │   (:9090)    │         │   (:3000)    │
   └──────────────┘         └──────────────┘
```

## Services

| Service    | Image              | Port | Description                              |
|------------|--------------------|------|------------------------------------------|
| nginx      | nginx:alpine       | 80   | Reverse proxy & load balancer            |
| app        | flask-app (custom) | 5000 | Flask TODO REST API (scalable)           |
| db         | postgres:14        | 5432 | PostgreSQL database                      |
| redis      | redis:7-alpine     | 6379 | Cache (30s TTL) & atomic visit counter   |
| prometheus | prom/prometheus    | 9090 | Metrics collection (scrapes every 15s)   |
| grafana    | grafana/grafana    | 3000 | Metrics visualization & dashboards       |

## Quick Start

### Start all services
```bash
docker compose up -d --build
```

### Scale Flask app to 3 instances
```bash
docker compose up -d --scale app=3
```

### Check service status
```bash
docker compose ps
```

### View logs
```bash
docker compose logs -f app
```

### Stop all services
```bash
docker compose down
```

### Stop and remove volumes
```bash
docker compose down -v
```

## API Endpoints

| Method | Endpoint       | Description                              |
|--------|----------------|------------------------------------------|
| GET    | /              | App info + visit counter + hostname      |
| GET    | /tasks         | List all tasks (cached in Redis, 30s TTL)|
| POST   | /tasks         | Create a task `{title, description}`     |
| PUT    | /tasks/\<id\>  | Update a task (title, description, done) |
| DELETE | /tasks/\<id\>  | Delete a task                            |
| GET    | /health        | Health check (DB + Redis connectivity)   |
| GET    | /metrics       | Prometheus metrics endpoint              |

### Example Requests (Linux/macOS)

```bash
# Get app info
curl http://localhost/

# List tasks
curl http://localhost/tasks

# Create a task
curl -X POST http://localhost/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "New task", "description": "Task description"}'

# Update a task
curl -X PUT http://localhost/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"done": true}'

# Delete a task
curl -X DELETE http://localhost/tasks/1
```

### Example Requests (PowerShell)

```powershell
# Get app info
Invoke-RestMethod -Uri http://localhost/

# List tasks
Invoke-RestMethod -Uri http://localhost/tasks

# Create a task
Invoke-RestMethod -Method POST -Uri http://localhost/tasks -ContentType "application/json" -Body '{"title":"New task","description":"Task description"}'

# Update a task
Invoke-RestMethod -Method PUT -Uri http://localhost/tasks/1 -ContentType "application/json" -Body '{"done":true}'

# Delete a task
Invoke-RestMethod -Method DELETE -Uri http://localhost/tasks/1
```

## Access URLs

| Service    | URL                          | Credentials  |
|------------|------------------------------|--------------|
| API        | http://localhost              | —            |
| Prometheus | http://localhost:9090         | —            |
| Grafana    | http://localhost:3000         | admin/admin  |

## Monitoring

- **Prometheus** scrapes the Flask `/metrics` endpoint every 15s via DNS service discovery
- Metrics exposed:
  - `http_requests_total` — counter by method, endpoint, status
  - `http_request_duration_seconds` — histogram of response times
  - `visit_count_total` — total visits to the home page
- **Grafana** has Prometheus auto-provisioned as a datasource

### Suggested Grafana Queries

| Panel                | PromQL Query                                                              |
|----------------------|---------------------------------------------------------------------------|
| Request Rate         | `rate(http_requests_total[1m])`                                           |
| P95 Response Time    | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))` |
| Total Visits         | `visit_count_total`                                                       |
| Requests by Endpoint | `sum by (endpoint) (rate(http_requests_total[1m]))`                       |
| Error Rate (5xx)     | `sum(rate(http_requests_total{status=~"5.."}[1m]))`                       |

## Scalability

The platform supports horizontal scaling of the Flask app:

```bash
docker compose up -d --scale app=3
```

Nginx uses Docker's internal DNS resolver (`127.0.0.11`) to dynamically discover all Flask instances and distribute traffic across them. Hit `GET /` multiple times to see different hostnames in the response, confirming load balancing is working.

## Project Structure

```
mini-projet-cloud/
├── docker-compose.yml          # All services, networks, volumes
├── flask-app/
│   ├── app.py                  # Flask REST API
│   ├── Dockerfile              # Python 3.11 + gunicorn
│   ├── requirements.txt        # Python dependencies
│   └── .dockerignore
├── nginx/
│   └── nginx.conf              # Reverse proxy + rate limiting
├── db/
│   └── init.sql                # Schema + seed data (3 tasks)
├── prometheus/
│   └── prometheus.yml          # Scrape config
├── grafana/
│   └── provisioning/
│       └── datasources/
│           └── prometheus.yml  # Auto-provisioned datasource
├── .github/
│   └── workflows/
│       └── ci-cd.yml           # Build, push, test pipeline
├── .gitignore
└── README.md
```
