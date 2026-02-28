
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from collections import Counter
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_API_KEY = "AIzaSyD4qOtZ6pM84rqDEmdz9GQOHxECvf6Zj14"


summary_cache = {}

@app.get("/")
def home():
    return {"message": "FoodBuddy backend is running"}


@app.get("/restaurants")
def get_restaurants(lat: float, lng: float, radius: int = 5000):

    search_url = "https://places.googleapis.com/v1/places:searchNearby"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.rating,places.formattedAddress,places.location,places.photos,places.primaryTypeDisplayName,places.priceLevel"
    }

    body = {
        "includedTypes": ["restaurant"],
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": radius
            }
        }
    }

    response = requests.post(search_url, json=body, headers=headers)
    data = response.json()

    results = []

    for place in data.get("places", []):
        place_id = place.get("id")

        # Fetch phone number
        details_url = f"https://places.googleapis.com/v1/places/{place_id}"
        details_headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GOOGLE_API_KEY,
            "X-Goog-FieldMask": "nationalPhoneNumber"
        }

        details_response = requests.get(details_url, headers=details_headers)
        details_data = details_response.json()

        phone = details_data.get("nationalPhoneNumber")

        photo_url = None
        if place.get("photos"):
            photo_name = place["photos"][0]["name"]
            photo_url = f"https://places.googleapis.com/v1/{photo_name}/media?maxHeightPx=400&key={GOOGLE_API_KEY}"

        results.append({
            "id": place_id,
            "name": place.get("displayName", {}).get("text"),
            "rating": place.get("rating"),
            "address": place.get("formattedAddress"),
            "lat": place.get("location", {}).get("latitude"),
            "lng": place.get("location", {}).get("longitude"),
            "photo": photo_url,
            "phone": phone,
            "category": place.get("primaryTypeDisplayName", {}).get("text"),
            "priceLevel": place.get("priceLevel")
        })

    return results


@app.get("/summary")
def get_summary(place_id: str):

    if place_id in summary_cache:
        return summary_cache[place_id]

    details_url = f"https://places.googleapis.com/v1/places/{place_id}"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "reviews,editorialSummary"
    }

    response = requests.get(details_url, headers=headers)
    data = response.json()

    description = data.get("editorialSummary", {}).get("text", "")

    reviews = []
    for r in data.get("reviews", []):
        text = r.get("text", {}).get("text", "")
        reviews.append(text.lower())

    # Extract dish-like words (very basic NLP)
    dish_candidates = []

    for review in reviews:
        words = re.findall(r'\b[a-zA-Z]{4,}\b', review)
        dish_candidates.extend(words)

    common_words = Counter(dish_candidates).most_common(20)

    # Remove generic words
    stopwords = {"place", "restaurant", "food", "good", "great", "very", "nice", "staff", "service"}
    top_dishes = []

    for word, _ in common_words:
        if word not in stopwords:
            top_dishes.append(word.capitalize())
        if len(top_dishes) == 5:
            break

    result = {
        "description": description if description else "Popular local restaurant.",
        "top_dishes": top_dishes
    }

    summary_cache[place_id] = result

    return result

@app.get("/menu")
def get_menu(place_id: str):

    details_url = f"https://places.googleapis.com/v1/places/{place_id}"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "websiteUri,photos"
    }

    response = requests.get(details_url, headers=headers)
    data = response.json()

    website = data.get("websiteUri")

    photos = []
    if data.get("photos"):
        for p in data["photos"][:5]:
            photo_name = p["name"]
            photo_url = f"https://places.googleapis.com/v1/{photo_name}/media?maxHeightPx=1200&key={GOOGLE_API_KEY}"
            photos.append(photo_url)

    return {
        "website": website,
        "photos": photos
    }