from utils.get_config import sendMessage,get_chat,get_id_msg,get_id_user 
from utils.dbfunctions import personal_trivial_leaderboard,global_trivial_leaderboard,update_trivial_score,get_wait_trivial_value,set_wait_trivial,unset_wait_trivial
from pyrogram import Client,errors
from pyrogram.enums import PollType
from pyrogram.handlers import PollHandler,RawUpdateHandler
from pyrogram.raw.types import UpdateMessagePollVote
import requests
import json
import random
import time
from bs4 import BeautifulSoup


categorie = {"General Knowledge"     :9,
             "Books"                 :10,
             "Film"                  :11,
             "Music"                 :12,
             "Musical & Theatres"    :13,
             "Television"            :14,
             "Video Games"           :15,
             "Board Games"           :16,
             "Science & Nature"      :17,
             "Science & Computers"   :18,
             "Science & Mathematics" :19,
             "Mythology"             :20,
             "Sports"                :21,
             "Geography"             :22,
             "History"               :23,
             "Politics"              :24,
             "Art"                   :25,
             "Celebrities"           :26,
             "Animals"               :27,
             "Vehicles"              :28,
             "Comics"                :29,
             "Science & Gadgets"     :30,
             "Japanese Anime & Manga":31,
             "Cartoon & Animations"  :32}


tipo_domanda = {"tf"       :"boolean",
                "multi"    :"multiple"}

response_code = {0:"Ok",
                 1:"No Results",
                 2:"Invalid Parameter",
                 3:"Token not found",
                 4:"Token Empty"}


global token

"""
    Chiamata per la creazione di un token che garantisce l'unicità delle domande fetchate da opentb.com
    Il token ha una vita di 6 ore se inattivo ininterrottamente.
    Una volta esaurito, va resettato e generato di nuovo.
"""
def create_token():
    global token
    url = "https://opentdb.com/api_token.php?command=request"
    resp = requests.get(url)
    data = json.loads(resp.text)
    if data["response_code"] == 0:
        token = data["token"]
    else:
        return response_code[data["response_code"]]
    return token

"""
    Chiamata per il reset del token nel caso in cui sia stato esaurito completamente.
"""
def reset_token():
    global token
    url = "https://opentb.com/api_token.php?command=reset&token=" + token
    resp = requests.get(url)
    data = json.loads(resp.text)
    if data["response_code"] == 0:
        token = data["token"]
    else:
        return response_code[data["response_code"]]
    return token



"""
    Controlla se il token è in buono stato e quindi se non lo è lo resetta o lo crea se non esistente.
"""
def check_token():
    #check token existence
    try:
        if token == None:
            token = create_token()
    except NameError:
        token = create_token()
    #check token is good
    if token == "Token Empty":
        token = reset_token()
    elif len(token) < 17:
        return sendMessage(client,message,token)
    return token


"""
    funzione ausiliaria per settare la difficoltà randomicamente
"""
def set_difficulty():
    difficulty_list = ["easy","medium","hard"]
    random.shuffle(difficulty_list)
    return difficulty_list[0]


"""
    Conversione codifica HTML in testo
"""
def html2text(strings):
    result = []
    for i in range(len(strings)):
        zuppa = BeautifulSoup(strings[i],features="lxml")
        result.append(zuppa.get_text())
    return result


"""
    Restituisce una domanda quiz tramite le api di opentdb.com
"""
global corretta
global difficolta_domanda
global versione_domanda
global categoria
global wait_trivial
wait_trivial = False
@Client.on_message()
def send_question(query,client,message):
    #check wait_quiz
    #wait_trivial = get_wait_trivial_value()
    if wait_trivial:
        return sendMessage(client,message,"__Un altro quiz è attualmente in corso.\nRiprova tra poco.__")
    #variabili globali per tenere traccia di alcune informazioni per la fine del poll
    global corretta
    global difficolta_domanda
    global versione_domanda
    global categoria
    #check token
    global token
    token = check_token()

    #build parameter for request
    if query == "/trivial":
        #Build random options for the request
        category_number = random.randint(9,32)
        category_keys = list(categorie.keys())
        values = categorie.values()
        #list comprehension per recuperare la chiave del dizionario categoria a partire dal valore random creato 
        category = str({i for i in categorie if categorie[i] == category_number}).replace("{'","").replace("'}","")
        #create question type in random mode 
        question_list = ["tf","multi"]
        random.shuffle(question_list)
        question_type = question_list[0]
        #setting difficulty
        difficulty = set_difficulty()
    else:
        splitted = query.split("/")
        try:
            category= splitted[1]
            question_type = splitted[0]
            difficulty = set_difficulty()
        except IndexError:
            return sendMessage(client,message,"__Errore formato trivial.__")

    #build api url
    api_url = "https://opentdb.com/api.php?amount=1&category=" + str(categorie[category.title()]) + "&difficulty=" + difficulty + "&type=" + tipo_domanda[question_type] + "&token=" + token
    resp = requests.get(api_url)
    data = json.loads(resp.text)
    incorrect = []
    question = ""
    correct = ""
    for item in data["results"]:
        category = item["category"]
        difficulty = item["difficulty"]
        question = item["question"]
        correct = item["correct_answer"]
        incorrect = item["incorrect_answers"]
        incorrect.append(correct)
    random.shuffle(incorrect)
    #prepare question and send
    zuppa = BeautifulSoup(question,features="lxml")
    question  = zuppa.get_text()
    incorrect = html2text(incorrect)
    
    #aggiungo handler per ricevere aggiornamenti sul quiz in corso
    #riga commentata per quando in futuro sarà possibile ricevere update anche sui quiz
    #client.add_handler(PollHandler(callback=check_trivial_updates))

    client.add_handler(RawUpdateHandler(callback=check_trivial_updates))
    corretta = incorrect.index(correct)
    versione_domanda = tipo_domanda[question_type] 
    difficolta_domanda = difficulty
    categoria = category.title()
    
    try:
        msg = client.send_poll(get_chat(message),question="Category: " + category.title() + "\nDifficulty: " + difficulty.title() + "\n" + question,options=incorrect,type=PollType.QUIZ,correct_option_id=incorrect.index(correct),open_period=20,is_anonymous=False,reply_to_message_id=get_id_msg(message))
        #Setto il wait così che non ci siano due quiz in contemporanea
        #set_wait_trivial()
        wait_trivial = True
        time.sleep(20)
        #setto a false dopo la fine del quiz
        wait_trivial = False
        #unset_wait_trivial()

    except errors.exceptions.bad_request_400.PollAnswersInvalid:
        return sendMessage(client,message,"__Errore durante invio trivial__")


punteggi = { 'Easy'  : 1,
             'Medium': 2,
             'Hard'  : 3}

"""
    Funzione che prende raw updates per ogni volta che un giocatore vota sul quiz, assegnando o meno il punteggio.
"""
@Client.on_raw_update()
def check_trivial_updates(client,update,users,chat):
    if isinstance(update,UpdateMessagePollVote):
        data = update
        player = data.user_id
        chosen = data.options[0]
        int_chosen = int.from_bytes(chosen,"big")
        if corretta == int_chosen:
            print(str(player) + " ha risposto correttamente")
            if versione_domanda.title() == 'Boolean':
                update_trivial_score(player,1,categoria)
            else:
                update_trivial_score(player,punteggi[difficolta_domanda.title()],categoria)

"""
    richiamo funzione per punteggi personali
"""
def get_personal_score(query,client,message):
    return personal_trivial_leaderboard(get_id_user(message),client,message)

"""
    richiamo funzione per classifica globale
"""
def get_global_score(query,client,message):
    return global_trivial_leaderboard(client,message)

