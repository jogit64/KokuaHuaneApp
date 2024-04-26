from flask import Flask, request, render_template, jsonify
import os
import requests
from flask_cors import CORS


api_key = os.getenv('OPENAI_API_KEY')
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=['https://kokua.fr', 'https://www.kokua.fr'])

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


@app.route('/ask', methods=['POST', 'OPTIONS'])
def ask():
    if request.method == 'OPTIONS':
        # Pour répondre à la requête préliminaire OPTIONS de CORS
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    if request.method == 'POST':
        question = request.json.get('question')
        response = ask_chatgpt(question)
        return jsonify({'response': response})




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
