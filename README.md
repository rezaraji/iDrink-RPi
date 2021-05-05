# iDrink-RPi
Electronic bartender-ported from the Arduino project
Dedicate touchscreen
Menu collection JSON file
Better, Stronger...Faster!

TO AUTORUN on Raspberry Pi (and have access to your display, since a cron job (via crontab) will be in a non-interactive shell. There's no display for it to use):

Edit /home/pi/.config/lxsession/LXDE-pi/autostart and add the following line at the end:

@sh /home/pi/iDrink/launcher.sh (where folder "iDrink" contains the iDrink-RPi script, Menu.json and the launcher script)

Fearure ideas:
1) Tweak drink - select a drink on themain page and allow the user to adjust ingredient amounts via sliders
2) Bottle level sensors
3) Light up the pumps that are on
4) Edit the Menu file via the touchscreen
5) Mix drinks while pouring by rapidly switching between the pumps
