program prueba ;{ Archivo Prueba C&I: EJ-SE01A2.PAS }
var
  a, b: integer;

function prueba(a: integer);
begin
  write ( a );
  prueba := a * 2;
end;

begin
   a:=9;
   write (prueba(a*2));;
end.

