from flask import Flask, request, render_template, jsonify, make_response
import os
import requests
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

# Récupère la clé API de l'environnement pour OpenAI.
api_key = os.getenv('OPENAI_API_KEY')
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

# Initialise l'application Flask.
app = Flask(__name__)
# Configure la clé secrète pour JWT, récupérée à partir des variables d'environnement.
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
# Initialise le gestionnaire JWT pour gérer les tokens d'authentification.
jwt = JWTManager(app)
# Configure CORS pour autoriser les requêtes cross-origin spécifiques aux routes '/ask' et '/login' de deux domaines.
CORS(app, supports_credentials=True, resources={
    r"/ask": {"origins": ["https://kokua.fr", "https://www.kokua.fr"]},
    r"/login": {"origins": ["https://kokua.fr", "https://www.kokua.fr"]}
})

# Fonction pour poser une question à ChatGPT via l'API OpenAI.
def ask_chatgpt(prompt):
    data = {
        'model': "gpt-4-turbo",
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 150
    }
    response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)
    json_response = response.json()
    print("API Response:", json_response)  # Affiche la réponse de l'API dans la console pour le débogage.
    if 'choices' in json_response and json_response['choices']:
        return json_response['choices'][0]['message']['content'].strip()
    else:
        return "Error: Unexpected response from OpenAI API"

# Route racine qui peut gérer à la fois GET et POST pour afficher et répondre aux questions.
@app.route('/', methods=['GET', 'POST'])
def hello():
    if request.method == 'POST':
        question = request.form['question']
        response = ask_chatgpt(question)
        return render_template('index.html', question=question, response=response)
    return render_template('index.html', question=None, response=None)

# Route de connexion qui supporte POST pour le login et OPTIONS pour les requêtes cross-origin.
@app.route('/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'https://kokua.fr')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response

    if request.method == 'POST':
        username = request.json.get('username')
        password = request.json.get('password')
        if username == 'johann' and password == 'johann':
            access_token = create_access_token(identity=username)
            return jsonify(access_token=access_token), 200
        else:
            return jsonify({"msg": "Invalid credentials"}), 401

# Route '/ask' pour poser des questions via API, protégée par JWT.
@app.route('/ask', methods=['POST', 'OPTIONS'])
@jwt_required(optional=True)  # Permet des requêtes sans JWT si nécessaire.
def ask():
    if request.method == 'OPTIONS':
        return {}, 200  # Répond simplement pour les requêtes OPTIONS gérées par CORS.

    current_user = get_jwt_identity()  # Obtient l'identité de l'utilisateur JWT actuel.
    question = request.json.get('question')
    response = ask_chatgpt(question)
    return jsonify(logged_in_as=current_user, response=response)

# Exécute l'application sur le port spécifié dans la variable d'environnement PORT, ou 5000 par défaut.
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
