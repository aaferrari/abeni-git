#!/usr/bin/env python

"""Abeni - Gentoo Linux Ebuild Editor/Syntax Checker
Released under the terms of the GNU Public License v2"""

__author__ = 'Rob Cakebread'
__email__ = 'robc@myrealbox.com'
__version__ = '0.0.5'
__changelog_ = 'http://abeni.sf.net/ChangeLog'

print "Importing portage config, wxPython, Python and Abeni modules..."
from portage import config
from wxPython.wx import *
from wxPython.lib.dialogs import wxScrolledMessageDialog
import os, string, sys, urlparse, time
import dialogs, panels
from utils import *

distdir = config().environ()['DISTDIR']
portdir = config().environ()['PORTDIR']
portdir_overlay = config().environ()['PORTDIR_OVERLAY']
portage_tmpdir = config().environ()['PORTAGE_TMPDIR']

defaults = ["SRC_URI", "HOMEPAGE", "DEPEND", "RDEPEND", "DESCRIPTION", \
            "S", "IUSE", "SLOT", "KEYWORDS", "LICENSE"]

class MyFrame(wxFrame):

    """ Main frame that holds the menu, toolbar and notebook """

    def __init__(self, parent, id, title):
        wxFrame.__init__(self, parent, -1, title, size=wxSize(900,600))

        #Catch the close event so we can clean up nicely.
        EVT_CLOSE(self,self.OnClose)
        # Are we in the process of editing an ebuild?
        self.editing = 0
        #Load recently accessed ebuilds
        if not os.path.exists(os.path.expanduser('~/.abeni')):
            print "Creating directory " + os.path.expanduser('~/.abeni')
            os.mkdir(os.path.expanduser('~/.abeni'))
        bookmarks = os.path.expanduser('~/.abeni/recent.txt')
        if os.path.exists(bookmarks):
            self.recentList = open(bookmarks, 'r').readlines()
        else:
            self.recentList = []
        # Get options from ~/.abeni/abenirc file
        GetOptions(self)
        # Custom functions added instances
        self.funcList = []
        #Misc statements/commands instances
        self.statementList = []
        # Keep track of order variables are set
        self.varOrder = []
        # Keep track of order functions are set
        self.funcOrder = []
        # Ebuild's path and filename
        self.filename = ''
        # Previous file opened. For use with diff
        self.lastFile = ''
        # Saved state
        self.saved = 1
        # Tells if an external command is running, like emerge, ebuild etc.
        self.running = None
        # Action performed during external commands
        self.action = None
        # Ordered list of notebook tabs
        self.tabs = []
        self.tabsInstance = []

        #Stuff to keep log window updating in "real-time" as shell commands are executed
        self.process = None
        EVT_IDLE(self, self.OnIdle)
        EVT_END_PROCESS(self, -1, self.OnProcessEnded)

        #application icon 16x16
        iconFile = ('/usr/share/pixmaps/abeni/abeni_logo16.png')
        icon = wxIcon(iconFile, wxBITMAP_TYPE_PNG)
        self.SetIcon(icon)
        AddMenu(self)
        AddToolbar(self)
        self.sb = self.CreateStatusBar(2, wxST_SIZEGRIP)
        self.splitter = wxSplitterWindow(self, -1, style=wxNO_3D|wxSP_3D)
        def EmptyHandler(evt): pass
        EVT_ERASE_BACKGROUND(self.splitter, EmptyHandler)
        self.nb = wxNotebook(self.splitter, -1, style=wxCLIP_CHILDREN)
        EVT_NOTEBOOK_PAGE_CHANGED(self.nb, -1, self.OnPageChanged)
        EVT_NOTEBOOK_PAGE_CHANGED(self.nb, -1, self.OnPageChanging)
        self.nb.portdir_overlay = portdir_overlay
        self.nb.portdir = portdir
        self.log = wxTextCtrl(self.splitter, -1,
                             style = wxTE_MULTILINE|wxTE_READONLY|wxHSCROLL)
        self.log.SetFont(wxFont(12, wxMODERN, wxNORMAL, wxNORMAL, faceName="Lucida Console"))
        #This would be nice, but some .gtkrc files screw it up:
        #self.log.SetBackgroundColour(wxBLACK)
        #self.log.SetDefaultStyle(wxTextAttr(wxWHITE))
        #self.log.SetDefaultStyle(wxTextAttr(wxNullColour, wxBLACK))

        wxLog_SetActiveTarget(MyLog(self.log))
        self.Show(True)
        self.splitter.SplitHorizontally(self.nb, self.log, 400)
        self.splitter.SetMinimumPaneSize(20)
        #Load ebuild if specified on command line, by filename or by full package name
        if len(sys.argv) == 2:
            f = sys.argv[1]
            if os.path.exists(f):
                LoadEbuild(self, f, __version__, portdir)
            else:
                print "No such file: %s" % f
                print "Checking for package: %s" % f
                #Make sure GUI is drawn before we start the slow search
                wxSafeYield()
                self.LoadByPackage(f)

    def __del__(self):
        if self.process is not None:
            self.process.Detach()
            self.process.CloseOutput()
            self.process = None

    def OnMnuLogBottom(self, event):
        """Switch ouput log to bottom"""
        if not self.editing:
            return
        self.LogBottom()


    def LogBottom(self):
        txt = self.log.GetValue()
        self.splitter.SplitHorizontally(self.nb, self.log, 400)
        self.splitter.SetMinimumPaneSize(20)
        wxLog_SetActiveTarget(MyLog(self.log))
        self.log.SetValue(txt)
        self.log.Show(True)
        self.log.ShowPosition(self.log.GetLastPosition())
        #self.log.Refresh()
        self.pref['log'] = 'bottom'
        self.nb.DeletePage(0)

    def OnMnuLogTab(self, event):
        """Switch ouput log to tab"""
        if not self.editing:
            return
        self.LogTab()
        self.logWindow.log.ShowPosition(self.logWindow.log.GetLastPosition())

    def LogTab(self):
        txt = self.log.GetValue()
        self.logWindow=panels.LogWindow(self.nb, self.sb, self.pref)
        wxLog_SetActiveTarget(MyLog(self.logWindow.log))
        self.nb.InsertPage(0, self.logWindow, "Log")
        self.logWindow.log.SetValue(txt)
        self.splitter.Unsplit()
        self.nb.SetSelection(0)
        self.pref['log'] = 'tab'

    def WriteText(self, text):
        if text[-1:] == '\n':
            text = text[:-1]
        wxLogMessage(text)

    def write(self, txt):
        self.WriteText(txt)

    def OnToolbarXterm(self, event):
        """Launch xterm in $PORTAGE_TMPDIR/portage/$P/"""
        #TODO: Damn it. I wish we could cd to ${S}
        if self.editing:
            c = os.getcwd()
            #TODO: Make a self.P variable or something:
            ebuild = self.panelMain.EbuildFile.GetValue()
            p = string.replace(ebuild, '.ebuild', '')
            os.chdir('%s/portage/%s' % (portage_tmpdir, p))
            os.system('sudo %s &' % self.pref['xterm'])
            os.chdir(c)

    def OnMnuNewVariable(self, event):
        """Dialog for adding new variable"""
        if not self.editing:
            return
        dlg = wxTextEntryDialog(self, 'New Variable Name:',
                            'Enter Variable Name', 'test')
        dlg.SetValue("")
        if dlg.ShowModal() == wxID_OK:
            newVariable = dlg.GetValue()
            self.varOrder.append(newVariable)
            self.AddNewVar(newVariable, "")
        self.saved = 0
        dlg.Destroy()

    def AddNewVar(self, var, val):
        """Add new variable on Main panel"""
        if val == '':
            val = '""'
        self.panelMain.AddVar(var, val)

    def OnMnuDelVariable(self, event):
        """Delete custom variable"""
        if not self.editing:
            return
        self.saved = 0
        DelVariable(self)

    def AddCommand(self, command):
        t = self.panelMain.stext.GetValue()
        t += "%s\n" % command
        self.panelMain.stext.SetValue(t)

    def OnMnuEdit(self, event):
        """Launch external editor then reload ebuild after editor exits"""
        if self.editing:
            if not self.VerifySaved():
                self.ClearNotebook()
                #Don't run sudo, we want user owner/perms on ebuild files in PORTDIR_OVERLAY
                wxSafeYield()
                os.system('%s %s' % (self.pref['editor'], self.filename))
                LoadEbuild(self, self.filename, __version__, portdir)

    def OnMnuDiff(self, event):
        """Run diff program on original vs. saved ebuild"""
        #TODO Add error dialog if last opened wasn't same package, or is empty
        if not self.editing:
            return

        #orgFile = string.replace(self.filename, 'local/', '')
        if self.lastFile:
            os.system(self.pref['diff'] + ' ' + self.lastFile + ' ' + self.filename + ' &')

    def OnMnuDiffCreate(self, event):
        """Create diff file of original vs. saved ebuild"""
        #TODO: Add error dialog if last opened wasn't same package, or is empty
        # Add dialog telling them file is saved in ~/.abeni/diffFile
        if not self.editing:
            return

        #No file to compare with
        if not self.lastFile:
            return

        #orgFile = string.replace(self.filename, 'local/', '')
        diffFile = string.replace(self.ebuild_file, '.ebuild', '.diff')
        #print orgFile, diffFile
        cmd = 'diff -u %s %s > ~/.abeni/%s' % (self.lastFile, self.filename, diffFile)
        #os.system(cmd)
        self.ExecuteInLog(cmd)

    def OnMnuCreateDigest(self, event):
        """Run 'ebuild filename digest' on this ebuild"""
        if not self.editing:
            return
        if self.SaveEbuild():
            #TODO: Strip escape codes so we can put in a text widget for those who use sudo
            cmd = 'sudo /usr/sbin/ebuild %s digest' % self.filename
            #os.system(self.pref['xterm'] + ' -T "Creating Digest" -hold -e ' + cmd + ' &')
            self.ExecuteInLog(cmd)

    def OnMnuRepoman(self, event):
        """Run 'repoman-local-5.py' on this ebuild"""
        if not self.editing:
            return
        current = os.getcwd()
        #os.chdir(self.ebuildDir)
        cmd = 'cd %s;/usr/bin/repoman-safe.py' % self.ebuildDir
        #cmd2 = self.pref['xterm'] + ' -T "repoman-safe" -e ' + cmd + ' &'
        #os.system(cmd2)
        os.chdir(current)
        self.ExecuteInLog(cmd)

    def OnMnuEmerge(self, event):
        """Run 'emerge <options> <this ebuild>' """
        if not self.editing:
            return
        if self.SaveEbuild():
            cmd = 'USE="%s" FEATURES="%s" sudo /usr/bin/emerge %s' % (self.pref['use'], self.pref['features'], self.filename)
            dlg = wxTextEntryDialog(self, 'What arguments do you want to pass?',
                                'Arguments?', cmd)
            #dlg.SetValue("")
            if dlg.ShowModal() == wxID_OK:
                cmd = dlg.GetValue()
                self.write("Executing:\n%s" % cmd)
                dlg.Destroy()
            else:
                dlg.Destroy()
                return
            """
            if opts == '-p' or opts == '--pretend':
                #cmd = '"/usr/bin/emerge ' + opts + ' ' + self.filename + ' ; echo Done"'
                cmd = '/usr/bin/emerge %s %s' % (opts, self.filename)
            else:
                if opts == 'unmerge' or opts == '-C' or opts == '-s' or opts == '--search':
                    #cmd = 'sudo /usr/bin/emerge ' + opts + ' ' + self.package + ' ; echo Done'
                    cmd = 'sudo /usr/bin/emerge %s %s' % (opts, self.package)
                    print cmd
                else:
                    #cmd = 'sudo /usr/bin/emerge ' + opts + ' ' + self.filename + ' ; echo Done'
                    cmd = 'sudo /usr/bin/emerge %s %s' % (opts, self.filename)
            """
            #cmd2 = self.pref['xterm'] + ' -T "emerge" -hold -e ' + cmd + ' &'
            #os.system(cmd2)
            self.ExecuteInLog(cmd)


    def OnMnuEbuild(self, event):
        """Run 'ebuild <file> <cmd>' """
        if not self.editing:
            return
        c = ['setup', 'depend', 'merge', 'qmerge', 'unpack',
             'compile', 'rpm', 'package', 'prerm', 'postrm',
             'preinst', 'postinst', 'config', 'touch', 'clean',
             'fetch', 'digest', 'install', 'unmerge']
        c.sort()
        dlg = wxSingleChoiceDialog(self, 'Command:', 'ebuild command',
                                   c, wxOK|wxCANCEL)
        if dlg.ShowModal() == wxID_OK:
            opt = dlg.GetStringSelection()
            dlg.Destroy()
        else:
            dlg.Destroy()
            return
        if self.SaveEbuild():
            cmd = 'USE="%s" FEATURES="%s" sudo /usr/sbin/ebuild %s %s' % (self.pref['use'], self.pref['features'], self.filename, opt)
            self.write('Executing:\n%s' % cmd)
            #cmd = 'sudo /usr/sbin/ebuild ' + self.filename + ' ' + opt + ' ; echo Done'
            #cmd = '%s %s sudo /usr/sbin/ebuild %s %s' % (self.pref['use'], self.pref['features'], self.filename, opt)
            #cmd2 = '%s  -T "ebuild" -hold -e %s' % (self.pref['xterm'], cmd)
            #os.system(cmd2)
            #for l in os.popen(cmd).readline():
            #    self.write(l)
            self.ExecuteInLog(cmd)

    '''
    def OnIdle(self, event):
        if self.inp is not None:
            wxYield()
            l = self.inp.readline()
            self.write(l)
            while l:
                wxYield()
                l = self.inp.readline()
                self.write(l)
            self.inp = None
            self.tb.EnableTool(self.toolStopID, False)
            #self.myTimer.Stop()
    '''

    def OnTimer(self, event):
        wxYield()
        print "OnTimer"

    def OnCloseStream(self, evt):
        #self.write('OnCloseStream\n')
        #print "b4 CloseOutput"
        self.process.CloseOutput()
        #print "after CloseOutput"

    def OnIdle(self, event):
        if self.process is not None:
            stream = self.process.GetInputStream()

            if stream.CanRead():
                text = stream.read()
                self.write(text)

    def OnProcessEnded(self, evt):
        #self.log.write('OnProcessEnded, pid:%s,  exitCode: %s\n' %
        #               (evt.GetPid(), evt.GetExitCode()))
        #print "PROCESS ENDED"
        stream = self.process.GetInputStream()
        if stream.CanRead():
            text = stream.read()
            self.write(text)

        self.process.Destroy()
        self.process = None
        self.tb.EnableTool(self.toolStopID, False)
        self.running = None
        self.log.ShowPosition(self.log.GetLastPosition())
        self.PostAction(self.action)
        self.action = None

    def PostAction(self, action):
        if action == 'unpack':
            ebuild = self.panelMain.EbuildFile.GetValue()
            p = string.replace(ebuild, '.ebuild', '')
            d = '%s/portage/%s/work' % (portage_tmpdir, p)
            self.write("Unpacked into ${WORKDIR}/work/:")
            self.ExecuteInLog('sudo ls %s' % d)

    def ExecuteInLog(self, cmd):
        if self.running:
            msg = ("Please wait till this finishes:\n %s" % self.running)
            dlg = wxMessageDialog(self, msg, 'Abeni: Error - Wait till external program is finished.', \
                                wxOK | wxICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
            return
        self.running = cmd
        self.tb.EnableTool(self.toolStopID, True)
        self.process = wxProcess(self)
        self.process.Redirect();
        pyCmd = "python -u doCmd.py %s" % cmd
        self.pid = wxExecute(pyCmd, wxEXEC_ASYNC, self.process)
        #self.write('"%s" pid: %s\n' % (cmd, pid))


    def KillProc(self, event):
        os.system("sudo kill %s" % self.pid)
        self.write("Killed %s" % self.pid)

    def OnMnuLintool(self, event):
        """Run 'lintool' on this ebuild"""
        if not self.editing:
            return

        cmd = '/usr/bin/lintool %s' % self.filename
        #print cmd
        #cmd2 = self.pref['xterm'] + ' -T "Lintool" -e ' + cmd + ' &'
        #print cmd2
        #os.system(cmd2)
        self.ExecuteInLog(cmd)

    def ClearNotebook(self):
        """Delete all pages in the notebook"""
        self.nb.DeleteAllPages()
        self.funcList = []
        self.statementList = []
        self.funcOrder = []
        self.varOrder = []
        # Stupid kludge. See TODO
        x,y  = self.GetSize()
        self.SetSize(wxSize(x+1, y))

    def SetFilename(self, filename):
        """Set the ebuild full path and filename"""
        #Keep last file for viewing and creating diffs
        self.lastFile = self.filename
        self.filename = filename
        self.sb.SetStatusText(filename, 1)

    def GetFilename(self):
        """Get the full path and filename of ebuild"""
        return self.filename

    def SeparateVars(self, vars):
        """Separates variables into defaultVars and all others (vars)"""
        defaultVars = {}
        for key in defaults:
            if vars.has_key(key):
                defaultVars[key] = vars[key]
                del vars[key]
            else:
                defaultVars[key] = ""
        return defaultVars, vars

    def VerifySaved(self):
        modified = 0
        status = 0
        for fns in self.funcList:
            if fns.edNewFun.GetModify():
                modified = 1
                break
        if modified or not self.saved:
            dlg = wxMessageDialog(self, 'Save modified ebuild?\n' + self.filename,
                    'Save ebuild?', wxYES_NO | wxCANCEL | wxICON_INFORMATION)
            val = dlg.ShowModal()
            if val == wxID_YES:
                WriteEbuild(self)
                self.saved = 1
                status = 0
            if val == wxID_NO:
                status = 0
            if val == wxID_CANCEL:
                status = 1
            dlg.Destroy()
        return status

    def OnFileHistory(self, evt):
        """Load ebuild on FileHistory event"""
        # get the file based on the menu ID
        fileNum = evt.GetId() - wxID_FILE1
        path = self.filehistory.GetHistoryFile(fileNum)
        if os.path.exists(path) and not self.VerifySaved():
            self.ClearNotebook()
            LoadEbuild(self, path, __version__, portdir)
            # add it back to the history so it will be moved up the list
            self.filehistory.AddFileToHistory(path)

    def OnMnuLoad(self, event):
        """Load ebuild file"""
        if not self.VerifySaved():
            wildcard = "ebuild files (*.ebuild)|*.ebuild"
            dlg = wxFileDialog(self, "Choose a file", portdir, "", \
                                wildcard, wxOPEN)
            if dlg.ShowModal() == wxID_OK:
                filename = dlg.GetPath()
                if os.path.exists(filename):
                    if self.editing:
                        self.ClearNotebook()
                    LoadEbuild(self, filename, __version__, portdir)
                    self.filehistory.AddFileToHistory(filename)
            dlg.Destroy()

    def PopulateForms(self, defaultVars):
        """Fill forms with saved data"""
        self.panelMain.Package.SetValue(defaultVars['package'])
        self.package = defaultVars['package']
        self.panelMain.EbuildFile.SetValue(defaultVars['ebuild_file'])
        self.panelMain.Category.SetValue(defaultVars['category'])
        self.panelMain.URI.SetValue(defaultVars['SRC_URI'])
        self.panelMain.Homepage.SetValue(defaultVars['HOMEPAGE'])
        self.panelMain.Desc.SetValue(defaultVars['DESCRIPTION'])
        self.panelMain.S.SetValue(defaultVars['S'])
        self.panelMain.USE.SetValue(defaultVars['IUSE'])
        self.panelMain.Slot.SetValue(defaultVars['SLOT'])
        self.panelMain.Keywords.SetValue(defaultVars['KEYWORDS'])
        self.panelMain.License.SetValue(defaultVars['LICENSE'])
        d = string.split(defaultVars['DEPEND'], '\n')
        depends = []
        for s in d:
            s = s.replace('"', '')
            depends.append(s)
        self.panelDepend.elb1.SetStrings(depends)
        r = string.split(defaultVars['RDEPEND'], '\n')
        rdepends = []
        for s in r:
            s = s.replace('"', '')
            rdepends.append(s)
        self.panelDepend.elb2.SetStrings(rdepends)

    def OnPageChanging(self, event):
        """Catch event when page in notebook is going to change"""
        #to = event.GetSelection()
        #current = event.GetOldSelection()
        #print "Change from %s to %s" % (current, to)
        #print "Page %s" % n
        #print "Tab %s" % self.tabs[n]
        #if self.tabs[current] == 'Ebuild File':
            #pass
            #need to reload all other pages based on changes. Ugh.
        #else:
            #pass
        event.Skip()

    def OnPageChanged(self, event):
        """Catch event when page in notebook is changed"""
        #n = self.nb.GetSelection()
        # If we switch to ebuild file editor, reload it with changes made in other tabs
        #if self.tabs[n] == 'Ebuild File':
            #WriteEbuild(self)
            #self.ebuildfile.editorCtrl.SetText(open(self.filename, 'r').read())
            #pass
        #print "Page - %s" % n
        #print "Tab - %s" % self.tabs[n]
        event.Skip()

    def OnMnuEclassCVS(self, event):
        """Add Python distutils-related variables, inherit etc."""
        print "Adding CVS skel\n"
        if not self.editing:
            return
        self.write("Adding CVS skel\n")
        EclassCVS(self)

    def OnMnuEclassDistutils(self, event):
        """Add CVS-related variables, inherit etc."""
        if not self.editing:
            return
        EclassDistutils(self)

    def OnMnuEclassGames(self, event):
        """Add games.eclass inherit, default funcs"""
        if not self.editing:
            return
        EclassGames(self)

    def OnMnuNewFunction(self, event):
        """Dialog to add new function"""
        if not self.editing:
            return
        #from NewFuncDialog import wxDialog1
        dlg = dialogs.NewFunction(self)
        dlg.CenterOnScreen()
        val = dlg.ShowModal()
        if val == wxID_OK:
            func, val = dlg.GetFunc()
            self.AddFunc(func, val)
        self.saved = 0
        dlg.Destroy()

    def NewPage(self, panel, name):
        self.nb.AddPage(panel, name)
        self.tabs.append(name)
        #self.tabsInstance.append(panel)
        #print self.tabsInstance
        #print self.tabs

    def AddFunc(self, newFunction, val):
        """Add page in notebook for a new function"""
        n = panels.NewFunction(self.nb, self.sb, self.pref)
        self.funcList.append(n)
        self.NewPage(n, newFunction)
        n.edNewFun.SetText(val)
        n.edNewFun.SetSavePoint()
        self.nb.SetSelection(self.nb.GetPageCount() -1)

    def OnMnuDelFunction(self, event):
        """Remove current function page"""
        #TODO: This removes any page, change to only move functions.
        p = self.nb.GetSelection()
        check = self.nb.GetPage(p)
        n = 0
        for f in self.funcList:
            if f == check:
                self.nb.SetSelection(p-1)
                self.nb.RemovePage(p)
                del self.tabs[p]
                x,y  = self.GetSize()
                self.SetSize(wxSize(x+1, y))
                break
            n += 1
        del self.funcList[n]
        self.saved = 0

    def AddEditor(self, name, val):
        """Add page in notebook for an editor"""
        n = panels.Editor(self.nb, self.sb, self.pref)
        if name == 'Output':
            self.ebuildfile = n
        #self.nb.AddPage(n, name)
        self.NewPage(n, name)
        n.editorCtrl.SetText(val)
        #self.nb.SetSelection(self.nb.GetPageCount() -1)

    def OnMnuHelpRef(self, event):
        """Display html help file"""
        os.system(self.pref['browser'] + " 'http://abeni.sf.net/docs/ebuild-quick-reference.html' &")

    def OnMnuHelp(self, event):
        """Display html help file"""
        #TODO:
        #Add: PORTDIR/profiles/use.desc
        os.system(self.pref['browser'] + " 'http://abeni.sf.net/docs/index.html' &")

    def OnMnuSave(self, event):
        """Save ebuild file to disk"""
        if not self.editing:
            return
        self.SaveEbuild()

    def SaveEbuild(self):
        msg = self.checkEntries()
        if not msg:
            defaultVars = getDefaultVars(self)
            WriteEbuild(self)
            self.saved = 1
            return 1
        else:
            dlg = wxMessageDialog(self, msg, 'Abeni: Error Saving', wxOK | wxICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
            return 0

    def checkEntries(self):
        """Validate entries on forms"""
        # We're checking category and license now.
        # TODO: Do sanity checking, like package, ebuild name ($P, $EBUILD)
        category = self.panelMain.Category.GetValue()
        categoryDir = self.GetCategory()
        valid_cat = os.path.join(portdir, category)
        if categoryDir == portdir_overlay + '/':
            msg = "You must specify a category."
            return msg
        if not os.path.exists(valid_cat):
            msg = category + " isn't a valid category."
            return msg
        l = self.panelMain.Category.GetValue()
        if not l:
            msg = "You must specify a license."
            return msg
        return 0

    def OnMnuNew(self,event):
        """Creates a new ebuild from scratch"""
        #TODO:
        # Show dialog if URI isn't properly formed or can't determine package, filename, ebuild name
        if not self.VerifySaved():
            win = dialogs.GetURIDialog(self, -1, "Enter Package URI", \
                                size=wxSize(350, 200), \
                                style = wxDEFAULT_DIALOG_STYLE \
                                )
            win.CenterOnScreen()
            val = win.ShowModal()
            self.URI = win.URI.GetValue()
            if self.URI == 'http://' or self.URI == '':
                return
            if val == wxID_OK and self.URI:
                self.ClearNotebook()
                self.AddPages()
                if self.pref['log'] == 'tab':
                    self.LogTab()
                self.panelMain.PopulateDefault()
                self.write(self.URI)
                if self.URI == "CVS" or self.URI == "cvs":
                    #self.panelMain.SetURI("package-cvs-0.0.1")
                    self.panelMain.SetName("package-cvs-0.0.1")
                else:
                    if self.URI.find('sourceforge') != -1:
                        #http://umn.dl.sourceforge.net/sourceforge/tikiwiki/tiki161.zip
                        #mirror://sourceforge/tikiwiki/tiki161.ip
                        #a = urlparse.urlparse("http://umn.dl.sourceforge.net/sourceforge/tikiwiki/tiki161.zip")
                        #('http', 'umn.dl.sourceforge.net', '/sourceforge/tikiwiki/tiki161.zip', '', '', '')
                        a = urlparse.urlparse(self.URI)
                        self.URI='mirror:/%s' % a[2]
                    self.panelMain.SetURI(self.URI)
                    self.panelMain.SetName(self.URI)
                self.panelMain.SetPackage()
                if self.URI.find('sourceforge') != -1:
                    self.panelMain.Homepage.SetValue('"http://%s.sourceforge.net/"' % self.panelMain.GetPackage().lower())
                self.panelChangelog.Populate("%s/skel.ChangeLog" % portdir, portdir)
                self.editing = 1
                self.saved = 0
                if self.URI == "CVS" or self.URI == "cvs":
                    self.OnMnuEclassCVS(-1)
                self.SetTitle(self.panelMain.GetEbuildName() + " | Abeni " + __version__)
                if self.pref['log'] == 'tab':
                    self.nb.SetSelection(1)

    def AddPages(self):
        """Add pages to blank notebook"""
        self.panelMain=panels.main(self.nb, self.sb, self.pref)
        self.panelDepend=panels.depend(self.nb)
        self.panelChangelog=panels.changelog(self.nb)
        self.NewPage(self.panelMain, "Main")
        self.NewPage(self.panelDepend, "Dependencies")
        self.NewPage(self.panelChangelog, "ChangeLog")

    def OnClose(self, event):
        """Called when trying to close application"""
        #TODO: Give yes/no quit dialog.
        if self.running:
            self.write("You're executing %s" % self.running)
            return

        if not self.VerifySaved():
            bookmarks = os.path.expanduser('~/.abeni/recent.txt')
            f = open(bookmarks, 'w')
            for ebuild in self.recentList:
                if ebuild != '\n':
                    l = string.strip(ebuild)
                    f.write(l + '\n')
            f.close()
            print "Exited safely."
            self.Destroy()

    def OnMnuExit(self,event):
        """Exits and closes application"""
        self.OnClose(-1)

    def OnMnuPref(self, event):
        """Modify preferences"""
        win = dialogs.Preferences(self, -1, "Preferences", \
                                size=wxSize(350, 200), \
                                style = wxDEFAULT_DIALOG_STYLE \
                                )
        win.CenterOnScreen()
        val = win.ShowModal()
        if val == wxID_OK:
            self.pref['browser'] = win.browser.GetValue()
            self.pref['xterm'] = win.xterm.GetValue()
            self.pref['diff'] = win.diff.GetValue()
            self.pref['editor'] = win.editor.GetValue()
            self.pref['autoTabs'] = win.autoTabs.GetValue()
            self.pref['fileBrowser'] = win.fileBrowser.GetValue()
            self.pref['use'] = win.use.GetValue()
            self.pref['features'] = win.features.GetValue()
            self.pref['log'] = win.log.GetValue()
            f = open(os.path.expanduser('~/.abeni/abenirc'), 'w')
            f.write('browser = %s\n' % self.pref['browser'])
            f.write('xterm = %s\n' % self.pref['xterm'])
            f.write('diff = %s\n' % self.pref['diff'])
            f.write('editor = %s\n' % self.pref['editor'])
            f.write('autoTabs = %s\n' % self.pref['autoTabs'])
            f.write('fileBrowser = %s\n' % self.pref['fileBrowser'])
            f.write('use = %s\n' % self.pref['use'])
            f.write('features = %s\n' % self.pref['features'])
            f.write('log = %s\n' % self.pref['log'])
            f.close()

    def OnMnuAbout(self,event):
        """Obligitory About me and my app screen"""
        dlg = wxMessageDialog(self, 'Abeni ' + __version__ + ' is a Python and wxPython application\n' +
                                'by Rob Cakebread released under the GPL license.\n\n', \
                                'About Abeni ' + __version__, wxOK | wxICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def GetCategory(self):
        """Return category of ebuild"""
        categoryDir = os.path.join (portdir_overlay, self.panelMain.Category.GetValue())
        return categoryDir

    def isDefault(self, var):
        """ Return 1 if varibale is in list of default ebuild variables"""
        for l in defaults:
            if var == l:
                return 1

    def LoadByPackage(self, f):
        """Offer list of ebuilds when given a package or filename on command line"""
        ebuilds = []
        if string.find(f, '/') == -1:
            s = 'etcat -v "^%s$"' % f
        else:
            s = 'etcat -v %s' % f
        for l in os.popen(s).readlines():
            if l[0:9] == '        [':
                l = l.strip()
                l = l[6:]
                ebuilds.append(l)
        if len(ebuilds):
            dlg = wxSingleChoiceDialog(self, 'Choose an ebuild:', 'Ebuilds Available',
                        ebuilds, wxOK|wxCANCEL)
            if dlg.ShowModal() == wxID_OK:
                s = dlg.GetStringSelection()
                s = string.split(s, ' ')
                if len(s) == 3:
                    overlay = 1
                else:
                    overlay = 0
                cat = string.split(s[0], '/')[0]
                package = string.split(s[0], '/')[1]
                if overlay:
                    if string.find(f, '/') == -1:
                        fname = '%s/%s/%s/%s.ebuild' % (portdir_overlay, cat, f, package)
                    else:
                        fname = '%s/%s/%s.ebuild' % (portdir_overlay, f, package)
                else:
                    if string.find(f, '/') == -1:
                        fname = '%s/%s/%s/%s.ebuild' % (portdir, cat, f, package)
                    else:
                        fname = '%s/%s/%s.ebuild' % (portdir, f, package)
                if os.path.exists(fname):
                    LoadEbuild(self, fname, __version__, portdir)
                else:
                    print "Error: Can't load %s" % fname
            dlg.Destroy()
        else:
            print "Package " + f + " not found. Be sure to use full package name."

    def OnMnuViewMakefile(self, event):
        """Show Makefile in editor window"""
        #We can't read ${WORKDIR} as non-root, so we have to copy the file and change permissions.
        if not self.editing:
            return
        p = self.panelMain.EbuildFile.GetValue()[:-7]
        s = '%s/portage/%s/work/%s/Makefile' % (portage_tmpdir, p, p)
        try:
            os.system('sudo cp %s /tmp/Makefile 2> /dev/null' % s)
            os.system('sudo chmod a+r /tmp/Makefile 2> /dev/null')
        except:
            pass
        # Example: /var/tmp/portage/zinf-2.2.3/work/zinf-2.2.3/configure
        if os.path.exists('/tmp/Makefile'):
            self.ViewMakefile()
        else:
            dlg = wxMessageDialog(self, 'You need to create a digest and unpack the package first\n\nThis can be done from the Tools menu.',
                          'Error', wxOK | wxICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()

    def ViewMakefile(self):
        """Show Makefile in editor window"""
        #We can't read ${WORKDIR} as non-root, so we have to copy the file and change permissions.
        p = self.panelMain.EbuildFile.GetValue()[:-7]
        s = '%s/portage/%s/work/%s/Makefile' % (portage_tmpdir, p, p)
        os.system('sudo cp %s /tmp/Makefile 2> /dev/null' % s)
        os.system('sudo chmod a+r /tmp/Makefile 2> /dev/null')
        # Example: /var/tmp/portage/zinf-2.2.3/work/zinf-2.2.3/configure
        if os.path.exists('/tmp/Makefile'):
            try:
                self.nb.RemovePage(self.tabs.index('Makefile'))
                del self.tabs[self.tabs.index('Makefile')]
            except:
                pass
            self.AddEditor('Makefile', open('/tmp/Makefile', 'r').read())
            self.SetToNewPage()
            os.system('sudo rm /tmp/Makefile')

    """
    def ExploreWorkdir(self, event):
        #Show configure file in editor window
        # Gah. This won't work with sudo. ${WORKDIR} is locked.
        # Could spawn an xterm, do su -c filemanager
        # Feh. xterm su -c doesn't work with kfmclient
        if not self.editing:
            return
        p = self.panelMain.EbuildFile.GetValue()[:-7]
        s = '%s/portage/%s/work' % (portage_tmpdir, p)
        if os.path.exists(s):
            self.write('Warning: Running %s as root.' % self.pref['fileBrowser'])
            cmd = '%s -e "su -c %s %s &"' % (self.pref['xterm'], self.pref['fileBrowser'], s)
            self.write(s)
            self.write(cmd)
            os.system(cmd)
            #os.system('sudo %s %s &' % (self.pref['fileBrowser'], s))
        else:
            dlg = wxMessageDialog(self, 'You need to create a digest and unpack the package first\n\nThis can be done from the Tools menu.',
                          'Error', wxOK | wxICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
    """

    def GetEnvs(self):
        #if not self.CheckUnpacked():
            #return
        self.env = {}
        p = self.panelMain.EbuildFile.GetValue()[:-7]
        f = '%s/portage/%s/temp/environment' % (portage_tmpdir, p)
        if not os.path.exists(f):
            cmd = 'sudo /usr/sbin/ebuild %s setup' % self.filename
            self.write(cmd)
            #self.ExecuteInLog(cmd)
            os.system(cmd)
        lines = open(f, 'r').readlines()
        envVars = ['A', 'AA', 'AUTOCLEAN', 'BUILDDIR', 'BUILD_PREFIX', \
                'D', 'DESTTREE', 'EBUILD', 'FEATURES', 'FILESDIR', \
                'INHERITED', 'KV', 'KVERS', 'O', 'P', 'PF', 'PN', 'PV', \
                'PVR', 'RESTRICT', 'S', 'SRC_URI', 'T', 'WORKDIR']
        for l in lines:
            if "=" in l:
                s = string.split(l, '=')
                var = s[0]
                val = s[1]
                if var in envVars:
                    self.env[var] = val.strip()

    def OnMnuViewConfigure(self, event):
        """Show configure file in editor window"""
        #We can't read ${WORKDIR} as non-root, so we have to copy the file and change permissions.
        if not self.editing:
            return
        if not self.CheckUnpacked():
            dlg = wxMessageDialog(self, 'You need to unpack the package first\n\nThis can be done from the Tools menu.',
                          'Error', wxOK | wxICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()

        p = self.panelMain.EbuildFile.GetValue()[:-7]
            #TODO: Need to get ${S}
        s = '%s/portage/%s/work/%s/configure' % (portage_tmpdir, p, p)
        try:
            os.system('sudo cp %s /tmp/configure 2> /dev/null' % s)
            os.system('sudo chmod a+r /tmp/configure 2> /dev/null')
        except:
            pass
        # Example: /var/tmp/portage/zinf-2.2.3/work/zinf-2.2.3/configure
        if os.path.exists('/tmp/configure'):
            self.ViewConfigure()
        else:
            dlg = wxMessageDialog(self, 'You need to create a digest and unpack the package first\n\nThis can be done from the Tools menu.',
                          'Error', wxOK | wxICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()

    def CheckUnpacked(self):
        p = self.panelMain.GetPackage()
        if os.path.exists('%s/portage/%s/.unpacked' % (portage_tmpdir, p)):
            return 1

    #TODO: Errr. I see a pattern here.
    def OnToolbarUnpack(self, event):
        if self.editing:
            if self.SaveEbuild():
                self.write("Unpacking %s " % self.filename)
                self.action = 'unpack'
                self.ExecuteInLog("sudo /usr/sbin/ebuild %s unpack" % self.filename)

    def OnToolbarCompile(self, event):
        if self.editing:
            if self.SaveEbuild():
                self.write("Compiling %s " % self.filename)
                self.ExecuteInLog("sudo /usr/sbin/ebuild %s compile" % self.filename)

    def OnToolbarInstall(self, event):
        if self.editing:
            if self.SaveEbuild():
                self.write("Installing %s " % self.filename)
                self.ExecuteInLog("sudo /usr/sbin/ebuild %s install" % self.filename)


    def OnMnuViewSetuppy(self, event):
        """Show setuppy file in editor window"""
        #We can't read ${WORKDIR} as non-root, so we have to copy the file and change permissions.
        if not self.editing:
            return
        if not self.CheckUnpacked():
            dlg = wxMessageDialog(self, 'You need to unpack the package first.\n\nThis can be done from the Tools menu.',
                        'Error', wxOK | wxICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
            return

        p = self.panelMain.EbuildFile.GetValue()[:-7]
        s = '%s/portage/%s/work/%s/setup.py' % (portage_tmpdir, p, p)
        try:
            os.system('sudo cp %s /tmp/setup.py 2> /dev/null' % s)
            os.system('sudo chmod a+r /tmp/setup.py 2> /dev/null')
        except:
            pass
        # Example: /var/tmp/portage/zinf-2.2.3/work/zinf-2.2.3/setup.py
        if os.path.exists('/tmp/setup.py'):
            self.ViewSetuppy()
        else:
            if not os.path.exists('%s/portage/%s/.unpack' % (portage_tmpdir, self.package)):
                dlg = wxMessageDialog(self, ('There is no setup.py: %s ' % s),
                          'Error', wxOK | wxICON_INFORMATION)
                dlg.ShowModal()
                dlg.Destroy()

    def ViewSetuppy(self):
        """Show setup.py file in editor window"""
        #We can't read ${WORKDIR} as non-root, so we have to copy the file and change permissions.
        p = self.panelMain.EbuildFile.GetValue()[:-7]
        s = '%s/portage/%s/work/%s/setup.py' % (portage_tmpdir, p, p)
        try:
            os.system('sudo cp %s /tmp/setup.py 2> null' % s)
            os.system('sudo chmod a+r /tmp/setup.py 2> null')
        except:
            pass
        # Example: /var/tmp/portage/zinf-2.2.3/work/zinf-2.2.3/configure
        if os.path.exists('/tmp/setup.py'):
            try:
                self.nb.RemovePage(self.tabs.index('setup.py'))
                del self.tabs[self.tabs.index('setup.py')]
            except:
                pass
            self.AddEditor('setup.py', open('/tmp/setup.py', 'r').read())
            self.SetToNewPage()
            os.system('sudo rm /tmp/setup.py')

    def ViewConfigure(self):
        """Show configure file in editor window"""
        #We can't read ${WORKDIR} as non-root, so we have to copy the file and change permissions.
        p = self.panelMain.EbuildFile.GetValue()[:-7]
        s = '%s/portage/%s/work/%s/configure' % (portage_tmpdir, p, p)
        try:
            os.system('sudo cp %s /tmp/configure 2> null' % s)
            os.system('sudo chmod a+r /tmp/configure 2> null')
        except:
            pass
        # Example: /var/tmp/portage/zinf-2.2.3/work/zinf-2.2.3/configure
        if os.path.exists('/tmp/configure'):
            try:
                self.nb.RemovePage(self.tabs.index('configure'))
                del self.tabs[self.tabs.index('configure')]
            except:
                pass
            self.AddEditor('configure', open('/tmp/configure', 'r').read())
            self.SetToNewPage()
            os.system('sudo rm /tmp/configure')

    def OnMnuViewEnvironment(self, event):
        """Show environment file in editor window"""
        if not self.editing:
            return
        #p = self.panelMain.EbuildFile.GetValue()[:-7]
        #f = '%s/portage/%s/temp/environment' % (portage_tmpdir, p)
        # Example: /var/tmp/portage/pysnmp-2.0.8/temp/environment
        #if os.path.exists(f):
        self.ViewEnvironment()
        #else:
        #    dlg = wxMessageDialog(self, 'You need to create a digest and unpack the package first.\n\nThis can be done from the Tools menu.',
        #                  'Error', wxOK | wxICON_INFORMATION)
        #    dlg.ShowModal()
        #    dlg.Destroy()

    def ViewEnvironment(self):
        """Show environment file in editor window"""
        #TODO: This is brief version, the commented out line below gives full environment.
        #Add config option to show either, or menu option. Or both.
        self.GetEnvs()
        txt = ''
        keys = self.env.keys()
        keys.sort()
        for k in keys:
            txt += '%s=%s\n' % (k, self.env[k])
        p = self.panelMain.EbuildFile.GetValue()[:-7]
        f = '%s/portage/%s/temp/environment' % (portage_tmpdir, p)
        if os.path.exists(f):
            try:
                self.nb.RemovePage(self.tabs.index('Environment'))
                del self.tabs[self.tabs.index('Environment')]
            except:
                pass
            #self.AddEditor('Environment', open(f, 'r').read())
            self.AddEditor('Environment', txt)
            self.SetToNewPage()

    def SetToNewPage(self):
        self.nb.SetSelection(self.nb.GetPageCount() -1)

class MyLog(wxPyLog):
    def __init__(self, textCtrl, logTime=0):
        wxPyLog.__init__(self)
        self.tc = textCtrl
        self.logTime = logTime

    def DoLogString(self, message, timeStamp):
        if self.logTime:
            message = time.strftime("%X", time.localtime(timeStamp)) + \
                      ": " + message
        if self.tc:
            self.tc.AppendText(message + '\n')

class MyApp(wxPySimpleApp):

    """ Main wxPython app class """

    def OnInit(self):
        """Set up the main frame"""
        # Enable gif, jpg, bmp, png handling for wxHtml and icons
        wxInitAllImageHandlers()
        frame=MyFrame(None, -1, 'Abeni - The ebuild Builder ' + __version__)
        frame.Show(true)
        self.SetTopWindow(frame)
        return true


app=MyApp(0)
app.MainLoop()

