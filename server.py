#!/usr/bin/env python3
"""Local Orakit preview server with a small Moralis-backed Ora search API."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SUGARTOWN_ORAS_CONTRACT = "0xd564c25b760cb278a55bdd98831f4ff4b6c97b38"
PIZZALORD_WALLET = "0x28af3356C6aaF449d20C59d2531941DDfB94d713"
DEFAULT_ENV_FILES = (
    ROOT / ".env",
    ROOT / ".env.local",
    Path.home() / ".hermes" / ".env",
)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def get_api_key() -> str:
    for path in DEFAULT_ENV_FILES:
        load_env_file(path)
    api_key = (
        os.environ.get("MORALIS_API_KEY")
        or os.environ.get("MORALIS_WEB3_API_KEY")
        or os.environ.get("MORALIS_API")
    )
    if not api_key:
        raise RuntimeError("Missing Moralis API key.")
    return api_key


def request_json(url: str, api_key: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "accept": "application/json",
            "user-agent": "orakit-preview/0.1",
            "X-API-Key": api_key,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Moralis HTTP {exc.code}: {body[:300]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Moralis request failed: {exc}") from exc


def request_public_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "accept": "application/json",
            "user-agent": "orakit-preview/0.1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body[:300]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Request failed: {exc}") from exc


def parse_metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def normalize_image_uri(value: str) -> str:
    if not value:
        return ""
    if value.startswith("ipfs://"):
        return "https://ipfs.io/ipfs/" + value.removeprefix("ipfs://")
    return value


def normalize_traits(metadata: dict[str, Any]) -> dict[str, str]:
    raw = metadata.get("attributes") or metadata.get("traits") or []
    traits: dict[str, str] = {}
    if not isinstance(raw, list):
        return traits
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("trait_type") or item.get("name") or item.get("key")
        value = item.get("value")
        if name and value is not None:
            traits[str(name)] = str(value)
    return traits


def resolve_wallet(value: str, api_key: str) -> tuple[str, str | None]:
    query = value.strip()
    if not query:
        raise RuntimeError("Wallet address or ENS name is required.")
    if query.lower() == "pizzalord.eth":
        return PIZZALORD_WALLET, query
    if query.lower().startswith("0x") and len(query) == 42:
        return query, None

    encoded = urllib.parse.quote(query, safe="")
    resolver_errors: list[str] = []

    try:
        data = request_json(f"https://deep-index.moralis.io/api/v2.2/resolve/ens/{encoded}", api_key)
        address = data.get("address")
        if isinstance(address, str) and address.startswith("0x"):
            return address, query
        resolver_errors.append("Moralis returned no address")
    except RuntimeError as exc:
        resolver_errors.append(f"Moralis: {exc}")

    try:
        data = request_public_json(f"https://api.ensideas.com/ens/resolve/{encoded}")
        address = data.get("address")
        if isinstance(address, str) and address.startswith("0x"):
            return address, query
        resolver_errors.append("ENSIdeas returned no address")
    except RuntimeError as exc:
        resolver_errors.append(f"ENSIdeas: {exc}")

    details = "; ".join(resolver_errors)
    raise RuntimeError(f'Could not resolve "{query}" to an EVM wallet. {details}')


def fetch_wallet_nfts(wallet: str, api_key: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    cursor = ""
    for _ in range(10):
        params = {
            "chain": "eth",
            "format": "decimal",
            "normalizeMetadata": "true",
            "media_items": "false",
            "limit": "100",
        }
        if cursor:
            params["cursor"] = cursor
        encoded_params = urllib.parse.urlencode(params)
        url = f"https://deep-index.moralis.io/api/v2.2/{urllib.parse.quote(wallet, safe='')}/nft?{encoded_params}"
        data = request_json(url, api_key)
        page = data.get("result")
        if isinstance(page, list):
            results.extend(item for item in page if isinstance(item, dict))
        cursor = str(data.get("cursor") or "")
        if not cursor:
            break
    return results


def nft_to_ora(item: dict[str, Any]) -> dict[str, Any] | None:
    contract = str(item.get("token_address") or "").lower()
    if contract != SUGARTOWN_ORAS_CONTRACT:
        return None

    token_id = str(item.get("token_id") or "")
    normalized = parse_metadata(item.get("normalized_metadata"))
    raw = parse_metadata(item.get("metadata"))
    metadata = {**raw, **normalized}
    name = str(metadata.get("name") or item.get("name") or f"Sugartown Oras #{token_id}")

    media = item.get("media") if isinstance(item.get("media"), dict) else {}
    media_collection = media.get("media_collection") if isinstance(media.get("media_collection"), dict) else {}
    high_media = media_collection.get("high") if isinstance(media_collection.get("high"), dict) else {}
    image = (
        metadata.get("image")
        or metadata.get("image_url")
        or high_media.get("url")
        or f"https://nfts.visitsugartown.com/nfts/oras/{token_id}.png"
    )

    return {
        "name": name,
        "oraNumber": token_id,
        "image": normalize_image_uri(str(image)),
        "traits": normalize_traits(metadata),
        "openseaUrl": f"https://opensea.io/assets/ethereum/{SUGARTOWN_ORAS_CONTRACT}/{token_id}",
        "contractAddress": SUGARTOWN_ORAS_CONTRACT,
        "previewSource": "metadata",
    }


def lookup_oras(wallet_query: str) -> dict[str, Any]:
    api_key = get_api_key()
    wallet, resolved_from = resolve_wallet(wallet_query, api_key)
    nfts = fetch_wallet_nfts(wallet, api_key)
    oras = [ora for item in nfts if (ora := nft_to_ora(item))]
    oras.sort(key=lambda item: int(item["oraNumber"]) if item["oraNumber"].isdigit() else item["oraNumber"])
    return {
        "success": True,
        "wallet": wallet,
        "resolvedFrom": resolved_from,
        "totalOras": len(oras),
        "oras": oras,
        "source": "moralis",
        "collection": {
            "name": "Sugartown Oras",
            "chain": "ethereum",
            "contractAddress": SUGARTOWN_ORAS_CONTRACT,
        },
    }


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/oras":
            self.handle_oras(parsed)
            return
        super().do_GET()

    def send_error(
        self,
        code: int,
        message: str | None = None,
        explain: str | None = None,
    ) -> None:
        if code != 404:
            super().send_error(code, message, explain)
            return

        body = b"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>OraKit 404</title>
    <style>
      :root { color-scheme: dark; }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        min-height: 100dvh;
        display: grid;
        place-items: center;
        background:
          radial-gradient(circle at 12% 14%, rgba(242, 193, 78, 0.16), transparent 30%),
          radial-gradient(circle at 88% 20%, rgba(91, 192, 235, 0.12), transparent 30%),
          #111318;
        color: #f4f1e8;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        padding: 24px;
      }
      main {
        width: min(920px, 100%);
        overflow: hidden;
        border: 1px solid #343b49;
        border-radius: 12px;
        background: #1c2028;
        box-shadow: 0 28px 80px rgba(0, 0, 0, 0.5);
      }
      img { display: block; width: 100%; background: #111318; }
      section { padding: 24px; }
      .eyebrow {
        color: #f2c14e;
        font-size: 12px;
        font-weight: 950;
        letter-spacing: 0.16em;
        text-transform: uppercase;
      }
      h1 {
        margin: 8px 0 10px;
        color: #f2c14e;
        font-size: clamp(38px, 7vw, 76px);
        line-height: 0.95;
      }
      p {
        margin: 0 0 18px;
        max-width: 680px;
        color: #aeb6c4;
        font-size: 18px;
        line-height: 1.55;
        font-weight: 650;
      }
      a {
        display: inline-flex;
        border-radius: 12px;
        background: #f2c14e;
        color: #08090c;
        padding: 12px 16px;
        text-decoration: none;
        font-weight: 950;
      }
    </style>
  </head>
  <body>
    <main>
      <img src="/assets/ora-4147-alpha-cola-fail.gif" alt="Ora 4147 failing a kickflip over Alpha Cola">
      <section>
        <div class="eyebrow">404 / Alpha Cola spill</div>
        <h1>Kickflip failed.</h1>
        <p>Ora 4147 could not land this route. Search another wallet or ENS from the OraKit home page.</p>
        <a href="/">Back to OraKit</a>
      </section>
    </main>
  </body>
</html>"""
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def handle_oras(self, parsed: urllib.parse.ParseResult) -> None:
        query = urllib.parse.parse_qs(parsed.query)
        wallet = (query.get("wallet") or [""])[0]
        try:
            payload = lookup_oras(wallet)
            self.write_json(200, payload)
        except Exception as exc:
            self.write_json(500, {"success": False, "error": str(exc)})

    def write_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 4173), PreviewHandler)
    print("Orakit preview server: http://localhost:4173/")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
