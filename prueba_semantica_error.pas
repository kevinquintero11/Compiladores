program pruebaErrores;

var
  numero: integer;
  Numero: boolean;
  bandera: boolean;

procedure mostrar(valor: integer; activo: boolean);
begin
  write(valor)
end;

function duplicar(n: integer): integer;
begin
  n := n + 1
end;

begin
  desconocida := 10;
  numero := true;
  bandera := numero + 5;
  if numero then
    numero := 1;
  mostrar(numero);
  mostrar(true, false);
  duplicar(numero);
  numero := mostrar(numero, true)
end.
