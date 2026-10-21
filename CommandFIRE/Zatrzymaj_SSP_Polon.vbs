Option Explicit
Dim shell, fso, folder, pythonExe, launchScript, cmd
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
pythonExe = fso.BuildPath(fso.BuildPath(folder, "runtime"), "python.exe")
launchScript = fso.BuildPath(fso.BuildPath(folder, "tools"), "launcher.py")
If Not fso.FileExists(pythonExe) Then
    MsgBox "Brak runtime\python.exe. Skopiuj pliki do lokalnego folderu programu.", vbExclamation, "CommandFIRE SSP Serwis"
ElseIf Not fso.FileExists(launchScript) Then
    MsgBox "Brak tools\launcher.py. Zastosuj komplet aktualizacji.", vbExclamation, "CommandFIRE SSP Serwis"
Else
    cmd = Chr(34) & pythonExe & Chr(34) & " -I -B " & Chr(34) & launchScript & Chr(34) & " stop"
    shell.Run cmd, 0, False
End If
