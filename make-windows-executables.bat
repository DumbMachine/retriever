python setup.py install
rmdir %~dp0windows /s /q
mkdir %~dp0windows
python setup.py py2exe
move dist\retriever.exe windows\
rmdir build dist /s /q
