# iDrink-RPi
Electronic bartender-ported from the Arduino project
Dedicate touchscreen
Menu collection JSON file
Better, Stronger...Faster!

TO AUTORUN on Raspberry Pi (and have access to your display, since a cron job (via crontab) will be in a non-interactive shell. There's no display for it to use):

Edit /home/pi/.config/lxsession/LXDE-pi/autostart and add the following line at the end:

@sh /home/pi/iDrink/launcher.sh (where folder "iDrink" contains the iDrink-RPi script, Menu.json and the launcher script)

Note: Raspbian is based on the LXDE desktop environment. As a result, the location of the autostart script might be different depending on your particular Linux computer and distribution version.
After your desktop environment starts (LXDE-pi, in this case), it runs whatever commands it finds in the profile's autostart script, which is located at /home/pi/.config/lxsession/LXDE-pi/autostart for our Raspberry Pi. Note that the directory pi might be different if you created a new user for your Raspberry Pi. If no user autostart script is found, Linux will run the global /etc/xdg/lxsession/LXDE-pi/autostart script instead. In the latter's case use sudo to edit since the file is outside of the home/pi/ environment.

Feature ideas:
1) Tweak drink - select a drink on themain page and allow the user to adjust ingredient amounts via sliders
2) Bottle level sensors
3) Light up the pumps that are on
4) Edit the Menu file via the touchscreen
5) Mix drinks while pouring by rapidly switching between the pumps
