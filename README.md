# Microservices SSO Platform

A robust Single Sign-On (SSO) ecosystem consisting of three Django microservices, integrating native authentication and Google OAuth.

---

## 🏗 Architecture

The platform uses a centralized authentication service and distributed applications that rely on a shared SSO cookie.

1.  **Auth Service (Port 8000):** 
    *   The central authority and database owner (PostgreSQL/SQLite).
    *   Exposes REST APIs: `/auth/register`, `/auth/login`, `/auth/validate`, `/auth/logout`.
    *   Manages user credentials and session tokens.
2.  **App 1 - Main App (Port 8001):**
    *   The primary user-facing interface for authentication.
    *   Handles native login/registration forms and Google OAuth integration via `django-allauth`.
    *   Communicates with the Auth Service to obtain tokens.
    *   Sets the `sso_token` HTTP-only cookie in the user's browser.
3.  **App 2 - Secondary App (Port 8002):**
    *   A protected application without its own login system.
    *   Reads the `sso_token` cookie on every request.
    *   Validates the token against the Auth Service via backend API calls.
    *   Grants access or redirects to App 1 for login.

---

## 🚀 Local Development Setup

### 1. Prerequisites
Ensure you have Python 3.8+ and PostgreSQL (optional for local, SQLite is default) installed.

### 2. Project Setup
```bash
git clone <your-repository-url>
cd project
```

### 3. Virtual Environment
It is recommended to use the shared virtual environment at the root level for local development.
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 4. Install Dependencies
Install dependencies for all services.
```bash
pip install -r auth_service/requirements.txt
pip install -r app1/requirements.txt
pip install -r app2/requirements.txt
```

### 5. Environment Variables
Create `.env` files in each service directory (`auth_service/`, `app1/`, `app2/`). 
*Placeholder `.env` files are already provided. Ensure `AUTH_SERVICE_URL`, `APP2_URL`, and `APP1_LOGIN_URL` match your local ports.*

### 6. Run Migrations
Run migrations for all three services.
```bash
cd auth_service && python manage.py migrate && cd ..
cd app1 && python manage.py migrate && cd ..
cd app2 && python manage.py migrate && cd ..
```

### 7. Start the Services
You will need three separate terminal windows, all with the virtual environment activated.

**Terminal 1 (Auth Service):**
```bash
cd auth_service
python manage.py runserver 8000
```

**Terminal 2 (App 1):**
```bash
cd app1
python manage.py runserver 8001
```

**Terminal 3 (App 2):**
```bash
cd app2
python manage.py runserver 8002
```

---

## ☁️ AWS Deployment Setup (Cloud-Native)

The deployment architecture uses one RDS instance for the database and three separate EC2 instances for the services.

### 1. Security Groups & Infrastructure (Crucial)
Properly configuring AWS Security Groups is essential to prove a cloud-native architecture:

1.  **RDS Security Group:** 
    *   Create a Security Group for your PostgreSQL RDS.
    *   **Inbound Rule:** Allow PostgreSQL (Port 5432) traffic originating *only* from the Security Groups of your three EC2 instances. Do not open to `0.0.0.0/0`.
2.  **Auth Service EC2 Security Group:**
    *   **Inbound Rule 1:** Allow Custom TCP (Port 8000) traffic originating *only* from the Security Groups of App 1 and App 2.
    *   **Inbound Rule 2:** Allow HTTP (Port 80) and HTTPS (Port 443) from `0.0.0.0/0` (if serving Auth API publicly).
3.  **App 1 & App 2 EC2 Security Groups:**
    *   **Inbound Rule:** Allow HTTP (Port 80) and HTTPS (Port 443) from `0.0.0.0/0`.
    *   **Outbound Rule:** All traffic allowed (default).

### 2. AWS Cookie Domain Strategy
For SSO to function across different EC2 instances, the browser needs to share the `sso_token` cookie. Since EC2 public IPs cannot share cookies, you must use one of these strategies for your Lab Demo:

*   **Strategy A (The "Hosts File" Method):** Map the public IPs of your EC2 instances to local test domains on your personal computer by editing your `hosts` file (e.g., mapping IPs to `auth.test`, `app1.test`, `app2.test`). Set `SSO_COOKIE_DOMAIN=.test` in App 1's `.env`.
*   **Strategy B (Free DNS):** Use a service like duckdns.org to create subdomains (e.g., `sso-app1.duckdns.org`, `sso-app2.duckdns.org`) pointing to your EC2 IPs. Set `SSO_COOKIE_DOMAIN=.duckdns.org` in App 1's `.env`.

### 3. Deployment Steps (Per Instance)
SSH into each instance and follow these steps.

1.  **Clone code:** Clone the repository to `/home/ubuntu/project`.
2.  **Configure `.env`:** Navigate to the specific service directory (e.g., `cd /home/ubuntu/project/auth_service`) and create/update the `.env` file with production values.
    *   **Auth Service:** Set `DATABASE_URL` to your RDS endpoint and define an `INTERNAL_SSO_KEY`.
    *   **App 1:** Set `AUTH_SERVICE_URL` to the public IP/domain of the Auth Service EC2 instance. Set `INTERNAL_SSO_KEY` to match the Auth Service. Set `SSO_COOKIE_DOMAIN` based on your chosen strategy above.
    *   **App 2:** Set `AUTH_SERVICE_URL` and `APP1_LOGIN_URL`.
3.  **Run Deploy Script:**
    ```bash
    cd /home/ubuntu/project
    chmod +x deploy.sh
    
    # For Auth Service instance:
    sudo ./deploy.sh auth_service
    
    # For App 1 instance:
    sudo ./deploy.sh app1
    
    # For App 2 instance:
    sudo ./deploy.sh app2
    ```

---

## 🛠 Cloud-Native Features Included

*   **SSO Middleware (App 2):** Instead of repeating token validation logic in every view, App 2 uses a custom Django Middleware (`SSOMiddleware`) to intercept all requests, validate the cookie against the Auth Service, and automatically attach user details to the request or redirect unauthenticated users.
*   **Token Synchronization (Server-to-Server Trust):** When a user logs in via Google on App 1, App 1 securely registers/logs them into the Auth Service via a dedicated `/auth/sso-login` endpoint using a shared `INTERNAL_SSO_KEY`. This avoids generating "placeholder passwords" and adheres to strict server-to-server trust mechanisms.
*   **Lazy Token Cleanup:** The Auth Service's token validation endpoint implements a "lazy cleanup" algorithm. 10% of the time, it automatically runs a background query to purge expired tokens from the database, preventing infinite table growth without requiring a separate EC2 Cron job. (A management command `python manage.py cleanup_tokens` is also available for manual purging).
*   **CORS Protection:** The Auth Service utilizes `django-cors-headers` to manage cross-origin requests securely.

---

## 🔑 Google SSO Setup (App 1)

1. Go to [Google Cloud Console](https://console.cloud.google.com).
2. Create a new project.
3. Go to **APIs & Services -> Credentials**.
4. Create an **OAuth 2.0 Client ID** (Web application).
5. Add Authorized Redirect URIs:
   *   Local: `http://localhost:8001/accounts/google/login/callback/`
   *   Production: `http://<your-app1-domain>/accounts/google/login/callback/`
6. Copy the **Client ID** and **Client Secret**.
7. Update the `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `app1/.env`.
8. In the **App 1 Django Admin** (`/admin`), configure the Site and Social Application settings for Google as required by `django-allauth`.

---

## 🧪 Testing the SSO Flow

1. Open **App 1** (`http://localhost:8001`). Register or Login.
2. Upon successful login, you will be on the App 1 Dashboard.
3. Open a new tab and navigate to **App 2** (`http://localhost:8002`).
4. You should be automatically granted access without logging in.
5. Wait 30 minutes (or manually delete the token from the DB), and refresh App 2. You should be redirected to the App 1 login page.
6. Click "Sign Out" on App 1, then try to visit App 2. You should be redirected to the login page.
