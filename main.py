from fastapi import FastAPI
from fastapi.responses import RedirectResponse
import string
import random

app = FastAPI()

# memory storage
url_map = {}


def generate_key(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


@app.get("/")
def home():
    return {"message": "URL shortener running"}


@app.post("/shorten")
def shorten_url(url: str):
    key = generate_key()
    url_map[key] = url
    return {"short_url": f"http://localhost:8000/{key}"}


@app.get("/{key}")
def redirect(key: str):
    if key not in url_map:
        return {"error": "Not found"}

    return RedirectResponse(url_map[key])