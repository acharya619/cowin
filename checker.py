import requests
import json
from datetime import date
import logging, time, os

bot_token = os.environ.get('BOT_TOKEN', None)

chat_id_list = []
offset = 0
endpoint = "cdn-api.co-vin.in/api"
date = date.today().strftime("%d-%m-%Y")
states_list = None

def log():
    # set up logging to file
    logging.basicConfig(
        filename='cowin.log',
        level=logging.DEBUG,
        format='[%(asctime)s]{%(pathname)s:%(lineno)d}%(levelname)s- %(message)s',
        datefmt='%H:%M:%S'
    )
    # set up logging to console
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)
    logger = logging.getLogger(__name__)
    return logger

logger = log()

headers = {
    "Accept-Language": "hi_IN",
    "Accept" : "application/json"
    }

def formUri(path):
    uri = "https://" + endpoint + path
    return uri

def fetchStatesList():
    #print(formUri("/v2/admin/location/states"))
    response = requests.get(formUri("/v2/admin/location/states"), headers={"Accept-Language": "hi_IN", "User-Agent": "PostmanRuntime/7.28.0"})
    #print(response.content)
    return json.loads(response.content)['states']

def fetchDistrictList(st_code):
    path = "/v2/admin/location/districts/" + str(st_code)
    response = requests.get(formUri(path), headers={"Accept-Language": "hi_IN", "User-Agent": "PostmanRuntime/7.28.0"})
    return json.loads(response.content)['districts']

def build_district_list(district_list):
    msg_bundle = '*_District Name - Code_*\n---------------------------------------\n'
    for district in district_list:
        msg_bundle += (district['district_name'] + " - " + str(district['district_id']) + '\n')
    #print(msg_bundle)
    return msg_bundle

def build_state_list(state_list):
    msg_bundle = '*_State Name - Code_*\n---------------------------------------\n'
    for state in states_list:
        msg_bundle += (state['state_name'] + " - " + str(state['state_id']) + '\n')
    return msg_bundle

def calenderByDistrict(districtCode):
    path = "/v2/appointment/sessions/public/calendarByDistrict"
    params = {"district_id": districtCode, "date": date}
    response = requests.get(formUri(path), params=params, headers=headers)
    logger.debug('Got response - calenderByDistrict')
    logger.debug(response.status_code)
    #logger.info(response.content)
    return json.loads(response.content)

def send_msg(bot_message, chat_id):
    for spchar in ['(', ')', '{', '}', '-', '.', ',', ':', '!']:
        bot_message = bot_message.replace(spchar, "\\" + spchar)
    uri = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + str(chat_id) + '&parse_mode=MarkdownV2&text=' + bot_message
    #print(uri, bot_message)
    response = requests.get(uri)
    logger.debug(json.loads(response.content))
    return json.loads(response.content)

def build_msg(name, pincode, fee, slot_date, capacity, age_limit, vaccine, slot_list, dose1_cap, dose2_cap):
    msg = "*_" + name + "_*\nPincode: " + pincode + "\nFee: " + fee + "\nDate: " + slot_date + "\nCapacity: " + capacity + "\nAge limit: " + age_limit + "\nVaccine: " + vaccine + "\nDose1 Capacity: " + dose1_cap + "\nDose2 Capacity: " + dose2_cap + "\n*__Slots__*\n" + "\n".join(slot_list) + "\n"
    #print(msg)
    return msg

def addToChatList(chatId, searchType, code, only45Plus, onlyAvailable):
    for chat in chat_id_list:
        changed = False
        if chat['id'] == chatId:
            if chat['type'].upper() != searchType.upper():
                chat['type'] == searchType.upper()
                changed = True
            if str(chat['code']) != str(code):
                chat['code'] = code
                changed = True
            if chat['only45Plus'].upper() != only45Plus.upper():
                chat['only45Plus'] = only45Plus.upper()
                changed = True
            if chat['onlyAvailable'].upper() != onlyAvailable.upper():
                chat['onlyAvailable'] = onlyAvailable.upper()
                changed = True
            if changed:
                send_msg("*Alert type has been changed to* \nBased on: " + searchType + ", District code: " + code + ", 18+ Only: " + only45Plus + ", Only Available Slots: " + onlyAvailable, chatId)
                return True
            else:
                send_msg("Alerts are already configured with given settings, Nothing Changed!", chatId)
                return False
    chat_id_list.append({"id": chatId, "type": searchType, "code": code, "only45Plus": only45Plus, "onlyAvailable": onlyAvailable})
    logger.info("New Alert registered: " + str(chat_id_list))
    send_msg("*Alert has been added*\n Based on: " + searchType + ", District code: " + code + ", 18+ Only: " + only45Plus + ", Only Available Slots: " + onlyAvailable, chatId)
    return True

def isCodeInStateList(st_code, states_list):
    for state in states_list:
        if str(state['state_id']) == st_code:
            return True
    return False

def isCodeInDistrictList(dist_code, district_list):
    for dist in district_list:
        if str(dist['district_id']) == dist_code:
            return True
    return False     

def removeChatId(chatToremove):
    for chat in chat_id_list:  
        if chatToremove['id'] == chat['id']:
            chat_id_list.remove(chat)
            logger.info("Alert removed: " + str(chat_id_list))
            send_msg("Alerts Stopped", chatToremove['id'])
            
def showStatus(chat):
    for c in chat_id_list:  
        if chat['id'] == c['id']:
            searchType = c['type']
            code = c['code']
            only45Plus = c['only45Plus']
            onlyAvailable = c['onlyAvailable']
            send_msg("*Alert are enabled with:*\n Based on: " + searchType + ", District code: " + code + ", 18+ Only: " + only45Plus + ", Only Available Slots: " + onlyAvailable, chat['id'])
            return True
    send_msg("Alerts are not enabled", chat['id'])
    return False

def showHelp(chat):
    help_msg = "*_Command and Usage\n\n_*"
    help_msg += "*_help_* : show help text\n\n"
    help_msg += "*_states_* : show states with state codes\n\n"
    help_msg += "*_districts_*-{state code} : Show help text\n\n"
    help_msg += "*_status_* : Show alert status\n\n"
    help_msg += "*_district-{state code}-{district code}-{Only 18-44 Age vaccines}-{Only available slots}_* : request to enable alerts districtwise\n\n"
    help_msg += "_NOTE: Alert enabling request should follow str-int-int-[yes/no]-[yes/no] format._"
    send_msg(help_msg, chat['id'])
    
    
def update_chat_list():
    try:
        global offset, states_list
        latest_update_offset = None
        uri = "https://api.telegram.org/bot" + bot_token + "/getUpdates"
        params = {
            "offset": offset
        }
        response = requests.get(uri, params=params, headers=headers)
        updates = json.loads(response.content)
        updates_msg_list = updates["result"]
        if updates_msg_list == []:
            return
        for update in updates_msg_list:
            latest_update_offset = update['update_id']
            if 'message' not in update.keys():
                continue
            update = update['message']
            chat = update['chat']
            txt = update['text']
            command = txt.split('-')
            if len(command) == 1:
                if command[0].lower() == 'stop':
                    removeChatId(chat)
                elif command[0].lower() == 'status':
                    showStatus(chat)
                elif command[0].lower() == 'help':
                    showHelp(chat)
                elif command[0].lower() == 'states':
                    send_msg(build_state_list(states_list), chat['id'])
                else:
                    send_msg("Not a valid format, Alerts not enabled.", chat['id'])
            elif len(command) == 2 and command[0].lower() == 'districts':
                district_list = fetchDistrictList(command[1])
                send_msg(build_district_list(district_list), chat['id'])
            elif len(command) == 5:
                if command[0].lower() == "district":
                    try:
                        st_code = command[1]
                        dist_code = command[2]
                        only45Plus = command[3]
                        onlyAvailable = command[4]
                        if isCodeInStateList(st_code, states_list):
                            district_list = fetchDistrictList(st_code)
                            if isCodeInDistrictList(dist_code, district_list):
                                if only45Plus.upper() in ['Y', 'N', 'YES', 'NO']:
                                    if onlyAvailable.upper() in ['Y', 'N', 'YES', 'NO']:
                                        addToChatList(chat['id'], command[0].lower(), dist_code, only45Plus, onlyAvailable)
                                    else:
                                        logger.error("Choose [Only Available slots] parameter as Y/N/Yes/No")
                                        send_msg("Choose [Only Available slots] parameter as Yes or No", chat['id'])
                                else:
                                    logger.error("Choose [Only 18+ Alerts] parameter as Y/N/Yes/No")
                                    send_msg("Choose [Only 18+ Alerts] parameter as Yes or No", chat['id'])
                            else:
                                logger.error("Not a valid district")
                                send_msg("Not a valid district code, Alerts not enabled. Choose a valid code.", chat['id'])
                                send_msg(build_district_list(district_list), chat['id'])
                        else:
                            send_msg("Not a valid state code, Alerts not enabled. Choose a valid code.", chat['id'])
                            send_msg(build_state_list(states_list), chat['id'])
                    except Exception as e:
                        logger.error(e)
                else:
                    send_msg("Not a valid format, Alerts not enabled.", chat['id'])
            elif len(command) == 2:
                if command[0].lower() == "pincode":
                    try:
                        pincode = command[1]
                        addToChatList(chat[id], searchType="pincode")
                    except Exception as e:
                        logger.error(e)
                else:
                    send_msg("Not a valid format, Alerts not enabled.", chat['id'])
            else:
                send_msg("Not a valid format, Alerts not enabled.", chat['id'])
        offset = latest_update_offset + 1 
    except Exception as e:
        logger.error(e)
        

def parse_json_response(response, chat):
    centers = response['centers']
    for center in centers:
        name = center["name"]
        pincode = str(center["pincode"])
        fee = center["fee_type"]
        msg = ""
        for session in center["sessions"]:
            slot_date = session["date"]
            capacity = str(session["available_capacity"])
            age_limit = str(session["min_age_limit"])
            vaccine = session["vaccine"]
            slot_list = session["slots"]
            dose1_cap = str(session["available_capacity_dose1"])
            dose2_cap = str(session["available_capacity_dose2"])
            if (chat['onlyAvailable'].upper() == 'Y' or chat['onlyAvailable'].upper() == 'YES') and capacity > '0':
                if (chat['only45Plus'].upper() == 'Y' or chat['only45Plus'].upper() == 'YES') and age_limit < '45':
                    msg += build_msg(name, pincode, fee, slot_date, capacity, age_limit, vaccine, slot_list, dose1_cap, dose2_cap)
                elif chat['only45Plus'].upper() == 'N' or chat['only45Plus'].upper() == 'NO':
                    msg += build_msg(name, pincode, fee, slot_date, capacity, age_limit, vaccine, slot_list, dose1_cap, dose2_cap)
            elif chat['onlyAvailable'].upper() == 'N' or chat['onlyAvailable'].upper() == 'NO':
                if (chat['only45Plus'].upper() == 'Y' or chat['only45Plus'].upper() == 'YES') and age_limit < '45':
                    msg += build_msg(name, pincode, fee, slot_date, capacity, age_limit, vaccine, slot_list, dose1_cap, dose2_cap)
                elif chat['only45Plus'].upper() == 'N' or chat['only45Plus'].upper() == 'NO':
                    msg += build_msg(name, pincode, fee, slot_date, capacity, age_limit, vaccine, slot_list, dose1_cap, dose2_cap)  
        if msg != "":
            send_msg(msg, chat['id'])
                      
                
            
    
if __name__ == "__main__":
    try:
        if bot_token is None:
            raise Exception('Bot token missing')
        logger.info("...Service started...")
        states_list = fetchStatesList()
        limit = 15
        while True:
            strt_time = time.time()
            logger.debug(str(chat_id_list) if chat_id_list != [] else "No Chat IDs found")
            update_chat_list()
            for chat in chat_id_list:
                chat_id = chat['id']
                if chat['type'] == "district":
                    response = calenderByDistrict(chat['code'])
                    parse_json_response(response, chat) 
                elif chat['type'] == "pincode":
                    send_msg("_Coming soon...!_", chat_id)
                    pass
            curr_time = time.time()
            if (curr_time - strt_time) < limit:
                time.sleep(limit - (curr_time - strt_time))
    except Exception as e:
        logger.error(e) 
