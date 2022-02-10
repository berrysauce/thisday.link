import uvicorn
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
import os
from dotenv import load_dotenv
from deta import Deta
import datetime
import string
import random
from typing import Optional
from pydantic import BaseModel


load_dotenv()
DETA_TOKEN = os.getenv("DETA_TOKEN")

app = FastAPI(docs_url=None, redoc_url=None)
deta = Deta(DETA_TOKEN)
db = deta.Base("links")
templates = Jinja2Templates(directory="templates")

app.mount("/assets", StaticFiles(directory="templates/assets"), name="assets")


def createEntry(url):
    if "http" not in url:
        raise HTTPException(status_code=500, detail="Wrong URL format")
    slug = ''.join(random.choices(string.ascii_lowercase + string.digits, k=7))
    expiry = datetime.datetime.now()
    expiry += datetime.timedelta(days=1)
    db.insert({
        "url": url,
        "slug": slug,
        "expiry": str(expiry)
    })
    return slug, expiry

class CreateItem(BaseModel):
    url: str


"""
=======================================================================
                           MAIN ENDPOINTS
=======================================================================
"""

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/r/{slug}", response_class=HTMLResponse)
def redirect(slug: str, request: Request):
    res = db.fetch({"slug": slug}, limit=1).items

    if len(res) == 0:
        countdown_html = """
                <div class="intro" style="min-width: 50%;margin-top: 50px;padding: 15px;background: #f5f5f5;border-radius: 10px;">
                    <h2 class="text-center" style="margin-bottom: 0px;font-size: 18px;">This link is</h2>
                    <p class="text-center" style="margin-bottom: 0px;font-size: 30px;color: var(--bs-red);">expired</p>
                    <div></div>
                </div>"""
        return templates.TemplateResponse("redirect.html", {
            "request": request,
            "countdown_html": countdown_html
        })
    res = res[0]
    expiry = datetime.datetime.strptime(res["expiry"], "%Y-%m-%d %H:%M:%S.%f")

    if expiry < datetime.datetime.now():
        countdown_html = """
        <div class="intro" style="min-width: 50%;margin-top: 50px;padding: 15px;background: #f5f5f5;border-radius: 10px;">
            <h2 class="text-center" style="margin-bottom: 0px;font-size: 18px;">This link is</h2>
            <p class="text-center" style="margin-bottom: 0px;font-size: 30px;color: var(--bs-red);">expired</p>
            <div></div>
        </div>"""
        return templates.TemplateResponse("redirect.html", {
            "request": request,
            "countdown_html": countdown_html,
            "url": res["url"]
        })
    else:
        countdown_html = """
        <div class="intro" style="min-width: 50%;margin-top: 50px;padding: 15px;background: #f5f5f5;border-radius: 10px;">
            <h2 class="text-center" style="margin-bottom: 0px;font-size: 18px;">This link is valid for</h2>
            <p class="text-center" style="margin-bottom: 0px;font-size: 30px;color: var(--bs-blue);"><span id="hours">00</span>:<span id="minutes">00</span>:<span id="seconds">00</span></p>
            <div></div>
        </div>"""
        redirect_html = """
        <div class="intro" style="min-width: 50%;margin-top: 0px;padding: 15px;background: #f5f5f5;border-radius: 10px;">
            <h2 class="text-start" style="margin-bottom: 0px;font-size: 22px;">Do you want to visit this link?</h2>
            <p class="text-start" style="margin-bottom: 20px;">If you want to visit&nbsp;<span style="color: var(--bs-blue);">{{ url }}</span>&nbsp;click the button below.<br></p><a class="btn btn-primary" role="button" href="{{ url }}" style="background: var(--bs-blue);border-style: none;padding: 6px 6px;color: rgb(255,255,255);border-radius: 5px;margin-top: 10px;padding-top: 8px;min-width: 100%;">Redirect me <svg class="icon icon-tabler icon-tabler-arrow-right" xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round" style="font-size: 20px;margin-bottom: 4px;">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <line x1="5" y1="12" x2="19" y2="12"></line>
            <line x1="13" y1="18" x2="19" y2="12"></line>
            <line x1="13" y1="6" x2="19" y2="12"></line>
            </svg></a>
                <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                <line x1="5" y1="12" x2="19" y2="12"></line>
                <line x1="13" y1="18" x2="19" y2="12"></line>
                <line x1="13" y1="6" x2="19" y2="12"></line>
            </svg></button>
        </div>""".replace("{{ url }}", res["url"])
        countdown = expiry.strftime("%b %d, %Y, %H:%M:%S")
        return templates.TemplateResponse("redirect.html", {
            "request": request,
            "countdown_html": countdown_html,
            "countdown": countdown,
            "redirect_html": redirect_html,
            "url": res["url"]
        })

@app.post("/create", response_class=HTMLResponse)
def create(request: Request, url: str = Form(...)):
    slug, expiry = createEntry(url)
    countdown = expiry.strftime("%b %d, %Y, %H:%M:%S")
    return templates.TemplateResponse("link.html", {
        "request": request,
        "countdown": countdown,
        "slug": slug
    })

@app.get("/terms", response_class=HTMLResponse)
def terms(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})

@app.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})

@app.get("/404", response_class=HTMLResponse)
def error(request: Request):
    return templates.TemplateResponse("error.html", {"request": request})


"""
=======================================================================
                           API ENDPOINTS
=======================================================================
"""

@app.get("/api/v1/meta/{slug}")
def api_meta(slug: str):
    res = db.fetch({"slug": slug}, limit=1).items

    if len(res) == 0:
        return {
            "detail": "Link expired",
            "slug": slug
        }
    res = res[0]
    expiry = datetime.datetime.strptime(res["expiry"], "%Y-%m-%d %H:%M:%S.%f")

    if expiry < datetime.datetime.now():
        return {
            "detail": "Link expired",
            "slug": slug
        }
    else:
        return {
            "detail": "Link available",
            "slug": slug,
            "expiry": res["expiry"],
            "redirect": res["url"]
        }

@app.post("/api/v1/create")
def api_meta(item: CreateItem):
    slug, expiry = createEntry(item.url)
    return {
        "detail": "Link created",
        "slug": slug,
        "expiry": str(expiry),
        "redirect": item.url
    }


"""
=======================================================================
                              RUNNER
=======================================================================
"""

@app.exception_handler(StarletteHTTPException)
async def my_custom_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse("error.html", {"request": request, "code": "404", "description": "The requested resource couldn't be found."})
    elif exc.status_code == 500:
        return templates.TemplateResponse("error.html", {"request": request, "code": "500", "description": exc.detail})
    else:
        return templates.TemplateResponse('error.html', {"request": request, "code": "Error", "description": exc.detail})


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)