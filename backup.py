from flask import Flask, jsonify, request, send_from_directory, render_template
import os
import pygame
import threading
import speech_recognition as sr
import time
from pymongo import MongoClient

app = Flask(__name__)

# ===== MongoDB Setup =====
client = MongoClient("mongodb://localhost:27017")
db = client["vmusic_db"]
collection = db["songs"]
# Example insertion (you can remove after testing)
data = {"name": "Shisir", "country": "Nepal"}
collection.insert_one(data)
print("✅ Data inserted successfully!")

# ===== Global Variables =====
current_playlist = []  # Will store full paths to songs
current_category = ""
current_index = -1
voice_control_active = False

# ===== Directories =====
TAMIL_DIR = os.path.abspath(r"C:\Users\user\Desktop\shisir_project\songs\tamil_songs")
NEPALI_DIR = os.path.abspath(r"C:\Users\user\Desktop\shisir_project\songs\nepali_songs")

# Initialize pygame mixer
pygame.mixer.init()

# ===== Helper Functions =====
def get_all_songs():
    tamil_songs = [f for f in os.listdir(TAMIL_DIR) if f.endswith(".mp3")]
    nepali_songs = [f for f in os.listdir(NEPALI_DIR) if f.endswith(".mp3")]
    return tamil_songs, nepali_songs

def listen_commands():
    global voice_control_active
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("Voice control activated. Say a command (play, pause, next, previous)...")

    while voice_control_active:
        try:
            with mic as source:
                print("Listening...")
                recognizer.adjust_for_ambient_noise(source)
                audio = recognizer.listen(source, timeout=3, phrase_time_limit=3)

            command = recognizer.recognize_google(audio).lower()
            print(f"Recognized command: {command}")

            if "play" in command:
                pygame.mixer.music.unpause()
                print("Playing music")
            elif "pause" in command:
                pygame.mixer.music.pause()
                print("Music paused")
            elif "stop" in command:
                pygame.mixer.music.stop()
                print("Music stopped")
            elif "next" in command:
                next_song()
                print("Next song")
            elif "previous" in command or "back" in command:
                prev_song()
                print("Previous song")
            else:
                print("Command not recognized")

        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            print("Could not understand audio")
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
        except Exception as e:
            print(f"Error: {e}")

        time.sleep(0.5)

# ===== Routes =====

@app.route("/")
def index():
    tamil_songs, nepali_songs = get_all_songs()
    songs = {
        "Tamil Songs": tamil_songs,
        "Nepali Songs": nepali_songs
    }
    return render_template("index.html", songs=songs, voice_control_active=voice_control_active)

@app.route("/toggle_voice_control", methods=["POST"])
def toggle_voice_control():
    global voice_control_active
    
    if not voice_control_active:
        voice_control_active = True
        threading.Thread(target=listen_commands, daemon=True).start()
        return jsonify({"status": "success", "message": "Voice control activated"})
    else:
        voice_control_active = False
        return jsonify({"status": "success", "message": "Voice control deactivated"})

@app.route("/songs")
def list_songs():
    tamil, nepali = get_all_songs()
    return jsonify({"tamil": tamil, "nepali": nepali})

@app.route("/select", methods=["POST"])
def select_song():
    global current_playlist, current_category, current_index
    data = request.get_json()
    song = data.get("song")

    tamil_songs = [f for f in os.listdir(TAMIL_DIR) if f.endswith(".mp3")]
    nepali_songs = [f for f in os.listdir(NEPALI_DIR) if f.endswith(".mp3")]

    if song in tamil_songs:
        current_category = "Tamil Songs"
        songs_list = tamil_songs
        base_dir = TAMIL_DIR
    elif song in nepali_songs:
        current_category = "Nepali Songs"
        songs_list = nepali_songs
        base_dir = NEPALI_DIR
    else:
        return jsonify({"status": "error", "message": "Song not found"}), 404

    current_playlist = [os.path.join(base_dir, s) for s in songs_list]
    current_index = songs_list.index(song)

    pygame.mixer.music.load(current_playlist[current_index])
    pygame.mixer.music.play()

    return jsonify({"status": "success", "message": f"Playing {song}", "category": current_category, "index": current_index})

@app.route("/play", methods=["POST"])
def play():
    pygame.mixer.music.unpause()
    return jsonify({"status": "success", "message": "Playback resumed"})

@app.route("/pause", methods=["POST"])
def pause():
    pygame.mixer.music.pause()
    return jsonify({"status": "success", "message": "Playback paused"})

@app.route("/play/<category>/<int:index>")
def play_by_category_index(category, index):
    global current_playlist, current_category, current_index
    
    try:
        if category == "Tamil Songs":
            songs = [os.path.join(TAMIL_DIR, f) for f in os.listdir(TAMIL_DIR) if f.endswith(".mp3")]
        elif category == "Nepali Songs":
            songs = [os.path.join(NEPALI_DIR, f) for f in os.listdir(NEPALI_DIR) if f.endswith(".mp3")]
        else:
            return jsonify({"status": "error", "message": "Invalid category"}), 400

        if not songs:
            return jsonify({"status": "error", "message": "No songs found in category"}), 404
        if index >= len(songs):
            return jsonify({"status": "error", "message": "Invalid index"}), 400

        current_playlist = songs
        current_category = category
        current_index = index
        
        pygame.mixer.music.load(current_playlist[current_index])
        pygame.mixer.music.play()
        
        return jsonify({
            "status": "success",
            "song": os.path.basename(current_playlist[current_index]),
            "category": category,
            "index": index
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/next", methods=["GET", "POST"])
def next_song():
    global current_index, current_playlist, current_category

    try:
        if not current_playlist or current_index == -1:
            return jsonify({"status": "error", "message": "No playlist loaded"}), 400
        
        current_index = (current_index + 1) % len(current_playlist)
        pygame.mixer.music.load(current_playlist[current_index])
        pygame.mixer.music.play()
        
        return jsonify({
            "status": "success",
            "song": os.path.basename(current_playlist[current_index]),
            "category": current_category,
            "index": current_index
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/prev", methods=["GET", "POST"])
def prev_song():
    global current_index, current_playlist, current_category
    print(f"Called /prev, current_index={current_index}, playlist length={len(current_playlist)}")
    try:
        if not current_playlist or current_index == -1:
            print("No playlist loaded")
            return jsonify({"status": "error", "message": "No playlist loaded"}), 400

        current_index = (current_index - 1) % len(current_playlist)
        print(f"New index: {current_index}, song: {os.path.basename(current_playlist[current_index])}")
        pygame.mixer.music.load(current_playlist[current_index])
        pygame.mixer.music.play()

        return jsonify({
            "status": "success",
            "song": os.path.basename(current_playlist[current_index]),
            "category": current_category,
            "index": current_index
        })
    except Exception as e:
        print(f"Error in /prev: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/songs/<folder>/<filename>")
def serve_song(folder, filename):
    if folder == "tamil":
        return send_from_directory(TAMIL_DIR, filename)
    elif folder == "nepali":
        return send_from_directory(NEPALI_DIR, filename)
    else:
        return "Folder not found", 404

if __name__ == "__main__":
    app.run(debug=True)
