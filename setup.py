from distutils.core import setup
import py2exe, sys

sys.argv.append("py2exe")

setup(
    options = {
            "py2exe":{
                "bundle_files": 1,
                "compressed": True,
                "dll_excludes": ["MSVCP90.dll", "HID.DLL", "w9xpopen.exe"],
                "includes":["sip"]
            }
        },
    windows=["ProfViz.py"]
)
