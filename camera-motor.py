# main.py (better name xD)
# combination of camera.py and socket_motor.py

import RPi.GPIO as GPIO
import socket
import io
import logging
import socketserver
import time
from http import server
from threading import Condition, Thread
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput

# Set GPIO mode
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Motor 1 control pins
ENA = 2
IN1 = 4
IN2 = 3

# Motor 2 control pins
ENB = 5
IN3 = 6
IN4 = 7

# Set initial state
GPIO.setup(ENA, GPIO.OUT)
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)

GPIO.setup(ENB, GPIO.OUT)
GPIO.setup(IN3, GPIO.OUT)
GPIO.setup(IN4, GPIO.OUT)

# Set PWM frequency and start with duty cycle 0 (stopped)
pwm1 = GPIO.PWM(ENA, 1000)  # 1 kHz
pwm2 = GPIO.PWM(ENB, 1000)  # 1 kHz
pwm1.start(0)
pwm2.start(0)

# HTML page for motor control and camera streaming
PAGE = """\
<html>
<head>
<title>Raspberry Pi Motor Control and Camera Streaming</title>
</head>
<body>
<h1>Motor Control</h1>
<form action="/start">
    <button type="submit">Start Motor</button>
</form>
<form action="/stop">
    <button type="submit">Stop Motor</button>
</form>
<form action="/left">
    <button type="submit">Move Left</button>
</form>
<form action="/right">
    <button type="submit">Move Right</button>
</form>
<form action="/back">
    <button type="submit">Move Back</button>
</form>
<p>{}</p>
<h1>Camera Streaming</h1>
<iframe src="/stream.mjpg" width="640" height="480"></iframe>
</body>
</html>
"""

def handle_request(path):
    print('Request:', path)  # Debug print
    response_message = ''
    if path.startswith('/start'):
        pwm1.ChangeDutyCycle(100)  # Start motor 1
        GPIO.output(IN1, GPIO.HIGH)
        GPIO.output(IN2, GPIO.LOW)

        pwm2.ChangeDutyCycle(100)  # Start motor 2
        GPIO.output(IN3, GPIO.HIGH)
        GPIO.output(IN4, GPIO.LOW)

        response_message = 'Motor started'
    elif path.startswith('/stop'):
        pwm1.ChangeDutyCycle(0)  # Stop motor 1
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.LOW)

        pwm2.ChangeDutyCycle(0)  # Stop motor 2
        GPIO.output(IN3, GPIO.LOW)
        GPIO.output(IN4, GPIO.LOW)

        response_message = 'Motor stopped'
    elif path.startswith('/left'):
        pwm1.ChangeDutyCycle(0)  # Stop motor 1
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.LOW)

        pwm2.ChangeDutyCycle(100)  # Start motor 2
        GPIO.output(IN3, GPIO.HIGH)
        GPIO.output(IN4, GPIO.LOW)

        response_message = 'Moving left'
    elif path.startswith('/right'):
        pwm1.ChangeDutyCycle(100)  # Start motor 1
        GPIO.output(IN1, GPIO.HIGH)
        GPIO.output(IN2, GPIO.LOW)

        pwm2.ChangeDutyCycle(0)  # Stop motor 2
        GPIO.output(IN3, GPIO.LOW)
        GPIO.output(IN4, GPIO.LOW)

        response_message = 'Moving right'
    elif path.startswith('/back'):
        pwm1.ChangeDutyCycle(100)  # Move motor 1 backwards
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.HIGH)

        pwm2.ChangeDutyCycle(100)  # Move motor 2 backwards
        GPIO.output(IN3, GPIO.LOW)
        GPIO.output(IN4, GPIO.HIGH)

        response_message = 'Moving backwards'
    else:
        response_message = 'Invalid request'

    print(response_message)
    return response_message

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

    def get_frame(self):
        with self.condition:
            self.condition.wait()
            return self.frame

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.format('').encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning('Removed streaming client %s: %s', self.client_address, str(e))
        else:
            response = handle_request(self.path)
            content = PAGE.format(response).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
time.sleep(2)
output = StreamingOutput()
picam2.start_recording(JpegEncoder(), FileOutput(output))

def run_camera_server():
    address = ('', 8000)
    server = StreamingServer(address, StreamingHandler)
    server.serve_forever()

def run_motor_server():
    addr = ('0.0.0.0', 80)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(addr)
    s.listen(1)

    print('Listening on', addr)

    while True:
        print('Waiting for client...')
        cl, addr = s.accept()
        print('Client connected from', addr)  # Debug print
        request = cl.recv(1024)
        request = str(request)
        print('Received request:', request)  # Debug print
        response = handle_request(request)
        print('Response:', response)  # Debug print

        html = PAGE.format(response).encode('utf-8')
        print('Sending response...')
        cl.send(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n')
        cl.send(html)
        cl.close()
        print('Response sent, connection closed')

try:
    camera_thread = Thread(target=run_camera_server, daemon=True)
    camera_thread.start()

    motor_thread = Thread(target=run_motor_server, daemon=True)
    motor_thread.start()

    camera_thread.join()
    motor_thread.join()

finally:
    picam2.stop_recording()
    GPIO.cleanup()
