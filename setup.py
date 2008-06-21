# -------------------------------------------------------------------
# Copyright: This file has been placed in the public domain.
#
# This file is part of AFMS. 
# Major parts of this file were copied from the module
# http://docutils.sourceforge.net/docutils/examples.py
# The author of this module is David Goodger <goodger@python.org>
# This module has been placed in the public domain.
#
# AFMS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with AFMS.  If not, see <http://www.gnu.org/licenses/>.
# -------------------------------------------------------------------

# $Id$

from distutils.core import setup
import zipfile, os, sys, py2exe
from version import VERSION

addonfile1 = os.path.join(sys.prefix,'Lib/site-packages/docutils/writers/html4css1/html4css1.css')
addonfile2 = os.path.join(sys.prefix,'Lib/site-packages/docutils/writers/html4css1/template.txt')

setup(
    windows = [{'script': 'afeditor.py',     'icon_resources': [(1, "icons/applications-system.ico")]}, 
               {'script': 'testrunner.py',   'icon_resources': [(1, "icons/applications-system.ico")]}],
    console = [{'script': 'afexporthtml.py', 'icon_resources': [(1, "icons/applications-system.ico")]}, 
               {'script': 'afexportxml.py',  'icon_resources': [(1, "icons/applications-system.ico")]}, 
               {'script': 'trexporthtml.py', 'icon_resources': [(1, "icons/applications-system.ico")]}, 
               {'script': 'trexportxml.py',  'icon_resources': [(1, "icons/applications-system.ico")]}],
    data_files = [("", ['html4css1.css', 'template.txt']),
                  ("", ['CHANGELOG.txt', 'COPYING.txt', 'README.txt']),
    
    ],
    options = {
        "py2exe":{
            "dist_dir": 'afms-win32-%s' % VERSION,
            "optimize": 2,
            "includes": ['docutils.readers.standalone', 'docutils.parsers.rst', 
                         'docutils.writers.html4css1', 'docutils.languages.en']
        }
    }
)