Option Explicit
Dim sh, fs, root, py, helper, choice, target, source, key, request, proc, result, msg, success, rec, username, display, passwordHex, adminJson, mode
Set sh=CreateObject("WScript.Shell")
Set fs=CreateObject("Scripting.FileSystemObject")
root=fs.GetParentFolderName(WScript.ScriptFullName)
py=fs.BuildPath(root,"runtime\python.exe")
helper=fs.BuildPath(root,"tools\konfigurator_cfdb.py")
If Not fs.FileExists(py) Or Not fs.FileExists(helper) Then
  MsgBox "Brak srodowiska portable lub plikow konfiguratora.",16,"CommandFIRE CFDB"
  WScript.Quit 1
End If
choice=InputBox("Konfigurator CommandFIRE CFDB" & vbCrLf & vbCrLf & "1 - Utworz NOWA baze CFDB" & vbCrLf & "2 - Dolacz komputer do ISTNIEJACEJ bazy CFDB" & vbCrLf & "3 - Przenies stara baze JSON do NOWEJ CFDB" & vbCrLf & vbCrLf & "Zamknij CommandFIRE przed konfiguracja.","CommandFIRE - konfiguracja stanowiska","2")
If choice="" Then WScript.Quit
If choice<>"1" And choice<>"2" And choice<>"3" Then
  MsgBox "Nieprawidlowa opcja.",48,"CommandFIRE": WScript.Quit 1
End If
Function picker(mode)
  Dim cmd, p, out
  cmd="powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File " & Chr(34) & fs.BuildPath(root,"tools\Okna_CFDB.ps1") & Chr(34) & " -Mode " & mode
  Set p=sh.Exec(cmd)
  out=Trim(p.StdOut.ReadAll)
  If p.ExitCode<>0 Then out=""
  picker=out
End Function
If choice="2" Then
  target=picker("opencfdb")
Else
  target=picker("save")
End If
If target="" Then WScript.Quit
source="": key="": adminJson=""
If choice="3" Then
  source=picker("openjson")
  If source="" Then WScript.Quit
End If
If choice="2" Then
  key=InputBox("Wpisz klucz odzyskiwania CFDB (64 znaki HEX). UWAGA: znaki sa widoczne. Upewnij sie, ze nikt nie obserwuje ekranu.","Dolaczanie stanowiska")
  If key="" Then WScript.Quit
End If
If choice="1" Then
  username=InputBox("Login pierwszego administratora (3-40 znakow):","Nowa baza - administrator")
  If username="" Then WScript.Quit
  display=InputBox("Imie i nazwisko administratora:","Nowa baza - administrator")
  If display="" Then WScript.Quit
  passwordHex=picker("password")
  ' PowerShell may prepend BOM or diagnostic output; accept only an exact hex token.
  Dim rx, matches, rawPassword
  rawPassword=passwordHex
  Set rx=CreateObject("VBScript.RegExp")
  rx.Pattern="[0-9A-Fa-f]{24,256}"
  rx.Global=False
  Set matches=rx.Execute(rawPassword)
  If matches.Count=0 Then
    MsgBox "Nie udalo sie odczytac hasla z okna. Sprawdz PowerShell i ponow probe. Nie utworzono bazy.",16,"CommandFIRE CFDB"
    WScript.Quit 1
  End If
  passwordHex=matches(0).Value
  If Len(passwordHex) Mod 2<>0 Then
    MsgBox "Nieprawidlowa dlugosc kodowania hasla. Nie utworzono bazy.",16,"CommandFIRE CFDB"
    WScript.Quit 1
  End If
End If
If MsgBox("Zamknij program na wszystkich stanowiskach przed migracja. Kontynuowac?",vbYesNo+vbQuestion,"CommandFIRE")<>vbYes Then WScript.Quit
Function esc(v)
  esc=Replace(Replace(Replace(v,"\","\\"),Chr(34),"\" & Chr(34)),vbCrLf,"\n")
End Function
Dim act
Select Case choice
 Case "1": act="new"
 Case "2": act="join"
 Case "3": act="migrate"
End Select
If choice="1" Then
  adminJson="," & Chr(34) & "admin" & Chr(34) & ":{" & Chr(34) & "username" & Chr(34) & ":" & Chr(34) & esc(username) & Chr(34) & "," & Chr(34) & "display" & Chr(34) & ":" & Chr(34) & esc(display) & Chr(34) & "," & Chr(34) & "password_hex" & Chr(34) & ":" & Chr(34) & esc(passwordHex) & Chr(34) & "}"
End If
request="{" & Chr(34) & "action" & Chr(34) & ":" & Chr(34) & act & Chr(34) & "," & Chr(34) & "path" & Chr(34) & ":" & Chr(34) & esc(target) & Chr(34) & "," & Chr(34) & "source" & Chr(34) & ":" & Chr(34) & esc(source) & Chr(34) & "," & Chr(34) & "key" & Chr(34) & ":" & Chr(34) & esc(key) & Chr(34) & adminJson & "}"
Set proc=sh.Exec(Chr(34) & py & Chr(34) & " -I -B " & Chr(34) & helper & Chr(34))
proc.StdIn.WriteLine request
proc.StdIn.Close
result=proc.StdOut.ReadAll
If proc.ExitCode<>0 Then
  MsgBox "Konfiguracja nie powiodla sie:" & vbCrLf & result & vbCrLf & proc.StdErr.ReadAll,16,"CommandFIRE CFDB"
  WScript.Quit 1
End If
If choice<>"2" Then
  ' Recovery key is returned once by the local Python process; never stored in a shared file.
  Dim a,b
  a=InStr(result,"""recovery"": """)
  If a>0 Then
    a=a+Len("""recovery"": """)
    b=InStr(a,result,Chr(34))
    If b>a Then
      rec=Mid(result,a,b-a)
      MsgBox "ZAPISZ TEN KLUCZ ODZYSKIWANIA W BEZPIECZNYM MIEJSCU (poza udzialem sieciowym):" & vbCrLf & vbCrLf & rec & vbCrLf & vbCrLf & "Nie przekazuj klucza innym osobom.",64,"CommandFIRE - klucz odzyskiwania"
    End If
  End If
End If
MsgBox "Konfiguracja CFDB zakonczona. Mozesz uruchomic CommandFIRE.",64,"CommandFIRE CFDB"
