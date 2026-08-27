import os
import logging
import requests
import re
import json
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from flask import send_from_directory
# Load variables from .env into the real process environment. Without
# this, every os.environ.get(...) call below (Gemini key, SMTP
# credentials, Maps key, etc.) silently returns None even if they're set
# in .env - Flask's dev server does NOT do this automatically.
load_dotenv()

from flask import Flask, request, jsonify, render_template, session, send_from_directory
from flask_cors import CORS
from gemini_service import GeminiService

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
app.secret_key = os.environ.get("SESSION_SECRET", "blindmate-secret-key-2024")

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


# Static files are now served automatically by Flask from /static folder
SETTINGS_FILE = "user_settings.json"


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
            contents=[ocr_prompt, {"mime_type": "image/jpeg", "data": image_bytes}],
        )

        text = response.text.strip() if response.text else ""

        return jsonify(
            {"success": True, "text": text if text else "No text detected."}
        )

    except Exception as e:
        import traceback

        traceback.print_exc()

        return jsonify({"success": False, "message": str(e)}), 500


MEMORY_FILE = "memory.json"


@app.route("/api/translate", methods=["POST"])
def translate():

    data = request.get_json()

    text = data.get("text", "")

    language = data.get("language", "en-IN")

    if not text:
        return jsonify({"success": False, "translated": ""})

    # English doesn't need translation
    if language == "en-IN":
        return jsonify({"success": True, "translated": text})

    language_map = {
        "en-IN": "English",
        "hi-IN": "Hindi",
        "kn-IN": "Kannada",
        "ta-IN": "Tamil",
        "te-IN": "Telugu",
        "bn-IN": "Bengali",
        "mr-IN": "Marathi",
        "gu-IN": "Gujarati",
    }

    target_language = language_map.get(language, "English")

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

        return jsonify({"success": True, "translated": response.text.strip()})

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
        with open(path, "r") as f:
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
    data = request.json

    memories = load_json_file(MEMORY_FILE, [])

    object_name = (data.get("object") or "").strip().lower()

    # Replace any existing entry for this object with the fresh sighting
    memories = [
        m for m in memories if (m.get("object") or "").strip().lower() != object_name
    ]
    memories.append(data)

    with open(MEMORY_FILE, "w") as f:
        json.dump(memories, f, indent=4)

    return jsonify({"success": True})


@app.route("/api/memory")
def get_memory():
    return jsonify(load_json_file(MEMORY_FILE, []))


PLACES_FILE = "places.json"


@app.route("/api/memory/place/save", methods=["POST"])
def save_place():
    """
    Save a named place (e.g. "bathroom", "kitchen", "front door") with the
    user's current GPS coordinates, so it can be recalled later with
    "where is the bathroom" / "take me to the bathroom".
    """
    data = request.json

    name = (data.get("name") or "").strip()
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if not name or latitude is None or longitude is None:
        return jsonify({"success": False, "message": "Missing name or coordinates."}), 400

    places = load_json_file(PLACES_FILE, [])

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

    with open(PLACES_FILE, "w") as f:
        json.dump(places, f, indent=4)

    return jsonify({"success": True})


@app.route("/api/memory/places")
def get_places():
    return jsonify(load_json_file(PLACES_FILE, []))


@app.route("/api/settings", methods=["GET"])
def get_settings():
    return jsonify(load_json_file(SETTINGS_FILE, {}))


@app.route("/api/settings", methods=["POST"])
def save_settings():

    data = request.json

    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)

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
        return False, "SMTP_EMAIL/SMTP_PASSWORD not set in .env"

    subject = (
        f"Urgent: {user_name} needs you to call them"
        if user_name
        else "Urgent: Please call your contact"
    )

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


@app.route("/api/emergency", methods=["POST"])
def emergency():

    data = request.json or {}
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    contacts = data.get("contacts", [])
    user_name = (data.get("user_name") or "").strip()
    user_phone = (data.get("user_phone") or "").strip()

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


def enhance_search_terms(address):
    """Enhance generic search terms for better geocoding results"""
    address_lower = address.lower().strip()

    # Add "near me" to generic terms to get local results
    generic_terms = {
        "library": "library near me",
        "hospital": "hospital near me",
        "school": "school near me",
        "restaurant": "restaurant near me",
        "pharmacy": "pharmacy near me",
        "bank": "bank near me",
        "grocery store": "grocery store near me",
        "gas station": "gas station near me",
        "shopping mall": "shopping mall near me",
        "park": "park near me",
        "gym": "gym near me",
        "university": "university near me",
        "college": "college near me",
        "airport": "airport near me",
        "train station": "train station near me",
        "bus station": "bus station near me",
        "hotel": "hotel near me",
        "cinema": "cinema near me",
        "movie theater": "movie theater near me",
        "coffee shop": "coffee shop near me",
        "post office": "post office near me",
    }

    # Check if it's a generic term
    for term, enhanced in generic_terms.items():
        if address_lower == term or address_lower == term + "s":
            return enhanced

    # If it's already a specific address, return as is
    return address


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


def geocode_address_osm(address, near_lat=None, near_lng=None):
    """Geocode an address/place name using Nominatim, optionally biased
    towards a nearby point so ambiguous queries like "pharmacy" or
    "library" resolve to the closest sensible match."""
    try:
        enhanced_address = enhance_search_terms(address)

        params = {
            "q": enhanced_address,
            "format": "jsonv2",
            "limit": 1,
            "addressdetails": 0,
        }

        # Bias results towards the user's location with a generous
        # viewbox (~0.5 degrees, roughly 50km) without hard-excluding
        # results outside it - keeps "take me to the Eiffel Tower"
        # working even if the user isn't in Paris.
        if near_lat is not None and near_lng is not None:
            params["viewbox"] = (
                f"{near_lng-0.5},{near_lat+0.5},{near_lng+0.5},{near_lat-0.5}"
            )
            params["bounded"] = 0

        headers = {"User-Agent": OSM_USER_AGENT}

        logging.info(f"Geocoding via Nominatim: {address} (enhanced: {enhanced_address})")
        response = requests.get(
            NOMINATIM_URL, params=params, headers=headers, timeout=30
        )
        response.raise_for_status()

        try:
            results = response.json()
        except Exception as e:
            logging.error(f"Failed to parse Nominatim response: {e}")
            return {"error": "PARSE_ERROR", "message": "Unable to find location"}

        if not results:
            logging.warning(f"No Nominatim results for: {address}")
            return {
                "error": "ZERO_RESULTS",
                "message": f'Could not find "{address}" near your location. Please try a more specific address.',
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
        logging.error(f"HTTP error geocoding address via Nominatim: {e}")
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
        response = requests.get(url, params=params, headers=headers, timeout=30)
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

    data = request.get_json()

    question = data.get("question", "")

    scene = data.get("scene", "")

    objects = data.get("objects", [])

    language = data.get("language", "en-IN")

    language_instruction = (
        "Reply ONLY in Hindi." if language == "hi-IN" else "Reply ONLY in English."
    )

    prompt = f"""
{language_instruction}

You are BlindMate,
an AI assistant for visually impaired people.

Question:

{question}

Scene:

{scene}

Objects:

{objects}

Answer naturally.
Keep answers short.
"""

    answer = gemini_service.answer_scene_question(prompt, scene, objects, language)

    return jsonify({"success": True, "answer": answer})


@app.route("/api/scene/describe", methods=["POST"])
def describe_scene():

    if "image" not in request.files:
        return jsonify({"success": False, "message": "No image received."})

    image = request.files["image"]

    objects = request.form.get("objects", "")

    image_bytes = image.read()

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
            contents=[prompt, {"mime_type": "image/jpeg", "data": image_bytes}],
        )

        return jsonify({"success": True, "description": response.text})

    except Exception as e:

        import traceback

        traceback.print_exc()

        return jsonify({"success": False, "description": str(e)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)