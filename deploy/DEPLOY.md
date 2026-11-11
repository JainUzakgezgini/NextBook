# Deploying NextBook on AWS EC2

The live app runs at **https://nextbook.duckdns.org**.

## Architecture

```
Browser --HTTPS--> Nginx (ports 80/443, Let's Encrypt certificate)
                     --> Gunicorn (127.0.0.1:8000, 2 workers, systemd service)
                           --> Flask app --> SQLite (instance/nextbook.db)
                                         --> Google Books API
                                         --> Google Gemini API
```

## AWS setup

- **EC2:** Ubuntu Server 24.04 LTS, t3.micro (Free Tier eligible), region eu-north-1 (Stockholm)
- **Elastic IP:** fixed public address, so the domain keeps working after a restart
- **Security group:** HTTP 80 and HTTPS 443 open to everyone; SSH 22 only from the
  EC2 Instance Connect range for eu-north-1 (13.48.4.200/30)
- **Budget:** monthly cost budget of 10 USD with e-mail alerts
- **Domain:** free subdomain from DuckDNS pointing to the Elastic IP

## Server setup (run once)

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip nginx git certbot python3-certbot-nginx
git clone https://github.com/JainUzakgezgini/NextBook.git nextbook
cd nextbook
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
nano .env                      # SECRET_KEY, GEMINI_API_KEY, GOOGLE_BOOKS_API_KEY,
                               # GEMINI_MODEL, COOKIE_SECURE=1 (never committed to Git)
sudo cp deploy/nextbook.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nextbook
sudo cp deploy/nginx-nextbook.conf /etc/nginx/sites-available/nextbook
sudo ln -sf /etc/nginx/sites-available/nextbook /etc/nginx/sites-enabled/nextbook
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx
sudo certbot --nginx -d nextbook.duckdns.org
```

## Updating the live app

On the development computer:

```bash
git add .
git commit -m "Describe the change"
git push
```

On the server:

```bash
cd ~/nextbook
git pull
source venv/bin/activate && pip install -r requirements.txt   # only if requirements changed
sudo systemctl restart nextbook
```

## Useful commands

```bash
sudo systemctl status nextbook --no-pager      # is the app running?
sudo journalctl -u nextbook -n 50 --no-pager   # latest app logs and warnings
sudo certbot renew --dry-run                   # test certificate renewal
```
