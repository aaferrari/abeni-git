#!/usr/bin/python2.2
# Copyright 1999-2003 Gentoo Technologies, Inc.
# Distributed under the terms of the GNU General Public License v2
# $Header: /cvsroot/abeni/abeni/bin/Attic/repoman-safe.py,v 1.2 2003/07/31 14:32:55 robc Exp $

# Next to do: dep syntax checking in mask files
# Then, check to make sure deps are satisfiable (to avoid "can't find match for" problems)
# that last one is tricky because multiple profiles need to be checked.

import os
os.environ["PORTAGE_CALLER"]="repoman"

import sys,string,signal,readline,portage,re,cvstree
from output import *

for p in sys.path:
    if os.path.basename(p) == 'site-packages':
        modulePath = "%s/abeni" % p
sys.path.append(modulePath)

from  nulloutput import *
from commands import getstatusoutput

exename=os.path.basename(sys.argv[0])
version="1.3"

def err(txt):
	print exename+": "+txt
	sys.exit(1)

def exithandler(signum=None,frame=None):
	sys.stderr.write("\n"+exename+": Interrupted; exiting...\n")
	sys.exit(1)
	os.kill(0,signal.SIGKILL)
signal.signal(signal.SIGINT,exithandler)

REPOROOTS=["gentoo-x86"]
modes=["scan","fix","full","help","commit"]
shortmodes={"ci":"commit"}
modeshelp={
"scan"  :"Scan current directory tree for QA issues (default)",
"fix"   :"Fix those issues that can be fixed (stray digests, missing digests)",
"full"  :"Scan current directory tree for QA issues (full listing)",
"help"  :"Show this screen",
"commit":"Scan current directory tree for QA issues; if OK, commit via cvs"
}
options=["--pretend","--help","--commitmsg","--commitmsgfile","--verbose"]
shortoptions={"-m":"--commitmsg","-M":"--commitmsgfile","-p":"--pretend","-v":"--verbose"}
optionshelp={
"--pretend":"Don't actually perform commit or fix steps; just show what would be done (always enabled when not started in a CVS tree).",
"--help"   :"Show this screen",
"--commitmsg"    :"Adds a commit message via the command line.",
"--commitmsgfile":"Adds a commit message from a file given on the command line.",
"--verbose":"Displays every package name while checking"
}
qacats=[
"digest.stray","digest.missing",
"ebuild.invalidname","ebuild.namenomatch",
"changelog.missing",
"changelog.notadded","ebuild.notadded","digest.notadded",
"ebuild.disjointed","digest.disjointed",
"DEPEND.bad","RDEPEND.bad",
"DEPEND.badmasked","RDEPEND.badmasked",
"ebuild.syntax","ebuild.output",
"ebuild.nesteddie","LICENSE.invalid",
"IUSE.invalid","KEYWORDS.invalid",
"ebuild.nostable","ebuild.allmasked"
]
qawarnings=[
"changelog.missing",
"changelog.notadded",
"ebuild.notadded",
"ebuild.nostable",
"ebuild.allmasked",
"digest.notadded",
"digest.disjointed",
"digest.missing",
"DEPEND.badmasked",
"RDEPEND.badmasked",
"IUSE.invalid"
]
missingvars=["KEYWORDS","LICENSE","DESCRIPTION","SLOT"]
allvars=portage.auxdbkeys
commitmessage=None
commitmessagefile=None
for x in missingvars:
	qacats.append(x+".missing")
	qawarnings.append(x+".missing")
qahelp={
	"digest.stray":"Digest files that do not have a corresponding ebuild",
	"digest.missing":"Digest files that are missing (ebuild exists, digest doesn't)",
	"ebuild.invalidname":"Ebuild files with a non-parseable or syntactically incorrect name",
	"ebuild.namenomatch":"Ebuild files that do not have the same name as their parent directory",
	"changelog.missing":"Missing ChangeLog files",
	"ebuild.disjointed":"Ebuilds not added to cvs when the matching digest has been added",
	"digest.disjointed":"Digests not added to cvs when the matching ebuild has been added",
	"digest.notadded":"Digests that exist but have not been added to cvs",
	"ebuild.notadded":"Ebuilds that exist but have not been added to cvs",
	"changelog.notadded":"ChangeLogs that exist but have not been added to cvs",
	"KEYWORDS.missing":"Ebuilds that have a missing KEYWORDS variable",
	"LICENSE.missing":"Ebuilds that have a missing LICENSE variable",
	"DESCRIPTION.missing":"Ebuilds that have a missing DESCRIPTION variable",
	"SLOT.missing":"Ebuilds that have a missing SLOT variable",
	"DEPEND.bad":"User-visible ebuilds with bad DEPEND settings (matched against *visible* ebuilds)",
	"RDEPEND.bad":"User-visible ebuilds with bad RDEPEND settings (matched against *visible* ebuilds)",
	"DEPEND.badmasked":"Masked ebuilds with bad DEPEND settings (matched against *all* ebuilds)",
	"RDEPEND.badmasked":"Masked ebuilds with RDEPEND settings (matched against *all* ebuilds)",
	"ebuild.syntax":"Error generating cache entry for ebuild; typically caused by ebuild syntax error",
	"ebuild.output":"A simple sourcing of the ebuild produces output; this breaks ebuild policy.",
	"ebuild.nesteddie":"Placing 'die' inside ( ) prints an error, but doesn't stop the ebuild.",
	"IUSE.invalid":"This build has a variable in IUSE that is not in the use.desc or use.local.desc file",
	"LICENSE.invalid":"This ebuild is listing a license that doesnt exist in portages license/ dir.",
	"KEYWORDS.invalid":"This ebuild contains KEYWORDS that are not listed in profiles/keywords.desc",
	"ebuild.nostable":"There are no ebuilds that are marked as stable for your ARCH",
	"ebuild.allmasked":"All ebuilds are masked for this package"
}

def err(txt):
	print exename+": "+txt
	sys.exit(1)


ven_cat = r'[\w0-9-]+'                                 # Category
ven_nam = r'([+a-z0-9-]+(?:[+_a-z0-9-]*[+a-z0-9-]+)*)' # Name
ven_ver = r'((?:\d+\.)*\d+[a-z]?)'                     # Version
ven_suf = r'(_(alpha\d*|beta\d*|pre\d*|rc\d*|p\d+))?'  # Suffix
ven_rev = r'(-r\d+)?'                                  # Revision

ven_string=ven_cat+'/'+ven_nam+'-'+ven_ver+ven_suf+ven_rev
valid_ebuild_name_re=re.compile(ven_string+'$', re.I)
valid_ebuild_filename_re=re.compile(ven_string+'\.ebuild$', re.I)

def valid_ebuild_name(name):
	"""(name) --- Checks to ensure that the package name meets portage specs.
	Return 1 if valid, 0 if not."""
	# Handle either a path to the ebuild, or cat/pkg-ver string
	if (len(name) > 7) and (name[-7:] == ".ebuild"):
		if valid_ebuild_filename_re.match(name):
			return 1
	else:
		if valid_ebuild_name_re.match(name):
			return 1
	return 0


def help():
	print
	print green(exename+" "+version)
	print " \"Quality is job zero.\""
	print " Copyright 1999-2003 Gentoo Technologies, Inc."
	print " Distributed under the terms of the GNU General Public License v2"
	print
	print bold(" Usage:"),turquoise(exename),"[",green("option"),"] [",green("mode"),"]"
	print bold(" Modes:"),turquoise("scan (default)"),
	for x in modes[1:]:
		print "|",turquoise(x),
	print "\n"
	print " "+green(string.ljust("Option",20)+" Description")
	for x in options:
		print " "+string.ljust(x,20),optionshelp[x]
	print
	print " "+green(string.ljust("Mode",20)+" Description")
	for x in modes:
		print " "+string.ljust(x,20),modeshelp[x]
	print
	print " "+green(string.ljust("QA keyword",20)+" Description")
	for x in qacats:
		print " "+string.ljust(x,20),qahelp[x]
	print
	sys.exit(1)


mymode=None
myoptions=[]
if len(sys.argv)>1:
	x=1
	while x < len(sys.argv):
		if sys.argv[x] in shortmodes.keys():
			sys.argv[x]=shortmodes[sys.argv[x]]
		if sys.argv[x] in modes:
			if mymode==None:
				mymode=sys.argv[x]
			else:
				err("Please specify either \""+mymode+"\" or \""+sys.argv[x]+"\", but not both.")
		elif sys.argv[x] in options+shortoptions.keys():
			optionx=sys.argv[x]
			if optionx in shortoptions.keys():
				optionx = shortoptions[optionx]
			if (optionx=="--commitmsg") and (len(sys.argv)>=(x+1)):
				commitmessage=sys.argv[x+1]
				x=x+1
			elif (optionx=="--commitmsgfile") and (len(sys.argv)>=(x+1)):
				commitmessagefile=sys.argv[x+1]
				x=x+1
			elif optionx not in myoptions:
				myoptions.append(optionx)
		else:
			err("\""+sys.argv[x]+"\" is not a valid mode or option.")
		x=x+1
if mymode==None:
	mymode="scan"
if mymode=="help" or ("--help" in myoptions):
	help()

if portage.settings["PORTDIR"][-1]!="/":
	portage.settings["PORTDIR"]=portage.settings["PORTDIR"]+"/"
if portage.settings["PORTDIR_OVERLAY"][-1]!="/":
	portage.settings["PORTDIR_OVERLAY"]=portage.settings["PORTDIR_OVERLAY"]+"/"

isCvs=False
isOverlay=False

mydir=os.getcwd()
if mydir[-1] != "/":
	mydir=mydir + "/"
if mydir[:len(portage.settings["PORTDIR_OVERLAY"])] == portage.settings["PORTDIR_OVERLAY"]:
	myreporoot=os.getcwd();
	myreporootpath=portage.settings["PORTDIR_OVERLAY"]
	isOverlay=True
elif mydir[:len(portage.settings["PORTDIR"])] == portage.settings["PORTDIR"]:
	myreporoot=os.getcwd();
	myreporootpath=portage.settings["PORTDIR"]
elif not os.path.isdir("CVS"):
	err("We do not appear to be inside a local repository or a portage tree. Exiting.")
else:
	try:
		isCvs=True
		myrepofile=open("CVS/Repository")
		myreporoot=myrepofile.readline()[:-1]
		myrepofile.close()
		myrepofile=open("CVS/Root")
		myreporootpath=string.split(myrepofile.readline()[:-1], ":")[-1]
		myrepofile.close()
	except:
		err("Error grabbing repository information; exiting.")

if not "--pretend" in myoptions and not isCvs:
	print
	print darkgreen("not in a CVS repository, enabling pretend mode")
	myoptions.append("--pretend");

if myreporootpath=="/space/cvsroot":
	print
	print
	print red("You're using the wrong cvsroot. For Manifests to be correct, you must")
	print red("use the same base cvsroot path that the servers use. Please try the")
	print red("following script to remedy this:")
	print
	print "cd my_cvs_tree"
	print
	print "rm -Rf [a-z]*"
	print "cvs up"
	print
	print "find ./ -type f -regex '.*/CVS/Root$' -print0 | xargs -0r sed \\"
	print "  -i 's:/space/cvsroot$:/home/cvsroot:'"
	print
	print red("You must clear and re-update your tree as all header tags will cause")
	print red("problems in manifests for all rsync and /home/cvsroot users.")
	print
	print "You should do this to any other gentoo trees your have as well,"
	print "excluding the deletions. 'gentoo-src' should be /home/cvsroot."
	print
	sys.exit(123)

os.environ["PORTAGE_CALLER"]="repoman"
os.environ["ACCEPT_KEYWORDS"]="-~"+portage.settings["ARCH"]
if isCvs:
	os.environ["FEATURES"]=portage.settings["FEATURES"]+" cvs"
reload(portage)

try: # Determine if we're in PORTDIR... If not tell portage to accomodate.
	mydir=os.getcwd()
	if portage.settings["PORTDIR"]!=mydir[:len(portage.settings["PORTDIR"])]:
		# We're not in the PORTDIR
		print
		#print darkred("We're not in PORTDIR..."),
		while mydir!="/":
			if os.path.exists(mydir+"/profiles/package.mask"):
				# mydir == a PORTDIR root... We make PORTDIR = mydir.
				print darkgreen("setting to:")+" "+bold(mydir)
				os.environ["PORTDIR"]=mydir
				break;
			else:
				mydir=os.path.normpath(mydir+"/..")
		if mydir=="/":
			print

except Exception, e:
	print "!!! Error when determining valid(ity of) PORTDIR:"
	print "!!!",e
	pass

if isCvs:
	reporoot=None
	for x in REPOROOTS:
		if myreporoot[0:len(x)]==x:
			reporoot=myreporoot
	if not reporoot:
		err("Couldn't recognize repository type.  Supported repositories:\n"+repr(REPOROOTS))
reposplit=string.split(myreporoot,"/")
repolevel=len(reposplit)

if not isCvs:
	repolevel-=(string.count(myreporootpath,"/") - 1)
startdir=os.getcwd()

for x in range(0,repolevel-1):
	os.chdir("..")
repodir=os.getcwd()
os.chdir(startdir)

def caterror(mycat):
	err(mycat+" is not an official category.  Skipping QA checks in this directory.\nPlease ensure that you add "+catdir+" to "+repodir+"/profiles/categories\nif it is a new category.")
print
if "--pretend" in myoptions:
	print green("RepoMan pretends to scour the neighborhood...")
else:
	print green("RepoMan scours the neighborhood...")

# retreive local USE list
luselist=[]
try:
	mylist=portage.grabfile(portage.settings["PORTDIR"]+"/profiles/use.local.desc")
	for mypos in range(0,len(mylist)):
		mysplit=mylist[mypos].split()[0]
		myuse=string.split(mysplit,":")
		if len(myuse)==2:
			luselist.append(myuse[1])
except:
	err("Couldn't read from use.local.desc")

# setup a uselist from portage
uselist=[]
try:
	uselist=portage.grabfile(portage.settings["PORTDIR"]+"/profiles/use.desc")
	for l in range(0,len(uselist)):
		uselist[l]=string.split(uselist[l])[0]
except:
	err("Couldn't read USE flags from use.desc")

uselist=uselist+luselist

# retreive a list of current licenses in portage
liclist=portage.listdir(portage.settings["PORTDIR"]+"/licenses")
if not liclist:
	err("Couldn't find licenses?")

# retreive list of offiial keywords
try:
	kwlist=portage.grabfile(portage.settings["PORTDIR"]+"/profiles/keywords.desc")
except:
	err("Couldn't read KEYWORDS from keywords.desc")
if not kwlist:
	kwlist=["alpha","arm","hppa","mips","ppc","sparc","x86"]

scanlist=[]
if repolevel==2:
	#we are inside a category directory
	catdir=reposplit[-1]
	if catdir not in portage.categories:
		caterror(catdir)
	mydirlist=os.listdir(startdir)
	for x in mydirlist:
		if x=="CVS":
			continue
		if os.path.isdir(startdir+"/"+x):
			scanlist.append(catdir+"/"+x)
elif repolevel==1:
	for x in portage.categories:
		if not os.path.isdir(startdir+"/"+x):
			continue
		for y in os.listdir(startdir+"/"+x):
			if y=="CVS":
				continue
			if os.path.isdir(startdir+"/"+x+"/"+y):
				scanlist.append(x+"/"+y)
elif repolevel==3:
	catdir = reposplit[-2]
	if catdir not in portage.categories:
		caterror(catdir)
	scanlist.append(catdir+"/"+reposplit[-1])

stats={}
fails={}
#objsadded records all object being added to cvs
objsadded=[]
for x in qacats:
	stats[x]=0
	fails[x]=[]
for x in scanlist:
	#ebuilds and digests added to cvs respectively.
	if "--verbose" in myoptions:
		print "checking package " + x
	eadded=[]
	dadded=[]
	cladded=0
	catdir,pkgdir=x.split("/")
	checkdir=repodir+"/"+x
	checkdirlist=os.listdir(checkdir)
	ebuildlist=[]
	for y in checkdirlist:
		if y[-7:]==".ebuild":
			ebuildlist.append(y[:-7])
	digestlist=[]
	if isCvs:
		try:
			myf=open(checkdir+"/CVS/Entries","r")
			myl=myf.readlines()
			for l in myl:
				if l[0]!="/":
					continue
				splitl=l[1:].split("/")
				if not len(splitl):
					continue
				objsadded.append(splitl[0])
				if splitl[0][-7:]==".ebuild":
					eadded.append(splitl[0][:-7])
				if splitl[0]=="ChangeLog":
					cladded=1
		except IOError:
			continue

		try:
			myf=open(checkdir+"/files/CVS/Entries","r")
			myl=myf.readlines()
			for l in myl:
				if l[0]!="/":
					continue
				splitl=l[1:].split("/")
				if not len(splitl):
					continue
				objsadded.append(splitl[0])
				if splitl[0][:7]=="digest-":
					dadded.append(splitl[0][7:])
		except IOError:
			continue

	if os.path.exists(checkdir+"/files"):
		filesdirlist=os.listdir(checkdir+"/files")
		for y in filesdirlist:
			if y[:7]=="digest-":
				if y[7:] not in dadded:
					#digest not added to cvs
					stats["digest.notadded"]=stats["digest.notadded"]+1
					fails["digest.notadded"].append(x+"/files/"+y)
					if y[7:] in eadded:
						stats["digest.disjointed"]=stats["digest.disjointed"]+1
						fails["digest.disjointed"].append(x+"/files/"+y)
				if y[7:] not in ebuildlist:
					#stray digest
					if mymode=="fix":
						if "--pretend" in myoptions:
							print "(cd "+repodir+"/"+x+"/files; cvs rm -f "+y+")"
						else:
							os.system("(cd "+repodir+"/"+x+"/files; cvs rm -f "+y+")")
					else:
						stats["digest.stray"]=stats["digest.stray"]+1
						fails["digest.stray"].append(x+"/files/"+y)

	if "ChangeLog" not in checkdirlist:
		stats["changelog.missing"]+=1
		fails["changelog.missing"].append(x+"/ChangeLog")

	for y in ebuildlist:
		if y not in eadded:
			#ebuild not added to cvs
			stats["ebuild.notadded"]=stats["ebuild.notadded"]+1
			fails["ebuild.notadded"].append(x+"/"+y+".ebuild")
			if y in dadded:
				stats["ebuild.disjointed"]=stats["ebuild.disjointed"]+1
				fails["ebuild.disjointed"].append(x+"/"+y+".ebuild")
		if not os.path.exists(checkdir+"/files/digest-"+y):
			if mymode=="fix":
				if "--pretend" in myoptions:
					print "/usr/sbin/ebuild "+repodir+"/"+x+"/"+y+".ebuild digest"
				else:
					os.system("/usr/sbin/ebuild "+repodir+"/"+x+"/"+y+".ebuild digest")
			else:
				stats["digest.missing"]=stats["digest.missing"]+1
				fails["digest.missing"].append(x+"/files/digest-"+y)
		myesplit=portage.pkgsplit(y)
		if myesplit==None or not valid_ebuild_name(x.split("/")[0]+"/"+y):
			stats["ebuild.invalidname"]=stats["ebuild.invalidname"]+1
			fails["ebuild.invalidname"].append(x+"/"+y+".ebuild")
			continue
		elif myesplit[0]!=pkgdir:
			print pkgdir,myesplit[0]
			stats["ebuild.namenomatch"]=stats["ebuild.namenomatch"]+1
			fails["ebuild.namenomatch"].append(x+"/"+y+".ebuild")
			continue
		try:
			myaux=portage.db["/"]["porttree"].dbapi.aux_get(catdir+"/"+y,allvars,strict=1)
		except KeyError:
			stats["ebuild.syntax"]=stats["ebuild.syntax"]+1
			fails["ebuild.syntax"].append(x+"/"+y+".ebuild")
			continue
		except IOError:
			stats["ebuild.output"]=stats["ebuild.output"]+1
			fails["ebuild.output"].append(x+"/"+y+".ebuild")
			continue
		for pos in range(0,len(missingvars)):
			if portage.db["/"]["porttree"].dbapi.aux_get(catdir+"/"+y, [ missingvars[pos] ] )[0]=="":
				myqakey=missingvars[pos]+".missing"
				stats[myqakey]=stats[myqakey]+1
				fails[myqakey].append(x+"/"+y+".ebuild")
		if not catdir+"/"+y in portage.db["/"]["porttree"].dbapi.xmatch("list-visible",x):
			#we are testing deps for a masked package; give it some lee-way
			suffix="masked"
			matchmode="match-all"
		else:
			suffix=""
			matchmode="match-visible"
		for mytype,mypos in [["DEPEND",len(missingvars)],["RDEPEND",len(missingvars)+1]]:
			mykey=mytype+".bad"+suffix
			myvalue=string.join(portage.db["/"]["porttree"].dbapi.aux_get(catdir+"/"+y,[ mytype ]))
			mydep=portage.dep_check(myvalue,portage.db["/"]["porttree"].dbapi,use="all",mode=matchmode)
			if mydep[0]==1:
				if mydep[1]!=[]:
					#we have some unsolvable deps
					#remove ! deps, which always show up as unsatisfiable
					d=0
					while d<len(mydep[1]):
						if mydep[1][d][0]=="!":
							del mydep[1][d]
						else:
							d += 1
					#if we emptied out our list, continue:
					if not mydep[1]:
						continue
					stats[mykey]=stats[mykey]+1
					fails[mykey].append(x+"/"+y+".ebuild: "+repr(mydep[1]))
			else:
					stats[mykey]=stats[mykey]+1
					fails[mykey].append(x+"/"+y+".ebuild: "+repr(mydep[1]))
		if not os.system("egrep '\([^)]*\<die\>' "+checkdir+"/"+y+".ebuild >/dev/null 2>&1"):
			stats["ebuild.nesteddie"]=stats["ebuild.nesteddie"]+1
			fails["ebuild.nesteddie"].append(x+"/"+y+".ebuild")
		# uselist checks - global and local
		myuse=string.split(portage.db["/"]["porttree"].dbapi.aux_get(catdir+"/"+y,["IUSE"])[0])
		for mypos in range(0,len(myuse)):
			if myuse[mypos] and (myuse[mypos] not in uselist):
				stats["IUSE.invalid"]=stats["IUSE.invalid"]+1
				fails["IUSE.invalid"].append(x+"/"+y+".ebuild: %s" % myuse[mypos])
		#license checks
		myuse=string.split(portage.db["/"]["porttree"].dbapi.aux_get(catdir+"/"+y,["LICENSE"])[0])
		for mypos in range(0,len(myuse)):
			if not myuse[mypos] in liclist and myuse[mypos] != "|":
				stats["LICENSE.invalid"]=stats["LICENSE.invalid"]+1
				fails["LICENSE.invalid"].append(x+"/"+y+".ebuild: %s" % myuse[mypos])
		#keyword checks
		myuse=string.split(portage.db["/"]["porttree"].dbapi.aux_get(catdir+"/"+y,["KEYWORDS"])[0])
		for mykey in myuse:
			myskey=mykey[:]
			if myskey[0]=="-":
				myskey=myskey[1:]
			if myskey[0]=="~":
				myskey=myskey[1:]
			if (mykey!="-*") and (myskey not in kwlist):
				stats["KEYWORDS.invalid"]=stats["KEYWORDS.invalid"]+1
				fails["KEYWORDS.invalid"].append(x+"/"+y+".ebuild: %s" % mykey)

	# Check for 'all unstable' or 'all masked' -- ACCEPT_KEYWORDS is stripped
	# XXX -- Needs to be implemented in dep code. Can't determine ~arch nicely.
	#if not portage.portdb.xmatch("bestmatch-visible",x):
	#    stats["ebuild.nostable"]+=1
	#    fails["ebuild.nostable"].append(x)
	if not portage.portdb.xmatch("list-visible",x):
	    stats["ebuild.allmasked"]+=1
	    fails["ebuild.allmasked"].append(x)


print
#dofail will be set to 1 if we have failed in at least one non-warning category
dofail=0
#dowarn will be set to 1 if we tripped any warnings
dowarn=0
#dofull will be set if we should print a "repoman full" informational message
dofull=0
for x in qacats:
	if not isCvs and (string.find(x, "notadded") != -1 or string.find(x, "digest") != -1):
		stats[x] = 0
	if stats[x]:
		dowarn=1
		if x not in qawarnings:
			dofail=1
	else:
		if mymode!="full":
			continue
	print "  "+string.ljust(x,20),
	if stats[x]==0:
		print green(`stats[x]`)
		continue
	elif x in qawarnings:
		print yellow(`stats[x]`)
	else:
		print red(`stats[x]`)
	if mymode!="full":
		if stats[x]<12:
			for y in fails[x]:
				print "   "+y
		else:
			dofull=1
	else:
		for y in fails[x]:
			print "   "+y
print

def grouplist(mylist,seperator="/"):
	"""(list,seperator="/") -- Takes a list of elements; groups them into
	same initial element categories. Returns a dict of {base:[sublist]}
	From: ["blah/foo","spork/spatula","blah/weee/splat"]
	To:   {"blah":["foo","weee/splat"], "spork":["spatula"]}"""
	mygroups={}
	for x in mylist:
		xs=string.split(x,seperator)
		if xs[0]==".":
			xs=xs[1:]
		if xs[0] not in mygroups.keys():
			mygroups[xs[0]]=[string.join(xs[1:],seperator)]
		else:
			mygroups[xs[0]]+=[string.join(xs[1:],seperator)]
	return mygroups

if mymode!="commit":
	if dofull:
		print bold("Note: type \"repoman full\" for a complete listing.")
		print
	if dowarn and not dofail:
		print green("RepoMan sez:"),"\"You're only giving me a partial QA payment?\nI'll take it this time, but I'm not happy.\""
	elif not dofail:
		print green("RepoMan sez:"),"\"If everyone were like you, I'd be out of business!\""
	print
else:
	if dofail:
		print turquoise("Please fix these important QA issues first.")
		print green("RepoMan sez:"),"\"Make your QA payment on time and you'll never see the likes of me.\"\n"
		sys.exit(1)

	if "--pretend" in myoptions:
		print green("RepoMan sez:"), "\"So, you want to play it safe. Good call.\"\n"

	if fails["digest.missing"]:
		print green("Creating missing digests...")
	for x in fails["digest.missing"]:
		xs=string.split(x,"/")
		del xs[-2]
		myeb=string.join(xs[:-1],"/")+"/"+xs[-1][7:]
		if "--pretend" in myoptions:
			print "(ebuild "+portage.settings["PORTDIR"]+"/"+myeb+".ebuild digest)"
		else:
			os.system("ebuild "+portage.settings["PORTDIR"]+"/"+myeb+".ebuild digest")
	mycvstree=cvstree.getentries("./",recursive=1)
	if isCvs and not mycvstree:
		print "!!! It seems we don't have a cvs tree?"
		sys.exit(3)

	myunadded=cvstree.findunadded(mycvstree,recursive=1,basedir="./")
	myautoadd=[]
	if myunadded:
		for x in range(len(myunadded)-1,-1,-1):
			xs=string.split(myunadded[x],"/")
			if xs[-1]=="files":
				print "!!! files dir is not added! Please correct this."
				sys.exit(-1)
			elif xs[-1]=="Manifest":
				# It's a manifest... auto add
				myautoadd+=[myunadded[x]]
				del myunadded[x]
			elif len(xs[-1])>=7:
				if xs[-1][:7]=="digest-":
					del xs[-2]
					myeb=string.join(xs[:-1]+[xs[-1][7:]],"/")+".ebuild"
					if os.path.exists(myeb):
						# Ebuild exists for digest... So autoadd it.
						myautoadd+=[myunadded[x]]
						del myunadded[x]

	if myautoadd:
		print ">>> Auto-Adding missing digests..."
		if "--pretend" in myoptions:
			print "(/usr/bin/cvs add "+string.join(myautoadd)+")"
			retval=0
		else:
			retval=os.system("/usr/bin/cvs add "+string.join(myautoadd))
		if retval:
			print "!!! Exiting on cvs (shell) error code:",retval
			sys.exit(retval)

	if myunadded:
		print red("!!! The following files are in your cvs tree but are not added to the master")
		print red("!!! tree. Please remove them from the cvs tree or add them to the master tree.")
		for x in myunadded:
			print "   ",x
		print
		print
		sys.exit(1)

	mymissing=None
	if mymissing:
		print "The following files are obviously missing from your cvs tree"
		print "and are being fetched so we can continue:"
		for x in mymissing:
			print "   ",x
		if "--pretend" in myoptions:
			print "(/usr/bin/cvs -q up "+string.join(mymissing)+")"
			retval=0
		else:
			retval=os.system("/usr/bin/cvs -q up "+string.join(mymissing))
		if retval:
			print "!!! Exiting on cvs (shell) error code:",retval
			sys.exit(retval)
		del mymissing

	retval=["",""]
	if isCvs:
		print "Performing a "+green("cvs -n up")+" with a little magic grep to check for updates."
		retval=getstatusoutput("/usr/bin/cvs -n up 2>&1 | egrep '^[^\?] .*' | egrep -v '^. .*/digest-[^/]+|^cvs server: .* -- ignored$'")

	mylines=string.split(retval[1], "\n")
	myupdates=[]
	for x in mylines:
		if not x:
			continue
		if x[0] not in "UPMAR": # Updates,Patches,Modified,Added,Removed
			print red("!!! Please fix the following issues reported from cvs: ")+green("(U and P are ok)")
			print red("!!! Note: This is a pretend/no-modify pass...")
			print retval[1]
			print
			sys.exit(1)
		elif x[0] in ["U","P"]:
			myupdates+=[x[2:]]

	if myupdates:
		print green("Fetching trivial updates...")
		if "--pretend" in myoptions:
			print "(/usr/bin/cvs up "+string.join(myupdates)+")"
			retval=0
		else:
			retval=os.system("/usr/bin/cvs up "+string.join(myupdates))
		if retval!=0:
			print "!!! cvs exited with an error. Terminating."
			sys.exit(retval)

	if isCvs:
		mycvstree=cvstree.getentries("./",recursive=1)
		mychanged=cvstree.findchanged(mycvstree,recursive=1,basedir="./")
		mynew=cvstree.findnew(mycvstree,recursive=1,basedir="./")
		myremoved=cvstree.findremoved(mycvstree,recursive=1,basedir="./")
		if not (mychanged or mynew or myremoved):
			print
			print green("RepoMan sez:"), "\"Doing nothing is not always good for QA.\"\n"
			print
			print "(Didn't find any changed files...)"
			print
			sys.exit(0)

	myupdates=mychanged+mynew
	myheaders=[]
	mydirty=[]
	headerstring="'\$(Header|Id)"
	headerstring+=".*\$'"
	for myfile in myupdates:
		myout=getstatusoutput("egrep -q "+headerstring+" "+myfile)
		if myout[0]==0:
			myheaders.append(myfile)

	print "*",green(str(len(myupdates))),"files being committed...",green(str(len(myheaders))),"have headers that will change."
	print "*","Files with headers will cause the manifests to be made and recommited."
	print "myupdates:",myupdates
	print "myheaders:",myheaders
	print
	unlinkfile=0
	if not (commitmessage or commitmessagefile):
		print "Please enter a CVS commit message at the prompt:"
		try:
			commitmessage=raw_input(green("> "))
		except KeyboardInterrupt:
			exithandler()
	if not commitmessagefile:
		unlinkfile=1
		commitmessagefile="/tmp/.repoman.msg"
		if os.path.exists(commitmessagefile):
			os.unlink(commitmessagefile)
		mymsg=open(commitmessagefile,"w")
		mymsg.write(commitmessage)
		mymsg.close()

		try:
			mymsg=open(commitmessagefile,"r")
			commitmessage=mymsg.read()
			mymsg.close()
		except Exception,e:
			print "!!! Failed to open commit message file."
			print "!!!",e
			sys.exit(1)
		print
		print green("Using commit message:")
		print green("------------------------------------------------------------------------------")
		print commitmessage
		print green("------------------------------------------------------------------------------")
		print

		if "--pretend" in myoptions:
			print "(/usr/bin/cvs -q commit -F "+commitmessagefile+")"
			retval=0
		else:
			retval=os.system("/usr/bin/cvs -q commit -F "+commitmessagefile)
		if retval:
			print "!!! Exiting on cvs (shell) error code:",retval
			sys.exit(retval)

	mychanges=[]
	if myheaders or myremoved or mynew:
		myfiles=myheaders+myremoved+mynew
		mydone=[]
		if repolevel==3:   # In a package dir
			portage.settings["O"]="./"
			portage.digestgen([],manifestonly=1)
		elif repolevel==2: # In a category dir
			for x in myfiles:
				xs=string.split(x,"/")
				if xs[0]==".":
					xs=xs[1:]
				if xs[0] in mydone:
					continue
				mydone.append(xs[0])
				portage.settings["O"]="./"+xs[0]
				portage.digestgen([],manifestonly=1)
		elif repolevel==1: # repo-cvsroot
			print green("RepoMan sez:"), "\"You're rather crazy... doing the entire repository.\"\n"
			for x in myfiles:
				xs=string.split(x,"/")
				if xs[0]==".":
					xs=xs[1:]
				if string.join(xs[:2],"/") in mydone:
					continue
				mydone.append(string.join(xs[:2],"/"))
				portage.settings["O"]="./"+string.join(xs[:2],"/")
				portage.digestgen([],manifestonly=1)
		else:
			print red("I'm confused... I don't know where I am!")
			sys.exit(1)

	mysigs=[]
	for x in mychanges:
		if "--pretend" in myoptions:
			print "(/usr/sbin/ebuild "+x+".ebuild digest)"
		else:
			os.system("/usr/sbin/ebuild "+x+".ebuild digest")
		y = string.split(x,"/")
		if "sign" in portage.features:
			gpgcmd="gpg -ab --yes "+portage.settings["GPG_OPTIONS"]+" "
			sigfile=y[:-1]+"/files/digest-"+y[-1]
			if "--pretend" in myoptions:
				print "("+gpgcmd+sigfile+")"
			else:
				os.system(gpgcmd+sigfile)
				mysigs+=[sigfile]

	if "--pretend" in myoptions:
		print "(/usr/bin/cvs -q commit -F "+commitmessagefile+")"
	else:
		retval=os.system("/usr/bin/cvs -q commit -F "+commitmessagefile)
		if retval:
			print "!!! Exiting on cvs (shell) error code:",retval
			sys.exit(retval)

	if unlinkfile:
		os.unlink(commitmessagefile)
	print
	if isCvs:
		print "CVS commit complete."
	else:
		print "repoman was too scared by not seeing any familiar cvs file that he forgot to commit anything"
	print green("RepoMan sez:"), "\"If everyone were like you, I'd be out of business!\"\n"
sys.exit(0)

