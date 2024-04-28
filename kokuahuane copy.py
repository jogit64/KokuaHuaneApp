from flask import Flask, request, render_template, jsonify, make_response
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
# CORS(app, supports_credentials=True, origins=['https://kokua.fr', 'https://www.kokua.fr'])
CORS(app, resources={r"/ask": {"origins": ["https://kokua.fr", "https://www.kokua.fr"]}})

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



@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    # Vérifiez les informations d'identification (par exemple, à partir d'une base de données)
    if username == 'your_username' and password == 'your_password':
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({"msg": "Invalid credentials"}), 401


@app.route('/ask', methods=['POST'])
@jwt_required()

def protected():
    current_user = get_jwt_identity()
    question = request.json.get('question')
    response = ask_chatgpt(question)
    return jsonify(logged_in_as=current_user, response=response)

def ask():
    if request.method == 'POST':
        question = request.json.get('question')
        response = ask_chatgpt(question)
        return jsonify({'response': response})




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
