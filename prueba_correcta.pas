program ejemplo;

var
    x, y: integer;
    b: boolean;

procedure imprimir(a: integer);
begin
    write(a)
end;

function suma(a: integer; c: integer): integer;
begin
    suma := a + c
end;

begin
    x := 10;
    y := suma(x, 20);
    if x < y then
    begin
        write(y)
    end
    else
    begin
        read(x)
    end;
    while x < y do
        x := x + 1
end.
