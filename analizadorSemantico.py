# Este archivo revisa que el programa mini-Pascal tenga sentido.
#
# Se ejecuta despues del analizador sintactico, cuando ya sabemos que el programa
# esta bien escrito. Aca se vuelve a leer pieza por pieza para revisar cosas
# como: variables sin declarar, tipos que no coinciden o llamadas mal hechas.
#
# Si no se puede saber el tipo de algo por un error anterior, se usa DESCONOCIDO.
# Asi se puede seguir revisando sin mostrar muchos errores por la misma causa.

from __future__ import annotations

from dataclasses import dataclass

from analizadorSintactico import DiagnosticoError, Token, TokenType
from tablaSimbolos import SimboloDuplicadoError, TablaSimbolos


# Estos son los tipos que vamos a manejar. VOID significa que no se devuelve
# ningun valor. DESCONOCIDO se usa cuando hubo un error y no sabemos el tipo.
INTEGER = "integer"
BOOLEAN = "boolean"
VOID = "void"
DESCONOCIDO = "desconocido"

# Ademas del tipo, guardamos que clase de nombre es: programa, variable,
# parametro, procedimiento o funcion. RESULTADO_FUNCION representa la asignacion
# al nombre de una funcion, por ejemplo: sumar := a + b.
PROGRAMA = "programa"
VARIABLE = "variable"
PARAMETRO = "parametro"
PROCEDIMIENTO = "procedimiento"
FUNCION = "funcion"
RESULTADO_FUNCION = "resultado_funcion"


@dataclass
class ResultadoSemantico:
    # Aca guardamos lo que queda al terminar: la lista de errores y la tabla con
    # todos los nombres que se encontraron en el programa.
    diagnostics: list[DiagnosticoError]
    tabla_global: TablaSimbolos


class AnalizadorSemantico:
    # Esta clase hace toda la revision. current marca por que parte de la lista
    # vamos. ambiente_actual indica en que parte del programa estamos trabajando.

    # Separamos los operadores en grupos para revisarlos en el orden correcto.
    # Por ejemplo, una multiplicacion se revisa antes que una suma.
    RELACIONES = {
        TokenType.IGUAL,
        TokenType.DISTINTO,
        TokenType.MENOR,
        TokenType.MENOR_IGUAL,
        TokenType.MAYOR,
        TokenType.MAYOR_IGUAL,
    }
    ADITIVOS = {TokenType.MAS, TokenType.MENOS, TokenType.OR}
    MULTIPLICATIVOS = {TokenType.POR, TokenType.DIV, TokenType.AND}

    def __init__(self, tokens: list[Token]):
        # Guardamos todas las piezas del programa y empezamos desde la primera.
        # Tambien preparamos una lista vacia de errores y la tabla principal.
        self.tokens = tokens
        self.current = 0
        self.diagnostics: list[DiagnosticoError] = []
        self.tabla_global = TablaSimbolos()
        self.ambiente_actual = self.tabla_global

    @property
    def actual(self) -> Token:
        # Mira la pieza actual del programa sin avanzar a la siguiente.
        return self.tokens[self.current]

    def analizar(self) -> ResultadoSemantico:
        # Empezamos leyendo "program nombre;". Guardamos el nombre del programa,
        # entramos en su espacio de trabajo, revisamos todo el contenido y al
        # final devolvemos los errores junto con la tabla de nombres.
        self.consumir(TokenType.PROGRAM)
        nombre = self.consumir(TokenType.IDENTIFICADOR)
        programa = self.declarar(nombre, VOID, PROGRAMA)
        self.consumir(TokenType.PUNTO_Y_COMA)
        self.abrir_ambito(nombre.lexema, programa)
        self.bloque()
        self.cerrar_ambito()
        self.consumir(TokenType.PUNTO)
        return ResultadoSemantico(self.diagnostics, self.tabla_global)

    def bloque(self) -> None:
        # Un bloque puede tener variables y funciones o procedimientos. Despues
        # de esas declaraciones siempre viene la parte encerrada en begin/end.
        if self.aceptar(TokenType.VAR):
            self.declaracion_variables()
            while self.aceptar(TokenType.PUNTO_Y_COMA):
                if self.actual.tipo != TokenType.IDENTIFICADOR:
                    break
                self.declaracion_variables()

        self.declaraciones_rutinas()
        self.comando_compuesto()

    def declaraciones_rutinas(self) -> None:
        # Mientras aparezcan funciones o procedimientos, los revisamos uno a uno.
        if self.actual.tipo not in {TokenType.PROCEDURE, TokenType.FUNCTION}:
            return

        self.declaracion_rutina(self.actual.tipo == TokenType.FUNCTION)
        self.consumir(TokenType.PUNTO_Y_COMA)
        self.declaraciones_rutinas()

    def declaracion_variables(self) -> None:
        # Lee algo como "a, b, c: integer" y guarda cada nombre por separado.
        nombres = self.lista_identificadores()
        self.consumir(TokenType.DOS_PUNTOS)
        tipo = self.tipo()
        for token in nombres:
            self.declarar(token, tipo, VARIABLE)

    def declaracion_rutina(self, es_funcion: bool) -> None:
        # Primero guardamos el nombre y los parametros de la rutina. Luego
        # entramos a revisar lo que hay dentro. Si es una funcion, tambien
        # guardamos su nombre como el lugar donde se deja el resultado, por
        # ejemplo: duplicar := n * 2.
        self.consumir(TokenType.FUNCTION if es_funcion else TokenType.PROCEDURE)
        nombre = self.consumir(TokenType.IDENTIFICADOR)
        parametros = self.parametros_opcionales()
        retorno = VOID
        if es_funcion:
            self.consumir(TokenType.DOS_PUNTOS)
            retorno = self.tipo()

        clase = FUNCION if es_funcion else PROCEDIMIENTO
        simbolo = self.declarar(nombre, retorno, clase, parametros)
        self.consumir(TokenType.PUNTO_Y_COMA)

        # Aunque el nombre este repetido, revisamos el cuerpo igualmente para no
        # perder otros errores que puedan estar dentro.
        self.abrir_ambito(nombre.lexema, simbolo)
        resultado_funcion = None
        if es_funcion:
            resultado_funcion = self.declarar(nombre, retorno, RESULTADO_FUNCION)
            if resultado_funcion is not None:
                resultado_funcion["nombre_original_funcion"] = nombre.lexema
        for parametro in parametros:
            self.declarar(
                Token(
                    TokenType.IDENTIFICADOR,
                    parametro["nombre"],
                    parametro["linea"],
                    parametro["columna"],
                ),
                parametro["tipo"],
                PARAMETRO,
            )
        self.bloque()
        if resultado_funcion is not None and not resultado_funcion["resultado_asignado"]:
            self.error(nombre, f"la funcion '{nombre.lexema}' no asigna su resultado")
        self.cerrar_ambito()

    def parametros_opcionales(self) -> list[dict]:
        # Lee los parametros que estan entre parentesis. De cada uno recordamos
        # su nombre, tipo y lugar, manteniendo el orden en el que fue escrito.
        parametros: list[dict] = []
        if not self.aceptar(TokenType.PARENTESIS_ABRE):
            return parametros
        while True:
            nombres = self.lista_identificadores()
            self.consumir(TokenType.DOS_PUNTOS)
            tipo = self.tipo()
            parametros.extend(
                {
                    "nombre": token.lexema,
                    "tipo": tipo,
                    "linea": token.linea,
                    "columna": token.columna,
                }
                for token in nombres
            )
            if not self.aceptar(TokenType.PUNTO_Y_COMA):
                break
        self.consumir(TokenType.PARENTESIS_CIERRA)
        return parametros

    def lista_identificadores(self) -> list[Token]:
        # Junta una lista de nombres separados por comas, como "a, b, c".
        nombres = [self.consumir(TokenType.IDENTIFICADOR)]
        while self.aceptar(TokenType.COMA):
            nombres.append(self.consumir(TokenType.IDENTIFICADOR))
        return nombres

    def tipo(self) -> str:
        # Lee si el tipo escrito es integer o boolean.
        if self.aceptar(TokenType.INTEGER):
            return INTEGER
        self.consumir(TokenType.BOOLEAN)
        return BOOLEAN

    def comando_compuesto(self) -> None:
        # Revisa todos los comandos que aparecen entre begin y end.
        self.consumir(TokenType.BEGIN)
        self.comando()
        while self.aceptar(TokenType.PUNTO_Y_COMA):
            if self.actual.tipo == TokenType.END:
                break
            self.comando()
        self.consumir(TokenType.END)

    def comando(self) -> None:
        # Miramos como empieza el comando para saber que revisar. Puede ser una
        # asignacion, una llamada, otro begin/end, un if, un while, read o write.
        if self.actual.tipo == TokenType.IDENTIFICADOR:
            nombre = self.consumir(TokenType.IDENTIFICADOR)
            if self.aceptar(TokenType.ASIGNACION):
                # En "numero := 10" averiguamos el tipo de 10, buscamos el tipo
                # de numero y comprobamos que los dos sean iguales.
                tipo_expresion = self.expresion()
                tipo_destino = self.tipo_destino(nombre)
                self.comprobar_compatibles(
                    tipo_destino, tipo_expresion, nombre,
                    "la asignacion requiere tipos iguales",
                )
            else:
                # Si no habia :=, el nombre corresponde a un procedimiento.
                argumentos = self.argumentos()
                self.comprobar_llamada(nombre, argumentos, espera_funcion=False)
            return
        if self.actual.tipo == TokenType.BEGIN:
            self.comando_compuesto()
            return
        if self.aceptar(TokenType.IF):
            # Lo que viene despues de if debe dar true o false.
            condicion = self.expresion()
            self.requerir_tipo(condicion, BOOLEAN, self.anterior, "if requiere una condicion boolean")
            self.consumir(TokenType.THEN)
            self.comando()
            if self.aceptar(TokenType.ELSE):
                self.comando()
            return
        if self.aceptar(TokenType.WHILE):
            # La condicion del while tambien debe dar true o false.
            condicion = self.expresion()
            self.requerir_tipo(condicion, BOOLEAN, self.anterior, "while requiere una condicion boolean")
            self.consumir(TokenType.DO)
            self.comando()
            return
        if self.actual.tipo in {TokenType.READ, TokenType.WRITE}:
            # read necesita una variable donde guardar un dato. write acepta una
            # expresion y solamente hay que comprobar que este bien formada.
            lectura = self.aceptar(TokenType.READ)
            if not lectura:
                self.consumir(TokenType.WRITE)
            self.consumir(TokenType.PARENTESIS_ABRE)
            if lectura:
                nombre = self.consumir(TokenType.IDENTIFICADOR)
                self.tipo_destino(nombre)
            else:
                self.expresion()
            self.consumir(TokenType.PARENTESIS_CIERRA)

    def expresion(self) -> str:
        # Revisa comparaciones como a = b o numero < 10. Para = y <> los dos
        # lados deben tener el mismo tipo. Para <, <=, > y >= deben ser enteros.
        # El resultado de una comparacion siempre es true o false.
        izquierdo = self.expresion_simple()
        if self.actual.tipo in self.RELACIONES:
            operador = self.avanzar()
            derecho = self.expresion_simple()
            if operador.tipo in {TokenType.IGUAL, TokenType.DISTINTO}:
                self.comprobar_compatibles(izquierdo, derecho, operador, "los operandos deben tener el mismo tipo")
                return BOOLEAN
            else:
                tipos_validos = self.requerir_operandos(
                    izquierdo, derecho, INTEGER, operador,
                )
                return BOOLEAN if tipos_validos else DESCONOCIDO
        return izquierdo

    def expresion_simple(self) -> str:
        # Revisa sumas, restas y "or". + y - necesitan numeros enteros, mientras
        # que "or" necesita valores true o false.
        signo = None
        if self.actual.tipo in {TokenType.MAS, TokenType.MENOS}:
            signo = self.avanzar()
        resultado = self.termino()
        if signo is not None:
            self.requerir_tipo(resultado, INTEGER, signo, "el signo unario requiere integer")
            resultado = INTEGER if resultado != DESCONOCIDO else resultado
        while self.actual.tipo in self.ADITIVOS:
            operador = self.avanzar()
            derecho = self.termino()
            esperado = BOOLEAN if operador.tipo == TokenType.OR else INTEGER
            tipos_validos = self.requerir_operandos(
                resultado, derecho, esperado, operador,
            )
            resultado = esperado if tipos_validos else DESCONOCIDO
        return resultado

    def termino(self) -> str:
        # Revisa multiplicaciones, divisiones enteras y "and". Se hace antes que
        # las sumas y restas para respetar el orden normal de las operaciones.
        resultado = self.factor()
        while self.actual.tipo in self.MULTIPLICATIVOS:
            operador = self.avanzar()
            derecho = self.factor()
            esperado = BOOLEAN if operador.tipo == TokenType.AND else INTEGER
            tipos_validos = self.requerir_operandos(
                resultado, derecho, esperado, operador,
            )
            resultado = esperado if tipos_validos else DESCONOCIDO
        return resultado

    def factor(self) -> str:
        # Aca llegamos a las partes mas chicas de una cuenta: un nombre, un
        # numero, true, false, algo entre parentesis o un "not". Si encontramos
        # un nombre, buscamos que exista y vemos que tipo tiene.
        if self.actual.tipo == TokenType.IDENTIFICADOR:
            nombre = self.avanzar()
            if self.actual.tipo == TokenType.PARENTESIS_ABRE:
                argumentos = self.argumentos()
                return self.comprobar_llamada(nombre, argumentos, espera_funcion=True)
            simbolo = self.resolver(nombre)
            if simbolo is None:
                return DESCONOCIDO
            if simbolo["categoria"] == FUNCION and not simbolo["parametros"]:
                return simbolo["tipo"]
            if simbolo["categoria"] == RESULTADO_FUNCION:
                self.error(
                    nombre,
                    f"la variable de retorno '{nombre.lexema}' no puede usarse en una expresion",
                )
                return DESCONOCIDO
            if simbolo["categoria"] not in {
                VARIABLE,
                PARAMETRO,
            }:
                self.error(nombre, f"'{nombre.lexema}' no es una variable ni un parametro")
                return DESCONOCIDO
            return simbolo["tipo"]
        if self.aceptar(TokenType.NUMERO):
            return INTEGER
        if self.actual.tipo in {TokenType.TRUE, TokenType.FALSE}:
            self.avanzar()
            return BOOLEAN
        if self.aceptar(TokenType.PARENTESIS_ABRE):
            resultado = self.expresion()
            self.consumir(TokenType.PARENTESIS_CIERRA)
            return resultado
        operador = self.consumir(TokenType.NOT)
        resultado = self.factor()
        self.requerir_tipo(resultado, BOOLEAN, operador, "not requiere un operando boolean")
        return BOOLEAN if resultado != DESCONOCIDO else resultado

    def argumentos(self) -> list[tuple[str, Token]]:
        # Lee los valores enviados en una llamada. Guardamos el tipo de cada uno
        # y su posicion para poder marcar el lugar si esta equivocado.
        self.consumir(TokenType.PARENTESIS_ABRE)
        if self.aceptar(TokenType.PARENTESIS_CIERRA):
            return []
        argumentos = [(self.expresion(), self.anterior)]
        while self.aceptar(TokenType.COMA):
            argumentos.append((self.expresion(), self.anterior))
        self.consumir(TokenType.PARENTESIS_CIERRA)
        return argumentos

    def comprobar_llamada(
        self,
        nombre: Token,
        argumentos: list[tuple[str, Token]],
        espera_funcion: bool,
    ) -> str:
        # Comprueba que el nombre exista y que se este usando de la manera
        # correcta: una funcion dentro de una cuenta y un procedimiento como un
        # comando. Tambien revisa cuantos valores se enviaron y si cada uno tiene
        # el tipo que se esperaba.
        simbolo = self.ambiente_actual.buscar_rutina(nombre.lexema)
        if simbolo is None:
            encontrado = self.ambiente_actual.buscar(nombre.lexema)
            if encontrado is None:
                self.error(nombre, f"identificador '{nombre.lexema}' no declarado")
            else:
                uso = "funcion" if espera_funcion else "procedimiento"
                self.error(nombre, f"'{nombre.lexema}' no es un {uso}")
            return DESCONOCIDO
        clase_esperada = FUNCION if espera_funcion else PROCEDIMIENTO
        if simbolo["categoria"] != clase_esperada:
            uso = "funcion" if espera_funcion else "procedimiento"
            self.error(nombre, f"'{nombre.lexema}' no es un {uso}")
            return DESCONOCIDO
        if len(argumentos) != len(simbolo["parametros"]):
            self.error(
                nombre,
                f"'{nombre.lexema}' espera {len(simbolo['parametros'])} argumento(s), se recibieron {len(argumentos)}",
            )
        for indice, ((tipo_argumento, token), parametro) in enumerate(
            zip(argumentos, simbolo["parametros"]), start=1,
        ):
            self.comprobar_compatibles(
                parametro["tipo"], tipo_argumento, token,
                f"el argumento {indice} de '{nombre.lexema}' debe ser {parametro['tipo']}",
            )
        return simbolo["tipo"]

    def tipo_destino(self, nombre: Token) -> str:
        # Comprueba que el nombre pueda recibir un valor. Esto se permite para
        # variables, parametros y el nombre de la funcion donde se deja el
        # resultado. No se puede asignar un valor a un programa o procedimiento.
        simbolo = self.ambiente_actual.buscar(nombre.lexema)
        if simbolo is not None and simbolo["categoria"] in {
            VARIABLE,
            PARAMETRO,
            RESULTADO_FUNCION,
        }:
            if simbolo["categoria"] == RESULTADO_FUNCION:
                simbolo["resultado_asignado"] = True
            return simbolo["tipo"]

        if simbolo is None:
            self.error(nombre, f"identificador '{nombre.lexema}' no declarado")
        else:
            self.error(nombre, f"'{nombre.lexema}' no es un destino asignable")
        return DESCONOCIDO

    def resolver(self, token: Token) -> dict | None:
        # Busca el nombre en las tablas disponibles. Si no aparece, no fue
        # declarado y se agrega el error correspondiente.
        simbolo = self.ambiente_actual.buscar(token.lexema)
        if simbolo is None:
            self.error(token, f"identificador '{token.lexema}' no declarado")
        return simbolo

    def declarar(self, token: Token, tipo: str, categoria: str, parametros=None) -> dict | None:
        # Guarda un nombre nuevo en la tabla. Si ya estaba usado en el mismo
        # lugar, agrega un error con la posicion de la primera declaracion. Luego
        # sigue revisando el programa para encontrar los demas problemas.
        conflictos_con_programa = {
            VARIABLE: "variable global",
            PROCEDIMIENTO: "procedimiento",
            FUNCION: "funcion",
        }
        if (
            categoria in conflictos_con_programa
            and self.ambiente_actual.anterior is self.tabla_global
        ):
            programa = self.tabla_global.buscar_local(token.lexema)
            if programa is not None and programa["categoria"] == PROGRAMA:
                self.error(
                    token,
                    "mismo identificador programa y "
                    f"{conflictos_con_programa[categoria]}: '{token.lexema}'",
                )

        try:
            return self.ambiente_actual.insertar(
                token.lexema, tipo, categoria, token.columna, token.linea,
                parametros=parametros,
            )
        except SimboloDuplicadoError as exc:
            anterior = exc.anterior
            self.error(
                token,
                f"identificador '{token.lexema}' ya declarado en este ambito "
                f"(linea {anterior['linea']}, columna {anterior['columna']})",
            )
            return None

    def requerir_operandos(
        self, izquierdo: str, derecho: str, esperado: str, operador: Token,
    ) -> bool:
        # Revisa que los dos lados de una operacion tengan el tipo necesario. Si
        # uno ya tenia un error, no mostramos otro mensaje por la misma causa.
        if DESCONOCIDO in {izquierdo, derecho}:
            return False
        if izquierdo != esperado or derecho != esperado:
            self.error(operador, f"el operador '{operador.lexema}' requiere operandos {esperado}")
            return False
        return True

    def requerir_tipo(self, actual: str, esperado: str, token: Token, detalle: str) -> None:
        # Comprueba que algo tenga el tipo que se necesita en ese lugar.
        if actual not in {esperado, DESCONOCIDO}:
            self.error(token, detalle)

    def comprobar_compatibles(
        self, esperado: str, actual: str, token: Token, detalle: str,
    ) -> None:
        # Compara dos tipos. Si son diferentes, agrega el error recibido.
        if DESCONOCIDO not in {esperado, actual} and esperado != actual:
            self.error(token, detalle)

    def abrir_ambito(self, nombre: str, propietario: dict | None) -> None:
        # Al entrar a un programa, funcion o procedimiento, creamos una tabla
        # nueva para sus propios nombres y recordamos de donde venimos.
        ruta = f"{self.ambiente_actual.nombre}.{nombre.casefold()}"
        nuevo_ambiente = TablaSimbolos(ruta, self.ambiente_actual)
        self.ambiente_actual = nuevo_ambiente
        if propietario is not None:
            propietario["ambito_local"] = nuevo_ambiente

    def cerrar_ambito(self) -> None:
        # Al terminar ese bloque, volvemos a la tabla de afuera.
        if self.ambiente_actual.anterior is not None:
            self.ambiente_actual = self.ambiente_actual.anterior

    @property
    def anterior(self) -> Token:
        # Devuelve la ultima pieza que acabamos de leer.
        return self.tokens[self.current - 1]

    def aceptar(self, tipo: TokenType) -> bool:
        # Si la pieza actual es la que buscamos, la toma y avanza. Si no, deja
        # todo como estaba. Sirve para partes opcionales del programa.
        if self.actual.tipo != tipo:
            return False
        self.avanzar()
        return True

    def consumir(self, tipo: TokenType) -> Token:
        # Toma obligatoriamente la pieza esperada. Si aparece otra cosa, significa
        # que hay un problema interno porque el sintactico ya habia revisado esto.
        if self.actual.tipo != tipo:
            raise AssertionError(f"se esperaba {tipo}, se encontro {self.actual.tipo}")
        return self.avanzar()

    def avanzar(self) -> Token:
        # Toma la pieza actual y pasa a la siguiente.
        token = self.actual
        self.current += 1
        return token

    def error(self, token: Token, detalle: str) -> None:
        # Guarda el mensaje junto con su linea y columna, sin repetirlo.
        diagnostico = DiagnosticoError("semantico", token.linea, token.columna, detalle)
        if diagnostico not in self.diagnostics:
            self.diagnostics.append(diagnostico)


def analizar_semantica(tokens: list[Token]) -> ResultadoSemantico:
    # Es la entrada: recibe lo que preparo el sintactico,
    # ejecuta toda la revision y entrega el resultado.
    return AnalizadorSemantico(tokens).analizar()
