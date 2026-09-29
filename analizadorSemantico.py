# Analisis semantico y construccion de tablas de simbolos para mini-Pascal.
#
# Esta fase se ejecuta unicamente despues de que el analizador sintactico acepta
# la entrada. Por esa razon no intenta recuperarse de errores de gramatica ni
# construye un AST: recorre otra vez la secuencia de tokens siguiendo las mismas
# producciones de la gramatica. Durante ese recorrido registra identificadores,
# resuelve nombres, infiere tipos, valida llamadas y produce diagnosticos.
#
# Cuando el tipo de una subexpresion no puede determinarse, usa DESCONOCIDO para
# continuar el recorrido sin generar errores derivados del mismo problema.

from __future__ import annotations

from dataclasses import dataclass

from analizadorSintactico import DiagnosticoError, Token, TokenType
from tablaSimbolos import SimboloDuplicadoError, TablaSimbolos


# Tipos internos. Son cadenas porque tambien se guardan directamente en cada
# entrada de la tabla de simbolos. VOID identifica rutinas sin valor de retorno
# y DESCONOCIDO representa un error previo, no un tipo del lenguaje Pascal.
INTEGER = "integer"
BOOLEAN = "boolean"
VOID = "void"
DESCONOCIDO = "desconocido"

# Categorias posibles de una entrada de la tabla. RESULTADO_FUNCION modela la
# variable implicita de Pascal que tiene el mismo nombre que la funcion y a la
# cual se asigna el valor que esta devuelve.
PROGRAMA = "programa"
VARIABLE = "variable"
PARAMETRO = "parametro"
PROCEDIMIENTO = "procedimiento"
FUNCION = "funcion"
RESULTADO_FUNCION = "resultado_funcion"


@dataclass
class ResultadoSemantico:
    # Resultado publico de una ejecucion del analizador.
    # diagnostics contiene los errores en orden de aparicion. tabla_global es
    # la raiz del arbol de ambientes y se devuelve aunque existan errores.
    diagnostics: list[DiagnosticoError]
    tabla_global: TablaSimbolos


class AnalizadorSemantico:
    # Comprueba nombres, categorias y tipos de una entrada valida. current es el
    # cursor sobre tokens. ambiente_actual cambia al entrar o salir del programa
    # y de cada rutina, lo que permite aplicar alcance estatico.
    # Operadores agrupados por nivel de precedencia. Estos conjuntos permiten
    # que los metodos de expresiones reflejen directamente la gramatica:
    # expresion -> expresion_simple [relacion expresion_simple]
    # expresion_simple -> termino {aditivo termino}
    # termino -> factor {multiplicativo factor}
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
        # La secuencia debe estar validada por el sintactico e incluir el token
        # final. El recorrido siempre comienza en un ambiente global vacio.
        self.tokens = tokens
        self.current = 0
        self.diagnostics: list[DiagnosticoError] = []
        self.tabla_global = TablaSimbolos()
        self.ambiente_actual = self.tabla_global

    @property
    def actual(self) -> Token:
        # Consulta el token situado bajo el cursor sin consumirlo.
        return self.tokens[self.current]

    def analizar(self) -> ResultadoSemantico:
        # El nombre del programa vive en la tabla global, mientras que sus
        # declaraciones y comandos viven en un ambiente hijo. El enlace entre
        # ambos permite navegar luego todo el arbol desde tabla_global.
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
        # Un bloque tiene una seccion var opcional, posibles rutinas anidadas y
        # un comando compuesto begin/end. Los puntos y coma se consumen aqui
        # para distinguir otro grupo de variables de la seccion siguiente.
        if self.aceptar(TokenType.VAR):
            self.declaracion_variables()
            while self.aceptar(TokenType.PUNTO_Y_COMA):
                if self.actual.tipo != TokenType.IDENTIFICADOR:
                    break
                self.declaracion_variables()

        self.declaraciones_rutinas()
        self.comando_compuesto()

    def declaraciones_rutinas(self) -> None:
        # Procesa recursivamente la lista de procedimientos y funciones.
        if self.actual.tipo not in {TokenType.PROCEDURE, TokenType.FUNCTION}:
            return

        self.declaracion_rutina(self.actual.tipo == TokenType.FUNCTION)
        self.consumir(TokenType.PUNTO_Y_COMA)
        self.declaraciones_rutinas()

    def declaracion_variables(self) -> None:
        # Declara un grupo de la forma: id {, id} : tipo.
        nombres = self.lista_identificadores()
        self.consumir(TokenType.DOS_PUNTOS)
        tipo = self.tipo()
        for token in nombres:
            self.declarar(token, tipo, VARIABLE)

    def declaracion_rutina(self, es_funcion: bool) -> None:
        # La firma se inserta primero en el ambiente exterior para que el cuerpo
        # y las rutinas anidadas puedan encontrarla. En una funcion tambien se
        # crea RESULTADO_FUNCION: la variable implicita a la que se asigna el
        # valor devuelto. es_funcion distingue function de procedure.
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

        # Un simbolo duplicado no se inserta y ``simbolo`` sera None. Aun asi se
        # abre el ambiente para poder analizar el cuerpo y descubrir mas errores.
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
        # Cada parametro conserva nombre, tipo y posicion. Primero se construye
        # la firma ordenada; los parametros se insertan en la tabla local despues
        # de abrir el ambiente. La firma tambien se usa para validar llamadas.
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
        # Consume una lista no vacia de nombres separados por comas.
        nombres = [self.consumir(TokenType.IDENTIFICADOR)]
        while self.aceptar(TokenType.COMA):
            nombres.append(self.consumir(TokenType.IDENTIFICADOR))
        return nombres

    def tipo(self) -> str:
        # Convierte un tipo de la gramatica en su representacion interna.
        if self.aceptar(TokenType.INTEGER):
            return INTEGER
        self.consumir(TokenType.BOOLEAN)
        return BOOLEAN

    def comando_compuesto(self) -> None:
        # Analiza: begin comando {; comando} end. Se admite un punto y coma antes
        # de end porque el sintactico ya comprobo que la secuencia fuera valida.
        self.consumir(TokenType.BEGIN)
        self.comando()
        while self.aceptar(TokenType.PUNTO_Y_COMA):
            if self.actual.tipo == TokenType.END:
                break
            self.comando()
        self.consumir(TokenType.END)

    def comando(self) -> None:
        # Un identificador seguido por := inicia una asignacion; en caso
        # contrario inicia una llamada a procedimiento. if y while requieren
        # condiciones booleanas. read necesita un destino asignable y write
        # recorre su argumento como cualquier otra expresion.
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
            if lectura:
                nombre = self.consumir(TokenType.IDENTIFICADOR)
                self.tipo_destino(nombre)
            else:
                self.expresion()
            self.consumir(TokenType.PARENTESIS_CIERRA)

    def expresion(self) -> str:
        # = y <> aceptan operandos del mismo tipo; las relaciones de orden exigen
        # enteros. Una relacion valida produce boolean. Si un operando ya es
        # DESCONOCIDO, se evita generar otro diagnostico por el mismo problema.
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
        # Los signos unarios, + y - trabajan con integer. or trabaja con boolean.
        # El bucle aplica los operadores con asociatividad izquierda.
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
        # * y div trabajan con integer; and trabaja con boolean. Al ejecutarse
        # dentro de expresion_simple, este nivel tiene mayor precedencia.
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
        # Un factor puede ser una variable, parametro, funcion, literal,
        # expresion entre parentesis o negacion. Las funciones con parametros
        # requieren llamada explicita; las que no tienen parametros pueden usarse
        # por su nombre. El resultado implicito solo puede recibir asignaciones:
        # no se lee como variable para evitar confundirlo con una llamada.
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
        # Cada argumento guarda su tipo y el ultimo token de su expresion. Ese
        # token proporciona la ubicacion para un posible error de tipos.
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
        # espera_funcion indica si la llamada aparece dentro de una expresion y
        # debe devolver un valor. Primero se valida la categoria de la rutina y
        # la cantidad de argumentos. Despues se comparan sus tipos por posicion.
        # zip evita accesos fuera de rango si las cantidades son diferentes, pero
        # permite revisar todos los pares disponibles. Ante un nombre o categoria
        # incorrectos se devuelve DESCONOCIDO para continuar sin errores en cadena.
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
        # Variables, parametros y resultados de funcion pueden recibir valores.
        # Asignar al resultado tambien marca resultado_asignado, que se revisa al
        # cerrar la funcion. Las demas categorias producen un diagnostico.
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
        # Busca un identificador visible e informa si no fue declarado.
        simbolo = self.ambiente_actual.buscar(token.lexema)
        if simbolo is None:
            self.error(token, f"identificador '{token.lexema}' no declarado")
        return simbolo

    def declarar(self, token: Token, tipo: str, categoria: str, parametros=None) -> dict | None:
        # Inserta una declaracion usando los datos y la posicion de token.
        # Ademas de duplicados locales, impide reutilizar el nombre del programa
        # para una variable global o rutina. Si hay conflicto devuelve None en
        # vez de interrumpir el recorrido, para poder descubrir mas errores.
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
        # Comprueba ambos operandos. Si uno es DESCONOCIDO devuelve False sin
        # repetir el error anterior; si son conocidos pero incorrectos, informa.
        if DESCONOCIDO in {izquierdo, derecho}:
            return False
        if izquierdo != esperado or derecho != esperado:
            self.error(operador, f"el operador '{operador.lexema}' requiere operandos {esperado}")
            return False
        return True

    def requerir_tipo(self, actual: str, esperado: str, token: Token, detalle: str) -> None:
        # Informa si un valor conocido no tiene el tipo puntual requerido.
        if actual not in {esperado, DESCONOCIDO}:
            self.error(token, detalle)

    def comprobar_compatibles(
        self, esperado: str, actual: str, token: Token, detalle: str,
    ) -> None:
        # Exige tipos iguales, salvo que un error previo haya dejado uno desconocido.
        if DESCONOCIDO not in {esperado, actual} and esperado != actual:
            self.error(token, detalle)

    def abrir_ambito(self, nombre: str, propietario: dict | None) -> None:
        # Crea un ambiente hijo con una ruta normalizada. El enlace guardado en
        # propietario permite navegar desde el simbolo hacia su tabla local.
        ruta = f"{self.ambiente_actual.nombre}.{nombre.casefold()}"
        nuevo_ambiente = TablaSimbolos(ruta, self.ambiente_actual)
        self.ambiente_actual = nuevo_ambiente
        if propietario is not None:
            propietario["ambito_local"] = nuevo_ambiente

    def cerrar_ambito(self) -> None:
        # Regresa al ambiente exterior sin sobrepasar la tabla global.
        if self.ambiente_actual.anterior is not None:
            self.ambiente_actual = self.ambiente_actual.anterior

    @property
    def anterior(self) -> Token:
        # Consulta el ultimo token consumido por el recorrido.
        return self.tokens[self.current - 1]

    def aceptar(self, tipo: TokenType) -> bool:
        # Consume el tipo esperado solo si coincide con el token actual.
        if self.actual.tipo != tipo:
            return False
        self.avanzar()
        return True

    def consumir(self, tipo: TokenType) -> Token:
        # Consume obligatoriamente el tipo indicado. Como el parser ya valido la
        # secuencia, una discrepancia seria un error interno y no un error del
        # programa fuente; por eso se lanza AssertionError.
        if self.actual.tipo != tipo:
            raise AssertionError(f"se esperaba {tipo}, se encontro {self.actual.tipo}")
        return self.avanzar()

    def avanzar(self) -> Token:
        # Devuelve el token actual y mueve el cursor a la posicion siguiente.
        token = self.actual
        self.current += 1
        return token

    def error(self, token: Token, detalle: str) -> None:
        # Registra linea, columna y detalle, evitando diagnosticos duplicados.
        diagnostico = DiagnosticoError("semantico", token.linea, token.columna, detalle)
        if diagnostico not in self.diagnostics:
            self.diagnostics.append(diagnostico)


def analizar_semantica(tokens: list[Token]) -> ResultadoSemantico:
    # Punto de entrada usado por analizadorSintactico. Recibe tokens ya validados
    # y devuelve los diagnosticos junto con la raiz de las tablas construidas.
    return AnalizadorSemantico(tokens).analizar()
