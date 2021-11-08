import RPi.GPIO as GPIO
import os
import threading
import time
import math
import signal

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
        self.pwm_pin = pwm_pin
        self.speed_pin = speed_pin
        
        #Thread initialisieren und starten
        threading.Thread.__init__(self)
        self.start()
        
        # Init der GPIOs
        # PWM Pin fuer Steuerung konfigurieren
        GPIO.setup(pwm_pin, GPIO.OUT)												# PWM Pin als Ausgang konfigurieren
        self.GPIOPWM = GPIO.PWM(self.pwm_pin, 25000) 	 							# PWM Pin konfigurieren mit 25 khz Grundfrequenz		
        
    def run(self):
        """
        Berechnen der Drehzahl im Sekundentakt im eigenen Thread. 
        """
        
        # Pin als Eingang mit internem Pullup gegen Vdd
        GPIO.setup(self.speed_pin, GPIO.IN, pull_up_down = GPIO.PUD_UP)				
        
        # Initialisierung der internen Variablen
        rev_counter = 0
        ms_timer = 0
        
        # Initialen Zustand des Drehzahlsignals auslesen
        state_prev = GPIO.input(self.speed_pin)
        
        while True:            
            # 1 ms Timer Inkrement
            time.sleep(0.001)
            ms_timer += 1
            
            # aktuellen Zustand des Drehzahlsignals auslesen
            state_now = GPIO.input(self.speed_pin)
            
            # bei steigender Flanke wird Counter inkrementiert
            if state_now == GPIO.HIGH and state_prev == GPIO.LOW:
                rev_counter += 1
                
            # aktuellen Zustand zwischenspeichern
            state_prev = state_now
            
            # Nach einer Sekunde die Drehzahl aus Counter berechnen
            if ms_timer >= 1000:
                rpm = rev_counter*60.0/2.0
                
                # Variablen zuruecksetzen
                rev_counter = 0
                ms_timer = 0
                
                # Drehzahl auf Object-Variable schreiben fuer Getter-Funktion
                self.fanspeed = rpm
   
    
    def count_revs(self, speed_pin):
        """
        Interrupt Service Routine fuer Drehzahlsignal erkennung.
        Wird bei steigender Flanke ausgeloest und inkrementiert einen Counter.
        Parameter:
        speed_pin -- GPIO mit dem ausloesenden add_event_detect
        """
        global rev_counter
        rev_counter += 1

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
    

    