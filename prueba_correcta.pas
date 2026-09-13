program  testCase1;

var
  a, b: integer;
  result, c, d, counter, limit: integer;
  isValid: boolean;
  isEven: boolean;
procedure p1 (a,b:integer);
var p1a : integer ;
function f1 (a,b:integer):integer;
var p1a : integer ;
begin
   f1 := 3 div 5
end ;

begin
   p1a := 3 div 5
end ;

function f1 (a,b:integer):integer;
var p1a : integer ;
begin
   f1 := 3 div 5
end ;


begin
  c := 2;
  d := 4;
  counter := 0;
  limit := 10;
  isValid := (5 > 3) and (c > 1);
  b := 10;
  result := a + b;
  isValid := true;
  p1(d,7);

while (counter < limit) do
  begin
    if (counter div 2 = 0) then
      isEven := true
    else
      isEven := false;

    write(counter);
    counter := counter + 1
  end;
  
  write(result);
end.
