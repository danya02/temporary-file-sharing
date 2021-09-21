from flask import Flask, render_template, send_file

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/style.css')
def style():
    return send_file('/bootstrap.min.css')
