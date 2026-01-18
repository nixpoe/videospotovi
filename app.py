from flask import Flask, request, jsonify, render_template, session, url_for, redirect
from authlib.integrations.flask_client import OAuth
from functools import wraps
from os import environ as env
from dotenv import load_dotenv
import json
import csv

load_dotenv()

app = Flask(__name__)
app.secret_key = env.get("APP_SECRET_KEY")

oauth = OAuth(app)
auth0 = oauth.register(
    'auth0',
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    api_base_url=f'https://{env.get("AUTH0_DOMAIN")}',
    access_token_url=f'https://{env.get("AUTH0_DOMAIN")}/oauth/token',
    authorize_url=f'https://{env.get("AUTH0_DOMAIN")}/authorize',
    jwks_uri=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/jwks.json',
    client_kwargs={
        'scope': 'openid profile email'
    }
)

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'profile' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def load_data():
    with open('music_videos.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open('music_videos.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

@app.route('/login')
def login():
    return auth0.authorize_redirect(
        redirect_uri=url_for('callback', _external=True)
    )

@app.route('/callback')
def callback():
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()
    session['profile'] = userinfo
    return redirect(url_for('profile'))

@app.route('/profile')
@requires_auth
def profile():
    return render_template('profile.html', userinfo=session['profile'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(
        f'https://{env.get("AUTH0_DOMAIN")}/v2/logout?' +
        f'client_id={env.get("AUTH0_CLIENT_ID")}&' +
        f'returnTo={url_for("home", _external=True)}'
    )

@app.route('/refresh-exports')
@requires_auth
def refresh_exports():
    videos = load_data()
    
    # Export to JSON
    with open('static/exports/music_videos_export.json', 'w', encoding='utf-8') as f:
        json.dump(videos, f, indent=2, ensure_ascii=False)
    
    # Export to CSV
    with open('static/exports/music_videos_export.csv', 'w', encoding='utf-8', newline='') as f:
        if videos:
            # Collect all unique field names from all videos
            all_fieldnames = set()
            for video in videos:
                all_fieldnames.update(video.keys())
            
            # Convert to sorted list for consistent ordering
            fieldnames = sorted(list(all_fieldnames))
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for video in videos:
                row = video.copy()
                if 'izvodaci' in row and isinstance(row['izvodaci'], list):
                    row['izvodaci'] = ', '.join(row['izvodaci'])
                writer.writerow(row)
    
    return redirect(url_for('home'))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/datatable')
def datatable():
    videos = load_data()
    return render_template('datatable.html', videos=videos)

# CRUD endpoints
@app.route('/api/v1/spots', methods=['GET'])
def get_all_videos():
    videos = load_data()
    return {
        "status": "OK",
        "message": "Dohvaćeni svi glazbeni spotovi",
        "response": videos
    }, 200

def add_jsonld_context(video):
    """Add JSON-LD context to video object"""
    return {
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "name": video.get("Naslov"),
        "director": {
            "@type": "Person",
            "name": video.get("Redatelj")
        },
        "duration": f"PT{video.get('Trajanje_sekunde')}S",
        "uploadDate": video.get("Datum"),
        "genre": video.get("Zanr"),
        "interactionStatistic": [
            {
                "@type": "InteractionCounter",
                "interactionType": "http://schema.org/WatchAction",
                "userInteractionCount": video.get("pregledi")
            },
            {
                "@type": "InteractionCounter",
                "interactionType": "http://schema.org/LikeAction",
                "userInteractionCount": video.get("lajkovi")
            }
        ],
        **video  # Include all original fields
    }

@app.route('/api/v1/spots/<id>', methods=['GET'])
def get_video(id):
    videos = load_data()
    video = next((v for v in videos if v.get('id') == id), None)
    if not video:
        return {
            "status": "Not Found",
            "message": f"Video s ID-em {id} nije pronađen",
            "response": None
        }, 404
    
    # Add JSON-LD context
    video_with_context = add_jsonld_context(video)
    
    return {
        "status": "OK",
        "message": "Video uspješno dohvaćen",
        "response": video_with_context
    }, 200

@app.route('/api/v1/spots', methods=['POST'])
def create_video():
    videos = load_data()
    new_video = request.get_json()
    
    # Validate required fields
    required_fields = ["Naslov", "Redatelj", "Label", "Datum", "Trajanje_sekunde", 
                      "Zanr", "pregledi", "komentari", "lajkovi", "izvodaci"]
    
    if not all(field in new_video for field in required_fields):
        return {
            "status": "Bad Request",
            "message": "Nedostaju obavezna polja",
            "response": None
        }, 400
        
    videos.append(new_video)
    save_data(videos)
    return {
        "status": "Created",
        "message": "Novi video uspješno dodan",
        "response": new_video
    }, 201

@app.route('/api/v1/spots/<id>', methods=['PUT'])
def update_video(id):
    videos = load_data()
    video_data = request.get_json()
    video_index = next((index for (index, v) in enumerate(videos) if v['id'] == id), None)
    
    if video_index is None:
        return {
            "status": "Not Found",
            "message": f"Video s ID-em {id} nije pronađen",
            "response": None
        }, 404
        
    videos[video_index].update(video_data)
    save_data(videos)
    return {
        "status": "OK",
        "message": "Video uspješno ažuriran",
        "response": videos[video_index]
    }, 200

@app.route('/api/v1/spots/<id>', methods=['DELETE'])
def delete_video(id):
    videos = load_data()
    video_index = next((index for (index, v) in enumerate(videos) if v['id'] == id), None)
    
    if video_index is None:
        return {
            "status": "Not Found",
            "message": f"Video s ID-em {id} nije pronađen",
            "response": None
        }, 404
        
    deleted_video = videos.pop(video_index)
    save_data(videos)
    return {
        "status": "OK",
        "message": "Video uspješno obrisan",
        "response": deleted_video
    }, 200

# Additional GET endpoints
@app.route('/api/v1/spots/by-genre/<genre>', methods=['GET'])
def get_videos_by_genre(genre):
    videos = load_data()
    filtered_videos = [v for v in videos if genre.lower() in v['Zanr'].lower()]
    return {
        "status": "OK",
        "message": f"Pronađeni spotovi žanra: {genre}",
        "response": filtered_videos
    }, 200

@app.route('/api/v1/spots/by-label/<label>', methods=['GET'])
def get_videos_by_label(label):
    videos = load_data()
    filtered_videos = [v for v in videos if label.lower() in v['Label'].lower()]
    return {
        "status": "OK",
        "message": f"Pronađeni spotovi izdavačke kuće: {label}",
        "response": filtered_videos
    }, 200

@app.route('/api/v1/spots/most-viewed', methods=['GET'])
def get_most_viewed_videos():
    videos = load_data()
    sorted_videos = sorted(videos, key=lambda x: x['pregledi'], reverse=True)
    limit = request.args.get('limit', default=10, type=int)
    return {
        "status": "OK",
        "message": f"Dohvaćeno {limit} najgledanijih spotova",
        "response": sorted_videos[:limit]
    }, 200

@app.route('/api/docs', methods=['GET'])
def get_api_docs():
    with open('openapi.json', 'r', encoding='utf-8') as f:
        spec = json.load(f)
    return {
        "status": "OK",
        "message": "OpenAPI specifikacija uspješno dohvaćena",
        "response": spec
    }, 200

if __name__ == '__main__':
    app.run(debug=True)

