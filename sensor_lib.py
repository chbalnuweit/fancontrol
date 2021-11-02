import RPi.GPIO as GPIO
import os
import threading
import time
import math

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


    