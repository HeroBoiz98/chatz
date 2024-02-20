from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, join_room, send
import os
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, secure=True)

# Directory to store HTML files for rooms
ROOMS_DIR = 'rooms'

# Create the rooms directory if it doesn't exist
if not os.path.exists(ROOMS_DIR):
    os.makedirs(ROOMS_DIR)

# Dictionary to store messages for each room
room_messages = {}

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Chat App</title>
    </head>
    <body>
        <h1>Welcome to the Chat App</h1>
        <a href="/create_room">Create Room</a><br>
        <form id="joinForm" method="get">
            <label for="room_code">Enter Room Code:</label><br>
            <input type="text" id="room_code" name="room_code"><br>
            <label for="name">Enter Your Name:</label><br>
            <input type="text" id="name" name="name"><br>
            <input type="button" value="Join Room" onclick="joinRoom()">
        </form>
        
        <script>
            function joinRoom() {
                var roomCode = document.getElementById("room_code").value.trim();
                var userName = document.getElementById("name").value.trim();
                if (roomCode !== "") {
                    window.location.href = "/join_room/" + roomCode + "?name=" + userName;
                }
            }
        </script>
    </body>
    </html>
    """

@app.route('/create_room')
def create_room():
    room_code = generate_room_code()
    room_file = os.path.join(ROOMS_DIR, f'{room_code}.html')
    with open(room_file, 'w') as f:
        f.write('')
    room_messages[room_code] = []
    return f'Room created! Unique code: {room_code}'

@app.route('/join_room/<room_code>', methods=['GET', 'POST'])
def join_room_route(room_code):
    if request.method == 'GET':
        room_file = os.path.join(ROOMS_DIR, f'{room_code}.html')
        if os.path.exists(room_file):
            session['name'] = request.args.get('name', 'Anonymous')
            session['room'] = room_code
            messages = room_messages.get(room_code, [])
            message_html = ""
            for message in messages:
                message_html += f"""
                    <div class="message {'sent' if message['user'] == session['name'] else 'received'}">
                        <strong>{message['user']}:</strong> {message['text']}
                    </div>
                """
            return f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Chat Room</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 0;
                    }}
                    .chat-container {{
                        max-width: 600px;
                        margin: 20px auto;
                        padding: 20px;
                        border: 1px solid #ccc;
                        border-radius: 5px;
                    }}
                    .chat-box {{
                        height: 300px;
                        overflow-y: auto;
                        border: 1px solid #ccc;
                        border-radius: 5px;
                        padding: 10px;
                        margin-bottom: 10px;
                    }}
                    .message {{
                        background-color: #f2f2f2;
                        padding: 10px;
                        margin-bottom: 5px;
                        border-radius: 5px;
                    }}
                    .sent {{
                        text-align: right;
                    }}
                    .received {{
                        text-align: left;
                    }}
                </style>
            </head>
            <body>
                <div class="chat-container">
                    <div id="chat-box" class="chat-box">
                        {message_html}
                    </div>
                    <form id="message-form" action="/room/{room_code}/send_message" method="post">
                        <input type="text" id="message-input" name="message" placeholder="Type your message...">
                        <button type="submit">Send</button>
                    </form>
                </div>
                <span id="user-name" style="display: none;">{session['name']}</span>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.3.1/socket.io.js"></script>
                <script>
                    var user_name = document.getElementById('user-name').innerText.trim();
                    var room_code = "{room_code}";

                    var socket = io.connect('https://' + document.domain + ':' + location.port);

                    socket.on('connect', function() {{
                        socket.emit('join', {{room: room_code}});
                    }});

                    socket.on('message', function(data) {{
                        if (data && data.user && data.text) {{
                            var chatBox = document.getElementById('chat-box');
                            var newMessage = document.createElement('div');
                            if (data.user === user_name) {{
                                newMessage.className = 'message sent';
                            }} else {{
                                newMessage.className = 'message received';
                            }}
                            newMessage.innerHTML = '<strong>' + data.user + ':</strong> ' + data.text;
                            chatBox.appendChild(newMessage);
                            chatBox.scrollTop = chatBox.scrollHeight;
                        }}
                    }});

                    document.getElementById('message-form').addEventListener('submit', function(e) {{
                        e.preventDefault();
                        var messageInput = document.getElementById('message-input');
                        var messageText = messageInput.value.trim();
                        if (messageText !== "") {{
                            socket.emit('send_message', {{'room_code': room_code, 'message': messageText}});
                            messageInput.value = '';
                        }}
                    }});
                </script>
            </body>
            </html>
            """
        else:
            return 'Room not found!'
    else:
        pass

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    send({'msg': session.get('name') + ' has entered the room.'}, room=room)

@socketio.on('send_message')
def send_message(data):
    room_code = data['room_code']
    message_text = data['message']
    user_name = session.get('name', 'Anonymous')
    message = {'user': user_name, 'text': message_text}
    room_messages[room_code].append(message)
    send(message, room=room_code)

def generate_room_code():
    return str(uuid.uuid4())[:10]

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
