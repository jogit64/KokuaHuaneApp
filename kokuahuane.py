from flask import Flask, request, render_template, jsonify, make_response
import os
import requests
from flask_cors import CORS, cross_origin
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
import re

load_dotenv() 


# Configuration de l'API pour la connexion à OpenAI.
api_key = os.getenv('OPENAI_API_KEY')
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

# Initialisation de l'application Flask.
app = Flask(__name__)



# Configuration de l'URI de la base de données à partir des variables d'environnement.
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace("postgres://", "postgresql://", 1)
app.config['DEBUG'] = True  # Active le mode debug, qui est utile pour le développement
app.config['LOGGING_LEVEL'] = 'DEBUG'  # Définit le niveau de logging à debug pour voir plus de détails dans les logs



# Affichage de l'URI de la base de données pour vérification
print("Database URI:", app.config['SQLALCHEMY_DATABASE_URI'])

db = SQLAlchemy(app)

# Initialisation de Flask-Migrate
migrate = Migrate(app, db)



# Configuration du secret pour JWT.
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
jwt = JWTManager(app)


# Configuration de CORS pour permettre les requêtes cross-origin.
CORS(app, supports_credentials=True, resources={
    r"/ask": {"origins": ["https://kokua.fr", "https://www.kokua.fr"]},
    r"/login": {"origins": ["https://kokua.fr", "https://www.kokua.fr"]},
    r"/register": {"origins": ["https://kokua.fr", "https://www.kokua.fr"]},  
    r"/interact": {"origins": ["https://kokua.fr", "https://www.kokua.fr"]} 
})


# Modèle utilisateur pour SQLAlchemy.
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)  # Assurez-vous que l'email est unique
    password = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(80), nullable=True)  # Pour le prénom ou pseudo affiché


    # Méthode pour vérifier le mot de passe.
    def check_password(self, password):
        return check_password_hash(self.password, password)

# Fonction pour ajouter un utilisateur à la base de données.
def add_user(email, password, display_name=None):
    hashed_password = generate_password_hash(password)
    new_user = User(email=email, password=hashed_password, display_name=display_name)
    db.session.add(new_user)
    db.session.commit()


# Fonction pour interroger l'API ChatGPT d'OpenAI.
# def ask_chatgpt(prompt):
#     data = {
#         'model': "gpt-4-turbo",
#         'messages': [{'role': 'user', 'content': prompt}],
#         'max_tokens': 150
#     }
#     response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)
#     json_response = response.json()
#     print("API Response:", json_response)
#     if 'choices' in json_response and json_response['choices']:
#         return json_response['choices'][0]['message']['content'].strip()
#     else:
#         return "Error: Unexpected response from OpenAI API"

# def ask_chatgpt(prompt, config_type):
#     # Chargement de la configuration du fichier JSON
#     with open('gpt_config.json', 'r') as config_file:
#         config_data = json.load(config_file)
    
#     config = config_data[config_type]
    
#     data = {
#         'model': config['model'],
#         'messages': [{'role': 'user', 'content': prompt}],
#         'max_tokens': config['max_tokens'],
#         'temperature': config['temperature'],
#         'top_p': config['top_p'],
#         'frequency_penalty': config['frequency_penalty'],
#         'presence_penalty': config['presence_penalty'],
#         'instructions': config['instructions']
#     }
#     response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)
#     json_response = response.json()
#     return json_response['choices'][0]['message']['content'].strip() if 'choices' in json_response else "Error: Unexpected response from OpenAI API"





# Route racine pour afficher et répondre aux questions.
@app.route('/', methods=['GET', 'POST'])
def hello():
    if request.method == 'POST':
        question = request.form['question']
        response = ask_chatgpt(question)
        return render_template('index.html', question=question, response=response)
    return render_template('index.html', question=None, response=None)

# Route pour connaitre la liste des utilisateurs.
@app.route('/users', methods=['GET'])
def list_users():
    try:
        users = User.query.all()  # Récupère tous les utilisateurs de la base de données
        users_data = [{'id': user.id, 'username': user.username} for user in users]
        return jsonify(users_data), 200
    except Exception as e:
        app.logger.error(f"Failed to fetch users: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Route pour enregistrer un nouvel utilisateur.
@app.route('/register', methods=['POST', 'OPTIONS'])
@cross_origin(origins=["https://kokua.fr", "https://www.kokua.fr"], supports_credentials=True)
def register():
    if request.method == 'OPTIONS':
        return {}, 200

    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    display_name = data.get('display_name', '')  # Utiliser un display name facultatif

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already in use"}), 409

    hashed_password = generate_password_hash(password)
    new_user = User(email=email, password=hashed_password, display_name=display_name)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User created successfully"}), 201


# Route pour le processus de connexion.
@app.route('/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'https://kokua.fr')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response

    if request.method == 'POST':
        email = request.json.get('email')
        password = request.json.get('password')

        user = User.query.filter_by(email=email).first()

        if user is None:
            return jsonify({"msg": "Email non trouvé"}), 404  # Email not found

        if not user.check_password(password):
            return jsonify({"msg": "Mot de passe invalide"}), 401  # Invalid password

        access_token = create_access_token(identity=user.email)
        return jsonify(access_token=access_token, displayName=user.display_name), 200



# Route pour poser des questions via l'API, protégée par JWT.
@app.route('/ask', methods=['POST', 'OPTIONS'])
@jwt_required(optional=True)
def ask():
    if request.method == 'OPTIONS':
        return {}, 200

    current_user = get_jwt_identity()
    question = request.json.get('question')
    response = ask_chatgpt(question)
    return jsonify(logged_in_as=current_user, response=response)




# ! EXTENSION DU PROJET ----------------------------------------------------------------------------------


class PositiveEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(100), nullable=True, default='souvenir')  # Default à 'souvenir'
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('positive_events', lazy=True))


def is_development():
    """Déterminer si l'application est en mode développement."""
    return os.getenv('FLASK_ENV') == 'development'

def jwt_optional(fn):
    """Un décorateur personnalisé qui n'exige pas de JWT en mode développement."""
    from flask_jwt_extended import jwt_required

    if is_development():
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request(optional=True)
            except Exception as e:
                # En mode développement, afficher un message d'erreur mais continuer
                print(f"JWT verification skipped: {e}")
            return fn(*args, **kwargs)
        return wrapper
    else:
        return jwt_required()(fn)


def record_event(user_id, description):
    """Enregistre un événement positif dans la base de données."""
    new_event = PositiveEvent(user_id=user_id, description=description)
    db.session.add(new_event)
    db.session.commit()
    return "Événement enregistré avec succès."

def recall_events(user_id):
    """Rappelle les événements positifs d'un utilisateur."""
    events = PositiveEvent.query.filter_by(user_id=user_id).order_by(PositiveEvent.date.desc()).all()
    return [{"description": event.description, "date": event.date.strftime('%Y-%m-%d')} for event in events]



# Fonction pour interroger l'API ChatGPT d'OpenAI.
def ask_chatgpt(prompt, config_type):
    config = load_json_config(config_type)  # Charge la configuration appropriée
    data = {
        'model': config['model'],
        'messages': [{'role': 'user', 'content': f"{config['instructions']} {prompt}"}],
        'max_tokens': config['max_tokens']
    }
    response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)
    return response.json()['choices'][0]['message']['content'].strip() if response.status_code == 200 else "Error processing your request."

def load_json_config(type):
    with open('gpt_config.json', 'r') as file:
        return json.load(file)[type]




@app.route('/interact', methods=['POST'])
@jwt_required()
def interact():
    user_email = get_jwt_identity()
    user = User.query.filter_by(email=user_email).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    user_input = request.json.get('question', '')
    # Première étape : Déterminer l'intention avec une analyse générale
    intent_response = ask_chatgpt(user_input, "detect_intent")

    # Traitement en fonction de l'intention
    if "enregistrer" in intent_response:
        action_to_record = ask_chatgpt(user_input, "record")
        if action_to_record and "action spécifique" in action_to_record:
            response = record_event(user.id, action_to_record.split('"')[1])  # Supposer que l'action est entre guillemets
        else:
            response = "Aucune action spécifique n'a été identifiée pour l'enregistrement."
    elif "rappel" in intent_response:
        recall_query = ask_chatgpt(user_input, "recall")
        response = recall_events(user.id, recall_query)
    else:
        # Si ce n'est ni un enregistrement ni un rappel, on considère comme une discussion générale ou un besoin de soutien
        response = ask_chatgpt(user_input, "support")  # Utilisation du modèle support pour répondre

    return jsonify({"response": response})








def record_event(user_id, description):
    if description:
        new_event = PositiveEvent(user_id=user_id, description=description)
        db.session.add(new_event)
        db.session.commit()
        return "Événement enregistré."
    return "Aucune action spécifique reconnue pour l'enregistrement."


def extract_period(user_input):
    """Extrait la période de la demande de l'utilisateur."""
    period_response = ask_chatgpt(user_input, "extract_period")
    return period_response.strip()

def recall_events(user_id, period):
    """Rappelle les événements positifs d'un utilisateur pour une période donnée."""
    if period == "aujourd'hui":
        date_filter = datetime.utcnow().date()
    elif period == "hier":
        date_filter = datetime.utcnow().date() - timedelta(days=1)
    else:
        # Définir plus de conditions pour d'autres périodes si nécessaire
        date_filter = datetime.utcnow().date()  # Exemple par défaut

    events = PositiveEvent.query.filter_by(user_id=user_id, date=date_filter).all()
    return [{"description": event.description, "date": event.date.strftime('%Y-%m-%d')} for event in events]







# Démarrage de l'application Flask.
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
