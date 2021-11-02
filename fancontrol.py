import RPi.GPIO as GPIO
import os
import threading
import time
import math


GPIO.setmode(GPIO.BCM)	# GPIO Namenskonvention "BCM" --> GPIO Nummer statt physische Pin Nummer


def Init1WireBus(pin=4):
    """
    Initialisierung des 1WireBus und Auslesen der erkannten Sensor-IDs
    Parameter:
    pin -- GPIO Pin fuer 1Wire (default 4) 
    """
    GPIO.setup(pin, GPIO.IN)														# Konfiguriere 1WirePin als Eingang
    time.sleep(1)																	# Warte bis 1WireBus init abgeschlossen
    try:
        devices = set(os.listdir('/sys/bus/w1/devices/')) - set(['w1_bus_master1']) # Lese Sensor IDs aus Systemordner
        devices = list(devices)														# Erzeuge eine Liste der Sensor IDs (strings)
    except:
        devices=[]																	# Erzeuge leere Liste wenn Fehler beim Lesen des Sysordner
    devices.insert(0,'None')														# Fuege Dummy-Device zur Liste hinzu
    return devices


class TempSensor_Thread(threading.Thread):
    """
    Klasse fuer DS18B20 1Wire Bus Temperatur Sensoren.
    Fuer jeden Sensor wird ein eigener Thread angelegt,
    in welchem die Temperaturwerte jede Sekunde ausgelesen werden.
    Parameter:
    id -- Sensor ID (wie in Init1WireBus Funktion ausgelesen)
    """
    def __init__(self, id):

        self.id = id                                                  # Sensor ID aus der Init1Wire Funktion
        self.source = '/sys/bus/w1/devices/' + self.id + '/w1_slave'  # Pfad zur Systemdatei mit den Sensorwerten
        self.temp = -273.15                                           # Initialisierung der Temperatur mit 0K
        
        # Initialisieren und starten des Threads
        threading.Thread.__init__(self)                             
        self.start()

    def run(self):
        """
        'run' ist eine Methode der Threading Library und wird waehrend des __init__ automatisch gestartet.
        Einmal pro Sekunde wird der Sensor ausgelesen und der Temperaturwert formatiert
        """
        while True:
            try:
                f = open(self.source, 'r')							  # Lese Sensordatei
                lines = f.readlines()								  # Alle Zeilen auslesen
                f.close()											  # Datei sauber schliessen
                tempStr = lines[1].find('t=')						  # Suche nach Zeile mit "t="
                if tempStr != -1 :									  # Wenn "t=" Zeile gefunde, werte sie aus
                    tempData = lines[1][tempStr+2:]					  # "t=" Zeile zerlegen
                    self.temp = float(tempData) / 1000.0			  # Temperatur von "milliCelsius" in Celsius umrechnen
                else:
                    self.temp = -273.15								  # Wenn "t=" Zeile nicht gefunden, Initwert
            except:
                self.temp = -273.15									  # Wenn Problem beim lesen der Datei, Initwert
   
            time.sleep(1)
            
    def get_temp(self):
        """ Getter-Funktion fuer Temperatur in degC"""
        return self.temp        


    
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
        self.GPIOPWM = GPIO.PWM(self.pwm_pin, 24) 									# PWM Pin konfigurieren mit 24 khz Grundfrequenz		
        
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
    

    
def loop():
    
    sensor_ids = Init1WireBus(4)				    # 1WireBus initialisieren und Sensor IDs vom Bus auslesen
    sensor_in  = TempSensor_Thread(sensor_ids[1])	# Sensor Instanz im eigenen Thread mit Sensor ID des Sensors im Gehaeuse
    sensor_out = TempSensor_Thread(sensor_ids[2])   # Sensor Instanz im eigenen Thread mit Sensor ID des Sensors ausserhalb
    
    fan1 = Fan_Thread(24,25)						# Luefter Instanz im eigenen Thread mit PWM Pin auf GPIO24 und Drehzahl Pin auf GPIO 25
    fan1.start_pwm()								# PWM mit 0 Prozent Dutycycle starten
    
    # Initialisierung der Reglergroessen
    w  = 0											# Fuehrungsgroesse (Sollwert)
    y  = 0											# Rueckfuehrung aus Regelstrecke (Istwert)
    e  = 0											# Regelabweichung initialisieren
    u  = 0   										# Stellgroesse initialisieren
    Kp = 10  										# Reglerparameter Kp definieren
    
    # Dauerschleife des Hauptprogramms fuer Temperaturregelung
    while True:
        
        # Fuehrungsgroesse und Rueckfuehrung auslesen
        y  = sensor_in.get_temp() 				# Innentemperatur als Regler Rueckfuehrung "y"
        w  = sensor_out.get_temp()				# Aussentemperatur als Regler Fuehrungsgroesse "w" 
        print("T_in: ", y)
        print("T_out: ", w)
        
        #Regelabweichung als Reglereingang berechnen
        e = y - w      
        print("Regelabweichung: ",e)
 
        # Wenn drinnen waermer als draussen, Stellgroesse berechnen
        if e > 0:
            
            # Stellgroesse P-Reglers auf Basis der Regelabweichung berechnen und auf ganze Zahlen abrunden
            u = math.floor(e * Kp)
            # Reglerausgang nach oben Begrenzen
            if u >= 100:
                u = 100
                print("Regler in Max-Begrenzung")
                
            # Reglerausgang nach unten begrenzen  
            if u <= 0:
                u = 0
                print("Regler in Min-Begrenzung")
                
        # Wenn draussen waermer als drinnen, Luefter abschalten
        else:
            u = 0
              
        # Stellgroesse setzen (PWM Wert)
        fan1.set_pwm(u)
        print("Neue Stellgroesse: ", u)
        

        # Drehzahlanzeige nur als Info, da noch keine Kaskadenregelung auf Luefterdrehzahl umgesetzt ist
        print("Drehzahl in rpm:")
        print(fan1.get_fanspeed())
        
        # Regler wird im 1 Sekunden Raster gerechnet, daher 1 Sekunde warten
        time.sleep(1)
        
        
        
if __name__ == "__main__":
    loop()
    GPIO.cleanup()
        
        
         
         
         
