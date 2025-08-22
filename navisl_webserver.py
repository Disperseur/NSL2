import re
import serial
import time
import os
import math
from flask import Flask, render_template, jsonify


#settings
DEBUG = True
UPDATE_PERIOD_MS = 1000



class Boat():

    def __init__(self, serial_port):
        self.ground_speed = "0 kt"
        self.ground_speed_tbl = [0]*(36000//UPDATE_PERIOD_MS) #36000     tableau pour la moyenne glissante de vitesse sol
        self.ground_speed_tbl_i = 0
        self.ground_speed_avg_30min = 0
        self.ground_speed_avg_1h = 0

        self.long = "001°08.9214' W"
        self.lat = "44°39.6210' N"
        self.heading = "-"

        self.time = "-"

        self.date = "-"
        self.month = "-"
        self.year = "-"

        self.wind_speed = "0 kt"
        self.wind_speed_avg_30min = "0 kt"
        self.wind_speed_avg_1h = "0 kt"
        self.wind_angle = "0°"

        self.water_speed = "-"
        self.water_temp = "-"
        self.water_depth = "-"



        #connextion au bateau ou ouverture du fichier log
        if not DEBUG:
            self.port = serial.Serial(serial_port, 57600)
        else:
            log_file = open("nav1.txt", 'r')
            self.log_file_lines = log_file.readlines()
            self.log_file_index = 0



    def parse_nmea(self):
        
        #lecture du port serie ou de la ligne du fichier de log
        if not DEBUG:
            sentence = self.port.readline().decode()
        else:
            sentence = self.log_file_lines[self.log_file_index]
            if self.log_file_index < len(self.log_file_lines)-1:
                self.log_file_index += 1
            else:
                self.log_file_index = 0 #retour au debut du fichier pour test
        
        nmea_rmc_re = re.compile(r"\$GPRMC,(?P<time>.*),(?P<champ1>.*),(?P<lat>.*),(?P<champ3>.*),(?P<long>.*),(?P<champ5>.*),(?P<ground_speed>.*),(?P<heading>.*),(?P<date>.*),,,(?P<champ11>.*)\*(?P<checksum>.*)")
        nmea_dbt_re = re.compile(r"\$SDDBT,(?P<depth_ft>.*),(?P<champ1>.*),(?P<depth_m>.*),(?P<champ3>.*),(?P<depth_f>.*),(?P<champ5>.*)\*(?P<checksum>.*)")
        nmea_mwv_re = re.compile(r"\$WIMWV,(?P<wind_angle>.*),(?P<champ1>.*),(?P<wind_speed_kt>.*),(?P<champ3>.*),(?P<champ4>.*)\*(?P<checksum>.*)")
        nmea_mtw_re = re.compile(r"\$WIMTW,(?P<water_temp>.*),(?P<champ1>.*)\*(?P<checksum>.*)")
        nmea_vhw_re = re.compile(r"\$VWVHW,,,,,(?P<speed_kt>.*),N,(?P<speed_kmh>.*),K\*(?P<checksum>.*)")

        nmea_rmc_parsed = nmea_rmc_re.match(sentence)
        nmea_dbt_parsed = nmea_dbt_re.match(sentence)
        nmea_mwv_parsed = nmea_mwv_re.match(sentence)
        nmea_mtw_parsed = nmea_mtw_re.match(sentence)
        nmea_vhw_parsed = nmea_vhw_re.match(sentence)


        if (nmea_rmc_parsed != None):
            self.time = f"{nmea_rmc_parsed.group('time')[0:2]}:{nmea_rmc_parsed.group('time')[2:4]}:{nmea_rmc_parsed.group('time')[4:]}"
            
            self.lat = f"{nmea_rmc_parsed.group('lat')[0:2]}°{nmea_rmc_parsed.group('lat')[2:]}' {nmea_rmc_parsed.group('champ3')}"
            self.long= f"{nmea_rmc_parsed.group('long')[0:3]}°{nmea_rmc_parsed.group('long')[3:]}' {nmea_rmc_parsed.group('champ5')}"

            self.ground_speed = f"{nmea_rmc_parsed.group('ground_speed')[:-1]} kt"
            self.heading = f"{nmea_rmc_parsed.group('heading')}°"

            self.date = f"{nmea_rmc_parsed.group('date')[0:2]}/{nmea_rmc_parsed.group('date')[2:4]}/{nmea_rmc_parsed.group('date')[4:]}"

        if (nmea_dbt_parsed != None):
            self.water_depth = f"{nmea_dbt_parsed.group('depth_m')} m"

        if (nmea_mwv_parsed != None):
            self.wind_speed = f"{nmea_mwv_parsed.group('wind_speed_kt')} kt"
            self.wind_angle = f"{nmea_mwv_parsed.group('wind_angle')[:-2]}°"
        
        if (nmea_mtw_parsed != None):
            self.water_temp = f"{nmea_mtw_parsed.group('water_temp')[:-2]}°"

        if (nmea_vhw_parsed != None):
            self.water_speed = f"{nmea_vhw_parsed.group('speed_kt')[:-1]} kt"


    def calcul_stats(self):
        #moyennes de vitesse sol
        self.ground_speed_tbl[self.ground_speed_tbl_i] = float(self.ground_speed[:-3]) #ajout element
        
        #rotation indice ecriture dans tableau
        if self.ground_speed_tbl_i < len(self.ground_speed_tbl) - 1:
            self.ground_speed_tbl_i += 1
        else:
            self.ground_speed_tbl_i = 0

        #calcul des moyennes
        for i in range(len(self.ground_speed_tbl)):
            self.ground_speed_avg_1h += self.ground_speed_tbl[i]
            if i >= len(self.ground_speed_tbl) // 2:
                self.ground_speed_avg_30min += self.ground_speed_tbl[i]
        
        self.ground_speed_avg_1h /= len(self.ground_speed_tbl)
        self.ground_speed_avg_30min /= (len(self.ground_speed_tbl)/2)






#main
app = Flask(__name__)

STLou = Boat("/dev/ttyUSB0")
t_start = int(time.monotonic())

@app.route("/")
def index():
    STLou.parse_nmea()
    STLou.calcul_stats()
    return render_template("index.html", boat=STLou)

@app.route("/data")
def data():
    STLou.parse_nmea()
    STLou.calcul_stats()
    return jsonify({
        "time": STLou.time,
        "date": STLou.date,
        "lat": STLou.lat,
        "long": STLou.long,
        "heading": STLou.heading,
        "ground_speed": STLou.ground_speed,
        "ground_speed_avg_30min": STLou.ground_speed_avg_30min,
        "ground_speed_avg_1h": STLou.ground_speed_avg_1h,
        "wind_speed": STLou.wind_speed,
        "wind_angle": STLou.wind_angle,
        "water_speed": STLou.water_speed,
        "water_temp": STLou.water_temp,
        "water_depth": STLou.water_depth
    })

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=DEBUG)