import os
from django.shortcuts import render,redirect
from django.http import HttpResponse
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from django.views.decorators.csrf import csrf_exempt
from textblob import TextBlob
import random


# Create your views here.


CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')

SCOPE= "user-library-read playlist-modify-public"

def spotify_login(request):
    sp_oauth=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE
    )
    auth_url=sp_oauth.get_authorize_url()
    return redirect(auth_url)

def spotify_callback(request):
    sp_oauth = SpotifyOAuth(client_id=CLIENT_ID,
                            client_secret=CLIENT_SECRET,
                            redirect_uri=REDIRECT_URI,
                            scope=SCOPE)
    code = request.GET.get('code')
    if code:
        token_info = sp_oauth.get_access_token(code)
        access_token = token_info['access_token']
        request.session['access_token'] = access_token
        return HttpResponse(f"Access Token Saved in Session! 🔥<br>{access_token[:20]}...")
    else:
        return HttpResponse("Spotify authorization failed 😢")
    
def home(request):
    return render(request,'index.html')
@csrf_exempt
def get_recommendations(request):
    if request.method == "POST":
        mood_text = request.POST.get("mood_text")

        blob = TextBlob(mood_text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity

        target_valence = (polarity + 1) / 2
        target_energy = subjectivity

        context = {
            "text": mood_text,
            "valence": round(target_valence * 100),
            "energy": round(target_energy * 100),
        }

        access_token = request.session.get('access_token')
        if not access_token:
            return redirect("spotify_login")

        sp = spotipy.Spotify(auth=access_token)

        safe_genres = ["pop", "rock", "dance", "edm", "hip-hop", "acoustic", "metal", "electronic"]

        max_attempts = 5
        recs = None

        for attempt in range(max_attempts):
            try:
                seed_genres = random.sample(safe_genres, 3)
                val = round(min(max(target_valence + random.uniform(-0.1, 0.1), 0.1), 0.9), 2)
                eng = round(min(max(target_energy + random.uniform(-0.1, 0.1), 0.1), 0.9), 2)

                recs = sp.recommendations(
                    seed_genres=seed_genres,
                    limit=10,
                    target_valence=val,
                    target_energy=eng,
                )

                if recs and recs['tracks']:
                    break

            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                continue

        if not recs or not recs['tracks']:
            return HttpResponse("😵 No recommendations for that mood! Try something else.")

        tracks = [
            {
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'url': track['external_urls']['spotify'],
                'preview': track['preview_url'],
                'image': track['album']['images'][0]['url']
            }
            for track in recs['tracks']
        ]

        context['tracks'] = tracks
        return render(request, "results.html", context)

