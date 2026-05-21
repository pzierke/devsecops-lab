from flask import Flask, request
import os

app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello DevSecOps"

@app.route("/run")
def run():
    cmd = request.args.get("cmd")
    os.system(cmd)
    return "Executed"

app.run(host="0.0.0.0", port=5000)
