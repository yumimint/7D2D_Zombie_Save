#! /bin/bash
pyinstaller --onefile --noconsole \
--icon=7D2D\ Zombie\ Save.ico \
--add-data "7D2D Zombie Save i18n.json;." \
--add-data "7D2D Zombie Save.ico;." \
7D2D\ Zombie\ Save.pyw
