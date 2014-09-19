TEMPLATE = app
FORMS += ../ui/gui-main.ui
SOURCES += gui.py
SOURCES += main.py
unix {

}QT += network \
 xml \
 gui \
 script \
 sql \
 core \
 webkit \
 svg \
 xmlpatterns
HEADERS += ../PyIPC/ipcmod.h
