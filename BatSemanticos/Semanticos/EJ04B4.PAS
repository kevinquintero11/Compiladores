program prueba ;{ Archivo Prueba C&I Semántico}
var
  a, b: integer;
  j,l:boolean;

function algo(m,n:boolean): integer;
 var b:boolean;
begin
  b := m OR n;
  b := b * n;
  algo := a + 5;
end;

procedure nuevo (b,c: integer);
begin
  b := b + c;
  write ( b + a );
end;

begin
   a:= 9 + algo(j, l);
   nuevo(a*2, b);
end.

