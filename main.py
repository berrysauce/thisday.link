import uvicorn
from fastapi import FastAPI, Request, Response, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
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
import requests
import re


load_dotenv()
DETA_TOKEN = os.getenv("DETA_TOKEN")

app = FastAPI(docs_url=None, redoc_url=None)
deta = Deta(DETA_TOKEN)
db = deta.Base("links")
blocklist = deta.Base("blocklist")
templates = Jinja2Templates(directory="templates")

app.mount("/assets", StaticFiles(directory="templates/assets"), name="assets")

# - TODOS ----------------------------------------------
# TODO Add Blocklist report form
# TODO Add Captcha to all forms (maybe)
# TODO Add security headers
# ------------------------------------------------------


def createEntry(url):
    """
    Creates a database entry with the given URL and returns its generated slug and expiry.
    Also checks for URL format.
    """

    if "http" not in url:
        raise HTTPException(status_code=500, detail="Wrong URL format")

    slug = ''.join(random.choices(string.ascii_lowercase + string.digits, k=7))

    # Get currect time and add time delta
    # NOTE: JavaScript later converts expiry date to user's timezone (this is likely UTC)
    expiry = datetime.datetime.now()
    expiry += datetime.timedelta(days=1)

    db.put({
        "url": url,
        "slug": slug,
        "expiry": str(expiry)
    }, expire_in=86400)
    # 86400s = 24h
    return slug, expiry


def checkSSL(domain):
    """
    Checks the given domain for SSL validity and returns False if SSL is invalid
    """

    try:
        requests.get(domain)
        return True
    except requests.exceptions.SSLError:
        return False


def checkBlocklist(domain):
    """
    Checks the given domain against the blocklist database.
    Also checks for RegEx incompatibility.
    """

    # search with RegEx
    blocksearch = re.search("https?://(www\.)?([a-zA-Z0-9]+)(\.[a-zA-Z0-9.-]+)", domain)
    items = blocklist.fetch().items

    if blocksearch:
        for item in items:
            # also check if blocklist domain is set to block
            if item["domain"] in blocksearch.group() and item["block"] is True:
                return True
    else:
        # domain does not contain any RegEx result -> invalid domain
        raise HTTPException(status_code=500, detail="Unsupported URL/TLD format")

    return False


class CreateItem(BaseModel):
    """
    BaseModel for HTTP API POST request.
    """

    url: str


"""
=======================================================================
                           MAIN ENDPOINTS
=======================================================================
"""

@app.get("/", response_class=HTMLResponse)
def root(request: Request, error: Optional[str] = None):
    """
    Main endpoint with web interface. Shows an error if error query parameter is given.
    """

    if error == "ssl":
        alert = """<div class="alert alert-danger" role="alert"><span><strong>Error </strong>- The link you&#39;re trying to shorten doesn&#39;t support SSL. thisday.link can only shorten links with valid SSL certificates.</span></div>"""
    elif error == "blocked":
        alert = """<div class="alert alert-danger" role="alert"><span><strong>Error </strong>- The domain of the link you&#39;re trying to shorten was blocked by thisday.link. You cannot create shortened links for it.</span></div>"""
    else:
        alert = """"""

    return templates.TemplateResponse("index.html", {"request": request, "alert": alert})

@app.get("/r/{slug}", response_class=HTMLResponse)
def redirect(slug: str, request: Request):
    """
    Shows redirect web interface based on given slug.
    """

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
    """
    Creates a shortened link item from form on main endpoint.
    """

    # replace http:// with https:// since only SSL compatible domains are allowed
    if "http://" in url:
        url = url.replace("http://", "https://")

    if checkBlocklist(url) is True:
        return RedirectResponse("/?error=blocked", status_code=status.HTTP_303_SEE_OTHER)

    if checkSSL(url) is False:
        return RedirectResponse("/?error=ssl", status_code=status.HTTP_303_SEE_OTHER)

    slug, expiry = createEntry(url)
    countdown = expiry.strftime("%b %d, %Y, %H:%M:%S")
    return templates.TemplateResponse("link.html", {
        "request": request,
        "countdown": countdown,
        "slug": slug
    })

@app.get("/terms", response_class=HTMLResponse)
def terms(request: Request):
    """
    Shows /terms.
    """

    return templates.TemplateResponse("terms.html", {"request": request})

@app.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    """
    Shows /privacy.
    """

    return templates.TemplateResponse("privacy.html", {"request": request})

@app.get("/404", response_class=HTMLResponse)
def error(request: Request):
    """
    Shows /404.
    """

    return templates.TemplateResponse("error.html", {"request": request})


"""
=======================================================================
                           API ENDPOINTS
=======================================================================
"""

@app.get("/api/v1/meta/{slug}")
def api_meta(slug: str, response: Response):
    """
    HTTP API metadata endpoint. Returns the shortened link's metadata from database.
    """

    res = db.fetch({"slug": slug}, limit=1).items

    if len(res) == 0:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {
            "detail": "Link expired",
            "slug": slug
        }
    res = res[0]
    expiry = datetime.datetime.strptime(res["expiry"], "%Y-%m-%d %H:%M:%S.%f")

    if expiry < datetime.datetime.now():
        response.status_code = status.HTTP_404_NOT_FOUND
        return {
            "detail": "Link expired",
            "slug": slug
        }
    else:
        response.status_code = status.HTTP_200_OK
        return {
            "detail": "Link available",
            "slug": slug,
            "expiry": res["expiry"],
            "redirect": res["url"]
        }

@app.post("/api/v1/create")
def api_meta(item: CreateItem, response: Response):
    """
    HTTP API create endpoint. Returns the shortened link's generated metadata from database.
    """

    # replace http:// with https:// since only SSL compatible domains are allowed
    if "http://" in item.url:
        url = item.url.replace("http://", "https://")
    else:
        url = item.url

    if checkBlocklist(url) is True:
        response.status_code = status.HTTP_403_FORBIDDEN
        return {
            "detail": "Domain blocked by thisday.link"
        }

    if checkSSL(url) is False:
        response.status_code = status.HTTP_403_FORBIDDEN
        return {
            "detail": "SSL Error"
        }

    slug, expiry = createEntry(url)
    response.status_code = status.HTTP_200_OK
    return {
        "detail": "Link created",
        "slug": slug,
        "expiry": str(expiry),
        "redirect": url
    }


"""
=======================================================================
                              RUNNER
=======================================================================
"""

@app.exception_handler(StarletteHTTPException)
async def my_custom_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handles exceptions and redirects to correct error page.
    """

    if exc.status_code == 404:
        return templates.TemplateResponse("error.html", {"request": request, "code": "404", "description": "The requested resource couldn't be found."})
    elif exc.status_code == 500:
        return templates.TemplateResponse("error.html", {"request": request, "code": "500", "description": exc.detail})
    else:
        return templates.TemplateResponse('error.html', {"request": request, "code": "Error", "description": exc.detail})


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)