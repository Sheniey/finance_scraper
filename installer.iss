#define AppName "Finance Scraper"
#define AppGroupName "FinanceScraper"
#define AppVersion "0.1.0"
#define AppPublisher "Finance Scraper"

#define CliExecName "finance-scraper.exe"
#define DesktopExecName "FinanceScraper.exe"



[Setup]
AppId={{5F72CA3C-BD7D-4CE0-A25D-DBE45A7ED643}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}

DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppGroupName}

UninstallDisplayIcon={app}\APP\{#DesktopExecName}

ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

PrivilegesRequired=lowest
ChangesEnvironment=yes

OutputDir=website\public\bin
OutputBaseFilename=FinanceScraperSetup-{#AppVersion}-x64

Compression=lzma2
SolidCompression=yes
WizardStyle=modern includetitlebar
SetupIconFile=website\public\favicon.ico



[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "addtopath"; Description: "Add finance-scraper.exe to the current user's PATH"; GroupDescription: "Terminal integration:"; Flags: checkedonce



[Files] 
Source: "finance_scraper\dist\finance-scraper\*"; DestDir: "{app}\CLI"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "desktop_app\dist\*"; DestDir: "{app}\APP"; Flags: ignoreversion recursesubdirs createallsubdirs



[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\CLI\{#CliExecName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\APP\{#DesktopExecName}"; WorkingDir: "{app}"; Tasks: desktopicon



[Code]
const
  WM_SETTINGCHANGE = $001A;
  HWND_BROADCAST = $FFFF;
  SMTO_ABORTIFHUNG = $0002;
  PathMarkerKey = 'Software\Finance Scraper';
  PathMarkerValue = 'InstallerManagedPath';

function NeedsAddPath(Param: string): Boolean;
var
  ExistingPath: string;
begin
  if not RegQueryStringValue(
    HKEY_LOCAL_MACHINE,
    'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
    'Path',
    ExistingPath
  ) then
    ExistingPath := '';

  Result := Pos(';' + Lowercase(Param) + ';',
    ';' + Lowercase(ExistingPath) + ';') = 0;
end;

function SendMessageTimeoutW(
  hWnd: HWND;
  Msg: UINT;
  wParam: Longint;
  lParam: string;
  fuFlags: UINT;
  uTimeout: UINT;
  var lpdwResult: DWORD
): LRESULT;
  external 'SendMessageTimeoutW@user32.dll stdcall';

function NormalizePathEntry(const Value: string): string;
begin
  Result := Uppercase(RemoveBackslashUnlessRoot(Trim(Value)));
end;

function ContainsPathEntry(const PathValue, Entry: string): Boolean;
var
  Remaining: string;
  Current: string;
  Separator: Integer;
begin
  Result := False;
  Remaining := PathValue;
  while True do
  begin
    Separator := Pos(';', Remaining);
    if Separator = 0 then
    begin
      Current := Remaining;
      Remaining := '';
    end
    else
    begin
      Current := Copy(Remaining, 1, Separator - 1);
      Delete(Remaining, 1, Separator);
    end;

    if CompareText(NormalizePathEntry(Current), NormalizePathEntry(Entry)) = 0 then
    begin
      Result := True;
      Exit;
    end;
    if Remaining = '' then
      Break;
  end;
end;

function RemovePathEntry(const PathValue, Entry: string): string;
var
  Remaining: string;
  Current: string;
  Separator: Integer;
  HasMore: Boolean;
  IsFirst: Boolean;
begin
  Result := '';
  IsFirst := True;
  Remaining := PathValue;
  while True do
  begin
    Separator := Pos(';', Remaining);
    if Separator = 0 then
    begin
      Current := Remaining;
      Remaining := '';
      HasMore := False;
    end
    else
    begin
      Current := Copy(Remaining, 1, Separator - 1);
      Delete(Remaining, 1, Separator);
      HasMore := True;
    end;

    if CompareText(NormalizePathEntry(Current), NormalizePathEntry(Entry)) <> 0 then
    begin
      if not IsFirst then
        Result := Result + ';';
      Result := Result + Current;
      IsFirst := False;
    end;
    if not HasMore then
      Break;
  end;
end;

procedure BroadcastEnvironmentChange;
var
  MessageResult: DWORD;
begin
  SendMessageTimeoutW(
    HWND_BROADCAST,
    WM_SETTINGCHANGE,
    0,
    'Environment',
    SMTO_ABORTIFHUNG,
    5000,
    MessageResult
  );
end;
procedure AddAppToUserPath;
var
  UserPath: string;
  AppPath: string;
begin
  AppPath := ExpandConstant('{app}\CLI');

  if not RegQueryStringValue(HKCU, 'Environment', 'Path', UserPath) then
    UserPath := '';

  if ContainsPathEntry(UserPath, AppPath) then
    Exit;

  if UserPath = '' then
    UserPath := AppPath
  else
    UserPath := UserPath + ';' + AppPath;

  if not RegWriteExpandStringValue(HKCU, 'Environment', 'Path', UserPath) then
  begin
    MsgBox(
      'Finance Scraper was installed, but Windows could not update your PATH.',
      mbError,
      MB_OK
    );
    Exit;
  end;

  RegWriteStringValue(
    HKCU,
    PathMarkerKey,
    PathMarkerValue,
    AppPath
  );

  BroadcastEnvironmentChange;
end;
procedure RemoveAppFromUserPath;
var
  UserPath: string;
  AppPath: string;
  ManagedPath: string;
begin
  AppPath := ExpandConstant('{app}\CLI');

  if not RegQueryStringValue(
    HKCU,
    PathMarkerKey,
    PathMarkerValue,
    ManagedPath
  ) then
    Exit;

  if CompareText(
    NormalizePathEntry(ManagedPath),
    NormalizePathEntry(AppPath)
  ) <> 0 then
    Exit;

  if RegQueryStringValue(HKCU, 'Environment', 'Path', UserPath) then
  begin
    UserPath := RemovePathEntry(UserPath, AppPath);

    if UserPath = '' then
      RegDeleteValue(HKCU, 'Environment', 'Path')
    else
      RegWriteExpandStringValue(
        HKCU,
        'Environment',
        'Path',
        UserPath
      );
  end;

  RegDeleteValue(HKCU, PathMarkerKey, PathMarkerValue);

  BroadcastEnvironmentChange;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('addtopath') then
    AddAppToUserPath;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    RemoveAppFromUserPath;
end;
