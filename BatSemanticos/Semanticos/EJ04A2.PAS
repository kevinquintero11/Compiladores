program prueba ;{ Archivo Prueba C&I Semántico}
var
  a, b: integer;
  j,l:boolean;

function algo(m,n:boolean): integer;
 var b:boolean;
begin
  algo := a + 5 AND b;
end;

function algoBool(m,n:boolean): boolean;
 var b:boolean;
begin
  algoBool := a + 5;
end;

procedure nuevo (b,c: integer);
begin
  write ( a + b + c );
end;

begin
   if algobool(j,l) then
      a:= 9 + algo(j AND TRUE, l);
   else
      nuevo(a*2, b);
end.

