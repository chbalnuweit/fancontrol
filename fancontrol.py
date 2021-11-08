import RPi.GPIO as GPIO
import os
import signal
import threading
import time
import datetime
import math
from fan_lib import *
from sensor_lib import *
from influxdb import InfluxDBClient


def InitInfluxDB():
    client = InfluxDBClient(host='127.0.0.1', port=8086, username='grafana', password='raspberry', database='fancontrol')
    return client

def WriteToInfluxDB(client,measurename,name,val):
    
    # Erzeuge leere JSON Struktur
    json_body = [{
             "measurement": '',
             "tags": {
                 "name": ''
                     },
             "time": '',
             "fields": {
               "value": 0.0
             }
          }]
    
    # Schreibe Daten in JSON Struktu
    json_body[0]['measurement'] = measurename
    json_body[0]['tags']['name'] = name
    json_body[0]['fields']['value'] = val
    json_body[0]['time'] = datetime.datetime.utcnow()

    # JSON Struktur in Datenbank schreiben
    client.write_points(json_body)
    

def fancontrol():
    
    GPIO.setmode(GPIO.BCM)	# GPIO Namenskonvention "BCM" --> GPIO Nummer statt physische Pin Nummer
    
    client = InitInfluxDB()
    
    sensor_ids = Init1WireBus(4)				    # 1WireBus initialisieren und Sensor IDs vom Bus auslesen
    sensor_in  = TempSensor_Thread(sensor_ids[1])	# Sensor Instanz im eigenen Thread mit Sensor ID des Sensors im Gehaeuse
    sensor_out = TempSensor_Thread(sensor_ids[2])   # Sensor Instanz im eigenen Thread mit Sensor ID des Sensors ausserhalb
    
    #GPIO.setup(25, GPIO.IN, pull_up_down = GPIO.PUD_UP)	
    fan1 = Fan_Thread(12,25)						# Luefter Instanz im eigenen Thread mit PWM Pin auf GPIO12 und Drehzahl Pin auf GPIO 25
    fan1.start_pwm()								# PWM mit 0 Prozent Dutycycle starten
    
    # Initialisierung der Reglergroessen
    w  = 0											# Fuehrungsgroesse (Sollwert)
    y  = 0											# Rueckfuehrung aus Regelstrecke (Istwert)
    e  = 0											# Regelabweichung initialisieren
    u  = 0   										# Stellgroesse initialisieren
    Kp = 10  										# Reglerparameter Kp definieren
    
    one_second_timer = 0
    one_minute_timer = 0
 
    # Dauerschleife des Hauptprogramms fuer Temperaturregelung
    while True:
        
        # Main timer 1 ms taks
        time.sleep(0.001)
        one_second_timer += 1
        one_minute_timer += 1

        #################################
        # 1 second task
        #################################
        if one_second_timer >= 1000:
            one_second_timer = 0
            
            # Fuehrungsgroesse und Rueckfuehrung auslesen
            y  = sensor_in.get_temp() 				# Innentemperatur als Regler Rueckfuehrung "y"
            w  = sensor_out.get_temp()				# Aussentemperatur als Regler Fuehrungsgroesse "w" 
            #print("T_in: ", y)
            #print("T_out: ", w)
            
            #Regelabweichung als Reglereingang berechnen
            e = y - w      
            #print("Regelabweichung: ",e)
     
            # Wenn drinnen waermer als draussen, Stellgroesse berechnen
            if e > 0:
                
                # Stellgroesse P-Reglers auf Basis der Regelabweichung berechnen und auf ganze Zahlen abrunden
                u = math.floor(e * Kp)
                # Reglerausgang nach oben Begrenzen
                if u >= 100:
                    u = 100
                    #print("Regler in Max-Begrenzung")
                    
                # Reglerausgang nach unten begrenzen  
                if u <= 10:
                    u = 0
                    #print("Regler in Min-Begrenzung")
                    
            # Wenn draussen waermer als drinnen, Luefter abschalten
            else:
                u = 0
                  
            # Stellgroesse setzen (PWM Wert)
            fan1.set_pwm(u)
            #print("Neue Stellgroesse: ", u)
            

            # Drehzahlanzeige nur als Info, da noch keine Kaskadenregelung auf Luefterdrehzahl umgesetzt ist
            #print("Drehzahl in rpm:")
            fan_speed = fan1.get_fanspeed()
            #print(fan_speed)
            
            # Regler wird im 1 Sekunden Raster gerechnet, daher 1 Sekunde warten
        
        #########################################################################
        # 1 minute task
        #########################################################################
        if one_minute_timer >= 60000:
            one_minute_timer = 0
            
            WriteToInfluxDB(client, "Temperature", "T_in", y)
            WriteToInfluxDB(client, "Temperature", "T_out", w)
            WriteToInfluxDB(client, "Fanspeed", "Fan1", fan_speed*1.0)
            WriteToInfluxDB(client, "PWM", "Fan1", u*1.0)
        
        
        
if __name__ == "__main__":
    fancontrol()
    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()
    GPIO.cleanup()

        
         
         
         
