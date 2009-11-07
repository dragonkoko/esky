#  Copyright (c) 2009, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.
"""

  esky.bdist_esky:  distutils command to freeze apps in esky format

Importing this module makes "bdist_esky" available as a distutils command.
This command will freeze the given scripts and package them into a zipfile
named with the application name, version and platform.

The resulting zipfile is conveniently in the format expected by the default
SimpleVersionFinder.  It will be named "appname-version.platform.zip"

"""

import os
import sys
import imp
import time
import zipfile
import marshal
import struct
import shutil
import inspect
import zipfile

import distutils.command
from distutils.core import Command

import bbfreeze

import esky.bootstrap
from esky.util import get_platform, is_core_dependency


class bdist_esky(Command):

    description = "create a frozen app in 'esky' format"

    user_options = [
                    ('dist-dir=', 'd',
                     "directory to put final built distributions in"),
                    ('bootstrap-module=', None,
                     "module to use for bootstrapping esky apps"),
                    ('includes=', None,
                     "list of modules to specifically include"),
                    ('excludes=', None,
                     "list of modules to specifically exclude"),
                   ]

    def initialize_options(self):
        self.dist_dir = None
        self.includes = []
        self.excludes = []
        self.bootstrap_module = None

    def finalize_options(self):
        self.set_undefined_options('bdist',('dist_dir', 'dist_dir'))

    def run(self):
        fullname = self.distribution.get_fullname()
        platform = get_platform()
        bsdir = os.path.join(self.dist_dir,"%s.%s"%(fullname,platform,))
        fdir = os.path.join(bsdir,"%s.%s"%(fullname,platform,))
        if os.path.exists(bsdir):
            shutil.rmtree(bsdir)
        os.makedirs(fdir)
        #  Do a standard bbfreeze of the given scripts
        f = bbfreeze.Freezer(fdir,includes=self.includes,excludes=self.excludes)
        f.linkmethod = "loader"
        f.addModule("esky")
        if self.distribution.has_scripts():
            for s in self.distribution.scripts:
                f.addScript(s,gui_only=s.endswith(".pyw"))
        f()
        #  Create the bootstrap environment
        bslib_path = os.path.join(bsdir,"library.zip")
        bslib = zipfile.PyZipFile(bslib_path,"w",zipfile.ZIP_STORED)
        #  store the bootstrapping module
        code_source = inspect.getsource(esky.bootstrap)
        code = imp.get_magic() + struct.pack("<i",0)
        code += marshal.dumps(compile(code_source,"bootstrap.py","exec"))
        bslib.writestr(zipfile.ZipInfo("bootstrap.pyc",(2000,1,1,0,0,0)),code)
        #  and the main module which uses it
        if self.bootstrap_module is None:
            code_source = "from bootstrap import bootstrap\nbootstrap()"
        else:
            bsmodule = __import__(self.bootstrap_module)
            code_source = inspect.getsource(bsmodule)
        code = imp.get_magic() + struct.pack("<i",0)
        code += marshal.dumps(compile(code_source,"__main__.py","exec"))
        bslib.writestr(zipfile.ZipInfo("__main__.pyc",(2000,1,1,0,0,0)),code)
        bslib.close()
        manifest = ["library.zip"]
        if self.distribution.has_scripts():
            for s in self.distribution.scripts:
                nm = os.path.basename(s)
                if nm.endswith(".py") or nm.endswith(".pyw"):
                    nm = ".".join(nm.split(".")[:-1])
                if sys.platform == "win32":
                    nm += ".exe"
                shutil.copy2(os.path.join(fdir,nm),os.path.join(bsdir,nm))
                manifest.append(nm)
        for nm in os.listdir(fdir):
            if is_core_dependency(nm):
                shutil.copy2(os.path.join(fdir,nm),os.path.join(bsdir,nm))
                manifest.append(nm)
        f_manifest = open(os.path.join(fdir,"esky-bootstrap.txt"),"wt")
        for nm in manifest:
            f_manifest.write(nm)
            f_manifest.write("\n")
        f_manifest.close()
        #  Zip up the distribution
        zfname = os.path.join(self.dist_dir,"%s.%s.zip"%(fullname,platform,))
        zf = zipfile.ZipFile(zfname,"w")
        for (dirpath,dirnames,filenames) in os.walk(bsdir):
            for fn in filenames:
                fpath = os.path.join(dirpath,fn)
                zpath = fpath[len(bsdir)+1:]
                zf.write(fpath,zpath)
        zf.close()
        shutil.rmtree(bsdir)


distutils.command.__all__.append("bdist_esky")
sys.modules["distutils.command.bdist_esky"] = sys.modules["esky.bdist_esky"]

