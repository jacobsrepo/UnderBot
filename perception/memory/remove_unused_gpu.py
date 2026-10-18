from importlib.metadata import distributions
from pathlib import Path
import subprocess
import sys
root=Path(sys.prefix).resolve()
names=[]
for d in distributions():
 name=d.metadata['Name']
 if name.lower() != 'nvidia-ml-py' and (name.lower().startswith(('nvidia-','cuda-')) or name.lower()=='triton') and Path(d.locate_file('')).resolve().is_relative_to(root):names.append(name)
if names:subprocess.run([sys.executable,'-m','pip','uninstall','-y',*sorted(set(names))],check=True)
subprocess.run([sys.executable,'-m','pip','check'],check=True)
