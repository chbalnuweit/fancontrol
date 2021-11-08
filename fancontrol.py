import RPi.GPIO as GPIO
import os
import threading
import time
import math
from fan_lib import *
from sensor_lib import *


GPIO.setmode(GPIO.BCM)	# GPIO Namenskonvention "BCM" --> GPIO Nummer statt physische Pin Nummer


def fancontrol():
    
    sensor_ids = Init1WireBus(4)				    # 1WireBus initialisieren und Sensor IDs vom Bus auslesen
    sensor_in  = TempSensor_Thread(sensor_ids[1])	# Sensor Instanz im eigenen Thread mit Sensor ID des Sensors im Gehaeuse
    sensor_out = TempSensor_Thread(sensor_ids[2])   # Sensor Instanz im eigenen Thread mit Sensor ID des Sensors ausserhalb
    
    fan1 = Fan_Thread(12,25)						# Luefter Instanz im eigenen Thread mit PWM Pin auf GPIO12 und Drehzahl Pin auf GPIO 25
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
            if u <= 10:
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
    fancontrol()
    GPIO.cleanup()
        
        
         
         
         
