# LifeOps Platform

**A comprehensive system for financial and health management based on microservices architecture.**

---

## About the Project

**LifeOps Platform** is a project aimed at the consolidation and containerization of personal life management tools.

**This project is the result of merging two independent systems:**

1. **OCR Receipts App:** A group project based on Flask for scanning receipts and managing shared settlements (refactored into a worker microservice).

2. **Personal Health Dashboard:** A personal FastAPI project integrating with Google Fit (acting as the logical core of the system).

The goal of this integration was to transition from a monolithic architecture to a **distributed microservices architecture**, implement a full **Observability** stack, and automate deployment processes using **Docker Compose**.

---

## System Architecture

The system consists of independent containers communicating within an internal Docker network:

Fragment kodu

```
graph TD
    User[User] -->|HTTP/Upload| Core["Core Dashboard API(FastAPI)"]
    Core -->|Read/Write| DB[(PostgreSQL)]
    Core -->|REST API / Image| Worker["OCR Worker<br/>(Flask + Tesseract)"]
    Worker -->|JSON Data| Core
    Prometheus[Prometheus] -->|Scrape Metrics| Core
    Grafana[Grafana] -->|Query| Prometheus
    Grafana -->|SQL Query| DB
```

### Components

1. **Core Dashboard:**

    - Technology: **FastAPI**

    - Responsibilities: Authentication (JWT), Google Fit API integration, financial logic, transaction management.

    - Exposes metrics for Prometheus (`/metrics`).

2. **OCR Worker:**

    - Technology: **Flask** + **Tesseract OCR** + **OpenCV**

    - Responsibilities: Stateless processing of receipt images. Isolation of heavy computational processes from the main API.

3. **Database:**

    - Technology: **PostgreSQL 15**

    - Role: Central data store for users, transactions, and health metrics.

4. **Monitoring Stack:**

    - **Prometheus:** Collection of technical metrics (API response times, resource usage).

    - **Grafana:** Visualization of business data (Expenses, Steps, Sleep) and system metrics. Replaces the traditional analytics frontend.

---

## Getting Started

### Prerequisites

- Docker & Docker Compose

- `.env` file (configured based on `.env.example`)

### Installation

1. **Clone the repository:**

    Bash

    ```
    git clone https://github.com/your-nick/lifeops-platform.git
    ```

2. **Configure environment variables:**

    - Create a `.env` file in the root directory:

        ```
        POSTGRES_USER=postgres
        POSTGRES_PASSWORD=secretpassword
        POSTGRES_DB=lifeops
        SECRET_KEY=your_jwt_key
        GOOGLE_CLIENT_ID=your_google_id
        GOOGLE_CLIENT_SECRET=your_google_secret
        ```

3. **Start the stack:**

    Bash

    ```
    docker-compose up --build -d
    ```

4. **Service Access:**

    - **App (Upload/Auth):** `http://localhost:8000`

    - **Grafana (Dashboards):** `http://localhost:3000` (Login: `admin` / `admin`)

    - **Prometheus:** `http://localhost:9090`

---

## DevOps Challenges & Solutions

- **Service Integration:** Implemented HTTP communication between `core` and `ocr-worker` containers using internal Docker DNS.

- **Image Optimization:** Used `slim` Python versions and cleaned `apt` cache to reduce image size.

- **Healthchecks:** Configured `depends_on` with `condition: service_healthy` in Docker Compose to ensure the API starts only after the database is ready.

- **Monitoring:** Moved away from hardcoded JS charts to dynamic Grafana dashboards powered directly by SQL and Prometheus.

---

## Roadmap

- [ ] Implement CI/CD with GitHub Actions (automated testing and build).

- [ ] Add Nginx as a Reverse Proxy / Gateway.

- [ ] Cloud deployment (AWS/Azure) using Terraform.

- [ ] Migration to Kubernetes (Minikube).

---

**Author:** Kacper Ślęzak
