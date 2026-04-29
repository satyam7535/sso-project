#!/bin/bash
# =============================================================
# deploy.sh — EC2 Deployment Script for SSO Microservices
# =============================================================
# Usage: chmod +x deploy.sh && sudo ./deploy.sh <service_name>
# Where <service_name> is: auth_service, app1, or app2
# =============================================================

set -e

SERVICE=$1

if [[ "$SERVICE" != "auth_service" && "$SERVICE" != "app1" && "$SERVICE" != "app2" ]]; then
    echo "Usage: sudo ./deploy.sh <service_name>"
    echo "Valid services: auth_service, app1, app2"
    exit 1
fi

echo "=========================================="
echo "  Deploying $SERVICE..."
echo "=========================================="

echo "=========================================="
echo "  Updating system packages..."
echo "=========================================="
apt update && apt upgrade -y

echo "=========================================="
echo "  Installing system dependencies..."
echo "=========================================="
apt install -y python3 python3-pip python3-venv nginx pkg-config \
    libpq-dev postgresql postgresql-contrib build-essential git

echo "=========================================="
echo "  Setting up project directory..."
echo "=========================================="
PROJECT_DIR="/home/ubuntu/project"
SERVICE_DIR="$PROJECT_DIR/$SERVICE"

# In a real scenario, you'd clone your repo here.
# For now, we assume the code is already transferred to $PROJECT_DIR
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: Project directory $PROJECT_DIR not found."
    echo "Please clone your repository to $PROJECT_DIR first."
    exit 1
fi

cd $SERVICE_DIR

echo "=========================================="
echo "  Setting up Python virtual environment..."
echo "=========================================="
python3 -m venv venv
source venv/bin/activate

echo "=========================================="
echo "  Installing Python dependencies..."
echo "=========================================="
pip install --upgrade pip
pip install -r requirements.txt
# Ensure gunicorn is installed
pip install gunicorn

echo "=========================================="
echo "  Setting up .env file..."
echo "=========================================="
if [ ! -f .env ]; then
    echo "Warning: .env file not found in $SERVICE_DIR."
    echo "Please create it with production values."
    # Creating a placeholder
    if [ "$SERVICE" == "auth_service" ]; then
        cat > .env <<EOF
SECRET_KEY=prod-auth-secret
DEBUG=False
TOKEN_EXPIRY_MINUTES=30
ALLOWED_HOSTS=*
DATABASE_URL=postgres://user:pass@rds-endpoint:5432/dbname
EOF
    elif [ "$SERVICE" == "app1" ]; then
        cat > .env <<EOF
SECRET_KEY=prod-app1-secret
DEBUG=False
AUTH_SERVICE_URL=http://<auth-ec2-ip>:8000
APP2_URL=http://<app2-ec2-ip>:8002
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
SSO_COOKIE_DOMAIN=.yourdomain.com
ALLOWED_HOSTS=*
EOF
    elif [ "$SERVICE" == "app2" ]; then
        cat > .env <<EOF
SECRET_KEY=prod-app2-secret
DEBUG=False
AUTH_SERVICE_URL=http://<auth-ec2-ip>:8000
APP1_LOGIN_URL=http://<app1-ec2-ip>:8001/login/
ALLOWED_HOSTS=*
EOF
    fi
    echo ".env template created. Update it before running!"
fi

echo "=========================================="
echo "  Running database migrations..."
echo "=========================================="
python manage.py migrate

echo "=========================================="
echo "  Collecting static files..."
echo "=========================================="
python manage.py collectstatic --noinput

echo "=========================================="
echo "  Setting up Systemd Service for Gunicorn..."
echo "=========================================="
PORT=8000
if [ "$SERVICE" == "app1" ]; then
    PORT=8001
elif [ "$SERVICE" == "app2" ]; then
    PORT=8002
fi

cat > /etc/systemd/system/gunicorn-$SERVICE.service <<EOF
[Unit]
Description=gunicorn daemon for $SERVICE
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=$SERVICE_DIR
ExecStart=$SERVICE_DIR/venv/bin/gunicorn --access-logfile - --workers 3 --bind 0.0.0.0:$PORT $SERVICE.wsgi:application

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl start gunicorn-$SERVICE
systemctl enable gunicorn-$SERVICE

echo "=========================================="
echo "  Setting up Nginx..."
echo "=========================================="
# Using the pre-created nginx.conf if available, otherwise creating a simple one
if [ -f "$PROJECT_DIR/nginx.conf" ]; then
    cp "$PROJECT_DIR/nginx.conf" /etc/nginx/sites-available/$SERVICE
else
    cat > /etc/nginx/sites-available/$SERVICE <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static/ {
        alias $SERVICE_DIR/staticfiles/;
    }
}
EOF
fi

ln -sf /etc/nginx/sites-available/$SERVICE /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
systemctl enable nginx

echo "=========================================="
echo "  Deployment complete for $SERVICE!"
echo "  Service running on port $PORT via Nginx on port 80"
echo "=========================================="
