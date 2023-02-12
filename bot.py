import telebot #libreria pyTelegramBot
from telebot import types

import qrcode # generador de codigo qr
from TOKEN import * # credenciales 

import threading # para ejecutar en segundo plano el bot

import folium # para generar mapas

import os  # trabajo con sistema operativo

import pickle # guardar y cargar archivos binarios
import time

# Para el servidor
from flask import Flask, request
from waitress import serve

# instanciamos al bot
bot = telebot.TeleBot(TOKEN, parse_mode='html')
# instanciamos el servidor
web_server = Flask(__name__)


chats_ids = []


# Ayuda QR
def ayuda(message):
    ejemplo = "<b>EJEMPLO:</b> \n"
    ejemplo += "_texto que deseo llevar a qr"
    bot.send_message(message.chat.id, ejemplo)

# Generador de Mapas
def mapas(lat, long, name):
    m = folium.Map(location=(lat, long), tiles="cartodb positron")
    m.save(f"./maps/{name}.html")
    return m

# Decorador del servidor
@web_server.route("/", methods=['POST'])
def webhook():
    if request.headers.get('content-type') == "aplication/json":
        update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
        bot.process_new_updates([update])
        return "OK", 200

# Capturador del comando start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "<b>Hola bienvenido al botQR</b>")
    # Lista de usuarios
    if os.path.isfile("conf.pkl"): # pregunto por si existe el archivo
        archivo = open("conf.pkl", "rb")
        ids = pickle.load(archivo) 
        n = 0
        for id in ids:
            n += 1
            if not id in chats_ids:
                chats_ids.append(id)
            print(f"ID: {n} -> {id}")    
        archivo.close()

    if not message.chat.id in chats_ids:
        chats_ids.append(message.chat.id)
    archivo = open("conf.pkl", "wb")
    pickle.dump(chats_ids, archivo)
    archivo.close()
    
# Capturador del comando qr
@bot.message_handler(commands=['qr'])
def ubi(message):
    markup = types.ReplyKeyboardMarkup()
    item1 = types.KeyboardButton("CREAR QR")
    item2 = types.KeyboardButton("AYUDA")
    markup.row(item1, item2)
    bot.send_message(message.chat.id, "<b>Creamos tu QR</b>", reply_markup=markup)
    #qr(message)

# Capturador del comando ubi
@bot.message_handler(commands=['ubi'])
def ubi(message):
    ayuda = "<b>Para obtrner un mapa offline de tu ubicacion solo debes enviarnos esta, a este bot</b>"
    bot.reply_to(message, ayuda)

# Captura de texto
@bot.message_handler(func=lambda m:True)
def cap_qr(message):
    if message.text == 'CREAR QR':
        bot.send_message(message.chat.id, 'Envie el texto que desea <b>empezando con el caracter "_" :</b>  ')
    elif message.text == 'AYUDA':
        ayuda(message)
    elif message.text[0] == '_':
        texto = message.text.strip('_')
        print(f"el texto es: {texto}")
        qr = qrcode.make(texto)
        print("Creado el codigo")
        qr = qr.save(f"./qr/{texto}.png")
        print("Guardado el codigo")
        qr = open(f'./qr/{texto}.png', 'rb')
        bot.send_photo(message.chat.id, qr)
        qr.close() # Cierro el archivo 
        os.remove(f'./qr/{texto}.png') # lo elimino

# Capturador de ubicacion
@bot.message_handler(content_types=['location'])
def handle_location(message):
    print(f"Tipo {type(message.location)} \n {message.location}")
    lat = message.location.latitude
    long = message.location.longitude
    ubicacion = "<b>Tu ubicacion es</b> \n"
    ubicacion += f"<b>Longitud:</b> {long}\n"
    ubicacion += f"<b>Latitud:</b> {lat}\n"
    x = bot.send_message(message.chat.id, ubicacion)
    name = x.message_id # id de cada mnsaje
    mapa = mapas(lat=lat, long=long, name=name) # creo el mapa con la libreria folium
    mapa = open(f"./maps/{name}.html", "rb")
    bot.send_message(message.chat.id, "Esta es tu ubicacion")
    bot.send_location(message.chat.id, lat, long)
    bot.send_chat_action(message.chat.id, action="upload_document")
    bot.send_document(message.chat.id, mapa, caption="<b>Aqui esta el mapa offline</b>")
    mapa.close() # cierro el archivo
    os.remove(f"./maps/{name}.html") # lo elimino
     
def listener():
    bot.remove_webhook()
    time.sleep(1)
    # Ponemos el bot a escuchar
    print("BOT INICIADO")
    bot.infinity_polling()

def start_web_server():
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f'https://{APP}.herokuapp.com/')
    serve(web_server, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
if __name__ == '__main__':
    # Configuramos los comandos disponibles para el bot
    bot.set_my_commands([
        telebot.types.BotCommand("/start", "Bienvenida"),
        telebot.types.BotCommand("/qr", "Crea codigo QR"),
        telebot.types.BotCommand("/ubi", "Envia un mapa offline de tu ubicacion")
        ])
    
    if os.environ.get("DYNO_RAM"):
        # Ejecutamos el bot en segundo plano usando webhook
        segundo_plano = threading.Thread(name="segundo_webhook", target=start_web_server)
    else:
        # Ejecutamos el bot en segundo plano usando pollimg
        segundo_plano = threading.Thread(name="segundo_plano", target=listener)
    segundo_plano.start()
    print("BOT YA INICIADO")