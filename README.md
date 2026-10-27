# Notes App

A small full-stack notes application. Users register, log in, and manage their own private notes through a REST API and a simple web page. Built with FastAPI and SQLite, tested with pytest, containerized with Docker, and checked by GitHub Actions on every push.

## Features

- User registration and login with token-based authentication
- Create, read, update and delete notes
- Notes are private: each user can only access their own
- Single-page front end served by the API itself
- Automated tests and continuous integration

## Tech stack

- Python 3.13+ with FastAPI
- SQLite via the standard library `sqlite3` module
- Plain HTML and JavaScript for the front end
- pytest for tests
- Docker for packaging
- GitHub Actions for CI

## Project structure

```
main.py            API, database setup and authentication
static/index.html  Front end (login, register, notes list)
test_main.py       Automated tests
requirements.txt   Python dependencies
Dockerfile         Container image definition
.github/workflows  CI workflow that runs the tests
```

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
fastapi dev main.py
```

Then open:

- Web app: http://127.0.0.1:8000/app/
- Interactive API docs: http://127.0.0.1:8000/docs

The database file `notes.db` is created automatically on first start.

## Run the tests

```bash
pytest -v
```

The tests cover registration, login, authentication, per-user isolation, and the create, read, update and delete operations. Each test uses its own temporary database.

## Run with Docker

```bash
docker build -t notes-app .
docker run --rm -p 8000:8000 -e DB_PATH=/data/notes.db -v notes-data:/data notes-app
```

The `DB_PATH` environment variable sets where the database file lives, and the `notes-data` volume keeps the data when the container is removed.

## API

| Method | Path | Description | Auth |
| --- | --- | --- | --- |
| POST | /register | Create an account (409 if the username is taken) | No |
| POST | /login | Returns a bearer token (401 on bad credentials) | No |
| GET | /notes | List your notes | Yes |
| POST | /notes | Create a note | Yes |
| GET | /notes/{id} | Get one of your notes (404 if not found) | Yes |
| PUT | /notes/{id} | Update one of your notes | Yes |
| DELETE | /notes/{id} | Delete one of your notes | Yes |

Authenticated requests send the header `Authorization: Bearer <token>`.

## Design decisions

- **SQLite with parameterized queries.** SQLite needs no extra service and keeps setup simple. Every query passes values through `?` placeholders, never string formatting, which prevents SQL injection.
- **Salted scrypt password hashing.** Passwords are never stored. Each user gets a random 16-byte salt, and the hash uses `hashlib.scrypt`, which is deliberately slow to make guessing expensive. Hashes are compared with `hmac.compare_digest` to avoid timing leaks.
- **Same error for unknown user and wrong password.** Login returns an identical 401 message in both cases, so the API does not reveal which usernames exist.
- **Opaque random tokens.** Login creates a token with `secrets.token_urlsafe` and stores it in a `sessions` table. A FastAPI dependency looks the token up on every protected request.
- **Ownership checks in every query.** Each notes query filters by `user_id`. Another user's note returns 404 instead of 403, so the API does not confirm that the note exists.
- **Safe rendering in the browser.** The front end builds the notes list with `textContent`, not `innerHTML`, so note content cannot inject scripts (XSS).
- **Isolated tests.** A pytest fixture points the app at a fresh temporary database for every test, so tests never touch real data and do not depend on each other.
- **Docker layer caching.** The Dockerfile installs dependencies before copying the code, so rebuilds are fast when only the code changes.

## Known limitations and next steps

- Tokens do not expire, and logging out only clears the token in the browser. Next step: token expiry and server-side logout.
- No password strength rules or login rate limiting.
- The token is kept in `sessionStorage`, which a script injection bug could read. An httpOnly cookie would be safer.
- The container serves plain HTTP. In production it should sit behind a TLS-terminating proxy.
- SQLite suits a single instance. A larger deployment would use a server database such as PostgreSQL, with schema migrations.
- Not yet deployed to a cloud platform.
