"""Tabla de simbolos por ambiente para mini-Pascal."""


class SimboloDuplicadoError(Exception):
    def __init__(self, anterior):
        self.anterior = anterior


class TablaSimbolos:
    """Ambiente con una tabla hash propia y un enlace al ambiente exterior."""

    def __init__(self, nombre="global", anterior=None):
        self.nombre = nombre
        self.tabla = {}
        self.anterior = anterior
        self.hijos = []
        if anterior is not None:
            anterior.hijos.append(self)

    @staticmethod
    def _normalizar(nombre):
        return nombre.casefold()

    def insertar(
        self,
        nombre,
        tipo,
        categoria,
        columna,
        linea,
        parametros=None,
    ):
        clave = self._normalizar(nombre)
        if clave in self.tabla:
            raise SimboloDuplicadoError(self.tabla[clave])

        simbolo = {
            "nombre": nombre,
            "tipo": tipo,
            "categoria": categoria,
            "ambito": self.nombre,
            "linea": linea,
            "columna": columna,
            "parametros": parametros or [],
            "nombre_original_funcion": None,
            "resultado_asignado": False,
            "ambito_local": None,
        }
        self.tabla[clave] = simbolo
        return simbolo

    def buscar_local(self, nombre):
        return self.tabla.get(self._normalizar(nombre))

    def buscar(self, nombre):
        ambiente = self
        while ambiente is not None:
            simbolo = ambiente.buscar_local(nombre)
            if simbolo is not None:
                return simbolo
            ambiente = ambiente.anterior
        return None

    def buscar_rutina(self, nombre):
        ambiente = self
        while ambiente is not None:
            simbolo = ambiente.buscar_local(nombre)
            if simbolo is not None and simbolo["categoria"] in {"procedimiento", "funcion"}:
                return simbolo
            ambiente = ambiente.anterior
        return None
