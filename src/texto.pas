unit Texto;

{$mode ObjFPC}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, ExtCtrls, StdCtrls;

type

  { Tfrmtexto }

  Tfrmtexto = class(TForm)
    Memo1: TMemo;
    Panel1: TPanel;
    ToggleBox1: TToggleBox;
    ToggleBox2: TToggleBox;
    procedure ToggleBox1Click(Sender: TObject);
    procedure ToggleBox2Click(Sender: TObject);
  private

  public
    procedure Adicionar(texto : string);

  end;

var
  frmtexto: Tfrmtexto;

implementation

{$R *.lfm}

{ Tfrmtexto }

procedure Tfrmtexto.ToggleBox1Click(Sender: TObject);
begin
  close;
end;

procedure Tfrmtexto.ToggleBox2Click(Sender: TObject);
begin
  Memo1.Lines.Clear;
end;

procedure Tfrmtexto.Adicionar(texto: string);
begin
  Memo1.Lines.Append(texto);
end;

end.

