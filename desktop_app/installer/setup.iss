; setup.iss - Script de instalador Inno Setup para Trading Bot Desktop
; Herramienta: Inno Setup 6 (https://jrsoftware.org/isinfo.php)
;
; Para compilar:
;   1. Instalar Inno Setup 6
;   2. Primero compilar el proyecto WPF en modo Release:
;      dotnet publish -c Release -r win-x64 --self-contained true
;   3. Abrir este archivo con Inno Setup y compilar

#define MyAppName      "Trading Bot MT5"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "TradingBot"
#define MyAppURL       "http://217.154.100.195:8080"
#define MyAppExeName   "TradingBotDesktop.exe"
#define MyAppGUID      "{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}"

; Ruta de salida del publish de .NET
; Ajustar segun donde quede el output de dotnet publish
#define PublishDir "..\TradingBotDesktop\bin\Release\net8.0-windows\win-x64\publish"

[Setup]
AppId={{#MyAppGUID}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=
OutputDir=output
OutputBaseFilename=TradingBotDesktop_Setup_v{#MyAppVersion}
SetupIconFile={#PublishDir}\Assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0.17763

; Colores del instalador (tema oscuro)
WizardSizePercent=120

[Languages]
Name: "spanish";   MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english";   MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";  Description: "{cm:CreateDesktopIcon}";   GroupDescription: "{cm:AdditionalIcons}"
Name: "startmenu";    Description: "Crear acceso en Menu Inicio"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; Todos los archivos del publish .NET (self-contained)
Source: "{#PublishDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}";     Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar";      Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartmenu}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startmenu

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Borrar configuracion de usuario al desinstalar (opcional)
; Type: dirifempty; Name: "{userappdata}\TradingBotDesktop"

[Code]
// Verificar .NET en el sistema (ya incluido en self-contained, pero por si acaso)
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

procedure InitializeWizard();
begin
  // Personalizar pantalla de bienvenida
  WizardForm.WelcomeLabel2.Caption :=
    'Este instalador configurara Trading Bot MT5 Desktop en tu PC.' + #13#10 + #13#10 +
    'Requieres:' + #13#10 +
    '  - Windows 10/11 (64-bit)' + #13#10 +
    '  - MetaTrader 5 instalado' + #13#10 +
    '  - Conexion a internet (VPS)' + #13#10 + #13#10 +
    'Haz clic en Siguiente para continuar.';
end;
