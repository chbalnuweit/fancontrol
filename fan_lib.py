import RPi.GPIO as GPIO
import os
import threading
import time
import math


class Fan_Thread(threading.Thread):
    """
    Klasse zum Ansteuern des 4 Pin Luefters per PWM und Auslesen des Drehzahlsignals
    Parameter:
    pwm_pin   -- GPIO des PWM Signals zur Lueftersteuerung
    speed_pin -- GPIO des Drehzahlsignals
    """
    def __init__(self, pwm_pin, speed_pin):
        # Attribute initialisieren
        self.fanspeed = 0
        self.rev_counter = 0
        self.pwm_pin = pwm_pin
        self.speed_pin = speed_pin
        
        #Thread initialisieren und starten
        threading.Thread.__init__(self)
        self.start()
        
        # Init der GPIOs
        # PWM Pin fuer Steuerung konfigurieren
        GPIO.setup(pwm_pin, GPIO.OUT)												# PWM Pin als Ausgang konfigurieren
        self.GPIOPWM = GPIO.PWM(self.pwm_pin, 25000) 	 							# PWM Pin konfigurieren mit 25 khz Grundfrequenz		
        
        # Interrupt Pin fuer Drehzahlsignal konfigurieren
        GPIO.setup(speed_pin, GPIO.IN, pull_up_down = GPIO.PUD_UP)					# Drehzahlpin mit Pullup konfigurieren
        GPIO.add_event_detect(speed_pin, GPIO.RISING, callback=self.count_revs)		# ISR bei steigender Flanke am Drehzahlpin
        
    def run(self):
        """
        Berechnen der Drehzahl im Sekundentakt im eigenen Thread. 
        """
        while True:
            self.rev_counter = 0
            time.sleep(1)
            self.fanspeed = math.floor(self.rev_counter / 2.0 * 60.0)
        
    def count_revs(self, speed_pin):
        """
        Interrupt Service Routine fuer Drehzahlsignal erkennung.
        Wird bei steigender Flanke ausgeloest und inkrementiert einen Counter.
        Parameter:
        speed_pin -- GPIO mit dem ausloesenden add_event_detect
        """
        self.rev_counter += 1

    def get_fanspeed(self):
        """ Getter-Funktion fuer Luefter Drehzahl in RPM """
        return self.fanspeed

    def start_pwm(self):
        """ Starte die PWM Generierung mit 0 Prozent Dutycycle """
        self.GPIOPWM.start(0)

    def set_pwm(self, dc):
        """
        Setter-Funktion fuer neu berechneten GPIO PWM DutyCycle
        Parameter:
        dc -- DutyCycle zwischen 0 und 100 Prozent
        """
        self.GPIOPWM.ChangeDutyCycle(dc)
    

    