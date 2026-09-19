"""Analisis semantico y construccion de tablas de simbolos para mini-Pascal."""

from __future__ import annotations

from dataclasses import dataclass

from analizadorSintactico import DiagnosticoError, Token, TokenType
from tablaSimbolos import SimboloDuplicadoError, TablaSimbolos


INTEGER = "integer"
BOOLEAN = "boolean"
VOID = "void"
DESCONOCIDO = "desconocido"

PROGRAMA = "programa"
VARIABLE = "variable"
PARAMETRO = "parametro"
PROCEDIMIENTO = "procedimiento"
FUNCION = "funcion"
RESULTADO_FUNCION = "resultado_funcion"


@dataclass
class ResultadoSemantico:
    diagnostics: list[DiagnosticoError]
    tabla_global: TablaSimbolos


class AnalizadorSemantico:
    """Recorre nuevamente una entrada sintacticamente valida y comprueba tipos/nombres."""

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
        self.tokens = tokens
        self.current = 0
        self.diagnostics: list[DiagnosticoError] = []
        self.tabla_global = TablaSimbolos()
        self.ambiente_actual = self.tabla_global

    @property
    def actual(self) -> Token:
        return self.tokens[self.current]

    def analizar(self) -> ResultadoSemantico:
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
        if self.aceptar(TokenType.VAR):
            self.declaracion_variables()
            while self.aceptar(TokenType.PUNTO_Y_COMA):
                if self.actual.tipo != TokenType.IDENTIFICADOR:
                    break
                self.declaracion_variables()

        self.declaraciones_rutinas()
        self.comando_compuesto()

    def declaraciones_rutinas(self) -> None:
        if self.actual.tipo not in {TokenType.PROCEDURE, TokenType.FUNCTION}:
            return

        self.declaracion_rutina(self.actual.tipo == TokenType.FUNCTION)
        self.consumir(TokenType.PUNTO_Y_COMA)
        self.declaraciones_rutinas()

    def declaracion_variables(self) -> None:
        nombres = self.lista_identificadores()
        self.consumir(TokenType.DOS_PUNTOS)
        tipo = self.tipo()
        for token in nombres:
            self.declarar(token, tipo, VARIABLE)

    def declaracion_rutina(self, es_funcion: bool) -> None:
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
        nombres = [self.consumir(TokenType.IDENTIFICADOR)]
        while self.aceptar(TokenType.COMA):
            nombres.append(self.consumir(TokenType.IDENTIFICADOR))
        return nombres

    def tipo(self) -> str:
        if self.aceptar(TokenType.INTEGER):
            return INTEGER
        self.consumir(TokenType.BOOLEAN)
        return BOOLEAN

    def comando_compuesto(self) -> None:
        self.consumir(TokenType.BEGIN)
        self.comando()
        while self.aceptar(TokenType.PUNTO_Y_COMA):
            if self.actual.tipo == TokenType.END:
                break
            self.comando()
        self.consumir(TokenType.END)

    def comando(self) -> None:
        if self.actual.tipo == TokenType.IDENTIFICADOR:
            nombre = self.consumir(TokenType.IDENTIFICADOR)
            if self.aceptar(TokenType.ASIGNACION):
                tipo_expresion = self.expresion()
                tipo_destino = self.tipo_destino(nombre)
                self.comprobar_compatibles(
                    tipo_destino, tipo_expresion, nombre,
                    "la asignacion requiere tipos iguales",
                )
            else:
                argumentos = self.argumentos()
                self.comprobar_llamada(nombre, argumentos, espera_funcion=False)
            return
        if self.actual.tipo == TokenType.BEGIN:
            self.comando_compuesto()
            return
        if self.aceptar(TokenType.IF):
            condicion = self.expresion()
            self.requerir_tipo(condicion, BOOLEAN, self.anterior, "if requiere una condicion boolean")
            self.consumir(TokenType.THEN)
            self.comando()
            if self.aceptar(TokenType.ELSE):
                self.comando()
            return
        if self.aceptar(TokenType.WHILE):
            condicion = self.expresion()
            self.requerir_tipo(condicion, BOOLEAN, self.anterior, "while requiere una condicion boolean")
            self.consumir(TokenType.DO)
            self.comando()
            return
        if self.actual.tipo in {TokenType.READ, TokenType.WRITE}:
            lectura = self.aceptar(TokenType.READ)
            if not lectura:
                self.consumir(TokenType.WRITE)
            self.consumir(TokenType.PARENTESIS_ABRE)
            nombre = self.consumir(TokenType.IDENTIFICADOR)
            if lectura:
                self.tipo_destino(nombre)
            else:
                simbolo = self.resolver(nombre)
                if simbolo is not None and simbolo["categoria"] not in {VARIABLE, PARAMETRO}:
                    self.error(nombre, f"'{nombre.lexema}' no es un valor que pueda escribirse")
            self.consumir(TokenType.PARENTESIS_CIERRA)

    def expresion(self) -> str:
        izquierdo = self.expresion_simple()
        if self.actual.tipo in self.RELACIONES:
            operador = self.avanzar()
            derecho = self.expresion_simple()
            if operador.tipo in {TokenType.IGUAL, TokenType.DISTINTO}:
                self.comprobar_compatibles(izquierdo, derecho, operador, "los operandos deben tener el mismo tipo")
            else:
                self.requerir_operandos(izquierdo, derecho, INTEGER, operador)
            return BOOLEAN
        return izquierdo

    def expresion_simple(self) -> str:
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
            self.requerir_operandos(resultado, derecho, esperado, operador)
            resultado = esperado if DESCONOCIDO not in {resultado, derecho} else DESCONOCIDO
        return resultado

    def termino(self) -> str:
        resultado = self.factor()
        while self.actual.tipo in self.MULTIPLICATIVOS:
            operador = self.avanzar()
            derecho = self.factor()
            esperado = BOOLEAN if operador.tipo == TokenType.AND else INTEGER
            self.requerir_operandos(resultado, derecho, esperado, operador)
            resultado = esperado if DESCONOCIDO not in {resultado, derecho} else DESCONOCIDO
        return resultado

    def factor(self) -> str:
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
            if simbolo["categoria"] not in {
                VARIABLE,
                PARAMETRO,
                RESULTADO_FUNCION,
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
        simbolo = self.ambiente_actual.buscar(token.lexema)
        if simbolo is None:
            self.error(token, f"identificador '{token.lexema}' no declarado")
        return simbolo

    def declarar(self, token: Token, tipo: str, categoria: str, parametros=None) -> dict | None:
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
    ) -> None:
        if DESCONOCIDO in {izquierdo, derecho}:
            return
        if izquierdo != esperado or derecho != esperado:
            self.error(operador, f"el operador '{operador.lexema}' requiere operandos {esperado}")

    def requerir_tipo(self, actual: str, esperado: str, token: Token, detalle: str) -> None:
        if actual not in {esperado, DESCONOCIDO}:
            self.error(token, detalle)

    def comprobar_compatibles(
        self, esperado: str, actual: str, token: Token, detalle: str,
    ) -> None:
        if DESCONOCIDO not in {esperado, actual} and esperado != actual:
            self.error(token, detalle)

    def abrir_ambito(self, nombre: str, propietario: dict | None) -> None:
        ruta = f"{self.ambiente_actual.nombre}.{nombre.casefold()}"
        nuevo_ambiente = TablaSimbolos(ruta, self.ambiente_actual)
        self.ambiente_actual = nuevo_ambiente
        if propietario is not None:
            propietario["ambito_local"] = nuevo_ambiente

    def cerrar_ambito(self) -> None:
        if self.ambiente_actual.anterior is not None:
            self.ambiente_actual = self.ambiente_actual.anterior

    @property
    def anterior(self) -> Token:
        return self.tokens[self.current - 1]

    def aceptar(self, tipo: TokenType) -> bool:
        if self.actual.tipo != tipo:
            return False
        self.avanzar()
        return True

    def consumir(self, tipo: TokenType) -> Token:
        # La fase solo se ejecuta si el parser ya valido la secuencia.
        if self.actual.tipo != tipo:
            raise AssertionError(f"se esperaba {tipo}, se encontro {self.actual.tipo}")
        return self.avanzar()

    def avanzar(self) -> Token:
        token = self.actual
        self.current += 1
        return token

    def error(self, token: Token, detalle: str) -> None:
        diagnostico = DiagnosticoError("semantico", token.linea, token.columna, detalle)
        if diagnostico not in self.diagnostics:
            self.diagnostics.append(diagnostico)


def analizar_semantica(tokens: list[Token]) -> ResultadoSemantico:
    return AnalizadorSemantico(tokens).analizar()
