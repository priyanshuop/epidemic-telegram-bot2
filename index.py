from http.server import BaseHTTPRequestHandler
import json
import os
import html
import httpx


# =========================
# ENVIRONMENT VARIABLES
# =========================

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
EPIDEMIC_KEY = os.environ["EPIDEMIC_API_KEY"]


# =========================
# API URLs
# =========================

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
EPIDEMIC_API = "https://partner-content-api.epidemicsound.com"


# =========================
# TELEGRAM API
# =========================

def telegram(method, data):
    response = httpx.post(
        f"{TELEGRAM_API}/{method}",
        json=data,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


# =========================
# EPIDEMIC SOUND SEARCH
# =========================

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


# =========================
# GET ARTIST
# =========================

def get_artist(track):

    artist = track.get("artist")

    if isinstance(artist, str):
        return artist

    if isinstance(artist, dict):
        return artist.get("name", "Unknown")

    artists = track.get("artists", [])

    if isinstance(artists, list):

        names = []

        for item in artists:

            if isinstance(item, str):
                names.append(item)

            elif isinstance(item, dict):

                name = item.get("name")

                if name:
                    names.append(name)

        if names:
            return ", ".join(names)

    return "Unknown"


# =========================
# SEND TELEGRAM MESSAGE
# =========================

def send_message(chat_id, text, buttons=None):

    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }

    if buttons:

        data["reply_markup"] = {
            "inline_keyboard": buttons
        }

    return telegram(
        "sendMessage",
        data
    )


# =========================
# HANDLE TELEGRAM UPDATE
# =========================

def handle_update(update):

    message = update.get("message")

    if not message:
        return

    chat_id = message["chat"]["id"]

    text = message.get(
        "text",
        ""
    ).strip()


    # =========================
    # /start
    # =========================

    if text == "/start":

        send_message(
            chat_id,

            "🎵 <b>Welcome to Music Bot!</b>\n\n"

            "Search the Epidemic Sound catalog "
            "directly from Telegram.\n\n"

            "🔎 <b>Try:</b>\n\n"

            "<code>/search cinematic music</code>\n\n"

            "<code>/search relaxing piano</code>\n\n"

            "<code>/search upbeat electronic</code>"
        )

        return


    # =========================
    # /help
    # =========================

    if text == "/help":

        send_message(
            chat_id,

            "🎧 <b>Music Bot Help</b>\n\n"

            "Use:\n"
            "<code>/search your query</code>\n\n"

            "Example:\n"
            "<code>/search cinematic music</code>"
        )

        return


    # =========================
    # /search
    # =========================

    if text.startswith("/search"):

        search_term = text[
            len("/search"):
        ].strip()


        if not search_term:

            send_message(
                chat_id,

                "❌ <b>Search query missing</b>\n\n"

                "Example:\n"
                "<code>/search relaxing piano</code>"
            )

            return


        # Searching message

        send_message(
            chat_id,
            "🔎 <b>Searching Epidemic Sound...</b>"
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


            # =========================
            # SEND EACH TRACK
            # =========================

            for number, track in enumerate(
                tracks,
                start=1
            ):

                title = html.escape(
                    str(
                        track.get(
                            "title",
                            "Unknown"
                        )
                    )
                )

                artist = html.escape(
                    str(
                        get_artist(track)
                    )
                )

                track_id = track.get(
                    "id"
                )


                # Clean result

                message_text = (

                    f"🎵 <b>{title}</b>\n\n"

                    f"👤 <b>Artist:</b> "
                    f"{artist}\n\n"

                    f"🎧 <b>Result:</b> "
                    f"{number}"
                )


                buttons = []


                # Preview button

                if track_id:

                    buttons.append(
                        [
                            {
                                "text": "🎧 Preview",
                                "callback_data":
                                f"preview:{track_id}"
                            }
                        ]
                    )


                send_message(
                    chat_id,
                    message_text,
                    buttons
                )


        except Exception as error:

            print(
                "Epidemic API error:",
                error
            )


            send_message(
                chat_id,

                "❌ <b>Epidemic Sound "
                "search failed.</b>\n\n"

                "Please check your API access."
            )

        return


    # =========================
    # UNKNOWN COMMAND
    # =========================

    send_message(
        chat_id,

        "❓ <b>Unknown command</b>\n\n"

        "Try:\n"
        "<code>/search relaxing piano</code>"
    )


# =========================
# VERCEL HANDLER
# =========================

class handler(BaseHTTPRequestHandler):


    # =========================
    # GET REQUEST
    # =========================

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain"
        )

        self.end_headers()

        self.wfile.write(
            b"Music Bot is running!"
        )


    # =========================
    # POST REQUEST
    # =========================

    def do_POST(self):

        try:

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    0
                )
            )


            body = self.rfile.read(
                content_length
            )


            update = json.loads(
                body.decode("utf-8")
            )


            handle_update(
                update
            )


            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.end_headers()


            self.wfile.write(
                b'{"ok":true}'
            )


        except Exception as error:

            print(
                "Webhook error:",
                error
            )


            self.send_response(500)

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.end_headers()


            self.wfile.write(
                b'{"ok":false}'
            )


    # =========================
    # PREVIEW BUTTON
    # =========================

    callback = update.get("callback_query")

    if callback:

        callback_id = callback["id"]
        callback_data = callback.get("data", "")
        callback_message = callback.get("message", {})
        callback_chat_id = callback_message.get("chat", {}).get("id")

        telegram(
            "answerCallbackQuery",
            {
                "callback_query_id": callback_id,
                "text": "🎧 Loading preview..."
            }
        )

        if callback_data.startswith("preview:"):

            track_id = callback_data.replace(
                "preview:",
                "",
                1
            )

            try:

                preview_data = get_preview(track_id)

                print("Preview response:", preview_data)

                # We'll process the returned URL here.

            except Exception as error:

                print(
                    "Preview error:",
                    error
                )

                if callback_chat_id:

                    send_message(
                        callback_chat_id,
                        "❌ Preview could not be loaded."
                    )

        return