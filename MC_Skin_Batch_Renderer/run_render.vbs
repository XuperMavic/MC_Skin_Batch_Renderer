Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get the script directory
strScriptPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Change to the script directory
objShell.CurrentDirectory = strScriptPath

' Install dependencies silently
objShell.Run "cmd /c python -m pip install pillow >nul 2>&1", 0, True

' Run the application silently
objShell.Run "cmd /c python MCskin_renderer.py >nul 2>&1", 0, False