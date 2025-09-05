pip install pyinstaller
pyinstaller --onefile --add-data "templates;templates" --add-data "static;static" --add-data "config.ini;." app.py