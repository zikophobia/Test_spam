import requests, os, sys, jwt, json, binascii, time, urllib3, xKEys, base64, datetime, re, socket, threading
import psutil
from protobuf_decoder.protobuf_decoder import Parser
from byte import *
from byte import xSendTeamMsg, xSEndMsg
from byte import Auth_Chat
from xHeaders import *
from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp
from concurrent.futures import ThreadPoolExecutor
from threading import Thread
from black9 import openroom, spmroom
import telebot
from telebot import types
import logging

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  

TOKEN = "TOKEN"
ADMIN_IDS = [7375963526]

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

connected_clients = {}
connected_clients_lock = threading.Lock()

active_spam_targets = {}
active_room_spam_targets = {}
active_spam_lock = threading.Lock()

spam_initiators = {}
spam_initiators_lock = threading.Lock()

spam_start_times = {}
spam_start_times_lock = threading.Lock()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS
    chat_type = message.chat.type
    
    if chat_type != 'private':
        msg = (
            "<b>🎮 Spam Bot Commands</b>\n\n"
            "<b>📝 Available Commands:</b>\n"
            "• <code>/spam {id} {hours}</code> - Start normal spam\n"
            "• <code>/room {id} {hours}</code> - Start room spam\n"
            "• <code>/status {id}</code> - Check spam status\n"
            "• <code>/stop_spam {id}</code> - Stop normal spam\n"
            "• <code>/stop_room {id}</code> - Stop room spam\n\n"
            "<b>⏰ Note:</b> Maximum 24 hours\n\n"
            "<b>📞 Support:</b> @noseyrobot"
        )
    else:
        if is_admin:
            msg = (
                "<b>👑 Welcome Admin</b>\n\n"
                "<b>📝 Available Commands:</b>\n"
                "• <code>/spam {id} {hours/d}</code> - Start normal spam (use d for days)\n"
                "• <code>/room {id} {hours/d}</code> - Start room spam (use d for days)\n"
                "• <code>/status {id}</code> - Check spam status\n"
                "• <code>/stop_spam {id}</code> - Stop normal spam\n"
                "• <code>/stop_room {id}</code> - Stop room spam\n"
                "• <code>/restart</code> - Restart accounts (Admin only)\n\n"
                "<b>📞 Support:</b> @noseyrobot"
            )
        else:
            msg = "🗿"
    
    bot.reply_to(message, msg)

@bot.message_handler(func=lambda message: message.chat.type == 'private' and message.from_user.id not in ADMIN_IDS and not message.text.startswith('/'))
def handle_private(message):
    bot.reply_to(message, "🗿")

@bot.message_handler(commands=['spam'])
def spam_command(message):
    user_id = message.from_user.id
    args = message.text.split()
    
    try:
        if len(args) != 3:
            bot.reply_to(message, "<b>❌ Wrong Format</b>\nUse: <code>/spam {id} {hours}</code>")
            return
        
        target_id = args[1]
        
        if user_id in ADMIN_IDS:
            time_value = args[2]
            if 'd' in time_value:
                days = int(time_value.replace('d', ''))
                hours = days * 24
            else:
                hours = int(time_value)
        else:
            hours = int(args[2])
        
        if hours <= 0 or hours > 720:
            bot.reply_to(message, "<b>❌ Error</b>\nMaximum 30 days (720 hours)")
            return
        
        if not ChEck_Commande(target_id):
            bot.reply_to(message, "<b>❌ Error</b>\nInvalid user_id")
            return
        
        with active_spam_lock:
            if target_id in active_spam_targets:
                bot.reply_to(message, f"<b>⚠️ This account is already in spam</b>")
                return
            
            active_spam_targets[target_id] = {
                'active': True,
                'start_time': datetime.now(),
                'duration': hours,
                'type': 'normal',
                'initiator': user_id
            }
            
            with spam_start_times_lock:
                spam_start_times[target_id] = datetime.now()
            
            with spam_initiators_lock:
                spam_initiators[target_id] = user_id
            
            threading.Thread(target=normal_spam_worker, args=(target_id, hours), daemon=True).start()
            
            time_text = "days" if hours >= 24 else "hours"
            time_value = hours // 24 if hours >= 24 else hours
            
            bot.reply_to(
                message, 
                f"<b>✅ Successfully started spam for ID <code>{target_id}</code> for {time_value} {time_text}</b>"
            )
            
    except ValueError:
        bot.reply_to(message, "<b>❌ Error</b>\nPlease enter a valid number")
    except Exception as e:
        bot.reply_to(message, f"<b>❌ Error:</b> {str(e)}")

@bot.message_handler(commands=['room'])
def room_command(message):
    user_id = message.from_user.id
    args = message.text.split()
    
    try:
        if len(args) != 3:
            bot.reply_to(message, "<b>❌ Wrong Format</b>\nUse: <code>/room {id} {hours}</code>")
            return
        
        target_id = args[1]
        
        if user_id in ADMIN_IDS:
            time_value = args[2]
            if 'd' in time_value:
                days = int(time_value.replace('d', ''))
                hours = days * 24
            else:
                hours = int(time_value)
        else:
            hours = int(args[2])
        
        if hours <= 0 or hours > 720:
            bot.reply_to(message, "<b>❌ Error</b>\nMaximum 30 days (720 hours)")
            return
        
        if not ChEck_Commande(target_id):
            bot.reply_to(message, "<b>❌ Error</b>\nInvalid user_id")
            return
        
        with active_spam_lock:
            if target_id in active_room_spam_targets:
                bot.reply_to(message, f"<b>⚠️ This account is already in room spam</b>")
                return
            
            active_room_spam_targets[target_id] = {
                'active': True,
                'start_time': datetime.now(),
                'duration': hours,
                'type': 'room',
                'initiator': user_id
            }
            
            with spam_start_times_lock:
                spam_start_times[f"room_{target_id}"] = datetime.now()
            
            with spam_initiators_lock:
                spam_initiators[f"room_{target_id}"] = user_id
            
            threading.Thread(target=room_spam_worker, args=(target_id, hours), daemon=True).start()
            
            time_text = "days" if hours >= 24 else "hours"
            time_value = hours // 24 if hours >= 24 else hours
            
            bot.reply_to(
                message, 
                f"<b>✅ Successfully started room spam for ID <code>{target_id}</code> for {time_value} {time_text}</b>"
            )
            
    except ValueError:
        bot.reply_to(message, "<b>❌ Error</b>\nPlease enter a valid number")
    except Exception as e:
        bot.reply_to(message, f"<b>❌ Error:</b> {str(e)}")

@bot.message_handler(commands=['status'])
def status_command(message):
    user_id = message.from_user.id
    args = message.text.split()
    
    try:
        if len(args) != 2:
            bot.reply_to(message, "<b>❌ Wrong Format</b>\nUse: <code>/status {id}</code>")
            return
        
        target_id = args[1]
        found = False
        
        with active_spam_lock:
            if target_id in active_spam_targets:
                with spam_start_times_lock:
                    if target_id in spam_start_times:
                        start_time = spam_start_times[target_id]
                        elapsed = datetime.now() - start_time
                        total_seconds = int(elapsed.total_seconds())
                        duration = active_spam_targets[target_id]['duration'] * 3600
                        remaining = duration - total_seconds
                        
                        if remaining > 0:
                            days = remaining // 86400
                            hours = (remaining % 86400) // 3600
                            minutes = (remaining % 3600) // 60
                            seconds = remaining % 60
                            
                            time_parts = []
                            if days > 0:
                                time_parts.append(f"{days}d")
                            if hours > 0:
                                time_parts.append(f"{hours}h")
                            if minutes > 0:
                                time_parts.append(f"{minutes}m")
                            if seconds > 0:
                                time_parts.append(f"{seconds}s")
                            
                            time_left = " ".join(time_parts)
                            
                            bot.reply_to(
                                message,
                                f"<b>📊 Spam Status</b>\n\n"
                                f"<b>Target:</b> <code>{target_id}</code>\n"
                                f"<b>Type:</b> Normal Spam\n"
                                f"<b>Time Left:</b> {time_left}\n"
                                f"<b>Started By:</b> <code>{active_spam_targets[target_id]['initiator']}</code>"
                            )
                            found = True
        
        if not found:
            with active_spam_lock:
                if target_id in active_room_spam_targets:
                    with spam_start_times_lock:
                        room_key = f"room_{target_id}"
                        if room_key in spam_start_times:
                            start_time = spam_start_times[room_key]
                            elapsed = datetime.now() - start_time
                            total_seconds = int(elapsed.total_seconds())
                            duration = active_room_spam_targets[target_id]['duration'] * 3600
                            remaining = duration - total_seconds
                            
                            if remaining > 0:
                                days = remaining // 86400
                                hours = (remaining % 86400) // 3600
                                minutes = (remaining % 3600) // 60
                                seconds = remaining % 60
                                
                                time_parts = []
                                if days > 0:
                                    time_parts.append(f"{days}d")
                                if hours > 0:
                                    time_parts.append(f"{hours}h")
                                if minutes > 0:
                                    time_parts.append(f"{minutes}m")
                                if seconds > 0:
                                    time_parts.append(f"{seconds}s")
                                
                                time_left = " ".join(time_parts)
                                
                                bot.reply_to(
                                    message,
                                    f"<b>📊 Spam Status</b>\n\n"
                                    f"<b>Target:</b> <code>{target_id}</code>\n"
                                    f"<b>Type:</b> Room Spam\n"
                                    f"<b>Time Left:</b> {time_left}\n"
                                    f"<b>Started By:</b> <code>{active_room_spam_targets[target_id]['initiator']}</code>"
                                )
                                found = True
        
        if not found:
            bot.reply_to(message, f"<b>❌ No active spam found for ID <code>{target_id}</code></b>")
            
    except Exception as e:
        bot.reply_to(message, f"<b>❌ Error:</b> {str(e)}")

@bot.message_handler(commands=['stop_spam'])
def stop_spam_command(message):
    user_id = message.from_user.id
    args = message.text.split()
    
    try:
        if len(args) != 2:
            bot.reply_to(message, "<b>❌ Wrong Format</b>\nUse: <code>/stop_spam {id}</code>")
            return
        
        target_id = args[1]
        
        with active_spam_lock:
            if target_id not in active_spam_targets:
                bot.reply_to(message, f"<b>❌ No active spam found for ID <code>{target_id}</code></b>")
                return
            
            with spam_initiators_lock:
                initiator = spam_initiators.get(target_id)
                if initiator != user_id and user_id not in ADMIN_IDS:
                    bot.reply_to(
                        message, 
                        "<b>⛔ Sorry, you cannot stop this spam. Only the person who added the ID can stop it.</b>"
                    )
                    return
                
                if target_id in spam_initiators:
                    del spam_initiators[target_id]
            
            with spam_start_times_lock:
                if target_id in spam_start_times:
                    del spam_start_times[target_id]
            
            del active_spam_targets[target_id]
            
            bot.reply_to(
                message, 
                f"<b>✅ Successfully stopped spam for target ID <code>{target_id}</code></b>"
            )
            
    except Exception as e:
        bot.reply_to(message, f"<b>❌ Error:</b> {str(e)}")

@bot.message_handler(commands=['stop_room'])
def stop_room_command(message):
    user_id = message.from_user.id
    args = message.text.split()
    
    try:
        if len(args) != 2:
            bot.reply_to(message, "<b>❌ Wrong Format</b>\nUse: <code>/stop_room {id}</code>")
            return
        
        target_id = args[1]
        room_key = f"room_{target_id}"
        
        with active_spam_lock:
            if target_id not in active_room_spam_targets:
                bot.reply_to(message, f"<b>❌ No active room spam found for ID <code>{target_id}</code></b>")
                return
            
            with spam_initiators_lock:
                initiator = spam_initiators.get(room_key)
                if initiator != user_id and user_id not in ADMIN_IDS:
                    bot.reply_to(
                        message, 
                        "<b>⛔ Sorry, you cannot stop this spam. Only the person who added the ID can stop it.</b>"
                    )
                    return
                
                if room_key in spam_initiators:
                    del spam_initiators[room_key]
            
            with spam_start_times_lock:
                if room_key in spam_start_times:
                    del spam_start_times[room_key]
            
            del active_room_spam_targets[target_id]
            
            bot.reply_to(
                message, 
                f"<b>✅ Successfully stopped room spam for target ID <code>{target_id}</code></b>"
            )
            
    except Exception as e:
        bot.reply_to(message, f"<b>❌ Error:</b> {str(e)}")

@bot.message_handler(commands=['restart'])
def restart_command(message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "<b>❌ This command is for admins only</b>")
        return
    
    bot.reply_to(message, "<b>🔄 Restarting accounts...</b>")
    threading.Thread(target=restart_accounts, daemon=True).start()

def restart_accounts():
    time.sleep(2)
    ResTarT_BoT()

def AuTo_ResTartinG():
    time.sleep(6 * 60 * 60)
    print(' - AuTo ResTartinG The BoT ... ! ')
    p = psutil.Process(os.getpid())
    for handler in p.open_files():
        try:
            os.close(handler.fd)
        except Exception as e:
            print(f" - Error CLose Files : {e}")
    for conn in p.net_connections():
        try:
            if hasattr(conn, 'fd'):
                os.close(conn.fd)
        except Exception as e:
            print(f" - Error CLose Connection : {e}")
    sys.path.append(os.path.dirname(os.path.abspath(sys.argv[0])))
    python = sys.executable
    os.execl(python, python, *sys.argv)
       
def ResTarT_BoT():
    print(' - ResTartinG The BoT ... ! ')
    p = psutil.Process(os.getpid())
    open_files = p.open_files()
    connections = p.net_connections()
    for handler in open_files:
        try:
            os.close(handler.fd)
        except Exception:
            pass           
    for conn in connections:
        try:
            conn.close()
        except Exception:
            pass
    sys.path.append(os.path.dirname(os.path.abspath(sys.argv[0])))
    python = sys.executable
    os.execl(python, python, *sys.argv)

def GeT_Time(timestamp):
    last_login = datetime.fromtimestamp(timestamp)
    now = datetime.now()
    diff = now - last_login   
    d = diff.days
    h , rem = divmod(diff.seconds, 3600)
    m , s = divmod(rem, 60)    
    return d, h, m, s

def Time_En_Ar(t): 
    return ' '.join(t.replace("Day","Day").replace("Hour","Hour").replace("Min","Min").replace("Sec","Sec").split(" - "))
    
Thread(target = AuTo_ResTartinG , daemon = True).start()

ACCOUNTS = []

def load_accounts_from_file(filename="accs.json"):
    accounts = []
    try:
        with open(filename, "r", encoding="utf-8") as file:
            data = json.load(file)
            
            if isinstance(data, list):
                for account in data:
                    if isinstance(account, dict):
                        account_id = account.get('uid', '')
                        password = account.get('password', '')
                        
                        if account_id:
                            accounts.append({
                                'id': str(account_id),
                                'password': password
                            })
            
            print(f"Loaded {len(accounts)} accounts from {filename}")
            
    except FileNotFoundError:
        print(f"File {filename} not found!")
    except json.JSONDecodeError:
        print(f"JSON format error in file {filename}!")
    except Exception as e:
        print(f"Error reading file: {e}")
    
    return accounts

ACCOUNTS = load_accounts_from_file()

def normal_spam_worker(target_id, duration_hours=None):
    print(f"Starting normal spam on target: {target_id}" + (f" for {duration_hours} hours" if duration_hours else ""))
    
    start_time = datetime.now()
    
    while True:
        with active_spam_lock:
            if target_id not in active_spam_targets:
                print(f"Normal spam stopped on target: {target_id}")
                break
                
            if duration_hours:
                elapsed = datetime.now() - start_time
                if elapsed.total_seconds() >= duration_hours * 3600:
                    print(f"Normal spam duration ended for target: {target_id}")
                    with spam_initiators_lock:
                        if target_id in spam_initiators:
                            del spam_initiators[target_id]
                    with spam_start_times_lock:
                        if target_id in spam_start_times:
                            del spam_start_times[target_id]
                    del active_spam_targets[target_id]
                    break
                
        try:
            send_normal_spam_from_all_accounts(target_id)
            time.sleep(0.1)
        except Exception as e:
            print(f"Error in normal spam on {target_id}: {e}")
            time.sleep(1)

def room_spam_worker(target_id, duration_hours=None):
    print(f"Starting room spam on target: {target_id}" + (f" for {duration_hours} hours" if duration_hours else ""))
    
    start_time = datetime.now()
    
    while True:
        with active_spam_lock:
            if target_id not in active_room_spam_targets:
                print(f"Room spam stopped on target: {target_id}")
                break
                
            if duration_hours:
                elapsed = datetime.now() - start_time
                if elapsed.total_seconds() >= duration_hours * 3600:
                    print(f"Room spam duration ended for target: {target_id}")
                    with spam_initiators_lock:
                        room_key = f"room_{target_id}"
                        if room_key in spam_initiators:
                            del spam_initiators[room_key]
                    with spam_start_times_lock:
                        if room_key in spam_start_times:
                            del spam_start_times[room_key]
                    del active_room_spam_targets[target_id]
                    break
                
        try:
            send_room_spam_from_all_accounts(target_id)
            time.sleep(0.1)
        except Exception as e:
            print(f"Error in room spam on {target_id}: {e}")
            time.sleep(1)

def send_normal_spam_from_all_accounts(target_id):
    with connected_clients_lock:
        for account_id, client in connected_clients.items():
            try:
                if (hasattr(client, 'CliEnts2') and client.CliEnts2 and 
                    hasattr(client, 'key') and client.key and 
                    hasattr(client, 'iv') and client.iv):
                    
                    for i in range(10):
                        try:
                            client.CliEnts2.send(SEnd_InV(1, target_id, client.key, client.iv))                           
                            client.CliEnts2.send(OpEnSq(client.key, client.iv))                            
                            client.CliEnts2.send(SPamSq(target_id, client.key, client.iv))
                        except (BrokenPipeError, ConnectionResetError, OSError) as e:
                            print(f"Connection error for account {account_id}: {e}")
                            break
                        except Exception as e:
                            print(f"Error sending from account {account_id}: {e}")
                            break
                else:
                    print(f"Account {account_id} connection is inactive")
            except Exception as e:
                print(f"Error sending normal spam from account {account_id}: {e}")

def send_room_spam_from_all_accounts(target_id):
    with connected_clients_lock:
        for account_id, client in connected_clients.items():
            try:
                if (hasattr(client, 'CliEnts2') and client.CliEnts2 and 
                    hasattr(client, 'key') and client.key and 
                    hasattr(client, 'iv') and client.iv):
                    
                    try:
                        client.CliEnts2.send(openroom(client.key, client.iv))
                    except Exception as e:
                        print(f"Error opening room from account {account_id}: {e}")
                    
                    for i in range(10):  
                        try:
                            client.CliEnts2.send(spmroom(client.key, client.iv, target_id))
                        except (BrokenPipeError, ConnectionResetError, OSError) as e:
                            print(f"Connection error for account {account_id}: {e}")
                            break
                        except Exception as e:
                            print(f"Error sending from account {account_id}: {e}")
                            break
                else:
                    print(f"Account {account_id} connection is inactive")
            except Exception as e:
                print(f"Error sending room spam from account {account_id}: {e}")
            
class FF_CLient():

    def __init__(self, id, password):
        self.id = id
        self.password = password
        self.key = None
        self.iv = None
        self.connection_active = True
        self.Get_FiNal_ToKen_0115()     
            
    def Connect_SerVer_OnLine(self , Token , tok , host , port , key , iv , host2 , port2):
            try:
                self.AutH_ToKen_0115 = tok    
                self.CliEnts2 = socket.create_connection((host2 , int(port2)))
                self.CliEnts2.send(bytes.fromhex(self.AutH_ToKen_0115))                  
            except:pass        
            while self.connection_active:
                try:
                    self.DaTa2 = self.CliEnts2.recv(99999)
                    if '0500' in self.DaTa2.hex()[0:4] and len(self.DaTa2.hex()) > 30:	         	    	    
                            self.packet = json.loads(DeCode_PackEt(f'08{self.DaTa2.hex().split("08", 1)[1]}'))
                            self.AutH = self.packet['5']['data']['7']['data']
                except:pass
                                                            
    def Connect_SerVer(self , Token , tok , host , port , key , iv , host2 , port2):
            self.AutH_ToKen_0115 = tok    
            self.CliEnts = socket.create_connection((host , int(port)))
            self.CliEnts.send(bytes.fromhex(self.AutH_ToKen_0115))  
            self.DaTa = self.CliEnts.recv(1024)          	        
            threading.Thread(target=self.Connect_SerVer_OnLine, args=(Token , tok , host , port , key , iv , host2 , port2)).start()
            self.Exemple = xMsGFixinG('12345678')
            
            self.key = key
            self.iv = iv
            
            with connected_clients_lock:
                connected_clients[self.id] = self
                print(f"Account {self.id} registered, total accounts: {len(connected_clients)}")
            
            while True:      
                try:
                    self.DaTa = self.CliEnts.recv(1024)   
                    if len(self.DaTa) == 0 or (hasattr(self, 'DaTa2') and len(self.DaTa2) == 0):	            		
                        print(f"Connection lost for account {self.id}, reconnecting...")
                        try:            		    
                            self.CliEnts.close()
                            if hasattr(self, 'CliEnts2'):
                                self.CliEnts2.close()
                            
                            time.sleep(3)
                            self.Connect_SerVer(Token , tok , host , port , key , iv , host2 , port2)                    		                    
                        except:
                            print(f"Failed to reconnect account {self.id}")
                            with connected_clients_lock:
                                if self.id in connected_clients:
                                    del connected_clients[self.id]
                            break	            
                                      
                    if '/pp/' in self.input_msg[:4]:
                        self.target_id = self.input_msg[4:]	 
                        self.Zx = ChEck_Commande(self.target_id)
                        if True == self.Zx:	            		     
                            threading.Thread(target=send_normal_spam_from_all_accounts, args=(self.target_id,)).start()
                            time.sleep(2.5)    			         
                            self.CliEnts.send(xSEndMsg(f'\n[b][c][{ArA_CoLor()}] SuccEss Spam To {xMsGFixinG(self.target_id)} From All Accounts\n', 2 , self.DeCode_CliEnt_Uid , self.DeCode_CliEnt_Uid , key , iv))
                            time.sleep(1.3)
                            self.CliEnts.close()
                            if hasattr(self, 'CliEnts2'):
                                self.CliEnts2.close()
                            self.Connect_SerVer(Token , tok , host , port , key , iv , host2 , port2)	            		      	
                        elif False == self.Zx: 
                            self.CliEnts.send(xSEndMsg(f'\n[b][c][{ArA_CoLor()}] - PLease Use /pp/<id>\n - Ex : /pp/{self.Exemple}\n', 2 , self.DeCode_CliEnt_Uid , self.DeCode_CliEnt_Uid , key , iv))	
                            time.sleep(1.1)
                            self.CliEnts.close()
                            if hasattr(self, 'CliEnts2'):
                                self.CliEnts2.close()
                            self.Connect_SerVer(Token , tok , host , port , key , iv , host2 , port2)	            		

                except Exception as e:
                    print(f"Error in Connect_SerVer: {e}")
                    try:
                        self.CliEnts.close()
                        if hasattr(self, 'CliEnts2'):
                            self.CliEnts2.close()
                    except:
                        pass
                    time.sleep(5)
                    try:
                        self.Connect_SerVer(Token , tok , host , port , key , iv , host2 , port2)
                    except:
                        print(f"Final reconnection failed for account {self.id}")
                        with connected_clients_lock:
                            if self.id in connected_clients:
                                del connected_clients[self.id]
                        break
                                    
    def GeT_Key_Iv(self , serialized_data):
        my_message = xKEys.MyMessage()
        my_message.ParseFromString(serialized_data)
        timestamp , key , iv = my_message.field21 , my_message.field22 , my_message.field23
        timestamp_obj = Timestamp()
        timestamp_obj.FromNanoseconds(timestamp)
        timestamp_seconds = timestamp_obj.seconds
        timestamp_nanos = timestamp_obj.nanos
        combined_timestamp = timestamp_seconds * 1_000_000_000 + timestamp_nanos
        return combined_timestamp , key , iv    

    def Guest_GeneRaTe(self , uid , password):
        self.url = "https://100067.connect.garena.com/oauth/guest/token/grant"
        self.headers = {"Host": "100067.connect.garena.com","User-Agent": "GarenaMSDK/4.0.19P4(G011A ;Android 9;en;US;)","Content-Type": "application/x-www-form-urlencoded","Accept-Encoding": "gzip, deflate, br","Connection": "close",}
        self.dataa = {"uid": f"{uid}","password": f"{password}","response_type": "token","client_type": "2","client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3","client_id": "100067",}
        try:
            self.response = requests.post(self.url, headers=self.headers, data=self.dataa).json()
            self.Access_ToKen , self.Access_Uid = self.response['access_token'] , self.response['open_id']
            time.sleep(0.2)
            return self.ToKen_GeneRaTe(self.Access_ToKen , self.Access_Uid)
        except Exception as e: 
            print(f"Error in Guest_GeneRaTe: {e}")
            time.sleep(10)
            return self.Guest_GeneRaTe(uid, password)
                                        
    def GeT_LoGin_PorTs(self , JwT_ToKen , PayLoad):
        self.UrL = 'https://clientbp.ggwhitehawk.com/GetLoginData'
        self.HeadErs = {
            'Expect': '100-continue',
            'Authorization': f'Bearer {JwT_ToKen}',
            'X-Unity-Version': '2022.3.47f1',
            'X-GA': 'v1 1',
            'ReleaseVersion': 'OB52',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
            'Host': 'clientbp.ggwhitehawk.com',
            'Connection': 'close',
            'Accept-Encoding': 'deflate, gzip',}        
        try:
                self.Res = requests.post(self.UrL , headers=self.HeadErs , data=PayLoad , verify=False)
                self.BesTo_data = json.loads(DeCode_PackEt(self.Res.content.hex()))  
                address , address2 = self.BesTo_data['32']['data'] , self.BesTo_data['14']['data'] 
                ip , ip2 = address[:len(address) - 6] , address2[:len(address2) - 6]
                port , port2 = address[len(address) - 5:] , address2[len(address2) - 5:]             
                return ip , port , ip2 , port2          
        except requests.RequestException as e:
                print(f" - Bad Requests !")
        print(" - Failed To GeT PorTs !")
        return None, None, None, None
        
    def ToKen_GeneRaTe(self , Access_ToKen , Access_Uid):
        self.UrL = "https://loginbp.ggwhitehawk.com/MajorLogin"
        self.HeadErs = {
            'X-Unity-Version': '2022.3.47f1',
            'ReleaseVersion': 'OB52',
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-GA': 'v1 1',
            'Content-Length': '928',
            'User-Agent': 'UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
            'Host': 'loginbp.ggwhitehawk.com',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'deflate, gzip'}   
        
        self.dT = bytes.fromhex('1a13323032362d30312d31342031323a31393a3032220966726565206669726528013a07312e3132302e324232416e64726f6964204f532039202f204150492d3238202850492f72656c2e636a772e32303232303531382e313134313333294a0848616e6468656c64520c4d544e2f537061636574656c5a045749464960800a68d00572033234307a2d7838362d3634205353453320535345342e3120535345342e32204156582041565832207c2032343030207c20348001e61e8a010f416472656e6f2028544d292036343092010d4f70656e474c20455320332e329a012b476f6f676c657c36323566373136662d393161372d343935622d396631362d303866653964336336353333a2010d3137362e32382e3134352e3239aa01026172b201203931333263366662373263616363666463383132306439656332636330366238ba010134c2010848616e6468656c64ca010d4f6e65506c7573204135303130d201025347ea014033646661396162396432353237306661663433326637623532383536346265396563343739306263373434613465626137303232353230373432376430633430f00101ca020c4d544e2f537061636574656cd2020457494649ca03203161633462383065636630343738613434323033626638666163363132306635e003b5ee02e803c28302f003af13f80384078004cf92028804b5ee029004cf92029804b5ee02b00404c80403d2043d2f646174612f6170702f636f6d2e6474732e667265656669726574682d49316855713474347641365f516f34432d58676165513d3d2f6c69622f61726de00401ea045f65363261623933353464386662356662303831646233333861636233333439317c2f646174612f6170702f636f6d2e6474732e667265656669726574682d49316855713474347641365f516f34432d58676165513d3d2f626173652e61706bf00406f804018a050233329a050a32303139313139363234b205094f70656e474c455332b805ff01c00504e005edb402ea05093372645f7061727479f2055c4b7173485438512b6c73302b4464496c2f4f617652726f7670795a596377676e51485151636d57776a476d587642514b4f4d63747870796f7054515754487653354a714d6967476b534c434c423651387839544161764d666c6a6f3d8806019006019a060134a2060134b206224006474f56540a011a5d0e115e00170d4b6e085709510a685a02586800096f000161')
        
        self.dT = self.dT.replace(b'2026-01-14 12:19:02' , str(datetime.now())[:-7].encode())        
        self.dT = self.dT.replace(b'3dfa9ab9d25270faf432f7b528564be9ec4790bc744a4eba70225207427d0c40' , Access_ToKen.encode())
        self.dT = self.dT.replace(b'9132c6fb72caccfdc8120d9ec2cc06b8' , Access_Uid.encode())
        
        try:
            hex_data = self.dT.hex()
            encoded_data = EnC_AEs(hex_data)
            
            if not all(c in '0123456789abcdefABCDEF' for c in encoded_data):
                print("Invalid hex output from EnC_AEs, using alternative encoding")
                encoded_data = hex_data
            
            self.PaYload = bytes.fromhex(encoded_data)
        except Exception as e:
            print(f"Error in encoding: {e}")
            self.PaYload = self.dT
        
        self.ResPonse = requests.post(self.UrL, headers = self.HeadErs ,  data = self.PaYload , verify=False)        
        if self.ResPonse.status_code == 200 and len(self.ResPonse.text) > 10:
            try:
                self.BesTo_data = json.loads(DeCode_PackEt(self.ResPonse.content.hex()))
                self.JwT_ToKen = self.BesTo_data['8']['data']           
                self.combined_timestamp , self.key , self.iv = self.GeT_Key_Iv(self.ResPonse.content)
                ip , port , ip2 , port2 = self.GeT_LoGin_PorTs(self.JwT_ToKen , self.PaYload)            
                return self.JwT_ToKen , self.key , self.iv, self.combined_timestamp , ip , port , ip2 , port2
            except Exception as e:
                print(f"Error parsing response: {e}")
                time.sleep(5)
                return self.ToKen_GeneRaTe(Access_ToKen, Access_Uid)
        else:
            print(f"Error in ToKen_GeneRaTe, status: {self.ResPonse.status_code}")
            time.sleep(5)
            return self.ToKen_GeneRaTe(Access_ToKen, Access_Uid)
      
    def Get_FiNal_ToKen_0115(self):
        try:
            result = self.Guest_GeneRaTe(self.id , self.password)
            if not result:
                print("Failed to get tokens, retrying...")
                time.sleep(5)
                return self.Get_FiNal_ToKen_0115()
                
            token , key , iv , Timestamp , ip , port , ip2 , port2 = result
            
            if not all([ip, port, ip2, port2]):
                print("Failed to get ports, retrying...")
                time.sleep(5)
                return self.Get_FiNal_ToKen_0115()
                
            self.JwT_ToKen = token        
            try:
                self.AfTer_DeC_JwT = jwt.decode(token, options={"verify_signature": False})
                self.AccounT_Uid = self.AfTer_DeC_JwT.get('account_id')
                self.EncoDed_AccounT = hex(self.AccounT_Uid)[2:]
                self.HeX_VaLue = DecodE_HeX(Timestamp)
                self.TimE_HEx = self.HeX_VaLue
                self.JwT_ToKen_ = token.encode().hex()
                print(f'ProxCed Uid : {self.AccounT_Uid}')
            except Exception as e:
                print(f"Error In ToKen : {e}")
                time.sleep(5)
                return self.Get_FiNal_ToKen_0115()
                
            try:
                self.Header = hex(len(EnC_PacKeT(self.JwT_ToKen_, key, iv)) // 2)[2:]
                length = len(self.EncoDed_AccounT)
                self.__ = '00000000'
                if length == 9: self.__ = '0000000'
                elif length == 8: self.__ = '00000000'
                elif length == 10: self.__ = '000000'
                elif length == 7: self.__ = '000000000'
                else:
                    print('Unexpected length encountered')                
                self.Header = f'0115{self.__}{self.EncoDed_AccounT}{self.TimE_HEx}00000{self.Header}'
                self.FiNal_ToKen_0115 = self.Header + EnC_PacKeT(self.JwT_ToKen_ , key , iv)
            except Exception as e:
                print(f"Error In Final Token : {e}")
                time.sleep(5)
                return self.Get_FiNal_ToKen_0115()
                
            self.AutH_ToKen = self.FiNal_ToKen_0115
            self.Connect_SerVer(self.JwT_ToKen , self.AutH_ToKen , ip , port , key , iv , ip2 , port2)        
            return self.AutH_ToKen , key , iv
            
        except Exception as e:
            print(f"Error in Get_FiNal_ToKen_0115: {e}")
            time.sleep(10)
            return self.Get_FiNal_ToKen_0115()

def start_account(account):
    try:
        print(f"Starting account: {account['id']}")
        FF_CLient(account['id'], account['password'])
    except Exception as e:
        print(f"Error starting account {account['id']}: {e}")
        time.sleep(5)
        start_account(account)

def run_bot():
    print("Bot started...")
    bot.infinity_polling()

def StarT_SerVer():
    threads = []
    
    for account in ACCOUNTS:
        thread = threading.Thread(target=start_account, args=(account,))
        thread.daemon = True
        threads.append(thread)
        thread.start()
        time.sleep(1)
    
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    StarT_SerVer()