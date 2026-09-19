program prueba ;{ Archivo Prueba C&I Semántico}
var
  a, b: integer;
  j,l:boolean;

function algo(m,n:boolean): boolean;
 var b:boolean;
begin
  algo := a AND m OR algo;
end;

procedure nuevo (b,c: integer);
begin
  write ( a OR b );
end;

begin
   a:= 9 + algo(j AND TRUE, l);
   nuevo(a*2, b);
end.

