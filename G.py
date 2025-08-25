from flask import Flask
app = Flask("GOD Bot")

@app.route("/")
def home():
    return "Bot is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)  # پورت دلخواه