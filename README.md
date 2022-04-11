<h1 align="center">📆 thisday.link</h1>
<p align="center">Secure link shortener with 24h valid links</p>

<p align="center">
  <img alt="Python version" src="https://img.shields.io/badge/python-%5E3.8-blue">
  <img alt="GitHub repo size" src="https://img.shields.io/github/repo-size/berrysauce/thisday.link">
  <img alt="GitHub last commit" src="https://img.shields.io/github/last-commit/berrysauce/thisday.link">
  <img alt="Website Status" src="https://img.shields.io/website?down_color=red&down_message=down&url=https%3A%2F%2Fthisday.link">
</p>

## What is thisday.link
It's basically *ANOTHER* link shortener. But why is it special, you might ask? Shortened links are only valid for 24 hours and shortened domains have to support SSL (and have it corectly set up) *and* not be on our blocklist. In the future, thisday.link might check popular malicious domain blacklists to be extra secure. thisday.link also generates a handy QR code for you.


## How to use
thisday.link can be used comfortably from the web interface, but it also supports HTTP API requests. Here is a small documentation of how to use it.

### ⬇ GET Meta
Gets the metadata of the shortened URL. This includes its slug, expiry, and redirect location.

```http
GET /api/v1/meta/{slug}
```
| Query Parameter | Type | Description |
| :--- | :--- | :--- |
| `slug` | `string` | **Required**. The slug of the shortened URL (e.g. https://thisday.link/r/**2sa837**) |

**Response (Valid link) [200]**
```javascript
{
  "detail": "Link available",
  "slug": "2sa837",
  "expiry": "2022-04-12 20:51:14.429058",
  "redirect": "https://example.com"
}
```
**Response (Expired link) [404]**
```javascript
{
  "detail": "Link expired",
  "slug": "2sa837"
}
```

### ⬆ POST Create
Gets the metadata of the shortened URL. This includes its slug, expiry, and redirect location.

```http
POST /api/v1/create
```
| Body Parameter | Type | Description |
| :--- | :--- | :--- |
| `url` | `string` | **Required**. The URL you would like to shorten (e.g. https://example.com) |

**Response (Success) [200]**
```javascript
{
  "detail": "Link created",
  "slug": "2sa837",
  "expiry": "2022-04-12 20:51:14.429058",
  "redirect": "https://example.com"
}
```
**Response (SSL Error) [403]**
```javascript
{
  "detail": "SSL Error"
}
```
**Response (Blocked) [403]**
```javascript
{
  "detail": "Domain blocked by thisday.link"
}
```


### Made possible by DETA ❤️
<a href="https://deta.sh/?ref=thisday.link" target="_blank"><img src="https://eu2.contabostorage.com/d74bc97ec80c4b13b7f1db8d39948228:brry-cdn/deta-sponsor/D3263D63-638F-46C3-B9AB-9DC7C5CAB9BC.jpeg" alt="Sponsored by Deta"></a>
