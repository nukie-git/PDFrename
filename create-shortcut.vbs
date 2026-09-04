Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

' 1. Get current PDFrename folder path and user's Desktop path
ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
DesktopPath = WshShell.SpecialFolders("Desktop")

' =========================================================================
' 1. CREATE DOWNLOADS RECEIPT RENAMER SHORTCUT (Default Downloads runner)
' =========================================================================
RenameBat = FSO.BuildPath(ScriptDir, "rename_workflow.bat")
RenameLink = FSO.BuildPath(DesktopPath, "Rename Downloads Receipts (PDFrename).lnk")
Set ShortcutRename = WshShell.CreateShortcut(RenameLink)

ShortcutRename.TargetPath = RenameBat
ShortcutRename.WorkingDirectory = ScriptDir
ShortcutRename.Description = "Automated Bank Mandiri receipt & bon scanner for %USERPROFILE%\Downloads"
ShortcutRename.IconLocation = "shell32.dll, 269"
ShortcutRename.Save

' =========================================================================
' 2. CREATE GENERAL WORKFLOW SHORTCUT (Custom folder or Drag-and-Drop)
' =========================================================================
RunBat = FSO.BuildPath(ScriptDir, "run_workflow.bat")
RunLink = FSO.BuildPath(DesktopPath, "PDFrename Workflow (Custom or Drag-Drop Folder).lnk")
Set ShortcutRun = WshShell.CreateShortcut(RunLink)

ShortcutRun.TargetPath = RunBat
ShortcutRun.WorkingDirectory = ScriptDir
ShortcutRun.Description = "Automated Bank Mandiri receipt & bon scanner (specify or drag-and-drop folder)"
ShortcutRun.IconLocation = "shell32.dll, 43"
ShortcutRun.Save

' =========================================================================
' 3. CONFIRMATION MESSAGE (Interactive only, suppressed in silent mode)
' =========================================================================
Dim isSilent
isSilent = False
If WScript.Arguments.Count > 0 Then
    If LCase(WScript.Arguments(0)) = "silent" Or LCase(WScript.Arguments(0)) = "/silent" Then
        isSilent = True
    End If
End If

If Not isSilent Then
    MsgBox "PDFrename shortcuts successfully created on your Desktop!" & vbCrLf & vbCrLf & _
           "1. Rename Downloads Receipts (PDFrename)" & vbCrLf & _
           "2. PDFrename Workflow (Custom or Drag-Drop Folder)" & vbCrLf & vbCrLf & _
           "Tip: You can drag and drop any folder directly onto the Custom shortcut to rename receipts inside it!", _
           64, "PDFrename Shortcut Setup"
Else
    WScript.Echo "Shortcuts created on Desktop."
End If
