program prueba ;{ Archivo Prueba C&I Semántico}
var
  a, b: integer;
  j,l:boolean;

function algo(m,n:boolean): integer;
 var b:boolean;
begin
  if n then algo := a + 5
       else algo := a - 5 + algo;
end;

procedure nuevo (b,c: integer);
begin
  write ( NOT a );
end;

begin
   a:= 9 + algo(j AND TRUE, l);
   nuevo(a*2, b);
end.

