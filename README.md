# Compiladores - Analizador Lexico y Sintactico para mini-Pascal

## Descripcion general

Este directorio contiene dos analizadores para un subconjunto de mini-Pascal:

- `analizadorLexico`: wrapper ejecutable del analizador lexico.
- `analizadorSintactico.py`: implementacion ejecutable e importable del analizador sintactico.

El flujo pensado es el clasico de un compilador: primero analisis lexico y luego analisis sintactico. En la implementacion actual, `analizadorSintactico.py` importa directamente la funcion `analizar` desde `analizadorLexico.py`, por lo que no necesitas pasarle tokens manualmente.

## Contenido del directorio

- `analizadorLexico`: wrapper ejecutable del analizador lexico.
- `analizadorLexico.py`: implementacion importable del analizador lexico.
- `analizadorSintactico.py`: implementacion ejecutable e importable del analizador sintactico.
- `prueba_correcta.pas`: programa lexica y sintacticamente valido.
- `prueba_error.pas`: programa sin errores lexicos pero con varios errores sintacticos.
- `prueba.txt`: ejemplo adicional que pasa por el lexico, pero falla sintacticamente.
- `errores.txt`: archivo con varios errores lexicos para probar `analizadorLexico`.
- `salidaLexico.txt`: archivo de salida generado por el analizador lexico.
- `salidaSintactico.txt`: archivo de salida generado por el analizador sintactico.
- `README.md`: documentacion del proyecto.

## Requisitos

- Python 3.10 o superior.
- No se requieren librerias externas.

## Flujo general del proyecto

1. `analizadorLexico` lee el archivo fuente completo.
2. Usa expresiones regulares para reconocer numeros, identificadores, palabras reservadas, operadores, delimitadores y comentarios.
3. Si encuentra simbolos invalidos, los reporta como errores lexicos.
4. Si el archivo no tiene errores lexicos, el sintactico toma esos tokens y los convierte a su formato interno.
5. `analizadorSintactico.py` aplica la gramatica LL(1) con descenso recursivo.
6. Si encuentra errores sintacticos, intenta recuperarse para seguir analizando y reportar varias fallas en una sola corrida.
7. Cada fase genera su propio archivo de salida.

## Analizador lexico

### Que reconoce

`analizadorLexico` identifica:

- palabras reservadas: `program`, `var`, `integer`, `boolean`, `procedure`, `function`, `begin`, `end`, `if`, `then`, `else`, `while`, `do`, `read`, `write`, `not`, `or`, `and`, `div`, `true`, `false`
- identificadores
- numeros enteros
- asignacion `:=`
- operadores relacionales: `=`, `<>`, `<`, `<=`, `>`, `>=`
- operadores aritmeticos: `+`, `-`, `*`, `/`
- delimitadores: `;`, `:`, `,`, `(`, `)`, `[`, `]`, `.`
- comentarios estilo Pascal: `{ ... }` y `(* ... *)`

### Ejecucion

Desde este directorio:

```bash
python3 analizadorLexico archivodeprueba.pas
```

O bien:

```bash
./analizadorLexico archivodeprueba.pas
```

### Salida del lexico

El analizador lexico genera `salidaLexico.txt` con:

- reconocimiento completo de tokens en orden de aparicion
- linea y columna de cada token
- atributos extra para operadores matematicos y relacionales
- resumen con cantidad de tokens validos y errores lexicos
- detalle de errores lexicos, si existen

### Ejemplos utiles

- `./analizadorLexico prueba_correcta.pas`
- `./analizadorLexico errores.txt`

## Analizador sintactico

### Idea general

`analizadorSintactico.py` implementa un analizador descendente recursivo predictivo para la gramatica del laboratorio. Su trabajo es verificar la estructura del programa, no los simbolos individuales.

Actualmente el sintactico:

- lee el archivo fuente
- importa directamente `analizar` desde `analizadorLexico.py`
- detiene el proceso si el lexico detecta errores
- convierte los tokens lexicos a su representacion interna
- agrega el token `EOF`
- ejecuta el parser LL(1)
- intenta recuperar errores para detectar varias fallas sintacticas en una sola corrida

### Ejecucion

Desde este directorio:

```bash
python3 analizadorSintactico.py archivodeprueba.pas
```

O bien:

```bash
./analizadorSintactico.py archivodeprueba.pas
```

### Comportamiento esperado

Si el archivo es correcto:

```text
Analisis sintactico correcto
```

Si el archivo tiene errores sintacticos, la salida en consola resume la corrida, por ejemplo:

```text
Se detectaron 8 errores sintacticos
```

Si el archivo no paso el lexico, el sintactico no continua con el parser y muestra un mensaje de error indicando que primero debe pasar satisfactoriamente por `analizadorLexico`.

### Salida del sintactico

El analizador sintactico genera `salidaSintactico.txt` con:

- nombre del archivo analizado
- resultado general del analisis
- lista de diagnosticos sintacticos
- codigo fuente completo con numeracion de lineas
- una marca `^` en la columna donde se detecta cada error

Ejemplo de marcado:

```text
4 |     x y: integer;
  |       ^
  |       Error sintactico en linea 4, columna 7: se esperaba :, se encontro identificador ('y')
```

## Relacion entre ambos analizadores

La separacion de responsabilidades es esta:

- `analizadorLexico` responde: "que tokens hay en el archivo y donde estan".
- `analizadorSintactico.py` responde: "esos tokens forman un programa valido segun la gramatica".

Aunque puedes ejecutar ambos por separado, el sintactico ya integra al lexico internamente. En otras palabras:

- si quieres estudiar tokens o errores lexicos, ejecuta `analizadorLexico`
- si quieres validar la estructura del programa, ejecuta `analizadorSintactico.py`

## Archivos de prueba recomendados

- `prueba_correcta.pas`: recomendable para validar que ambas fases funcionen bien.
- `prueba_error.pas`: recomendable para revisar recuperacion de errores sintacticos.
- `prueba.txt`: util para probar un archivo que pasa por el lexico pero falla sintacticamente.
- `errores.txt`: util para probar varios errores lexicos en una sola corrida.

## Secuencia sugerida de uso

### Solo analisis lexico

```bash
./analizadorLexico errores.txt
```

Revision esperada:

- mirar `salidaLexico.txt`
- confirmar donde aparecen los simbolos invalidos

### Analisis sintactico completo

```bash
./analizadorSintactico.py prueba_correcta.pas
./analizadorSintactico.py prueba_error.pas
```

Revision esperada:

- mirar `salidaSintactico.txt`
- verificar si el programa fue aceptado o rechazado
- revisar las lineas marcadas con `^`

## Notas importantes

- `salidaLexico.txt` se sobrescribe cada vez que se ejecuta `analizadorLexico`.
- `salidaSintactico.txt` se sobrescribe cada vez que se ejecuta `analizadorSintactico.py`.
- El sintactico no analiza semantica; solo estructura gramatical.
- El sintactico intenta continuar despues de ciertos errores para reportar varias fallas, por lo que pueden aparecer errores en cascada cuando una falla temprana desacomoda el resto del analisis.
