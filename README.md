# aiogram_template

1. Create `.env` based on `.env.example`.
2. Put web cookies into `cookies-5ka-ru.txt`.
3. Run

- Locally
```bash
pip install -r requirements.txt
python run.py
```

- Docker with hot reload (dev mode):

```bash
docker compose -f docker-compose.DEV.yml up --build
```

- Docker (prod mode):

```bash
docker compose up --build -d
```
