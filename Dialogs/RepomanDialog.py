#!/usr/bin/env python
# -*- coding: ANSI_X3.4-1968 -*-
# generated by wxGlade 0.3.5.1 on Tue Jan 11 00:02:35 2005

import shutil
import sys
import os
import wx

from FileBrowser import MyBrowser
from MyLog import MyLog
#import abeniCVS

import utils
import options

codes={}
codes["bold"]="\x1b[01m"
codes["teal"]="\x1b[36;06m"
codes["turquoise"]="\x1b[36;01m"
codes["fuscia"]="\x1b[35;01m"
codes["purple"]="\x1b[35;06m"
codes["blue"]="\x1b[34;01m"
codes["darkblue"]="\x1b[34;06m"
codes["green"]="\x1b[32;01m"
codes["darkgreen"]="\x1b[32;06m"
codes["yellow"]="\x1b[33;01m"
codes["brown"]="\x1b[33;06m"
codes["red"]="\x1b[31;01m"
codes["darkred"]="\x1b[31;06m"
codes["reset"] = "\x1b[0m"

class MyFrame(wx.Frame):

    """Repoman console for scan/full/commit, metadata editting"""

    def __init__(self, *args, **kwds):
        # begin wxGlade: MyFrame.__init__
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.repoman_console_statusbar = self.CreateStatusBar(1, 0)
        self.button_cvs_up = wx.Button(self, -1, "cvs update")
        self.button_copy_olay = wx.Button(self, -1, "Copy ebuild from overlay")
        self.button_filesdir = wx.Button(self, -1, "Copy from FILESDIR")
        self.button_cvs_add = wx.Button(self, -1, "cvs add file")
        self.button_metadata = wx.Button(self, -1, "Edit metadata")
        self.button_digest = wx.Button(self, -1, "Create digest")
        self.button_repoman_full = wx.Button(self, -1, "repoman full")
        self.button_commit_pretend = wx.Button(self, -1, "repoman pretend commit")
        self.button_commit = wx.Button(self, -1, "repoman commit")
        self.text_ctrl_log = wx.TextCtrl(self, -1, "", style=wx.TE_MULTILINE|wx.TE_READONLY)
        self.label_dir = wx.StaticText(self, -1, "CVS dir:")
        self.fileBrowser = MyBrowser(self, )

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: MyFrame.__set_properties
        self.SetTitle("Repoman Console")
        _icon = wx.EmptyIcon()
        _icon.CopyFromBitmap(wx.Bitmap("/usr/share/pixmaps/abeni/abeni_logo16.png", wx.BITMAP_TYPE_ANY))
        self.SetIcon(_icon)
        self.SetSize((891, 618))
        self.repoman_console_statusbar.SetStatusWidths([-1])
        # statusbar fields
        repoman_console_statusbar_fields = [""]
        for i in range(len(repoman_console_statusbar_fields)):
            self.repoman_console_statusbar.SetStatusText(repoman_console_statusbar_fields[i], i)
        self.button_cvs_up.SetDefault()
        self.button_copy_olay.SetDefault()
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: MyFrame.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4 = wx.BoxSizer(wx.VERTICAL)
        sizer_3 = wx.BoxSizer(wx.VERTICAL)
        sizer_3.Add(self.button_cvs_up, 0, wx.BOTTOM|wx.EXPAND|wx.FIXED_MINSIZE, 8)
        sizer_3.Add(self.button_copy_olay, 0, wx.BOTTOM|wx.EXPAND|wx.FIXED_MINSIZE, 8)
        sizer_3.Add(self.button_filesdir, 0, wx.BOTTOM|wx.EXPAND|wx.FIXED_MINSIZE, 8)
        sizer_3.Add(self.button_cvs_add, 0, wx.BOTTOM|wx.EXPAND|wx.FIXED_MINSIZE, 8)
        sizer_3.Add(self.button_metadata, 0, wx.BOTTOM|wx.EXPAND|wx.FIXED_MINSIZE, 8)
        sizer_3.Add(self.button_digest, 0, wx.BOTTOM|wx.EXPAND|wx.FIXED_MINSIZE, 8)
        sizer_3.Add(self.button_repoman_full, 0, wx.BOTTOM|wx.EXPAND|wx.FIXED_MINSIZE, 8)
        sizer_3.Add(self.button_commit_pretend, 0, wx.BOTTOM|wx.EXPAND|wx.FIXED_MINSIZE, 8)
        sizer_3.Add(self.button_commit, 0, wx.BOTTOM|wx.EXPAND|wx.FIXED_MINSIZE, 8)
        sizer_2.Add(sizer_3, 0, wx.ALL|wx.EXPAND, 10)
        sizer_4.Add(self.text_ctrl_log, 1, wx.ALL|wx.EXPAND|wx.FIXED_MINSIZE, 4)
        sizer_4.Add(self.label_dir, 0, wx.LEFT|wx.FIXED_MINSIZE, 2)
        sizer_4.Add(self.fileBrowser, 1, wx.ALL|wx.EXPAND, 4)
        sizer_2.Add(sizer_4, 1, wx.EXPAND, 0)
        sizer_1.Add(sizer_2, 1, wx.EXPAND, 0)
        self.SetAutoLayout(True)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

        self.__my_layout()

    def __my_layout(self):
        """Customize frame, add events"""
        wx.EVT_BUTTON(self, self.button_cvs_up.GetId(), self.OnCvsUp) 
        wx.EVT_BUTTON(self, self.button_copy_olay.GetId(), self.OnCopyOlay) 
        wx.EVT_BUTTON(self, self.button_filesdir.GetId(), self.OnFilesdir) 
        wx.EVT_BUTTON(self, self.button_cvs_add.GetId(), self.OnCvsAdd) 
        wx.EVT_BUTTON(self, self.button_metadata.GetId(), self.OnMetadata) 
        wx.EVT_BUTTON(self, self.button_digest.GetId(), self.OnDigest) 
        wx.EVT_BUTTON(self, self.button_repoman_full.GetId(), self.OnRepoFull) 
        wx.EVT_BUTTON(self, self.button_commit_pretend.GetId(),
                      self.OnCommitPretend) 
        wx.EVT_BUTTON(self, self.button_commit.GetId(), self.OnCommit) 
        
        wx.EVT_CLOSE(self, self.OnClose)
        wx.EVT_END_PROCESS(self, -1, self.OnProcessEnded)

        self.process = None
        self.running = None
        self.action = None

        points = self.text_ctrl_log.GetFont().GetPointSize()
        f = wx.Font(points, wx.MODERN, wx.NORMAL, True)
        self.text_ctrl_log.SetDefaultStyle(wx.TextAttr("BLACK",
                                                       wx.NullColour, f)
                                           )
        wx.Log_SetActiveTarget(MyLog(self.text_ctrl_log))
        self.Write("))) Repoman console ready.")

        prefs = options.Options().Prefs()
        self.cvs_root = prefs["cvsRoot"]
        frame = self.GetParent()
        self.cat = utils.get_category_name(frame)
        self.pn = utils.get_pn(frame)
        ebuild_path = frame.filename
        ebuild_basename = os.path.basename(ebuild_path)
        self.cvs_ebuild_dir = self.QueryDir()
        self.cvs_ebuild_path = "%s/%s" % (self.cvs_ebuild_dir, ebuild_basename)
        self.orig_ebuild_path = ebuild_path
        self.overlay_dir = os.path.dirname(ebuild_path)
        if not os.path.exists(self.cvs_ebuild_dir):
            self.new_pkg = 1
        else:
            self.new_pkg = 0
        self.cur_dir = os.getcwd()
        os.chdir(self.cvs_ebuild_dir)
        self.RefreshBrowser()

    def DoFilesdir(self):
        """Copy files from overlay ${FILESDIR} to CVS ${FILESDIR} """
        p = '%s/files' % utils.get_ebuild_dir(self.parent)
        if not os.path.exists(p):
            return 0
        files = os.listdir(p)
        def strp(s): return s.strip()
        files = map(strp, files )
        files = filter(None, files)
        files.sort()
        my_files = []
        for f in files:
            if f[:7] != "digest-":
                my_files.append(f)
        if not my_files:
            return 0
        dlg = wx.MultipleChoiceDialog(self.parent, 'Choose one or more:', '${FILESDIR}', my_files)
        if dlg.ShowModal() == wx.ID_OK:
            files = dlg.GetValueString()
        else:
            dlg.Destroy()
            return 0

        filesdir = "%s/files" % self.overlay_dir
        cvs_filesdir = "%s/files/" % self.cvs_ebuild_dir 
        try:
            os.mkdir(cvs_filesdir)
        except:
            self.parent.Write("!!! Failed to create dir: %s " % cvs_filesdir)
            return "error"
        for f in files:
            fpath = "%s/%s" % (filesdir, f)
            try:
                shutil.copy(fpath, cvs_filesdir)
                self.parent.Write("))) Copied: %s " % f)
            except:
                self.parent.Write("!!! Failed to copy %s from %s" % (f, filesdir))
                return "error"
            self.CVSAdd("files/%s" % f)
        return 1

    def QueryDir(self):
        """Return CVS directory of this ebuild"""
        return "%s/%s/%s" % (self.cvs_root, self.cat, self.pn)

    def CreateCVSdir(self):
        """Create CVSroot/category/package directory"""
        try:
            #self.SyncExecute("mkdir %s" % self.cvs_ebuild_dir)
            #self.SyncExecute("mkdir %s/files" % self.cvs_ebuild_dir)
            return 1
        except:
            return 0

    def CvsUpdate(self):
        """cvs update"""
        self.Write("))) cvs update in %s" % self.cvs_ebuild_dir)
        cmd = "/usr/bin/cvs update"
        self.ExecuteInLog(cmd)

    def CopyEbuild(self):
        """Copy ebuild from PORT_OVERLAY to CVSroot/category/package/"""
        #TODO: Catch exact exceptions
        try:
            shutil.copy(self.orig_ebuild_path, self.cvs_ebuild_dir)
            return 1
        except:
            return 0

    def CopyMetadata(self):
        """Copy metadata.xml from PORT_OVERLAY to CVSroot/category/package/"""
        file = "%s/metadata.xml" % self.overlay_dir
        try:
            shutil.copy(file, self.cvs_ebuild_dir)
            return 1
        except:
            return 0


    def Repoman(self, args):
        """/usr/bin/repoman"""
        cmd = "/usr/bin/repoman %s" % (args)
        self.Execute(cmd)

    def RepomanCommit(self):
        msg = self.GetMsg()
        if msg:
            cmd = "/usr/bin/repoman commit -m '%s'" %  msg
            self.SyncExecute(cmd)

    def GetMsg(self, caption, title):
        dlg = wx.TextEntryDialog(self.parent, caption, title, self.cmsg)
        if dlg.ShowModal() == wx.ID_OK:
            self.cmsg = dlg.GetValue()
            dlg.Destroy()
            return 1
        else:
            dlg.Destroy()
            return 0

    def CreateDigest(self):
        cmd = "/usr/sbin/ebuild %s digest" % os.path.basename(self.cvs_ebuild_path)
        self.SyncExecute(cmd)

    def CVSAddDir(self):
        cmd = "/usr/bin/cvs add %s" % self.pn
        cmd = "/usr/bin/cvs add %s/files" % self.pn
        self.SyncExecute(cmd)

    def CVSAdd(self, file):
        cmd = "/usr/bin/cvs add %s" % file
        self.SyncExecute(cmd)

    def StripColor(self, text):
        for c in codes:
            if text.find(codes[c]) != -1:
                text = text.replace(codes[c], '')
        return text 

    def Echangelog(self, msg):
        self.SyncExecute("/usr/bin/echangelog %s" % msg)

    def OnCvsUp(self, event):
        """"""
        self.CvsUpdate()

    def OnCopyOlay(self, event):
        """"""
        print "pass"

    def OnFilesdir(self, event):
        """"""
        print "pass"

    def OnCvsAdd(self, event):
        """"""
        print "pass"

    def OnMetadata(self, event):
        """"""
        print "pass"

    def OnDigest(self, event):
        """"""
        print "pass"

    def OnRepoFull(self, event):
        """"""
        print "pass"

    def OnCommitPretend(self, event):
        """"""
        print "pass"

    def OnCommit(self, event):
        """"""
        print "pass"


    def OnClose(self, event):
        """Clean up"""
        os.chdir(self.cur_dir)
        self.Destroy()

    def Write(self, txt):
        """Send text to log window"""
        print txt
        self.WriteText(txt)

    def WriteText(self, text):
        """Send text to log window after colorizing"""
        #self.logfile.write(text + "\n")

        if text[-1:] == '\n':
            text = text[:-1]
        #Remove color and other esc codes
        text = text.replace('\b', '')
        text = text.replace("\x1b[0m" , '')
        text = text.replace("\x1b[01m", '')
        text = text.replace("\x1b[32;01m" , '')
        text = text.replace("\x1b[32;06m" , '')
        text = text.replace("\x1b[31;06m", '')
        text = text.replace("\x1b[31;01m", '')
        text = text.replace("\x1b[33;06m", '')
        text = text.replace("\x1b[33;01m", '')
        text = text.replace("\x1b[32;06m", '')
        text = text.replace("\x1b[32;01m", '')
        text = text.replace("\x1b[34;06m", '')
        text = text.replace("\x1b[35;06m", '')
        text = text.replace("\x1b[34;01m", '')
        text = text.replace("\x1b[35;01m", '')
        text = text.replace("\x1b[36;01m", '')
        text = text.replace("\x1b[36;06m", '')
        # For the [ok]'s
        text = text.replace("\x1b[A", '')
        text = text.replace("\x1b[-7G", '')
        text = text.replace("\x1b[73G", '')
        pref = text[0:3]
        if pref == ">>>" or pref == "<<<" or pref == "---" \
             or pref == ")))" or  pref == " * ":
            self.LogColor("BLUE")
            wx.LogMessage(text)
            self.LogColor("BLACK")
        elif pref == "!!!":
            self.LogColor("RED")
            wx.LogMessage(text)
            self.LogColor("BLACK")
        else:
            wx.LogMessage(text)

    def LogColor(self, color):
        """Set color of text sent to log window"""
        self.text_ctrl_log.SetDefaultStyle(wx.TextAttr(wx.NamedColour(color)))

    def ExecuteInLog(self, cmd, log_msg=''):
        """Run program asynchronously sending stdout & stderr to log window"""
        if self.running:
            msg = "!!! Please wait till this finishes:\n %s" % self.running
            self.Write(msg)
            return
        if log_msg:
            self.Write(log_msg)
        self.running = cmd
        self.process = wx.Process(self)
        self.process.Redirect();
        module_path = "/usr/lib/python%s/site-packages/abeni" % sys.version[0:3]
        py_cmd = "python -u %s/doCmd.py %s" % (module_path, cmd)
        self.pid = wx.Execute(py_cmd, wx.EXEC_ASYNC, self.process)
        #Start timer to keep GUI updated:
        ID_Timer = wx.NewId()
        self.timer = wx.Timer(self, ID_Timer)
        wx.EVT_TIMER(self,  ID_Timer, self.HandleIdle)
        self.timer.Start(100)

    def HandleIdle(self, event):
        """Keep GUI fresh while executing async commands"""
        if self.process is not None:
            stream = self.process.GetInputStream()
            if stream.CanRead():
                t = stream.readline()
                self.Write(t)
            stream = self.process.GetErrorStream()
            if stream.CanRead():
                t = stream.readline()
                self.Write(t)

    def OnProcessEnded(self, evt):
        """Clean up after async command finishes"""
        self.timer.Stop()
        stream = self.process.GetInputStream()
        if stream.CanRead():
            text = stream.read()
            text = text.split('\n')
            for t in text:
                self.Write(t)
        self.process.Destroy()
        self.process = None
        self.running = None
        action = self.action
        self.action = None
        self.PostAction(action)

    def PostAction(self, action):
        """Perform something after async cmd finishes"""
        self.Write("))) Done.")
        self.RefreshBrowser()

    #def RefreshBrowserFilesdir(self):
    #    """Populate file browser with CVSdir/FILESDIR"""
    #    filesdir = os.path.join(self.cvs.cvs_ebuild_dir, "filesdir") 
    #    #TODO: Make sure its a directory?
    #    if os.path.exists(filesdir):
    #        parent.fileBrowser.populate(filesdir)

    def RefreshBrowser(self):
        """Populate file browser"""
        if os.path.exists(self.cvs_ebuild_dir):
            self.fileBrowser.populate(self.cvs_ebuild_dir)


# end of class MyFrame

