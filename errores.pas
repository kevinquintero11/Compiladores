program errores;
var
   total: integer;
   activo: boolean;
   precio: integer;

begin
   { Error 1: símbolo '@' no pertenece al lenguaje }
   total := 10 @ 5;

   { Error 2: símbolo '$' no pertenece al lenguaje }
   precio := $250;

   { Error 3: símbolo '#' no pertenece al lenguaje }
   activo := #true;

   { Error 4: símbolo '!' no pertenece al lenguaje }
   if total ! 0 then
      write(total);

   { Error 5: símbolo '?' no pertenece al lenguaje }
   activo := false?;

   { Error 6: símbolo '%' no pertenece al lenguaje (no existe módulo en mini-Pascal) }
   total := total % 3;

   { Error 7: símbolo '~' no pertenece al lenguaje }
   total := ~total;

   { Error 8: símbolo '&' no pertenece al lenguaje (and se escribe con palabra reservada) }
   activo := true & false;

   { Error 9: símbolo '^' no pertenece al lenguaje }
   total := 2 ^ 8;
end.
