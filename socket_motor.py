# socket_motor.py
import RPi.GPIO as GPIO
import socket
import time

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

# Create a socket server
addr = ('0.0.0.0', 80)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(addr)
s.listen(1)

print('Listening on', addr)

def handle_request(req):
    print('Request:', req)  # Debug print
    if 'GET /start' in req:
        pwm1.ChangeDutyCycle(100)  # Start motor 1
        GPIO.output(IN1, GPIO.HIGH)
        GPIO.output(IN2, GPIO.LOW)

        pwm2.ChangeDutyCycle(100)  # Start motor 2
        GPIO.output(IN3, GPIO.HIGH)
        GPIO.output(IN4, GPIO.LOW)

        return 'Motor started'
    elif 'GET /stop' in req:
        pwm1.ChangeDutyCycle(0)  # Stop motor 1
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.LOW)

        pwm2.ChangeDutyCycle(0)  # Stop motor 2
        GPIO.output(IN3, GPIO.LOW)
        GPIO.output(IN4, GPIO.LOW)

        return 'Motor stopped'
    elif 'GET /left' in req:
        pwm1.ChangeDutyCycle(0)  # Stop motor 1
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.LOW)

        pwm2.ChangeDutyCycle(100)  # Start motor 2
        GPIO.output(IN3, GPIO.HIGH)
        GPIO.output(IN4, GPIO.LOW)

        return 'Moving left'
    elif 'GET /right' in req:
        pwm1.ChangeDutyCycle(100)  # Start motor 1
        GPIO.output(IN1, GPIO.HIGH)
        GPIO.output(IN2, GPIO.LOW)

        pwm2.ChangeDutyCycle(0)  # Stop motor 2
        GPIO.output(IN3, GPIO.LOW)
        GPIO.output(IN4, GPIO.LOW)

        return 'Moving right'
    elif 'GET /back' in req:
        pwm1.ChangeDutyCycle(100)  # Move motor 1 backwards
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.HIGH)

        pwm2.ChangeDutyCycle(100)  # Move motor 2 backwards
        GPIO.output(IN3, GPIO.LOW)
        GPIO.output(IN4, GPIO.HIGH)

        return 'Moving backwards'
    return 'Invalid request'

while True:
    print('Waiting for client...')
    cl, addr = s.accept()
    print('Client connected from', addr)  # Debug print
    request = cl.recv(1024)
    request = str(request)
    print('Received request:', request)  # Debug print
    response = handle_request(request)
    print('Response:', response)  # Debug print
    
    html = """<!DOCTYPE html>
    <html>
    <head>
        <title>Motor Control</title>
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
    </body>
    </html>
    """.format(response)
    
    print('Sending response...')
    cl.send(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n')
    cl.send(html.encode('utf-8'))
    cl.close()
    print('Response sent, connection closed')
