#!/usr/bin/env python3

VERSION = "0.3.0 alpha"
ENAME = "Prism"
ESITE = "https://github.com/frank038/Prism"

import sys,os
import gi
gi.require_version("Gtk","4.0")
gi.require_version("Adw","1")
from gi.repository import Gtk,Gdk,GLib,Gio,Adw,GObject
import json
import pycurl
import certifi
import locale
import urllib.parse

_app = None
self_main = None
_curr_dir = os.getcwd()
_HOME = os.path.expanduser("~")
icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())

_CSS="""
viewport list row:hover {
background: @card_bg_color;
color: @card_fg_color;
}
"""


# the directory settings and options
if not os.access(_curr_dir, os.W_OK):
    HOME_CONFIG = os.path.join(_HOME,".config","PrimsDM4")
    try:
        if not os.path.exists(HOME_CONFIG):
            os.mkdir(HOME_CONFIG, mode=0o770)
    except:
        HOME_CONFIG = _curr_dir
    if HOME_CONFIG != _curr_dir:
        try:
            shutil.copytree("/usr/share/PrimsDM4/configs", os.path.join(HOME_CONFIG, "configs"))
            shutil.copytree("/usr/share/PrimsDM4/icons", os.path.join(HOME_CONFIG, "icons"))
            shutil.copytree("/usr/share/PrimsDM4/langs", os.path.join(HOME_CONFIG, "langs"))
        except Exception as E:
            HOME_CONFIG = _curr_dir
else:
    HOME_CONFIG = _curr_dir

sys.path.append(os.path.join(HOME_CONFIG, "langs"))
_lang = __import__("en")

config_file = os.path.join(HOME_CONFIG, "configs/config.json")
config_conf_start = { 
"wwidth": 1200, 
"wheight": 800,
"notification": 1
}
if not os.path.exists(config_file):
    try:
        _data_json = config_conf_start
        _ff =  open(config_file, "w")
        json.dump(_data_json, _ff, indent = 4)
        _ff.close()
        config_conf = config_conf_start
    except:
        sys.exit()
else:
    try:
        _ff = open(config_file, "r")
        config_conf = json.load(_ff)
        _ff.close()
    except:
        sys.exit()

######### CONFIGURATION
WWIDTH = config_conf["wwidth"] # this program width
WHEIGHT = config_conf["wheight"] # this program height
USENOTIF = config_conf["notification"] # can send notifications
#########

dest_dir_tmp = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
dest_dir = os.path.join(dest_dir_tmp, "PrimsDM4")
if not os.path.exists(dest_dir):
    try:
        os.mkdir(dest_dir, mode=0o770)
    except:
        dest_dir = _HOME

# where to store the downloading
# file_url - file path - download_speed ; newline separated
DOWNLOADS_LIST = os.path.join(HOME_CONFIG, "configs", "downloads")

MENU_XML="""
<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <menu id="app-menu">
    <section>
      <item>
        <attribute name="action">win.newdownload</attribute>
        <attribute name="label" translatable="yes">{}</attribute>
      </item>
      <item>
        <attribute name="action">win.about</attribute>
        <attribute name="label" translatable="yes">{}</attribute>
      </item>
      <item>
        <attribute name="action">win.quit</attribute>
        <attribute name="label" translatable="yes">{}</attribute>
        <attribute name="accel">&lt;Primary&gt;Q</attribute>
    </item>
    </section>
  </menu>
</interface>
""".format(_lang.NEWDOWNLOAD, _lang.ABOUT, _lang.QUIT)


# convert the size into readable string
locale.setlocale(locale.LC_ALL, '')
DECIMAL_SEP = locale.localeconv()["decimal_point"]
def convert_size(fsize2):
    if fsize2 == 0 or fsize2 == 1:
        sfsize = str(fsize2)+" byte"
    elif fsize2//1024 == 0:
        sfsize = str(fsize2)+" bytes"
    elif fsize2//1048576 == 0:
        sfsize = str(round(fsize2/1024, 3))+" KB"
    elif fsize2//1073741824 == 0:
        sfsize = str(round(fsize2/1048576, 3))+" MB"
    elif fsize2//1099511627776 == 0:
        sfsize = str(round(fsize2/1073741824, 3))+" GiB"
    else:
        sfsize = str(round(fsize2/1099511627776, 3))+" GiB"
    return sfsize.replace(".", DECIMAL_SEP or ".")


class AlDial(Adw.AlertDialog):
    def __init__(self, _parent, _str1):
        super().__init__()
        self._parent = _parent
        # self.set_heading("")
        self.set_body(_str1)
        #
        self.add_response("close", _lang.CLOSE)
        self.connect("response", self.on_close)
        #
        self.present(self._parent)
    
    def on_close(self, _d, _r):
        self.close()
    
def on_send_notification(_title, _file):
    _not = Gio.Notification.new(_title)
    _not.set_body(_file)
    _not.set_icon(Gio.ThemedIcon.new_from_names(["download","notifications","empty"]))
    _not.set_priority(Gio.NotificationPriority.NORMAL)
    # _not.set_default_action_and_target("Activate", _app.props.active_window.present())
    # _not.set_default_action_and_target("Activate", GLib.Variant.new_int16(123))
    return _not

class SignalObject(GObject.Object):
    
    def __init__(self):
        GObject.Object.__init__(self)
        self._name = ""
        self.value = -999
        self._list = []
    
    @GObject.Property(type=str)
    def propName(self):
        'Read-write integer property.'
        return self._name

    @propName.setter
    def propName(self, name):
        self._name = name
    
    @GObject.Property(type=int)
    def propInt(self):
        'Read-write integer property.'
        return self.value

    @propInt.setter
    def propInt(self, value):
        self.value = value
    
    @GObject.Property(type=object)
    def propList(self):
        'Read-write integer property.'
        return self._list

    @propList.setter
    def propList(self, data):
        self._list = [data]
    

# yes/no dialog - delete items
class YNDial(Adw.AlertDialog):
    def __init__(self, _parent, _str1, _str2, _data):
        super().__init__()
        self._parent = _parent
        self.set_heading(_str1)
        self.set_body(_str2)
        #
        self.add_response("no", _lang.NO)
        self.add_response("yes", _lang.YES)
        self.choose(self._parent, None, self._parent.dialog_action, _data)
    
    
class MainWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_default_size(WWIDTH, WHEIGHT)
        self.app_ = self.get_application()
        self.set_title(ENAME)
        global self_main
        self_main = self
        self.connect("close-request", self.on_this_close)
        try:
            self.connect("force-close", self.on_this_close)
        except:
            pass
        self.connect("destroy", self.on_this_close)
        self.connect("show", self.on_show)
        # list of the saved urls: [[url,path,speed]]
        self._list = None
        #
        self.mainvbox = Gtk.Box.new( Gtk.Orientation.VERTICAL,6)
        self.set_content(self.mainvbox)
        #
        self.headerbar = Adw.HeaderBar.new() 
        self.mainvbox.append(self.headerbar)
        #
        _sw = Gtk.ScrolledWindow.new()
        _sw.set_hexpand(True)
        _sw.set_vexpand(True)
        _sw.propagate_natural_height = 1
        _sw.propagate_natural_width = 1
        self.swbox = Gtk.Box.new( Gtk.Orientation.VERTICAL,0)
        _sw.set_child(self.swbox)
        self.mainvbox.append(_sw)
        #
        quit_action = Gio.SimpleAction.new("quit", None) 
        quit_action.connect("activate", self.on_quit_action_actived)
        self.add_action(quit_action)
        #
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about_action_actived)
        self.add_action(about_action)
        #
        new_action = Gio.SimpleAction.new("newdownload", None)
        new_action.connect("activate", self.on_new_action_added)
        self.add_action(new_action)
        #
        self.menu_button = Gtk.MenuButton.new()
        self.headerbar.pack_end(self.menu_button)
        menu = Gtk.Builder.new_from_string(MENU_XML, -1).get_object("app-menu")
        self.menu_button.set_icon_name("open-menu-symbolic")
        self.menu_button.set_menu_model(menu)
        #
        clamp = Adw.Clamp.new()
        self.swbox.append(clamp)
        #
        self.listbox = Gtk.ListBox.new()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listbox.set_css_classes(["boxed-list"])
        clamp.set_child(self.listbox)
        self.listbox.set_name("viewp")
        #
        self.css_provider = Gtk.CssProvider()
        self.css_provider.load_from_string(_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        #
        self.items_count = 0 # the number of downloads
    
    # 3a. add the entry and execute the download
    # file_path is not None if there is a previous interrupted download
    def add_new_download(self, _URI, _redir, _speed, file_path=None):
        # create the new entry
        # wdg = self.create_entry(_URI, _redir, _speed, file_path)
        self.items_count += 1
        wdg = createEntry(self, _URI, _redir, _speed, file_path, self.items_count)
        self.listbox.append(wdg)
    
    # check if there is an interrupted download - if any add an entry in the list
    def on_show(self, _w):
        try:
            with open(DOWNLOADS_LIST, "r") as _f:
                # populate the list
                self._list = _f.readlines()
            for i in range(0,len(self._list),3):
                file_uri = self._list[i].strip("\n")
                file_path = self._list[i+1].strip("\n")
                _speed = int(self._list[i+2].strip("\n"))
                if file_uri == "\n" or file_path == "\n" or _speed == "\n":
                    continue
                self.add_new_download(file_uri, 5, _speed, file_path)
        except Exception as E:
            pass
    
    # 2. manage the added uri - callback of 1. only
    def on_add_download(self, _w, _buffer, _dlg, _redir, _speed):
        _dlg.close()
        _URI = _buffer.get_text()
        if _URI == "":
            return
        _URI = str(urllib.parse.unquote(_URI, encoding='utf-8'))
        # check the list when trying to add a new download - skip if exists
        file_path = None
        for i in range(0,len(self._list),3):
            file_uri = self._list[i].strip("\n")
            file_path = self._list[i+1].strip("\n")
            # _speed = int(self._list[i+2].strip("\n"))
            if file_uri == _URI:# and file_path == os.path.join(dest_dir, os.path.basename(_URI)):
                AlDial(self_main, _lang.FALREADYDOWNLOAD)
                return
        # 
        # self.get_file_data([_URI, 5, _speed, self._signalm, None])
        self.add_new_download(_URI, _redir, _speed, file_path)
        
    # 1. dialog for getting the url
    def on_new_action_added(self, action, param=None):
        new_dlg = Adw.Dialog.new()
        new_dlg.set_size_request(500,10)
        new_dlg.set_can_close(True)
        dlg_box = Gtk.Box.new(Gtk.Orientation.VERTICAL,4)
        dlg_box.set_margin_bottom(4)
        dlg_box.set_margin_end(4)
        dlg_box.set_margin_start(4)
        dlg_box.set_margin_top(4)
        new_dlg.set_child(dlg_box)
        #
        _buffer = Gtk.EntryBuffer.new("", -1)
        _entry = Gtk.Entry.new_with_buffer(_buffer)
        dlg_box.append(_entry)
        #
        opt_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL,4)
        dlg_box.append(opt_box)
        #
        spn_lbl = Gtk.Label(label=_lang.REDIRECTION)
        # opt_box.append(spn_lbl)
        spn_btn = Gtk.SpinButton.new_with_range(1,20,1)
        spn_btn.set_numeric(True)
        # opt_box.append(spn_btn)
        #
        spn_lbl2 = Gtk.Label(label=_lang.SPEEDDOWNLOAD)
        opt_box.append(spn_lbl2)
        spn_btn2 = Gtk.SpinButton.new_with_range(0,20000000,100000)
        spn_btn2.set_tooltip_text(_lang.SPEEDDOWNLOAD2)
        spn_btn2.set_numeric(True)
        opt_box.append(spn_btn2)
        #
        btn_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL,4)
        btn_box.set_margin_end(4)
        btn_box.set_margin_start(4)
        btn_box.set_margin_bottom(4)
        dlg_box.append(btn_box)
        #
        close_btn = Gtk.Button(label=_lang.CLOSE)
        btn_box.append(close_btn)
        # close the dialog
        def dlg_close(_w):
            new_dlg.close()
        close_btn.connect("clicked", dlg_close)
        #
        _b = Gtk.Box.new(Gtk.Orientation.HORIZONTAL,0)
        _b.set_hexpand(True)
        btn_box.append(_b)
        #
        add_btn = Gtk.Button(label=_lang.ADD)
        btn_box.append(add_btn)
        #
        def dlg_add(_w):
            self.on_add_download(_w, _buffer, new_dlg, int(spn_btn.get_value()), int(spn_btn2.get_value()))
        add_btn.connect("clicked", dlg_add)
        add_btn.set_css_classes(["suggested-action",""])
        #
        _entry.connect("activate", self.on_add_download, _buffer, new_dlg, spn_btn.get_digits(), int(spn_btn2.get_value()))
        #
        new_dlg.present(self)
    
    def on_quit_action_actived(self, action, param=None):
        self.app_.quit()
    
    def on_this_close(self, _w):
        global WWIDTH
        global WHEIGHT
        _WWIDTH = self.get_width()
        _WHEIGHT = self.get_height()
        if _WWIDTH != WWIDTH or _WHEIGHT != WHEIGHT:
            WWIDTH = _WWIDTH
            config_conf["wwidth"] = WWIDTH
            WHEIGHT = _WHEIGHT
            config_conf["wheight"] = WHEIGHT
            try:
                _ff =  open(os.path.join(HOME_CONFIG,"configs/config.json"), "w")
                json.dump(config_conf, _ff, indent = 4)
                _ff.close()
            except:
                pass
        self.on_quit_action_actived(None)
        return True
    
    def on_about_action_actived(self, action, param=None):
        _aboutdial = Adw.AboutDialog.new()
        _aboutdial.set_presentation_mode(Adw.DialogPresentationMode.FLOATING)#.BOTTOM_SHEET)#.FLOATING)
        _aboutdial.set_application_icon("com.Prism.download.manager")
        _aboutdial.set_developers(["Philip J. Fry"])
        _aboutdial.set_comments("Made for me 🙂")
        _aboutdial.set_version(VERSION)
        _aboutdial.set_website(ESITE)
        _aboutdial.set_license_type(Gtk.License.GPL_3_0_ONLY)
        _aboutdial.present(self)


class createEntry(Gtk.Box):
    def __init__(self, main_app, _URL, _redir, _speed, file_path, _count):
        super().__init__()
        self.main_app = main_app
        self._URL = _URL # urllib.parse.unquote(_URL, encoding='utf-8')
        self._redir = _redir
        self._speed = _speed # the download speed
        self.file_path = file_path # where to save the file to download
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(0)
        #
        self.t_count = 0
        self.t_cancel = 0
        self._count = _count # this name as number
        self._realname = None
        self._realsize = 0
        ########
        self._signalm = SignalObject()
        self._signalm.connect("notify::propName", self.get_real_filename)
        self._signalm.connect("notify::propInt", self.get_real_filesize)
        self._signalm.connect("notify::propList", self.on_get_data_last)
        self.get_file_data([self._URL, 5, self._speed, self._signalm, None])
        ########
        # self.create_entry(self._URL, self._redir, self._speed, self.file_path)
    
    # 2a. get the real file name and size before executing everything else
    # see self.on_get_data_last
    # _d : [_URI, _redir, _speed, _signal, file_path or None]
    def get_file_data(self, _data):
        # # [_buffer.get_text(), 5, 2048, self._signalm, file_path or None]
        _thread = GLib.Thread.new(None, self.set_curl2, _data)
    
    def get_real_filename(self, _signal,_param):
        self._realname = _signal.propName
        if self._realname[-1] == '"':
            self._realname = self._realname[:-1]
            if self._realname[0] == '"':
                self._realname = self._realname[1:]
        
    def get_real_filesize(self, _signal,_param):
        self._realsize = _signal.propInt
    
    # the initial searching of data is finished
    def on_get_data_last(self, _signal,_param):
        # ["END", [url, redirect, speed, file_path]]
        _list = _signal.propList[0]
        # for new downloads
        _URI_tmp = _list[1][0]
        _URI = urllib.parse.unquote(_URI_tmp, encoding='utf-8')
        _redir = _list[1][1]
        _speed = _list[1][2]
        file_path = _list[1][3]
        try:
            if self._realname != None:# or self._realname != "":
                n_file_path = os.path.join(dest_dir, self._realname)
            else:
                n_file_path = os.path.join(dest_dir, os.path.basename(_URI))
            if _URI+"\n" not in self.main_app._list:
                with open(DOWNLOADS_LIST, "a") as _f:
                    _f.write(_URI+"\n"+n_file_path+"\n"+"{}\n".format(_speed))
                self.main_app._list.append(_URI+"\n")
                self.main_app._list.append(n_file_path+"\n")
                self.main_app._list.append(str(_speed)+"\n")
            self.add_new_download(_URI, _redir, _speed, file_path)
        except Exception as E:
            pass
        #
        self.create_entry(self._URL, self._redir, self._speed, self.file_path)
        # set the label size for existing files
        if self.file_path != None and os.path.exists(self.file_path):
            _size = os.path.getsize(self.file_path) # the size already downloaded
            if _speed == -1:
                self._btn._lbl.set_label("{} {}".format(_lang.COMPLETED, convert_size(_size)))
            else:
                self._btn._lbl.set_label(convert_size(_size))
    
    # 4. stop/resume button
    def on_stopresume_button(self, _w):
        if _w._state == 1:
            _signal = _w._signal
            try:
                _signal.propList = ["COPY_ABORT",[_w._thread,self._count]]
            except Exception as E:
                _signal.propList = ["COPY_ABORT",[_w._thread,self._count]]
                pass
        elif _w._state == 0: # start the download
            _action = _w._row
            _URI = _w._uri
            _speed = _w._speed
            _redir = _w._redir
            _path = _w._path
            #
            def signal_threadslot(_signal,_param):
                _list = _signal.propList[0]
                if _list[0] in ["ERROR1","ERROR2"] and _list[1][1] == self._count:
                    _w.set_label(_lang.START)
                    _w._state = 0
                    _w._thread = None
                    if os.path.exists(_path):
                        _size = os.path.getsize(_path)
                        _w._lbl.set_label("{} {}".format(convert_size(_size), _lang.COPYERROR))
                    else:
                        _w._lbl.set_label(_lang.COPYERROR)
                    if on_send_notification:
                        _app.send_notification(None, on_send_notification(_lang.COPYERROR, os.path.basename(_URI)))
                elif _list[0] == "COPY" and _list[1][2] == self._count:
                    _size_all = _list[1][0]
                    _size_tmp = _list[1][1]
                    GLib.idle_add(self.set_copy_lbl, _w, _size_all, _size_tmp)
                elif _list[0] == "TERMINATED" and _list[1][1] == self._count:
                    _w.set_label(_lang.START)
                    _w._thread = None
                    _w._state = 0
                    _w.set_sensitive(False)
                    _size = _list[1][0]
                    _w._lbl.set_label(_lang.TERMINATED+" "+str(convert_size(_size)))
                    _w._completed = 1
                    GLib.idle_add(self.set_terminated_mark, _w)
                    if on_send_notification:
                        _app.send_notification(None, on_send_notification(_lang.TERMINATED, os.path.basename(_URI)))
                elif _list[0] == "COPY_ABORT" and _list[1][1] == self._count:
                    _w.set_label(_lang.START)
                    _w._thread = None
                    _w._state = 0
                    if os.path.exists(_path):
                        _size = os.path.getsize(_path)
                        _w._lbl.set_label("{} / {}".format(convert_size(_size), _lang.COPYABORTED))
                    else:
                        _w._lbl.set_label(_lang.COPYABORTED)
                    # if on_send_notification:
                        # _app.send_notification(None, on_send_notification(_lang.COPYABORTED, os.path.basename(_URI)))
            _signal = SignalObject()
            _signal.connect("notify::propList", signal_threadslot)
            _thread = GLib.Thread.new(None, self.set_curl, [_URI, _redir, _speed, _signal, _path, self._count])
            _w._thread = _thread
            _w.set_label(_lang.STOP)
            _w._state = 1
            _w._signal = _signal
        
    def set_copy_lbl(self, action_button, _tt, _t1):
        _d = action_button._downloaded
        _size_tmp = convert_size(_t1)
        _size_all = convert_size(_tt+_d)
        action_button._lbl.set_label("{} / {}".format(_size_tmp, _size_all))
    
    # set the mark of the completed file in the downloads file
    # (speed to -1 if terminated or to 0 if file is been deleted by the user)
    def set_terminated_mark(self, action_button, _type=1):
        _URI = action_button._uri
        _path = action_button._path
        try:
            _idx_found = -1
            for i in range(0,len(self.main_app._list[:]),3):
                if self.main_app._list[i].strip("\n") == _URI and self.main_app._list[i+1].strip("\n") == _path:
                    _idx_found = i+2
                    break
            # change the list
            if _idx_found != -1:
                if _type == 1:
                    self.main_app._list[_idx_found] = "-1\n"
                elif _type == 0:
                    self.main_app._list[_idx_found] = "0\n"
            # rebuild the file
            _f = open(DOWNLOADS_LIST, "w")
            for el in self.main_app._list:
                _f.write(el)
            _f.close()
        except:
            pass
    
    # 3a1
    def on_btn_remove(self, _w, _ba):
        YNDial(self, _lang.QREMOVE, os.path.basename(_ba._btn._path), ["remove", _ba])
    
    # 3a2
    def on_btn_delete(self, _w, _ba):
        YNDial(self, _lang.QDELETE, os.path.basename(_ba._btn._path), ["delete", _ba])
    
    # 3a3 - callback of on_btn_remove and on_btn_delete
    def dialog_action(self, _obj, _res, _data=None):
        _result = _obj.choose_finish(_res)
        if _result == "no":
            return
        #
        _action = _data[0]
        _ba = _data[1]
        action_button = _ba._btn
        if _action in ["remove", "delete"]:
            if action_button._state == 1:
                return
            # else:
        if _action == "remove":
            # remove from the list
            # _URL = _ba._url
            _file_path = os.path.join(dest_dir, os.path.basename(self._URL))
            for i in range(0,len(self.main_app._list[:]),3):
                file_uri = self.main_app._list[i].strip("\n")
                file_path = self.main_app._list[i+1].strip("\n")
                if file_uri == self._URL:
                    self.main_app._list.pop(i+2)
                    self.main_app._list.pop(i+1)
                    self.main_app._list.pop(i)
                    # remove from the file
                    _f = open(DOWNLOADS_LIST, "w")
                    for el in self.main_app._list:
                        _f.write(el)
                    _f.close()
                    break
            # remove the entry
            _fc = self.main_app.listbox.get_first_child()
            while _fc != None:
                if _fc.get_child() != _ba:
                    _fc = _fc.get_next_sibling()
                else:
                    self.main_app.listbox.remove(_fc)
                    break
        # remove only the file
        if _action == "delete":
            try:
                # os.unlink(os.path.join(dest_dir, os.path.basename(action_button._uri)))
                os.unlink(action_button._path)
                action_button.set_sensitive(True)
                action_button._completed = 0
                action_button._lbl.set_label("-/-")
                # change the file state
                self.set_terminated_mark(action_button, 0)
                #
                if not os.path.exists(os.path.join(dest_dir, os.path.basename(action_button._uri))):
                    AlDial(self_main, _lang.REMOVED)
            except Exception as E:
                AlDial(self_main, str(E))
                return
    
    
    # 3b. create the entry in the listbox
    def create_entry(self, _URI, _redir, _speed, file_path=None):
        real_path = ""
        if file_path != None:
            real_path = file_path
            _name = os.path.basename(real_path)
        else:
            if self._realname != None:
                _name = self._realname
                real_path = os.path.join(dest_dir, _name)
            else:
                _name = os.path.basename(_URI)
                real_path = os.path.join(dest_dir, _name)
        #
        self._path = real_path # the full file path in which the downloaded item will be written
        #
        real_size = 0
        if self._realsize > 0:
            real_size = self._realsize
            self._realsize = 0
        self._size = real_size # the claimed size
        #
        action_row = Adw.ExpanderRow.new()
        action_row.set_use_markup(False)
        action_row.set_activatable(False)
        action_row.set_selectable(False)
        action_row.set_name("actionrow1")
        self.append(action_row)
        action_row.set_title(_name) # the file name
        action_row.set_title_lines(3)
        try:
            action_row.set_subtitle(_URI) # the web address
        except:
            action_row.set_subtitle("----")
            # action_row.set_subtitle(GLib.uri_unescape_string(_URI, None))
        action_row.set_subtitle_lines(1)
        #
        btn_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL,4)
        btn_box.set_margin_end(4)
        btn_box.set_margin_start(4)
        btn_box.set_margin_bottom(4)
        # 
        close_btn = Gtk.Button(label=_lang.CLOSE)
        btn_box.append(close_btn)
        #
        box_sfx = Gtk.Box.new(Gtk.Orientation.HORIZONTAL,4)
        action_row.add_suffix(box_sfx)
        #
        action_label = Gtk.Label(label="-/-")
        #
        action_button = Gtk.Button.new_with_label(_lang.START)
        action_button._state = 0
        action_button.connect("clicked",self.on_stopresume_button)
        action_button._action = action_row
        action_button.set_css_classes(["suggested-action","pill"])
        box_sfx.append(action_button)
        self._btn = action_button
        if _speed == -1:
            action_button.set_sensitive(False)
        #
        action_button._row = action_row
        action_button._uri = _URI # the complete web address
        action_button._thread = None
        action_button._redir = _redir
        action_button._speed = _speed
        action_button._lbl = action_label
        action_button._completed = 0
        action_button._downloaded = 0
        action_button._size = real_size # the claimed size
        action_button._path = real_path # the complete file path
        # _path = os.path.join(dest_dir, os.path.basename(_URI)) # where to save the file and the file name
        if os.path.exists(real_path):
            _size = os.path.getsize(real_path)
            action_button._downloaded = _size # the size of the downloaded piece of the file
        #
        folder_btn = Gtk.Button.new()
        folder_btn.set_icon_name("folder-symbolic")
        folder_btn.connect("clicked", self.show_in_filemanager, real_path)
        box_sfx.append(folder_btn)
        ### redirections and speed
        row_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL,4)
        action_row.add_row(row_box)
        ###
        spn_lbl = Gtk.Label(label=_lang.REDIRECTION)
        # row_box.append(spn_lbl)
        spn_btn = Gtk.SpinButton.new_with_range(1,20,1)
        def on_redir_changed(_w):
            action_button._redir = _w.get_digits()
        spn_btn.set_value(_redir)
        # spn_btn.connect("value-changed", on_redir_changed)
        spn_btn.set_numeric(True)
        # row_box.append(spn_btn)
        #
        row_box.append(action_label)
        f_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL,0)
        f_box.set_hexpand(True)
        row_box.append(f_box)
        #
        spn_lbl2 = Gtk.Label(label=_lang.SPEEDDOWNLOAD)
        row_box.append(spn_lbl2)
        spn_btn2 = Gtk.SpinButton.new_with_range(0,2000000000,100000)
        def on_speed_changed(_w):
            action_button._speed = _w.get_digits()
        if _speed > 0:
            spn_btn2.set_value(_speed)
        spn_btn2.connect("value-changed", on_speed_changed)
        spn_btn2.set_tooltip_text(_lang.SPEEDDOWNLOAD2)
        spn_btn2.set_numeric(True)
        row_box.append(spn_btn2)
        ###
        btn_remove = Gtk.Button.new()
        btn_remove.set_icon_name("remove-symbolic")
        btn_remove.connect("clicked", self.on_btn_remove, self)
        btn_remove.set_tooltip_text(_lang.REMOVE)
        action_row.add_prefix(btn_remove)
        #
        btn_delete = Gtk.Button.new()
        btn_delete.set_icon_name("delete-symbolic")
        btn_delete.connect("clicked", self.on_btn_delete,  self)
        btn_delete.set_tooltip_text(_lang.DELETE)
        action_row.add_prefix(btn_delete)
        
    # show the file manager
    # 3b. related
    def show_in_filemanager(self, _w, real_path):
        # if not os.path.exists(real_path):
            # _path = os.path.basename(real_path)
        # else:
            # _path = real_path
        launcher = Gtk.FileLauncher(file=Gio.File.new_for_path(dest_dir or GLib.get_home_dir()))
        #
        def _done(launcher, result, _data = None):
           try:
               launcher.launch_finish(result)
           except GLib.Error as e:
               AlDial(self_main, e.message)
        launcher.launch(self_main, None, _done)
    
#################
    
    # find the filename
    # _data: [_URI, _redir, _speed, _signalm, file_path or None]
    def set_curl2(self, _data):
        # global _cancel
        c = pycurl.Curl()
        url = _data[0] # the web url
        _redir = _data[1]
        _speed = _data[2] # the download speed
        _signal = _data[3] # self._signalm
        file_path = _data[4] # the local full file path
        self.t_cancel = 0
        #
        filename = url.split("/")[-1].strip()
        filepath = os.path.join(dest_dir,filename)
        #
        # headers = []
        def header_function(header_line):
            # HTTP standard specifies that headers are encoded in iso-8859-1.
            header_line = header_line.decode('iso-8859-1')
            # headers.append(header_line)
            # _count += 1
            self.t_count += 1
            # stop abruptly
            if self.t_count == 30:
                self.t_cancel = 1
                c.pause(pycurl.PAUSE_ALL)
                return -1
            if header_line.startswith("Content-Disposition:"):
                # _start1 = header_line.find("filename=")
                _start1 = header_line.lower().find("filename=")
                _end1 = header_line.find(";", _start1)
                filename = urllib.parse.unquote(header_line[_start1+9:_end1], encoding='utf-8')
                filepath = os.path.join(dest_dir,filename)
                _signal.propName = filename
                self.t_cancel = 1
                c.pause(pycurl.PAUSE_ALL)
            # the content lenght
            elif header_line.lower().startswith("content-length:"):
                _size = int(header_line.split(":")[1].strip())
                _signal.propInt = _size
            elif header_line.strip() == "" or header_line.strip() == None:
                _signal.propList = ["END", [url, _redir, _speed, file_path]]
                self.t_cancel = 1
                c.pause(pycurl.PAUSE_ALL)

        c.setopt(c.HEADERFUNCTION, header_function)
        #
        # c.setopt(pycurl.CONNECTTIMEOUT, 30)
        c.setopt(pycurl.URL, url)
        c.setopt(pycurl.FOLLOWLOCATION, 1)
        c.setopt(pycurl.MAXREDIRS, 5)
        if _speed != 0:
            c.setopt(pycurl.MAX_RECV_SPEED_LARGE, 4096)# KB/s
        custom_headers = ['User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:58.0) Gecko/20100101 Firefox/58.0']
        c.setopt(pycurl.HTTPHEADER, custom_headers)
        #
        # Setup writing
        if os.path.exists(filepath):
            f = open(os.devnull, "ab")
            c.setopt(pycurl.RESUME_FROM, os.path.getsize(filepath))
            # c.setopt(pycurl.RESUME_FROM_LARGE, os.path.getsize(filepath))
        else:
            f = open(os.devnull, "wb")
        #
        c.setopt(pycurl.WRITEDATA, f)
        c.setopt(c.CAINFO, certifi.where())
        #
        def progress(total, existing, upload_t, upload_d):
            return self.t_cancel
        #
        c.setopt(c.NOPROGRESS, False)
        # c.setopt(c.XFERINFOFUNCTION, progress)
        c.setopt(pycurl.PROGRESSFUNCTION, progress)
        # 
        try:
            c.perform()
            c.close()
            return
        except pycurl.error as e:
            c.close()

###########

    # _data: [_URI, _redir, _speed, _signal, file_path, _count]
    def set_curl(self, _data):
        self.t_count = 0 # reset
        c = pycurl.Curl()
        url = _data[0]
        _redir = _data[1]
        _speed = _data[2]
        _signal = _data[3]
        file_path = _data[4]
        d_count = _data[5] # the incremental number associated to the file to download
        self.t_cancel = 0
        def signal_threadslot_c(_sign, _param,dd_count):
            _list = _signal.propList[0]
            if _list[0] == "COPY_ABORT" and dd_count == d_count:
                # global _cancel
                self.t_cancel = 1
                _thread = _list[0]
                return 1
        _signal.connect("notify::propList", signal_threadslot_c,d_count)
        #
        # c.setopt(pycurl.CONNECTTIMEOUT, 30)
        c.setopt(pycurl.URL, url)
        c.setopt(pycurl.FOLLOWLOCATION, 1)
        c.setopt(pycurl.MAXREDIRS, 5)
        if _speed != 0:
            c.setopt(pycurl.MAX_RECV_SPEED_LARGE, int(_speed))# KB/s
        custom_headers = ['User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:58.0) Gecko/20100101 Firefox/58.0']
        c.setopt(pycurl.HTTPHEADER, custom_headers)
        #
        # Setup writing
        if os.path.exists(file_path):
            f = open(file_path, "ab")
            c.setopt(pycurl.RESUME_FROM, os.path.getsize(file_path))
            # c.setopt(pycurl.RESUME_FROM_LARGE, os.path.getsize(file_path))
        else:
            f = open(file_path, "wb")
        #
        c.setopt(pycurl.WRITEDATA, f)
        c.setopt(c.CAINFO, certifi.where())
        c.setopt(pycurl.NOPROGRESS, 0)
        #
        def progress(total, existing, upload_t, upload_d):
            existing = os.path.getsize(file_path)
            try:
                frac = float(existing)/float(total)
            except:
                frac = 0
            _signal.propList = ["COPY",[total,existing,d_count]]
            return self.t_cancel
        #
        c.setopt(c.NOPROGRESS, False)
        # c.setopt(c.XFERINFOFUNCTION, progress)
        c.setopt(pycurl.PROGRESSFUNCTION, progress)
        # 
        try:
            c.perform()
            _signal.propList = ["TERMINATED",[os.path.getsize(file_path),d_count]]
            c.close()
            return
        except pycurl.error as e:
            if e.args[0] == pycurl.E_COULDNT_CONNECT and c.exception:
                _signal.propList = ["ERROR1",[c.exception,d_count]]
                return
            else:
                _signal.propList = ["ERROR2",[e,d_count]]
                return


class MyApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def do_activate(self):
        active_window = self.props.active_window
        if active_window:
            active_window.present()
        else:
            self.win = MainWindow(application=self)
            self.win.present()

app = MyApp(application_id="com.Prism.download.manager",flags= Gio.ApplicationFlags.DEFAULT_FLAGS)
_app = app
app.run(sys.argv)
