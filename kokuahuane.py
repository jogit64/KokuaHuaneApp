from flask import Flask, request, render_template, jsonify,make_response
import os
import requests
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

api_key = os.getenv('OPENAI_API_KEY')
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
jwt = JWTManager(app)
CORS(app, supports_credentials=True, resources={
    r"/ask": {"origins": ["https://kokua.fr", "https://www.kokua.fr"]},
    r"/login": {"origins": ["https://kokua.fr", "https://www.kokua.fr"]}
})


def ask_chatgpt(prompt):
    data = {
        'model': "gpt-4-turbo",
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 150
    }
    response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)
    json_response = response.json()
    print("API Response:", json_response)  
    if 'choices' in json_response and json_response['choices']:
        return json_response['choices'][0]['message']['content'].strip()
    else:
        return "Error: Unexpected response from OpenAI API"

@app.route('/', methods=['GET', 'POST'])
def hello():
    if request.method == 'POST':
        question = request.form['question']
        response = ask_chatgpt(question)
        return render_template('index.html', question=question, response=response)
    return render_template('index.html', question=None, response=None)

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


@app.route('/ask', methods=['POST', 'OPTIONS'])  # Ajout de 'OPTIONS' ici
@jwt_required(optional=True)  # `optional=True` permet à Flask-JWT-Extended de traiter la requête OPTIONS sans exiger un jeton.
def ask():
    if request.method == 'OPTIONS':
        # Laissez Flask-CORS gérer la requête OPTIONS si vous n'avez rien de spécifique à faire.
        return {}, 200
    
    current_user = get_jwt_identity()
    question = request.json.get('question')
    response = ask_chatgpt(question)
    return jsonify(logged_in_as=current_user, response=response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
