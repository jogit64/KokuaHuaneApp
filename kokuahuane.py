from flask import Flask, request, render_template
import os
import requests

api_key = os.getenv('OPENAI_API_KEY')
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
