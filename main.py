#!/usr/bin/python

"""Abeni - Gentoo Linux Ebuild Integrated Development Environment
"""

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

# Author: Rob Cakebread
# email : pythonhead@gentoo.org
# ChangeLog : http://abeni.sourceforge.net/ChangeLog


import sys
import os
import shutil

import wxversion
wxversion.select("2.5")
import wx

from MyFrame import MyFrame
import utils


def gentoo_sanity_check():
    """Make sure we have a working portage system"""

    portdir_overlay = utils.get_portdir_overlay()
    if portdir_overlay[-1] == "/":
        portdir_overlay = portdir_overlay[:-1]

    #Exit if they don't have PORTDIR_OVERLAY defined in /etc/make.conf
    # or if defined but directory doesn't exist.
    #TODO: Pop up a dialog instead with utils.my_message
    if not os.path.exists(portdir_overlay):
        print "ERROR: You must define PORTDIR_OVERLAY in your /etc/make.conf"
        print "You can simply uncomment this line:"
        print "#PORTDIR_OVERLAY='/usr/local/portage'"
        print "Then: mkdir /usr/local/portage"
        sys.exit(1)
    if not portdir_overlay:
        print "ERROR: Create the directory PORTDIR_OVERLAY in /etc/make.conf"
        sys.exit(1)


class MyApp(wx.App):

    """ Main wxPython app class """

    def OnInit(self):
        """Display main frame"""
        from __version__ import version
        # Enable gif, jpg, bmp, png handling for wxHtml and icons
        wx.InitAllImageHandlers()
        self.frame=MyFrame(None,-1, "Abeni - The ebuild Builder " + \
                           version)
        self.frame.Show(True)
        self.SetTopWindow(self.frame)
        return True

gentoo_sanity_check()
app=MyApp(0)
app.MainLoop()
