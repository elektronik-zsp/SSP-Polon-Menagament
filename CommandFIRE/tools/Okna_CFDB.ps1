param([ValidateSet('save','openjson','opencfdb','password')][string]$Mode)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Application]::EnableVisualStyles()
if ($Mode -eq 'save') {
  $dlg = New-Object System.Windows.Forms.SaveFileDialog
  $dlg.Title = 'CommandFIRE - wybierz folder i nazwe nowej bazy'
  $dlg.Filter = 'Baza CommandFIRE (*.cfdb)|*.cfdb'
  $dlg.DefaultExt = 'cfdb'; $dlg.AddExtension = $true; $dlg.OverwritePrompt = $true
  if ($dlg.ShowDialog() -eq 'OK') { [Console]::WriteLine($dlg.FileName) }
} elseif ($Mode -eq 'openjson' -or $Mode -eq 'opencfdb') {
  $dlg = New-Object System.Windows.Forms.OpenFileDialog
  if ($Mode -eq 'openjson') {$dlg.Filter = 'Stara baza JSON (*.json)|*.json'} else {$dlg.Filter = 'Baza CFDB (*.cfdb)|*.cfdb'}
  $dlg.Title = 'CommandFIRE - wskaz plik bazy'
  if ($dlg.ShowDialog() -eq 'OK') {[Console]::WriteLine($dlg.FileName)}
} else {
  $form = New-Object System.Windows.Forms.Form
  $form.Text = 'CommandFIRE - haslo administratora'; $form.Width=410; $form.Height=200; $form.StartPosition='CenterScreen'
  $label=New-Object System.Windows.Forms.Label; $label.Text='Haslo (12-128 znakow):'; $label.SetBounds(15,15,350,22); $form.Controls.Add($label)
  $pwd=New-Object System.Windows.Forms.TextBox; $pwd.SetBounds(15,40,355,25); $pwd.UseSystemPasswordChar=$true; $form.Controls.Add($pwd)
  $label2=New-Object System.Windows.Forms.Label; $label2.Text='Powtorz haslo:'; $label2.SetBounds(15,75,350,22); $form.Controls.Add($label2)
  $pwd2=New-Object System.Windows.Forms.TextBox; $pwd2.SetBounds(15,98,355,25); $pwd2.UseSystemPasswordChar=$true; $form.Controls.Add($pwd2)
  $ok=New-Object System.Windows.Forms.Button; $ok.Text='Zatwierdz'; $ok.SetBounds(260,130,110,26); $ok.DialogResult='OK'; $form.Controls.Add($ok); $form.AcceptButton=$ok
  if ($form.ShowDialog() -eq 'OK') {
    if ($pwd.Text.Length -lt 12 -or $pwd.Text -ne $pwd2.Text) { [System.Windows.Forms.MessageBox]::Show('Hasla musza byc identyczne i miec minimum 12 znakow.'); exit 1 }
    [Console]::WriteLine([BitConverter]::ToString([Text.Encoding]::UTF8.GetBytes($pwd.Text)).Replace("-", ""))
  }
}
