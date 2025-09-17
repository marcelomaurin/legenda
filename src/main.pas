unit main;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, StdCtrls, ToolsOuvir,
  texto, rotulo;

type

  { Tfrmmain }

  Tfrmmain = class(TForm)
    Button1: TButton;
    ToggleBox1: TToggleBox;
    procedure Button1Click(Sender: TObject);
    procedure FormCreate(Sender: TObject);
    procedure ToggleBox1Change(Sender: TObject);
  private

  public

  end;

var
  frmmain: Tfrmmain;

implementation

{$R *.lfm}

{ Tfrmmain }

procedure Tfrmmain.FormCreate(Sender: TObject);
begin
  frmToolsOuvir := TfrmToolsOuvir.create(self);
  frmToolsOuvir.show;
  frmToolsOuvir.Conectar();
  frmtexto := Tfrmtexto.Create(self);
  frmrotulo := Tfrmrotulo.create(self);
end;

procedure Tfrmmain.ToggleBox1Change(Sender: TObject);
begin
  frmrotulo.show;
end;

procedure Tfrmmain.Button1Click(Sender: TObject);
begin
  frmtexto.show;
end;

end.

