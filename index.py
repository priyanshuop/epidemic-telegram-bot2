from http.server import BaseHTTPRequestHandler
import json
import os

import httpx


TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
EPIDEMIC_KEY = os.environ["EPIDEMIC_API_KEY"]

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
EPIDEMIC_API = "https://partner-content-api.epidemicsound.com"


def telegram(method, data):
    response = httpx.post(
        f"{TELEGRAM_API}/{method}",
        json=data,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def search_epidemic(term):

    headers = {
        "Authorization": f"Bearer {EPIDEMIC_KEY}",
        "Accept": "application/json",
    }

    params = {
        "term": term,
        "limit": 5,
        "offset": 0,
        "sort": "Relevance",
    }

    response = httpx.get(
        f"{EPIDEMIC_API}/v0/tracks/search",
        headers=headers,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def get_artist(track):

    artist = track.get("artist")

    if isinstance(artist, str):
        return artist

    artists = track.get("artists", [])

    if isinstance(artists, list):

        names = []

        for item in artists:

            if isinstance(item, str):
                names.append(item)

            elif isinstance(item, dict):
                names.append(
                    item.get("name", "Unknown")
                )

        if names:
            return ", ".join(names)

    return "Unknown"


def send_message(chat_id, text):

    return telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        },
    )


def handle_update(update):

    message = update.get("message")

    if not message:
        return

    chat_id = message["chat"]["id"]

    text = message.get(
        "text",
        "",
    ).strip()

    # -------------------------
    # /start
    # -------------------------

    if text == "/start":

        send_message(
            chat_id,
            "🎵 <b>Welcome to Music Bot!</b>\n\n"
            "I can search the Epidemic Sound catalog.\n\n"
            "Try:\n"
            "<code>/search relaxing piano</code>\n\n"
            "Other examples:\n"
            "• cinematic music\n"
            "• upbeat electronic\n"
            "• acoustic guitar\n"
            "• relaxing music",
        )

        return

    # -------------------------
    # /help
    # -------------------------

    if text == "/help":

        send_message(
            chat_id,
            "🎧 <b>Music Bot</b>\n\n"
            "Use:\n"
            "<code>/search your query</code>\n\n"
            "Example:\n"
            "<code>/search cinematic music</code>",
        )

        return

    # -------------------------
    # /search
    # -------------------------

    if text.startswith("/search"):

        search_term = text[
            len("/search"):
        ].strip()

        if not search_term:

            send_message(
                chat_id,
                "❌ Please enter a search query.\n\n"
                "Example:\n"
                "<code>/search relaxing piano</code>",
            )

            return

        send_message(
            chat_id,
            "🔎 Searching Epidemic Sound..."
        )

        try:

            data = search_epidemic(
                search_term
            )

            tracks = data.get(
                "tracks",
                []
            )

            if not tracks:

                send_message(
                    chat_id,
                    "❌ No tracks found."
                )

                return

            result = (
                f"🎵 <b>Results for:</b> "
                f"{search_term}\n\n"
            )

            for number, track in enumerate(
                tracks,
                start=1,
            ):

                title = track.get(
                    "title",
                    "Unknown",
                )

                artist = get_artist(
                    track
                )

                track_id = track.get(
                    "id",
                    "Unknown",
                )

                result += (
                    f"<b>{number}. "
                    f"{title}</b>\n"
                    f"👤 {artist}\n"
                    f"🆔 <code>{track_id}</code>\n\n"
                )

            send_message(
                chat_id,
                result,
            )

        except Exception as error:

            print(
                "Epidemic API error:",
                error,
            )

            send_message(
                chat_id,
                "❌ Epidemic Sound search failed.\n\n"
                "Please check your API access.",
            )

        return

    # -------------------------
    # Unknown message
    # -------------------------

    send_message(
        chat_id,
        "❓ Unknown command.\n\n"
        "Try:\n"
        "<code>/search relaxing piano</code>",
    )


class handler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain",
        )

        self.end_headers()

        self.wfile.write(
            b"Music Bot is running!"
        )

    def do_POST(self):

        try:

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    0,
                )
            )

            body = self.rfile.read(
                content_length
            )

            update = json.loads(
                body.decode("utf-8")
            )

            handle_update(update)

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/json",
            )

            self.end_headers()

            self.wfile.write(
                b'{"ok":true}'
            )

        except Exception as error:

            print(
                "Webhook error:",
                error,
            )

            self.send_response(500)

            self.send_header(
                "Content-Type",
                "application/json",
            )

            self.end_headers()

            self.wfile.write(
                b'{"ok":false}'
            )