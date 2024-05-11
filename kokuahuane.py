from flask import Flask, request, render_template, jsonify, make_response
import os
import requests
from flask_cors import CORS, cross_origin
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from dotenv import load_dotenv
from datetime import datetime
from dateutil import parser
import json
import sys
import logging




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


# Configuration du logging
app.config['DEBUG'] = True  # Active le mode debug, qui est utile pour le développement
app.config['LOGGING_LEVEL'] = 'DEBUG'  # Définit le niveau de logging à debug pour voir plus de détails dans les logs
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')



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
    r"/interact": {"origins": ["https://kokua.fr", "https://www.kokua.fr"]},
    r"/propose_event": {"origins": ["https://kokua.fr", "https://www.kokua.fr"]}, 
    r"/confirm_event": {"origins": ["https://kokua.fr", "https://www.kokua.fr"]},
    r"/get_actions": {"origins": ["https://kokua.fr", "https://www.kokua.fr"]} 
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



# # Route pour poser des questions via l'API, protégée par JWT.
# @app.route('/ask', methods=['POST', 'OPTIONS'])
# @jwt_required(optional=True)
# def ask():
#     if request.method == 'OPTIONS':
#         return {}, 200

#     current_user = get_jwt_identity()
#     question = request.json.get('question')
#     response = ask_chatgpt(question)
#     return jsonify(logged_in_as=current_user, response=response)




# ! EXTENSION 1 DU PROJET ----------------------------------------------------------------------------------


class PositiveEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(100), nullable=True, default='souvenir')  # Default à 'souvenir'
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('positive_events', lazy=True))


def is_development():
    #Déterminer si l'application est en mode développement.#
    return os.getenv('FLASK_ENV') == 'development'

def jwt_optional(fn):
    #Un décorateur personnalisé qui n'exige pas de JWT en mode développement.#
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




# Fonction pour interroger l'API ChatGPT d'OpenAI.
def ask_chatgpt(prompt, config_type):
    #Interroger l'API ChatGPT avec des paramètres spécifiques définis dans un fichier de configuration JSON.#
    # Charge la configuration appropriée pour le type demandé
    with open('gpt_config.json', 'r') as file:
        config = json.load(file)[config_type]

    data = {
        'model': config['model'],
        'messages': [{'role': 'user', 'content': f"{config['instructions']} {prompt}"}],
        'max_tokens': config['max_tokens'],
        'temperature': config.get('temperature', 1),  # Valeur par défaut si non spécifiée
        'top_p': config.get('top_p', 1),  # Valeur par défaut si non spécifiée
        'frequency_penalty': config.get('frequency_penalty', 0),  # Valeur par défaut
        'presence_penalty': config.get('presence_penalty', 0)  # Valeur par défaut
    }

    response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content'].strip()
    else:
        app.logger.error('Failed to receive valid response from OpenAI: %s', response.text)
        return "Error processing your request."


# @app.route('/interact', methods=['POST'])
# @jwt_required()
# def interact():
#     # Récupère l'identifiant de l'utilisateur à partir du token JWT
#     user_email = get_jwt_identity()
#     # Recherche l'utilisateur dans la base de données par son email
#     user = User.query.filter_by(email=user_email).first()

#     # Si l'utilisateur n'est pas trouvé, renvoie une erreur 404
#     if not user:
#         return jsonify({"error": "User not found"}), 404

#     # Récupère l'entrée de l'utilisateur à partir de la requête JSON
#     user_input = request.json.get('question', '')
#     # Demande à ChatGPT de déterminer l'intention de l'utilisateur
#     intent = ask_chatgpt(user_input, "detect_intent")





#     # Traite les différentes intentions possibles
#     if "enregistrer" in intent:
#         logging.debug(f"Intent 'enregistrer' detected with input: {user_input}")

#         # Demande à ChatGPT de formuler l'action à enregistrer
#         action_to_record = ask_chatgpt(user_input, "record")
#         logging.debug(f"Action to record: {action_to_record}")

#         # Enregistre l'action dans la base de données
#         response = record_event(user.id, action_to_record)
#         logging.debug(f"Response from record_event: {response}")

#     elif "rappel" in intent:
#         logging.debug(f"Intent 'rappel' detected with input: {user_input}")
        
#         # Extrait la période potentiellement mentionnée par l'utilisateur
#         period_query = ask_chatgpt(user_input, "extract_period")
#         logging.debug(f"Extracted period query: {period_query}") 

#         if period_query:
#             # Convertit la période extraite en plage de dates
#             date_output = ask_chatgpt(period_query, "convert_date_range")
#             logging.debug(f"Converted date output from extracted period: {date_output}")

#             # Récupère les événements correspondants à cette plage de dates
#             events = recall_events(user.id, date_output)
#             # Demande à ChatGPT de formuler un message de soutien avec ces événements
#             supportive_message = ask_chatgpt(events, "support")
#             response = supportive_message
#         else:
#             # Si aucune période n'est identifiée, utilise la date d'aujourd'hui
#             today = datetime.now().strftime('%Y-%m-%d')
#             logging.debug(f"No period identified, using today's date: {today}")
#             events = recall_events(user.id, today)
#             supportive_message = ask_chatgpt(events, "support")
#             response = supportive_message
#     else:
#         logging.debug(f"No clear intent found, defaulting to support API with input: {user_input}")
#         # Si aucune intention claire n'est trouvée, utilise l'API support pour répondre
#         response = ask_chatgpt(user_input, "support")

#     # Renvoie la réponse sous forme de JSON
#     return jsonify({"response": response})


# def record_event(user_id, description):
#     logging.debug(f"Recording event for user_id: {user_id} with description: {description}")
#     # Enregistre un événement positif dans la base de données. #
#     new_event = PositiveEvent(user_id=user_id, description=description)
#     db.session.add(new_event)
#     db.session.commit()
#     return "Événement enregistré avec succès."


# def recall_events(user_id, date_info):
#     logging.debug(f"Recalling events for user_id: {user_id} with date_info: {date_info}")
#     # Récupère les événements d'un utilisateur pour une période donnée. #
#     if " to " in date_info:
#         start_date, end_date = date_info.split(" to ")
#         events = query_events(user_id, start_date, end_date)
#     else:
#         events = query_events(user_id, date_info, date_info)
#     return jsonify([{"description": event.description, "date": event.date.strftime('%Y-%m-%d')} for event in events])


# def query_events(user_id, start_date, end_date):
#     logging.debug(f"Querying events between {start_date} and {end_date} for user_id: {user_id}")
#     # Interroge la base de données pour récupérer les événements entre deux dates. #
#     return PositiveEvent.query.filter(
#         PositiveEvent.user_id == user_id,
#         PositiveEvent.date.between(start_date, end_date)
#     ).order_by(PositiveEvent.date.desc()).all()

# !* Gestion de la date ---------------

# def get_current_datetime():
#     api_key = 'YOUR_API_KEY'  # Remplace cela par ta clé d'API TimezoneDB
#     url = f'http://api.timezonedb.com/v2.1/get-time-zone?key={api_key}&format=json&by=zone&zone=Europe/Paris'
    
#     response = requests.get(url)
#     if response.status_code == 200:
#         data = response.json()
#         return data['formatted']
#     else:
#         print("Failed to fetch current datetime.")
#         return None

# # Utilisation de la fonction pour obtenir la date et l'heure actuelles
# current_datetime = get_current_datetime()




# !*zone de test ----------------------

# @app.route('/test-date-conversion', methods=['POST'])
# def test_date_conversion():
#     return test_convert_date_range()


# def test_convert_date_range():
#     results = []
#     test_cases = ["aujourd'hui", "les deux derniers jours", "ce mois-ci"]
#     for case in test_cases:
#         output = ask_chatgpt(case, "convert_date_range")
#         results.append(f"Input: {case} -> Output: {output}")
#     return jsonify(results)  # Retourne un JSON des résultats


# def test_convert_date_range_local():
#     """ Tests unitaires pour vérifier la fonctionnalité de conversion de date de l'API. """
#     test_cases = ["aujourd'hui", "les deux derniers jours", "ce mois-ci"]
#     for case in test_cases:
#         output = ask_chatgpt(case, "convert_date_range")
#         print(f"Input: {case} -> Output: {output}")


# ! FIN DE L'EXTENSION 1 DU PROJET ----------------------------------------------------------------------------------
# Cette section du code gère l'extension de fonctionnalités de l'application.
# Elle implémente la capacité d'enregistrer des événements positifs et de les rappeler à l'utilisateur
# pour soutenir sa motivation et son moral. Cependant, nous rencontrons des difficultés avec la fonction
# de conversion de dates utilisée pour interpréter les expressions de dates fournies par l'utilisateur.
# 
# En raison de cette limitation, nous décidons d'abandonner cette approche et de simplifier l'interaction
# avec l'utilisateur en ajoutant des boutons côté client pour des actions spécifiques comme l'enregistrement
# d'une action positive ou le rappel des actions positives pour une période donnée. Cela permettra
# d'améliorer l'expérience utilisateur tout en réduisant la complexité du traitement des intentions
# par ChatGPT. Nous allons donc revoir notre approche et nous concentrer sur la mise en œuvre de cette
# nouvelle fonctionnalité plus conviviale pour l'utilisateur.


# (env) C:\Users\johan\Documents\projets web\0 - MES IA\IA KokuaHuane\KokuaHuaneApp>curl -k -X POST https://kokuauhane-071dbd833182.herokuapp.com/test-date-conversion
# [
#   "Input: aujourd'hui -> Output: 2023-11-27",
#   "Input: les deux derniers jours -> Output: 2023-09-27 - 2023-09-28",
#   "Input: ce mois-ci -> Output: 2023-09-01 - 2023-09-30"
# ]

# (env) C:\Users\johan\Documents\projets web\0 - MES IA\IA KokuaHuane\KokuaHuaneApp>curl -k -X POST https://kokuauhane-071dbd833182.herokuapp.com/test-date-conversion
# [
#   "Input: aujourd'hui -> Output: 2022-03-22",
#   "Input: les deux derniers jours -> Output: 2022-03-06 - 2022-03-07",
#   "Input: ce mois-ci -> Output: 2022-02-01 - 2022-02-28"
# ]

# (env) C:\Users\johan\Documents\projets web\0 - MES IA\IA KokuaHuane\KokuaHuaneApp>



# et en local : 
# 
# (env) C:\Users\johan\Documents\projets web\0 - MES IA\IA KokuaHuane\KokuaHuaneApp>python kokuahuane.py test
# Database URI: postgresql://postgres@localhost/kokuahuane_local
# 2024-05-06 17:35:00,571 - DEBUG - Starting new HTTPS connection (1): api.openai.com:443
# 2024-05-06 17:35:02,075 - DEBUG - https://api.openai.com:443 "POST /v1/chat/completions HTTP/1.1" 200 None
# Input: aujourd'hui -> Output: 2022-03-13
# 2024-05-06 17:35:02,090 - DEBUG - Starting new HTTPS connection (1): api.openai.com:443
# 2024-05-06 17:35:04,449 - DEBUG - https://api.openai.com:443 "POST /v1/chat/completions HTTP/1.1" 200 None
# Input: les deux derniers jours -> Output: 2022-03-06 - 2022-03-07
# 2024-05-06 17:35:04,462 - DEBUG - Starting new HTTPS connection (1): api.openai.com:443
# 2024-05-06 17:35:06,772 - DEBUG - https://api.openai.com:443 "POST /v1/chat/completions HTTP/1.1" 200 None
# Input: ce mois-ci -> Output: 2022-02-01 - 2022-02-28

# (env) C:\Users\johan\Documents\projets web\0 - MES IA\IA KokuaHuane\KokuaHuaneApp>

# !  ----------------------------------------------------------------------------------------------------------------





# ! EXTENSION 2 DU PROJET -------------------------------------------------------------------------------------------

# Fonction pour interroger l'API OpenAI avec un prompt spécifique
def ask_gpt_mood(prompt, config_type):
    # Charge la configuration appropriée pour le type demandé
    with open('gpt_config.json', 'r') as file:
        config = json.load(file)[config_type]

    data = {
        'model': config['model'],
        'messages': [{'role': 'user', 'content': f"{config['instructions']} {prompt}"}],
        'max_tokens': config['max_tokens'],
        'temperature': config.get('temperature', 1),
        'top_p': config.get('top_p', 1),
        'frequency_penalty': config.get('frequency_penalty', 0),
        'presence_penalty': config.get('presence_penalty', 0)
    }

    # Utilisation des headers globaux qui contiennent déjà la clé API correcte
    response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)

    if response.status_code == 200:
        json_response = response.json()
        # Log de la réponse complète de l'API pour faciliter le débogage
        app.logger.debug(f"Réponse complète de l'API : {json_response}")

        # Vérifie la présence de 'choices' et extrait la réponse
        if 'choices' in json_response and len(json_response['choices']) > 0 and 'message' in json_response['choices'][0] and 'content' in json_response['choices'][0]['message']:
            content_extracted = json_response['choices'][0]['message']['content'].strip()
            # Log du contenu extrait pour voir ce qui a été précisément obtenu
            app.logger.debug(f"Contenu extrait : {content_extracted}")
            return content_extracted
        else:
            # Log la structure inattendue de la réponse pour aider à déboguer
            app.logger.debug(f"Structure de réponse inattendue : {json_response}")
            return None
    else:
        # Log de l'erreur de réponse de l'API pour aider à identifier le problème
        app.logger.error(f"Échec de la réception d'une réponse valide d'OpenAI : {response.text}")
        return None



@app.route('/propose_event', methods=['POST'])
@jwt_required()
def propose_event():
    user_email = get_jwt_identity()
    user = User.query.filter_by(email=user_email).first()
    
    if not user:
        logging.error("User not found")
        return jsonify({"error": "User not found"}), 404
    
    user_input = request.json.get('question', '')
    logging.debug(f"User input: {user_input}")  # Log pour observer l'entrée utilisateur
    
    # Appel pour tenter d'extraire un événement
    event_detection = ask_gpt_mood(user_input, "record")

    logging.debug(f"Detected event response: {event_detection}")  # Log pour observer la réponse de détection d'événement

    # Vérifie si un événement clair est détecté
    if not event_detection or event_detection.strip() == "flag":
        # Directement retourner un message invitant l'utilisateur à fournir plus de détails
        return jsonify({"status": "info", "message": "Aucun événement spécifique n'a été identifié. Pouvez-vous donner plus de détails pour que nous puissions vous aider davantage ?"})
    else:
        # Si un événement est détecté, demandez la confirmation
        logging.debug(f"Event detected: {event_detection}")
        return jsonify({"status": "success", "message": "Confirmez-vous cet événement ?", "event": event_detection, "options": ["Confirmer", "Annuler"]})




@app.route('/confirm_event', methods=['POST'])
@jwt_required()
def confirm_event():
    user_email = get_jwt_identity()
    user = User.query.filter_by(email=user_email).first()
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    confirmation = request.json.get('confirmation', '')
    event_description = request.json.get('event', '')
    
    if confirmation == "Confirmer":
        response = save_event(user.id, event_description)
        return jsonify({"status": "success", "message": response})
    else:
        return jsonify({"status": "cancelled", "message": "L'action a été annulée."})

def save_event(user_id, description):
    logging.debug(f"Recording event for user_id: {user_id} with description: {description}")
    new_event = PositiveEvent(user_id=user_id, description=description)
    db.session.add(new_event)
    db.session.commit()
    return "Événement enregistré avec succès."




# ! ajout EXTENSION 2 affichage de list ---------------

@app.route('/get_actions', methods=['POST'])
@jwt_required()
def get_actions():
    user_email = get_jwt_identity()
    user = User.query.filter_by(email=user_email).first()
    
    if not user:
        logging.error("User not found")
        return jsonify({"error": "User not found"}), 404
    
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    day_before_yesterday = today - timedelta(days=2)
    
    grouped_actions = {
        "Aujourd'hui": [],
        "Hier": [],
        "Avant-Hier": []
    }
    
    # Query events for the last three days
    events = PositiveEvent.query.filter(
        PositiveEvent.user_id == user.id,
        PositiveEvent.date >= day_before_yesterday
    ).all()
    
    for event in events:
        event_date = event.date.date()
        if event_date == today:
            grouped_actions["Aujourd'hui"].append(event.description)
        elif event_date == yesterday:
            grouped_actions["Hier"].append(event.description)
        elif event_date == day_before_yesterday:
            grouped_actions["Avant-Hier"].append(event.description)
    
    return jsonify(grouped_actions)


# ! fin list


# Point d'entrée pour décider d'exécuter l'application ou le test
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # test_convert_date_range()
        test_convert_date_range_local()
    else:
        app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)