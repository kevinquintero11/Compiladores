program prueba ;{ Archivo Prueba C&I Semántico}
var
  a, b: integer;

function algo: integer;
 var b:boolean;
begin
  algo := a + 5;
end;

procedure nuevo (a,b,c: integer);
begin
  write ( a );
end;

begin
   a:=9 + algo(a);
   nuevo(a*2);
end.

