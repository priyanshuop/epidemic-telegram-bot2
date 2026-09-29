import os
import httpx
from urllib.parse import quote


TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
EPIDEMIC_KEY = os.environ["EPIDEMIC_API_KEY"]

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
EPIDEMIC_API = "https://partner-content-api.epidemicsound.com"


async def telegram(method, data):
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{TELEGRAM_API}/{method}",
            json=data
        )
        return response.json()


async def epidemic_search(term):
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

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{EPIDEMIC_API}/v0/tracks/search",
            headers=headers,
            params=params,
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
                names.append(item.get("name", "Unknown"))

        return ", ".join(names)

    return "Unknown"


async def send_message(chat_id, text):
    return await telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        },
    )


async def handle_update(update):
    message = update.get("message")

    if not message:
        return

    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    # /start
    if text == "/start":

        await send_message(
            chat_id,
            "🎵 <b>Welcome to Music Bot!</b>\n\n"
            "Search Epidemic Sound music using:\n\n"
            "<code>/search relaxing piano</code>\n\n"
            "Try:\n"
            "• relaxing piano\n"
            "• cinematic music\n"
            "• upbeat electronic\n"
            "• acoustic guitar",
        )

        return

    # /help
    if text == "/help":

        await send_message(
            chat_id,
            "🎧 <b>Music Bot Help</b>\n\n"
            "<code>/search YOUR QUERY</code>\n\n"
            "Example:\n"
            "<code>/search cinematic</code>",
        )

        return

    # /search
    if text.startswith("/search"):

        search_term = text[7:].strip()

        if not search_term:

            await send_message(
                chat_id,
                "❌ Please enter something to search.\n\n"
                "Example:\n"
                "<code>/search relaxing piano</code>",
            )

            return

        await send_message(
            chat_id,
            "🔎 Searching Epidemic Sound..."
        )

        try:

            data = await epidemic_search(search_term)

            tracks = data.get("tracks", [])

            if not tracks:

                await send_message(
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
                start=1
            ):

                title = track.get(
                    "title",
                    "Unknown title"
                )

                artist = get_artist(track)

                track_id = track.get(
                    "id",
                    "Unknown"
                )

                result += (
                    f"<b>{number}. "
                    f"{title}</b>\n"
                    f"👤 {artist}\n"
                    f"🆔 <code>{track_id}</code>\n\n"
                )

            result += (
                "ℹ️ Use the track ID with the "
                "download feature in the next version."
            )

            await send_message(
                chat_id,
                result
            )

        except Exception as error:

            print("Epidemic API error:", error)

            await send_message(
                chat_id,
                "❌ Something went wrong while "
                "searching the music catalog."
            )

        return

    # Unknown command
    await send_message(
        chat_id,
        "❓ I don't understand that command.\n\n"
        "Try <code>/search relaxing piano</code>"
    )


async def process_request(request):

    try:
        update = request.get_json()
    except Exception:
        return {
            "statusCode": 400,
            "body": "Invalid JSON",
        }

    await handle_update(update)

    return {
        "statusCode": 200,
        "body": "OK",
    }


async def handler(request):
    return await process_request(request)