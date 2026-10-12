import os
import logging
import requests
import re
import json
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from flask import Response, send_from_directory
# Load variables from .env into the real process environment. Without
# this, every os.environ.get(...) call below (Gemini key, SMTP
# credentials, Maps key, etc.) silently returns None even if they're set
# in .env - Flask's dev server does NOT do this automatically.
load_dotenv()

from flask import Flask, request, jsonify, render_template, session, send_from_directory
from flask_cors import CORS
from google.genai import types
from gemini_service import GeminiService
import uuid
import time
from flask import g

log_level = (
    logging.DEBUG if os.environ.get("FLASK_ENV") == "development" else logging.INFO
)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

# Create Flask app with proper template and static folders
app = Flask(__name__, template_folder="templates", static_folder="static")
_secret = os.environ.get("SESSION_SECRET")
if not _secret:
    logging.warning("SESSION_SECRET not set - using a random per-process key. "
                    "Set SESSION_SECRET on Render so sessions survive restarts.")
    _secret = uuid.uuid4().hex
app.secret_key = _secret

# Enable CORS for frontend communication
CORS(app, origins=["*"])

# Initialize Gemini service (also used for OCR/text-reading via Gemini Vision)
gemini_service = GeminiService()


@app.route("/")
def index():
    """Serve the main application page"""
    try:
        return render_template("index.html")
    except Exception as e:
        logging.error(f"Error serving index.html: {e}")
        return "Application files not found", 404


@app.route("/sw.js")
def service_worker():
    """
    Serve the service worker from the root path (not /static/js/sw.js).
    Service workers can only control pages within their own scope by
    default - serving it from /static/js/ would limit it to that folder
    only, breaking the whole "installable app" experience. Root scope is
    required for Add to Home Screen / voice-assistant launching to work
    properly across the whole app.
    """
    response = send_from_directory("static/js", "sw.js")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Content-Type"] = "application/javascript"
    return response


# ---------------------------------------------------------------------------
# Per-device storage. Settings (name, phone, emergency contacts, home address),
# remembered objects and saved places used to live in ONE shared file, so every
# visitor of the public site saw - and could overwrite - the same private data.
# Each browser now gets a random anonymous id cookie and its own folder.
# ---------------------------------------------------------------------------
DATA_DIR = os.environ.get("DATA_DIR", "user_data")
CID_COOKIE = "bm_cid"
_CID_RE = re.compile(r"^[0-9a-f]{32}$")


@app.before_request
def assign_client_id():
    cid = request.cookies.get(CID_COOKIE, "")
    g.new_cid = False
    if not _CID_RE.match(cid):
        cid = uuid.uuid4().hex
        g.new_cid = True
    g.cid = cid


@app.after_request
def persist_client_id(response):
    if getattr(g, "new_cid", False):
        response.set_cookie(
            CID_COOKIE, g.cid, max_age=60 * 60 * 24 * 365,
            httponly=True, samesite="Lax", secure=request.is_secure,
        )
    return response


def user_file(name):
    """Path of a data file belonging to the current device (file fallback)."""
    folder = os.path.join(DATA_DIR, g.cid)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, name)


# ---------------------------------------------------------------------------
# Persistence. With DATABASE_URL set (Postgres on Render/Neon/Supabase, or
# sqlite for testing) everything lives in one small key-value table and
# survives redeploys. Without it we fall back to JSON files, which are wiped
# on Render's free tier every deploy.
# ---------------------------------------------------------------------------
_engine = None
_DB_URL = os.environ.get("DATABASE_URL", "").strip()
if _DB_URL:
    try:
        from sqlalchemy import create_engine, text as _sql

        if _DB_URL.startswith("postgres://"):
            _DB_URL = "postgresql://" + _DB_URL[len("postgres://"):]
        _engine = create_engine(_DB_URL, pool_pre_ping=True, pool_recycle=300)
        with _engine.begin() as _c:
            _c.execute(_sql(
                "CREATE TABLE IF NOT EXISTS kv ("
                "owner VARCHAR(64) NOT NULL, name VARCHAR(64) NOT NULL, "
                "value TEXT NOT NULL, updated DOUBLE PRECISION NOT NULL, "
                "PRIMARY KEY (owner, name))"
            ))
        logging.info("Using database storage (%s)", _engine.dialect.name)
    except Exception as _e:
        logging.error("Database unavailable, falling back to files: %s", _e)
        _engine = None


def db_get(owner, name, default=None):
    if _engine is None:
        return None
    try:
        with _engine.connect() as c:
            row = c.execute(
                _sql("SELECT value FROM kv WHERE owner=:o AND name=:n"),
                {"o": owner, "n": name},
            ).fetchone()
        return json.loads(row[0]) if row else default
    except Exception as e:
        logging.error("db_get failed: %s", e)
        return default


def db_set(owner, name, value):
    try:
        payload = {"o": owner, "n": name, "v": json.dumps(value, ensure_ascii=False), "t": time.time()}
        with _engine.begin() as c:
            res = c.execute(
                _sql("UPDATE kv SET value=:v, updated=:t WHERE owner=:o AND name=:n"), payload
            )
            if res.rowcount == 0:
                c.execute(
                    _sql("INSERT INTO kv (owner, name, value, updated) VALUES (:o, :n, :v, :t)"),
                    payload,
                )
        return True
    except Exception as e:
        logging.error("db_set failed: %s", e)
        return False


def load_user(name, default):
    """Read this device's stored value (database first, else file)."""
    if _engine is not None:
        return db_get(g.cid, name, default)
    return load_json_file(user_file(name + ".json"), default)


def save_user(name, value):
    if _engine is not None:
        return db_set(g.cid, name, value)
    write_json(user_file(name + ".json"), value)
    return True


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


LANGUAGE_NAMES = {
    "en-IN": "English", "hi-IN": "Hindi", "kn-IN": "Kannada", "ta-IN": "Tamil",
    "te-IN": "Telugu",
}


@app.route("/api/ocr", methods=["POST"])
def read_ocr():

    if "image" not in request.files:
        return jsonify({"success": False, "message": "No image uploaded."})

    if gemini_service.client is None:
        return jsonify(
            {
                "success": False,
                "message": "Text reading is unavailable right now. Please check that the AI service is configured.",
            }
        )

    image = request.files["image"]
    image_bytes = image.read()
    mime = image.mimetype if (image.mimetype or "").startswith("image/") else "image/jpeg"

    ocr_prompt = """You are helping a blind user read printed or handwritten text out loud.

Read ALL visible text in this image exactly as it appears, in natural reading order (top to bottom, left to right).
This is often a medicine label, pill bottle, document, or piece of paper, so pay close attention to:
- Medicine or product name
- Dosage instructions (e.g. "take 2 tablets twice daily")
- Expiry date and batch number
- Any warnings

Rules:
- Output ONLY the text you can read - no descriptions of the image, no commentary, no markdown.
- If the image contains no readable text at all, respond with exactly: No text detected.
- If text is blurry or partially unreadable, still read what you can and skip only the unreadable parts."""

    try:
        response = gemini_service.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[ocr_prompt, types.Part.from_bytes(data=image_bytes, mime_type=mime)],
        )

        text = response.text.strip() if response.text else ""

        return jsonify(
            {"success": True, "text": text if text else "No text detected."}
        )

    except Exception as e:
        import traceback

        traceback.print_exc()

        return jsonify({"success": False, "message": str(e)}), 500




_TRANSLATION_CACHE = {}


@app.route("/api/translate", methods=["POST"])
def translate():

    data = request.get_json(silent=True) or {}

    text = data.get("text", "")

    language = data.get("language", "en-IN")

    if not text:
        return jsonify({"success": False, "translated": ""})

    if gemini_service.client is None:
        return jsonify({"success": False, "translated": text})

    # English doesn't need translation
    if language == "en-IN":
        return jsonify({"success": True, "translated": text})

    target_language = LANGUAGE_NAMES.get(language, "English")

    cache_key = (language, text.strip().lower())
    if cache_key in _TRANSLATION_CACHE:
        return jsonify({"success": True, "translated": _TRANSLATION_CACHE[cache_key]})

    prompt = f"""
Translate this entire sentence fully into {target_language}, including any object,
place, or item names (e.g. "phone", "chair", "bottle") - {target_language} has its
own words for these common nouns, so translate them too. Do not leave any English
words in the output unless they are a proper noun with no natural {target_language}
equivalent (e.g. a brand name).

Rules:
- Return only the translated sentence, fully in {target_language} script.
- Do not explain.
- Do not add quotation marks.
- Do not mix English words into the translated sentence.
- Preserve meaning exactly.

Sentence:
{text}
"""

    try:

        response = gemini_service.client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt
        )

        translated = (response.text or "").strip()
        if not translated:
            return jsonify({"success": False, "translated": text})
        if len(_TRANSLATION_CACHE) > 2000:
            _TRANSLATION_CACHE.pop(next(iter(_TRANSLATION_CACHE)))
        _TRANSLATION_CACHE[cache_key] = translated
        return jsonify({"success": True, "translated": translated})

    except Exception as e:

        print(e)

        return jsonify({"success": False, "translated": text})


def load_json_file(path, default):
    """
    Safely load a JSON file, tolerating it being missing OR existing-but-
    empty/corrupt (e.g. a 0-byte file, which raises JSONDecodeError on
    json.load and would otherwise crash the request with a 500 error).
    """
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return default
            return json.loads(content)
    except json.JSONDecodeError:
        logging.warning(f"{path} contains invalid JSON - treating as empty")
        return default


@app.route("/api/memory/save", methods=["POST"])
def save_memory():
    """
    Save/update an object's last-seen info. Upserts by object name (case-
    insensitive) instead of appending forever - this keeps the file small
    and, importantly, makes "last seen" queries actually return the most
    recent sighting instead of the oldest one ever recorded.
    """
    data = request.get_json(silent=True) or {}
    memories = load_user("memory", [])

    object_name = (data.get("object") or "").strip().lower()

    # Replace any existing entry for this object with the fresh sighting
    memories = [
        m for m in memories if (m.get("object") or "").strip().lower() != object_name
    ]
    memories.append(data)

    save_user("memory", memories[-200:])

    return jsonify({"success": True})


@app.route("/api/memory")
def get_memory():
    return jsonify(load_user("memory", []))




@app.route("/api/memory/place/save", methods=["POST"])
def save_place():
    """
    Save a named place (e.g. "bathroom", "kitchen", "front door") with the
    user's current GPS coordinates, so it can be recalled later with
    "where is the bathroom" / "take me to the bathroom".
    """
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if not name or latitude is None or longitude is None:
        return jsonify({"success": False, "message": "Missing name or coordinates."}), 400

    places = load_user("places", [])

    # Upsert by name (case-insensitive) - re-saving "bathroom" updates it
    # rather than creating duplicates.
    places = [p for p in places if (p.get("name") or "").strip().lower() != name.lower()]
    places.append(
        {
            "name": name,
            "latitude": latitude,
            "longitude": longitude,
            "time": data.get("time"),
            "timestamp": data.get("timestamp"),
        }
    )

    save_user("places", places)

    return jsonify({"success": True})


@app.route("/api/memory/places")
def get_places():
    return jsonify(load_user("places", []))


@app.route("/api/settings", methods=["GET"])
def get_settings():
    return jsonify(load_user("settings", {}))


@app.route("/api/settings", methods=["POST"])
def save_settings():

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "message": "Invalid settings."}), 400

    save_user("settings", data)

    return jsonify({"success": True, "message": "Settings saved successfully."})


@app.route("/settings")
def settings():
    return render_template("settings.html")


@app.route("/onboarding")
def onboarding():
    return render_template("onboarding.html")


@app.route("/help")
def help_page():
    """Serve the shortcuts/instructions reference page"""
    try:
        return render_template("help.html")
    except Exception as e:
        logging.error(f"Error serving help.html: {e}")
        return "Help page not found", 404


@app.route("/tutorial")
def tutorial():
    """Serve the onboarding tutorial page"""
    try:
        return render_template("onboarding.html")
    except Exception as e:
        logging.error(f"Error serving onboarding.html: {e}")
        return "Tutorial not found", 404


@app.route("/navigation")
def navigation():
    """Serve navigation page"""
    try:
        return render_template("navigation.html")
    except Exception as e:
        logging.error(f"Error serving navigation.html: {e}")
        return "Navigation page not found", 404


# JavaScript files are now served automatically by Flask from /static folder


@app.route("/api/process-command", methods=["POST"])
def process_command():
    """Process voice commands using Gemini API"""
    try:
        data = request.get_json()

        if not data or "command" not in data:
            return jsonify({"error": "Missing command in request"}), 400

        command = data["command"]
        language = data.get("language", session.get("current_language", "en-IN"))
        tone = data.get("tone", session.get("current_tone", "friendly"))

        logging.info(
            f"Processing command: {command} in language: {language} with tone: {tone}"
        )

        # Check for language/tone change commands
        result = gemini_service.process_voice_command(command, language, tone)

        # Update session if language or tone changed
        if result.get("action") == "change_language" and result.get("language"):
            session["current_language"] = result["language"]
            logging.info(f"Language changed to: {result['language']}")

        if result.get("action") == "change_tone" and result.get("tone"):
            session["current_tone"] = result["tone"]
            logging.info(f"Tone changed to: {result['tone']}")

        # Add current session preferences to response
        result["current_language"] = session.get("current_language", "en-IN")
        result["current_tone"] = session.get("current_tone", "friendly")

        return jsonify(result)

    except Exception as e:
        logging.error(f"Error processing command: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/directions", methods=["POST"])
def get_directions():
    """Get walking directions using free OpenStreetMap services -
    Nominatim for geocoding and the FOSSGIS OSRM instance for routing.
    No API key or billing account required."""
    try:
        data = request.get_json()

        if not data or "origin" not in data or "destination" not in data:
            return (
                jsonify({"success": False, "message": "Missing origin or destination"}),
                400,
            )

        origin = data["origin"]  # Expected format: "lat,lng"
        destination = data["destination"]  # Can be address text or "lat,lng"

        # Validate origin coordinates format
        coord_pattern = r"^-?\d+\.?\d*,-?\d+\.?\d*$"
        if not re.match(coord_pattern, origin):
            return (
                jsonify(
                    {"success": False, "message": "Invalid origin coordinates format"}
                ),
                400,
            )

        # Parse origin coordinates
        try:
            origin_lat, origin_lng = map(float, origin.split(","))
            if not (-90 <= origin_lat <= 90) or not (-180 <= origin_lng <= 180):
                return (
                    jsonify(
                        {"success": False, "message": "Origin coordinates out of range"}
                    ),
                    400,
                )
        except ValueError:
            return (
                jsonify({"success": False, "message": "Invalid origin coordinates"}),
                400,
            )

        # Check if destination is coordinates or address text
        destination_coords = destination
        destination_display_name = destination
        if not re.match(coord_pattern, destination):
            # Destination is text address - geocode it via Nominatim,
            # biased towards the user's current location so ambiguous
            # names ("library", "pharmacy") resolve to a nearby match.
            logging.info(f"Geocoding destination: {destination}")

            geocoded = geocode_address_osm(destination, origin_lat, origin_lng)

            if not geocoded or "error" in geocoded:
                message = (
                    geocoded.get("message")
                    if geocoded
                    else f'Could not find "{destination}" near your location. Please try a more specific address.'
                )
                return (
                    jsonify({"success": False, "message": message}),
                    404,
                )

            destination_coords = f"{geocoded['lat']},{geocoded['lng']}"
            destination_display_name = geocoded.get("display_name", destination)
            logging.info(f"Geocoded '{destination}' to {destination_coords}")

        # Get walking directions from the FOSSGIS OSRM instance
        directions_data = get_osrm_directions(origin, destination_coords)

        if not directions_data:
            return jsonify({"success": False, "message": "Route not available"}), 404
        elif "error" in directions_data:
            return (
                jsonify({"success": False, "message": directions_data["message"]}),
                404,
            )

        # Parse and format the directions for voice navigation
        try:
            navigation_data = parse_osrm_directions(
                directions_data, destination_display_name
            )
            return jsonify(navigation_data)
        except Exception as parse_error:
            logging.error(f"Error parsing OSRM directions: {parse_error}")
            return (
                jsonify(
                    {"success": False, "message": "Failed to parse navigation data"}
                ),
                500,
            )

    except requests.exceptions.Timeout:
        logging.error("Routing service timeout")
        return jsonify({"success": False, "message": "Navigation service timeout"}), 504
    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP error getting directions: {e}")
        return (
            jsonify({"success": False, "message": "Navigation service unavailable"}),
            503,
        )
    except Exception as e:
        logging.error(f"Error getting directions: {e}")
        return jsonify({"success": False, "message": "Navigation service error"}), 500


@app.route("/api/preferences", methods=["GET", "POST"])
def preferences():
    """Get or set user language and tone preferences"""
    if request.method == "GET":
        return jsonify(
            {
                "language": session.get("current_language", "en-IN"),
                "tone": session.get("current_tone", "friendly"),
            }
        )

    elif request.method == "POST":
        data = request.get_json()

        if "language" in data:
            session["current_language"] = data["language"]
            logging.info(f"Language preference updated to: {data['language']}")

        if "tone" in data:
            session["current_tone"] = data["tone"]
            logging.info(f"Tone preference updated to: {data['tone']}")

        return jsonify(
            {
                "success": True,
                "language": session.get("current_language"),
                "tone": session.get("current_tone"),
            }
        )


def send_emergency_email(to_email, contact_name, message, user_name=""):
    """
    Send a real emergency alert email via SMTP. Configured through env vars:
    SMTP_EMAIL / SMTP_PASSWORD (an app password, not a regular account
    password, if using Gmail) and optionally SMTP_HOST / SMTP_PORT.
    Returns (success: bool, error: str | None) - the error string is
    surfaced back to the client so failures are actually debuggable
    instead of only appearing in server logs.
    """
    subject = (
        f"Urgent: {user_name} needs you to call them"
        if user_name
        else "Urgent: Please call your contact"
    )

    # Preferred: HTTPS email API (Brevo). Hosts like Render's free tier block
    # outgoing SMTP ports, so smtplib silently fails there; port 443 works.
    brevo_key = os.environ.get("BREVO_API_KEY")
    brevo_sender = os.environ.get("BREVO_SENDER_EMAIL")
    if brevo_key and brevo_sender:
        try:
            r = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": brevo_key, "accept": "application/json",
                         "content-type": "application/json"},
                json={
                    "sender": {"email": brevo_sender, "name": "BlindMate Alert"},
                    "to": [{"email": to_email, "name": contact_name or to_email}],
                    "subject": subject,
                    "textContent": message,
                },
                timeout=12,
            )
            if r.status_code in (200, 201):
                return True, None
            err = f"Brevo HTTP {r.status_code}: {r.text[:200]}"
            logging.error(f"Emergency email failed for {to_email}: {err}")
            return False, err
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            logging.error(f"Emergency email failed for {to_email}: {err}")
            return False, err

    smtp_email = os.environ.get("SMTP_EMAIL")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))

    if not smtp_email or not smtp_password:
        logging.warning(
            "Emergency email skipped: SMTP_EMAIL/SMTP_PASSWORD not set in environment "
            "(check that your .env file is named exactly '.env', not '.env.txt', "
            "and is in the same folder as app.py)"
        )
        return False, "No email channel configured (set BREVO_API_KEY + BREVO_SENDER_EMAIL)"

    try:
        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = smtp_email
        msg["To"] = to_email

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, [to_email], msg.as_string())

        return True, None
    except Exception as e:
        error_detail = f"{type(e).__name__}: {e}"
        logging.error(f"Emergency email failed for {to_email}: {error_detail}")
        return False, error_detail


def send_emergency_sms(to_phone, message):
    """
    Send a real SMS via Twilio, if configured. Env vars: TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER. Returns True only if the SMS
    genuinely sent. This is optional - Twilio is a paid service - email
    alerts work without it.
    """
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = os.environ.get("TWILIO_PHONE_NUMBER")

    if not (account_sid and auth_token and from_number):
        logging.info(
            "Emergency SMS skipped: Twilio credentials not set (this is optional - only needed if you want SMS in addition to email)"
        )
        return False

    try:
        response = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
            auth=(account_sid, auth_token),
            data={"From": from_number, "To": to_phone, "Body": message},
            timeout=10,
        )
        return response.status_code == 201
    except Exception as e:
        logging.error(f"Emergency SMS failed for {to_phone}: {e}")
        return False


_EMERGENCY_LOG = {}


@app.route("/api/emergency", methods=["POST"])
def emergency():

    data = request.get_json(silent=True) or {}
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    contacts = data.get("contacts", [])
    if not isinstance(contacts, list):
        contacts = []
    contacts = [c for c in contacts if isinstance(c, dict)][:5]
    user_name = (data.get("user_name") or "").strip()
    user_phone = (data.get("user_phone") or "").strip()
    battery = data.get("battery") if isinstance(data.get("battery"), dict) else {}
    try:
        battery_level = int(battery.get("level"))
        if not 0 <= battery_level <= 100:
            battery_level = None
    except (TypeError, ValueError):
        battery_level = None
    tracking_url = (data.get("tracking_url") or "").strip()
    if tracking_url and not tracking_url.startswith(request.host_url):
        tracking_url = ""  # only ever include links to this site

    maps_link = (
        f"https://maps.google.com/?q={latitude},{longitude}"
        if latitude is not None and longitude is not None
        else "location unavailable"
    )

    who = user_name if user_name else "A visually impaired user"
    callback = f" You can call them back at {user_phone}." if user_phone else ""

    message = (
        f"This is an automated message from BlindMate. "
        f"{who}, who has you listed as an emergency contact, needs help and cannot call you directly. "
        f"Their current location: {maps_link}.{callback} Please call them as soon as you can."
    )
    if battery_level is not None:
        message += f" Their phone battery is at {battery_level}%."
    if tracking_url:
        message += f" Live location (updates for the next 2 hours): {tracking_url}"

    # This endpoint can send email/SMS, so stop it being used as a spam relay:
    # max 5 alerts per device per 10 minutes.
    now = time.time()
    recent = [t for t in _EMERGENCY_LOG.get(g.cid, []) if now - t < 600]
    if len(recent) >= 5:
        return jsonify({"success": False, "message": "Too many alerts. Please call your contact directly.",
                        "results": [], "maps_link": maps_link, "raw_message": message}), 429
    recent.append(now)
    _EMERGENCY_LOG[g.cid] = recent

    logging.info("EMERGENCY ALERT triggered - lat=%s lon=%s", latitude, longitude)

    results = []
    any_sent = False

    for contact in contacts:
        name = contact.get("name") or "Contact"
        phone = contact.get("phone")
        email = contact.get("email")

        sent_email = False
        email_error = None
        sent_sms = False

        if email:
            sent_email, email_error = send_emergency_email(
                email, name, message, user_name
            )
        if phone:
            sent_sms = send_emergency_sms(phone, message)

        if sent_email or sent_sms:
            any_sent = True

        results.append(
            {
                "name": name,
                "phone": phone,
                "email": email,
                "email_sent": sent_email,
                "email_error": email_error,
                "sms_sent": sent_sms,
            }
        )

    return jsonify(
        {
            "success": any_sent,
            "message": (
                "Emergency alert sent."
                if any_sent
                else "No alert channel is configured on the server (email or SMS)."
            ),
            "results": results,
            "maps_link": maps_link,
            "raw_message": message,
        }
    )



# ---------------------------------------------------------------------------
# Readiness check: tells the app (at startup) whether an SOS would actually work.
# ---------------------------------------------------------------------------
@app.route("/api/readiness")
def readiness():
    settings = load_user("settings", {}) or {}
    contacts = [
        (settings.get(f"contact{i}Phone"), settings.get(f"contact{i}Email"))
        for i in (1, 2, 3)
    ]
    has_contacts = any(p or e for p, e in contacts)
    has_email_contact = any(e for _, e in contacts)
    email_channel = bool(
        (os.environ.get("BREVO_API_KEY") and os.environ.get("BREVO_SENDER_EMAIL"))
        or (os.environ.get("SMTP_EMAIL") and os.environ.get("SMTP_PASSWORD"))
    )
    sms_channel = bool(os.environ.get("TWILIO_ACCOUNT_SID") and os.environ.get("TWILIO_AUTH_TOKEN"))
    return jsonify(
        {
            "has_contacts": has_contacts,
            "has_email_contact": has_email_contact,
            "email_channel": email_channel,
            "sms_channel": sms_channel,
            "ai_configured": gemini_service.client is not None,
            "persistent_storage": _engine is not None,
        }
    )


# ---------------------------------------------------------------------------
# Live location sharing after an SOS. The link contains a random token that
# only the person's contacts receive; it stops working after 2 hours.
# ---------------------------------------------------------------------------
TRACK_TTL = 2 * 60 * 60


def _track_load(token):
    if not re.match(r"^[0-9a-f]{32}$", token or ""):
        return None
    if _engine is not None:
        rec = db_get("_track", token)
    else:
        rec = _TRACK_MEM.get(token)
    if rec and time.time() - rec.get("started", 0) > TRACK_TTL:
        return None
    return rec


def _track_save(token, rec):
    if _engine is not None:
        db_set("_track", token, rec)
    else:
        _TRACK_MEM[token] = rec


_TRACK_MEM = {}


@app.route("/api/track/start", methods=["POST"])
def track_start():
    data = request.get_json(silent=True) or {}
    token = uuid.uuid4().hex
    rec = {
        "started": time.time(),
        "name": (data.get("name") or "")[:60],
        "lat": data.get("latitude"),
        "lng": data.get("longitude"),
        "updated": time.time(),
        "active": True,
    }
    _track_save(token, rec)
    return jsonify({"success": True, "token": token, "url": request.host_url + "track/" + token})


@app.route("/api/track/update", methods=["POST"])
def track_update():
    data = request.get_json(silent=True) or {}
    token = data.get("token", "")
    rec = _track_load(token)
    if not rec:
        return jsonify({"success": False, "expired": True}), 404
    try:
        lat, lng = float(data.get("latitude")), float(data.get("longitude"))
    except (TypeError, ValueError):
        return jsonify({"success": False}), 400
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return jsonify({"success": False}), 400
    if data.get("stop"):
        rec["active"] = False
    rec.update({"lat": lat, "lng": lng, "updated": time.time()})
    _track_save(token, rec)
    return jsonify({"success": True})


@app.route("/api/track/<token>.json")
def track_json(token):
    rec = _track_load(token)
    if not rec:
        return jsonify({"found": False}), 404
    return jsonify(
        {
            "found": True,
            "name": rec.get("name", ""),
            "lat": rec.get("lat"),
            "lng": rec.get("lng"),
            "seconds_ago": int(time.time() - rec.get("updated", 0)),
            "active": rec.get("active", True),
        }
    )


TRACK_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Live location</title>
<style>body{font-family:system-ui,sans-serif;background:#0d1117;color:#e6edf3;margin:0;padding:24px;max-width:560px;margin:auto}
h1{font-size:1.4rem}.card{background:#161b22;border-radius:12px;padding:16px;margin:16px 0}
a.btn{display:block;text-align:center;background:#238636;color:#fff;padding:16px;border-radius:10px;text-decoration:none;font-size:1.1rem}
.muted{opacity:.7}</style></head><body>
<h1 id="title">Live location</h1>
<div class="card"><div id="status">Loading...</div><div id="ago" class="muted"></div></div>
<a class="btn" id="map" href="#" style="display:none">Open in Google Maps</a>
<p class="muted">This page updates every 10 seconds and stops working 2 hours after the alert.</p>
<script>
const token = location.pathname.split("/").pop();
async function tick(){
  try{
    const r = await fetch("/api/track/"+token+".json"); 
    if(!r.ok){document.getElementById("status").textContent="This link has expired or is not valid.";return;}
    const d = await r.json();
    document.getElementById("title").textContent = (d.name||"Someone")+" - live location";
    if(d.lat==null){document.getElementById("status").textContent="Waiting for a location...";}
    else{
      document.getElementById("status").textContent = d.active ? "Location is being shared." : "Sharing has stopped. This is the last known location.";
      document.getElementById("ago").textContent = "Last updated "+d.seconds_ago+" seconds ago";
      const m=document.getElementById("map"); m.href="https://maps.google.com/?q="+d.lat+","+d.lng; m.style.display="block";
    }
  }catch(e){document.getElementById("status").textContent="Connection problem, retrying...";}
}
tick(); setInterval(tick,10000);
</script></body></html>"""


@app.route("/track/<token>")
def track_page(token):
    return Response(TRACK_PAGE, mimetype="text/html")


# ---------------------------------------------------------------------------
# Currency (Indian rupee) identification from the camera.
# ---------------------------------------------------------------------------
@app.route("/api/currency", methods=["POST"])
def identify_currency():
    if "image" not in request.files:
        return jsonify({"success": False, "message": "No image received."}), 400
    if gemini_service.client is None:
        return jsonify({"success": False, "message": "Currency reading is unavailable. The AI service is not configured."})

    image = request.files["image"]
    image_bytes = image.read()
    mime = image.mimetype if (image.mimetype or "").startswith("image/") else "image/jpeg"

    prompt = (
        "You are helping a blind person identify money. Look at the image and identify every "
        "Indian rupee banknote or coin visible. Reply in one or two short spoken sentences, "
        "for example: 'This is a 500 rupee note.' or 'I can see a 10 rupee note and a 5 rupee coin. "
        "Total 15 rupees.' If the denomination is not clearly visible, say so and ask them to hold "
        "the note flat, closer, and in good light. Never guess a denomination you cannot see. "
        "If there is no money in the image, say that."
    )
    try:
        response = gemini_service.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type=mime)],
        )
        text = (response.text or "").strip()
        if not text:
            return jsonify({"success": False, "message": "I could not read the money. Please try again."})
        return jsonify({"success": True, "text": text})
    except Exception as e:
        logging.error("Currency identification failed: %s", e)
        return jsonify({"success": False, "message": "Sorry, I could not identify the money right now."})


GENERIC_PLACE_TERMS = {
    "library", "hospital", "school", "restaurant", "pharmacy", "bank",
    "grocery store", "gas station", "petrol pump", "shopping mall", "mall", "park", "gym",
    "university", "college", "airport", "train station", "railway station",
    "bus station", "bus stand", "hotel", "cinema", "movie theater", "coffee shop",
    "post office", "temple", "mosque", "church", "police station", "atm",
    "toilet", "restroom", "supermarket", "clinic", "market",
}


def is_generic_place(address):
    a = address.lower().strip()
    if a in GENERIC_PLACE_TERMS:
        return True
    if a.endswith("ies") and a[:-3] + "y" in GENERIC_PLACE_TERMS:
        return True
    return a.endswith("s") and a[:-1] in GENERIC_PLACE_TERMS


def enhance_search_terms(address):
    """Clean up a spoken destination. (Nominatim does not understand
    'near me', so nearby-ness is handled with a bounded viewbox instead.)"""
    a = re.sub(r"^(the|a|an)\s+", "", address.strip(), flags=re.I)
    a = re.sub(r"\s+(near me|nearby|near here)$", "", a, flags=re.I)
    return a or address


# Free OpenStreetMap-based navigation. No API key, no billing account.
#
# - Nominatim (nominatim.openstreetmap.org) for geocoding/search.
# - FOSSGIS's public OSRM instance (routing.openstreetmap.de) for
#   pedestrian ("foot") turn-by-turn routing.
#
# Both are shared community infrastructure with a strict usage policy:
# max ~1 request/second, a real identifying User-Agent, and no heavy/
# scripted scraping. We stay well within that since this endpoint only
# fires when a person actually asks to navigate somewhere. If AIVI ever
# gets heavy usage, self-hosting Nominatim/OSRM (or moving to a paid
# provider) is the right next step - see:
# https://operations.osmfoundation.org/policies/nominatim/
# https://github.com/fossgis-routing-server
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_FOOT_URL = "https://routing.openstreetmap.de/routed-foot/route/v1/foot"
OSM_USER_AGENT = "AIVI-VoiceNavigation/1.0 (accessibility assistant; contact via app settings)"


def _nominatim_search(query, near_lat, near_lng, delta, bounded):
    params = {"q": query, "format": "jsonv2", "limit": 1, "addressdetails": 0}
    if near_lat is not None and near_lng is not None:
        params["viewbox"] = (
            f"{near_lng-delta},{near_lat+delta},{near_lng+delta},{near_lat-delta}"
        )
        params["bounded"] = 1 if bounded else 0
    response = requests.get(
        NOMINATIM_URL, params=params, headers={"User-Agent": OSM_USER_AGENT}, timeout=12
    )
    response.raise_for_status()
    return response.json()


def geocode_address_osm(address, near_lat=None, near_lng=None):
    """Geocode a spoken place name with Nominatim. Generic words like
    'pharmacy' are searched only within ~10 km of the user (so you get the
    closest one, not one in another city); specific names/addresses are only
    biased towards the user's area."""
    try:
        query = enhance_search_terms(address)
        results = []
        have_pos = near_lat is not None and near_lng is not None

        if have_pos and is_generic_place(query):
            results = _nominatim_search(query, near_lat, near_lng, 0.1, True)
            if not results:
                results = _nominatim_search(query, near_lat, near_lng, 0.4, True)
        if not results:
            results = _nominatim_search(query, near_lat, near_lng, 0.5, False)

        if not results:
            logging.warning(f"No Nominatim results for: {address}")
            return {
                "error": "ZERO_RESULTS",
                "message": f'Could not find "{address}" near you. Please try a more specific name or address.',
            }

        top = results[0]
        return {
            "lat": float(top["lat"]),
            "lng": float(top["lon"]),
            "display_name": top.get("display_name", address),
        }

    except requests.exceptions.Timeout:
        logging.error("Nominatim geocoding timeout")
        return {"error": "TIMEOUT", "message": "Navigation service timeout"}
    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP error geocoding via Nominatim: {e}")
        return {"error": "REQUEST_FAILED", "message": "Navigation service unavailable"}
    except Exception as e:
        logging.error(f"Nominatim geocoding error: {e}")
        return {"error": "UNKNOWN", "message": "Unable to find location"}


def get_osrm_directions(origin, destination):
    """Get walking directions from the FOSSGIS public OSRM instance
    (pedestrian/foot profile). origin and destination are 'lat,lng'."""
    try:
        origin_lat, origin_lng = origin.split(",")
        dest_lat, dest_lng = destination.split(",")

        # OSRM expects lon,lat order (opposite of the lat,lng convention
        # used elsewhere in this app), and semicolon-separated waypoints.
        coords = f"{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
        url = f"{OSRM_FOOT_URL}/{coords}"
        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "true",
        }
        headers = {"User-Agent": OSM_USER_AGENT}

        logging.info(f"Getting OSRM walking directions from {origin} to {destination}")
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()

        try:
            data = response.json()
        except Exception as e:
            logging.error(f"Failed to parse OSRM response as JSON: {e}")
            logging.error(f"Response content: {response.text[:500]}")
            return None

        code = data.get("code")
        if code != "Ok":
            if code == "NoRoute":
                logging.warning(f"No walking route found from {origin} to {destination}")
                return {"error": "ZERO_RESULTS", "message": "Route not available"}
            elif code in ("InvalidInput", "NoSegment"):
                return {
                    "error": "NOT_FOUND",
                    "message": "Location not found, please try again.",
                }
            else:
                logging.error(f"OSRM API error: {code} - {data.get('message')}")
                return {"error": code, "message": "Route not available"}

        if not data.get("routes") or len(data["routes"]) == 0:
            logging.error("OSRM returned no routes")
            return None

        route = data["routes"][0]
        if not route.get("legs") or len(route["legs"]) == 0:
            logging.error("OSRM route has no legs")
            return None

        return data

    except requests.exceptions.Timeout:
        logging.error("OSRM directions timeout")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP error getting OSRM directions: {e}")
        return None
    except Exception as e:
        logging.error(f"OSRM directions error: {e}")
        return None


def build_instruction_from_maneuver(maneuver, street_name):
    """Turn an OSRM maneuver (type + modifier) into a plain-English,
    voice-friendly instruction. OSRM doesn't provide ready-made prose
    like Google's html_instructions did, so we build it ourselves from
    https://project-osrm.org/docs/v5.24.0/api/#stepmaneuver-object"""
    m_type = maneuver.get("type", "continue")
    modifier = maneuver.get("modifier")
    name = street_name.strip() if street_name else ""
    onto_name = f" onto {name}" if name else ""
    along_name = f" along {name}" if name else ""

    if m_type == "depart":
        if modifier:
            return f"Head {modifier}{along_name}".strip()
        return f"Start walking{along_name}".strip() or "Start walking"

    if m_type == "arrive":
        if modifier in ("left", "right"):
            return f"You have arrived, your destination is on the {modifier}"
        return "You have arrived at your destination"

    if m_type == "turn":
        if modifier:
            return f"Turn {modifier}{onto_name}".strip()
        return f"Continue{onto_name}".strip() or "Continue straight"

    if m_type == "new name":
        return f"Continue{onto_name}".strip() or "Continue straight"

    if m_type == "merge":
        return f"Merge{onto_name}".strip() or "Merge"

    if m_type in ("on ramp", "off ramp"):
        return f"Take the {m_type}{onto_name}".strip()

    if m_type == "fork":
        if modifier:
            return f"Keep {modifier} at the fork{onto_name}".strip()
        return f"Continue at the fork{onto_name}".strip()

    if m_type == "end of road":
        if modifier:
            return f"Turn {modifier} at the end of the road{onto_name}".strip()
        return f"Continue{onto_name}".strip() or "Continue straight"

    if m_type in ("roundabout", "rotary", "roundabout turn"):
        exit_num = maneuver.get("exit")
        if exit_num:
            return f"At the roundabout, take exit {exit_num}{onto_name}".strip()
        return f"Go through the roundabout{onto_name}".strip()

    if m_type == "continue":
        if modifier and modifier != "straight":
            return f"Continue {modifier}{onto_name}".strip()
        return f"Continue straight{along_name}".strip() or "Continue straight"

    # Fallback for any maneuver type not explicitly handled above
    return f"Continue{onto_name}".strip() or "Continue straight"


def parse_osrm_directions(directions_data, destination_name):
    """Parse an OSRM /route response into the same shape the frontend
    already expects (previously produced from Google's Directions API)."""
    try:
        if not directions_data.get("routes") or len(directions_data["routes"]) == 0:
            raise ValueError("No routes in OSRM response")

        route = directions_data["routes"][0]

        legs = route.get("legs", [])
        if not legs:
            raise ValueError("Missing route legs")

        total_distance_m = route.get("distance", 0)
        total_duration_s = route.get("duration", 0)

        steps = []
        step_number = 1

        for leg in legs:
            leg_steps = leg.get("steps", [])

            for step in leg_steps:
                distance_m = step.get("distance", 0)
                duration_s = step.get("duration", 0)
                street_name = step.get("name", "")
                maneuver = step.get("maneuver", {})

                instruction = build_instruction_from_maneuver(maneuver, street_name)

                step_distance = (
                    f"{distance_m:.0f} m"
                    if distance_m < 1000
                    else f"{distance_m/1000:.1f} km"
                )
                step_duration = (
                    f"{duration_s//60:.0f} min"
                    if duration_s >= 60
                    else f"{duration_s:.0f} sec"
                )

                # OSRM gives maneuver location as [lon, lat]; the step's
                # own geometry (if present) gives start/end. We fall back
                # to the maneuver point for both when geometry is absent.
                maneuver_location = maneuver.get("location", [0, 0])
                start_location = {
                    "lat": maneuver_location[1],
                    "lng": maneuver_location[0],
                }
                geometry_coords = step.get("geometry", {}).get("coordinates", [])
                if geometry_coords:
                    end_lon, end_lat = geometry_coords[-1]
                    end_location = {"lat": end_lat, "lng": end_lon}
                else:
                    end_location = start_location

                step_data = {
                    "step_number": step_number,
                    "instruction": clean_instruction_text(instruction),
                    "distance": step_distance,
                    "duration": step_duration,
                    "distance_meters": distance_m,
                    "distance_value": distance_m,  # Add for frontend compatibility
                    "duration_seconds": duration_s,
                    "start_location": start_location,
                    "end_location": end_location,
                    "maneuver": maneuver.get("type", "straight"),
                    "travel_mode": "WALKING",
                }
                steps.append(step_data)
                step_number += 1

        total_distance = (
            f"{total_distance_m:.0f} m"
            if total_distance_m < 1000
            else f"{total_distance_m/1000:.1f} km"
        )
        total_duration = (
            f"{total_duration_s//60:.0f} min"
            if total_duration_s >= 60
            else f"{total_duration_s:.0f} sec"
        )

        if not steps:
            steps.append(
                {
                    "step_number": 1,
                    "instruction": f"Walk to {destination_name}",
                    "distance": total_distance,
                    "duration": total_duration,
                    "distance_meters": total_distance_m,
                    "duration_seconds": total_duration_s,
                    "start_location": {"lat": 0, "lng": 0},
                    "end_location": {"lat": 0, "lng": 0},
                    "maneuver": "straight",
                    "travel_mode": "WALKING",
                }
            )

        # Full route geometry as [lat, lng] pairs, for drawing the route
        # on a Leaflet map (replaces Google's encoded overview_polyline).
        route_coords = route.get("geometry", {}).get("coordinates", [])
        overview_path = [[lat, lng] for lng, lat in route_coords]

        start_address = "Current Location"
        end_address = destination_name

        return {
            "success": True,
            "route": {
                "distance": total_distance,
                "duration": total_duration,
                "distance_meters": total_distance_m,
                "duration_seconds": total_duration_s,
                "steps": steps,
                "start_address": start_address,
                "end_address": end_address,
                "overview_path": overview_path,
            },
        }

    except (KeyError, IndexError, TypeError) as e:
        logging.error(f"Error parsing OSRM directions data: {e}")
        logging.error(
            f"OSRM response structure keys: {list(directions_data.keys()) if isinstance(directions_data, dict) else 'Not a dict'}"
        )
        raise ValueError("Invalid OSRM directions data format")


def clean_instruction_text(instruction):
    """Clean and optimize navigation instructions for voice"""
    if not instruction:
        return "Continue straight"

    # Clean up text
    clean_text = instruction.strip()

    # Make instructions more voice-friendly
    clean_text = clean_text.replace("toward", "towards")
    clean_text = clean_text.replace(
        "Destination will be on the right", "Your destination will be on the right"
    )
    clean_text = clean_text.replace(
        "Destination will be on the left", "Your destination will be on the left"
    )
    clean_text = clean_text.replace("Continue on", "Continue along")

    return clean_text


@app.route("/api/gemini/chat", methods=["POST"])
def gemini_chat():

    data = request.get_json(silent=True) or {}

    question = data.get("question", "")
    scene = data.get("scene", "")
    objects = data.get("objects", [])
    language = data.get("language", "en-IN")

    if not question.strip():
        return jsonify({"success": False, "answer": ""}), 400

    answer = gemini_service.answer_scene_question(question, scene, objects, language)

    return jsonify({"success": True, "answer": answer})


@app.route("/api/scene/describe", methods=["POST"])
def describe_scene():

    if "image" not in request.files:
        return jsonify({"success": False, "message": "No image received."})

    if gemini_service.client is None:
        return jsonify({"success": False, "description": "Scene description is unavailable. The AI service is not configured."})

    image = request.files["image"]

    objects = request.form.get("objects", "")

    image_bytes = image.read()
    mime = image.mimetype if (image.mimetype or "").startswith("image/") else "image/jpeg"

    prompt = f"""
You are BlindMate, an AI assistant for visually impaired users.

Detected objects:
{objects}

Analyze the image and describe:

1. What environment is this?
2. Where are the important objects?
3. Are there any people?
4. Are there any obstacles?
5. Is the path clear?
6. Mention only important things.
7. Keep the answer under 80 words.
8. Speak naturally like helping a blind person.
"""

    try:

        response = gemini_service.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type=mime)],
        )

        return jsonify({"success": True, "description": response.text})

    except Exception as e:

        import traceback

        traceback.print_exc()

        return jsonify({"success": False, "description": "Sorry, I could not describe the scene right now."})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_ENV") == "development")