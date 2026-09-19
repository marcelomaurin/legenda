unit ToolsOuvir;

{$mode ObjFPC}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, StdCtrls, ExtCtrls,
  AdvLed, lNetComponents, lNet, fpjson, jsonparser, rotulo, texto;

type

  { TfrmToolsOuvir }

  TfrmToolsOuvir = class(TForm)
    AdvLed1: TAdvLed;
    btConect: TButton;
    btDisconect: TButton;
    edIP: TEdit;
    edTexto: TEdit;
    edPort: TEdit;
    Label1: TLabel;
    Label2: TLabel;
    Label3: TLabel;
    LTCPComponent1: TLTCPComponent;
    Shape1: TShape;
    procedure btConectClick(Sender: TObject);
    procedure btDisconectClick(Sender: TObject);
    procedure LTCPComponent1Accept(aSocket: TLSocket);
    procedure LTCPComponent1Connect(aSocket: TLSocket);
    procedure LTCPComponent1Disconnect(aSocket: TLSocket);
    procedure LTCPComponent1Receive(aSocket: TLSocket);
    procedure Shape1ChangeBounds(Sender: TObject);
  private
    FReceiveBuffer: string;
    FLastPhrase: string;
    procedure ProcessLine(const ALine: string);
    function ExtractCaptionText(const ALine: string): string;
  public
    frase: string;
    procedure Conectar;
    procedure Disconectar;
  end;

var
  frmToolsOuvir: TfrmToolsOuvir;

implementation

{$R *.lfm}

{ TfrmToolsOuvir }

procedure TfrmToolsOuvir.Shape1ChangeBounds(Sender: TObject);
begin
end;

procedure TfrmToolsOuvir.btConectClick(Sender: TObject);
begin
  Conectar;
end;

procedure TfrmToolsOuvir.btDisconectClick(Sender: TObject);
begin
  Disconectar;
end;

procedure TfrmToolsOuvir.LTCPComponent1Accept(aSocket: TLSocket);
begin
end;

procedure TfrmToolsOuvir.LTCPComponent1Connect(aSocket: TLSocket);
begin
  AdvLed1.Blink := False;
  AdvLed1.State := lsOn;
end;

procedure TfrmToolsOuvir.LTCPComponent1Disconnect(aSocket: TLSocket);
begin
  AdvLed1.Blink := False;
  AdvLed1.State := lsOff;
end;

function TfrmToolsOuvir.ExtractCaptionText(const ALine: string): string;
var
  Data: TJSONData;
  Obj: TJSONObject;
begin
  Result := '';
  if Trim(ALine) = '' then
    Exit;

  { Compatibilidade: servidores antigos ainda podem enviar texto puro. }
  if TrimLeft(ALine)[1] <> '{' then
  begin
    Result := Trim(ALine);
    Exit;
  end;

  Data := nil;
  try
    Data := GetJSON(ALine);
    if Data.JSONType <> jtObject then
      Exit;

    Obj := TJSONObject(Data);
    if Obj.Get('type', '') = 'caption' then
      Result := Obj.Get('text', '');
  except
    on E: Exception do
      Result := '';
  end;
  Data.Free;
end;

procedure TfrmToolsOuvir.ProcessLine(const ALine: string);
var
  Info: string;
begin
  Info := ExtractCaptionText(ALine);
  if Info = '' then
    Exit;

  edTexto.Text := Info;

  if FLastPhrase = Info then
    Exit;

  FLastPhrase := Info;
  frase := Info;

  if Assigned(frmrotulo) then
    frmrotulo.Label1.Caption := Info;

  if Assigned(frmtexto) then
    frmtexto.Adicionar(Info);
end;

procedure TfrmToolsOuvir.LTCPComponent1Receive(aSocket: TLSocket);
var
  Chunk: string;
  P: SizeInt;
  Line: string;
begin
  Chunk := '';
  aSocket.GetMessage(Chunk);
  FReceiveBuffer := FReceiveBuffer + Chunk;

  repeat
    P := Pos(#10, FReceiveBuffer);
    if P = 0 then
      Break;

    Line := Copy(FReceiveBuffer, 1, P - 1);
    Delete(FReceiveBuffer, 1, P);
    Line := StringReplace(Line, #13, '', [rfReplaceAll]);
    ProcessLine(Line);
  until False;
end;

procedure TfrmToolsOuvir.Conectar;
begin
  if LTCPComponent1.Active then
    Exit;

  LTCPComponent1.Connect(edIP.Text, StrToIntDef(edPort.Text, 8097));
end;

procedure TfrmToolsOuvir.Disconectar;
begin
  if LTCPComponent1.Active then
    LTCPComponent1.Disconnect(True);
end;

end.
