#!/usr/bin/env python3
import sys
import re

# Diccionario que mapea palabras reservadas a sus tokens
PALABRAS_RESERVADAS = {
    'program': 'PROGRAM', 
    'var': 'VAR', 
    'integer': 'INTEGER', 
    'boolean': 'BOOLEAN',
    'procedure': 'PROCEDURE', 
    'function': 'FUNCTION', 
    'begin': 'BEGIN', 
    'end': 'END',
    'if': 'IF', 
    'then': 'THEN', 
    'else': 'ELSE', 
    'while': 'WHILE', 
    'do': 'DO',
    'read': 'READ', 
    'write': 'WRITE', 
    'not': 'NOT', 
    'or': 'OR', 
    'and': 'AND',
    'div': 'DIVISION_ENTERA', 
    'true': 'TRUE', 
    'false': 'FALSE',
}

# Diccionario que mapea delimitadores a sus tokens
MAPA_DELIMITADORES = {
    ';': 'FIN_SENTENCIA', '.': 'FIN_PROGRAMA', ':': 'DECLARACION_TIPO',
    ',': 'SEPARADOR', '(': 'PARENTESIS_IZQ', ')': 'PARENTESIS_DER',
    '[': 'CORCHETE_IZQ', ']': 'CORCHETE_DER',
}

# Diccionario para atributos de operadores matemáticos
MAPA_OPERADOR_MAT = {
    '+': 'SUMA', '-': 'RESTA', '*': 'MULTIPLICACION', '/': 'DIVISION'
}

# Diccionario para atributos de operadores relacionales
MAPA_OPERADOR_REL = {
    '=': 'IGUAL', '<>': 'DISTINTO', '<': 'MENOR', '<=': 'MENOR_IGUAL',
    '>': 'MAYOR', '>=': 'MAYOR_IGUAL'
}

# Especificación de tokens mediante expresiones regulares
# El orden es importante: las reglas de arriba tienen prioridad
ESPECIFICACION_TOKENS = [
    ('NUMERO', r'\d+'),                      # Números enteros
    ('ID', r'[a-zA-Z][a-zA-Z0-9]*'),         # Identificadores
    ('ASIGNACION', r':='),                  # Asignación :=
    ('OPER_RELACIONAL', r'<=|>=|<>|<|>|='), # Operadores relacionales
    ('OPERADOR_MATEMATICO', r'[\+\-\*/]'),  # Operadores aritméticos
    ('DELIMITADOR', r'[;:\,\(\)\[\]\.]'),   # Delimitadores
    ('ESPACIO', r'[ \t\f\r\n]+'),            # Espacios (ignorar)
    ('COMENTARIO', r'\{[^\}]*\}|\(\*.*?\*\)'),  # Comentarios { } o (* *)
    ('ERROR', r'.'),                         # Carácter no válido
]

def analizar(codigo_fuente):
    # Une todas las regex en una sola con grupos nombrados
    regex_unida = '|'.join('(?P<%s>%s)' % par for par in ESPECIFICACION_TOKENS)
    
    numero_linea = 1      # Línea actual
    inicio_linea = 0      # Posición donde inicia la línea actual
    reconocimientos = []  # Resultado completo en orden de aparición
    lista_tokens = []     # Almacena tokens válidos
    lista_errores = []    # Almacena errores léxicos
    
    # Busca todos los patrones en el código
    for coincidencia in re.finditer(regex_unida, codigo_fuente):
        # Ejemplo: si lexema = "program", tipo_token = "ID" (luego se convierte a "PROGRAM")
        # Si lexema = "10", tipo_token = "NUMERO"
        tipo_token = coincidencia.lastgroup  # Nombre del token reconocido (ID, NUMERO, etc.)
        lexema = coincidencia.group()         # Texto que coincidió (ej: "program", "10")
        columna = coincidencia.start() - inicio_linea + 1  # Calcula columna
        
        # Si es ESPACIO, no genera token. Actualiza línea si hay saltos de línea
        if tipo_token == 'ESPACIO':
            cantidad_saltos = lexema.count('\n')
            if cantidad_saltos > 0:
                numero_linea += cantidad_saltos
                inicio_linea = coincidencia.start() + lexema.rfind('\n') + 1
            continue
        
        # Si es COMENTARIO, se ignora. Actualiza línea si hay saltos
        if tipo_token == 'COMENTARIO':
            cantidad_saltos = lexema.count('\n')
            if cantidad_saltos > 0:
                numero_linea += cantidad_saltos
                inicio_linea = coincidencia.start() + lexema.rfind('\n') + 1
            continue
        
        # Si es un ID, verificar si es palabra reservada usando diccionario
        if tipo_token == 'ID':
            tipo_token = PALABRAS_RESERVADAS.get(lexema.lower(), 'ID')
        
        # Si es operador matemático, guardar con atributo
        if tipo_token == 'OPERADOR_MATEMATICO':
            atributo = MAPA_OPERADOR_MAT.get(lexema)
            lista_tokens.append((tipo_token, lexema, numero_linea, columna, atributo))
            reconocimientos.append(('OK', tipo_token, lexema, numero_linea, columna, atributo))
            continue
        
        # Si es operador relacional, guardar con atributo
        if tipo_token == 'OPER_RELACIONAL':
            atributo = MAPA_OPERADOR_REL.get(lexema)
            lista_tokens.append((tipo_token, lexema, numero_linea, columna, atributo))
            reconocimientos.append(('OK', tipo_token, lexema, numero_linea, columna, atributo))
            continue
        
        # Si es delimitador, mapear al token correspondiente
        if tipo_token == 'DELIMITADOR':
            tipo_token = MAPA_DELIMITADORES.get(lexema, lexema)
        
        # Si es carácter inválido, registrar error
        if tipo_token == 'ERROR':
            lista_errores.append((lexema, numero_linea, columna))
            reconocimientos.append(('ERROR', None, lexema, numero_linea, columna, None))
            continue
        
        # Agregar token válido a la lista
        lista_tokens.append((tipo_token, lexema, numero_linea, columna))
        reconocimientos.append(('OK', tipo_token, lexema, numero_linea, columna, None))
        
    return reconocimientos, lista_tokens, lista_errores


def escribir_salida(archivo_salida, reconocimientos, tokens, errores):
    print("Reconocimiento total de tokens:", file=archivo_salida)

    for estado, tipo_token, lexema, linea, columna, atributo in reconocimientos:
        if estado == 'ERROR':
            print(
                f"[ERROR] carácter '{lexema}' inesperado en (lin. {linea:03d}, col. {columna:03d})",
                file=archivo_salida,
            )
            continue

        descripcion = (
            f"[OK] {tipo_token:<20} lexema='{lexema}' "
            f"(lin. {linea:03d}, col. {columna:03d})"
        )
        if atributo is not None:
            descripcion += f" atributo={atributo}"
        print(descripcion, file=archivo_salida)

    print("", file=archivo_salida)
    print("Resumen:", file=archivo_salida)
    print(f"Tokens válidos: {len(tokens)}", file=archivo_salida)
    print(f"Errores léxicos: {len(errores)}", file=archivo_salida)

    if errores:
        print("", file=archivo_salida)
        print("Detalle de errores:", file=archivo_salida)
        for caracter, linea, columna in errores:
            print(
                f"- carácter '{caracter}' inesperado en (lin. {linea:03d}, col. {columna:03d})",
                file=archivo_salida,
            )
    else:
        print("No se encontraron errores léxicos.", file=archivo_salida)

def principal():
    # Verifica que se pase un archivo como argumento
    if len(sys.argv) < 2:
        print("Uso correcto: ./analizadorLexico <archivodeprueba.txt>")
        sys.exit(1)
    
    nombre_archivo = sys.argv[1]
    try:
        # Abre el archivo en modo lectura
        with open(nombre_archivo, 'r', encoding='utf-8') as archivo:
            codigo_fuente = archivo.read()
    except FileNotFoundError:
        print(f"Error: El archivo '{nombre_archivo}' no fue encontrado.")
        sys.exit(1)
    
    # Ejecuta el análisis léxico
    reconocimientos, tokens, errores = analizar(codigo_fuente)
    
    # Guarda el análisis completo en archivo salidaLexico.txt
    with open('salidaLexico.txt', 'w', encoding='utf-8') as archivo_salida:
        escribir_salida(archivo_salida, reconocimientos, tokens, errores)


if __name__ == '__main__':
    principal()
