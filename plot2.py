import os
import sys
import subprocess
from os import listdir
from os.path import isfile, join
from pathlib import Path

mypath = str(sys.argv[1])
plotfoldname = str(sys.argv[2])

# onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
allfiles = ([os.path.join(r,file) for r,d,f in os.walk(mypath) for file in f])

for e, file in enumerate(allfiles):
	if file.endswith(".csv"):
		folds = file[:-4]

	folds = folds.split("/")
	folds[0] = plotfoldname

	newfolderpath = "/".join(folds)

	path = Path(newfolderpath)
	path.mkdir(parents=True, exist_ok=True)

	call = ["python3", "plot.py", file, newfolderpath]
	subprocess.call(call, stdout=open(os.devnull, 'wb'))

	print("[*] {}/{}: {}".format(e, len(allfiles), " ".join(call)))
