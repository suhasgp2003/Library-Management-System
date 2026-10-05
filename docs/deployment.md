# Deploy Django with MySQL

The application expects a persistent MySQL 8 server with InnoDB and utf8mb4.
Do not use the local isolated port-3307 instance for a cloud deployment.

1. Back up the current database before updating an existing deployment.
2. Provision a persistent MySQL database with a dedicated application user.
   The normal application user does not need access to other databases. A separate
   test user may create/drop `test_reading_room` for local tests and CI.
3. Install Python 3.12+ and `requirements.txt`. Linux builds of `mysqlclient`
   need `default-libmysqlclient-dev`, `build-essential`, and `pkg-config`.
4. Configure the variables below in the host's environment, not in Git.

```dotenv
DJANGO_SECRET_KEY=<new random secret, at least 50 characters>
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=<your actual deployment hostname>
CSRF_TRUSTED_ORIGINS=https://<your actual deployment hostname>
MYSQL_DATABASE=<database>
MYSQL_USER=<dedicated application user>
MYSQL_PASSWORD=<password>
MYSQL_HOST=<MySQL hostname>
MYSQL_PORT=3306
MYSQL_SSL_CA=<provider CA certificate path, if required>
DJANGO_TRUST_PROXY=true
```

Enable `DJANGO_TRUST_PROXY` only when the hosting proxy strips untrusted forwarded
headers and supplies its own `X-Forwarded-Proto`. HTTPS redirects and secure cookies
are enabled when DEBUG is false. HSTS subdomain/preload options are deliberately
opt-in: use `DJANGO_HSTS_INCLUDE_SUBDOMAINS=true` only if every subdomain supports
HTTPS, and `DJANGO_HSTS_PRELOAD=true` only after reviewing domain-wide preload rules.
The former committed development secret must not be reused in production.

## Build and start

The compiled stylesheet is committed. To change it, run `npm ci` and
`npm run build:css` before deploying. Then:

```bash
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py check --deploy
gunicorn library_project.wsgi:application --bind 0.0.0.0:$PORT
```

Create the initial production librarian using `python manage.py createsuperuser`
in your host's secure shell. Do not run `seed_demo` or commit a production password.
If migrating the old SQLite data to a new empty MySQL database, upload the backup
privately and run `python manage.py import_legacy_sqlite --source /private/backup.sqlite3`
before using the new application. No original database files are in new commits.

## Reminder delivery

Configure `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST`,
`EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, and
`DEFAULT_FROM_EMAIL` for your provider. Without SMTP configuration, reminders use
the console backend and are not delivered to inboxes.

Verify `python manage.py send_reminders --dry-run`, then schedule
`python manage.py send_reminders` daily using the deployment provider's scheduler.
The scheduler must have the same database and SMTP environment as the web service.
The command returns a non-zero status on email failures so a scheduler can alert
or retry. No cloud service, paid resource, or live email campaign is created here.

## Before presenting a public demo

Use synthetic data in a separate demo database. Confirm role restrictions,
registration, issue/return, reservations, and the mobile layout at the live URL.
Keep real student records, `.env`, backups and database data directories private.
