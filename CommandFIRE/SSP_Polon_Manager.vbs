Option Explicit
Dim shell, fso, folder, runtime, pythonExe, managerScript, cmd, windowStyle
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
runtime = fso.BuildPath(folder, "runtime")
pythonExe = fso.BuildPath(runtime, "pythonw.exe")
If Not fso.FileExists(pythonExe) Then pythonExe = fso.BuildPath(runtime, "python.exe")
managerScript = fso.BuildPath(fso.BuildPath(folder, "tools"), "manager_boot.py")
If Not fso.FileExists(pythonExe) Then
    MsgBox "Brak runtime\python.exe. Program musi byc skopiowany lokalnie.", vbExclamation, "CommandFIRE SSP Serwis"
ElseIf Not fso.FileExists(managerScript) Then
    MsgBox "Brak tools\manager_boot.py. Skopiuj pliki poprawki 2.4.3.", vbExclamation, "CommandFIRE SSP Serwis"
Else
    cmd = Chr(34) & pythonExe & Chr(34) & " -I -B " & Chr(34) & managerScript & Chr(34)
    On Error Resume Next
    ' pythonw.exe has no console and can start visibly. If only python.exe
    ' is present, keep its console hidden; manager.py explicitly shows its
    ' own window regardless of this startup flag.
    windowStyle = 1
    If LCase(fso.GetFileName(pythonExe)) = "python.exe" Then windowStyle = 0
    shell.Run cmd, windowStyle, False
    If Err.Number <> 0 Then
        MsgBox "Nie udalo sie uruchomic Pythona:" & vbCrLf & Err.Description & vbCrLf & vbCrLf & _
               "Sprawdz przez Diagnoza_Menedzera.bat.", vbCritical, "CommandFIRE SSP Serwis"
        Err.Clear
    End If
    On Error GoTo 0
End If
