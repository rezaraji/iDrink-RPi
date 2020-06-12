# iDrink Automatic Bartender
# Ported to Raspberry Pi from Arduino
# Reza Raji
# May 28, 2020
#
# Written for Python 3
# Ported/modified from the original Arduino iDrink project
# Using dedicated touchscreen instead of iPad with web server
# Seperate Menu collection file (Menu.json)
# Using GUIZERO library for UI
# Using GPIOZERO for I/O

import threading
import time
from time import sleep
import json

with open('Menu.json') as f:  # Read in the Menu JSON file
  menu_json = json.load(f)

from guizero import App, Window, Text, TextBox, Box, PushButton, ListBox

menu_index = 0 #keep count of which menue is being displayed as user scrolls through them in the Menu screen
chosen_menu_index = 0 # the active menu chosen by the user (default is 0 of course)
pumps_ON = [0,0,0,0,0,0,0,0] #Keep track of which pumps are on during a recipe pour
DRINK_SIZE_FACTOR = 1.0     #Scale the drink up or down in size. 1 = actual specified ounce units
PUMP_POUR_RATE = 286        #How many milliseconds for a pump to pour 1/10th of an ounce of liquid
touchscreen_debounce = 0   #for debouncing the drink our tap

# Pump I/O assignments
# 8 pumps, each with a forward and reverse relay (H circuit) - 16 pins total
# First two numbers are F and R relay GPIO pins for first pump. And so on.
from gpiozero import LEDBoard
relay = LEDBoard (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17) # RPi GPIO pins being used
relay.on()  #turn off all the relays at startup (active low)

#Functions for entering the three screens (Main, Menu, Control)
def enter_main_panel():
    update_main_panel()
    window_main_menu_panel.show()
    window_main_menu_panel.focus()
    window_control_panel.hide()
    window_menu_select_panel.hide()

def enter_menu_panel():
    global menu_index
    global chosen_menu_index
    menu_index = chosen_menu_index  # start with the current active menu
    update_menu_panel()
    window_menu_select_panel.show()
    window_menu_select_panel.focus()
    window_main_menu_panel.hide()
    window_control_panel.hide()

def enter_control_panel():
    window_control_panel.show()
    window_control_panel.focus()
    window_main_menu_panel.hide()
    window_menu_select_panel.hide()

def next_menu():
    global menu_index
    menu_index += 1
    update_menu_panel()

def prev_menu():
    global menu_index
    menu_index -= 1
    update_menu_panel()

def select_menu():
    global menu_index
    global chosen_menu_index

    window_main_menu_panel.show()
    window_main_menu_panel.focus()
    window_control_panel.hide()
    window_menu_select_panel.hide()
    chosen_menu_index = menu_index #set the chosen menu to the user selection
    update_main_panel() #Now rebuild the Main screen

# Main panel update for the chosen_menu_index (update Menu Name name, Drink buttons)
def update_main_panel():
    global chosen_menu_index
    #repopulate the drink list for this menu
    main_drinks_list.clear()  # clear the existing drink list
    y = 0  # ListBox entry index
    for x in menu_json['Menu'][chosen_menu_index]['Drink']: #now repopulate it
        main_drinks_list.insert(y, x['Name'])
        y = y+1
    main_drinks_list.text_size = "30"
    main_drinks_list.text_color = "blue"

# Menu panel update for the menu_index (update Menu Name name, Bottles and Drink Names)
def update_menu_panel():
    global menu_index
    message_menu1.clear()
    message_menu1.value = menu_json['Menu'][menu_index]['MenuName']
    message_menu3.clear()
    message_menu3.value = menu_json['Menu'][menu_index]['Bottles']
    menu_menu_drink_list.clear()
    menu_menu_drink_list.value = "Drinks: "

    for x in menu_json['Menu'][menu_index]['Drink']:
        #menu_menu_drink_list.append(x['Name'])
        menu_menu_drink_list.append(x['Name'])
        menu_menu_drink_list.append(x['Recipe'])
        menu_menu_drink_list.font = "helvetica"
        menu_menu_drink_list.text_size = "25"
        menu_menu_drink_list.text_color = "red"

    # Prevent user from going out of bounds on the menu array
    if len(menu_json['Menu']) == (menu_index + 1):  #last entry in the Menu array so don't allow "Next"
        button_next_menu.enabled = False
    else: button_next_menu.enabled = True
    if (menu_index == 0):                       #first entry in the Menu array so don't allow "Prev"
        button_prev_menu.enabled = False
    else: button_prev_menu.enabled = True

# Thread function for handling drink pours (so the entire app isn;t locked up during)
def thread_function(value):
    x = threading.Thread(target=pour_drink, args=(value,))
    x.start()

# Pour a drink recipe with upto 8 liquid ingredients poured in parallel
# Drink recipe is specified in 1/10th of an ounce in the Menu.json file
# Unused pumps/ingredients should be assigned a "0" (zero) in the JSON file
# Notes: This routine does not return UNTIL the drink has finished pouring. So can not do other activity (e.g. lights control)
# Might try using timer interrupts (but that's for later)
def pour_drink(value):
    global chosen_menu_index
    global touchscreen_debounce

    main_drinks_list.disable() #disallow the user tapping another drink

    if time.time() < (touchscreen_debounce+1): #debounce in seconds
        return

    touchscreen_debounce = time.time()  #snap shot the current time

    sleep (0.2) #pause briefly for aesthetics

    drink_pour_label.append("       Pouring a: ") #announce what's being poured at the bottom banner
    drink_pour_text.append(value)

    # Get the recipe for that index (load into an array)
    for key in menu_json['Menu'][chosen_menu_index]['Drink']:
        if (key['Name'] == value):
            recipe = key['Recipe']

    # Reset the pump ON flag array
    for x in range(8):
        pumps_ON[x] = 0

    # Turn on the relevant pumps for this drink recipe
    for x in range (8):
        if recipe[x] != 0:
            drive_pump(x+1,'FORWARD') #turn on pump
            pumps_ON[x] = 1     #flag that pump as ON

    time_epoch = time.time() * 1000  #get current millisoconds since epoch

    while ((pumps_ON[0] + pumps_ON[1] + pumps_ON[2] + pumps_ON[3] + pumps_ON[4] + pumps_ON[5] + pumps_ON[6] + pumps_ON[7]) != 0): #while there is a pump still on
        for x in range (8):                     #go through each pump and check the lapsed time vs recipe time / pour
            if (pumps_ON[x] == 1):
                if (time.time()*1000 >= (time_epoch + (recipe[x] * PUMP_POUR_RATE * DRINK_SIZE_FACTOR))): #If enough time has passed for a pump pour, turn OFF that pump
                    drive_pump (x+1, 'OFF')     #Turn off pump
                    pumps_ON[x] = 0             #also turn off its ON flag

    touchscreen_debounce = time.time()  #start the debounce timer again - snap shot the current time

    drink_pour_label.clear() #clear the drink bottom banner
    drink_pour_text.clear()
    main_drinks_list.enable() #re-enable drink selection

# Core pump control function
# Valid pump_action values are: FORWARD, REVERSE, OFF. Any other value turns pump OFF
# pump_Num is from 1-8
# LOW output turns ON the relay (active low)
def drive_pump(pump_num, pump_action):
    if pump_action == 'OFF': #turn pump off
        relay[(pump_num * 2) - 2].on() # find the I/O pins from pin index array and control the two relays
        relay[(pump_num * 2) - 1].on()
        #print(str((pump_num * 2) - 2) + ' ON  ', end = '')
        #print(str((pump_num * 2) - 1) + ' ON')
    elif pump_action == 'FORWARD': #Pump in forward mode
        relay[(pump_num * 2) - 2].off()
        relay[(pump_num * 2) - 1].on()
        #print(str((pump_num * 2) - 2) + ' OFF  ', end = '')
        #print(str((pump_num * 2) - 1) + ' ON')
    elif pump_action == 'REVERSE': #Pump in reverse mode
        relay[(pump_num * 2) - 2].on()
        relay[(pump_num * 2) - 1].off()
        #print(str((pump_num * 2) - 2) + ' ON  ', end = '')
        #print(str((pump_num * 2) - 1) + ' OFF')
    else: #turn pump off by default
        relay[(pump_num * 2) - 2].on()
        relay[(pump_num * 2) - 1].on()
        #print(str((pump_num * 2) - 2) + ' ON  ', end = '')
        #print(str((pump_num * 2) - 1) + ' ON')

def all_pumps_forward():
    all_pumps_off()
    sleep(0.05)
    drive_pump(1, "FORWARD")
    drive_pump(2, "FORWARD")
    drive_pump(3, "FORWARD")
    drive_pump(4, "FORWARD")
    drive_pump(5, "FORWARD")
    drive_pump(6, "FORWARD")
    drive_pump(7, "FORWARD")
    drive_pump(8, "FORWARD")

def all_pumps_reverse():
    all_pumps_off()
    sleep(0.05)
    drive_pump(1, "REVERSE")
    drive_pump(2, "REVERSE")
    drive_pump(3, "REVERSE")
    drive_pump(4, "REVERSE")
    drive_pump(5, "REVERSE")
    drive_pump(6, "REVERSE")
    drive_pump(7, "REVERSE")
    drive_pump(8, "REVERSE")

def all_pumps_off():
    drive_pump(1, "OFF")
    drive_pump(2, "OFF")
    drive_pump(3, "OFF")
    drive_pump(4, "OFF")
    drive_pump(5, "OFF")
    drive_pump(6, "OFF")
    drive_pump(7, "OFF")
    drive_pump(8, "OFF")


####################################################################
####################################################################
# Main app, and initial layout, which will contain the other windows
####################################################################
####################################################################

app = App(title="iDrink", bg="white", height="600", width="1024")
app.hide()  #Don't need to see it since all the panels/screens are in windows

###################
#Main Screen Layout
###################
window_main_menu_panel = Window(app, title="iDrink Main Menu", bg="white", height="600", width="1024")
window_main_menu_panel.set_full_screen()
window_main_menu_panel.bg="#99d6ff" #blue

# set screen left and right margins
menu_left_margin_box = Box(window_main_menu_panel, layout="auto", width=45, height="fill", align="left")
menu_right_margin_box = Box(window_main_menu_panel, layout="auto", width=45, height="fill", align="right")

message = Text(window_main_menu_panel, text="", size=10)  # vertical spacing
message = Text(window_main_menu_panel, text="iDrink - Please Tap to Pour!", size=35)
message = Text(window_main_menu_panel, text="", size=10)  # vertical spacing

main_buttons_box = Box(window_main_menu_panel, layout="auto", width="fill", align="bottom")
main_drinks_list = ListBox(window_main_menu_panel, command=thread_function, width="fill", height="fill", scrollbar=True, align="top")
main_drinks_list.bg="white"

message = Text(main_buttons_box, text="", size=10)  # vertical spacing
button_menu = PushButton(main_buttons_box, command=enter_menu_panel, align="left", width="10", height="2", text="Menus")
button_control = PushButton(main_buttons_box, command=enter_control_panel, align="left", width="10",height="2", text="Control")
drink_pour_label = Text(main_buttons_box, text="", size="25", align="left")
drink_pour_text = Text(main_buttons_box, text="", size="25", align="left", color="red")

button_menu.bg="#cccccc" #grey
button_control.bg="#cccccc" #grey

update_main_panel()

############################
#Menu Selection Panel layout
############################
window_menu_select_panel = Window(app, title="iDrink Menu selection screen", bg="white", height="600", width="1024")
window_menu_select_panel.set_full_screen()
window_menu_select_panel.bg = "#b3ffb3" #green
window_menu_select_panel.hide()

# set screen left and right margins
menu_left_margin_box = Box(window_menu_select_panel, layout="auto", width=45, height="fill", align="left")
menu_right_margin_box = Box(window_menu_select_panel, layout="auto", width=45, height="fill", align="right")

message = Text(window_menu_select_panel, text="", size=10)  # vertical spacing
message = Text(window_menu_select_panel, text="iDrink Bar Menus", size=35)
message = Text(window_menu_select_panel, text="", size=10)  # vertical spacing

menu_name_box = Box(window_menu_select_panel, layout="auto", width="fill", align="top")
menu_name_box.bg="#bfbfbf" #grey
menu_bottles_box = Box(window_menu_select_panel, layout="grid", width="fill", align="top")
menu_bottles_box.bg="#bfbfbf" #grey
menu_drinks_box = Box(window_menu_select_panel, layout="auto", width="fill", align="top")
menu_drinks_box.bg="white"

# print Menu name
message_menu1 = TextBox(menu_name_box, text=menu_json['Menu'][menu_index]['MenuName'], width="fill", align="top")
#print the Bottles used in this Menu
message_menu2 = Text(menu_bottles_box, text="Bottles: ", width="fill", grid=[0, 0])
message_menu3 = TextBox(menu_bottles_box, text=menu_json['Menu'][menu_index]['Bottles'], width="fill", multiline=True, grid=[1, 0])
menu_menu_drink_list = TextBox(menu_drinks_box, text="Drinks:", width="fill", height="8", multiline=True, scrollbar=True, align="top")

message_menu1.font = "helvetica"
message_menu2.font = "helvetica"
message_menu3.font = "helvetica"
message_menu1.text_size = "30"
message_menu2.text_size = "25"
message_menu3.text_size = "15"

menu_buttons_box = Box(window_menu_select_panel, layout="auto", width="fill", align="bottom")
button_prev_menu = PushButton(menu_buttons_box, command=prev_menu, align="left", width="15", height="2", text="Prev")
button_next_menu = PushButton(menu_buttons_box, command=next_menu, align="left", width="15",height="2", text="Next")
button_select = PushButton(menu_buttons_box, command=select_menu, align="left", width="15", height="2", text="Select")
button_cancel = PushButton(menu_buttons_box, command=enter_main_panel, align="left", width="15", height="2", text="Cancel")
button_prev_menu.bg="#cccccc" #grey
button_next_menu.bg="#cccccc" #grey
button_select.bg="#cccccc" #grey
button_cancel.bg="#cccccc" #grey

update_menu_panel()

#############################
# Control Panel screen layout
#############################
window_control_panel = Window(app, title="iDrink Control Panel", bg="white", height="600", width="1024")
window_control_panel.set_full_screen()
window_control_panel.hide()

message = Text(window_control_panel, text="", size=10) # vertical spacing
message = Text(window_control_panel, text="iDrink Control Panel", size=30)
message = Text(window_control_panel, text="", size=10) #vertical spacing

# set screen left and right margins
control_left_margin_box = Box(window_control_panel, layout="auto", width=45, height="fill", align="left")
control_right_margin_box = Box(window_control_panel, layout="auto", width=45, height="fill", align="right")

Pump_Label_box = Box(window_control_panel, layout="auto", width="fill", align="top")
message = Text(Pump_Label_box, text="1", size=22, align="left", width="7")
message = Text(Pump_Label_box, text="2", size=22, align="left", width="7")
message = Text(Pump_Label_box, text="3", size=22, align="left", width="7")
message = Text(Pump_Label_box, text="4", size=22, align="left", width="7")
message = Text(Pump_Label_box, text="5", size=22, align="left", width="7")
message = Text(Pump_Label_box, text="6", size=22, align="left", width="7")
message = Text(Pump_Label_box, text="7", size=22, align="left", width="7")
message = Text(Pump_Label_box, text="8", size=22, align="left", width="7")

# Pump forward buttons
#message = Text(left_margin_box, text="F", size=30)
Pump_Forward_buttons_box = Box(window_control_panel, layout="auto", width="fill", align="top")
button_Pump_Forward_1 = PushButton(Pump_Forward_buttons_box, command=drive_pump, args=[1,"FORWARD"], width=7, height=1, align="left", text="F")
button_Pump_Forward_2 = PushButton(Pump_Forward_buttons_box, command=drive_pump, args=[2,"FORWARD"], width=7, height=1, align="left", text="F")
button_Pump_Forward_3 = PushButton(Pump_Forward_buttons_box, command=drive_pump, args=[3,"FORWARD"], width=7, height=1, align="left", text="F")
button_Pump_Forward_4 = PushButton(Pump_Forward_buttons_box, command=drive_pump, args=[4,"FORWARD"], width=7, height=1, align="left", text="F")
button_Pump_Forward_5 = PushButton(Pump_Forward_buttons_box, command=drive_pump, args=[5,"FORWARD"], width=7, height=1, align="left", text="F")
button_Pump_Forward_6 = PushButton(Pump_Forward_buttons_box, command=drive_pump, args=[6,"FORWARD"], width=7, height=1, align="left", text="F")
button_Pump_Forward_7 = PushButton(Pump_Forward_buttons_box, command=drive_pump, args=[7,"FORWARD"], width=7, height=1, align="left", text="F")
button_Pump_Forward_8 = PushButton(Pump_Forward_buttons_box, command=drive_pump, args=[8,"FORWARD"], width=7, height=1, align="left", text="F")
button_Pump_Forward_1.text_color="white"
button_Pump_Forward_2.text_color="white"
button_Pump_Forward_3.text_color="white"
button_Pump_Forward_4.text_color="white"
button_Pump_Forward_5.text_color="white"
button_Pump_Forward_6.text_color="white"
button_Pump_Forward_7.text_color="white"
button_Pump_Forward_8.text_color="white"
# Note: button.bg property does not work on the MacOS
button_Pump_Forward_1.bg="#009900" #green
button_Pump_Forward_2.bg="#009900"
button_Pump_Forward_3.bg="#009900"
button_Pump_Forward_4.bg="#009900"
button_Pump_Forward_5.bg="#009900"
button_Pump_Forward_6.bg="#009900"
button_Pump_Forward_7.bg="#009900"
button_Pump_Forward_8.bg="#009900"
button_Pump_Forward_1.text_size="16"
button_Pump_Forward_2.text_size="16"
button_Pump_Forward_3.text_size="16"
button_Pump_Forward_4.text_size="16"
button_Pump_Forward_5.text_size="16"
button_Pump_Forward_6.text_size="16"
button_Pump_Forward_7.text_size="16"
button_Pump_Forward_8.text_size="16"

# Pump reverse buttons
#message = Text(left_margin_box, text="R", size=30)
Pump_Reverse_buttons_box = Box(window_control_panel, layout="auto", width="fill", align="top")
button_Pump_Reverse_1 = PushButton(Pump_Reverse_buttons_box, command=drive_pump, args=[1,"REVERSE"], width=7, height=1, align="left", text="R")
button_Pump_Reverse_2 = PushButton(Pump_Reverse_buttons_box, command=drive_pump, args=[2,"REVERSE"], width=7, height=1, align="left", text="R")
button_Pump_Reverse_3 = PushButton(Pump_Reverse_buttons_box, command=drive_pump, args=[3,"REVERSE"], width=7, height=1, align="left", text="R")
button_Pump_Reverse_4 = PushButton(Pump_Reverse_buttons_box, command=drive_pump, args=[4,"REVERSE"], width=7, height=1, align="left", text="R")
button_Pump_Reverse_5 = PushButton(Pump_Reverse_buttons_box, command=drive_pump, args=[5,"REVERSE"], width=7, height=1, align="left", text="R")
button_Pump_Reverse_6 = PushButton(Pump_Reverse_buttons_box, command=drive_pump, args=[6,"REVERSE"], width=7, height=1, align="left", text="R")
button_Pump_Reverse_7 = PushButton(Pump_Reverse_buttons_box, command=drive_pump, args=[7,"REVERSE"], width=7, height=1, align="left", text="R")
button_Pump_Reverse_8 = PushButton(Pump_Reverse_buttons_box, command=drive_pump, args=[8,"REVERSE"], width=7, height=1, align="left", text="R")
button_Pump_Reverse_1.text_color="white"
button_Pump_Reverse_2.text_color="white"
button_Pump_Reverse_3.text_color="white"
button_Pump_Reverse_4.text_color="white"
button_Pump_Reverse_5.text_color="white"
button_Pump_Reverse_6.text_color="white"
button_Pump_Reverse_7.text_color="white"
button_Pump_Reverse_8.text_color="white"
# Note, button.bg property does not work on the MacOS
button_Pump_Reverse_1.bg="#0099ff" #blue
button_Pump_Reverse_2.bg="#0099ff"
button_Pump_Reverse_3.bg="#0099ff"
button_Pump_Reverse_4.bg="#0099ff"
button_Pump_Reverse_5.bg="#0099ff"
button_Pump_Reverse_6.bg="#0099ff"
button_Pump_Reverse_7.bg="#0099ff"
button_Pump_Reverse_8.bg="#0099ff"
button_Pump_Reverse_1.text_size="16"
button_Pump_Reverse_2.text_size="16"
button_Pump_Reverse_3.text_size="16"
button_Pump_Reverse_4.text_size="16"
button_Pump_Reverse_5.text_size="16"
button_Pump_Reverse_6.text_size="16"
button_Pump_Reverse_7.text_size="16"
button_Pump_Reverse_8.text_size="16"

# Pump Off buttons
pump_off_buttons_box = Box(window_control_panel, layout="auto", width="fill", align="top")
button_Pump_Off_1 = PushButton(pump_off_buttons_box, command=drive_pump, args=[1,"OFF"], width=7, height=1, align="left", text="OFF")
button_Pump_Off_2 = PushButton(pump_off_buttons_box, command=drive_pump, args=[2,"OFF"], width=7, height=1, align="left", text="OFF")
button_Pump_Off_3 = PushButton(pump_off_buttons_box, command=drive_pump, args=[3,"OFF"], width=7, height=1, align="left", text="OFF")
button_Pump_Off_4 = PushButton(pump_off_buttons_box, command=drive_pump, args=[4,"OFF"], width=7, height=1, align="left", text="OFF")
button_Pump_Off_5 = PushButton(pump_off_buttons_box, command=drive_pump, args=[5,"OFF"], width=7, height=1, align="left", text="OFF")
button_Pump_Off_6 = PushButton(pump_off_buttons_box, command=drive_pump, args=[6,"OFF"], width=7, height=1, align="left", text="OFF")
button_Pump_Off_7 = PushButton(pump_off_buttons_box, command=drive_pump, args=[7,"OFF"], width=7, height=1, align="left", text="OFF")
button_Pump_Off_8 = PushButton(pump_off_buttons_box, command=drive_pump, args=[8,"OFF"], width=7, height=1, align="left", text="OFF")
button_Pump_Off_1.text_color="white"
button_Pump_Off_2.text_color="white"
button_Pump_Off_3.text_color="white"
button_Pump_Off_4.text_color="white"
button_Pump_Off_5.text_color="white"
button_Pump_Off_6.text_color="white"
button_Pump_Off_7.text_color="white"
button_Pump_Off_8.text_color="white"
# Note: button.bg property does not work on the MacOS
button_Pump_Off_1.bg="red"
button_Pump_Off_2.bg="red"
button_Pump_Off_3.bg="red"
button_Pump_Off_4.bg="red"
button_Pump_Off_5.bg="red"
button_Pump_Off_6.bg="red"
button_Pump_Off_7.bg="red"
button_Pump_Off_8.bg="red"
button_Pump_Off_1.text_size="16"
button_Pump_Off_2.text_size="16"
button_Pump_Off_3.text_size="16"
button_Pump_Off_4.text_size="16"
button_Pump_Off_5.text_size="16"
button_Pump_Off_6.text_size="16"
button_Pump_Off_7.text_size="16"
button_Pump_Off_8.text_size="16"

message = Text(app, text="", size=15) #vertical spacing

pump_all_margin_left_box = Box(window_control_panel, layout="auto", width="200", align="left")
pump_all_margin_right_box = Box(window_control_panel, layout="auto", width="200", align="right")
pump_all_buttons_box = Box(window_control_panel, layout="auto", width="fill", align="top")

button_all_forward = PushButton(pump_all_buttons_box, command=all_pumps_forward, align="top", width="fill", height="2", text="ALL FORWARD")
button_all_reverse = PushButton(pump_all_buttons_box, command=all_pumps_reverse, align="top", width="fill", height="2", text="ALL REVERSE")
button_all_off = PushButton(pump_all_buttons_box, command=all_pumps_off, align="top", width="fill", height="2", text="ALL OFF")
button_exit = PushButton(pump_all_buttons_box, command=enter_main_panel, align="top", width="fill", height="2", text="EXIT")

button_all_forward.text_color="white"
button_all_reverse.text_color="white"
button_all_off.text_color="white"
button_all_forward.text_size="14"
button_all_reverse.text_size="14"
button_all_off.text_size="14"
button_exit.text_size="14"
button_all_forward.bg="#009900" #green
button_all_reverse.bg="#0099ff" #blue
button_all_off.bg="red"
button_exit.bg="#808080" #grey

app.display()